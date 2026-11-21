//! エンジン（段階1）: タスクスタック・ターン進行（start / draw / charge / main の選択肢 / attack / end）・
//! イベント（draw / untap / move(マナチャージ) / turn_start / turn_end）・状況起因処理（デッキ切れ）。
//! Python 版 dmsim/engine/{core,turn,events}.py と同じ順序・同じ状態の書き換えを行う（digest が一致することが基準）。
//! 未移植の処理に当たったら Err(Unsupported) を返す。
use crate::rules::Rules;
use crate::state::GameState;
use serde_json::{json, Map, Value};
use std::collections::BTreeMap;
use std::sync::Arc;

#[derive(Debug)]
pub enum EngErr {
    Unsupported(String),
    Illegal(String),
}
pub type R<T> = Result<T, EngErr>;

fn uns<T>(what: impl Into<String>) -> R<T> {
    Err(EngErr::Unsupported(what.into()))
}

/// 常在型の条件の入れ子の深さ（&self から増減する。PyO3 の型は Sync が要るので原子変数）
#[derive(Default)]
pub struct SDepth(std::sync::atomic::AtomicU32);
impl SDepth {
    pub fn get(&self) -> u32 { self.0.load(std::sync::atomic::Ordering::Relaxed) }
    pub fn set(&self, v: u32) { self.0.store(v, std::sync::atomic::Ordering::Relaxed) }
}
impl Clone for SDepth {
    fn clone(&self) -> Self { SDepth(std::sync::atomic::AtomicU32::new(self.get())) }
}

/// 特性計算中のカード集合（Python の _chars_busy）。Clone は中身のコピー
pub struct BusySet(std::sync::Mutex<std::collections::HashSet<i64>>);
impl BusySet {
    fn contains(&self, cid: i64) -> bool { self.0.lock().unwrap().contains(&cid) }
    fn insert(&self, cid: i64) -> bool { self.0.lock().unwrap().insert(cid) }
    fn remove(&self, cid: i64) { self.0.lock().unwrap().remove(&cid); }
}
impl Clone for BusySet {
    fn clone(&self) -> Self { BusySet(std::sync::Mutex::new(self.0.lock().unwrap().clone())) }
}
impl Default for BusySet {
    fn default() -> Self { BusySet(std::sync::Mutex::new(std::collections::HashSet::new())) }
}

/// power_when の再入ガード（Python の _pw_busy）
pub struct PwBusy(std::sync::atomic::AtomicBool);
impl PwBusy {
    fn get(&self) -> bool { self.0.load(std::sync::atomic::Ordering::Relaxed) }
    fn set(&self, v: bool) { self.0.store(v, std::sync::atomic::Ordering::Relaxed) }
}
impl Clone for PwBusy {
    fn clone(&self) -> Self { PwBusy(std::sync::atomic::AtomicBool::new(self.get())) }
}
impl Default for PwBusy {
    fn default() -> Self { PwBusy(std::sync::atomic::AtomicBool::new(false)) }
}

#[derive(Clone)]
pub struct Engine {
    pub s: GameState,
    pub rules: Arc<Rules>,
    pub log: Vec<Value>,
    pub step_limit: i64,
    pub turn_limit: i64,
    /// 常在型の条件を評価中の深さ（Python の _in_static_cond。2段目からはフィルタが印刷の特性を見る）
    pub static_depth: SDepth,
    /// 特性を計算中のカード（Python の _chars_busy。計算中のカードをフィルタで見る時は印刷の特性で見る）
    pub chars_busy: BusySet,
    /// power_when の count を数えている最中か（Python の _pw_busy。入れ子の power_when は 0）
    pub pw_busy: PwBusy,
}

enum Ask {
    Answer(Vec<usize>),
    Decision(Value),
}

/// 特性の計算結果（Python の chars の、plain の範囲で要る部分だけ）
struct Chars {
    power: i64,
    pay_cost: i64,
    allow: Vec<Value>,
    deny: Vec<Value>,
    require: Vec<String>,
    break_opts: Vec<i64>,
    breaks: i64,
    breaks_add: i64,
    keywords: Vec<String>,
    win_all_battles: bool,
    sealed: bool,
}

impl Engine {
    pub fn new(s: GameState, rules: Arc<Rules>) -> R<Engine> {
        for c in &s.cards {
            match rules.cards.get(&c.defn) {
                Some(d) if d.plain => {}
                Some(_) => return uns(format!("card {} (plain でない)", c.defn)),
                None => return Err(EngErr::Illegal(format!("unknown card {}", c.defn))),
            }
        }
        Ok(Engine { s, rules, log: vec![], step_limit: 20000, turn_limit: 80, static_depth: SDepth::default(),
                    chars_busy: BusySet::default(), pw_busy: PwBusy::default() })
    }

    // ---- 基本の読み取り ----
    fn shared(&self, z: &str) -> bool {
        z != "hold" && self.rules.zone(z).shared
    }
    fn zl(&self, z: &str, p: i64) -> &Vec<i64> {
        &self.s.zones[z][if self.shared(z) { 0 } else { p as usize }]
    }
    /// 今使っている面の定義（Python の fdef(cid)。ツインパクトはバトルゾーン・保留中は面、他のゾーンでは両面を合わせた定義）
    fn def(&self, cid: i64) -> &crate::rules::CardDef {
        let c = &self.s.cards[cid as usize];
        let d = &self.rules.cards[&c.defn];
        if c.face >= 0 && !d.faces.is_empty() { &d.faces[c.face as usize] } else { d }
    }
    /// 面を指定した定義（Python の fdef(cid, face)）
    fn fdef(&self, cid: i64, face: Option<i64>) -> &crate::rules::CardDef {
        match face {
            Some(f) => {
                let d = &self.rules.cards[&self.s.cards[cid as usize].defn];
                if d.faces.is_empty() { d } else { &d.faces[f as usize] }
            }
            None => self.def(cid),
        }
    }
    /// 面の一覧（面を持たない札は [None]）
    fn face_list(&self, cid: i64) -> Vec<Option<i64>> {
        let n = self.rules.cards[&self.s.cards[cid as usize].defn].faces.len();
        if n == 0 { vec![None] } else { (0..n as i64).map(Some).collect() }
    }
    /// 101.2: 禁止 → 許可 → 既定値。自分自身への常在型はバトルゾーンにある間だけ働く
    fn permits(&self, cid: i64, action: &str) -> bool {
        self.permits_face(cid, action, None)
    }
    /// 相手側のカード other に対して action できるか（Python の permits(cid, action, other)）。辞書形の禁止 {action, other} を見る
    fn permits_vs(&self, cid: i64, action: &str, other: i64) -> bool {
        self.permits_o(cid, action, None, Some(other))
    }
    /// 継続的効果が cid に及ぶか（Python の _ce_applies）。範囲固定は affected、dynamic は生成時にベイクした filter
    fn ce_applies(&self, ce: &Value, cid: i64) -> bool {
        if let Some(a) = ce["affected"].as_array() {
            return a.contains(&self.refv(cid));
        }
        let f = &ce["filter"];
        let c = &self.s.cards[cid as usize];
        // Python の zones_of: "any" は全ゾーン、配列はそのどれか
        let fz = &f["zone"];
        let zone_ok = match fz.as_str() {
            Some("any") => true,
            Some(z) => z == c.zone,
            None => fz.as_array().map_or(false, |a| a.iter().any(|z| z.as_str() == Some(c.zone.as_str()))),
        };
        if !zone_ok {
            return false;
        }
        if f["owner"] != json!("any") && f["owner"].as_i64() != Some(c.controller) {
            return false;
        }
        // Python は base=True（印刷の特性）で照合する
        self.static_depth.set(self.static_depth.get() + 2);
        let ok = self.filter_ok(cid, &f["filter"]).unwrap_or(false);
        self.static_depth.set(self.static_depth.get() - 2);
        ok
    }
    /// キーワードの常在型（Python の rules.keywords の static の写し。(zone, mod) の列）
    fn kw_static_mods(kw: &str) -> Vec<(&'static str, Value)> {
        match kw {
            "blocker" => vec![("bz", json!({"allow": ["block"]}))],
            "cannot_attack" => vec![("bz", json!({"deny": ["attack_player", "attack_creature"]}))],
            "cannot_attack_player" => vec![("bz", json!({"deny": ["attack_player"]}))],
            "cannot_be_attacked" => vec![("bz", json!({"deny": ["be_attacked"]}))],
            "cannot_block" => vec![("bz", json!({"deny": ["block"]}))],
            "cannot_untap" => vec![("bz", json!({"deny": ["untap_at_start"]}))],
            "double_breaker" => vec![("bz", json!({"breaks": 2}))],
            "guardman" => vec![("bz", json!({"allow": ["guardman"]}))],
            "hunting" => vec![("bz", json!({"battle_power": {"amount": 1000, "count": {"zone": "bz", "owner": "you", "filter": {"race_has": "ハンター"}}}}))],
            "must_attack" => vec![("bz", json!({"require": ["attack"]}))],
            "null_breaker" => vec![("bz", json!({"breaks": 0}))],
            "powered_breaker" => vec![("bz", json!({"breaks_per_power": 6000}))],
            "quad_breaker" => vec![("bz", json!({"breaks": 4}))],
            "s_trigger" | "s_trigger_plus" | "super_s_trigger" => vec![("shield", json!({"allow": ["s_trigger"]}))],
            "shinka_rise" => vec![("bz", json!({"allow": ["evolve_base"]}))],
            "slayer" => vec![("bz", json!({"allow": ["slayer"]}))],
            "speed_attacker" => vec![("bz", json!({"allow": ["attack_summoning_sick"]}))],
            "abyss_rush" | "summon_from_graveyard" => vec![("graveyard", json!({"allow": ["summon_from_graveyard"]}))],
            "summon_from_mana" => vec![("mana", json!({"allow": ["summon_from_mana"]}))],
            "triple_breaker" => vec![("bz", json!({"breaks": 3}))],
            "unblockable" => vec![("bz", json!({"deny": ["be_blocked"]}))],
            "world_breaker" => vec![("bz", json!({"breaks": 99}))],
            _ => vec![],
        }
    }
    /// 常在型の if 条件の評価（Python の _static_cond: 深さを 1 つ上げて評価し、失敗は不成立として扱う）
    fn eval_static_cond(&self, cond: &Value, env: &Value) -> bool {
        self.static_depth.set(self.static_depth.get() + 1);
        let ok = self.eval_cond(cond, env).unwrap_or(false);
        self.static_depth.set(self.static_depth.get() - 1);
        ok
    }
    /// セレクタの件数（Python の count_of: 数えられないセレクタは 0 として扱う）
    fn count_of(&self, v: &Value, env: &Value) -> i64 {
        self.candidates_ro(v, env).map(|l| l.len() as i64).unwrap_or(0)
    }
    /// Python の _subject_match（特性計算から base=True で呼ばれる形）。pat は "self" か辞書
    fn subject_match(&self, pat: &Value, cid: i64, env: &Value) -> bool {
        if let Some(s) = pat.as_str() {
            return s == "self" && env["self"][0].as_i64() == Some(cid);
        }
        let obj = match pat.as_object() {
            Some(o) => o,
            None => return false,
        };
        if let Some(z) = obj.get("zone") {
            if z.as_str() != Some(self.s.cards[cid as usize].zone.as_str()) {
                return false;
            }
        }
        if let Some(o) = obj.get("owner") {
            let os = o.as_str().unwrap_or("");
            if os != "any" {
                let you = env["you"].as_i64().unwrap_or(0);
                let want = if os == "you" { you } else if os == "opp" { 1 - you } else { -1 };
                if self.s.cards[cid as usize].controller != want {
                    return false;
                }
            }
        }
        if obj.get("other").and_then(|v| v.as_bool()).unwrap_or(false) && env["self"][0].as_i64() == Some(cid) {
            return false;
        }
        let f = obj.get("filter").cloned().unwrap_or(json!({}));
        // Python は base=True（印刷の特性）で照合する
        self.static_depth.set(self.static_depth.get() + 2);
        let ok = self.filter_ok(cid, &f).unwrap_or(false);
        self.static_depth.set(self.static_depth.get() - 2);
        ok
    }
    /// 他のカードに及ぶ常在型を持つか（Python の _affects_others）
    fn affects_others(&self, src: i64) -> bool {
        self.fdef(src, None).abil.iter().any(|ab| {
            ab["kind"] == json!("static") && ab.get("mod").is_some()
                && ab.get("affects").and_then(|v| v.as_str()) != Some("self")
        })
    }
    /// 発生源 src の、ab_zone にいる間の常在型のうち対象 target に及ぶものを mods に足す
    /// （Python の _chars_calc の発生源ループ）。src_of は once つき許可の発生源として記録する値
    /// （シールドゾーンの発生源は Python の src_of に載らないので対象自身になる）
    fn collect_aff(&self, src: i64, src_of: i64, target: i64, ab_zone: &str, mods: &mut Vec<(i64, Value)>) {
        let zone = self.s.cards[target as usize].zone.clone();
        let env = json!({"you": self.s.cards[src as usize].controller, "self": self.refv(src), "vars": {}});
        for ab in &self.fdef(src, None).abil {
            if ab["kind"] != json!("static") {
                continue;
            }
            if ab.get("zone").and_then(|v| v.as_str()).unwrap_or("bz") != ab_zone {
                continue;
            }
            let m = match ab.get("mod") {
                Some(m) => m,
                None => continue,
            };
            let aff = ab.get("affects").cloned().unwrap_or(json!({}));
            if aff.as_str() == Some("self") {
                continue;
            }
            if aff.get("zone").and_then(|v| v.as_str()).unwrap_or("bz") != zone {
                continue;
            }
            if !self.subject_match(&aff, target, &env) {
                continue;
            }
            if let Some(cond) = ab.get("if") {
                if !self.eval_static_cond(cond, &env) {
                    continue;
                }
            }
            mods.push((src_of, m.clone()));
        }
    }
    /// power_when の値（Python の _power_when: 攻撃タスクを見て、攻撃中／ブロック中なら amount × 件数）
    fn power_when(&self, pw: &Value, refv: &Value, env_self: &Value) -> i64 {
        let amount = pw.get("amount").and_then(|v| v.as_i64()).unwrap_or(0);
        let attacking = pw.get("when").and_then(|v| v.as_str()) == Some("attacking");
        for t in &self.s.tasks {
            if t["t"] != json!("attack") {
                continue;
            }
            let cand = if attacking {
                &t["attacker"]
            } else if t.get("blocked").and_then(|v| v.as_bool()).unwrap_or(false) {
                &t["target"]
            } else {
                continue;
            };
            if cand == refv {
                return match pw.get("count") {
                    None => amount,
                    Some(cnt) => {
                        if self.pw_busy.get() {
                            0
                        } else {
                            self.pw_busy.set(true);
                            let n = self.count_of(cnt, env_self);
                            self.pw_busy.set(false);
                            amount * n
                        }
                    }
                };
            }
        }
        0
    }
    /// 特性の計算（Python の chars / _chars_calc_body の写し）。計算中のカードは busy に載せ、
    /// フィルタがそのカードを見る時は印刷の特性で見る（Python の _chars_busy）
    fn chars(&self, cid: i64, face: Option<i64>) -> Chars {
        let inserted = self.chars_busy.insert(cid);
        let out = self.chars_inner(cid, face);
        if inserted {
            self.chars_busy.remove(cid);
        }
        out
    }
    fn chars_inner(&self, cid: i64, face: Option<i64>) -> Chars {
        let (zone, controller) = {
            let c = &self.s.cards[cid as usize];
            (c.zone.clone(), c.controller)
        };
        let d = self.fdef(cid, face);
        if face.is_none() && zone == "bz" && !self.s.cards[cid as usize].seals.is_empty() {
            // 封印されているクリーチャーは無視される（Python の _chars_calc の早期リターン）
            return Chars { power: d.power, pay_cost: d.cost, allow: vec![], deny: vec![], require: vec![],
                           break_opts: vec![], breaks: 0, breaks_add: 0, keywords: vec![],
                           win_all_battles: false, sealed: true };
        }
        let env_self = json!({"you": controller, "self": self.refv(cid), "vars": {}});
        // (発生源, mod) の列: 自分への常在型 → バトルゾーンの常在型 → シールドゾーンの常在型
        // → 継続的効果 → 与えられたキーワードの常在型（Python の _chars_calc_body の収集順）
        let mut mods: Vec<(i64, Value)> = vec![];
        for ab in &d.abil {
            if ab["kind"] != json!("static") || ab.get("affects").and_then(|v| v.as_str()) != Some("self") {
                continue;
            }
            let m = match ab.get("mod") {
                Some(m) => m,
                None => continue,
            };
            if ab.get("zone").and_then(|v| v.as_str()).unwrap_or("bz") != zone {
                continue;
            }
            if let Some(cond) = ab.get("if") {
                if !self.eval_static_cond(cond, &env_self) {
                    continue;
                }
            }
            mods.push((cid, m.clone()));
        }
        let bz: Vec<i64> = self.s.zones["bz"][0].clone();
        for src in bz {
            if self.s.cards[src as usize].top_of >= 0 || !self.affects_others(src) {
                continue;
            }
            if !self.s.cards[src as usize].seals.is_empty() {
                continue;   // 封印されているクリーチャーの能力は機能しない（Python の abilities() が空を返す）
            }
            self.collect_aff(src, src, cid, "bz", &mut mods);
        }
        for p in 0..2 {
            let sh: Vec<i64> = self.s.zones["shield"][p].clone();
            for src in sh {
                if !self.affects_others(src) {
                    continue;
                }
                self.collect_aff(src, cid, cid, "shield", &mut mods);
            }
        }
        for ce in &self.s.continuous {
            if self.ce_applies(ce, cid) {
                mods.push((cid, ce["mod"].clone()));
            }
        }
        // 与えられたキーワード（印刷に無いもの、名前順）の常在型は 1 段だけ
        let mut granted: Vec<String> = vec![];
        for (_, m) in &mods {
            if let Some(l) = m.get("grant").and_then(|v| v.as_array()) {
                for kw in l.iter().filter_map(|x| x.as_str()) {
                    if !d.keywords.iter().any(|k| k == kw) && !granted.iter().any(|k| k == kw) {
                        granted.push(kw.to_string());
                    }
                }
            }
        }
        granted.sort();
        for kw in &granted {
            for (z, m) in Self::kw_static_mods(kw) {
                if z == zone {
                    mods.push((cid, m));
                }
            }
        }
        // 畳み込み（Python の _chars_calc_body の本体ループと同じ順）
        let mut ch = Chars { power: d.power, pay_cost: d.cost, allow: vec![], deny: vec![], require: vec![],
                             break_opts: vec![], breaks: 1, breaks_add: 0, keywords: d.keywords.clone(),
                             win_all_battles: false, sealed: false };
        let mut cost_min = 0i64;
        for (src, m) in &mods {
            match m.get("power") {
                Some(pw) if pw.is_object() => {
                    let amount = pw.get("amount").and_then(|v| v.as_i64()).unwrap_or(0);
                    let n = match pw.get("count") {
                        Some(cnt) => self.count_of(cnt, &env_self),
                        None => 1,
                    };
                    ch.power += amount * n;
                }
                Some(pw) => ch.power += pw.as_i64().unwrap_or(0),
                None => {}
            }
            if let Some(pwn) = m.get("power_when") {
                ch.power += self.power_when(pwn, &env_self["self"], &env_self);
            }
            if let Some(l) = m.get("grant").and_then(|v| v.as_array()) {
                for kw in l.iter().filter_map(|x| x.as_str()) {
                    if !ch.keywords.iter().any(|k| k == kw) {
                        ch.keywords.push(kw.to_string());
                    }
                }
            }
            if let Some(l) = m.get("allow").and_then(|v| v.as_array()) {
                for e in l {
                    if e.is_object() && e.get("once").and_then(|v| v.as_bool()).unwrap_or(false) {
                        let mut e2 = e.clone();
                        e2["src"] = json!(src);
                        ch.allow.push(e2);
                    } else {
                        ch.allow.push(e.clone());
                    }
                }
            }
            if let Some(l) = m.get("deny").and_then(|v| v.as_array()) {
                ch.deny.extend(l.iter().cloned());
            }
            if let Some(l) = m.get("require").and_then(|v| v.as_array()) {
                ch.require.extend(l.iter().filter_map(|x| x.as_str().map(String::from)));
            }
            if m.get("win_all_battles").and_then(|v| v.as_bool()).unwrap_or(false) {
                ch.win_all_battles = true;
            }
            if let Some(n) = m.get("breaks_add").and_then(|v| v.as_i64()) {
                ch.breaks_add += n;
            }
            if let Some(b) = m.get("breaks").and_then(|v| v.as_i64()) {
                ch.break_opts.push(b);
                ch.breaks = ch.breaks.max(b);
            }
            match m.get("cost") {
                Some(cv) if cv.is_object() => {
                    let amount = cv.get("amount").and_then(|v| v.as_i64()).unwrap_or(0);
                    let n = match cv.get("count") {
                        Some(cnt) => self.count_of(cnt, &env_self),
                        None => 1,
                    };
                    ch.pay_cost += amount * n;
                }
                Some(cv) => ch.pay_cost += cv.as_i64().unwrap_or(0),
                None => {}
            }
            cost_min = cost_min.max(m.get("cost_min").and_then(|v| v.as_i64()).unwrap_or(0));
        }
        ch.pay_cost = ch.pay_cost.max(cost_min);
        // パワード・ブレイカーは最終パワーで見る（Python の後段ループ）
        for (_, m) in &mods {
            if let Some(v) = m.get("breaks_per_power").and_then(|x| x.as_i64()) {
                let n = 1 + ch.power.max(0) / v;
                ch.break_opts.push(n);
                ch.breaks = ch.breaks.max(n);
            }
        }
        if ch.breaks_add != 0 {
            if ch.break_opts.is_empty() {
                ch.break_opts = vec![ch.breaks];
            }
            for v in &mut ch.break_opts {
                *v = (*v + ch.breaks_add).max(0);
            }
            ch.breaks = ch.break_opts.iter().copied().max().unwrap_or(0);
        }
        ch.keywords.sort();
        ch.keywords.dedup();
        ch
    }
    /// Python の permits の hit: 文字列は行動名一致、辞書は action 一致＋ other フィルタ
    /// （許可される側 cid を基準に式を前評価してから照合する）
    fn entries_hit(&self, cid: i64, entries: &[Value], action: &str, other: Option<i64>) -> bool {
        for e in entries {
            if let Some(s) = e.as_str() {
                if s == action {
                    return true;
                }
            } else if e.get("action").and_then(|v| v.as_str()) == Some(action) {
                match other {
                    None => return true,
                    Some(o) => {
                        let f = e.get("other").cloned().unwrap_or(json!({}));
                        let env = json!({"you": self.s.cards[cid as usize].controller, "self": self.refv(cid), "vars": {}});
                        let baked = self.bake_filter(&f, &env).unwrap_or(f);
                        if self.filter_ok(o, &baked).unwrap_or(false) {
                            return true;
                        }
                    }
                }
            }
        }
        false
    }
    fn permits_face(&self, cid: i64, action: &str, face: Option<i64>) -> bool {
        self.permits_o(cid, action, face, None)
    }
    /// Python の permits(cid, action, other, face) の写し: 特性（chars）の禁止を全て見てから許可を見る（101.2）
    fn permits_o(&self, cid: i64, action: &str, face: Option<i64>, other: Option<i64>) -> bool {
        let ch = self.chars(cid, face);
        if self.entries_hit(cid, &ch.deny, action, other) {
            return false;
        }
        if self.entries_hit(cid, &ch.allow, action, other) {
            return true;
        }
        *self.rules.actions.get(action).unwrap_or(&false)
    }
    /// バトルゾーンにある間のブレイク数の候補（509.2c）。能力が無ければ [1]
    fn break_opts(&self, cid: i64) -> Vec<i64> {
        let mut v = self.chars(cid, None).break_opts;
        v.sort();
        v.dedup();
        if v.is_empty() { vec![1] } else { v }
    }
    fn bz_tops(&self, controller: Option<i64>) -> Vec<i64> {
        self.s.zones["bz"][0]
            .iter()
            .copied()
            .filter(|&c| {
                let k = &self.s.cards[c as usize];
                k.top_of < 0 && controller.map_or(true, |p| k.controller == p) && k.link == 0
            })
            .collect()
    }
    fn refv(&self, cid: i64) -> Value {
        json!([cid, self.s.cards[cid as usize].gen])
    }
    fn alive(&self, r: &Value) -> bool {
        match r.as_array() {
            Some(a) if a.len() == 2 => {
                let cid = a[0].as_i64().unwrap_or(-1);
                cid >= 0 && (cid as usize) < self.s.cards.len() && self.s.cards[cid as usize].gen == a[1].as_i64().unwrap_or(-2)
            }
            _ => false,
        }
    }

