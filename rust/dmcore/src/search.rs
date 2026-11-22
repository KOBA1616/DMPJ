//! 探索側のターン内展開ループ（Rust 化 増分E・段階1＋段階2）。
//!
//! Python の tools/exhaustive_crossturn.LeafCollector の収集走査（TurnSearch._search と
//! 同じ規則でターン終了の葉を全て集める処理）を写したもの。葉は Engine そのものと
//! (評価, 手順ログ, digest) のメタ情報で Python に返す。
//!
//! 段階2でループ検出（Detectors / 証明書 / verify / fast_forward / ストック）を写した。
//! params.detectors=false の場合は段階1の意味論（検出器スタブ = observe は常に None）。
//! 検出された証明書はメタ情報の certs に cert_to_dict 形（検出順）で返す。
//!
//! 範囲外（呼び出し側のゲートで委譲対象から外れる）:
//! - 局面内チェックポイント（経路ガイド再生）→ 段階3
//! - 登録簿マクロ（macro.active() が空でない場合）、value_fn、lookahead、
//!   KEEP_HAND、DRAWOUT_ORDER、既定以外の相手役、ループ発見モード（ts.collect）
//! 意味論は Python と一致させることが目的で、食い違いがあれば常にこちらを直す。

use crate::engine::{Engine, EngErr, R};
use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde_json::{json, Map, Value};
use std::cmp::Ordering;
use std::collections::{BTreeMap, HashMap, HashSet};

pub const WIN: f64 = 1e9;
const ROLLOUT_CAP: i64 = 2000; // Python の TurnSearch.rollout_cap
const INF: usize = 1_000_000_000_000;

// ---------- Python の json.dumps と同じ文字列化（区切り ", " と ": "、キーは整列） ----------

fn escape_str(s: &str, ascii: bool, out: &mut String) {
    out.push('"');
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{08}' => out.push_str("\\b"),
            '\u{0c}' => out.push_str("\\f"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c if ascii && (c as u32) > 0x7f => {
                let mut buf = [0u16; 2];
                for u in ch.encode_utf16(&mut buf) {
                    out.push_str(&format!("\\u{:04x}", u));
                }
            }
            c => out.push(c),
        }
    }
    out.push('"');
}

/// json.dumps(v, sort_keys=True) と同じ出力。ascii=true が Python の既定（ensure_ascii=True）、
/// false が abstract() の外側の dumps（ensure_ascii=False）。
pub fn py_dumps(v: &Value, ascii: bool) -> String {
    let mut out = String::new();
    dumps_into(v, ascii, &mut out);
    out
}

fn dumps_into(v: &Value, ascii: bool, out: &mut String) {
    match v {
        Value::Null => out.push_str("null"),
        Value::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        Value::Number(n) => out.push_str(&n.to_string()),
        Value::String(s) => escape_str(s, ascii, out),
        Value::Array(a) => {
            out.push('[');
            for (i, x) in a.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                dumps_into(x, ascii, out);
            }
            out.push(']');
        }
        Value::Object(m) => {
            let mut keys: Vec<&String> = m.keys().collect();
            keys.sort(); // UTF-8 のバイト順 = コードポイント順（Python の str 比較と同じ）
            out.push('{');
            for (i, k) in keys.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                escape_str(k, ascii, out);
                out.push_str(": ");
                dumps_into(&m[*k], ascii, out);
            }
            out.push('}');
        }
    }
}

/// Python の sorted() と同じ順序（同じ位置の要素は型が揃っている前提で、
/// 型が混ざる場合は決定的な順序に倒す。Python では例外になる入力）。
fn py_cmp(a: &Value, b: &Value) -> Ordering {
    fn rank(v: &Value) -> u8 {
        match v {
            Value::Null => 0,
            Value::Bool(_) => 1,
            Value::Number(_) => 2,
            Value::String(_) => 3,
            Value::Array(_) => 4,
            Value::Object(_) => 5,
        }
    }
    let (ra, rb) = (rank(a), rank(b));
    if ra != rb {
        return ra.cmp(&rb);
    }
    match (a, b) {
        (Value::Bool(x), Value::Bool(y)) => x.cmp(y),
        (Value::Number(x), Value::Number(y)) => {
            if let (Some(xi), Some(yi)) = (x.as_i64(), y.as_i64()) {
                xi.cmp(&yi)
            } else {
                x.as_f64()
                    .unwrap_or(0.0)
                    .partial_cmp(&y.as_f64().unwrap_or(0.0))
                    .unwrap_or(Ordering::Equal)
            }
        }
        (Value::String(x), Value::String(y)) => x.cmp(y),
        (Value::Array(x), Value::Array(y)) => {
            for (u, v) in x.iter().zip(y.iter()) {
                let c = py_cmp(u, v);
                if c != Ordering::Equal {
                    return c;
                }
            }
            x.len().cmp(&y.len())
        }
        (Value::Object(x), Value::Object(y)) => {
            let kx: Vec<&String> = x.keys().collect();
            let ky: Vec<&String> = y.keys().collect();
            kx.cmp(&ky)
        }
        _ => Ordering::Equal,
    }
}

fn py_sorted(mut v: Vec<Value>) -> Vec<Value> {
    v.sort_by(py_cmp);
    v
}

fn blake2b16_hex(data: &str) -> String {
    let mut h = Blake2bVar::new(16).unwrap();
    h.update(data.as_bytes());
    let mut out = [0u8; 16];
    h.finalize_variable(&mut out).unwrap();
    out.iter().map(|b| format!("{:02x}", b)).collect()
}

// ---------- 骨格ハッシュと tkey（engine.loop.abstract / _abstract_raw の写し） ----------

/// abstract(eng, "in_turn") の (ハッシュ, カウンタ)。材料は skel_raw（Python の
/// _abstract_raw が読むのと同じ欄）から取るので、結果は Python と一致する。
/// hand_keys を渡すと、手札はその名前の札だけを骨格に入れ、残りは枚数だけの
/// カウンタにする（Python の abstract の hand_keys 分岐と同じ）。
pub fn abstract_of(eng: &Engine, zones_counter: &HashMap<String, bool>) -> (String, BTreeMap<String, i64>) {
    abstract_hk(eng, zones_counter, None)
}

