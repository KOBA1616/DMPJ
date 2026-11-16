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

#[derive(Clone)]
pub struct Engine {
    pub s: GameState,
    pub rules: Arc<Rules>,
    pub log: Vec<Value>,
    pub step_limit: i64,
    pub turn_limit: i64,
    /// 常在型の条件を評価中の深さ（Python の _in_static_cond。2段目からはフィルタが印刷の特性を見る）
    pub static_depth: SDepth,
}

enum Ask {
    Answer(Vec<usize>),
    Decision(Value),
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
        Ok(Engine { s, rules, log: vec![], step_limit: 20000, turn_limit: 80, static_depth: SDepth::default() })
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
        if self.s.cards[cid as usize].zone == "bz" {
            for e in &self.def(cid).deny_x {
                if e["action"] == json!(action) && self.filter_ok(other, &e["other"]).unwrap_or(false) {
                    return false;
                }
            }
        }
        self.permits(cid, action)
    }
    /// 継続的効果が cid に及ぶか（Python の _ce_applies）。範囲固定は affected、dynamic は生成時にベイクした filter
    fn ce_applies(&self, ce: &Value, cid: i64) -> bool {
        if let Some(a) = ce["affected"].as_array() {
            return a.contains(&self.refv(cid));
        }
        let f = &ce["filter"];
        let c = &self.s.cards[cid as usize];
        if f["zone"].as_str() != Some(c.zone.as_str()) {
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
    /// 条件を満たしている「条件つきの自分への禁止」（バトルゾーンにある間）
    fn cond_deny(&self, cid: i64, face: Option<i64>) -> Vec<String> {
        let d = self.fdef(cid, face);
        if d.deny_if.is_empty() || self.s.cards[cid as usize].zone != "bz" {
            return vec![];
        }
        let env = json!({"you": self.s.cards[cid as usize].controller, "self": self.refv(cid), "vars": {}});
        self.static_depth.set(self.static_depth.get() + 1);
        let out = d.deny_if.iter().filter(|(c, _)| self.eval_cond(c, &env).unwrap_or(false)).flat_map(|(_, l)| l.clone()).collect();
        self.static_depth.set(self.static_depth.get() - 1);
        out
    }
    /// 継続的効果の mod の allow / deny に action があるか
    fn ce_lists(&self, cid: i64, key: &str) -> Vec<String> {
        let mut out = vec![];
        for ce in &self.s.continuous {
            if let Some(l) = ce["mod"].get(key).and_then(|v| v.as_array()) {
                if self.ce_applies(ce, cid) {
                    out.extend(l.iter().filter_map(|x| x.as_str().map(String::from)));
                }
            }
        }
        out
    }
    fn permits_face(&self, cid: i64, action: &str, face: Option<i64>) -> bool {
        if face.is_none() && !self.s.continuous.is_empty() && self.ce_lists(cid, "deny").iter().any(|x| x == action) {
            return false;   // 101.2:「できない」は「できる」に勝つ
        }
        if self.s.cards[cid as usize].zone == "shield" {
            // シールドゾーンで働く自身への許可（S・トリガー）
            if self.fdef(cid, face).shield_allow.iter().any(|x| x == action) {
                return true;
            }
        }
        if self.s.cards[cid as usize].zone == "bz" {
            let d = self.fdef(cid, face);
            if d.deny.iter().any(|x| x == action) {
                return false;
            }
            if self.cond_deny(cid, face).iter().any(|x| x == action) {
                return false;
            }
            if d.allow.iter().any(|x| x == action) {
                return true;
            }
        }
        if face.is_none() && !self.s.continuous.is_empty() && self.ce_lists(cid, "allow").iter().any(|x| x == action) {
            return true;
        }
        *self.rules.actions.get(action).unwrap_or(&false)
    }
    /// バトルゾーンにある間のブレイク数の候補（509.2c）。能力が無ければ [1]
    fn break_opts(&self, cid: i64) -> Vec<i64> {
        let mut v: Vec<i64> = self.def(cid).breaks.clone();
        v.extend(self.granted_breaks(cid));
        v.sort();
        v.dedup();
        if v.is_empty() { vec![1] } else { v }
    }
    /// 継続的効果で与えられたキーワード（印刷のキーワードに無いもの、名前順）。Python の chars の granted
    fn granted_kw(&self, cid: i64) -> Vec<String> {
        let mut out: Vec<String> = vec![];
        if self.s.continuous.is_empty() {
            return out;
        }
        let d = self.def(cid);
        for ce in &self.s.continuous {
            if let Some(l) = ce["mod"].get("grant").and_then(|v| v.as_array()) {
                if self.ce_applies(ce, cid) {
                    out.extend(l.iter().filter_map(|x| x.as_str()).filter(|x| !d.keywords.iter().any(|k| k == x)).map(String::from));
                }
            }
        }
        out.sort();
        out.dedup();
        out
    }
    /// 与えられたブレイカーのブレイク数（バトルゾーンにある間だけ働く）
    fn granted_breaks(&self, cid: i64) -> Vec<i64> {
        if self.s.cards[cid as usize].zone != "bz" {
            return vec![];
        }
        self.granted_kw(cid).iter().filter_map(|k| match k.as_str() { "double_breaker" => Some(2), "triple_breaker" => Some(3), _ => None }).collect()
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
            let zone = sel["zone"].as_str().unwrap_or("");
            if !["hand", "deck", "graveyard", "mana", "bz", "shield"].contains(&zone) {
                return uns(format!("cands zone {}", zone));
            }
            lst = vec![];
            for p in players {
                let mut part = if zone == "bz" { self.bz_tops(Some(p)) } else { self.zl(zone, p).clone() };
                if let Some(n) = sel.get("from_top") {
                    match n.as_i64() {
                        Some(n) => part.truncate(n.max(0) as usize),
                        None => return uns("from_top expr"),
                    }
                }
                lst.extend(part);
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

    /// フィルタの値が式（{cost_of: ...} など）なら解決時に数へ置き換える（Python の select と同じ前評価）
    fn bake_filter(&self, f: &Value, env: &Value) -> R<Value> {
        let o = match f.as_object() { Some(o) => o, None => return Ok(f.clone()) };
        if !o.values().any(|v| v.is_object()) {
            return Ok(f.clone());
        }
        let mut out = serde_json::Map::new();
        for (k, v) in o {
            out.insert(k.clone(), if v.is_object() { json!(self.eval_num(v, env)?) } else { v.clone() });
        }
        Ok(Value::Object(out))
    }

    fn eval_num(&self, x: &Value, env: &Value) -> R<i64> {
        if let Some(n) = x.as_i64() {
            return Ok(n);
        }
        if let Some(v) = x.get("cost_of") {
            // 参照カード（複数なら最大）のコスト。参照は変数名か {ref: 名前}、"self" は自分
            let name = v.get("ref").and_then(|r| r.as_str()).or(v.as_str()).unwrap_or("");
            let refs: Vec<Value> = if name == "self" { vec![env["self"].clone()] }
                else if name.starts_with("event.") || name == "crossed" { return uns("cost_of ref"); }
                else { env["vars"].get(name).and_then(|a| a.as_array()).cloned().unwrap_or_default() };
            return Ok(refs.iter().filter_map(|r| r[0].as_i64()).map(|c| self.def(c).cost).max().unwrap_or(0));
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
            if !["zone", "owner", "count", "from_top", "filter", "chooser", "look", "ref", "up_to", "other", "under_of"].contains(&k.as_str()) {
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
        if let Some(u) = sel.get("under_of") {
            // 「このクリーチャーの下にあるカード」（メテオバーン）
            if u != &json!("self") {
                return uns("under_of");
            }
            let me = env["self"].clone();
            lst = if self.alive(&me) { self.s.cards[me[0].as_i64().unwrap() as usize].under.clone() } else { vec![] };
        } else if let Some(name) = sel.get("ref").and_then(|v| v.as_str()) {
            if name == "self" || name == "self_moved" || name == "self_entered" || name == "crossed" || name == "subject" || name.starts_with("event.") {
                return uns("selector ref");
            }
            let refs: Vec<Value> = env["vars"].get(name).and_then(|v| v.as_array()).cloned().unwrap_or_default();
            lst = refs.iter().filter(|r| self.alive(r)).map(|r| r[0].as_i64().unwrap()).collect();
        } else {
            // owner any: ターン・プレイヤーから順に両者（114.2a）
            let players: Vec<i64> = match sel.get("owner").and_then(|v| v.as_str()).unwrap_or("you") {
                "you" => vec![you],
                "opp" => vec![1 - you],
                "any" => vec![self.s.active, 1 - self.s.active],
                _ => return uns("selector owner"),
            };
            let zone = sel["zone"].as_str().unwrap_or("");
            if !["hand", "deck", "graveyard", "mana", "bz", "shield"].contains(&zone) {
                return uns(format!("selector zone {}", zone));
            }
            lst = vec![];
            for p in players {
                let mut part = if zone == "bz" { self.bz_tops(Some(p)) } else { self.zl(zone, p).clone() };
                if let Some(n) = sel.get("from_top") {
                    let n = match n.as_i64() {
                        Some(n) => n.max(0) as usize,
                        None => return uns("from_top expr"),
                    };
                    part.truncate(n);
                }
                lst.extend(part);
            }
            if sel.get("other").and_then(|v| v.as_bool()).unwrap_or(false) {
                if let Some(me) = env.get("self").and_then(|v| v.as_array()) {
                    let m = me[0].as_i64().unwrap();
                    lst.retain(|&c| c != m);
                }
            }
        }
        if let Some(f) = &filter {
            let mut keep = vec![];
            for &c in &lst {
                if self.filter_ok(c, f)? {
                    keep.push(c);
                }
            }
            lst = keep;
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
            "opp" => 1 - you,
            _ => return uns("chooser"),
        };
        let cands: Vec<i64> = lst
            .into_iter()
            .filter(|&c| {
                let k = &self.s.cards[c as usize];
                k.zone != "bz" || k.controller == chooser || self.permits(c, "be_chosen")
            })
            .collect();
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

    /// フィルタの照合（Python 版 filter_match の、plain の札で値が定義どおりになるキーだけ。他は Unsupported）
    /// フィルタが見るパワー: 特性（継続的効果・条件つき修整込み）。常在型の条件の入れ子（2段目以降）では印刷のパワー
    fn filter_power(&self, cid: i64) -> i64 {
        if self.static_depth.get() > 1 { self.def(cid).power } else { self.power(cid) }
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
                "keyword" => d.keywords.iter().any(|x| Some(x.as_str()) == v.as_str()),
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

    fn play_options(&self, p: i64) -> Vec<Value> {
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
        for c in self.bz_tops(Some(a)) {
            let k = &self.s.cards[c as usize];
            if k.tapped || (k.entered_turn == turn && !self.permits(c, "attack_summoning_sick")) {
                continue;
            }
            let dfn = k.defn.clone();
            if self.permits(c, "attack_player") {
                opts.push(json!({"key": format!("attack:{}:player", dfn), "cid": c, "target": "player"}));
            }
            for tc in self.bz_tops(Some(1 - a)) {
                if self.s.cards[tc as usize].tapped && self.permits(c, "attack_creature") && self.permits_vs(tc, "be_attacked", c) {
                    opts.push(json!({"key": format!("attack:{}:{}", dfn, self.s.cards[tc as usize].defn), "cid": c, "target": self.refv(tc)}));
                }
            }
        }
        opts.push(json!({"key": "pass"}));
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
                !self.s.cards[c as usize].tapped && self.permits(c, "block") && self.permits_vs(attc, "be_blocked", c)
                    && json!([c, self.s.cards[c as usize].gen]) != target
            }).collect();
            let guards: Vec<i64> = if target == json!("player") { vec![] } else {
                self.bz_tops(Some(1 - a)).into_iter().filter(|&c| {
                    !self.s.cards[c as usize].tapped && json!([c, self.s.cards[c as usize].gen]) != target && self.permits(c, "guardman")
                }).collect()
            };
            let mut opts: Vec<Value> = blockers.iter().map(|&c| self.card_option(c, None)).collect();
            for &c in &guards {
                opts.push(self.card_option(c, Some(format!("guard:{}", self.s.cards[c as usize].defn))));
            }
            opts.push(json!({"key": "no_block"}));
            let ans = match self.ask(1 - a, "block", opts.clone(), 1, 1) {
                Ask::Decision(d) => return Ok(Some(d)),
                Ask::Answer(x) => x,
            };
            self.tset("phase", json!(3));
            let o = opts[ans[0]].clone();
            if o["key"] != json!("no_block") {
                let c = o["cid"].as_i64().unwrap();
                let was_tapped = self.s.cards[c as usize].tapped;
                let r = self.refv(c);
                self.tset("target", r.clone());
                if o["key"].as_str().unwrap().starts_with("guard:") {
                    if !was_tapped {
                        let te = self.ev_task(vec![json!({"ev": "tap", "subject": r})]);
                        self.push(vec![te]);
                    }
                    return Ok(None);
                }
                self.tset("blocked", json!(true));
                let rec = json!({"ev": "block", "subject": r, "attacker": att, "controller": 1 - a});
                let e = self.ev_task(vec![rec.clone()]);
                self.push(vec![e, Self::decl(a, "block", &rec), Self::decl(1 - a, "block", &rec)]);
                if !was_tapped {   // 第190弾: ブロック宣言のタップも tap イベント（block より先に実行）
                    let te = self.ev_task(vec![json!({"ev": "tap", "subject": r})]);
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
                } else {
                    // Python は空でも _defer する（pc+1）ので、h_effect の「_defer していなければ次へ」でさらに pc+1 され、次の op をとばす。
                    // 基準の Python に合わせる（Python 側の不具合。直すなら両方同時に）
                    let t = self.s.tasks.last_mut().unwrap();
                    t["pc"] = json!(pc as i64 + 2);
                    t["os"] = json!({});
                }
                deferred = true;
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
                let out_tasks: Vec<Value> = owners.iter().map(|&o| {
                    let cs: Vec<i64> = shield_out.iter().copied().filter(|&c| self.s.cards[c as usize].controller == o).collect();
                    json!({"t": "break", "victim": o, "by": env["you"], "count": cs.len(), "phase": 1, "chosen": cs,
                           "in_effect": in_st, "reason": op["reason"], "fire_break": false})
                }).collect();
                let evs: Vec<Value> = cids
                    .iter()
                    .filter(|c| !shield_out.contains(c))
                    .map(|&c| {
                        let mut e = json!({"ev": "move", "subject": self.refv(c), "to": to, "reason": op["reason"], "position": pos});
                        if tapped {
                            e["tapped"] = json!(true);
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

    /// 誘発チェック（Python 版 _collect_triggers の、バトルゾーンの「出た時」「攻撃する時」だけを扱う版）
    fn collect_triggers(&mut self, rec: &mut Value) {
        self.s.ev_seq += 1;
        rec["_eid"] = json!(self.s.ev_seq);
        let win = self.s.windows.last().copied().unwrap_or(0);
        // 発生源（Python 版 _collect_triggers と同じ並び）: バトルゾーン → 他のゾーンで働く誘発の札 → 離れたカード自身（LKI）
        let mut sources: Vec<(i64, Option<Value>)> = self.bz_tops(None).into_iter().map(|c| (c, None)).collect();
        for z in self.rules.zt_zones.clone() {
            for p in 0..2i64 {
                for &c in self.zl(&z, p).clone().iter() {
                    if self.def(c).zt {
                        sources.push((c, None));
                    }
                }
            }
        }
        let lki = rec.get("lki").cloned().filter(|v| !v.is_null());
        if let Some(l) = &lki {
            let subj = rec["subject"][0].as_i64().unwrap();
            let lz = l["zone"].as_str().unwrap_or("");
            if lz == "bz" && rec.get("to").and_then(|v| v.as_str()) != Some("bz") {
                sources.push((subj, Some(l.clone())));
            } else if lz != "bz" && self.s.cards[subj as usize].zone != lz {
                sources.push((subj, Some(l.clone())));
            }
        }
        for (src, lsrc) in sources {
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
                if !self.when_match(&ab["when"], rec, src, ctrl) {
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

    /// 誘発条件の照合（Python 版 _match_when の、event / from / to / reason / player / subject: self の部分）
    fn when_match(&self, w: &Value, rec: &Value, src: i64, ctrl: i64) -> bool {
        if w["event"] != rec["ev"] {
            return false;
        }
        for k in ["from", "to", "reason"] {
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
            return false;
        }
        if let Some(pl) = w.get("player").and_then(|v| v.as_str()) {
            let want = if pl == "you" { ctrl } else { 1 - ctrl };
            if rec.get("player").and_then(|v| v.as_i64()) != Some(want) {
                return false;
            }
        }
        if let Some(sw) = w.get("subject") {
            if let Some(ow) = sw.get("owner").and_then(|v| v.as_str()) {
                // 持ち主だけの指定（バトルゾーン以外から動いたカード。Python の whitelist が保証する）: 今のコントローラーで見る
                let want = if ow == "you" { ctrl } else { 1 - ctrl };
                match rec.get("subject").and_then(|s| s[0].as_i64()) {
                    Some(c) if self.s.cards[c as usize].controller == want => {}
                    _ => return false,
                }
            } else if rec.get("subject").map_or(true, |s| s[0].as_i64() != Some(src)) {
                // subject: self
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

    /// パワー（印刷パワー＋継続的効果の修整）
    fn power(&self, cid: i64) -> i64 {
        let mut p = self.def(cid).power;
        if !self.def(cid).power_if.is_empty() && self.s.cards[cid as usize].zone == "bz" {
            let env = json!({"you": self.s.cards[cid as usize].controller, "self": self.refv(cid), "vars": {}});
            for (c, n) in &self.def(cid).power_if {
                self.static_depth.set(self.static_depth.get() + 1);
                let ok = self.eval_cond(c, &env).unwrap_or(false);
                self.static_depth.set(self.static_depth.get() - 1);
                if ok {
                    p += n;
                }
            }
        }
        if !self.s.continuous.is_empty() {
            for ce in &self.s.continuous {
                if ce["mod"].get("power").is_some() && self.ce_applies(ce, cid) {
                    p += ce["mod"].get("power").and_then(|v| v.as_i64()).unwrap_or(0);
                }
            }
        }
        p
    }

    fn chars_json(&self, cid: i64) -> Value {
        let d = self.def(cid);
        let power = self.power(cid);
        let in_bz = self.s.cards[cid as usize].zone == "bz";
        let (mut allow, mut deny, mut bo): (Vec<String>, Vec<String>, Vec<i64>) =
            if in_bz { (d.allow.clone(), d.deny.clone(), d.breaks.clone()) }
            else if self.s.cards[cid as usize].zone == "shield" { (d.shield_allow.clone(), vec![], vec![]) }   // シールドゾーンで働く自身への許可
            else { (vec![], vec![], vec![]) };
        if in_bz {
            deny.extend(self.cond_deny(cid, None));
        }
        if !self.s.continuous.is_empty() {
            allow.extend(self.ce_lists(cid, "allow"));
            deny.extend(self.ce_lists(cid, "deny"));
        }
        let deny: Vec<Value> = (if in_bz { d.deny_x.clone() } else { vec![] }).into_iter().chain(deny.iter().map(|x| json!(x))).collect();

        let gk = self.granted_kw(cid);
        if in_bz {
            bo.extend(self.granted_breaks(cid));
        }
        let breaks = bo.iter().copied().max().unwrap_or(1).max(1);
        let mut kw = d.keywords.clone();
        kw.extend(gk);
        kw.sort();
        kw.dedup();
        json!({"power": power, "cost": d.cost, "civs": d.civs, "types": d.types, "races": d.races, "keywords": kw,
            "name": d.name, "names": [d.name], "allow": (if in_bz { d.allow_x.clone() } else { vec![] }).into_iter().chain(allow.iter().map(|x| json!(x))).collect::<Vec<_>>(), "deny": deny, "require": [], "breaks": breaks, "break_opts": bo,
            "breaks_add": 0, "pay_cost": d.cost, "sac_reduce": 0, "opt_reduce": null, "cost_may": [], "no_leave": [],
            "must_be_attacked": false, "must_be_attacked_first": false, "must_be_chosen": false, "must_attack_creature": false,
            "must_attack_creature_first": false, "battle_indestructible": false, "battle_indestructible_filters": [],
            "win_all_battles": false, "indestructible": false, "crystal_soul": 0})
    }

    fn game_lose(&mut self, loser: i64, reason: &str) {
        if self.s.result.is_none() {
            self.s.result = Some(json!({"winner": 1 - loser, "reason": reason, "turn": self.s.turn}));
        }
    }

    /// バトル（701.13）: plain はパワーだけで勝敗が決まる
    fn battle(&mut self, x: &Value, y: &Value) -> R<()> {
        let (xc, yc) = (x[0].as_i64().unwrap(), y[0].as_i64().unwrap());
        let (px, py) = (self.power(xc), self.power(yc));
        let mut losers: Vec<&Value> = vec![];
        if px <= py {
            losers.push(x);
        }
        if py <= px {
            losers.push(y);
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
            let mut opts: Vec<Value> = vec![];
            for &c in &ch {
                let k = &self.s.cards[c as usize];
                if k.strigger_off || k.strigger_on {
                    return uns("strigger mark");
                }
                for fi in self.face_list(c) {
                    if self.permits_face(c, "s_trigger", fi) {
                        match fi {
                            None => opts.push(json!({"key": format!("strigger:{}", k.defn), "cid": c})),
                            Some(f) => opts.push(json!({"key": format!("strigger:{}:{}", k.defn, f), "cid": c, "face": f})),
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
        let mut seq = vec![self.ev_task(chosen.iter().map(|&c| json!({"ev": "move", "subject": self.refv(c), "to": "hand", "reason": reason})).collect())];
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
        let eff = cost.unwrap_or(d.cost).max(0);
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
        for &c in &untapped {
            let k = &self.s.cards[c as usize];
            let civkey: Vec<String> = if k.face_down {
                vec![]
            } else {
                let mut v = self.def(c).civs.clone();
                v.sort();
                v
            };
            groups.entry((k.defn.clone(), k.face_down, civkey)).or_default().push(c);
        }
        let names: Vec<&(String, bool, Vec<String>)> = groups.keys().collect();
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
                if !self.when_match(&ab["when"], &rec, src, ctrl) {
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
                    }
                    let has_host = rec.get("host").map_or(false, |v| !v.is_null());
                    if frm == "shield" && to != "shield" && !has_host {
                        self.hist_bump("shield_left", ctrl, 1);
                    }
                    if to == "mana" {
                        let n = self.hist_bump("mana_put", rc, 1);
                        rec["ord"] = json!({"mana_put": n});
                    }
                    if to == "bz" {
                        let n = self.hist_bump("enter", rc, 1);
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
                let summon_hold = to == "bz" && czone == "hold" && reason == "summon";
                let resolve_hold = czone == "hold" && ((to == "graveyard" || to == "mana" || to == "shield") && reason == "resolve" || to == "shield" && reason == "put");   // 唱え終えた呪文（スローリー・チェーンは自身をシールドへ）
                if czone == "hold" && !summon_hold && !resolve_hold {
                    return uns(format!("move {}→{}", from, to));
                }
                if to == "bz" && czone != "hold" && !self.permits(cid, "enter_bz") {
                    return Ok(vec![]);   // 出せない（効果で出す場合はここで止まる）
                }
                let ctl = if summon_hold { Some(ev["controller"].as_i64().unwrap()) } else { None };
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
                if ev.get("tapped").and_then(|v| v.as_bool()).unwrap_or(false) {
                    self.s.cards[cid as usize].tapped = true;   // 「タップして置く」
                }
                if ev.get("sst").and_then(|v| v.as_bool()).unwrap_or(false) {
                    self.s.cards[cid as usize].sst = true;
                }
                if ev.get("stp").and_then(|v| v.as_bool()).unwrap_or(false) {
                    self.s.cards[cid as usize].stp = true;
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
                if ev.get("stack_on").map_or(false, |v| !v.is_null()) {
                    out[0]["stacked"] = json!(true);
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