    // ---- 進行 ----
    pub fn advance(&mut self) -> R<Option<Value>> {
        while self.s.result.is_none() {
            if let Some(w) = &self.s.waiting {
                return Ok(Some(w.clone()));
            }
            if self.s.tasks.is_empty() {
                return Err(EngErr::Illegal("task stack empty".into()));
            }
            let tt = self.s.tasks.last().unwrap()["t"].as_str().unwrap_or("").to_string();
            let cp = self.s.tasks.last().unwrap().get("cp").and_then(|v| v.as_bool()).unwrap_or(false);
            if cp && self.s.pending.iter().any(|p| p["win"] == json!(0)) {
                self.s.tasks.push(json!({"t": "resolve_pending", "win": 0, "only_st": false}));
                continue;
            }
            let d = match tt.as_str() {
                "turn" => self.h_turn()?,
                "event" => self.h_event()?,
                "play" => self.h_play()?,
                "declare" => {
                    // 使用宣言できる能力（declare）は能力を持つカードだけ。plain では候補なし
                    self.s.tasks.pop();
                    None
                }
                "attack" => self.h_attack()?,
                "break" => self.h_break()?,
                "enqueue_st" => {
                    let t = self.s.tasks.pop().unwrap();
                    let win = self.s.windows.last().copied().unwrap_or(0);
                    let player = t["player"].as_i64().unwrap();
                    for pr in t["cids"].as_array().unwrap() {
                        let c = pr[0].as_i64().unwrap();
                        if self.s.cards[c as usize].zone == "hand" {
                            if t.get("strigger").and_then(|v| v.as_bool()).unwrap_or(false) {
                                self.s.ev_seq += 1;   // 「相手がS・トリガーを使った時」の合成レコード（plain には該当する誘発が無いので通し番号だけ進む）
                            }
                            self.s.seq += 1;
                            let mut p = json!({"pid": self.s.seq, "kind": "strigger", "win": win, "controller": player,
                                "src": self.refv(c), "defn": self.s.cards[c as usize].defn.clone(), "ab": -1, "env": {}});
                            if !pr[1].is_null() {
                                p["face"] = pr[1].clone();
                            }
                            self.s.pending.push(p);
                        }
                    }
                    None
                }
                "seal_release" => {
                    let t = self.s.tasks.pop().unwrap();
                    let p = t["player"].as_i64().unwrap();
                    if self.bz_tops(Some(p)).iter().any(|&c| !self.s.cards[c as usize].seals.is_empty()) {
                        return uns("seal_release");
                    }
                    None
                }
                "capture" => {
                    // 置換効果が起こすイベントを、適用待ちの束（直近の適用中の event タスク）に加える
                    let t = self.s.tasks.pop().unwrap();
                    let host = self.s.tasks.iter_mut().rev().find(|x| x["t"] == json!("event") && x["applying"].as_bool().unwrap_or(false));
                    match host {
                        Some(h) => h["captured"].as_array_mut().unwrap().extend(t["evs"].as_array().unwrap().iter().cloned()),
                        None => return uns("capture without host"),
                    }
                    None
                }
                "open_win" => {
                    let t = self.s.tasks.pop().unwrap();
                    self.s.windows.push(t["win"].as_i64().unwrap());
                    None
                }
                "close_win" => {
                    self.s.tasks.pop();
                    let w = self.s.windows.pop().unwrap_or(0);
                    let outer = self.s.windows.last().copied().unwrap_or(0);
                    for p in self.s.pending.iter_mut() {
                        if p["win"] == json!(w) {
                            p["win"] = json!(outer);
                        }
                    }
                    None
                }
                "bind" => {
                    // 移動の後、移動先にあるカードの新しい参照を変数に入れる。Python は env の辞書を親子の効果で共有するので、
                    // 同じ env（値が等しいもの）を持つ効果すべてに書く
                    let t = self.s.tasks.pop().unwrap();
                    let zone = t["zone"].as_str().unwrap_or("").to_string();
                    let refs: Vec<Value> = t["cids"].as_array().unwrap().iter().filter_map(|v| v.as_i64())
                        .filter(|&c| self.s.cards[c as usize].zone == zone).map(|c| self.refv(c)).collect();
                    let name = t["name"].as_str().unwrap_or("").to_string();
                    let env0 = t["env"].clone();
                    for task in self.s.tasks.iter_mut() {
                        if task.get("env") == Some(&env0) {
                            if !task["env"]["vars"].is_object() {
                                task["env"]["vars"] = json!({});
                            }
                            task["env"]["vars"][name.as_str()] = json!(refs.clone());
                        }
                    }
                    None
                }
                "resolve_pending" => self.h_resolve_pending()?,
                "effect" => self.h_effect()?,
                "slayer" => {
                    let t = self.s.tasks.pop().unwrap();
                    let evs: Vec<Value> = t["pairs"].as_array().unwrap().iter()
                        .map(|p| p[1].clone()).filter(|o| self.alive(o))
                        .map(|o| json!({"ev": "move", "subject": o, "to": "graveyard", "reason": "destroy"})).collect();
                    if !evs.is_empty() {
                        let e = self.ev_task(evs);
                        self.push(vec![e]);
                    }
                    None
                }
                "battle_run" => {
                    let t = self.s.tasks.pop().unwrap();
                    if self.alive(&t["att"]) && self.alive(&t["tgt"]) {
                        self.battle(&t["att"], &t["tgt"])?;
                    }
                    None
                }
                other => return uns(format!("task {}", other)),
            };
            if let Some(d) = d {
                self.s.waiting = Some(d.clone());
                return Ok(Some(d));
            }
            self.s.steps_this_turn += 1;
            if self.s.steps_this_turn > self.step_limit {
                self.s.result = Some(json!({"winner": null, "reason": "step_limit", "turn": self.s.turn}));
            }
        }
        Ok(None)
    }

    pub fn answer(&mut self, choice: Vec<i64>) -> R<()> {
        let d = match &self.s.waiting {
            Some(d) => d.clone(),
            None => return Err(EngErr::Illegal("no decision pending".into())),
        };
        let n = d["options"].as_array().map_or(0, |a| a.len()) as i64;
        let mn = d["min"].as_i64().unwrap_or(1);
        let mx = d["max"].as_i64().unwrap_or(1);
        let mut seen = std::collections::BTreeSet::new();
        for &i in &choice {
            seen.insert(i);
        }
        if seen.len() != choice.len() || !(mn <= choice.len() as i64 && choice.len() as i64 <= mx) || choice.iter().any(|&i| i < 0 || i >= n) {
            return Err(EngErr::Illegal(format!("bad choice {:?} for {}", choice, d["kind"])));
        }
        let keys: Vec<Value> = choice.iter().map(|&i| d["options"][i as usize]["key"].clone()).collect();
        self.s.tasks.last_mut().unwrap()["answer"] = json!(choice);
        self.s.waiting = None;
        self.log.push(json!({"p": d["player"], "kind": d["kind"], "choice": choice, "keys": keys}));
        Ok(())
    }

    fn ask(&mut self, player: i64, kind: &str, options: Vec<Value>, mn: usize, mx: usize) -> Ask {
        let t = self.s.tasks.last_mut().unwrap();
        if let Some(a) = t.as_object_mut().unwrap().remove("answer") {
            return Ask::Answer(a.as_array().unwrap().iter().map(|v| v.as_u64().unwrap() as usize).collect());
        }
        if mn == mx && mx == options.len() && kind != "order_cards" {
            return Ask::Answer((0..options.len()).collect());
        }
        Ask::Decision(json!({"player": player, "kind": kind, "options": options, "min": mn, "max": mx, "prompt": ""}))
    }

    fn push(&mut self, tasks: Vec<Value>) {
        for t in tasks.into_iter().rev() {
            self.s.tasks.push(t);
        }
    }

    fn ev_task(&self, evs: Vec<Value>) -> Value {
        json!({"t": "event", "evs": evs, "i": 0, "rp": 0, "skip": [], "instead": [], "captured": [], "applying": false})
    }

    /// 効果の解決者が起こす移動に、起こしたプレイヤーと発生源（効果帰属）を記録する（Python 版 ev_task(evs, env)）
    fn ev_task_env(&self, evs: Vec<Value>, env: &Value) -> Value {
        let you = env["you"].as_i64();
        let evs: Vec<Value> = evs
            .into_iter()
            .map(|mut e| {
                if e["ev"] == json!("move") {
                    if let Some(y) = you {
                        if e.get("by").is_none() {
                            e["by"] = json!(y);
                        }
                        if let Some(sr) = env.get("self").and_then(|v| v.as_array()) {
                            let src = sr[0].as_i64().unwrap();
                            if e.get("cause_defn").is_none() {
                                let cause = self.s.cards[src as usize].defn.clone();
                                e["cause"] = json!(cause);
                                e["cause_defn"] = json!(cause);
                                let ck = if self.def(src).types.iter().any(|t| t == "spell") { "spell" } else { "ability" };
                                e["cause_kind"] = json!(ck);
                            }
                        }
                    }
                }
                e
            })
            .collect();
        if env.get("capture").and_then(|v| v.as_bool()).unwrap_or(false) {
            // 置換効果の中で起こすイベントは、元の束に加えて同時に適用する（609.9）
            let evs: Vec<Value> = evs.into_iter().map(|mut e| { e["replaced"] = json!(true); e }).collect();
            return json!({"t": "capture", "evs": evs});
        }
        if env.get("no_replace").and_then(|v| v.as_bool()).unwrap_or(false) {
            let evs: Vec<Value> = evs.into_iter().map(|mut e| { e["replaced"] = json!(true); e }).collect();
            return self.ev_task(evs);
        }
        self.ev_task(evs)
    }

    /// 数えるだけのセレクタ（Python の candidates）。選ばせない。ref 変数／ゾーン(owner you,opp・from_top 整数・filter・other)だけ。
    /// セレクタの zone 指定（名前／リスト／"any"）をゾーン名の列にする（Python の zones_of と同じ）
    fn zones_of_sel(&self, sel: &Value) -> R<Vec<String>> {
        match sel.get("zone") {
            Some(Value::String(z)) if z == "any" => Ok(self.rules.zones.iter().map(|(n, _)| n.clone()).collect()),
            Some(Value::String(z)) => Ok(vec![z.clone()]),
            Some(Value::Array(a)) => {
                let mut out = vec![];
                for z in a {
                    match z.as_str() {
                        Some(s) => out.push(s.to_string()),
                        None => return uns("zone list shape"),
                    }
                }
                Ok(out)
            }
            _ => uns("zone shape"),
        }
    }

    /// from_top の値（整数か式）を評価する
    fn from_top_n(&self, sel: &Value, env: &Value) -> R<Option<usize>> {
        match sel.get("from_top") {
            None => Ok(None),
            Some(v) => Ok(Some(self.eval_num(v, env)?.max(0) as usize)),
        }
    }

    /// 1プレイヤー分のゾーン候補: ゾーンをリスト順に連結する。from_top は複数ゾーンでは
    /// デッキの部分にだけ、単一ゾーンでは連結後に効く（Python の candidates と同じ）
    fn zone_part(&self, zones: &[String], p: i64, from_top: Option<usize>) -> Vec<i64> {
        let mut lst = vec![];
        for z in zones {
            let mut part = if z == "bz" { self.bz_tops(Some(p)) } else { self.zl(z, p).clone() };
            if let Some(n) = from_top {
                if zones.len() > 1 && z == "deck" {
                    part.truncate(n);
                }
            }
            lst.extend(part);
        }
        if let Some(n) = from_top {
            if zones.len() == 1 {
                lst.truncate(n);
            }
        }
        lst
    }

    fn candidates_ro(&self, sel: &Value, env: &Value) -> R<Vec<i64>> {
        let obj = match sel.as_object() {
            Some(o) => o,
            None => return uns("cands sel"),
        };
        for k in obj.keys() {
            if !["zone", "owner", "from_top", "filter", "ref", "other"].contains(&k.as_str()) {
                return uns(format!("cands key {}", k));
            }
        }
        let you = env["you"].as_i64().unwrap();
        let mut lst: Vec<i64>;
        if let Some(name) = sel.get("ref").and_then(|v| v.as_str()) {
            let refs: Vec<Value> = if name == "self" {
                vec![env["self"].clone()]
            } else if name == "self_moved" || name == "self_entered" || name == "crossed" || name == "subject" || name.starts_with("event.") {
                return uns("cands ref");
            } else {
                env["vars"].get(name).and_then(|v| v.as_array()).cloned().unwrap_or_default()
            };
            lst = refs.iter().filter(|r| self.alive(r)).map(|r| r[0].as_i64().unwrap()).collect();
        } else {
            // owner any: ターン・プレイヤーから順に両者（114.2a）
            let players: Vec<i64> = match sel.get("owner").and_then(|v| v.as_str()).unwrap_or("you") {
                "you" => vec![you],
                "opp" => vec![1 - you],
                "any" => vec![self.s.active, 1 - self.s.active],
                _ => return uns("cands owner"),
            };
            let zones = self.zones_of_sel(sel)?;
            for z in &zones {
                if !["hand", "deck", "graveyard", "mana", "bz", "shield"].contains(&z.as_str()) {
                    return uns(format!("cands zone {}", z));
                }
            }
            let ft = self.from_top_n(sel, env)?;
            lst = vec![];
            for p in players {
                lst.extend(self.zone_part(&zones, p, ft));
            }
            if sel.get("other").and_then(|v| v.as_bool()).unwrap_or(false) {
                if let Some(me) = env.get("self").and_then(|v| v.as_array()) {
                    let m = me[0].as_i64().unwrap();
                    lst.retain(|&c| c != m);
                }
            }
        }
        if let Some(f) = sel.get("filter") {
            let f = &self.bake_filter(f, env)?;
            let mut keep = vec![];
            for &c in &lst {
                if self.filter_ok(c, f)? {
                    keep.push(c);
                }
            }
            lst = keep;
        }
        Ok(lst)
    }

    /// フィルタの値が式（{cost_of: ...} など）なら解決時に値へ置き換える（Python の filter_match の前評価と同じ。
    /// any_of の中身にも再帰する）。name の {name_of: ...} は名前の文字列に、{race: ...} は種族1件のリストに、
    /// {declared: ...} は宣言値そのものになる。それ以外は数に評価する
    fn bake_filter(&self, f: &Value, env: &Value) -> R<Value> {
        let o = match f.as_object() { Some(o) => o, None => return Ok(f.clone()) };
        if !o.values().any(|v| v.is_object() || v.is_array()) {
            return Ok(f.clone());
        }
        let mut out = serde_json::Map::new();
        for (k, v) in o {
            let nv = if k == "any_of" && v.is_array() {
                let mut subs = vec![];
                for sub in v.as_array().unwrap() {
                    subs.push(self.bake_filter(sub, env)?);
                }
                json!(subs)
            } else if v.is_object() {
                if k == "name" {
                    if let Some(r) = v.get("name_of") {
                        let refs = self.expr_refs(r, env)?;
                        match refs.first().and_then(|r| r[0].as_i64()) {
                            Some(c) => json!(self.def(c).name),
                            None => json!("\u{0}"),   // 参照が無い時はどの名前にも一致しない
                        }
                    } else {
                        json!(self.eval_num(v, env)?)
                    }
                } else if v.get("race").is_some() && v.as_object().map_or(false, |m| m.len() == 1) {
                    json!([v["race"].as_str().unwrap_or("")])
                } else if v.get("declared").is_some() && v.as_object().map_or(false, |m| m.len() == 1) {
                    let key = v["declared"].as_str().unwrap_or("");
                    match self.s.declares.get(key) {
                        Some(dv) => dv.clone(),
                        None => return uns("declared missing"),
                    }
                } else {
                    json!(self.eval_num(v, env)?)
                }
            } else {
                v.clone()
            };
            out.insert(k.clone(), nv);
        }
        Ok(Value::Object(out))
    }

    /// 式の参照（{cost_of: X} の X など）をカード参照の列にする。X は変数名か {ref: 名前}。
    /// 変数が優先し、次に self / subject / event.* を見る（Python の _chars_refs と同じ）。crossed は未対応
    fn expr_refs(&self, v: &Value, env: &Value) -> R<Vec<Value>> {
        let name = v.get("ref").and_then(|r| r.as_str()).or(v.as_str()).unwrap_or("");
        if let Some(a) = env["vars"].get(name).and_then(|a| a.as_array()) {
            return Ok(a.clone());
        }
        if name == "self" {
            return Ok(vec![env["self"].clone()]);
        }
        if name == "subject" || name == "event.subject" {
            let s = &env["event"]["subject"];
            return Ok(if s.is_array() { vec![s.clone()] } else { vec![] });
        }
        if let Some(key) = name.strip_prefix("event.") {
            let s = &env["event"][key];
            return Ok(if s.is_array() { vec![s.clone()] } else { vec![] });
        }
        if name == "crossed" {
            return uns("expr crossed ref");
        }
        Ok(vec![])
    }

    fn eval_num(&self, x: &Value, env: &Value) -> R<i64> {
        if let Some(n) = x.as_i64() {
            return Ok(n);
        }
        if let Some(v) = x.get("cost_of") {
            // 参照カード（複数なら最大）の印刷コスト（Python の _chars_val は特性コストだが、
            // plain の範囲では印刷コストと一致する箇所でのみゲートが通す）
            let refs = self.expr_refs(v, env)?;
            return Ok(refs.iter().filter_map(|r| r[0].as_i64()).map(|c| self.def(c).cost).max().unwrap_or(0));
        }
        if let Some(v) = x.get("power_of") {
            // 参照カード（複数なら最大）の現在パワー。参照が無い時は 0（Python の max(default=0) と同じ）
            let refs = self.expr_refs(v, env)?;
            let mut best: Option<i64> = None;
            for r in &refs {
                if let Some(c) = r[0].as_i64() {
                    let p = self.chars(c, None).power;
                    best = Some(best.map_or(p, |b: i64| b.max(p)));
                }
            }
            return Ok(best.unwrap_or(0));
        }
        if let Some(l) = x.get("sum").and_then(|v| v.as_array()) {
            let mut t = 0i64;
            for e in l {
                t += self.eval_num(e, env)?;
            }
            return Ok(t);
        }
        if let Some(l) = x.get("mul").and_then(|v| v.as_array()) {
            let mut t = 1i64;
            for e in l {
                t *= self.eval_num(e, env)?;
            }
            return Ok(t);
        }
        if let Some(k) = x.get("declared").and_then(|v| v.as_str()) {
            // 未宣言は 0（Python の declares.get(name, 0) と同じ）
            return Ok(self.s.declares.get(k).and_then(|v| v.as_i64()).unwrap_or(0));
        }
        if let Some(l) = x.get("civ_count").and_then(|v| v.as_array()) {
            // 自分のバトルゾーンのクリーチャーが持つ、指定された文明の種類数（Python の eval_expr と同じ）
            let you = env["you"].as_i64().unwrap_or(0);
            let want: Vec<&str> = l.iter().filter_map(|v| v.as_str()).collect();
            let mut seen: Vec<&str> = vec![];
            for c in self.bz_tops(Some(you)) {
                let d = self.def(c);
                if d.types.iter().any(|t| t == "creature") {
                    for civ in &d.civs {
                        if want.contains(&civ.as_str()) && !seen.contains(&civ.as_str()) {
                            seen.push(civ.as_str());
                        }
                    }
                }
            }
            return Ok(seen.len() as i64);
        }
        if x.is_object() && x.as_object().unwrap().len() == 1 {
            if let Some(sel) = x.get("count") {
                return Ok(self.candidates_ro(sel, env)?.len() as i64);
            }
        }
        uns("expr")
    }

    fn eval_cond(&self, c: &Value, env: &Value) -> R<bool> {
        let o = match c.as_object() {
            Some(o) if o.len() == 1 => o,
            _ => return uns("cond shape"),
        };
        let (k, v) = o.iter().next().unwrap();
        match k.as_str() {
            "exists" => Ok(!self.candidates_ro(v, env)?.is_empty()),
            "cmp" => {
                let a = v.as_array().filter(|a| a.len() == 3);
                let a = match a {
                    Some(a) => a,
                    None => return uns("cmp shape"),
                };
                let (x, y) = (self.eval_num(&a[0], env)?, self.eval_num(&a[2], env)?);
                Ok(match a[1].as_str().unwrap_or("") {
                    "<" => x < y,
                    "<=" => x <= y,
                    "==" => x == y,
                    ">=" => x >= y,
                    ">" => x > y,
                    _ => return uns("cmp op"),
                })
            }
            "not" => Ok(!self.eval_cond(v, env)?),
            "all" | "any" => {
                let l = match v.as_array() {
                    Some(l) => l,
                    None => return uns("cond list"),
                };
                let mut rs = vec![];
                for x in l {
                    rs.push(self.eval_cond(x, env)?);
                }
                Ok(if k == "all" { rs.iter().all(|&b| b) } else { rs.iter().any(|&b| b) })
            }
            "is_turn" => {
                let you = env["you"].as_i64().unwrap();
                let p = match v.as_str() {
                    Some("you") => you,
                    Some("opp") => 1 - you,
                    _ => return uns("is_turn"),
                };
                Ok(self.s.active == p)
            }
            _ => uns(format!("cond {}", k)),
        }
    }