pub fn abstract_hk(eng: &Engine, zones_counter: &HashMap<String, bool>,
                   hand_keys: Option<&HashSet<String>>) -> (String, BTreeMap<String, i64>) {
    let r = eng.skel_raw();
    let mut skel = Map::new();
    skel.insert("active".into(), r["active"].clone());
    skel.insert("step".into(), r["step"].clone());
    skel.insert("turn".into(), r["turn"].clone());
    let bz: Vec<Value> = r["bz"]
        .as_array()
        .unwrap()
        .iter()
        .map(|b| {
            let under = py_sorted(b[4].as_array().unwrap().clone());
            json!([b[0], b[1], b[2], b[3], under])
        })
        .collect();
    skel.insert("bz".into(), Value::Array(py_sorted(bz)));
    skel.insert("pending".into(), Value::Array(py_sorted(r["pending"].as_array().unwrap().clone())));
    let cont: Vec<Value> = r["cont"]
        .as_array()
        .unwrap()
        .iter()
        .map(|c| {
            let names = py_sorted(c[2].as_array().unwrap().clone());
            json!([py_dumps(&c[0], true), c[1], names, py_dumps(&c[3], true)])
        })
        .collect();
    skel.insert("cont".into(), Value::Array(py_sorted(cont)));
    skel.insert("hold".into(), Value::Array(py_sorted(r["hold"].as_array().unwrap().clone())));
    skel.insert("tasks".into(), r["tasks"].clone());
    let w = &r["waiting"];
    if w.is_null() {
        skel.insert("waiting".into(), Value::Null);
    } else if hand_keys.is_some() {
        // hand_keys がある場合は選択肢のキーを骨格に入れない（Python と同じ）
        skel.insert("waiting".into(), json!([w["kind"], w["player"]]));
    } else {
        let keys = py_sorted(
            w["options"]
                .as_array()
                .unwrap()
                .iter()
                .map(|o| o["key"].clone())
                .collect(),
        );
        skel.insert("waiting".into(), json!([w["kind"], w["player"], keys]));
    }
    let delayed: Vec<Value> = r["delayed"]
        .as_array()
        .unwrap()
        .iter()
        .map(|d| Value::String(py_dumps(&json!([d["when"], d["effect"], d["duration"]]), true)))
        .collect();
    skel.insert("delayed".into(), Value::Array(py_sorted(delayed)));
    let step_mods: Vec<Value> = r["step_mods"]
        .as_array()
        .unwrap()
        .iter()
        .map(|m| Value::String(py_dumps(m, true)))
        .collect();
    skel.insert("step_mods".into(), Value::Array(py_sorted(step_mods)));
    let mut counters: BTreeMap<String, i64> = BTreeMap::new();
    for (z, pair) in r["zones"].as_object().unwrap() {
        let counter = zones_counter.get(z).copied().unwrap_or(false);
        for p in 0..2usize {
            let names = pair[p].as_array().unwrap();
            if counter {
                counters.insert(format!("{z}:{p}"), names.len() as i64);
            } else if z == "hand" && hand_keys.is_some() {
                let hk = hand_keys.unwrap();
                let kept: Vec<Value> = names
                    .iter()
                    .filter(|n| hk.contains(n.as_str().unwrap_or("")))
                    .cloned()
                    .collect();
                let rest = names.len() - kept.len();
                skel.insert(format!("{z}:{p}"), Value::Array(py_sorted(kept)));
                counters.insert(format!("{z}:{p}"), rest as i64);
            } else {
                skel.insert(format!("{z}:{p}"), Value::Array(py_sorted(names.clone())));
            }
        }
    }
    for p in 0..2usize {
        let b: Vec<Value> = r["bundles"][p]
            .as_array()
            .unwrap()
            .iter()
            .map(|b| {
                // Python: sorted(set(under))（並べ替えてから重複を除く）
                let mut under = py_sorted(b[1].as_array().unwrap().clone());
                under.dedup();
                json!([b[0], under])
            })
            .collect();
        skel.insert(format!("bundles:{p}"), Value::Array(py_sorted(b)));
        counters.insert(format!("under:{p}"), r["under"][p].as_i64().unwrap_or(0));
        counters.insert(
            format!("mana_untapped:{p}"),
            r["mana_untapped"][p].as_i64().unwrap_or(0),
        );
    }
    let h = blake2b16_hex(&py_dumps(&Value::Object(skel), false));
    (h, counters)
}

/// TurnSearch の tkey（骨格ハッシュ＋カウンタ＋残りマナ＋ゾーン枚数）。
/// 集合のキーとして使う文字列にする（プロセス内でのみ使うので形は任意だが、
/// ハッシュ部は Python の abstract と一致させる）。
fn tkey(eng: &Engine, zones_counter: &HashMap<String, bool>) -> String {
    let (h, ctr) = abstract_of(eng, zones_counter);
    let r = eng.skel_raw();
    let mut mana: Vec<(String, bool)> = r["mana"]
        .as_array()
        .unwrap()
        .iter()
        .map(|m| {
            (
                m[0].as_str().unwrap_or("").to_string(),
                m[1].as_bool().unwrap_or(false),
            )
        })
        .collect();
    mana.sort();
    let mut sizes: Vec<i64> = vec![];
    for p in 0..2usize {
        for z in ["hand", "shield", "graveyard", "bz"] {
            if z == "bz" {
                sizes.push(r["bz_n"][p].as_i64().unwrap_or(0));
            } else {
                sizes.push(r["zones"][z][p].as_array().map_or(0, |a| a.len()) as i64);
            }
        }
    }
    let ctr_pairs: Vec<Value> = ctr.iter().map(|(k, v)| json!([k, v])).collect();
    let mana_pairs: Vec<Value> = mana.iter().map(|(d, t)| json!([d, t])).collect();
    py_dumps(&json!([h, ctr_pairs, mana_pairs, sizes]), false)
}

// ---------- パラメータ ----------

#[derive(Clone)]
pub struct Weights {
    pub shield: f64,
    pub threat: f64,
    pub mana: f64,
    pub hand: f64,
    pub board: f64,
    pub opp_deck: f64,
    pub deck_danger: f64,
    pub max_mana: i64,
    pub deck_keep: i64,
    pub goal_card: f64,
    pub goal_dist: f64,
}

#[derive(Clone)]
pub enum Cand {
    Default,
    Stage { order: String, stage: i64 },
}

#[derive(Clone)]
pub struct Params {
    pub me: i64,
    pub budget: i64,
    pub leaf_cap: i64,
    pub combo_cap: i64,
    pub w: Weights,
    pub repeat_first: bool,
    pub charge_keep_free: bool,
    pub cand: Cand,
    pub root_log: usize,
    pub zones_counter: HashMap<String, bool>,
    // 段階2（ループ検出）。detectors=false は段階1の意味論（検出器スタブ）。
    pub detectors: bool,
    pub draw_discard: bool,
    pub burn_stock: bool,
    pub stock_offsets: Vec<i64>,
    pub stock_cap: i64,
}

fn bad(msg: String) -> EngErr {
    EngErr::Illegal(msg)
}

impl Params {
    pub fn parse(js: &str) -> R<Params> {
        let v: Value = serde_json::from_str(js).map_err(|e| bad(format!("expand params: {e}")))?;
        let g = |o: &Value, k: &str| o.get(k).cloned().unwrap_or(Value::Null);
        let fi = |o: &Value, k: &str, d: i64| g(o, k).as_i64().or_else(|| g(o, k).as_f64().map(|x| x as i64)).unwrap_or(d);
        let ff = |o: &Value, k: &str, d: f64| g(o, k).as_f64().unwrap_or(d);
        let wv = g(&v, "weights");
        let w = Weights {
            shield: ff(&wv, "shield", 100.0),
            threat: ff(&wv, "threat", 40.0),
            mana: ff(&wv, "mana", 10.0),
            hand: ff(&wv, "hand", 4.0),
            board: ff(&wv, "board", 2.0),
            opp_deck: ff(&wv, "opp_deck", 3.0),
            deck_danger: ff(&wv, "deck_danger", 60.0),
            max_mana: fi(&wv, "max_mana", 8),
            deck_keep: fi(&wv, "deck_keep", 8),
            goal_card: ff(&wv, "goal_card", 200.0),
            goal_dist: ff(&wv, "goal_dist", 40.0),
        };
        let cv = g(&v, "cand");
        let cand = if g(&cv, "mode").as_str() == Some("stage") {
            Cand::Stage {
                order: g(&cv, "order").as_str().unwrap_or("rank").to_string(),
                stage: fi(&cv, "stage", 1),
            }
        } else {
            Cand::Default
        };
        let mut zones_counter = HashMap::new();
        if let Some(m) = g(&v, "zones_counter").as_object() {
            for (k, x) in m {
                zones_counter.insert(k.clone(), x.as_bool().unwrap_or(false));
            }
        }
        let stock_offsets: Vec<i64> = g(&v, "stock_offsets")
            .as_array()
            .map(|a| a.iter().map(|x| x.as_i64().unwrap_or(0)).collect())
            .unwrap_or_else(|| vec![0, 1]);
        Ok(Params {
            me: fi(&v, "me", 0),
            budget: fi(&v, "budget", 0),
            leaf_cap: fi(&v, "leaf_cap", 0),
            combo_cap: fi(&v, "combo_cap", 6),
            w,
            repeat_first: g(&v, "repeat_first").as_bool().unwrap_or(false),
            charge_keep_free: g(&v, "charge_keep_free").as_bool().unwrap_or(true),
            cand,
            root_log: fi(&v, "root_log", 0) as usize,
            zones_counter,
            detectors: g(&v, "detectors").as_bool().unwrap_or(false),
            draw_discard: g(&v, "draw_discard").as_bool().unwrap_or(true),
            burn_stock: g(&v, "burn_stock").as_bool().unwrap_or(true),
            stock_offsets,
            stock_cap: fi(&v, "stock_cap", 8),
        })
    }
}

// ---------- 評価（leaf_eval.evaluate の RustEngine 経路＝eval_feats の式） ----------

fn evaluate(eng: &Engine, me: i64, w: &Weights) -> f64 {
    if let Some(r) = &eng.s.result {
        let winner = &r["winner"];
        if winner.as_i64() == Some(me) {
            return WIN - r["turn"].as_f64().unwrap_or(0.0);
        }
        if winner.as_i64() == Some(1 - me) {
            return -WIN;
        }
        return -WIN / 2.0;
    }
    let f = eng.eval_feats(me);
    let (sh, breaks, deck, mana, hand, board, odeck) = (f[0], f[1], f[2], f[3], f[4], f[5], f[6]);
    w.goal_card * 0.0 - w.goal_dist * 0.0 - w.shield * sh as f64
        + w.threat * breaks.min(sh + 1) as f64
        + w.mana * mana as f64
        + w.hand * hand as f64
        + w.board * board as f64
        + w.opp_deck * (40 - odeck) as f64
        - w.deck_danger * 0.max(w.deck_keep - deck) as f64
}

// ---------- 相手役（charge_only_policy）と settle ----------

fn opp_policy(d: &Value) -> Vec<i64> {
    let opts = d["options"].as_array().unwrap();
    let keys: Vec<&str> = opts.iter().map(|o| o["key"].as_str().unwrap_or("")).collect();
    if d["kind"].as_str() == Some("charge") {
        if let Some(i) = keys.iter().position(|&k| k != "pass") {
            return vec![i as i64];
        }
        if let Some(i) = keys.iter().position(|&k| k == "pass") {
            return vec![i as i64];
        }
        return vec![]; // Python では ValueError（到達しない前提）
    }
    for k in ["pass", "no_block", "no", "decline"] {
        if let Some(i) = keys.iter().position(|&x| x == k) {
            return vec![i as i64];
        }
    }
    (0..d["min"].as_i64().unwrap_or(0)).collect()
}

fn settle(eng: &mut Engine, me: i64) -> R<Option<Value>> {
    loop {
        let d = eng.advance()?;
        if d.is_none() || eng.s.active != me {
            return Ok(None);
        }
        let d = d.unwrap();
        if d["player"].as_i64() == Some(me) {
            return Ok(Some(d));
        }
        let ans = opp_policy(&d);
        eng.answer(ans)?;
    }
}

// ---------- 候補生成（turn.candidates / _rank と exhaustive_proto の段方式） ----------

fn opt_cost(eng: &Engine, o: &Value) -> i64 {
    let Some(cid) = o.get("cid").and_then(|v| v.as_i64()) else {
        return 0;
    };
    let base = &eng.rules.cards[&eng.s.cards[cid as usize].defn];
    match o.get("face").and_then(|v| v.as_i64()) {
        Some(f) if !base.faces.is_empty() => base.faces[f as usize].cost,
        _ => base.cost,
    }
}

/// turn._rank の写し（KEEP_HAND はゲートで None が保証されるので keep は常に空）。
fn rank(eng: &Engine, d: &Value, p: &Params) -> Vec<usize> {
    let opts = d["options"].as_array().unwrap();
    let kind = d["kind"].as_str().unwrap_or("");
    let player = d["player"].as_i64().unwrap_or(0);
    let mut free_now: HashSet<&str> = HashSet::new();
    if kind == "charge" && p.charge_keep_free {
        for o in eng.play_options(player) {
            if o.get("free").and_then(|v| v.as_bool()).unwrap_or(false) {
                if let Some(cid) = o.get("cid").and_then(|v| v.as_i64()) {
                    free_now.insert(eng.s.cards[cid as usize].defn.as_str());
                }
            }
        }
    }
    let mana_len = eng
        .s
        .zones
        .get("mana")
        .map(|z| z[player as usize].len())
        .unwrap_or(0) as i64;
    let key = |o: &Value| -> Vec<i64> {
        let k = o["key"].as_str().unwrap_or("");
        match kind {
            "charge" => {
                if k == "pass" {
                    vec![if mana_len >= p.w.max_mana { 0 } else { 2 }, 0]
                } else {
                    let free = match o.get("cid").and_then(|v| v.as_i64()) {
                        Some(cid) => free_now.contains(eng.s.cards[cid as usize].defn.as_str()),
                        None => false,
                    };
                    vec![1, 0, i64::from(free), -opt_cost(eng, o)]
                }
            }
            "main" => {
                if k == "pass" {
                    vec![1, 0]
                } else {
                    vec![0, -opt_cost(eng, o)]
                }
            }
            "attack" => {
                if k == "pass" {
                    vec![2, 0]
                } else {
                    vec![
                        if o.get("target").and_then(|v| v.as_str()) == Some("player") {
                            0
                        } else {
                            1
                        },
                        0,
                    ]
                }
            }
            "yes_no" => vec![if k == "yes" { 0 } else { 1 }],
            _ => {
                if matches!(k, "pass" | "decline" | "no" | "no_block") {
                    vec![1, 0]
                } else {
                    vec![0, 0]
                }
            }
        }
    };
    let keys: Vec<Vec<i64>> = opts.iter().map(|o| key(o)).collect();
    let mut idx: Vec<usize> = (0..opts.len()).collect();
    idx.sort_by(|&a, &b| keys[a].cmp(&keys[b])); // 安定ソート（Python の sorted と同じ）
    idx
}