    /// セレクタの解決（Python 版 select の、ゾーン指定・枚数・選ぶ人・types 絞り込みだけの版）。
    /// Ok(Ok(cids)) か Ok(Err(decision))。
    fn select(&mut self, sel: &Value, env: &Value) -> R<Result<Vec<i64>, Value>> {
        if let Some(c) = self.s.tasks.last().unwrap()["os"].get("chosen") {
            return Ok(Ok(c.as_array().unwrap().iter().map(|v| v.as_i64().unwrap()).collect()));
        }
        let obj = sel.as_object().unwrap();
        let you = env["you"].as_i64().unwrap();
        if obj.len() == 1 && sel.get("ref") == Some(&json!("self")) {
            let me = env["self"].clone();
            return Ok(Ok(if self.alive(&me) { vec![me[0].as_i64().unwrap()] } else { vec![] }));
        }
        for k in obj.keys() {
            if !["zone", "owner", "count", "from_top", "filter", "chooser", "look", "ref", "up_to", "other", "under_of",
                 "exlife_of", "owner_of", "exclude", "extremal", "distinct_from",
                 "total_cost_le", "total_cost_ge", "total_power_le", "total_power_ge", "distinct_costs"].contains(&k.as_str()) {
                return uns(format!("selector key {}", k));
            }
        }
        let look = sel.get("look").and_then(|v| v.as_bool()).unwrap_or(false);
        let filter: Option<Value> = match sel.get("filter") {
            Some(f) => Some(self.bake_filter(f, env)?),
            None => None,
        };
        let up_to = sel.get("up_to").and_then(|v| v.as_bool()).unwrap_or(false);
        let mut lst: Vec<i64>;
        let mut zone_path = false;   // exclude / extremal が効くのはゾーン経路だけ（Python の candidates と同じ）
        let mut skip_filter = false; // self_moved / self_entered / exlife_of は candidates が即返しで filter が効かない
        if let Some(u) = sel.get("under_of") {
            // 「このクリーチャーの下にあるカード」（メテオバーン等）。基底は self か束変数（Python の _under_base と同じ）
            let base: Option<i64> = if u.as_str() == Some("self") {
                env["self"].as_array().and_then(|a| a[0].as_i64())
            } else if let Some(name) = u.as_str() {
                env["vars"].get(name).and_then(|v| v.as_array()).and_then(|a| a.first()).and_then(|r| r[0].as_i64())
            } else {
                return uns("under_of shape");
            };
            lst = match base {
                Some(b) if b >= 0 && (b as usize) < self.s.cards.len() => self.s.cards[b as usize].under.clone(),
                _ => vec![],
            };
        } else if let Some(name) = sel.get("ref").and_then(|v| v.as_str()) {
            // 参照経路: self / subject / event.* / self_moved / self_entered / crossed / 変数。
            // filter と zone（現在ゾーンでの絞り込み）が併記できる
            if name == "self_moved" || name == "self_entered" {
                skip_filter = true;
                let me = env["self"].clone();
                let cid = me[0].as_i64().unwrap_or(-1);
                let self_gen = me[1].as_i64().unwrap_or(-1);
                lst = match self.s.cards.get(cid as usize) {
                    Some(c) if c.gen == self_gen + 1 && (if name == "self_moved" { c.zone != "bz" } else { c.zone == "bz" }) => vec![cid],
                    _ => vec![],
                };
            } else {
                let refs: Vec<Value> = match name {
                    "self" => vec![env["self"].clone()],
                    "subject" => {
                        let s = &env["event"]["subject"];
                        if s.is_array() { vec![s.clone()] } else { vec![] }
                    }
                    _ if name.starts_with("event.") => {
                        let s = &env["event"][&name[6..]];
                        if s.is_array() { vec![s.clone()] } else { vec![] }
                    }
                    "crossed" => {
                        let me = env["self"].clone();
                        match self.s.cards.get(me[0].as_i64().unwrap_or(-1) as usize).and_then(|c| c.crossed.clone()) {
                            Some(g) => vec![g],
                            None => vec![],
                        }
                    }
                    _ => env["vars"].get(name).and_then(|v| v.as_array()).cloned().unwrap_or_default(),
                };
                lst = refs.iter().filter(|r| self.alive(r)).map(|r| r[0].as_i64().unwrap()).collect();
                if sel.get("zone").is_some() {
                    let zones = self.zones_of_sel(sel)?;
                    lst.retain(|&c| zones.iter().any(|z| z == &self.s.cards[c as usize].zone));
                }
            }
        } else if let Some(x) = sel.get("exlife_of") {
            // EXライフの紐付きシールド: 参照に紐付いたままシールドにあるカードを両プレイヤー分（プレイヤー順）
            skip_filter = true;
            let refs = self.expr_refs(x, env)?;
            lst = vec![];
            for p in [0i64, 1] {
                for &c in &self.zl("shield", p).clone() {
                    if let Some(eo) = &self.s.cards[c as usize].exlife_of {
                        if refs.iter().any(|r| r == eo) {
                            lst.push(c);
                        }
                    }
                }
            }
        } else {
            zone_path = true;
            let players: Vec<i64> = if let Some(vname) = sel.get("owner_of").and_then(|v| v.as_str()) {
                // そのカードの持ち主たち（ターンプレイヤーから順。Python の candidates と同じ）
                let refs = env["vars"].get(vname).and_then(|v| v.as_array()).cloned().unwrap_or_default();
                let mut owners: Vec<i64> = vec![];
                for r in &refs {
                    if let Some(c) = r[0].as_i64() {
                        let o = self.s.cards[c as usize].owner;
                        if !owners.contains(&o) {
                            owners.push(o);
                        }
                    }
                }
                let a = self.s.active;
                owners.sort_by_key(|&o| o != a);
                owners
            } else {
                // owner any: ターン・プレイヤーから順に両者（114.2a）
                match sel.get("owner").and_then(|v| v.as_str()).unwrap_or("you") {
                    "you" => vec![you],
                    "opp" => vec![1 - you],
                    "any" => vec![self.s.active, 1 - self.s.active],
                    _ => return uns("selector owner"),
                }
            };
            let zones = self.zones_of_sel(sel)?;
            for z in &zones {
                if !["hand", "deck", "graveyard", "mana", "bz", "shield"].contains(&z.as_str()) {
                    return uns(format!("selector zone {}", z));
                }
            }
            let ft = self.from_top_n(sel, env)?;
            lst = vec![];
            for p in players {
                lst.extend(self.zone_part(&zones, p, ft));
            }
            if sel.get("other").and_then(|v| v.as_bool()).unwrap_or(false) {
                if let Some(me) = env.get("self").and_then(|v| v.as_array()) {
                    let m = me[0].as_i64().unwrap();
                    lst.retain(|&c| c != m);
                }
            }
        }
        if let Some(f) = &filter {
            if !skip_filter {
                let mut keep = vec![];
                for &c in &lst {
                    if self.filter_ok(c, f)? {
                        keep.push(c);
                    }
                }
                lst = keep;
            }
        }
        if zone_path {
            if let Some(ex) = sel.get("exclude") {
                // ゾーン経路の候補から除外セレクタの候補を引く（Python の candidates と同じ）
                let subs: Vec<&Value> = match ex {
                    Value::Array(a) => a.iter().collect(),
                    other => vec![other],
                };
                let mut banned: Vec<i64> = vec![];
                for sub in subs {
                    for c in self.candidates_ro(sub, env)? {
                        if !banned.contains(&c) {
                            banned.push(c);
                        }
                    }
                }
                lst.retain(|c| !banned.contains(c));
            }
            if let Some(ex) = sel.get("extremal").and_then(|v| v.as_str()) {
                // 現在パワーの最小／最大に同点全残し（Python の candidates と同じ）
                if !lst.is_empty() {
                    let mut best: Option<i64> = None;
                    for &c in &lst {
                        let p = self.chars(c, None).power;
                        best = Some(match best {
                            None => p,
                            Some(b) => if ex == "min_power" { b.min(p) } else { b.max(p) },
                        });
                    }
                    let b = best.unwrap();
                    lst.retain(|&c| self.chars(c, None).power == b);
                }
            }
        }
        let cnt = sel.get("count");
        // count: any = 「好きな枚数」（0枚から候補の全部まで）。count: all + up_to と同じ
        let any_n = cnt == Some(&json!("any")) || (cnt == Some(&json!("all")) && up_to);
        let up_to = up_to || any_n;
        if ((sel.get("from_top").is_some() || sel.get("ref").is_some() || sel.get("under_of").is_some()) && cnt.is_none()) || (cnt == Some(&json!("all")) && !any_n) {
            return Ok(Ok(lst));
        }
        let n = match cnt {
            _ if any_n => lst.len(),
            None => 1usize,
            Some(v) => match v.as_i64() {
                Some(n) => n.max(0) as usize,
                None => return uns("count expr"),
            },
        };
        if n.min(lst.len()) == 0 {
            return Ok(Ok(vec![]));
        }
        let random = sel.get("chooser") == Some(&json!("random"));   // 「見ないで選ぶ」: 効果の使用者が無作為に選ぶ
        let chooser = match sel.get("chooser").and_then(|v| v.as_str()).unwrap_or("you") {
            "you" | "random" => you,
            "opp" | "opponent" => 1 - you,   // opponent は opp の同義語
            _ => return uns("chooser"),
        };
        let mut cands: Vec<i64> = lst
            .into_iter()
            .filter(|&c| {
                let k = &self.s.cards[c as usize];
                k.zone != "bz" || k.controller == chooser || self.permits(c, "be_chosen")
            })
            .collect();
        if let Some(df) = sel.get("distinct_from") {
            // 「自分のどのクリーチャーともコストが異なる」: 参照集合のコストと重なる候補を外す。
            // 評価は選択開始時に1回だけ（Python の select と同じ位置）
            let refs = self.candidates_ro(df, env)?;
            let mut costs: Vec<i64> = vec![];
            for c in refs {
                let p = self.chars(c, None).pay_cost;
                if !costs.contains(&p) {
                    costs.push(p);
                }
            }
            cands.retain(|&c| !costs.contains(&self.chars(c, None).pay_cost));
        }
        let n = n.min(cands.len());
        if n == 0 {
            return Ok(Ok(vec![]));
        }
        if random {
            let mut pool = cands.clone();
            let mut picked = vec![];
            for _ in 0..n.min(pool.len()) {
                let j = self.s.rng_below(pool.len() as u64) as usize;
                picked.push(pool.remove(j));
            }
            self.s.tasks.last_mut().unwrap()["os"]["chosen"] = json!(picked);
            return Ok(Ok(picked));
        }
        if sel.get("total_cost_le").is_some() || sel.get("total_cost_ge").is_some()
            || sel.get("total_power_le").is_some() || sel.get("total_power_ge").is_some()
            || sel.get("distinct_costs").and_then(|v| v.as_bool()).unwrap_or(false) {
            // 合計制限つきの「好きな数」選択（1枚ずつ積み上げる。Python の select の同分岐と同じ）
            return self.select_total(sel, env, &cands, n, any_n, cnt.is_some(), up_to, chooser, look);
        }
        let opts: Vec<Value> = cands.iter().map(|&c| if look { self.card_option_look(c) } else { self.card_option(c, None) }).collect();
        let mn = if up_to { 0 } else { n };
        let mut a = match self.ask(chooser, "choose_cards", opts.clone(), mn, n) {
            Ask::Decision(d) => return Ok(Err(d)),
            Ask::Answer(a) => a,
        };
        if a.iter().any(|&i| i >= cands.len()) {
            // 公平探索で隠れた中身が決定の時と答えの時で違うと候補の数が変わる。Python と同じく範囲外の答えは捨て、足りなければ聞き直す
            a.retain(|&i| i < cands.len());
            if a.len() < mn {
                a = match self.ask(chooser, "choose_cards", opts, mn, n) {
                    Ask::Decision(d) => return Ok(Err(d)),
                    Ask::Answer(a) => a,
                };
            }
        }
        let chosen: Vec<i64> = a.iter().map(|&i| cands[i]).collect();
        self.s.tasks.last_mut().unwrap()["os"]["chosen"] = json!(chosen);
        for &c in &chosen {
            let k = &self.s.cards[c as usize];
            if k.zone == "bz" && k.controller != chooser {
                self.s.ev_seq += 1;   // 「相手がこのクリーチャーを選んだ時」の収集（plain には該当する誘発が無いので通し番号だけ進む）
            }
        }
        Ok(Ok(chosen))
    }

    /// 合計制限の軸の値（コストは特性の支払いコスト、パワーは現在パワー。Python の chars_ro と同じ）
    fn total_val(&self, key: &str, c: i64) -> i64 {
        if key == "cost" { self.chars(c, None).pay_cost } else { self.chars(c, None).power }
    }

    fn totals_of(&self, limits: &[(&str, Option<i64>, Option<i64>)], picked: &[i64]) -> Vec<i64> {
        limits.iter().map(|(k, _, _)| picked.iter().map(|&c| self.total_val(k, c)).sum()).collect()
    }

    /// 合計制限に収まるか（上限のみを見る。下限は can_stop 側。distinct_costs はコストの重なりを禁じる）
    fn total_fits(&self, limits: &[(&str, Option<i64>, Option<i64>)], distinct: bool, picked: &[i64], c: i64, totals: &[i64]) -> bool {
        if distinct {
            let cc = self.total_val("cost", c);
            if picked.iter().any(|&x| self.total_val("cost", x) == cc) {
                return false;
            }
        }
        limits.iter().zip(totals.iter()).all(|((k, le, _), t)| le.map_or(true, |le| t + self.total_val(k, c) <= le))
    }

    /// 合計制限つき選択（total_cost_le/ge・total_power_le/ge・distinct_costs）: 1枚ずつ積み上げる。
    /// 済んだ段の答えは os の tc_answers から再生する（Python の select の同分岐と同じ）
    fn select_total(&mut self, sel: &Value, env: &Value, cands: &[i64], n: usize, any_n: bool,
                    cnt_present: bool, up_to: bool, chooser: i64, look: bool) -> R<Result<Vec<i64>, Value>> {
        let mut limits: Vec<(&str, Option<i64>, Option<i64>)> = vec![];
        if sel.get("total_cost_le").is_some() || sel.get("total_cost_ge").is_some() {
            limits.push(("cost",
                         match sel.get("total_cost_le") { Some(v) => Some(self.eval_num(v, env)?), None => None },
                         match sel.get("total_cost_ge") { Some(v) => Some(self.eval_num(v, env)?), None => None }));
        }
        if sel.get("total_power_le").is_some() || sel.get("total_power_ge").is_some() {
            limits.push(("power",
                         match sel.get("total_power_le") { Some(v) => Some(self.eval_num(v, env)?), None => None },
                         match sel.get("total_power_ge") { Some(v) => Some(self.eval_num(v, env)?), None => None }));
        }
        let distinct = sel.get("distinct_costs").and_then(|v| v.as_bool()).unwrap_or(false);
        // 「N体まで」と併記された場合の枚数上限。count が無い「好きな数」は上限なし
        let cap: Option<usize> = if cnt_present && !any_n && sel.get("count") != Some(&json!("all")) { Some(n) } else { None };
        // 型3（全コスト網羅）: distinct_costs かつ count が固定なら、必要数に達するまで止められない
        let need: Option<usize> = if distinct && !any_n && !up_to && cnt_present { Some(n) } else { None };
        let mut picked: Vec<i64> = vec![];
        let answers: Vec<Value> = self.s.tasks.last().unwrap()["os"].get("tc_answers")
            .and_then(|v| v.as_array()).cloned().unwrap_or_default();
        let mut replayed = true;   // Python の for-else: break しなければ while へ進む
        for ans in &answers {
            if cap.map_or(false, |cp| picked.len() >= cp) {
                replayed = false;
                break;
            }
            let totals = self.totals_of(&limits, &picked);
            let rest: Vec<i64> = cands.iter().copied().filter(|c| !picked.contains(c))
                .filter(|&c| self.total_fits(&limits, distinct, &picked, c, &totals)).collect();
            let a = match ans.as_array() {
                Some(a) => a,
                None => {
                    replayed = false;
                    break;
                }
            };
            if a.is_empty() {
                replayed = false;
                break;
            }
            let idx = a[0].as_i64().unwrap_or(-1);
            if idx < 0 || idx as usize >= rest.len() {
                return uns("tc answer out of range");   // Python はここで IndexError（壊れた再生）になる箇所
            }
            picked.push(rest[idx as usize]);
        }
        if replayed {
            loop {
                if cap.map_or(false, |cp| picked.len() >= cp) {
                    break;
                }
                let totals = self.totals_of(&limits, &picked);
                let rest: Vec<i64> = cands.iter().copied().filter(|c| !picked.contains(c))
                    .filter(|&c| self.total_fits(&limits, distinct, &picked, c, &totals)).collect();
                let mut can_stop = limits.iter().zip(totals.iter())
                    .all(|((_, _, ge), t)| ge.map_or(true, |ge| *t >= ge));
                if !can_stop && limits.iter().zip(totals.iter()).any(|((k, _, ge), t)| {
                    ge.map_or(false, |ge| *t < ge && *t + rest.iter().map(|&c| self.total_val(k, c)).sum::<i64>() < ge)
                }) {
                    can_stop = true;   // どう選んでも下限に届かない時は打ち切る
                }
                if let Some(nd) = need {
                    if picked.len() < nd {
                        // 全コスト網羅: 残りのコストの種類数で届くかどうかを見る（ge の同型）
                        let mut dcosts: Vec<i64> = vec![];
                        for &c in &rest {
                            let v = self.total_val("cost", c);
                            if !dcosts.contains(&v) {
                                dcosts.push(v);
                            }
                        }
                        can_stop = picked.len() + dcosts.len() < nd;
                    }
                }
                if rest.is_empty() {
                    break;
                }
                let opts: Vec<Value> = rest.iter().map(|&c| if look { self.card_option_look(c) } else { self.card_option(c, None) }).collect();
                let a = match self.ask(chooser, "choose_cards", opts, if can_stop { 0 } else { 1 }, 1) {
                    Ask::Decision(d) => return Ok(Err(d)),
                    Ask::Answer(a) => a,
                };
                {
                    let t = self.s.tasks.last_mut().unwrap();
                    if !t["os"]["tc_answers"].is_array() {
                        t["os"]["tc_answers"] = json!([]);
                    }
                    t["os"]["tc_answers"].as_array_mut().unwrap().push(json!(a));
                }
                if a.is_empty() {
                    break;
                }
                if a[0] >= rest.len() {
                    // 隠れた札の中身が変わって候補が減った。今の候補で聞き直す
                    self.s.tasks.last_mut().unwrap()["os"]["tc_answers"].as_array_mut().unwrap().pop();
                    continue;
                }
                picked.push(rest[a[0]]);
            }
        }
        let chosen = picked;
        self.s.tasks.last_mut().unwrap()["os"]["chosen"] = json!(chosen);
        for &c in &chosen {
            let k = &self.s.cards[c as usize];
            if k.zone == "bz" && k.controller != chooser {
                self.s.ev_seq += 1;   // 「相手がこのクリーチャーを選んだ時」の収集（通常の選択と同じ）
            }
        }
        Ok(Ok(chosen))
    }

    /// フィルタの照合（Python 版 filter_match の、plain の札で値が定義どおりになるキーだけ。他は Unsupported）
    /// フィルタが見るパワー: 特性（継続的効果・条件つき修整込み）。常在型の条件の入れ子（2段目以降）では印刷のパワー
    fn filter_power(&self, cid: i64) -> i64 {
        if self.static_depth.get() > 1 || self.chars_busy.contains(cid) { self.def(cid).power } else { self.power(cid) }
    }

    fn filter_ok(&self, cid: i64, f: &Value) -> R<bool> {
        let d = self.def(cid);
        let c = &self.s.cards[cid as usize];
        let sl = |v: &Value| -> Vec<String> {
            match v {
                Value::String(x) => vec![x.clone()],
                Value::Array(a) => a.iter().filter_map(|x| x.as_str().map(|y| y.to_string())).collect(),
                _ => vec![],
            }
        };
        for (k, v) in f.as_object().unwrap() {
            let ok = match k.as_str() {
                "types" => sl(v).iter().any(|t| d.types.contains(t)),
                "not_types" => !sl(v).iter().any(|t| d.types.contains(t)),
                "civs" => sl(v).iter().any(|t| d.civs.contains(t)),
                "not_civs" => !sl(v).iter().any(|t| d.civs.contains(t)),
                "races" => sl(v).iter().any(|t| d.races.contains(t)),
                "race_has" => d.races.iter().any(|r| r.contains(v.as_str().unwrap_or("\u{0}"))),
                "not_race_has" => !d.races.iter().any(|r| sl(v).iter().any(|p| r.contains(p))),
                "name" => d.name == v.as_str().unwrap_or("\u{0}"),
                "not_name" => d.name != v.as_str().unwrap_or("\u{0}"),
                "name_has" => d.name.contains(v.as_str().unwrap_or("\u{0}")),
                "entered_this_turn" => (c.entered_turn == self.s.turn) == v.as_bool().unwrap_or(false),
                "face_up" => c.face_up == v.as_bool().unwrap_or(false),
                "face_down" => c.face_down == v.as_bool().unwrap_or(false),
                "twinpact" => !self.rules.cards[&c.defn].faces.is_empty() == v.as_bool().unwrap_or(false),
                "keyword" => {
                    // Python の filter_match: 静的な文脈（base）では印刷のキーワード、それ以外は実際の特性のキーワード
                    if self.static_depth.get() > 1 || self.chars_busy.contains(cid) {
                        d.keywords.iter().any(|x| Some(x.as_str()) == v.as_str())
                    } else {
                        self.chars(cid, None).keywords.iter().any(|x| Some(x.as_str()) == v.as_str())
                    }
                }
                "cost_le" => d.cost <= v.as_i64().ok_or(EngErr::Unsupported("filter expr".into()))?,
                "cost_ge" => d.cost >= v.as_i64().ok_or(EngErr::Unsupported("filter expr".into()))?,
                "power_le" => self.filter_power(cid) <= v.as_i64().ok_or(EngErr::Unsupported("filter expr".into()))?,
                "power_ge" => self.filter_power(cid) >= v.as_i64().ok_or(EngErr::Unsupported("filter expr".into()))?,
                "tapped" => c.tapped == v.as_bool().unwrap_or(false),
                "multicolor" => (d.civs.len() > 1) == v.as_bool().unwrap_or(false),
                "evolution" => self.def(cid).types.iter().any(|t| t == "evolution") == v.as_bool().unwrap_or(false),
                "colorless" => d.civs.is_empty() == v.as_bool().unwrap_or(false),
                "any_of" => {
                    let mut hit = false;
                    for sub in v.as_array().unwrap() {
                        if self.filter_ok(cid, sub)? {
                            hit = true;
                            break;
                        }
                    }
                    hit
                }
                other => return uns(format!("filter key {}", other)),
            };
            if !ok {
                return Ok(false);
            }
        }
        Ok(true)
    }

    fn build_steps(&self, _p: i64) -> R<Vec<Value>> {
        if !self.s.step_mods.is_empty() {
            return uns("step_mods");
        }
        Ok(self.rules.steps.iter().map(|x| json!(x)).collect())
    }

    // ---- ターン ----
    fn h_turn(&mut self) -> R<Option<Value>> {
        if self.s.skip_rest {
            // 残りのステップを行わずに次のターンへ（ターン終了時の誘発もなし）。状況起因処理と待機はこのターンのうちに
            self.s.skip_rest = false;
            let n = self.s.tasks.last().unwrap()["steps"].as_array().unwrap().len();
            self.tset("i", json!(n));
            self.expire("end_of_turn")?;
            return Ok(None);
        }
        let (i, n) = {
            let t = self.s.tasks.last().unwrap();
            (t["i"].as_i64().unwrap(), t["steps"].as_array().unwrap().len() as i64)
        };
        if i < n {
            let name = self.s.tasks.last().unwrap()["steps"][i as usize].as_str().unwrap().to_string();
            self.s.step = name.clone();
            return match name.as_str() {
                "start" => self.st_start(),
                "draw" => self.st_draw(),
                "charge" => self.st_charge(),
                "main" => self.st_main(),
                "attack" => self.st_attack(),
                "end" => self.st_end(),
                other => uns(format!("step {}", other)),
            };
        }
        // 512 次のターンへ
        if !self.s.hold.is_empty() {
            return uns("hold");
        }
        self.s.active = if !self.s.extra_turns.is_empty() { self.s.extra_turns.remove(0) } else { 1 - self.s.active };
        self.s.turn += 1;
        if self.s.turn > self.turn_limit {
            self.s.result = Some(json!({"winner": null, "reason": "turn_limit", "turn": self.s.turn}));
        }
        let steps = self.build_steps(self.s.active)?;
        let t = self.s.tasks.last_mut().unwrap();
        t["steps"] = json!(steps);
        t["i"] = json!(0);
        t["sub"] = json!(0);
        Ok(None)
    }

    fn step_done(&mut self) {
        let t = self.s.tasks.last_mut().unwrap();
        t["i"] = json!(t["i"].as_i64().unwrap() + 1);
        t["sub"] = json!(0);
    }

    fn st_start(&mut self) -> R<Option<Value>> {
        let a = self.s.active;
        for c in self.zl("bz", a).clone() {
            if self.s.cards[c as usize].controller == a {
                self.s.cards[c as usize].hyper = false;
            }
        }
        self.s.steps_this_turn = 0;
        self.s.prev_counters = self.s.turn_counters.clone();
        self.s.turn_counters = Map::new();
        // 継続的効果・遅延効果の期限切れ（「次の自分のターンのはじめまで」）
        if !self.s.delayed.is_empty() {
            return uns("delayed");
        }
        {
            let key = format!("until_turn_start:{}", a);
            if self.s.continuous.iter().any(|c| c["duration"] == json!(key)) {
                return uns("expire until_turn_start");
            }
        }
        // サイレントスキルは能力を持つカードだけ。plain では候補なし
        let mut zs = self.bz_tops(Some(a));
        zs.extend(self.zl("mana", a).iter().copied());
        let frozen: Vec<i64> = zs.iter().copied().filter(|&c| self.s.cards[c as usize].no_untap_next).collect();
        for &c in &frozen {
            self.s.cards[c as usize].no_untap_next = false;
        }
        let untap: Vec<Value> = zs
            .iter()
            .copied()
            .filter(|&c| self.s.cards[c as usize].tapped && self.permits(c, "untap_at_start") && !frozen.contains(&c))
            .map(|c| json!({"ev": "untap", "subject": self.refv(c)}))
            .collect();
        self.step_done();
        let mut ts = vec![];
        if !untap.is_empty() {
            ts.push(self.ev_task(untap));
        }
        ts.push(self.ev_task(vec![json!({"ev": "turn_start", "player": a})]));
        self.push(ts);
        Ok(None)
    }

    fn st_draw(&mut self) -> R<Option<Value>> {
        self.step_done();
        if !(self.s.turn == 1 && self.s.active == self.s.first_player) {
            let t = self.ev_task(vec![json!({"ev": "draw", "player": self.s.active})]);
            self.push(vec![t]);
        }
        Ok(None)
    }

    fn distinct_hand_options(&self, p: i64, verb: &str) -> Vec<Value> {
        let mut seen = std::collections::BTreeSet::new();
        let mut out = vec![];
        for &cid in self.zl("hand", p) {
            let dfn = self.s.cards[cid as usize].defn.clone();
            if seen.insert(dfn.clone()) {
                out.push(json!({"key": format!("{}:{}", verb, dfn), "cid": cid, "name": self.rules.cards[&dfn].name}));
            }
        }
        out
    }