/// 1つ選ぶ決定の同値統合キー（turn._card_sig と同じ）。
type Sig = (String, Option<(String, Vec<String>)>);

fn sig_of(eng: &Engine, o: &Value) -> Sig {
    let k = o["key"].as_str().unwrap_or("").to_string();
    if let Some(cid) = o.get("cid").and_then(|v| v.as_i64()) {
        if o.get("name").and_then(|v| v.as_str()) == Some("?") {
            let (defn, under) = eng.card_sig(cid);
            return (k, Some((defn, under)));
        }
    }
    (k, None)
}

/// itertools.combinations(order, n) と同じ順序の組み合わせ列挙（遅延評価）。
struct ComboIter<'a> {
    order: &'a [usize],
    idx: Vec<usize>,
    started: bool,
    done: bool,
}

impl<'a> ComboIter<'a> {
    fn new(order: &'a [usize], n: usize) -> Self {
        ComboIter {
            order,
            idx: (0..n).collect(),
            started: false,
            done: false,
        }
    }
    fn next_combo(&mut self) -> Option<Vec<i64>> {
        if self.done {
            return None;
        }
        let n_items = self.order.len();
        let k = self.idx.len();
        if !self.started {
            self.started = true;
            if k > n_items {
                self.done = true;
                return None;
            }
            return Some(self.idx.iter().map(|&i| self.order[i] as i64).collect());
        }
        if k == 0 {
            self.done = true;
            return None;
        }
        let mut i = k;
        loop {
            if i == 0 {
                self.done = true;
                return None;
            }
            i -= 1;
            if self.idx[i] < n_items - k + i {
                self.idx[i] += 1;
                for j in i + 1..k {
                    self.idx[j] = self.idx[j - 1] + 1;
                }
                return Some(self.idx.iter().map(|&t| self.order[t] as i64).collect());
            }
        }
    }
}

fn combo_sig(opts: &[Value], combo: &[i64]) -> Vec<String> {
    let mut s: Vec<String> = combo
        .iter()
        .map(|&i| opts[i as usize]["key"].as_str().unwrap_or("").to_string())
        .collect();
    s.sort();
    s
}

/// exhaustive_proto._enumerate の写し。single では limit を適用しない。
fn enumerate_cands(eng: &Engine, d: &Value, order: &[usize], limit: usize) -> Vec<Vec<i64>> {
    let opts = d["options"].as_array().unwrap();
    let mn = d["min"].as_i64().unwrap_or(1);
    let mx = d["max"].as_i64().unwrap_or(1);
    let mut out: Vec<Vec<i64>> = vec![];
    if mn == 1 && mx == 1 {
        let mut seen: HashSet<Sig> = HashSet::new();
        for &i in order {
            if seen.insert(sig_of(eng, &opts[i])) {
                out.push(vec![i as i64]);
            }
        }
        return out;
    }
    let mut seen: HashSet<Vec<String>> = HashSet::new();
    for n in (mn..=mx).rev() {
        let mut it = ComboIter::new(order, n as usize);
        while let Some(combo) = it.next_combo() {
            if seen.insert(combo_sig(opts, &combo)) {
                out.push(combo);
                if out.len() >= limit {
                    return out;
                }
            }
        }
    }
    out
}

/// turn.candidates の写し（DRAWOUT_ORDER はゲートで無効が保証される）。
fn candidates_default(eng: &Engine, d: &Value, p: &Params, cap: i64) -> Vec<Vec<i64>> {
    let opts = d["options"].as_array().unwrap();
    let mn = d["min"].as_i64().unwrap_or(1);
    let mx = d["max"].as_i64().unwrap_or(1);
    let order = rank(eng, d, p);
    if mn == 1 && mx == 1 {
        let mut out: Vec<Vec<i64>> = vec![];
        let mut seen: HashSet<Sig> = HashSet::new();
        for i in order {
            if seen.insert(sig_of(eng, &opts[i])) {
                out.push(vec![i as i64]);
            }
        }
        if d["kind"].as_str() == Some("pay_mana") {
            out.truncate(2);
        }
        return out;
    }
    let mut out: Vec<Vec<i64>> = vec![];
    let mut seen: HashSet<Vec<String>> = HashSet::new();
    for n in (mn..=mx).rev() {
        let mut it = ComboIter::new(&order, n as usize);
        while let Some(combo) = it.next_combo() {
            if seen.insert(combo_sig(opts, &combo)) {
                out.push(combo);
                if out.len() as i64 >= cap {
                    return out;
                }
            }
        }
    }
    out
}

/// exhaustive_proto._value_after の写し（例外は -inf）。
fn value_after(eng: &Engine, choice: &[i64], p: &Params, player: i64) -> f64 {
    let mut e2 = eng.clone();
    if e2.answer(choice.to_vec()).is_err() {
        return f64::NEG_INFINITY;
    }
    for _ in 0..400 {
        match e2.advance() {
            Ok(Some(_)) => break,
            Ok(None) => continue,
            Err(_) => return f64::NEG_INFINITY,
        }
    }
    evaluate(&e2, player, &p.w)
}

fn kind_caps(stage: i64, class: &str) -> usize {
    match (stage, class) {
        (1, "multi") | (1, "evo") => 6,
        (2, "multi") | (2, "evo") => 64,
        _ => INF,
    }
}

/// exhaustive_proto.make_candidates の写し。
fn candidates_stage(eng: &Engine, d: &Value, p: &Params, order_name: &str, stage: i64) -> Vec<Vec<i64>> {
    let n = d["options"].as_array().unwrap().len();
    let mn = d["min"].as_i64().unwrap_or(1);
    let mx = d["max"].as_i64().unwrap_or(1);
    let class = if mn == 1 && mx == 1 {
        "single"
    } else if d["kind"].as_str() == Some("choose_evo_source") {
        "evo"
    } else {
        "multi"
    };
    let eff = if class == "single" {
        INF
    } else {
        kind_caps(stage, class)
    };
    let identity: Vec<usize> = (0..n).collect();
    if order_name == "value" {
        let player = d["player"].as_i64().unwrap_or(0);
        if class == "single" {
            let base = enumerate_cands(eng, d, &identity, INF);
            let mut scored: Vec<(f64, Vec<i64>)> = base
                .into_iter()
                .map(|c| (value_after(eng, &c, p, player), c))
                .collect();
            scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(Ordering::Equal));
            return scored.into_iter().map(|x| x.1).take(eff).collect();
        }
        let combos = enumerate_cands(eng, d, &identity, 301);
        if combos.len() <= 300 {
            let mut scored: Vec<(f64, Vec<i64>)> = combos
                .into_iter()
                .map(|c| (value_after(eng, &c, p, player), c))
                .collect();
            scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(Ordering::Equal));
            return scored.into_iter().map(|x| x.1).take(eff).collect();
        }
        return combos.into_iter().take(eff).collect();
    }
    let order = if order_name == "rank" {
        rank(eng, d, p)
    } else {
        identity
    };
    enumerate_cands(eng, d, &order, eff)
}