    fn st_charge(&mut self) -> R<Option<Value>> {
        let a = self.s.active;
        let mut opts = self.distinct_hand_options(a, "charge");
        opts.push(json!({"key": "pass"}));
        let ans = match self.ask(a, "charge", opts.clone(), 1, 1) {
            Ask::Decision(d) => return Ok(Some(d)),
            Ask::Answer(a) => a,
        };
        self.step_done();
        let o = &opts[ans[0]];
        if o["key"] != json!("pass") {
            let cid = o["cid"].as_i64().unwrap();
            let t = self.ev_task(vec![json!({"ev": "move", "subject": self.refv(cid), "to": "mana", "reason": "charge"})]);
            self.push(vec![t]);
        }
        Ok(None)
    }

    fn st_main(&mut self) -> R<Option<Value>> {
        let a = self.s.active;
        let mut opts = self.play_options(a);
        // 十字ギア・ハイパー・ビビッドローの選択肢は plain では出ない
        opts.push(json!({"key": "pass"}));
        let ans = match self.ask(a, "main", opts.clone(), 1, 1) {
            Ask::Decision(d) => return Ok(Some(d)),
            Ask::Answer(x) => x,
        };
        if opts[ans[0]]["key"] == json!("pass") {
            self.step_done();
            return Ok(None);
        }
        let o = &opts[ans[0]];
        let cid = o["cid"].as_i64().unwrap();
        let gen = self.s.cards[cid as usize].gen;
        let a = self.s.active;
        let mut t = json!({"t": "play", "cid": cid, "player": a, "free": false, "phase": "start", "gen": gen});
        if let Some(f) = o.get("face") {
            t["face"] = f.clone();
        }
        self.push(vec![t]);
        Ok(None)
    }

    /// カードの実行（601）。段階2-a: 通常のクリーチャー召喚（コスト軽減・進化・代替コストなどは無い札だけ）
    fn h_play(&mut self) -> R<Option<Value>> {
        let (cid, p, gen, face) = {
            let t = self.s.tasks.last().unwrap();
            (t["cid"].as_i64().unwrap(), t["player"].as_i64().unwrap(), t["gen"].as_i64().unwrap(), t.get("face").and_then(|v| v.as_i64()))
        };
        let (g, z) = {
            let c = &self.s.cards[cid as usize];
            (c.gen, c.zone.clone())
        };
        if g != gen || z == "bz" || z == "hold" {
            self.s.tasks.pop();
            return Ok(None);
        }
        let is_spell = !self.fdef(cid, face).types.iter().any(|t| t == "creature");
        let denied = if is_spell { !self.permits(cid, "cast") } else { !self.permits(cid, "summon") || !self.permits(cid, "enter_bz") };
        if denied {
            self.s.tasks.pop();
            return Ok(None);
        }
        let has = |t: &Value, k: &str| t.get(k).is_some();
        let (free, st) = {
            let t = self.s.tasks.last().unwrap();
            (t["free"].as_bool().unwrap_or(false), t.get("st").and_then(|v| v.as_bool()).unwrap_or(false))
        };
        let kws = self.fdef(cid, face).keywords.clone();
        let sst_bonus = st && kws.iter().any(|k| k == "super_s_trigger") && self.zl("shield", p).is_empty();
        let broken = self.s.turn_counters.get(&format!("broken:{}", p)).and_then(|v| v.as_i64()).unwrap_or(0);
        let stp_bonus = st && kws.iter().any(|k| k == "s_trigger_plus") && self.s.active != p && broken >= 2;
        // ササゲール（破壊してコスト軽減）: 候補なし → 空の sac と sac_done を残す（コストを払わない実行では聞かない）
        if self.is_evo(cid, face) && !has(self.s.tasks.last().unwrap(), "evo") {
            // 通常の進化: 進化元を選ぶ（超無限墓地進化は墓地から好きな数）
            let srcs = self.evo_sources(cid, p, face);
            let (cnt, any) = { let d = self.fdef(cid, face); (d.evolve_count, d.evolve_any) };
            if (srcs.len() as i64) < cnt {
                self.s.tasks.pop();
                return Ok(None);
            }
            let opts: Vec<Value> = srcs.iter().map(|&c| self.card_option(c, None)).collect();
            let (mn, mx) = if any { (1, srcs.len()) } else { (cnt as usize, cnt as usize) };
            let ans = match self.ask(p, "choose_evo_source", opts, mn, mx) {
                Ask::Decision(d) => return Ok(Some(d)),
                Ask::Answer(x) => x,
            };
            let evo: Vec<Value> = ans.iter().map(|&i| self.refv(srcs[i])).collect();
            self.s.tasks.last_mut().unwrap()["evo"] = json!(evo);
        }
        if !free && !has(self.s.tasks.last().unwrap(), "sac_done") {
            let t = self.s.tasks.last_mut().unwrap();
            if !has(t, "sac") {
                t["sac"] = json!([]);
            }
            t["sac_done"] = json!(true);
        }
        self.s.turn_counters.insert(format!("last_play_creature:{}", p), json!(if is_spell { 0 } else { 1 }));
        if !free && !has(self.s.tasks.last().unwrap(), "cost_may_done") {
            self.s.tasks.last_mut().unwrap()["cost_may_done"] = json!(true);
        }
        if !free && !has(self.s.tasks.last().unwrap(), "paid_done") {
            let n_evo = self.s.tasks.last().unwrap().get("evo").and_then(|v| v.as_array()).map_or(0, |a| a.len()) as i64;
            let ecost = self.evo_cost(cid, face, n_evo);
            let choices = self.mana_choices_f(cid, p, face, ecost, 32);
            if choices.is_empty() {
                self.s.tasks.pop();
                return Ok(None);
            }
            let opts: Vec<Value> = choices
                .iter()
                .map(|ch| {
                    let mut names: Vec<String> = ch.iter().map(|&c| self.s.cards[c as usize].defn.clone()).collect();
                    names.sort();
                    json!({"key": format!("mana:{}", names.join(",")), "cids": ch})
                })
                .collect();
            let ans = match self.ask(p, "pay_mana", opts.clone(), 1, 1) {
                Ask::Decision(d) => return Ok(Some(d)),
                Ask::Answer(x) => x,
            };
            for c in opts[ans[0]]["cids"].as_array().unwrap() {
                self.s.cards[c.as_i64().unwrap() as usize].tapped = true;
            }
            self.s.tasks.last_mut().unwrap()["summon_paid"] = opts[ans[0]]["cids"].clone();
            self.s.tasks.last_mut().unwrap()["paid_done"] = json!(true);
        }
        let paid: Vec<i64> = self.s.tasks.last().unwrap().get("summon_paid")
            .and_then(|v| v.as_array()).map(|a| a.iter().filter_map(|x| x.as_i64()).collect()).unwrap_or_default();
        let evo: Vec<Value> = self.s.tasks.last().unwrap().get("evo").and_then(|v| v.as_array()).cloned().unwrap_or_default();
        self.s.tasks.pop();
        // フォートE（Python 第168弾と同じ）: 召喚時にタップしたマナを種族のスナップショットつきで刻む
        let paid_snapshot: Vec<Value> = paid.iter()
            .map(|&c| json!({"ref": self.refv(c), "races": self.chars_json(c)["races"].clone()})).collect();
        // 保留状態へ（409, 601.1b）。gen は変えない
        let from_zone = self.s.cards[cid as usize].zone.clone();
        let owner = self.s.cards[cid as usize].owner as usize;
        let sh = self.shared(&from_zone);
        {
            let lst = self.s.zones.get_mut(&from_zone).unwrap();
            let idx = if sh { 0 } else { owner };
            if let Some(pos) = lst[idx].iter().position(|&x| x == cid) {
                lst[idx].remove(pos);
            }
        }
        self.note_deck(cid);
        self.s.cards[cid as usize].zone = "hold".to_string();
        self.s.hold.push(cid);
        if let Some(f) = face {
            self.s.cards[cid as usize].face = f;   // 実行する面（810.3）。保留中はその面として扱う
        }
        let r = self.refv(cid);
        if sst_bonus {
            self.s.cards[cid as usize].sst = true;
        }
        if stp_bonus {
            self.s.cards[cid as usize].stp = true;
        }
        let mut ev = json!({"ev": "move", "subject": r, "from": from_zone, "to": "bz", "reason": "summon", "controller": p, "unpaid": free});
        if sst_bonus {
            ev["sst"] = json!(true);
        }
        if !evo.is_empty() {
            ev["stack_on"] = evo[0].clone();
            ev["evolution"] = json!(true);   // 進化として重ねた印（evolve_base レコードは進化の時だけ出す）
            if evo.len() > 1 {
                ev["stack_more"] = json!(evo[1..].to_vec());
            }
        }
        if stp_bonus {
            ev["stp"] = json!(true);
        }
        if !paid_snapshot.is_empty() {
            self.s.cards[cid as usize].summon_tapped = paid_snapshot.clone();
            if !is_spell {
                ev["summon_tapped"] = json!(paid_snapshot);
            }
        }
        if is_spell {
            // 呪文（Python と同じ）: 唱えた → 書かれた順に解決 → 最終段階として墓地へ（605.2f）
            let mut env = json!({"you": p, "self": r, "vars": {}});
            if st {
                env["in_st"] = json!(true);
            }
            let ops = json!(self.def(cid).spell.clone());
            let cev = self.ev_task(vec![json!({"ev": "cast", "player": p, "subject": r, "unpaid": free})]);
            let mv = self.ev_task(vec![json!({"ev": "move", "subject": r, "from": from_zone, "to": self.def(cid).resolve_to.clone(), "reason": "resolve", "position": "top"})]);
            self.push(vec![cev, json!({"t": "effect", "ops": ops, "pc": 0, "env": env, "os": {}}), mv]);
            return Ok(None);
        }
        let t = self.ev_task(vec![ev]);
        self.push(vec![t]);
        Ok(None)
    }

    pub(crate) fn play_options(&self, p: i64) -> Vec<Value> {
        let mut out = vec![];
        for o in self.distinct_hand_options(p, "play") {
            let cid = o["cid"].as_i64().unwrap();
            for fi in self.face_list(cid) {
                if !self.can_play(cid, p, fi) {
                    continue;
                }
                match fi {
                    None => out.push(json!({"key": o["key"], "cid": cid, "name": self.def(cid).name})),
                    Some(f) => out.push(json!({"key": format!("{}:{}", o["key"].as_str().unwrap(), f), "cid": cid,
                        "name": self.fdef(cid, fi).name, "face": f})),
                }
            }
        }
        // マナ・墓地からの召喚は、許可を与える能力が無いので plain では出ない
        out
    }

    /// 適正な進化元（801.1a）。evolve_zone（既定は自分のバトルゾーン、超無限墓地進化は墓地）のクリーチャーで evolve_from を満たすもの
    fn evo_sources(&self, cid: i64, p: i64, face: Option<i64>) -> Vec<i64> {
        let d = self.fdef(cid, face);
        let ef = d.evolve_from.clone().unwrap_or(json!({}));
        let pool = if d.evolve_zone == "bz" || d.evolve_zone.is_empty() { self.bz_tops(Some(p)) } else { self.zl(&d.evolve_zone, p).clone() };
        pool.into_iter().filter(|&c| self.def(c).types.iter().any(|t| t == "creature") && self.filter_ok(c, &ef).unwrap_or(false)).collect()
    }
    /// 進化元の数による軽減後のコスト（「コストは0以下にはならない」= 最低1）
    fn evo_cost(&self, cid: i64, face: Option<i64>, n: i64) -> Option<i64> {
        let d = self.fdef(cid, face);
        if d.cost_reduce_per_evo != 0 { Some((d.cost - n * d.cost_reduce_per_evo).max(1)) } else { None }
    }
    fn is_evo(&self, cid: i64, face: Option<i64>) -> bool {
        self.fdef(cid, face).types.iter().any(|t| t == "evolution")
    }

    fn can_play(&self, cid: i64, p: i64, face: Option<i64>) -> bool {
        if self.is_evo(cid, face) {
            if !self.permits(cid, "summon") || !self.permits(cid, "enter_bz") {
                return false;
            }
            let d = self.fdef(cid, face);
            let srcs = self.evo_sources(cid, p, face);
            if (srcs.len() as i64) < d.evolve_count {
                return false;
            }
            let n = if d.evolve_any { srcs.len() as i64 } else { d.evolve_count };
            return !self.mana_choices_f(cid, p, face, self.evo_cost(cid, face, n), 1).is_empty();
        }
        if !self.fdef(cid, face).types.iter().any(|t| t == "creature") {
            if !self.permits(cid, "cast") {
                return false;
            }
        } else if !self.permits(cid, "summon") || !self.permits(cid, "enter_bz") {
            return false;
        }
        !self.mana_choices_f(cid, p, face, None, 1).is_empty()
    }

    fn st_attack(&mut self) -> R<Option<Value>> {
        let a = self.s.active;
        let turn = self.s.turn;
        let mut opts: Vec<Value> = vec![];
        let mut forced = false;   // 「攻撃する時、可能なら攻撃しなければならない」クリーチャーが攻撃できるなら pass は無い
        for c in self.bz_tops(Some(a)) {
            let before = opts.len();
            let k = &self.s.cards[c as usize];
            if k.tapped || (k.entered_turn == turn && !self.permits(c, "attack_summoning_sick")) {
                continue;
            }
            let dfn = k.defn.clone();
            if self.permits(c, "attack_player") {
                opts.push(json!({"key": format!("attack:{}:player", dfn), "cid": c, "target": "player"}));
            }
            for tc in self.bz_tops(Some(1 - a)) {
                // 505.2 既定はタップ状態だけ。allow 辞書 {attack_creature, other:{tapped:false,…}} が
                // 対象に一致すればタップされていないクリーチャーも攻撃できる（combat.py と同じ直接参照）
                let widened = !self.s.cards[tc as usize].tapped && self.allow_entries(c).iter().any(|e| {
                    e.get("action").and_then(|x| x.as_str()) == Some("attack_creature")
                        && e.get("other").map(|o| o.get("tapped") == Some(&json!(false)) && self.filter_ok(tc, o).unwrap_or(false)).unwrap_or(false)
                });
                if (self.s.cards[tc as usize].tapped || widened) && self.permits_o(c, "attack_creature", None, Some(tc)) && self.permits_vs(tc, "be_attacked", c) {
                    opts.push(json!({"key": format!("attack:{}:{}", dfn, self.s.cards[tc as usize].defn), "cid": c, "target": self.refv(tc)}));
                }
            }
            if opts.len() > before && self.chars(c, None).require.iter().any(|r| r == "attack") {
                forced = true;
            }
        }
        if !forced {
            opts.push(json!({"key": "pass"}));
        }
        let ans = match self.ask(a, "attack", opts.clone(), 1, 1) {
            Ask::Decision(d) => return Ok(Some(d)),
            Ask::Answer(x) => x,
        };
        let o = opts[ans[0]].clone();
        if o["key"] == json!("pass") {
            self.step_done();
            return Ok(None);
        }
        self.s.turn_counters.insert("attacked".into(), json!(true));
        let att = self.refv(o["cid"].as_i64().unwrap());
        self.push(vec![json!({"t": "attack", "attacker": att, "target": o["target"], "phase": 0, "cp": true})]);
        Ok(None)
    }

    fn window(&mut self, inner: Vec<Value>) -> Vec<Value> {
        self.s.seq += 1;
        let w = self.s.seq;
        let mut v = vec![json!({"t": "open_win", "win": w})];
        v.extend(inner);
        v.push(json!({"t": "resolve_pending", "win": w, "only_st": false}));
        v.push(json!({"t": "close_win"}));
        v
    }

    fn decl(player: i64, window: &str, rec: &Value) -> Value {
        json!({"t": "declare", "player": player, "window": window, "ctx": rec})
    }

    fn tset(&mut self, k: &str, v: Value) {
        self.s.tasks.last_mut().unwrap()[k] = v;
    }

    /// 攻撃ステップのサブステップ（506〜510）。ブロッカー・バトル置換・使用宣言は能力を持つカードだけなので plain では空振り
    fn h_attack(&mut self) -> R<Option<Value>> {
        let a = self.s.active;
        let (att, target, ph) = {
            let t = self.s.tasks.last().unwrap();
            (t["attacker"].clone(), t["target"].clone(), t["phase"].as_i64().unwrap())
        };
        if self.s.skip_rest {
            self.s.tasks.pop();
            self.expire("during_attack")?;
            return Ok(None);
        }
        if ph == 0 {
            self.tset("phase", json!(1));
            let n = self.s.turn_counters.get("attack_no").and_then(|v| v.as_i64()).unwrap_or(0) + 1;
            self.s.turn_counters.insert("attack_no".into(), json!(n));
            self.tset("ano", json!(n));
            self.s.turn_counters.insert("current_attack".into(), json!(n));
            let rec = json!({"ev": "attack", "subject": att, "target": target, "controller": a});
            let e = self.ev_task(vec![rec.clone()]);
            self.push(vec![e, Self::decl(a, "attack", &rec)]);
            // 第190弾（Python と同じ）: 攻撃宣言のタップは tap イベント。後から積むので先に実行される
            if !self.s.cards[att[0].as_i64().unwrap() as usize].tapped {
                let te = self.ev_task(vec![json!({"ev": "tap", "subject": att})]);
                self.push(vec![te]);
            }
            return Ok(None);
        }
        if ph == 1 {
            self.tset("phase", json!(2));
            if self.alive(&att) {
                let rec = json!({"ev": "attack", "subject": att, "target": target, "controller": a});
                self.push(vec![Self::decl(1 - a, "attack", &rec)]);
            }
            return Ok(None);
        }
        if ph < 5 && (!self.alive(&att) || (target != json!("player") && !self.alive(&target))) {
            self.tset("phase", json!(5));
            return Ok(None);
        }
        if ph == 2 {
            // 攻撃先の変更（第171弾）: plain には変更の能力が無いので済みの印だけ付ける（Python と同じ状態）
            if self.s.tasks.last().unwrap().get("redirect_done").is_none() {
                self.tset("redirect_done", json!(true));
            }
            // 507 ブロッククリーチャー指定
            let attc = att[0].as_i64().unwrap();
            let blockers: Vec<i64> = self.bz_tops(Some(1 - a)).into_iter().filter(|&c| {
                !self.s.cards[c as usize].tapped && self.def(c).types.iter().any(|t| t == "creature")
                    && self.permits_o(c, "block", None, Some(attc)) && self.permits_vs(attc, "be_blocked", c)
                    && json!([c, self.s.cards[c as usize].gen]) != target
            }).collect();
            // ブロックしなければならないクリーチャーがいる時はブロックしない選択肢が無く、ブロッカー全員がタップする
            let forced: Vec<i64> = blockers.iter().copied().filter(|&c| self.chars(c, None).require.iter().any(|r| r == "block")).collect();
            let guards: Vec<i64> = if target == json!("player") { vec![] } else {
                self.bz_tops(Some(1 - a)).into_iter().filter(|&c| {
                    !self.s.cards[c as usize].tapped && json!([c, self.s.cards[c as usize].gen]) != target && self.permits_o(c, "guardman", None, Some(attc))
                }).collect()
            };
            let mut opts: Vec<Value> = blockers.iter().map(|&c| self.card_option(c, None)).collect();
            for &c in &guards {
                opts.push(self.card_option(c, Some(format!("guard:{}", self.s.cards[c as usize].defn))));
            }
            if forced.is_empty() {
                opts.push(json!({"key": "no_block"}));
            }
            let ans = match self.ask(1 - a, "block", opts.clone(), 1, 1) {
                Ask::Decision(d) => return Ok(Some(d)),
                Ask::Answer(x) => x,
            };
            self.tset("phase", json!(3));
            let o = opts[ans[0]].clone();
            if o["key"] != json!("no_block") {
                let c = o["cid"].as_i64().unwrap();
                // ブロックしなければならないクリーチャー全員と、選ばれたブロッカー／ガードマンがタップする
                let to_tap: Vec<i64> = forced.iter().copied().chain([c]).filter(|&x| !self.s.cards[x as usize].tapped).collect();
                let r = self.refv(c);
                self.tset("target", r.clone());
                if o["key"].as_str().unwrap().starts_with("guard:") {
                    for &tc in &to_tap {
                        let te = self.ev_task(vec![json!({"ev": "tap", "subject": self.refv(tc)})]);
                        self.push(vec![te]);
                    }
                    return Ok(None);
                }
                self.tset("blocked", json!(true));
                let rec = json!({"ev": "block", "subject": r, "attacker": att, "controller": 1 - a});
                let e = self.ev_task(vec![rec.clone()]);
                self.push(vec![e, Self::decl(a, "block", &rec), Self::decl(1 - a, "block", &rec)]);
                for &tc in &to_tap {   // 第190弾: ブロック宣言のタップも tap イベント（block より先に実行）
                    let te = self.ev_task(vec![json!({"ev": "tap", "subject": self.refv(tc)})]);
                    self.push(vec![te]);
                }
            }
            return Ok(None);
        }
        if ph == 3 {
            self.tset("phase", json!(4));
            if target != json!("player") {
                if self.s.tasks.last().unwrap().get("subbed").is_none() {
                    self.tset("subbed", json!([]));
                }
                let bs = json!({"ev": "battle_start", "subject": att, "opponent": target, "controller": a});
                let e = self.ev_task(vec![bs]);
                let mut ts = self.window(vec![e]);
                ts.push(json!({"t": "battle_run", "att": att, "tgt": target}));
                self.push(ts);
            }
            return Ok(None);
        }
        if ph == 4 {
            // 509 ダイレクトアタック: 複数のブレイカー能力ならどれを使うか選ぶ
            let mut n = 1;
            if target == json!("player") && !self.zl("shield", 1 - a).is_empty() {
                let counts = self.break_opts(att[0].as_i64().unwrap());
                let opts: Vec<Value> = counts.iter().map(|n| json!({"key": format!("breaks:{}", n)})).collect();
                let ans = match self.ask(a, "choose_breaker", opts, 1, 1) {
                    Ask::Decision(d) => return Ok(Some(d)),
                    Ask::Answer(x) => x,
                };
                n = counts[ans[0]];
            }
            self.tset("phase", json!(5));
            if target == json!("player") {
                if !self.zl("shield", 1 - a).is_empty() {
                    if n > 0 {
                        self.push(vec![json!({"t": "break", "victim": 1 - a, "by": a, "count": n, "phase": 0, "in_effect": false, "breaker": att})]);
                    }
                } else {
                    self.game_lose(1 - a, "direct_attack");
                }
            }
            return Ok(None);
        }
        let end_fired = self.s.tasks.last().unwrap().get("end_fired").is_some();
        if !end_fired && self.s.result.is_none() {
            self.tset("end_fired", json!(true));
            let ano = self.s.tasks.last().unwrap().get("ano").cloned().unwrap_or(Value::Null);
            let broke = self.s.turn_counters.get(&format!("broke_in:{}", att[0].as_i64().unwrap())).cloned() == Some(ano);
            let e = self.ev_task(vec![json!({"ev": "attack_end", "subject": att, "target": target, "controller": a, "broke": broke, "blocked": self.s.tasks.last().unwrap().get("blocked").and_then(|v| v.as_bool()).unwrap_or(false)})]);
            self.push(vec![e]);
            return Ok(None);
        }
        self.s.tasks.pop();
        self.expire("during_attack")?;   // 510.2
        Ok(None)
    }