fn candidates(eng: &Engine, d: &Value, p: &Params, rollout: bool) -> Vec<Vec<i64>> {
    match &p.cand {
        Cand::Default => candidates_default(eng, d, p, if rollout { 1 } else { p.combo_cap }),
        Cand::Stage { order, stage } => candidates_stage(eng, d, p, order, *stage),
    }
}

/// TurnSearch._repeat_order の写し（同じ種類の決定で前に選んだ意味キーの候補を先頭へ）。
fn repeat_order(eng: &Engine, d: &Value, cands: Vec<Vec<i64>>, root_log: usize) -> Vec<Vec<i64>> {
    let opts = d["options"].as_array().unwrap();
    let keys: Vec<String> = opts
        .iter()
        .map(|o| o["key"].as_str().unwrap_or("").to_string())
        .collect();
    let ks: HashSet<&str> = keys.iter().map(|s| s.as_str()).collect();
    let log = &eng.log;
    let start = root_log.min(log.len());
    for a in log[start..].iter().rev() {
        if a["kind"].as_str() != d["kind"].as_str() || a["p"].as_i64() != d["player"].as_i64() {
            continue;
        }
        let akeys: Vec<String> = a["keys"]
            .as_array()
            .map(|arr| {
                arr.iter()
                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                    .collect()
            })
            .unwrap_or_default();
        if akeys.is_empty() {
            continue;
        }
        let aset: HashSet<&str> = akeys.iter().map(|s| s.as_str()).collect();
        if !aset.is_subset(&ks) {
            continue;
        }
        let mut prev = akeys;
        prev.sort();
        let mut out = cands;
        out.sort_by_key(|ch| {
            let mut ck: Vec<String> = ch.iter().map(|&i| keys[i as usize].clone()).collect();
            ck.sort();
            ck != prev
        });
        return out;
    }
    cands
}

// ---------- ロールアウト（予算切れ後の貪欲な打ち切り） ----------

fn rollout(eng: &mut Engine, p: &Params) -> R<()> {
    let mut n: i64 = 0;
    while let Some(d) = settle(eng, p.me)? {
        n += 1;
        if n > ROLLOUT_CAP {
            eng.s.result = Some(json!({"winner": Value::Null, "reason": "step_limit", "turn": eng.s.turn}));
            break;
        }
        let cands = candidates(eng, &d, p, true);
        eng.answer(cands[0].clone())?;
    }
    Ok(())
}

// ---------- ループ検出（engine.loop / search.turn.Detectors の写し、増分E・段階2） ----------

pub const WILD_HAND: &str = "hand:*";

/// LoopCertificate の写し。Python 消費側へは to_dict（playback.cert_to_dict と
/// 同じ形）で返す。verified / notes は検出時点では 0 / 空なので dict 側もそうなる。
#[derive(Clone)]
pub struct Cert {
    pub start_skeleton: String,
    pub actions: Vec<Vec<String>>,
    pub deciders: Vec<i64>,
    pub delta: BTreeMap<String, i64>,
    pub limit: f64,
    pub period: String,
    pub win_by: Option<String>,
    pub needed: Option<i64>,
    pub hand_keys: Option<HashSet<String>>,
    pub wild: bool,
}

impl Cert {
    /// playback.cert_to_dict と同じ形（limit の inf は None、hand_keys は整列済み）。
    pub fn to_dict(&self) -> Value {
        let limit = if self.limit.is_infinite() {
            Value::Null
        } else {
            json!(self.limit as i64)
        };
        let hk: Value = match &self.hand_keys {
            Some(s) => {
                let mut v: Vec<&String> = s.iter().collect();
                v.sort();
                json!(v)
            }
            None => Value::Null,
        };
        json!({
            "start_skeleton": self.start_skeleton,
            "actions": self.actions,
            "deciders": self.deciders,
            "delta": self.delta,
            "limit": limit,
            "period": self.period,
            "win_by": self.win_by,
            "needed": self.needed,
            "verified": 0,
            "notes": [],
            "hand_keys": hk,
        })
    }
}

/// engine.loop.analyze の写し。
fn analyze(delta: &BTreeMap<String, i64>, counters: &BTreeMap<String, i64>, me: i64) -> (f64, Option<String>, Option<i64>) {
    let opp = 1 - me;
    let mut limit = f64::INFINITY;
    let suffix = format!(":{me}");
    for (k, &d) in delta {
        if d < 0 && k.ends_with(&suffix) {
            let reserve: i64 = if k.starts_with("deck:") { 1 } else { 0 };
            let v = (counters[k] - reserve).div_euclid(-d) as f64;
            if v < limit {
                limit = v;
            }
        }
    }
    let mut win_by: Option<String> = None;
    let mut needed: Option<i64> = None;
    let d_deck = delta.get(&format!("deck:{opp}")).copied().unwrap_or(0);
    if d_deck < 0 {
        let c = counters[&format!("deck:{opp}")];
        let n = -((-c).div_euclid(-d_deck));
        needed = Some(n);
        if (n as f64) <= limit {
            win_by = Some("opp_deck_out".to_string());
        }
    }
    let d_sh = delta.get(&format!("shield:{opp}")).copied().unwrap_or(0);
    if win_by.is_none() && d_sh < 0 {
        let c = counters[&format!("shield:{opp}")];
        let n = -((-c).div_euclid(-d_sh));
        if (n as f64) <= limit {
            win_by = Some("shield_zero".to_string());
            needed = Some(n);
        }
    }
    (limit, win_by, needed)
}

/// engine.loop.is_engine の写し（検出器の受け付け判定用。turn 側の同名関数とは別）。
fn loop_is_engine(delta: &BTreeMap<String, i64>, me: i64) -> bool {
    let suffix = format!(":{me}");
    let mut any_pos = false;
    let mut all_nonneg = true;
    for (k, &v) in delta {
        if k.ends_with(&suffix) && !k.starts_with("deck:") {
            if v > 0 && (k.starts_with("hand:") || k.starts_with("mana_untapped:")) {
                any_pos = true;
            }
            if v < 0 {
                all_nonneg = false;
            }
        }
    }
    any_pos && all_nonneg
}

/// engine.loop.is_burn の写し。
fn loop_is_burn(delta: &BTreeMap<String, i64>, me: i64) -> bool {
    let suffix = format!(":{me}");
    let deck_key = format!("deck:{me}");
    delta.get(&deck_key).copied().unwrap_or(0) < 0
        && !loop_is_engine(delta, me)
        && delta
            .iter()
            .all(|(k, &v)| k.ends_with(&suffix) && (v >= 0 || *k == deck_key))
}

/// search.turn.is_burn_loop の写し。
fn turn_is_burn(cert: &Cert, me: i64) -> bool {
    cert.win_by.is_none() && loop_is_burn(&cert.delta, me)
}

/// search.turn.is_engine_loop の写し。
fn turn_is_engine(cert: &Cert, me: i64) -> bool {
    let suffix = format!(":{}", 1 - me);
    cert.win_by.is_none()
        && !cert.delta.iter().any(|(k, &v)| v < 0 && k.ends_with(&suffix))
}

/// engine.loop.wild_keys の写し。
fn wild_keys(keys: &[String], hand_keys: &HashSet<String>) -> Vec<String> {
    keys.iter()
        .map(|k| {
            let parts: Vec<&str> = k.split(':').collect();
            if parts.len() >= 3 && parts[0] == "hand" && !hand_keys.contains(parts[1]) {
                WILD_HAND.to_string()
            } else {
                k.clone()
            }
        })
        .collect()
}

/// engine.loop.LoopDetector の写し（period は Detectors の使う "in_turn" 固定）。
#[derive(Clone)]
struct LoopDetector {
    me: i64,
    hand_keys: Option<HashSet<String>>,
    engine_loops: bool,
    report_all: bool,
    burn_loops: bool,
    wild: bool, // 実効値（Python の __init__ で hand_keys がある場合だけ有効化される）
    seen: HashMap<String, (BTreeMap<String, i64>, usize)>,
}

impl LoopDetector {
    fn new(me: i64, hand_keys: Option<HashSet<String>>, engine_loops: bool,
           report_all: bool, burn_loops: bool, wild: bool) -> Self {
        let wild = wild && hand_keys.is_some();
        LoopDetector {
            me,
            hand_keys,
            engine_loops,
            report_all,
            burn_loops,
            wild,
            seen: HashMap::new(),
        }
    }

    fn observe(&mut self, eng: &Engine, zc: &HashMap<String, bool>) -> Option<Cert> {
        let (h, ctr) = abstract_hk(eng, zc, self.hand_keys.as_ref());
        let now = eng.log.len();
        if let Some((old, at)) = self.seen.get(&h).cloned() {
            let delta: BTreeMap<String, i64> = ctr
                .iter()
                .filter(|(k, &v)| old.get(*k) != Some(&v))
                .map(|(k, &v)| (k.clone(), v - old[k]))
                .collect();
            if !delta.is_empty() && now > at {
                let (limit, win_by, needed) = analyze(&delta, &ctr, self.me);
                let opp_suffix = format!(":{}", 1 - self.me);
                let hurts_opp = delta.iter().any(|(k, &v)| v < 0 && k.ends_with(&opp_suffix));
                if hurts_opp
                    || win_by.is_some()
                    || (self.engine_loops && loop_is_engine(&delta, self.me))
                    || self.report_all
                    || (self.burn_loops && loop_is_burn(&delta, self.me))
                {
                    let acts = &eng.log[at..now];
                    let mut keys: Vec<Vec<String>> = acts
                        .iter()
                        .map(|a| {
                            a["keys"]
                                .as_array()
                                .map(|arr| {
                                    arr.iter()
                                        .map(|v| v.as_str().unwrap_or("").to_string())
                                        .collect()
                                })
                                .unwrap_or_default()
                        })
                        .collect();
                    let mut wild = false;
                    if self.wild {
                        let hk = self.hand_keys.as_ref().unwrap();
                        keys = keys.iter().map(|k| wild_keys(k, hk)).collect();
                        wild = keys.iter().any(|k| k.iter().any(|x| x == WILD_HAND));
                    }
                    let deciders: Vec<i64> = acts
                        .iter()
                        .map(|a| a["p"].as_i64().unwrap_or(0))
                        .collect();
                    return Some(Cert {
                        start_skeleton: h,
                        actions: keys,
                        deciders,
                        delta,
                        limit,
                        period: "in_turn".to_string(),
                        win_by,
                        needed,
                        hand_keys: self.hand_keys.clone(),
                        wild,
                    });
                }
            }
        }
        self.seen.insert(h, (ctr, now));
        None
    }
}

/// search.turn.Detectors の写し（厳密・手札ぼかし・burn 受け付けの3検出器）。
#[derive(Clone)]
struct Detectors {
    dets: Vec<LoopDetector>,
}

impl Detectors {
    fn new(eng: &Engine, me: i64, draw_discard: bool) -> Detectors {
        let hk: HashSet<String> = eng.zone_names("hand", me, false).into_iter().collect();
        Detectors {
            dets: vec![
                LoopDetector::new(me, None, false, false, false, false),
                LoopDetector::new(me, Some(hk), true, false, draw_discard, draw_discard),
                LoopDetector::new(me, None, false, false, true, false),
            ],
        }
    }

    fn empty() -> Detectors {
        Detectors { dets: vec![] }
    }

    fn fork(&self) -> Detectors {
        self.clone()
    }

    /// 全検出器を回して（副作用は全てに効く）最初の証明書を返す（Python と同じ）。
    fn observe(&mut self, eng: &Engine, zc: &HashMap<String, bool>) -> Option<Cert> {
        let mut found: Option<Cert> = None;
        for d in &mut self.dets {
            let c = d.observe(eng, zc);
            if found.is_none() {
                found = c;
            }
        }
        found
    }
}

// ---------- 証明書の再生（engine.loop の verify / fast_forward の写し） ----------

fn replay_equiv() -> bool {
    static V: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
    *V.get_or_init(|| std::env::var("DMSIM_REPLAY_EQUIV").map(|s| s != "0").unwrap_or(true))
}

fn illegal<T>(msg: impl Into<String>) -> R<T> {
    Err(EngErr::Illegal(msg.into()))
}

/// Engine.answer_by_keys の写し（待機中の決定を意味キーで答える）。
fn answer_by_keys(eng: &mut Engine, keys: &[String]) -> R<()> {
    let w = match &eng.s.waiting {
        Some(w) => w.clone(),
        None => return illegal("no decision pending"),
    };
    let opts: Vec<String> = w["options"]
        .as_array()
        .map(|a| {
            a.iter()
                .map(|o| o["key"].as_str().unwrap_or("").to_string())
                .collect()
        })
        .unwrap_or_default();
    let mut choice: Vec<i64> = vec![];
    let mut used: HashSet<usize> = HashSet::new();
    for k in keys {
        let mut hit: Option<usize> = None;
        for (i, ok) in opts.iter().enumerate() {
            if ok == k && !used.contains(&i) {
                hit = Some(i);
                break;
            }
        }
        match hit {
            Some(i) => {
                choice.push(i as i64);
                used.insert(i);
            }
            None => return illegal(format!("key {k} not available in {opts:?}")),
        }
    }
    eng.answer(choice)
}