    /// 101.4 / 605.1: ターン・プレイヤーの待機中の効果から順に、1つずつ解決する（S・トリガー系・遅延は plain に無い）
    fn h_resolve_pending(&mut self) -> R<Option<Value>> {
        let (win, only_st) = {
            let t = self.s.tasks.last().unwrap();
            (t["win"].clone(), t["only_st"].as_bool().unwrap_or(false))
        };
        let here: Vec<Value> = self.s.pending.iter().filter(|p| p["win"] == win).cloned().collect();
        if here.iter().any(|p| p["kind"] != json!("normal") && p["kind"] != json!("strigger")) {
            return uns("pending kind");
        }
        let active = self.s.active;
        let st: Vec<Value> = here.iter().filter(|p| p["kind"] == json!("strigger")).cloned().collect();
        let pool: Vec<Value> = if !st.is_empty() {
            let mine: Vec<Value> = st.iter().filter(|p| p["controller"] == json!(active)).cloned().collect();
            if mine.is_empty() { st } else { mine }
        } else if only_st {
            vec![]
        } else {
            let mine: Vec<Value> = here.iter().filter(|p| p["controller"] == json!(active)).cloned().collect();
            if mine.is_empty() { here } else { mine }
        };
        if pool.is_empty() {
            self.s.tasks.pop();
            return Ok(None);
        }
        let player = pool[0]["controller"].as_i64().unwrap();
        let opts: Vec<Value> = pool
            .iter()
            .map(|p| json!({"key": format!("pending:{}:{}:{}", p["kind"].as_str().unwrap(), p["defn"].as_str().unwrap(), p["ab"]), "pid": p["pid"]}))
            .collect();
        let ans = match self.ask(player, "order_pending", opts.clone(), 1, 1) {
            Ask::Decision(d) => return Ok(Some(d)),
            Ask::Answer(x) => x,
        };
        let pid = opts[ans[0]]["pid"].clone();
        let idx = self.s.pending.iter().position(|p| p["pid"] == pid).unwrap();
        let p = self.s.pending.remove(idx);
        if p["kind"] == json!("strigger") {
            if self.alive(&p["src"]) {
                let c = p["src"][0].as_i64().unwrap();
                let gen = self.s.cards[c as usize].gen;
                let mut t = json!({"t": "play", "cid": c, "player": player, "free": true, "phase": "start", "gen": gen, "st": true});
                if let Some(f) = p.get("face") {
                    t["face"] = f.clone();
                }
                self.push(vec![t]);
            }
            return Ok(None);
        }
        let defn = p["defn"].as_str().unwrap().to_string();
        let ab = {
            let d = &self.rules.cards[&defn];
            let fd = match p.get("face").and_then(|v| v.as_i64()) { Some(f) if !d.faces.is_empty() => &d.faces[f as usize], _ => d };
            fd.abil[p["ab"].as_i64().unwrap() as usize].clone()
        };
        if let Some(cond) = ab.get("if") {
            if !self.eval_cond(cond, &p["env"])? {   // 条件は解決時に確認（603.4, 605.2a）
                return Ok(None);
            }
        }
        let eff = ab["effect"].clone();
        self.push(vec![json!({"t": "effect", "ops": eff, "pc": 0, "env": p["env"], "os": {}})]);
        Ok(None)
    }

    /// 効果の解釈（ops の1つずつ）。段階2-d の範囲: draw / may / tap・untap（自身）
    fn h_effect(&mut self) -> R<Option<Value>> {
        let (pc, n) = {
            let t = self.s.tasks.last().unwrap();
            (t["pc"].as_i64().unwrap() as usize, t["ops"].as_array().unwrap().len())
        };
        if pc >= n || self.s.result.is_some() {
            self.s.tasks.pop();
            return Ok(None);
        }
        let (op, env) = {
            let t = self.s.tasks.last().unwrap();
            (t["ops"][pc].clone(), t["env"].clone())
        };
        let mut deferred = false;
        match op["op"].as_str().unwrap_or("") {
            "modify" => {
                // 継続的効果（パワーの修整・このターンの間）。対象は解決時に固定（110.2e）
                if op.get("duration").map_or(false, |d| d != "end_of_turn") {
                    return uns("modify duration");
                }
                if let Some(cnt) = op["mod"].get("power").and_then(|pw| pw.get("count")) {
                    // {amount, count} の count は特性計算のたびに数え直す。数えられない形はここで Unsupported にする
                    self.candidates_ro(cnt, &env)?;
                }
                if op.get("dynamic").and_then(|v| v.as_bool()).unwrap_or(false) {
                    // 後から入ったカードにも及ぶ範囲指定。範囲は生成時に持ち主を固定してベイクする
                    let sel = &op["select"];
                    let you = env["you"].as_i64().unwrap();
                    let owner = match sel.get("owner").and_then(|v| v.as_str()).unwrap_or("you") {
                        "you" => json!(you), "opp" => json!(1 - you), "any" => json!("any"), _ => return uns("dynamic owner") };
                    self.s.seq += 1;
                    let src = env.get("self").and_then(|v| v.as_array()).map(|a| a[0].clone()).unwrap_or(Value::Null);
                    let ce = json!({"id": self.s.seq, "mod": op["mod"], "duration": "end_of_turn", "controller": env["you"], "src": src,
                        "affected": Value::Null, "filter": {"zone": sel.get("zone").cloned().unwrap_or(json!("bz")), "owner": owner,
                        "filter": sel.get("filter").cloned().unwrap_or(json!({}))}});
                    self.s.continuous.push(ce);
                    let sba = self.sba_power_tasks();
                    if !sba.is_empty() {
                        self.defer(sba);
                        deferred = true;
                    }
                } else {
                    self.s.seq += 1;
                    let cids = match self.select(&op["select"], &env)? {
                        Ok(c) => c,
                        Err(d) => {
                            self.s.seq -= 1;
                            return Ok(Some(d));
                        }
                    };
                    let src = env.get("self").and_then(|v| v.as_array()).map(|a| a[0].clone()).unwrap_or(Value::Null);
                    let ce = json!({"id": self.s.seq, "mod": op["mod"], "duration": "end_of_turn", "controller": env["you"], "src": src,
                        "affected": cids.iter().map(|&c| self.refv(c)).collect::<Vec<_>>()});
                    self.s.continuous.push(ce);
                    let sba = self.sba_power_tasks();
                    if !sba.is_empty() {
                        self.defer(sba);   // パワー0以下になったら、この効果の続きより先に破壊する（703.4c）
                        deferred = true;
                    }
                }
            }
            "flip_down" => {
                // 裏向きにする（水晶武装）。マナは無色として払い、シールドは表向きを戻す。イベントは作らない
                let cids = match self.select(&op["select"], &env)? {
                    Ok(c) => c,
                    Err(d) => return Ok(Some(d)),
                };
                for c in cids {
                    let k = &mut self.s.cards[c as usize];
                    if k.zone == "mana" {
                        k.face_down = true;
                    } else if k.zone == "shield" {
                        k.face_up = false;
                    }
                }
            }
            "play_free" => {
                // コストを支払わずに召喚する／唱える（112.3g）。ツインパクトは選択条件が呪文だけなら呪文面、他はクリーチャー面
                let cids = match self.select(&op["select"], &env)? {
                    Ok(c) => c,
                    Err(d) => return Ok(Some(d)),
                };
                let want: Vec<String> = op["select"].get("filter").and_then(|f| f.get("types")).and_then(|v| v.as_array())
                    .map(|a| a.iter().filter_map(|x| x.as_str().map(String::from)).collect()).unwrap_or_default();
                let you = env["you"].as_i64().unwrap();
                let mut ts = vec![];
                for c in cids.clone() {
                    let mut t = json!({"t": "play", "cid": c, "player": you, "free": true, "phase": "start", "gen": self.s.cards[c as usize].gen});
                    let faces = &self.rules.cards[&self.s.cards[c as usize].defn].faces;
                    if !faces.is_empty() {
                        let mut f = 0;
                        if want.iter().any(|x| x == "spell") && !want.iter().any(|x| x == "creature") {
                            if let Some(i) = faces.iter().position(|fd| fd.types.iter().any(|x| x == "spell")) {
                                f = i;
                            }
                        }
                        t["face"] = json!(f);
                    }
                    ts.push(t);
                }
                if let Some(name) = op.get("as").and_then(|v| v.as_str()) {
                    ts.push(json!({"t": "bind", "env": env, "name": name, "cids": cids, "zone": "bz"}));
                }
                if !ts.is_empty() {
                    self.defer(ts);
                    deferred = true;
                }
            }
            "end_turn" => {
                // ターンの残りをとばす（今の効果の解決は最後まで行う）
                self.s.skip_rest = true;
            }
            "win" => {
                let you = env["you"].as_i64().unwrap();
                let w = match op.get("player").and_then(|v| v.as_str()).unwrap_or("you") { "you" => you, "opp" => 1 - you, _ => return uns("win player") };
                self.s.result = Some(json!({"winner": w, "reason": "effect", "turn": self.s.turn}));
                // Python は置換の instead に積んだ効果タスクと実行中のタスクが同じオブジェクト。対局がここで終わると
                // 残ったタスクが digest に出るので、写しの pc も進めておく
                if env.get("capture").is_some() {
                    let ops = self.s.tasks.last().unwrap()["ops"].clone();
                    for t in self.s.tasks.iter_mut().rev() {
                        if t["t"] == json!("event") && t["applying"].as_bool().unwrap_or(false) {
                            for e in t["instead"].as_array_mut().unwrap() {
                                if e["ops"] == ops && e["env"] == env && e["pc"] == json!(pc) {
                                    e["pc"] = json!(pc + 1);
                                }
                            }
                            break;
                        }
                    }
                }
            }
            "draw" => {
                let cnt = op.get("count").and_then(|v| v.as_i64()).unwrap_or(1);
                let you = env["you"].as_i64().unwrap();
                let ps: Vec<i64> = match op.get("player").and_then(|v| v.as_str()).unwrap_or("you") {
                    "you" => vec![you],
                    "opp" => vec![1 - you],
                    "each" => {
                        let a = self.s.active;
                        vec![a, 1 - a]
                    }
                    _ => return uns("draw player"),
                };
                let mut ch = vec![];
                for p in ps {
                    for _ in 0..cnt {
                        ch.push(self.ev_task_env(vec![json!({"ev": "draw", "player": p})], &env));
                    }
                }
                self.defer(ch);
                deferred = true;
            }
            "if" => {
                if op.as_object().unwrap().keys().any(|k| !["op", "cond", "then", "else"].contains(&k.as_str())) {
                    return uns("if options");
                }
                let br = if self.eval_cond(&op["cond"], &env)? { op.get("then") } else { op.get("else") };
                let ops = br.cloned().unwrap_or(json!([]));
                let child = json!({"t": "effect", "ops": ops, "pc": 0, "env": env, "os": {}});
                self.defer(vec![child]);
                deferred = true;
            }
            "repeat" => {
                let n = op["times"].as_i64().ok_or_else(|| "repeat times".to_string());
                let n = match n { Ok(n) => n, Err(e) => return uns(e) };
                let kids: Vec<Value> = (0..n).map(|_| json!({"t": "effect", "ops": op["body"], "pc": 0, "env": env, "os": {}})).collect();
                if !kids.is_empty() {
                    self.defer(kids);
                    deferred = true;
                }
            }
            "modal" => {
                // 「次のうちいずれか count 個を選ぶ」（repeat なし）: 異なるモードを選び、書かれた順に解決する
                if op.get("repeat").and_then(|v| v.as_bool()).unwrap_or(false) {
                    return uns("modal repeat");
                }
                let n = op.get("count").and_then(|v| v.as_i64()).unwrap_or(1);
                let modes = op["modes"].as_array().cloned().unwrap_or_default();
                {
                    let os = &mut self.s.tasks.last_mut().unwrap()["os"];
                    if os.get("picked").is_none() {
                        os["picked"] = json!([]);
                    }
                }
                let you = env["you"].as_i64().unwrap();
                let opts: Vec<Value> = (0..modes.len()).map(|i| json!({"key": format!("mode:{}", i)})).collect();
                let mut ans = match self.ask(you, "choose_mode", opts, n as usize, n as usize) {
                    Ask::Decision(d) => return Ok(Some(d)),
                    Ask::Answer(x) => x,
                };
                ans.sort();
                let kids: Vec<Value> = ans.iter().map(|&i| json!({"t": "effect", "ops": modes[i], "pc": 0, "env": env, "os": {}})).collect();
                if !kids.is_empty() {
                    self.defer(kids);
                    deferred = true;
                }
            }
            "may" => {
                if op.get("label").is_some() || op.get("player").is_some() || op.get("else").is_some() {
                    return uns("may options");
                }
                let you = env["you"].as_i64().unwrap();
                let ans = match self.ask(you, "yes_no", vec![json!({"key": "yes"}), json!({"key": "no"})], 1, 1) {
                    Ask::Decision(d) => return Ok(Some(d)),
                    Ask::Answer(x) => x,
                };
                if ans[0] == 0 {
                    let child = json!({"t": "effect", "ops": op["body"], "pc": 0, "env": env, "os": {}});
                    self.defer(vec![child]);
                    deferred = true;
                }
            }
            k @ ("tap" | "untap") => {
                if op.get("no_untap_next").is_some() {
                    return uns("no_untap_next");
                }
                let cids = match self.select(&op["select"], &env)? {
                    Ok(c) => c,
                    Err(d) => return Ok(Some(d)),
                };
                if !cids.is_empty() {
                    let evs: Vec<Value> = cids.iter().map(|&c| json!({"ev": k, "subject": self.refv(c)})).collect();
                    let e = self.ev_task_env(evs, &env);
                    self.defer(vec![e]);
                    deferred = true;
                }
            }
            "move" => {
                let to = op["to"].as_str().unwrap_or("");
                if !["hand", "graveyard", "mana", "deck", "shield", "bz"].contains(&to) {
                    return uns(format!("move to {}", to));
                }
                let mut cids = match self.select(&op["select"], &env)? {
                    Ok(c) => c,
                    Err(d) => return Ok(Some(d)),
                };
                if op.get("order").and_then(|v| v.as_str()) == Some("shuffle") && cids.len() > 1 {
                    // 選んだカードの順を無作為に入れ替える（Python の op_move と同じ Fisher-Yates）
                    for i in (1..cids.len()).rev() {
                        let j = self.s.rng_below((i + 1) as u64) as usize;
                        cids.swap(i, j);
                    }
                }
                let pos = op.get("position").and_then(|v| v.as_str()).unwrap_or("top");
                if op.get("order").and_then(|v| v.as_str()) == Some("choose") && to == "deck" {
                    let names: std::collections::BTreeSet<String> = cids.iter().map(|&c| self.s.cards[c as usize].defn.clone()).collect();
                    if names.len() > 1 {
                        let opts: Vec<Value> = cids.iter().map(|&c| self.card_option_look(c)).collect();
                        let n = cids.len();
                        let a = match self.ask(env["you"].as_i64().unwrap(), "order_cards", opts, n, n) {
                            Ask::Decision(d) => return Ok(Some(d)),
                            Ask::Answer(x) => x,
                        };
                        cids = a.iter().map(|&i| cids[i]).collect();
                        if pos == "top" {
                            cids.reverse();   // 1枚ずつ一番上に置かれるので、最後に置いたものが一番上になる
                        }
                    }
                }
                let tapped = op.get("tapped").and_then(|v| v.as_bool()).unwrap_or(false);
                // 効果でシールドを手札に加える時は、S・トリガー等の使用宣言ができる（113.6。Python と同じく break タスクで）
                let shield_out: Vec<i64> = if to == "hand" { cids.iter().copied().filter(|&c| self.s.cards[c as usize].zone == "shield").collect() } else { vec![] };
                let mut owners: Vec<i64> = vec![];
                for &c in &shield_out {
                    let o = self.s.cards[c as usize].controller;
                    if !owners.contains(&o) {
                        owners.push(o);
                    }
                }
                owners.sort_by_key(|&o| (o != self.s.active, o));
                let in_st = env.get("in_st").and_then(|v| v.as_bool()).unwrap_or(false);
                let face_up = op.get("face_up").and_then(|v| v.as_bool()).unwrap_or(false);
                let face_down = op.get("face_down").and_then(|v| v.as_bool()).unwrap_or(false);
                let strigger = op.get("strigger").and_then(|v| v.as_str());
                let out_tasks: Vec<Value> = owners.iter().map(|&o| {
                    let cs: Vec<i64> = shield_out.iter().copied().filter(|&c| self.s.cards[c as usize].controller == o).collect();
                    let mut t = json!({"t": "break", "victim": o, "by": env["you"], "count": cs.len(), "phase": 1, "chosen": cs,
                           "in_effect": in_st, "reason": op["reason"], "fire_break": false});
                    if let Some(st) = strigger {
                        t["strigger"] = json!(st);   // この移動で手札に加わるカードの S・トリガー印（宣言時に見る）
                    }
                    t
                }).collect();
                let evs: Vec<Value> = cids
                    .iter()
                    .filter(|c| !shield_out.contains(c))
                    .map(|&c| {
                        let mut e = json!({"ev": "move", "subject": self.refv(c), "to": to, "reason": op["reason"], "position": pos});
                        if tapped {
                            e["tapped"] = json!(true);
                        }
                        if face_up {
                            e["face_up"] = json!(true);
                        }
                        if face_down {
                            e["face_down"] = json!(true);
                        }
                        if let Some(st) = strigger {
                            e["strigger"] = json!(st);
                        }
                        e
                    })
                    .collect();
                let bind: Vec<Value> = match op.get("as").and_then(|v| v.as_str()) {
                    Some(name) => vec![json!({"t": "bind", "env": env, "name": name, "cids": cids, "zone": to})],
                    None => vec![],
                };
                if evs.is_empty() && out_tasks.is_empty() {
                    if let Some(name) = op.get("as").and_then(|v| v.as_str()) {
                        let t = self.s.tasks.last_mut().unwrap();
                        if !t["env"]["vars"].is_object() {
                            t["env"]["vars"] = json!({});
                        }
                        t["env"]["vars"][name] = json!([]);
                    }
                } else {
                    let mut tasks: Vec<Value> = if to == "bz" {
                        evs.into_iter().map(|e| self.ev_task_env(vec![e], &env)).collect()   // バトルゾーンへ複数枚は1枚ずつ（409.1e）
                    } else if !evs.is_empty() {
                        vec![self.ev_task_env(evs, &env)]
                    } else {
                        vec![]
                    };
                    if to != "bz" {
                        tasks.extend(out_tasks);
                    }
                    tasks.extend(bind);
                    self.defer(tasks);
                    deferred = true;
                }
            }
            "choose" => {
                if op.get("reveal").is_some() {
                    return uns("choose reveal");
                }
                let cids = match self.select(&op["select"], &env)? {
                    Ok(c) => c,
                    Err(d) => return Ok(Some(d)),
                };
                let refs: Vec<Value> = cids.iter().map(|&c| self.refv(c)).collect();
                let name = op["as"].as_str().unwrap_or("").to_string();
                // Python は子の効果と env の辞書を共有する。同じ env（値が等しいもの）を持つタスクすべてに書く
                let old = self.s.tasks.last().unwrap()["env"].clone();
                for t in self.s.tasks.iter_mut() {
                    if t.get("env") == Some(&old) {
                        if !t["env"]["vars"].is_object() {
                            t["env"]["vars"] = json!({});
                        }
                        t["env"]["vars"][name.as_str()] = json!(refs.clone());
                    }
                }
            }
            "shuffle" => {
                let you = env["you"].as_i64().unwrap();
                let p = match op.get("player").and_then(|v| v.as_str()).unwrap_or("you") {
                    "you" => you,
                    "opp" => 1 - you,
                    _ => return uns("shuffle player"),
                };
                let n = self.s.pub_len();
                let turn = self.s.turn;
                self.s.r#pub.push(json!({"n": n, "turn": turn, "kind": "shuffle", "viewers": [0, 1], "player": p, "zone": "deck"}));
                let len = self.s.zones["deck"][p as usize].len();
                for i in (1..len).rev() {
                    let j = self.s.rng_below((i + 1) as u64) as usize;
                    self.s.zones.get_mut("deck").unwrap()[p as usize].swap(i, j);
                }
            }
            other => return uns(format!("op {}", other)),
        }
        if !deferred {
            let t = self.s.tasks.last_mut().unwrap();
            t["pc"] = json!(pc as i64 + 1);
            t["os"] = json!({});
        }
        Ok(None)
    }

    /// t の次の op を children が終わった後に回す（書かれた順に解決する 605.2c）
    fn defer(&mut self, children: Vec<Value>) {
        let t = self.s.tasks.last_mut().unwrap();
        t["pc"] = json!(t["pc"].as_i64().unwrap() + 1);
        t["os"] = json!({});
        self.push(children);
    }

    /// 誘発チェック（Python 版 _collect_triggers の写し）
    fn collect_triggers(&mut self, rec: &mut Value) {
        self.s.ev_seq += 1;
        rec["_eid"] = json!(self.s.ev_seq);
        let win = self.s.windows.last().copied().unwrap_or(0);
        // 発生源（Python 版 _collect_triggers と同じ並び）: バトルゾーン → 他のゾーンで働く誘発の札
        // → 離れたカード自身（LKI）→ 宿主（from_under 専用）→ 進化元自身。3つ目は host_only か
        let mut sources: Vec<(i64, Option<Value>, bool)> = self.bz_tops(None).into_iter().map(|c| (c, None, false)).collect();
        for z in self.rules.zt_zones.clone() {
            for p in 0..2i64 {
                for &c in self.zl(&z, p).clone().iter() {
                    if self.def(c).zt {
                        sources.push((c, None, false));
                    }
                }
            }
        }
        let lki = rec.get("lki").cloned().filter(|v| !v.is_null());
        if let Some(l) = &lki {
            let subj = rec["subject"][0].as_i64().unwrap();
            let lz = l["zone"].as_str().unwrap_or("");
            if lz == "bz" && rec.get("to").and_then(|v| v.as_str()) != Some("bz") {
                sources.push((subj, Some(l.clone()), false));
            } else if lz != "bz" && self.s.cards[subj as usize].zone != lz {
                sources.push((subj, Some(l.clone()), false));
            }
        }
        let host_lki = rec.get("host_lki").cloned().filter(|v| !v.is_null());
        if let (Some(hl), Some(host)) = (&host_lki, rec.get("host")) {
            if hl["zone"].as_str() == Some("bz") {
                if let Some(h) = host[0].as_i64() {
                    sources.push((h, Some(hl.clone()), true));
                }
            }
        }
        if rec["ev"] == json!("evolve_base") {
            if let Some(sb) = rec["subject"][0].as_i64() {
                sources.push((sb, None, false));
            }
        }
        for (src, lsrc, host_only) in sources {
            let (defn, zone, ctrl, sref, face) = match &lsrc {
                Some(l) => (l["defn"].as_str().unwrap().to_string(), l["zone"].as_str().unwrap().to_string(),
                            l["controller"].as_i64().unwrap(), l["ref"].clone(), l["face"].as_i64().unwrap_or(-1)),
                None => {
                    let c = &self.s.cards[src as usize];
                    (c.defn.clone(), c.zone.clone(), c.controller, json!([src, c.gen]), c.face)
                }
            };
            // Python の _trigger_abs: 面が決まっていればその面、面未定のツインパクトは各面の能力を面つきで
            let abs: Vec<(usize, Value, Option<i64>)> = {
                let d = &self.rules.cards[&defn];
                if d.faces.is_empty() {
                    d.abil.iter().cloned().enumerate().map(|(i, a)| (i, a, None)).collect()
                } else if face >= 0 {
                    d.faces[face as usize].abil.iter().cloned().enumerate().map(|(i, a)| (i, a, Some(face))).collect()
                } else {
                    d.faces.iter().enumerate().flat_map(|(fi, f)| f.abil.iter().cloned().enumerate().map(move |(i, a)| (i, a, Some(fi as i64)))).collect()
                }
            };
            for (i, ab, ab_face) in abs {
                if ab["kind"] != json!("trigger") || ab.get("zone").and_then(|v| v.as_str()).unwrap_or("bz") != zone {
                    continue;
                }
                if host_only && ab["when"].get("from_under").is_none() {
                    continue;   // 宿主の lki 発生源は from_under 誘発専用
                }
                if !self.when_match(&ab["when"], rec, &sref, ctrl) {
                    continue;
                }
                let env = json!({"you": ctrl, "self": sref, "event": rec.clone(), "vars": {}});
                if lsrc.is_none() {
                    if let Some(cond) = ab.get("if") {
                        // 誘発条件つきの能力は誘発時にも条件を見る（603.4）。離れた時の誘発は解決時だけ
                        if !self.eval_cond(cond, &json!({"you": ctrl, "self": sref, "event": rec.clone(), "vars": {}})).unwrap_or(false) {
                            continue;
                        }
                    }
                }
                let face_s = ab_face.map(|f| f.to_string()).unwrap_or_default();
                if ab.get("once_per_turn").and_then(|v| v.as_bool()).unwrap_or(false) {
                    // 「各ターンに一度」: このカード（オブジェクト）のこの能力は1ターンに1回だけ誘発する
                    let key = format!("once:{}:{}:{}:{}", sref[0].as_i64().unwrap_or(-1), sref[1].as_i64().unwrap_or(-1), face_s, i);
                    if self.s.turn_counters.get(&key).map_or(false, |v| !v.is_null() && v.as_bool() != Some(false) && v.as_i64() != Some(0)) {
                        continue;
                    }
                    self.s.turn_counters.insert(key, json!(1));
                }
                if ab.get("first_time").and_then(|v| v.as_bool()).unwrap_or(false) {
                    // 「各ターン、はじめて〜した時」: その出来事がこのターン最初に起きた時だけ誘発する
                    // （同名カード・同能力で共有し、最初の出来事では全コピーが誘発する）
                    let key = format!("first:{}:{}:{}:{}", ctrl, defn, face_s, i);
                    let eid = rec["_eid"].as_i64().unwrap_or(0);
                    if let Some(seen) = self.s.turn_counters.get(&key) {
                        if seen.as_i64() != Some(eid) {
                            continue;
                        }
                    }
                    self.s.turn_counters.insert(key, json!(eid));
                }
                self.s.seq += 1;
                let mut p = json!({"pid": self.s.seq, "kind": "normal", "win": win, "controller": ctrl, "src": sref, "defn": defn, "ab": i,
                    "env": env});
                if let Some(f) = ab_face {
                    p["face"] = json!(f);
                }
                self.s.pending.push(p);
            }
        }
    }

    /// 誘発条件の照合（Python 版 _match_when の写し）。sref は発生源の参照（env["self"]）、
    /// ctrl は発生源のコントローラー（env["you"]）
    fn when_match(&self, w: &Value, rec: &Value, sref: &Value, ctrl: i64) -> bool {
        if w["event"] != rec["ev"] {
            return false;
        }
        for k in ["from", "to", "reason", "via"] {
            if let Some(wv) = w.get(k) {
                match wv.as_array() {
                    Some(l) => {
                        if !l.contains(rec.get(k).unwrap_or(&Value::Null)) {
                            return false;
                        }
                    }
                    None => {
                        if rec.get(k) != Some(wv) {
                            return false;
                        }
                    }
                }
            }
        }
        if rec["ev"] == json!("move") && rec.get("from") == Some(&json!("bz")) && rec.get("to") == Some(&json!("bz"))
            && w.get("from").is_some() && w.get("to").is_none() {
            return false;   // バトルゾーン内の移動は「離れた時」ではない（第183弾）
        }
        if let Some(tw) = w.get("target") {
            // 攻撃先: player（シールドも含む）か creature か、self や {owner, filter} のクリーチャーか
            let tg = rec.get("target");
            if tw.as_str() == Some("player") || tw.as_str() == Some("creature") {
                let is_player = tg.map_or(false, |t| t.as_str() == Some("player"));
                if is_player != (tw.as_str() == Some("player")) {
                    return false;
                }
            } else if tg.map_or(true, |t| t.is_null() || t.as_str() == Some("player"))
                || !self.ref_match(tw, tg.unwrap(), sref, ctrl) {
                return false;
            }
        }
        for k in ["shield", "attacker", "opponent", "sealed_from"] {
            if let Some(pat) = w.get(k) {
                match rec.get(k) {
                    Some(x) if !x.is_null() => {
                        if !self.ref_match(pat, x, sref, ctrl) {
                            return false;
                        }
                    }
                    _ => return false,
                }
            }
        }
        if let Some(spec) = w.get("ord") {
            // その出来事のこのターンでの通し番号（履歴基盤が rec に刻む）
            let kind = spec.get("kind").and_then(|k| k.as_str());
            let v = match kind {
                Some(k) => rec.get("ord").and_then(|o| o.get(k)).and_then(|x| x.as_i64()),
                None => None,
            };
            let v = match v {
                Some(v) => v,
                None => return false,
            };
            if let Some(x) = spec.get("eq").and_then(|x| x.as_i64()) {
                if v != x {
                    return false;
                }
            }
            if let Some(x) = spec.get("ge").and_then(|x| x.as_i64()) {
                if v < x {
                    return false;
                }
            }
            if let Some(x) = spec.get("gt").and_then(|x| x.as_i64()) {
                if v <= x {
                    return false;
                }
            }
            if let Some(x) = spec.get("le").and_then(|x| x.as_i64()) {
                if v > x {
                    return false;
                }
            }
            if let Some(x) = spec.get("lt").and_then(|x| x.as_i64()) {
                if v >= x {
                    return false;
                }
            }
        }
        for k in ["unpaid", "broke", "blocked", "face_up", "emblem", "vivid", "stacked"] {
            if let Some(wv) = w.get(k) {
                if rec.get(k).and_then(|v| v.as_bool()).unwrap_or(false) != wv.as_bool().unwrap_or(false) {
                    return false;
                }
            }
        }
        if let Some(pl) = w.get("player").and_then(|v| v.as_str()) {
            let want = if pl == "you" { ctrl } else { 1 - ctrl };
            if rec.get("player").and_then(|v| v.as_i64()) != Some(want) {
                return false;
            }
        }
        if let Some(by) = w.get("by").and_then(|v| v.as_str()) {
            // そのイベントを起こした効果の解決者（「相手の効果によって〜」）
            let want = if by == "you" { ctrl } else { 1 - ctrl };
            if rec.get("by").and_then(|v| v.as_i64()) != Some(want) {
                return false;
            }
        }
        if let Some(fu) = w.get("from_under") {
            // 移動直前に他のカードの下にあったか: true=下にあった / false=下になかった /
            // self=発生源自身の下にあった / {owner, filter}=宿主への条件（宿主の lki に当てる）
            let host = rec.get("host").filter(|v| !v.is_null());
            if fu.as_bool() == Some(false) {
                if host.is_some() {
                    return false;
                }
            } else if host.is_none() {
                return false;
            } else if fu.as_bool() == Some(true) {
                // そのまま通す
            } else if fu.as_str() == Some("self") {
                if !self.ref_match(&json!("self"), host.unwrap(), sref, ctrl) {
                    return false;
                }
            } else if fu.is_object() {
                let hl = rec.get("host_lki").filter(|v| !v.is_null());
                if !self.subject_match_trig(fu, host.unwrap()[0].as_i64().unwrap_or(-1), sref, ctrl, hl) {
                    return false;
                }
            } else {
                return false;
            }
        }
        if let Some(sw) = w.get("subject") {
            let subj = match rec.get("subject") {
                Some(s) if !s.is_null() => s,
                _ => return false,
            };
            if sw.as_str() == Some("self") {
                return sref[0].as_i64() == subj[0].as_i64();
            }
            // 離れた時の姿（lki）で見るのは、バトルゾーンから動いた時（と exlife_of の照合）だけ
            let lki = if rec.get("from").and_then(|v| v.as_str()) == Some("bz")
                || (sw.is_object() && sw.get("exlife_of").is_some()) {
                rec.get("lki").filter(|v| !v.is_null())
            } else {
                None
            };
            return self.subject_match_trig(sw, subj[0].as_i64().unwrap_or(-1), sref, ctrl, lki);
        }
        true
    }

    /// イベントに出てくるクリーチャー（攻撃先・攻撃クリーチャー等）の参照への照合（Python 版 _ref_match）
    fn ref_match(&self, pat: &Value, refv: &Value, sref: &Value, ctrl: i64) -> bool {
        if pat.as_str() == Some("self") {
            return refv[0].as_i64() == sref[0].as_i64();
        }
        match refv[0].as_i64() {
            Some(cid) => self.subject_match_trig(pat, cid, sref, ctrl, None),
            None => false,
        }
    }

    /// Python 版 _subject_match（誘発の文脈: base=False、lki を見る形）。pat は "self" か辞書
    /// （ゲートが refs / castle_of / castle_only / exlife_of を除いている）
    fn subject_match_trig(&self, pat: &Value, cid: i64, sref: &Value, you: i64, lki: Option<&Value>) -> bool {
        if cid < 0 {
            return false;
        }
        if let Some(s) = pat.as_str() {
            return s == "self" && sref[0].as_i64() == Some(cid);
        }
        let obj = match pat.as_object() {
            Some(o) => o,
            None => return false,
        };
        let c = &self.s.cards[cid as usize];
        if let Some(z) = obj.get("zone") {
            // subject のいるゾーン。離れた時は lki のゾーンで見る
            let cz = if let Some(l) = lki { l["zone"].as_str().unwrap_or("") } else { c.zone.as_str() };
            if z.as_str() != Some(cz) {
                return false;
            }
        }
        let cctrl = if let Some(l) = lki { l["controller"].as_i64().unwrap_or(-1) } else { c.controller };
        if let Some(o) = obj.get("owner") {
            let os = o.as_str().unwrap_or("");
            if os != "any" {
                let want = if os == "you" { you } else if os == "opp" { 1 - you } else { -1 };
                if cctrl != want {
                    return false;
                }
            }
        }
        if obj.get("other").and_then(|v| v.as_bool()).unwrap_or(false) && sref[0].as_i64() == Some(cid) {
            return false;
        }
        let f = obj.get("filter").cloned().unwrap_or(json!({}));
        self.filter_match_trig(cid, &f, lki)
    }

    /// Python 版 filter_match（誘発の subject 照合の文脈）。特性の見え方は、lki があれば lki の chars、
    /// 常在型の条件の入れ子・特性計算中は印刷、それ以外は現在の特性
    /// （plain の範囲では cost / civs / types / races / names は印刷どおりで、パワーとキーワードだけが特性で動く）
    fn filter_match_trig(&self, cid: i64, f: &Value, lki: Option<&Value>) -> bool {
        let c = &self.s.cards[cid as usize];
        let is_sealed = c.zone == "bz" && !c.seals.is_empty();
        if let Some(sv) = f.get("sealed") {
            if is_sealed != sv.as_bool().unwrap_or(false) {
                return false;
            }
        } else if is_sealed && lki.is_none() {
            return false;   // 封印されているクリーチャーは無視される（封印を対象にする効果だけが sealed で指す）
        }
        let d = self.def(cid);
        let sl = |v: &Value| -> Vec<String> {
            match v {
                Value::String(x) => vec![x.clone()],
                Value::Array(a) => a.iter().filter_map(|x| x.as_str().map(|y| y.to_string())).collect(),
                _ => vec![],
            }
        };
        let str_list = |v: &Value| -> Vec<String> {
            v.as_array().map(|a| a.iter().filter_map(|x| x.as_str().map(|y| y.to_string())).collect()).unwrap_or_default()
        };
        // 特性のビュー: (power, cost, civs, types, races, keywords, names)
        let (power, cost, civs, types, races, keywords, names): (i64, i64, Vec<String>, Vec<String>, Vec<String>, Vec<String>, Vec<String>) =
            if let Some(l) = lki {
                let ch = &l["chars"];
                let names = {
                    let ns = str_list(&ch["names"]);
                    if ns.is_empty() { vec![ch["name"].as_str().unwrap_or("").to_string()] } else { ns }
                };
                (ch["power"].as_i64().unwrap_or(0), ch["cost"].as_i64().unwrap_or(0),
                 str_list(&ch["civs"]), str_list(&ch["types"]), str_list(&ch["races"]), str_list(&ch["keywords"]), names)
            } else if self.static_depth.get() > 1 || self.chars_busy.contains(cid) {
                (d.power, d.cost, d.civs.clone(), d.types.clone(), d.races.clone(), d.keywords.clone(), vec![d.name.clone()])
            } else {
                let ch = self.chars(cid, None);
                (ch.power, d.cost, d.civs.clone(),
                 if ch.sealed { vec![] } else { d.types.clone() },
                 if ch.sealed { vec![] } else { d.races.clone() },
                 ch.keywords.clone(), vec![d.name.clone()])
            };
        for (k, v) in f.as_object().unwrap() {
            let ok = match k.as_str() {
                "sealed" => continue,
                "any_of" => v.as_array().map_or(false, |subs| subs.iter().any(|sub| self.filter_match_trig(cid, sub, lki))),
                "types" => sl(v).iter().any(|t| types.contains(t)),
                "not_types" => !sl(v).iter().any(|t| types.contains(t)),
                "race_has" => races.iter().any(|r| r.contains(v.as_str().unwrap_or("\u{0}"))),
                "not_race_has" => !races.iter().any(|r| sl(v).iter().any(|p| r.contains(p))),
                "name_has" => names.iter().any(|nm| nm.contains(v.as_str().unwrap_or("\u{0}"))),
                "twinpact" => !self.rules.cards[&c.defn].faces.is_empty() == v.as_bool().unwrap_or(false),
                "civs" => sl(v).iter().any(|t| civs.contains(t)),
                "civs_all" => sl(v).iter().all(|t| civs.contains(t)),
                "not_civs" => !sl(v).iter().any(|t| civs.contains(t)),
                "races" => sl(v).iter().any(|t| races.contains(t)),
                "name" => names.iter().any(|nm| Some(nm.as_str()) == v.as_str()),
                "not_name" => !names.iter().any(|nm| Some(nm.as_str()) == v.as_str()),
                "cost_le" => v.as_i64().map_or(false, |x| cost <= x),
                "cost_ge" => v.as_i64().map_or(false, |x| cost >= x),
                "power_le" => v.as_i64().map_or(false, |x| power <= x),
                "power_ge" => v.as_i64().map_or(false, |x| power >= x),
                "multicolor" => (civs.len() > 1) == v.as_bool().unwrap_or(false),
                "colorless" => civs.is_empty() == v.as_bool().unwrap_or(false),
                "tapped" => (if let Some(l) = lki { l["tapped"].as_bool().unwrap_or(false) } else { c.tapped }) == v.as_bool().unwrap_or(false),
                "face_down" => c.face_down == v.as_bool().unwrap_or(false),
                "face_up" => c.face_up == v.as_bool().unwrap_or(false),
                "evolution" => d.types.iter().any(|t| t == "evolution") == v.as_bool().unwrap_or(false),
                "entered_this_turn" => (c.entered_turn == self.s.turn) == v.as_bool().unwrap_or(false),
                "keyword" => keywords.iter().any(|x| Some(x.as_str()) == v.as_str()),
                _ => true,   // Python の filter_match は知らないキーを無視する（ゲートがキーを制限している）
            };
            if !ok {
                return false;
            }
        }
        true
    }

    /// chars の JSON（lki に載せる。Python 版 _chars_calc の、能力が自身への単純な常在型だけの札の結果）
    /// 探索の葉の評価に使う数（Python の search.leaf_eval._evaluate が読む欄だけ）:
    /// [相手のシールド, 自分のクリーチャーのブレイク数の和, 自分の山札, マナ, 手札, 自分の場の数, 相手の山札]
    pub fn eval_feats(&self, me: i64) -> Vec<i64> {
        let opp = 1 - me;
        let mine = self.bz_tops(Some(me));
        let mut breaks = 0;
        for &c in &mine {
            if self.def(c).types.iter().any(|t| t == "creature") {
                breaks += self.chars_json(c)["breaks"].as_i64().unwrap_or(1);
            }
        }
        vec![self.zl("shield", opp).len() as i64, breaks, self.zl("deck", me).len() as i64, self.zl("mana", me).len() as i64,
             self.zl("hand", me).len() as i64, mine.len() as i64, self.zl("deck", opp).len() as i64]
    }

    /// ループ検出の骨格の材料（Python の engine.loop.abstract が読む欄だけ。並べ替え・文字列化・ハッシュは Python 側）
    /// 区域の札の id（Python の s.zones[z][owner] と同じ並び。zl と違い共有扱いの区域でも持ち主の欄をそのまま返す）
    pub fn zone_ids(&self, z: &str, owner: i64) -> Vec<i64> {
        self.s.zones[z][owner as usize].clone()
    }

    /// 札の定義名と、下にある札の定義名（並べ替え済み）
    pub fn card_sig(&self, cid: i64) -> (String, Vec<String>) {
        let k = &self.s.cards[cid as usize];
        let mut u: Vec<String> = k.under.iter().map(|&c| self.s.cards[c as usize].defn.clone()).collect();
        u.sort();
        (k.defn.clone(), u)
    }

    /// 区域の札の定義名（route_goal.count 用。top なら場の札の下にある札を除く）
    pub fn zone_names(&self, z: &str, owner: i64, top: bool) -> Vec<String> {
        let cids = &self.s.zones[z][owner as usize];
        let below: std::collections::HashSet<i64> = if top && z == "bz" {
            cids.iter().flat_map(|&c| self.s.cards[c as usize].under.iter().copied()).collect()
        } else { Default::default() };
        cids.iter().filter(|c| !below.contains(c)).map(|&c| self.s.cards[c as usize].defn.clone()).collect()
    }

    pub fn skel_raw(&self) -> Value {
        let name = |c: i64| self.s.cards[c as usize].defn.clone();
        let turn = self.s.turn;
        let bz: Vec<Value> = self.bz_tops(None).iter().map(|&c| {
            let k = &self.s.cards[c as usize];
            json!([k.controller, k.defn, k.tapped, k.entered_turn == turn, k.under.iter().map(|&u| name(u)).collect::<Vec<_>>()])
        }).collect();
        let cont: Vec<Value> = self.s.continuous.iter().map(|ce| {
            let names: Vec<String> = ce["affected"].as_array().map(|a| a.iter().filter(|r| self.alive(r))
                .map(|r| name(r[0].as_i64().unwrap())).collect()).unwrap_or_default();
            json!([ce["mod"], ce["duration"], names, ce.get("filter").cloned().unwrap_or(Value::Null)])
        }).collect();
        let tasks: Vec<Value> = self.s.tasks.iter().map(|t| json!([t["t"], t.get("phase").cloned().unwrap_or(Value::Null),
            t.get("pc").cloned().unwrap_or(Value::Null), t.get("i").cloned().unwrap_or(Value::Null), t.get("sub").cloned().unwrap_or(Value::Null)])).collect();
        let mut zones = serde_json::Map::new();
        for (z, zd) in &self.rules.zones {
            if zd.shared || z == "hold" {
                continue;
            }
            zones.insert(z.clone(), json!([self.zl(z, 0).iter().map(|&c| name(c)).collect::<Vec<_>>(),
                                           self.zl(z, 1).iter().map(|&c| name(c)).collect::<Vec<_>>()]));
        }
        let mut bundles = vec![];
        let mut under_n = vec![];
        let mut mana_un = vec![];
        for p in 0..2i64 {
            bundles.push(Value::Array(self.zl("shield", p).iter().filter(|&&c| !self.s.cards[c as usize].under.is_empty())
                .map(|&c| json!([name(c), self.s.cards[c as usize].under.iter().map(|&u| name(u)).collect::<Vec<_>>()])).collect()));
            under_n.push(self.zl("shield", p).iter().map(|&c| self.s.cards[c as usize].under.len()).sum::<usize>());
            mana_un.push(self.zl("mana", p).iter().filter(|&&c| !self.s.cards[c as usize].tapped).count());
        }
        json!({"active": self.s.active, "step": self.s.step, "turn": turn, "bz": bz,
            "pending": self.s.pending.iter().map(|p| json!([p["kind"], p["defn"], p["ab"], p["controller"], p["win"]])).collect::<Vec<_>>(),
            "cont": cont, "hold": self.s.hold.iter().map(|&c| name(c)).collect::<Vec<_>>(), "tasks": tasks,
            "waiting": self.s.waiting.clone(), "delayed": self.s.delayed.clone(), "step_mods": self.s.step_mods.clone(),
            "zones": zones, "bundles": bundles, "under": under_n, "mana_untapped": mana_un,
            "mana": (0..2i64).flat_map(|p| self.zl("mana", p).iter().map(|&c| json!([name(c), self.s.cards[c as usize].tapped])).collect::<Vec<_>>()).collect::<Vec<_>>(),
            "bz_n": [self.s.zones["bz"][0].len(), self.s.zones["bz"][1].len()]})
    }

    /// パワー（特性の power。Python の chars(cid)["power"]）
    fn power(&self, cid: i64) -> i64 {
        self.chars(cid, None).power
    }

    /// chars の allow リストそのもの（Python の chars["allow"] と同じ並び）。
    /// 攻撃対象の拡大（combat.py の allow 辞書の直接参照）でも使う
    fn allow_entries(&self, cid: i64) -> Vec<Value> {
        self.chars(cid, None).allow
    }

    fn chars_json(&self, cid: i64) -> Value {
        let d = self.def(cid);
        let ch = self.chars(cid, None);
        let mut out = json!({"power": ch.power, "cost": d.cost, "civs": d.civs,
            "types": if ch.sealed { json!([]) } else { json!(d.types) }, "races": if ch.sealed { json!([]) } else { json!(d.races) },
            "keywords": ch.keywords, "name": d.name, "names": [d.name], "allow": ch.allow, "deny": ch.deny, "require": ch.require,
            "breaks": ch.breaks, "break_opts": ch.break_opts, "breaks_add": ch.breaks_add, "pay_cost": ch.pay_cost,
            "sac_reduce": 0, "opt_reduce": null, "cost_may": [], "no_leave": [],
            "must_be_attacked": false, "must_be_attacked_first": false, "must_be_chosen": false, "must_attack_creature": false,
            "must_attack_creature_first": false, "battle_indestructible": false, "win_all_battles": ch.win_all_battles,
            "crystal_soul": 0, "mana_number": 0});
        if !ch.sealed {
            out["battle_indestructible_filters"] = json!([]);
            out["indestructible"] = json!(false);
        }
        out
    }

    /// バトル中だけのパワー修整（Python の combat._battle_bonus）。見るのはそのクリーチャー自身の常在型だけ
    fn battle_bonus(&self, r: &Value, attacking: bool, opponent: &Value) -> i64 {
        let cid = r[0].as_i64().unwrap();
        let c = &self.s.cards[cid as usize];
        let env = json!({"you": c.controller, "self": r.clone(), "vars": {}});
        let zone = c.zone.clone();
        let mut total = 0;
        for ab in &self.fdef(cid, None).abil {
            if ab["kind"] != json!("static") {
                continue;
            }
            let bp = match ab.get("mod").and_then(|m| m.get("battle_power")) {
                Some(bp) => bp,
                None => continue,
            };
            if let Some(cond) = ab.get("if") {
                if !self.eval_static_cond(cond, &env) {
                    continue;
                }
            }
            if bp.get("only").and_then(|v| v.as_str()) == Some("attacking") && !attacking {
                continue;
            }
            if let Some(of) = bp.get("opponent_filter") {
                if !self.filter_ok(opponent[0].as_i64().unwrap(), of).unwrap_or(false) {
                    continue;
                }
            }
            if ab.get("affects").and_then(|v| v.as_str()) != Some("self") {
                continue;
            }
            if ab.get("zone").and_then(|v| v.as_str()).unwrap_or("bz") != zone {
                continue;
            }
            let amount = bp.get("amount").and_then(|v| v.as_i64()).unwrap_or(0);
            total += amount * match bp.get("count") {
                Some(cnt) => self.count_of(cnt, &env),
                None => 1,
            };
        }
        total
    }

    fn game_lose(&mut self, loser: i64, reason: &str) {
        if self.s.result.is_none() {
            self.s.result = Some(json!({"winner": 1 - loser, "reason": reason, "turn": self.s.turn}));
        }
    }

    /// バトル（701.13）: パワー（バトル中修整込み）で勝敗。全てのバトルに勝つ特性があればパワー無関係に勝つ
    fn battle(&mut self, x: &Value, y: &Value) -> R<()> {
        let (xc, yc) = (x[0].as_i64().unwrap(), y[0].as_i64().unwrap());
        let px = self.power(xc) + self.battle_bonus(x, true, y);
        let py = self.power(yc) + self.battle_bonus(y, false, x);
        let (xw, yw) = (self.chars(xc, None).win_all_battles, self.chars(yc, None).win_all_battles);
        let mut losers: Vec<&Value> = vec![];
        if xw && yw {
            // 両方とも全てのバトルに勝つ: 負けは無い
        } else if xw {
            losers.push(y);
        } else if yw {
            losers.push(x);
        } else {
            if px <= py {
                losers.push(x);
            }
            if py <= px {
                losers.push(y);
            }
        }
        let slay: Vec<Value> = losers
            .iter()
            .filter(|r| self.permits(r[0].as_i64().unwrap(), "slayer"))
            .map(|r| json!([r, if *r == x { y } else { x }]))
            .collect();
        let mut evs: Vec<Value> = losers
            .iter()
            .map(|r| json!({"ev": "move", "subject": r, "to": "graveyard", "reason": "destroy", "battle": true}))
            .collect();
        for r in [x, y] {
            if !losers.contains(&r) {
                let c = self.s.cards[r[0].as_i64().unwrap() as usize].controller;
                evs.push(json!({"ev": "battle_win", "subject": r, "opponent": if r == x { y } else { x }, "controller": c}));
            }
        }
        // 「バトルに負けた時」（Python #463）: 破壊の移動より前に拾い、同じ窓の終わりに解決する
        let lose_evs: Vec<Value> = losers.iter().map(|r| {
            let c = self.s.cards[r[0].as_i64().unwrap() as usize].controller;
            json!({"ev": "battle_lose", "subject": r, "opponent": if *r == x { y } else { x }, "controller": c})
        }).collect();
        let e = self.ev_task(evs);
        let mut inner = vec![];
        if !lose_evs.is_empty() {
            inner.push(self.ev_task(lose_evs));
        }
        inner.push(e);
        let mut ts = self.window(inner);
        if !slay.is_empty() {
            ts.extend(self.window(vec![json!({"t": "slayer", "pairs": slay})]));
        }
        let (cx, cy) = (self.s.cards[xc as usize].controller, self.s.cards[yc as usize].controller);
        ts.push(self.ev_task(vec![
            json!({"ev": "battle_end", "subject": x, "opponent": y, "controller": cx}),
            json!({"ev": "battle_end", "subject": y, "opponent": x, "controller": cy}),
        ]));
        self.push(ts);
        Ok(())
    }