/// engine.loop.replay_keys の写し。d は直前の advance で得た決定（= 待機中の決定）。
fn replay_keys(eng: &mut Engine, keys: &[String], hand_keys: &Option<HashSet<String>>, d: &Value) -> R<()> {
    if !keys.iter().any(|k| k == WILD_HAND) {
        return answer_by_keys(eng, keys);
    }
    let empty = HashSet::new();
    let hk = hand_keys.as_ref().unwrap_or(&empty);
    let opts = d["options"].as_array().cloned().unwrap_or_default();
    let player = d["player"].as_i64().unwrap_or(0);
    let hand = eng.zone_ids("hand", player);
    let order: HashMap<i64, i64> = hand.iter().enumerate().map(|(i, &c)| (c, i as i64)).collect();
    let mut sorted_keys: Vec<&String> = keys.iter().collect();
    sorted_keys.sort_by_key(|k| *k == WILD_HAND); // 安定ソート: 具体キーを先に（Python と同じ）
    let mut choice: Vec<i64> = vec![];
    let mut used: HashSet<usize> = HashSet::new();
    for k in sorted_keys {
        let hit: Option<usize> = if k == WILD_HAND {
            let mut cand: Vec<usize> = (0..opts.len())
                .filter(|&i| {
                    if used.contains(&i) {
                        return false;
                    }
                    let key = opts[i]["key"].as_str().unwrap_or("");
                    if !key.starts_with("hand:") {
                        return false;
                    }
                    let name = key.split(':').nth(1).unwrap_or("");
                    !hk.contains(name)
                })
                .collect();
            cand.sort_by_key(|&i| {
                let ord = opts[i]
                    .get("cid")
                    .and_then(|v| v.as_i64())
                    .and_then(|c| order.get(&c).copied())
                    .unwrap_or(-1);
                -ord
            });
            cand.first().copied()
        } else {
            (0..opts.len()).find(|&i| !used.contains(&i) && opts[i]["key"].as_str() == Some(k.as_str()))
        };
        match hit {
            Some(i) => {
                choice.push(i as i64);
                used.insert(i);
            }
            None => {
                return illegal(format!(
                    "key {k} not available in {:?}",
                    opts.iter().map(|o| o["key"].as_str().unwrap_or("")).collect::<Vec<_>>()
                ))
            }
        }
    }
    choice.sort();
    eng.answer(choice)
}

/// engine.loop._equiv_keys の写し。
fn equiv_keys(d: &Value, keys: &[String]) -> Option<Vec<String>> {
    let opts: HashSet<&str> = d["options"]
        .as_array()
        .map(|a| a.iter().map(|o| o["key"].as_str().unwrap_or("")).collect())
        .unwrap_or_default();
    let mut out: Vec<String> = vec![];
    for k in keys {
        if opts.contains(k.as_str()) {
            out.push(k.clone());
        } else if k.starts_with("play:") && !k.ends_with(":free") && opts.contains(format!("{k}:free").as_str()) {
            out.push(format!("{k}:free"));
        } else if k.starts_with("mana:")
            && d["kind"].as_str() == Some("pay_mana")
            && d["options"].as_array().map(|a| !a.is_empty()).unwrap_or(false)
        {
            out.push(d["options"][0]["key"].as_str().unwrap_or("").to_string());
        } else {
            return None;
        }
    }
    Some(out)
}

/// engine.loop._replay_lap の写し。(終了したか, 同一視したか) を返す。
fn replay_lap(e: &mut Engine, cert: &Cert) -> R<(bool, bool)> {
    let mut subst = false;
    let mut i = 0;
    while i < cert.actions.len() {
        let keys = &cert.actions[i];
        let d = e.advance()?;
        let Some(d) = d else {
            return Ok((true, subst));
        };
        if replay_equiv()
            && !keys.is_empty()
            && d["kind"].as_str() != Some("pay_mana")
            && keys.iter().all(|k| k.starts_with("mana:"))
        {
            subst = true;
            i += 1;
            continue;
        }
        match replay_keys(e, keys, &cert.hand_keys, &d) {
            Ok(()) => {}
            Err(EngErr::Illegal(_)) => {
                let alt = if replay_equiv() && !keys.iter().any(|k| k == WILD_HAND) {
                    equiv_keys(&d, keys)
                } else {
                    None
                };
                match alt {
                    Some(alt) => {
                        answer_by_keys(e, &alt)?;
                        subst = true;
                    }
                    None => return illegal("replay_keys failed"),
                }
            }
            Err(e2) => return Err(e2),
        }
        i += 1;
    }
    Ok((false, subst))
}

/// engine.loop._delta_ok の写し。
fn delta_ok(delta: &BTreeMap<String, i64>, cert: &Cert, subst: bool) -> bool {
    if *delta == cert.delta {
        return true;
    }
    if !subst {
        return false;
    }
    let keys: HashSet<&String> = delta.keys().chain(cert.delta.keys()).collect();
    for k in keys {
        let a = delta.get(k).copied().unwrap_or(0);
        let b = cert.delta.get(k).copied().unwrap_or(0);
        if a == b {
            continue;
        }
        if k.starts_with("mana_untapped:") && a > b {
            continue;
        }
        return false;
    }
    true
}

fn ctr_diff(c1: &BTreeMap<String, i64>, c0: &BTreeMap<String, i64>) -> BTreeMap<String, i64> {
    c1.iter()
        .filter(|(k, &v)| c0.get(*k) != Some(&v))
        .map(|(k, &v)| (k.clone(), v - c0[k]))
        .collect()
}

/// engine.loop.verify の写し。戻り値は確認できた周回数（Python の cert.verified の増分）。
fn verify(eng: &Engine, cert: &Cert, times: i64, zc: &HashMap<String, bool>) -> R<i64> {
    let mut e = eng.clone();
    let mut verified: i64 = 0;
    for _ in 0..times {
        let (_h0, c0) = abstract_hk(&e, zc, cert.hand_keys.as_ref());
        match replay_lap(&mut e, cert) {
            Err(EngErr::Illegal(_)) => return Ok(verified),
            Err(e2) => return Err(e2),
            Ok((true, _)) => return Ok(verified),
            Ok((false, subst)) => {
                e.advance()?;
                let (h1, c1) = abstract_hk(&e, zc, cert.hand_keys.as_ref());
                let delta = ctr_diff(&c1, &c0);
                if h1 != cert.start_skeleton || !delta_ok(&delta, cert, subst) {
                    return Ok(verified);
                }
                verified += 1;
            }
        }
    }
    Ok(verified)
}

/// engine.loop.fast_forward の写し。
fn fast_forward(eng: &mut Engine, cert: &Cert, n: i64, zc: &HashMap<String, bool>) -> R<()> {
    for _ in 0..n {
        let (_h0, c0) = abstract_hk(eng, zc, cert.hand_keys.as_ref());
        let (ended, subst) = replay_lap(eng, cert)?;
        if ended {
            return Ok(());
        }
        if cert.wild || subst {
            eng.advance()?;
            let (h1, c1) = abstract_hk(eng, zc, cert.hand_keys.as_ref());
            if h1 != cert.start_skeleton || !delta_ok(&ctr_diff(&c1, &c0), cert, subst) {
                return illegal("fast_forward diverged from certificate");
            }
        }
    }
    eng.advance()?;
    Ok(())
}