    /// look: true の時の選択肢（Python の _card_option(c, look=True): 山札・シールドでも名前を見せる）
    fn card_option_look(&self, cid: i64) -> Value {
        let c = &self.s.cards[cid as usize];
        json!({"cid": cid, "key": format!("{}:{}:{}", c.zone, c.defn, c.tapped as i32), "name": self.rules.cards[&c.defn].name.clone()})
    }

    fn card_option(&self, cid: i64, key: Option<String>) -> Value {
        let c = &self.s.cards[cid as usize];
        let hidden = c.zone == "shield" || c.zone == "deck";
        let k = key.unwrap_or_else(|| if hidden { c.zone.clone() } else { format!("{}:{}:{}", c.zone, c.defn, c.tapped as i32) });
        json!({"cid": cid, "key": k, "name": if hidden { "?".to_string() } else { self.rules.cards[&self.s.cards[cid as usize].defn].name.clone() }})
    }

    /// ブレイク（509.3〜509.5）。置換・S・トリガー・S・バックは能力を持つカードだけなので plain では空振り
    fn h_break(&mut self) -> R<Option<Value>> {
        let (victim, by, ph) = {
            let t = self.s.tasks.last().unwrap();
            (t["victim"].as_i64().unwrap(), t["by"].as_i64().unwrap(), t["phase"].as_i64().unwrap())
        };
        if ph == 0 {
            let shields = self.zl("shield", victim).clone();
            let n = (self.s.tasks.last().unwrap()["count"].as_i64().unwrap() as usize).min(shields.len());
            let opts: Vec<Value> = shields.iter().map(|&c| json!({"cid": c, "key": "shield", "name": "?"})).collect();
            let ans = match self.ask(by, "choose_shields", opts, n, n) {
                Ask::Decision(d) => return Ok(Some(d)),
                Ask::Answer(x) => x,
            };
            let chosen: Vec<i64> = ans.iter().map(|&i| shields[i]).collect();
            self.tset("chosen", json!(chosen));
            self.tset("phase", json!(1));
            return Ok(None);
        }
        if ph == 1 {
            let t = self.s.tasks.last().unwrap();
            let fire = t.get("fire_break").and_then(|v| v.as_bool()).unwrap_or(true);
            if fire && t.get("brk_done").is_none() {
                // ブレイクの置換の諮問: 候補なし。印だけ残す
                let chosen = t["chosen"].clone();
                let n = chosen.as_array().unwrap().len();
                let t = self.s.tasks.last_mut().unwrap();
                t["brk_list"] = chosen;
                t["brk_i"] = json!(n);
                t["brk_p"] = json!(0);
                t["brk_cancelled"] = json!([]);
                t["brk_done"] = json!(true);
            }
            let ch: Vec<i64> = self.s.tasks.last().unwrap()["chosen"].as_array().unwrap().iter().map(|v| v.as_i64().unwrap()).collect();
            let victim_p = victim;
            let task_st = self.s.tasks.last().unwrap().get("strigger").and_then(|v| v.as_str()).map(|s| s.to_string());
            let mut opts: Vec<Value> = vec![];
            // シールドの束は、重なったカードのどれも宣言できる（113.2。Python の h_break と同じ）
            let mut pool: Vec<i64> = vec![];
            for &c in &ch {
                pool.push(c);
                pool.extend(self.s.cards[c as usize].under.iter().copied());
            }
            for c in pool {
                let (off, on, defn) = {
                    let k = &self.s.cards[c as usize];
                    (k.strigger_off, k.strigger_on, k.defn.clone())
                };
                for fi in self.face_list(c) {
                    let mut ok = self.permits_face(c, "s_trigger", fi);
                    if task_st.as_deref() == Some("off") || off {
                        ok = false;   // S・トリガーの印（使用不可）: この移動で手札に加わるカード／印つきのカードは宣言できない
                    } else if task_st.as_deref() == Some("on") || on {
                        // S・トリガーの印（付与）: 実行可能な種別の面なら宣言できる
                        let fd = self.fdef(c, fi);
                        ok = ok || fd.types.iter().any(|t| t == "creature") || fd.types.iter().any(|t| t == "spell");
                    }
                    if ok {
                        match fi {
                            None => opts.push(json!({"key": format!("strigger:{}", defn), "cid": c})),
                            Some(f) => opts.push(json!({"key": format!("strigger:{}:{}", defn, f), "cid": c, "face": f})),
                        }
                    }
                }
            }
            let mut declared: Vec<Value> = vec![];
            if !opts.is_empty() {
                let n = opts.len();
                let ans = match self.ask(victim_p, "declare_strigger", opts.clone(), 0, n) {
                    Ask::Decision(d) => return Ok(Some(d)),
                    Ask::Answer(x) => x,
                };
                let mut seen: Vec<i64> = vec![];
                for i in ans {
                    let cid = opts[i]["cid"].as_i64().unwrap();
                    if !seen.contains(&cid) {
                        seen.push(cid);
                        declared.push(json!([cid, opts[i].get("face").cloned().unwrap_or(Value::Null)]));
                    }
                }
            }
            self.tset("declared", json!(declared));
            self.tset("phase", json!(2));
            return Ok(None);
        }
        // phase 2: S・バックなし → 手札へ
        let tk = self.s.tasks.pop().unwrap();
        let chosen: Vec<i64> = tk["chosen"].as_array().unwrap().iter().map(|v| v.as_i64().unwrap()).filter(|&c| self.s.cards[c as usize].zone == "shield").collect();
        let reason = tk.get("reason").and_then(|v| v.as_str()).unwrap_or("break").to_string();
        let task_st = tk.get("strigger").and_then(|v| v.as_str()).map(|s| s.to_string());
        let mut seq = vec![self.ev_task(chosen.iter().map(|&c| {
            let mut e = json!({"ev": "move", "subject": self.refv(c), "to": "hand", "reason": reason});
            if let Some(st) = &task_st {
                e["strigger"] = json!(st);   // 印は移動の適用時に手札のカードへ付く（Python の h_break と同じ）
            }
            e
        }).collect())];
        seq.push(json!({"t": "enqueue_st", "cids": tk["declared"], "player": victim, "strigger": true}));
        let fire = tk.get("fire_break").and_then(|v| v.as_bool()).unwrap_or(true);
        if fire && !chosen.is_empty() {
            let mut ev = json!({"ev": "break", "player": victim, "count": chosen.len()});
            let br = tk.get("breaker").cloned().unwrap_or(Value::Null);
            if !br.is_null() && self.alive(&br) {
                ev["subject"] = br.clone();
                let cur = self.s.turn_counters.get("current_attack").cloned().unwrap_or(json!(0));
                self.s.turn_counters.insert(format!("broke_in:{}", br[0].as_i64().unwrap()), cur.clone());
                // 第185弾: その攻撃中にそのクリーチャーがブレイクした枚数（Python 側 h_break と同じキー）
                let k = format!("broke_count:{}:atk{}", br[0].as_i64().unwrap(), cur.as_i64().unwrap_or(0));
                let v = self.s.turn_counters.get(&k).and_then(|v| v.as_i64()).unwrap_or(0) + chosen.len() as i64;
                self.s.turn_counters.insert(k, json!(v));
            }
            seq.push(self.ev_task(vec![ev]));
        }
        if tk.get("in_effect").and_then(|v| v.as_bool()).unwrap_or(false) {
            // S・トリガーの解決中のブレイクは、新しい S・トリガーをその場で解決する（101.4g）
            self.s.seq += 1;
            let w = self.s.seq;
            let mut v = vec![json!({"t": "open_win", "win": w})];
            v.extend(seq);
            v.push(json!({"t": "resolve_pending", "win": w, "only_st": true}));
            v.push(json!({"t": "close_win"}));
            seq = v;
        }
        self.push(seq);
        Ok(None)
    }

    fn st_end(&mut self) -> R<Option<Value>> {
        let sub = self.s.tasks.last().unwrap()["sub"].as_i64().unwrap();
        if sub == 0 {
            self.s.tasks.last_mut().unwrap()["sub"] = json!(1);
            let t = self.ev_task(vec![json!({"ev": "turn_end", "player": self.s.active})]);
            self.push(vec![t]);
            return Ok(None);
        }
        self.expire("end_of_turn")?;   // 511.2
        self.step_done();
        Ok(None)
    }

    // ---- マナの支払いの組（Python 版 _mana_choices と同じ列挙順） ----
    pub fn mana_choices(&self, cid: i64, p: i64, cost: Option<i64>, limit: usize) -> Vec<Vec<i64>> {
        self.mana_choices_f(cid, p, None, cost, limit)
    }
    fn mana_choices_f(&self, cid: i64, p: i64, face: Option<i64>, cost: Option<i64>, limit: usize) -> Vec<Vec<i64>> {
        let d = self.fdef(cid, face);
        // 実効コストは特性の支払いコスト（pay_cost）で見る（Python の _mana_choices: max(0, eff + pay_cost - 印刷コスト)）
        let eff = (cost.unwrap_or(d.cost) + self.chars(cid, face).pay_cost - d.cost).max(0);
        let need: Vec<String> = d.civs.clone();
        if eff == 0 && need.is_empty() {
            return vec![vec![]];
        }
        let untapped: Vec<i64> = self.zl("mana", p).iter().copied().filter(|&c| !self.s.cards[c as usize].tapped).collect();
        let total_mana: i64 = untapped.iter().map(|&c| self.def(c).mana).sum();
        if (untapped.len() as i64) < d.civs.len() as i64 || total_mana < eff {
            return vec![];
        }
        let mut groups: BTreeMap<(String, bool, Vec<String>), Vec<i64>> = BTreeMap::new();
        let mut order: Vec<(String, bool, Vec<String>)> = vec![];
        for &c in &untapped {
            let k = &self.s.cards[c as usize];
            let civkey: Vec<String> = if k.face_down {
                vec![]
            } else {
                let mut v = self.def(c).civs.clone();
                v.sort();
                v
            };
            let key = (k.defn.clone(), k.face_down, civkey);
            if !groups.contains_key(&key) {
                order.push(key.clone());
            }
            groups.entry(key).or_default().push(c);
        }
        // 山はマナゾーンでの初出順（Python 版の pools と同じ。第212弾で並べ替えをやめた）
        let names: Vec<&(String, bool, Vec<String>)> = order.iter().collect();
        let mana: Vec<i64> = names.iter().map(|n| self.rules.cards[&n.0].mana).collect();
        let mut out: Vec<Vec<i64>> = vec![];

        fn civ_ok(names: &[&(String, bool, Vec<String>)], cnt: &[i64], need: &[String]) -> bool {
            let mut civsets: Vec<&Vec<String>> = vec![];
            for (n, &k) in names.iter().zip(cnt.iter()) {
                for _ in 0..k {
                    civsets.push(&n.2);
                }
            }
            fn rec(j: usize, need: &[String], civsets: &[&Vec<String>], used: &mut Vec<bool>) -> bool {
                if j == need.len() {
                    return true;
                }
                for i in 0..civsets.len() {
                    if !used[i] && civsets[i].contains(&need[j]) {
                        used[i] = true;
                        if rec(j + 1, need, civsets, used) {
                            return true;
                        }
                        used[i] = false;
                    }
                }
                false
            }
            let mut used = vec![false; civsets.len()];
            rec(0, need, &civsets, &mut used)
        }

        #[allow(clippy::too_many_arguments)]
        fn dfs(i: usize, cnt: &mut Vec<i64>, total: i64, zeros: i64, eff: i64, names: &[&(String, bool, Vec<String>)], mana: &[i64],
               groups: &BTreeMap<(String, bool, Vec<String>), Vec<i64>>, need: &[String], limit: usize, out: &mut Vec<Vec<i64>>) {
            if out.len() >= limit {
                return;
            }
            if i == names.len() {
                if total == eff && civ_ok(names, cnt, need) {
                    let mut v = vec![];
                    for (n, &k) in names.iter().zip(cnt.iter()) {
                        v.extend(groups[*n].iter().take(k as usize).copied());
                    }
                    out.push(v);
                }
                return;
            }
            let cap = groups[names[i]].len() as i64;
            let bound = if mana[i] != 0 { (eff - total).div_euclid(mana[i]) } else { need.len() as i64 - zeros };
            let mut k = cap.min(bound);
            while k >= 0 {
                cnt.push(k);
                dfs(i + 1, cnt, total + k * mana[i], zeros + if mana[i] == 0 { k } else { 0 }, eff, names, mana, groups, need, limit, out);
                cnt.pop();
                k -= 1;
            }
        }

        fn floor_dfs(i: usize, cnt: &mut Vec<i64>, left: i64, names: &[&(String, bool, Vec<String>)],
                     groups: &BTreeMap<(String, bool, Vec<String>), Vec<i64>>, need: &[String], limit: usize, out: &mut Vec<Vec<i64>>) {
            if out.len() >= limit {
                return;
            }
            if i == names.len() {
                if left == 0 && civ_ok(names, cnt, need) {
                    let mut v = vec![];
                    for (n, &k) in names.iter().zip(cnt.iter()) {
                        v.extend(groups[*n].iter().take(k as usize).copied());
                    }
                    out.push(v);
                }
                return;
            }
            let mut k = (groups[names[i]].len() as i64).min(left);
            while k >= 0 {
                cnt.push(k);
                floor_dfs(i + 1, cnt, left - k, names, groups, need, limit, out);
                cnt.pop();
                k -= 1;
            }
        }

        let mut cnt = vec![];
        if (eff as usize) < need.len() {
            floor_dfs(0, &mut cnt, need.len() as i64, &names, &groups, &need, limit, &mut out);
        } else {
            dfs(0, &mut cnt, 0, 0, eff, &names, &mana, &groups, &need, limit, &mut out);
        }
        out
    }

    // ---- イベント ----
    fn h_event(&mut self) -> R<Option<Value>> {
        // 置換効果の決定（609.9a）: まずターン・プレイヤーが束の全イベントについて決め、次に非ターン・プレイヤー。決め終えたら同時に適用する。
        // G・リンクの離脱置換は plain では起きない
        let order = [self.s.active, 1 - self.s.active];
        {
            // Python の G・リンク離脱の走査が残す印（対局が途中で終わると digest に出る）
            let t = self.s.tasks.last_mut().unwrap();
            let n = t["evs"].as_array().unwrap().len();
            if t.get("link_chosen").is_none() {
                t["link_chosen"] = json!([]);
            }
            if n > 0 {
                t["link_i"] = json!(n);
            }
        }
        loop {
            let (rp, i, n) = {
                let t = self.s.tasks.last().unwrap();
                (t["rp"].as_i64().unwrap(), t["i"].as_i64().unwrap() as usize, t["evs"].as_array().unwrap().len())
            };
            if rp >= 2 {
                break;
            }
            if i >= n {
                let t = self.s.tasks.last_mut().unwrap();
                t["i"] = json!(0);
                t["rp"] = json!(rp + 1);
                continue;
            }
            let (ev, skipped) = {
                let t = self.s.tasks.last().unwrap();
                (t["evs"][i].clone(), t["skip"].as_array().unwrap().contains(&json!(i)))
            };
            if !ev.get("replaced").and_then(|v| v.as_bool()).unwrap_or(false) && !skipped {
                match self.replacement(&ev, order[rp as usize])? {
                    Ok(Some(child)) => {
                        let t = self.s.tasks.last_mut().unwrap();
                        t["skip"].as_array_mut().unwrap().push(json!(i));
                        t["instead"].as_array_mut().unwrap().push(child);
                    }
                    Ok(None) => {}
                    Err(d) => return Ok(Some(d)),
                }
            }
            self.s.tasks.last_mut().unwrap()["i"] = json!(i + 1);
        }
        let (has_instead, applying) = {
            let t = self.s.tasks.last().unwrap();
            (!t["instead"].as_array().unwrap().is_empty(), t["applying"].as_bool().unwrap_or(false))
        };
        if has_instead && !applying {
            // 置換後のイベントを集めてから、束と同時に適用する（609.9）
            let t = self.s.tasks.last_mut().unwrap();
            t["applying"] = json!(true);
            let inst = t["instead"].as_array().unwrap().clone();
            self.push(inst);
            return Ok(None);
        }
        let t = self.s.tasks.pop().unwrap();
        let skip = t["skip"].as_array().unwrap().clone();
        let mut evs: Vec<Value> = t["evs"].as_array().unwrap().iter().enumerate()
            .filter(|(k, _)| !skip.contains(&json!(*k))).map(|(_, e)| e.clone()).collect();
        evs.extend(t["captured"].as_array().unwrap().iter().cloned());
        self.apply_batch(evs)?;
        Ok(None)
    }

    /// 適用前のイベントを、置換の照合用レコードにする（Python 版 _record_for の move の部分）
    fn record_for(&self, ev: &Value) -> Option<Value> {
        if ev["ev"] == json!("draw") {
            return Some(json!({"ev": "draw", "player": ev["player"]}));
        }
        if ev["ev"] != json!("move") || !self.alive(&ev["subject"]) {
            return None;
        }
        let cid = ev["subject"][0].as_i64().unwrap();
        let c = &self.s.cards[cid as usize];
        let from = if c.zone == "hold" { ev.get("from").cloned().unwrap_or(Value::Null) } else { json!(c.zone) };
        let mut rec = json!({"ev": "move", "subject": ev["subject"], "from": from, "to": ev["to"], "reason": ev["reason"], "controller": c.controller});
        for k in ["cause", "cause_defn"] {
            if ev.get(k).map_or(false, |v| v.as_str().map_or(false, |x| !x.is_empty())) {
                rec[k] = ev[k].clone();
            }
        }
        if ev.get("cause_defn").map_or(false, |v| v.as_str().map_or(false, |x| !x.is_empty())) {
            rec["cause_kind"] = ev["cause_kind"].clone();
        }
        if let Some(b) = ev.get("by") {
            rec["by"] = b.clone();
        }
        if ev.get("unpaid").and_then(|v| v.as_bool()).unwrap_or(false) {
            rec["unpaid"] = json!(true);
        }
        if ev.get("stack_on").map_or(false, |v| !v.is_null()) {
            rec["stacked"] = json!(true);   // 進化として重なった移動（Python の _record_for と同じ）
        }
        if let Some(v) = ev.get("via") {
            if !v.is_null() {
                rec["via"] = v.clone();
            }
        }
        if c.zone == "bz" && c.top_of >= 0 && c.seal_of < 0 {
            // 下にあったカードが単独で動く: 宿主の移動直前の姿を載せる（from_under 照合用）
            let h = c.top_of;
            let hc = &self.s.cards[h as usize];
            rec["host"] = self.refv(h);
            rec["host_lki"] = json!({"defn": hc.defn, "face": hc.face, "controller": hc.controller, "zone": "bz", "tapped": hc.tapped,
                "chars": self.chars_json(h), "ref": self.refv(h)});
        }
        Some(rec)
    }

    /// プレイヤー p の置換効果の選択（Python 版 _replacement）。Ok(None): 置換なし / Ok(Some(task)): 置換後に実行する効果 / Err: 決定待ち
    fn replacement(&mut self, ev: &Value, p: i64) -> R<Result<Option<Value>, Value>> {
        let rec = match self.record_for(ev) {
            Some(r) => r,
            None => return Ok(Ok(None)),
        };
        let mut srcs = self.bz_tops(Some(p));
        if let Some(subj) = ev.get("subject").filter(|v| !v.is_null()) {
            if self.alive(subj) {
                let sc = subj[0].as_i64().unwrap();
                if self.s.cards[sc as usize].controller == p && !srcs.contains(&sc) {
                    srcs.push(sc);
                }
            }
        }
        for &x in self.zl("shield", p).clone().iter() {
            if !srcs.contains(&x) {
                srcs.push(x);
            }
        }
        let mut cands: Vec<(i64, usize, Value)> = vec![];
        for src in srcs {
            let zone = self.s.cards[src as usize].zone.clone();
            let ctrl = self.s.cards[src as usize].controller;
            let abil = self.def(src).abil.clone();
            for (i, ab) in abil.iter().enumerate() {
                if ab["kind"] != json!("replace") {
                    continue;
                }
                if zone != "bz" && ab.get("zone").and_then(|v| v.as_str()) != Some(zone.as_str()) {
                    continue;
                }
                if !self.when_match(&ab["when"], &rec, &self.refv(src), ctrl) {
                    continue;
                }
                if let Some(cond) = ab.get("if") {
                    let env = json!({"you": ctrl, "self": self.refv(src), "event": rec, "vars": {}});
                    if !self.eval_cond(cond, &env)? {
                        continue;
                    }
                }
                cands.push((src, i, ab.clone()));
            }
        }
        if cands.is_empty() {
            return Ok(Ok(None));
        }
        let opts: Vec<Value> = cands.iter()
            .map(|(s_, i, _)| json!({"key": format!("replace:{}:{}", self.s.cards[*s_ as usize].defn, i), "cid": s_, "ab": i})).collect();
        let ans = match self.ask(p, "choose_replacement", opts.clone(), 1, 1) {
            Ask::Decision(d) => return Ok(Err(d)),
            Ask::Answer(x) => x,
        };
        let (src, _, ab) = &cands[ans[0]];
        let env = json!({"you": self.s.cards[*src as usize].controller, "self": self.refv(*src), "event": rec,
            "vars": {}, "no_replace": true, "capture": true});
        Ok(Ok(Some(json!({"t": "effect", "ops": ab["instead"], "pc": 0, "env": env, "os": {}}))))
    }

    fn apply_batch(&mut self, evs: Vec<Value>) -> R<()> {
        if !evs.is_empty() && !evs.iter().any(|e| e.get("sba").and_then(|v| v.as_bool()).unwrap_or(false)) {
            self.s.sba_held.clear();
        }
        let mut records: Vec<Value> = vec![];
        for ev in &evs {
            records.extend(self.apply_one(ev)?);
        }
        for r in &records {
            if r["ev"] == json!("break") {
                let k = format!("broken:{}", r["player"].as_i64().unwrap());
                let n = self.s.turn_counters.get(&k).and_then(|v| v.as_i64()).unwrap_or(0) + r.get("count").and_then(|v| v.as_i64()).unwrap_or(0);
                self.s.turn_counters.insert(k, json!(n));
            }
        }
        self.record_history(&mut records);
        self.sba()?;
        for r in records.iter_mut() {
            self.collect_triggers(r);
        }
        Ok(())
    }

    /// 移動元つきの履歴カウンタ（Python 版 _hist_bump_from。hist:<kind>_from_<zone>:<player>）
    fn hist_bump_from(&mut self, kind: &str, frm: &str, player: i64) {
        if !frm.is_empty() {
            self.hist_bump(&format!("{}_from_{}", kind, frm), player, 1);
        }
    }
    fn hist_bump(&mut self, kind: &str, player: i64, n: i64) -> i64 {
        let k = format!("hist:{}:{}", kind, player);
        let v = self.s.turn_counters.get(&k).and_then(|v| v.as_i64()).unwrap_or(0) + n;
        self.s.turn_counters.insert(k, json!(v));
        v
    }

    fn push_list(&mut self, k: String, v: i64) {
        let mut l = self.s.turn_counters.get(&k).and_then(|v| v.as_array().cloned()).unwrap_or_default();
        l.push(json!(v));
        self.s.turn_counters.insert(k, Value::Array(l));
    }