/// TurnSearch._stocks の写し（記録 lp は作らず、ストック先の局面だけを返す。
/// lp は LeafCollector の葉に乗らないため等価性には影響しない）。
fn stocks(p: &Params, eng: &Engine, cert: &Cert) -> R<Vec<Engine>> {
    let engine_f = turn_is_engine(cert, p.me);
    let burn_f = turn_is_burn(cert, p.me);
    let mut n: i64 = if burn_f {
        if cert.limit.is_finite() {
            cert.limit as i64
        } else {
            0
        }
    } else if cert.win_by.is_some() {
        cert.needed.unwrap_or(0)
    } else if engine_f {
        cert.limit.min(p.stock_cap as f64) as i64
    } else if cert.limit.is_finite() {
        cert.limit as i64
    } else {
        0
    };
    let d_deck = cert.delta.get(&format!("deck:{}", p.me)).copied().unwrap_or(0);
    if engine_f && !burn_f && d_deck < 0 {
        let deck_len = eng.zone_ids("deck", p.me).len() as i64;
        n = n.min((deck_len - p.w.deck_keep).div_euclid(-d_deck));
    }
    if n <= 0 || verify(eng, cert, 1, &p.zones_counter)? < 1 {
        return Ok(vec![]);
    }
    let offsets: &[i64] = if burn_f || (engine_f && cert.win_by.is_none()) {
        &p.stock_offsets
    } else {
        &[0]
    };
    let mut out = vec![];
    for &k in offsets {
        let m = n - k;
        if m <= 0 {
            continue;
        }
        let mut ff = eng.clone();
        if fast_forward(&mut ff, cert, m, &p.zones_counter).is_err() {
            continue;
        }
        out.push(ff);
    }
    Ok(out)
}

// ---------- 展開ループ（LeafCollector._rec / collect の写し） ----------

enum Flow {
    Ok,
    Stop, // 葉上限に到達（Python の _CapReached）
}

struct LeafOut {
    value: f64,
    engine: Engine,
    digest: String,
}

struct Ctx {
    p: Params,
    seen: HashSet<String>,
    left: i64,
    nodes: i64,
    leaf_count: i64,
    truncated: bool,
    leaves: Vec<LeafOut>,
    certs: Vec<Value>, // Detectors.observe が返した証明書（cert_to_dict 形、観測順）
}

impl Ctx {
    fn push_leaf(&mut self, eng: Engine) -> Flow {
        let value = evaluate(&eng, self.p.me, &self.p.w);
        let digest = eng.s.digest();
        self.leaves.push(LeafOut {
            value,
            engine: eng,
            digest,
        });
        self.leaf_count += 1;
        if self.leaf_count >= self.p.leaf_cap {
            self.truncated = true;
            return Flow::Stop;
        }
        Flow::Ok
    }

    fn rec(&mut self, mut eng: Engine, det: Detectors) -> R<Flow> {
        let d = settle(&mut eng, self.p.me)?;
        let Some(d) = d else {
            return Ok(self.push_leaf(eng));
        };
        if self.left <= 0 {
            self.truncated = true;
            rollout(&mut eng, &self.p)?;
            return Ok(self.push_leaf(eng));
        }
        let tk = tkey(&eng, &self.p.zones_counter);
        if self.p.detectors {
            // LeafCollector._rec の証明書処理（collect モードはゲートで除外済み）。
            // observe の副作用（seen の更新）はこの経路の det に残り、子へは fork して渡す。
            let mut det = det;
            let cert = det.observe(&eng, &self.p.zones_counter);
            if let Some(cert) = cert {
                self.certs.push(cert.to_dict());
                let burn = turn_is_burn(&cert, self.p.me);
                if burn && !self.p.burn_stock {
                    // cert = None として通常展開へ
                } else if verify(&eng, &cert, 1, &self.p.zones_counter)? < 1 {
                    // 骨格が戻っただけで繰り返せない。cert = None として通常展開へ
                } else {
                    let stocks = stocks(&self.p, &eng, &cert)?;
                    if !stocks.is_empty() {
                        for ff in stocks {
                            let det2 = Detectors::new(&ff, self.p.me, self.p.draw_discard);
                            if let Flow::Stop = self.rec(ff, det2)? {
                                return Ok(Flow::Stop);
                            }
                        }
                        return Ok(Flow::Ok);
                    }
                    if turn_is_engine(&cert, self.p.me) && !burn {
                        // 資源ループはストックし切った局面を葉として残す
                        return Ok(self.push_leaf(eng));
                    }
                    // cert = None として通常展開へ
                }
            }
            return self.expand_children(eng, d, tk, det);
        }
        self.expand_children(eng, d, tk, det)
    }

    fn expand_children(&mut self, eng: Engine, d: Value, tk: String, det: Detectors) -> R<Flow> {
        if self.seen.contains(&tk) {
            return Ok(Flow::Ok);
        }
        self.seen.insert(tk);
        // 登録簿マクロの子はゲートで「マクロが空」の場合だけ委譲されるので、ここでは何もしない
        let mut cands = candidates(&eng, &d, &self.p, false);
        if self.p.repeat_first && cands.len() > 1 {
            cands = repeat_order(&eng, &d, cands, self.p.root_log);
        }
        for choice in cands {
            if self.left <= 0 {
                self.truncated = true;
                break;
            }
            self.left -= 1;
            self.nodes += 1;
            let mut child = eng.clone();
            child.answer(choice)?;
            if let Flow::Stop = self.rec(child, det.fork())? {
                return Ok(Flow::Stop);
            }
        }
        Ok(Flow::Ok)
    }
}

/// expand_turn の本体。root は変更しない（複製して走査する）。
/// 戻り値は (メタ情報の JSON 文字列, 葉の Engine の列)。メタ情報:
/// {leaves: [{value, log, digest}], truncated, nodes, left, leaf_count}
/// 葉を状態 JSON で返すと、受け側が葉ごとに規則バンドルを読み直して割に合わないため、
/// 葉は Engine そのもの（規則は Arc 共有）で返す。log はメタ情報側に含める。
pub fn expand_turn(root: &Engine, params_json: &str) -> R<(String, Vec<Engine>)> {
    let p = Params::parse(params_json)?;
    let det = if p.detectors {
        Detectors::new(root, p.me, p.draw_discard)
    } else {
        Detectors::empty()
    };
    let mut ctx = Ctx {
        left: p.budget,
        p,
        seen: HashSet::new(),
        nodes: 0,
        leaf_count: 0,
        truncated: false,
        leaves: vec![],
        certs: vec![],
    };
    ctx.rec(root.clone(), det)?;
    let leaves: Vec<Value> = ctx
        .leaves
        .iter()
        .map(|l| json!({"value": l.value, "log": l.engine.log, "digest": l.digest}))
        .collect();
    let engines: Vec<Engine> = ctx.leaves.into_iter().map(|l| l.engine).collect();
    Ok((
        json!({
            "leaves": leaves,
            "truncated": ctx.truncated,
            "nodes": ctx.nodes,
            "left": ctx.left,
            "leaf_count": ctx.leaf_count,
            "certs": ctx.certs,
        })
        .to_string(),
        engines,
    ))
}

/// テスト・照合用: abstract(eng, "in_turn") のハッシュだけを返す。
pub fn abstract_hash_of(eng: &Engine, zones_counter: &HashMap<String, bool>) -> String {
    abstract_of(eng, zones_counter).0
}