    /// 履歴カウンタ（Python 版 _record_history。ここで扱うのは plain の対戦で起きる種類だけ）
    fn record_history(&mut self, records: &mut [Value]) {
        for rec in records.iter_mut() {
            match rec["ev"].as_str().unwrap_or("") {
                "move" => {
                    let ctrl = if rec["lki"].is_null() { rec["controller"].as_i64().unwrap() } else { rec["lki"]["controller"].as_i64().unwrap() };
                    let rc = rec["controller"].as_i64().unwrap();
                    let (frm, to) = (rec["from"].as_str().unwrap_or("").to_string(), rec["to"].as_str().unwrap_or("").to_string());
                    let (frm, to) = (frm.as_str(), to.as_str());
                    if to == "shield" {
                        self.hist_bump("shield_put", rc, 1);
                        self.hist_bump_from("shield_put", frm, rc);
                    }
                    let has_host = rec.get("host").map_or(false, |v| !v.is_null());
                    if frm == "shield" && to != "shield" && !has_host {
                        self.hist_bump("shield_left", ctrl, 1);
                    }
                    if to == "mana" {
                        let n = self.hist_bump("mana_put", rc, 1);
                        self.hist_bump_from("mana_put", frm, rc);
                        rec["ord"] = json!({"mana_put": n});
                    }
                    if to == "bz" {
                        let n = self.hist_bump("enter", rc, 1);
                        self.hist_bump_from("enter", frm, rc);
                        rec["ord"] = json!({"enter": n});
                        if rec.get("unpaid").and_then(|v| v.as_bool()).unwrap_or(false) {
                            self.hist_bump("enter_unpaid", rc, 1);
                        }
                    }
                    if frm == "bz" && to != "bz" && !has_host {   // 下にあったカードはクリーチャーとして離れた数に入れない
                        self.hist_bump("leave", ctrl, 1);
                        if to == "graveyard" && rec["reason"] == json!("destroy") {
                            self.hist_bump("destroyed", ctrl, 1);
                        }
                    }
                    if to == "graveyard" && rec["reason"] == json!("discard") {
                        self.hist_bump("discard", ctrl, 1);
                        self.hist_bump_from("discard", frm, ctrl);
                    }
                }
                "summon" => {
                    let n = self.hist_bump("summon", rec["controller"].as_i64().unwrap(), 1);
                    rec["ord"] = json!({"summon": n});
                }
                "draw" => {
                    let n = self.hist_bump("draw", rec["player"].as_i64().unwrap(), 1);
                    rec["ord"] = json!({"draw": n});
                }
                "break" => {
                    let cnt = rec.get("count").and_then(|v| v.as_i64()).unwrap_or(1);
                    self.hist_bump("broken", rec["player"].as_i64().unwrap(), cnt);
                    if let Some(s) = rec.get("subject") {
                        if !s.is_null() {
                            let k = format!("hist:broke_by:{}", s[0].as_i64().unwrap());
                            let v = self.s.turn_counters.get(&k).and_then(|v| v.as_i64()).unwrap_or(0) + cnt;
                            self.s.turn_counters.insert(k, json!(v));
                        }
                    }
                }
                "attack" => {
                    let a = rec["controller"].as_i64().unwrap();
                    let att = rec["subject"][0].as_i64().unwrap();
                    let n = self.hist_bump("attack", a, 1);
                    self.push_list(format!("hist:attackers:{}", a), att);
                    let k = format!("hist:attack_by:{}", att);
                    let v = self.s.turn_counters.get(&k).and_then(|v| v.as_i64()).unwrap_or(0) + 1;
                    self.s.turn_counters.insert(k, json!(v));
                    rec["ord"] = json!({"attack": n, "attack_by": v});
                    if let Some(tg) = rec["target"].as_array() {
                        let k2 = format!("hist:attack_on:{}", tg[0].as_i64().unwrap());
                        let v = self.s.turn_counters.get(&k2).and_then(|v| v.as_i64()).unwrap_or(0) + 1;
                        self.s.turn_counters.insert(k2, json!(v));
                    }
                }
                "cast" => {
                    let p = rec["player"].as_i64().unwrap();
                    let n = self.hist_bump("cast", p, 1);
                    rec["ord"] = json!({"cast": n});
                    if let Some(c) = rec["subject"][0].as_i64() {
                        let d = self.def(c);
                        let snap = json!({"cost": d.cost, "types": d.types, "civs": d.civs});
                        let k = format!("hist:used:{}", p);
                        let e = self.s.turn_counters.entry(k).or_insert(json!([]));
                        e.as_array_mut().unwrap().push(snap);
                    }
                }
                "block" => { self.hist_bump("block", rec["controller"].as_i64().unwrap(), 1); }
                "tap" => { self.hist_bump("tap", rec["controller"].as_i64().unwrap(), 1); }
                "untap" => {
                    // 状態が実際に変わったアンタップだけ。場のクリーチャーは untap_creature も数える（マナのアンタップを除く）
                    let p = rec["controller"].as_i64().unwrap();
                    self.hist_bump("untap", p, 1);
                    let uc = rec["subject"][0].as_i64().unwrap();
                    if self.alive(&rec["subject"]) && self.s.cards[uc as usize].zone == "bz" && self.def(uc).types.iter().any(|t| t == "creature") {
                        self.hist_bump("untap_creature", p, 1);
                    }
                }
                _ => {}
            }
        }
    }

    /// 適用して、生まれたレコードを返す
    fn apply_one(&mut self, ev: &Value) -> R<Vec<Value>> {
        let kind = ev["ev"].as_str().unwrap_or("");
        match kind {
            "draw" => {
                let p = ev["player"].as_i64().unwrap();
                let deck = &self.s.zones["deck"][p as usize];
                if deck.is_empty() {
                    return Ok(vec![]);
                }
                let cid = deck[0];
                self.raw_move(cid, "hand", "top", None);
                self.s.cards[cid as usize].drawn_turn = self.s.turn;
                let k = format!("drew:{}", p);
                let n = self.s.turn_counters.get(&k).and_then(|v| v.as_i64()).unwrap_or(0) + 1;
                self.s.turn_counters.insert(k, json!(n));
                let r = self.refv(cid);
                Ok(vec![
                    json!({"ev": "draw", "player": p, "subject": r}),
                    json!({"ev": "move", "subject": r, "lki": null, "from": "deck", "to": "hand", "reason": "draw", "controller": p}),
                ])
            }
            "tap" | "untap" => {
                if !self.alive(&ev["subject"]) {
                    return Ok(vec![]);
                }
                let cid = ev["subject"][0].as_i64().unwrap();
                let c = &mut self.s.cards[cid as usize];
                if c.tapped == (kind == "tap") {
                    return Ok(vec![]);
                }
                c.tapped = kind == "tap";
                Ok(vec![json!({"ev": kind, "subject": ev["subject"], "controller": c.controller})])
            }
            "move" => {
                if !self.alive(&ev["subject"]) {
                    return Ok(vec![]);
                }
                let cid = ev["subject"][0].as_i64().unwrap();
                let to = ev["to"].as_str().unwrap_or("");
                let czone = self.s.cards[cid as usize].zone.clone();
                let from = if czone == "hold" { ev["from"].as_str().unwrap_or("").to_string() } else { czone.clone() };
                let reason = ev.get("reason").and_then(|v| v.as_str()).unwrap_or("");
                let ctl_before = self.s.cards[cid as usize].controller;
                let (tapped_before, gen_before, face_before) = {
                    let c = &self.s.cards[cid as usize];
                    (c.tapped, c.gen, c.face)
                };
                let chars_before = self.chars_json(cid);
                let defn_before = self.s.cards[cid as usize].defn.clone();
                // hold（召喚・唱えの途中）からの移動も、置換（instead）で行き先が変わる場合を含めて
                // Python の _apply_one と同じく通常の移動として適用する（旧ガードは subject 参照の
                // 置換を塞いでいた。行き先はイベントの指定どおり）
                if to == "bz" && czone != "hold" && !self.permits(cid, "enter_bz") {
                    return Ok(vec![]);   // 出せない（効果で出す場合はここで止まる）
                }
                let ctl = if to == "bz" && czone == "hold" && reason == "summon" { Some(ev["controller"].as_i64().unwrap()) } else { None };
                let pos = ev.get("position").and_then(|v| v.as_str()).unwrap_or("top").to_string();
                // このカード自身が他のカードの下にあった場合の宿主（移動直前の姿。from_under 照合用）
                let host = {
                    let c = &self.s.cards[cid as usize];
                    if from == "bz" && c.top_of >= 0 && c.seal_of < 0 {
                        let h = c.top_of;
                        let hc = &self.s.cards[h as usize];
                        Some((self.refv(h), json!({"defn": hc.defn, "face": hc.face, "controller": hc.controller, "zone": "bz",
                            "tapped": hc.tapped, "chars": self.chars_json(h), "ref": self.refv(h)})))
                    } else { None }
                };
                let was_face_up = self.s.cards[cid as usize].face_up;   // 移動前の表向き状態（紋章・face_up 照合用）
                let unders: Vec<i64> = self.s.cards[cid as usize].under.clone();
                let under_lkis: Vec<(i64, Value)> = if from == "bz" && to != "bz" {
                    unders.iter().map(|&u| {
                        let uc = &self.s.cards[u as usize];
                        (u, json!({"defn": uc.defn, "face": uc.face, "controller": uc.controller, "zone": from, "tapped": uc.tapped,
                            "chars": self.chars_json(u), "ref": self.refv(u), "face_up": uc.face_up}))
                    }).collect()
                } else { vec![] };
                self.raw_move(cid, to, &pos, ctl);
                for &u in &unders {   // クリーチャーとして離れたら下のカードも同じゾーンへ（109.2b）
                    if self.s.cards[u as usize].zone == "bz" || self.s.cards[u as usize].top_of == cid {
                        self.raw_move(u, to, "top", None);
                    }
                }
                // 進化: 進化元（超無限墓地進化は墓地から）を重ねる
                let mut evo_bases: Vec<i64> = vec![];
                if let Some(so) = ev.get("stack_on").filter(|v| !v.is_null()) {
                    if to == "bz" && self.alive(so) {
                        let base = so[0].as_i64().unwrap();
                        if self.s.cards[base as usize].zone != "bz" {
                            self.raw_move(base, "bz", "top", None);
                        }
                        self.stack(cid, base, false);
                        if ev.get("evolution").is_some() {
                            evo_bases.push(base);
                        }
                        for x in ev.get("stack_more").and_then(|v| v.as_array()).cloned().unwrap_or_default() {
                            if !self.alive(&x) {
                                continue;
                            }
                            let xc = x[0].as_i64().unwrap();
                            if self.s.cards[xc as usize].zone == "graveyard" {
                                self.raw_move(xc, "bz", "top", None);
                            }
                            if self.s.cards[xc as usize].zone == "bz" {
                                self.stack(cid, xc, true);
                                if ev.get("evolution").is_some() {
                                    evo_bases.push(xc);
                                }
                            }
                        }
                    }
                }
                if to == "bz" && self.chars(cid, None).keywords.iter().any(|k| k == "enters_tapped") {
                    self.s.cards[cid as usize].tapped = true;   // タップしてバトルゾーンに出る（特性のキーワードで見る。Python の events と同じ）
                }
                if ev.get("tapped").and_then(|v| v.as_bool()).unwrap_or(false) {
                    self.s.cards[cid as usize].tapped = true;   // 「タップして置く」
                }
                if ev.get("sst").and_then(|v| v.as_bool()).unwrap_or(false) {
                    self.s.cards[cid as usize].sst = true;
                }
                if ev.get("stp").and_then(|v| v.as_bool()).unwrap_or(false) {
                    self.s.cards[cid as usize].stp = true;
                }
                if ev.get("face_up").and_then(|v| v.as_bool()).unwrap_or(false) && to == "shield" {
                    self.s.cards[cid as usize].face_up = true;   // 表向きでシールドに置く（Python の _apply_one と同じ）
                    self.note_public("face_up", cid);
                }
                if ev.get("face_down").and_then(|v| v.as_bool()).unwrap_or(false) && to == "mana" {
                    self.s.cards[cid as usize].face_down = true;   // 裏向きでマナに置く（Python の _apply_one と同じ）
                }
                if to == "hand" {
                    if let Some(st) = ev.get("strigger").and_then(|v| v.as_str()) {
                        if st == "off" || st == "on" {
                            // S・トリガーの印（バンドC2 U68）: 手札に加わったカード（束の下のカードも含む）に付ける
                            let mut targets = vec![cid];
                            for &u in &unders {
                                if self.s.cards[u as usize].zone == "hand" {
                                    targets.push(u);
                                }
                            }
                            for u in targets {
                                if st == "off" {
                                    self.s.cards[u as usize].strigger_off = true;
                                } else {
                                    self.s.cards[u as usize].strigger_on = true;
                                }
                            }
                        }
                    }
                }
                if let Some(st) = ev.get("summon_tapped").and_then(|v| v.as_array()) {
                    if !st.is_empty() {
                        self.s.cards[cid as usize].summon_tapped = st.iter()
                            .map(|e| json!({"ref": e["ref"].clone(), "races": e.get("races").cloned().unwrap_or(json!([]))})).collect();
                    }
                }
                let after = self.s.cards[cid as usize].controller;
                let mut out = vec![json!({"ev": "move", "subject": self.refv(cid), "lki": {"defn": defn_before, "face": face_before, "controller": ctl_before, "zone": from, "tapped": tapped_before,
                        "chars": chars_before, "ref": [cid, gen_before], "exlife_of": null}, "from": from, "to": to,
                    "reason": reason, "controller": after})];
                if ev.get("unpaid").and_then(|v| v.as_bool()).unwrap_or(false) {
                    out[0]["unpaid"] = json!(true);
                }
                if ev.get("face_up").and_then(|v| v.as_bool()).unwrap_or(false) || (from == "shield" && was_face_up) {
                    out[0]["face_up"] = json!(true);   // 表向きで置かれた／表向きのシールドが離れた（Python の _apply_one と同じ）
                }
                if from == "shield" && was_face_up && !unders.is_empty() {
                    out[0]["emblem"] = json!(true);   // 裁きの紋章: シールドの上に表向きに置かれていたカード
                }
                if ev.get("stack_on").map_or(false, |v| !v.is_null()) {
                    out[0]["stacked"] = json!(true);
                }
                if let Some(v) = ev.get("via") {
                    if !v.is_null() {
                        out[0]["via"] = v.clone();   // 「革命チェンジで出た」等の経緯（Python の _apply_one と同じ伝播）
                    }
                }
                for k in ["cause", "cause_defn", "cause_kind"] {
                    if let Some(v) = ev.get(k) {
                        if v.as_str().map_or(false, |x| !x.is_empty()) {
                            out[0][k] = v.clone();
                        }
                    }
                }
                if let Some(b) = ev.get("by") {
                    if !b.is_null() {
                        out[0]["by"] = b.clone();
                    }
                }
                if to == "bz" {
                    self.push_list(format!("entered:{}", after), cid);
                    if self.def(cid).races.iter().any(|r| r.contains("コマンド")) {
                        // コマンドが出た時、同じ文明の自身のカードから封印を1つ墓地に置く
                        let civs = self.def(cid).civs.clone();
                        self.s.tasks.push(json!({"t": "seal_release", "player": after, "civs": civs}));
                    }
                }
                if reason == "summon" {
                    out.push(json!({"ev": "summon", "subject": self.refv(cid), "controller": after, "player": after,
                        "unpaid": ev.get("unpaid").and_then(|v| v.as_bool()).unwrap_or(false)}));
                }
                for b in evo_bases {   // 「進化元になる時」: 進化元を subject、出たクリーチャーを top とする合成レコード
                    out.push(json!({"ev": "evolve_base", "subject": self.refv(b), "top": self.refv(cid), "controller": self.s.cards[b as usize].controller}));
                }
                if let Some((h, hl)) = host {
                    out[0]["host"] = h;
                    out[0]["host_lki"] = hl;
                }
                let lki0 = out[0]["lki"].clone();
                for (u, ul) in under_lkis {
                    // 一緒に離れた下のカードにも move レコード（宿主の移動直前の姿を host / host_lki に載せる）
                    if self.s.cards[u as usize].zone != to {
                        continue;
                    }
                    let mut r = json!({"ev": "move", "subject": self.refv(u), "lki": ul, "from": from, "to": to, "reason": reason,
                        "controller": ul["controller"], "host": lki0["ref"], "host_lki": lki0});
                    if from == "shield" && ul["face_up"].as_bool().unwrap_or(false) {
                        r["emblem"] = json!(true);   // 束の下にいた表向きのカードも裁きの紋章
                    }
                    for k in ["cause", "cause_defn", "cause_kind"] {
                        if let Some(v) = ev.get(k) {
                            if v.as_str().map_or(false, |x| !x.is_empty()) {
                                r[k] = v.clone();
                            }
                        }
                    }
                    if let Some(b) = ev.get("by") {
                        if !b.is_null() {
                            r["by"] = b.clone();
                        }
                    }
                    out.push(r);
                }
                Ok(out)
            }
            "cast" | "turn_start" | "turn_end" | "attack" | "block" | "battle_start" | "battle_win" | "battle_lose" | "battle_end" | "attack_end" | "break" => {
                Ok(vec![ev.clone()])
            }
            other => uns(format!("event {}", other)),
        }
    }

    /// 山札の最後の1枚が離れた瞬間を記録する（104.2b）
    fn note_deck(&mut self, cid: i64) {
        let c = &self.s.cards[cid as usize];
        if c.zone == "deck" && self.s.zones["deck"][c.owner as usize].is_empty() && !self.s.deck_emptied.contains(&c.owner) {
            let o = c.owner;
            self.s.deck_emptied.push(o);
        }
    }

    /// イベントを通さない移動（Python 版 _raw_move の、plain の対戦で通る部分）
    /// 進化: base（とその下）を top の下に重ねる（801.1, 801.2）。more は2枚目以降の進化元
    fn stack(&mut self, top: i64, base: i64, more: bool) {
        let old = self.refv(base);
        let bunder = self.s.cards[base as usize].under.clone();
        let btapped = self.s.cards[base as usize].tapped;
        let mut nu = if more { self.s.cards[top as usize].under.clone() } else { vec![] };
        nu.push(base);
        nu.extend(bunder);
        for &u in &nu {
            self.s.cards[u as usize].top_of = top;
        }
        self.s.cards[base as usize].under.clear();
        let t = &mut self.s.cards[top as usize];
        t.under = nu;
        t.tapped = if more { t.tapped || btapped } else { btapped };
        t.entered_turn = -1;
        let new = self.refv(top);
        for ce in self.s.continuous.iter_mut() {
            if let Some(a) = ce["affected"].as_array_mut() {
                if a.contains(&old) {
                    a.push(new.clone());
                }
            }
        }
        for t_ in self.s.tasks.iter_mut() {   // 攻撃中のクリーチャーが進化しても攻撃は続く（801.2a）
            if t_["t"] == json!("attack") && t_["attacker"] == old {
                t_["attacker"] = new.clone();
            }
        }
    }

    /// 公開イベントを s.pub に追記する（Python の note_public と同じ。cid つきの形だけ）
    fn note_public(&mut self, kind: &str, cid: i64) {
        let (gen, defn, owner, zone) = {
            let c = &self.s.cards[cid as usize];
            (c.gen, c.defn.clone(), c.owner, c.zone.clone())
        };
        let idx = match self.s.zones.get(&zone) {
            Some(z) => {
                let lst = if self.shared(&zone) { &z[0] } else { &z[owner as usize] };
                lst.iter().position(|&x| x == cid).map_or(-1, |i| i as i64)
            }
            None => -1,
        };
        let n = self.s.r#pub.len() as i64;
        let turn = self.s.turn;
        self.s.r#pub.push(json!({"n": n, "turn": turn, "kind": kind, "viewers": [0, 1], "cid": cid, "gen": gen,
                                 "defn": defn, "owner": owner, "zone": zone, "idx": idx}));
    }

    fn raw_move(&mut self, cid: i64, to: &str, position: &str, controller: Option<i64>) {
        {
            let tp = self.s.cards[cid as usize].top_of;
            if tp >= 0 {   // 下のカードだけが動く時は、上のカードの under から外す（メテオバーン等）
                self.s.cards[tp as usize].under.retain(|&x| x != cid);
            }
        }
        let (owner, from) = {
            let c = &self.s.cards[cid as usize];
            (c.owner as usize, c.zone.clone())
        };
        let idx = if self.shared(&from) { 0 } else { owner };
        if from == "hold" {
            self.s.hold.retain(|&x| x != cid);
        } else {
            let lst = self.s.zones.get_mut(&from).unwrap();
            if let Some(pos) = lst[idx].iter().position(|&x| x == cid) {
                lst[idx].remove(pos);
            }
        }
        if from != "hold" && !(to == "deck" && from == "deck") {
            self.note_deck(cid);
        }
        let multi = self.rules.cards[&self.s.cards[cid as usize].defn].civs.len() > 1;
        let twin = !self.rules.cards[&self.s.cards[cid as usize].defn].faces.is_empty();
        let public = self.rules.zone(to).public;
        {
            let turn = self.s.turn;
            if to == "bz" {
                self.s.seq += 1;
            }
            let seq = self.s.seq;
            let c = &mut self.s.cards[cid as usize];
            c.gen += 1;
            if to != "mana" {
                c.face_down = false;
            }
            if to != "hand" && (from == "hand" || from == "hold") {
                c.strigger_off = false;   // S・トリガーの印は手札にある間だけ有効（手札を離れたら消える。Python の core と同じ）
                c.strigger_on = false;
            }
            c.zone = to.to_string();
            c.tapped = to == "mana" && multi;
            c.face_up = public;
            c.controller = controller.unwrap_or(c.owner);
            c.entered_turn = if to == "bz" { turn } else { -1 };
            if to == "bz" {
                c.entered_seq = seq;
            }
            c.face = if to == "bz" && twin { 0 } else { -1 };   // ツインパクトはクリーチャー側としてバトルゾーンにある（810.4）
            c.under.clear();
            c.top_of = -1;
            c.exlife_of = None;
            c.sforce_of = None;
            c.fortifies = None;
            c.no_untap_next = false;
            c.hyper = false;
            c.sst = false;
            c.stp = false;
            c.odrive = false;
            c.odrive_civs.clear();
            c.summon_fuel.clear();
            c.summon_tapped.clear();
            c.bazurenda = 0;
            c.vivid = false;
        }
        let ordered = self.rules.zone(to).ordered;
        let didx = if self.shared(to) { 0 } else { owner };
        let dest = &mut self.s.zones.get_mut(to).unwrap()[didx];
        if ordered && position == "top" {
            dest.insert(0, cid);
        } else {
            dest.push(cid);
        }
    }

    /// 状況起因処理（plain では デッキ切れだけ）
    fn sba(&mut self) -> R<()> {
        if self.s.result.is_some() {
            return Ok(());
        }
        let mut out: Vec<i64> = self.s.deck_emptied.clone();
        for p in 0..2i64 {
            if self.s.zones["deck"][p as usize].is_empty() {
                out.push(p);
            }
        }
        out.sort();
        out.dedup();
        if !out.is_empty() {
            let loser = if out.len() == 2 { self.s.active } else { out[0] };
            self.s.result = Some(json!({"winner": 1 - loser, "reason": "deck_out", "turn": self.s.turn}));
            return Ok(());
        }
        let ts = self.sba_power_tasks();
        self.push(ts);
        Ok(())
    }

    /// パワー0以下のクリーチャーの破壊（703.4c）。破壊できずに残ったものは状態が動くまで繰り返さない（sba_held）
    fn sba_power_tasks(&mut self) -> Vec<Value> {
        if self.s.result.is_some() {
            return vec![];
        }
        let dead: Vec<Vec<i64>> = self.bz_tops(None).into_iter()
            .filter(|&c| self.def(c).types.iter().any(|t| t == "creature") && self.power(c) <= 0)
            .map(|c| vec![c, self.s.cards[c as usize].gen]).collect();
        let held: Vec<Vec<i64>> = self.s.sba_held.iter().filter(|r| dead.contains(r)).cloned().collect();
        self.s.sba_held = held;
        let dead: Vec<Vec<i64>> = dead.into_iter().filter(|r| !self.s.sba_held.contains(r)).collect();
        if dead.is_empty() {
            return vec![];
        }
        for r in &dead {
            if !self.s.sba_held.contains(r) {
                self.s.sba_held.push(r.clone());
            }
        }
        vec![self.ev_task(dead.into_iter().map(|r| json!({"ev": "move", "subject": r, "to": "graveyard", "reason": "destroy", "sba": true})).collect())]
    }

    /// 期限の切れた継続的効果を消す。修整が切れてパワー0以下になったら、その場で破壊する
    fn expire(&mut self, duration: &str) -> R<()> {
        if !self.s.delayed.is_empty() {
            return uns("expire delayed");
        }
        let n = self.s.continuous.len();
        self.s.continuous.retain(|c| c["duration"] != json!(duration));
        if self.s.continuous.len() != n {
            self.sba()?;
        }
        Ok(())
    }
}
