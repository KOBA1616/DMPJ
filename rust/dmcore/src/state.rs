//! ゲーム状態。Python 版 dmsim/engine/state.py と同じ形の純データ（JSON で相互に変換できる）。
//! フィールドはアルファベット順に宣言する: Python の digest は sort_keys=True の JSON を取るので、
//! 構造体の出力順をそれに合わせれば、バイト列が一致する。
use blake2::digest::{Update, VariableOutput};
use blake2::Blake2bVar;
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use std::collections::BTreeMap;

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct Card {
    pub bazurenda: i64,
    pub cid: i64,
    pub controller: i64,
    pub crossed: Option<Value>,
    pub defn: String,
    pub drawn_turn: i64,
    pub dswitched: bool,
    pub entered_seq: i64,
    pub entered_turn: i64,
    pub exlife_of: Option<Value>,
    pub face: i64,
    pub face_down: bool,
    pub face_up: bool,
    pub fortifies: Option<Value>,
    pub gen: i64,
    pub hyper: bool,
    pub link: i64,
    pub no_untap_next: bool,
    pub odrive: bool,
    pub odrive_civs: Vec<Value>,
    pub owner: i64,
    pub seal_of: i64,
    pub seals: Vec<i64>,
    pub sforce_of: Option<Value>,
    pub sst: bool,
    pub stp: bool,
    pub strigger_off: bool,
    pub strigger_on: bool,
    pub summon_fuel: Vec<Value>,
    pub summon_tapped: Vec<Value>,
    pub tapped: bool,
    pub top_of: i64,
    pub under: Vec<i64>,
    pub vivid: bool,
    pub zone: String,
}

impl Card {
    pub fn new(cid: i64, defn: &str, owner: i64) -> Card {
        Card {
            bazurenda: 0, cid, controller: owner, crossed: None, defn: defn.to_string(), drawn_turn: -1, dswitched: false,
            entered_seq: 0, entered_turn: -1, exlife_of: None, face: -1, face_down: false, face_up: false,
            fortifies: None, gen: 0, hyper: false, link: 0, no_untap_next: false, odrive: false, odrive_civs: vec![],
            owner, seal_of: -1, seals: vec![], sforce_of: None, sst: false, stp: false, strigger_off: false, strigger_on: false, summon_fuel: vec![], summon_tapped: vec![], tapped: false, top_of: -1,
            under: vec![], vivid: false, zone: "deck".to_string(),
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct GameState {
    pub active: i64,
    pub cards: Vec<Card>,
    pub continuous: Vec<Value>,
    pub deck_emptied: Vec<i64>,
    pub declares: Map<String, Value>,
    pub delayed: Vec<Value>,
    pub ev_seq: i64,
    pub extra_turns: Vec<i64>,
    pub first_player: i64,
    pub game_counters: Map<String, Value>,
    pub hold: Vec<i64>,
    pub pending: Vec<Value>,
    pub prev_counters: Map<String, Value>,
    pub r#pub: Vec<Value>,
    pub result: Option<Value>,
    pub rng: u64,
    pub sba_held: Vec<Vec<i64>>,
    pub seq: i64,
    pub skip_rest: bool,
    pub step: String,
    pub step_mods: Vec<Value>,
    pub steps_this_turn: i64,
    pub tasks: Vec<Value>,
    pub trace: Option<Vec<Value>>,
    pub turn: i64,
    pub turn_counters: Map<String, Value>,
    pub waiting: Option<Value>,
    pub windows: Vec<i64>,
    pub zones: BTreeMap<String, Vec<Vec<i64>>>,
}

impl GameState {
    /// splitmix64（Python 版 rng_next と同じ）
    pub fn rng_next(&mut self) -> u64 {
        self.rng = self.rng.wrapping_add(0x9E3779B97F4A7C15);
        let mut z = self.rng;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
        z ^ (z >> 31)
    }

    pub fn pub_len(&self) -> usize {
        self.r#pub.len()
    }

    pub fn rng_below(&mut self, n: u64) -> u64 {
        self.rng_next() % n
    }

    /// Python の GameState.to_json と同じバイト列（キーは整列、区切りは , と :、非 ASCII はそのまま）
    pub fn to_json(&self) -> String {
        serde_json::to_string(self).expect("state is serializable")
    }

    pub fn digest(&self) -> String {
        let mut h = Blake2bVar::new(16).unwrap();
        h.update(self.to_json().as_bytes());
        let mut out = [0u8; 16];
        h.finalize_variable(&mut out).unwrap();
        out.iter().map(|b| format!("{:02x}", b)).collect()
    }

    /// Python の GameState.fast_key と同じ値（dmsim/engine/state.py の
    /// _enc_into の位置符号化を写したもの）。探索内部の重複統合・
    /// チェックポイントの葉照合に使う。digest() とは別物なので注意。
    pub fn fast_key(&self) -> String {
        let mut out = String::new();
        enc_state(self, &mut out);
        let mut h = Blake2bVar::new(16).unwrap();
        h.update(out.as_bytes());
        let mut buf = [0u8; 16];
        h.finalize_variable(&mut buf).unwrap();
        buf.iter().map(|b| format!("{:02x}", b)).collect()
    }
}

/// Python の repr(str)（辞書キーの並べ替えに使う）。CPython の str の
/// repr はシングルクォートで、キーに現れるのは基本的に ASCII 識別子なので
/// 特殊な文字の扱いは近似で十分（順序が変わるのは引用符・制御文字を含む場合のみ）。
fn py_repr_str(s: &str) -> String {
    let mut out = String::from("'");
    for ch in s.chars() {
        match ch {
            '\'' => out.push_str("\\'"),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\x{:02x}", c as u32)),
            c if (c as u32) == 0x7f => out.push_str("\\x7f"),
            c => out.push(c),
        }
    }
    out.push('\'');
    out
}

/// Python の repr(float) の近似（状態に浮動小数点数は現れない前提の保険）。
fn py_repr_float(v: f64) -> String {
    if v == v.trunc() && v.abs() < 1e16 {
        return format!("{:.1}", v);
    }
    let s = format!("{:e}", v);
    if let Some(pos) = s.find('e') {
        let (m, e) = s.split_at(pos);
        let e = &e[1..];
        let (sign, digits) = match e.strip_prefix('-') {
            Some(d) => ("-", d),
            None => ("+", e),
        };
        format!("{}e{}{:0>2}", m, sign, digits)
    } else {
        s
    }
}

fn enc_i64(v: i64, out: &mut String) {
    out.push_str(&format!("i{};", v));
}

fn enc_bool(v: bool, out: &mut String) {
    out.push_str(if v { "b1;" } else { "b0;" });
}

fn enc_str(v: &str, out: &mut String) {
    out.push_str(&format!("s{}:{};", v.chars().count(), v));
}

/// _enc_into の写し（任意の JSON 値）。辞書はキー repr 順、リストは順序どおり。
/// dataclass（GameState / Card）は宣言順が要るので専用の enc_state / enc_card を使う。
fn enc_value(v: &Value, out: &mut String) {
    match v {
        Value::Null => out.push_str("N;"),
        Value::Bool(b) => enc_bool(*b, out),
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                enc_i64(i, out);
            } else if let Some(u) = n.as_u64() {
                out.push_str(&format!("i{};", u));
            } else if let Some(f) = n.as_f64() {
                out.push_str(&format!("r{};", py_repr_float(f)));
            } else {
                out.push_str(&format!("r{};", n));
            }
        }
        Value::String(s) => enc_str(s, out),
        Value::Array(a) => {
            out.push('[');
            for x in a {
                enc_value(x, out);
            }
            out.push(']');
        }
        Value::Object(m) => {
            out.push('{');
            let mut keys: Vec<&String> = m.keys().collect();
            keys.sort_by(|a, b| py_repr_str(a).cmp(&py_repr_str(b)));
            for k in keys {
                enc_str(k, out);
                enc_value(&m[k], out);
            }
            out.push('}');
        }
    }
}

fn enc_opt_value(v: &Option<Value>, out: &mut String) {
    match v {
        None => out.push_str("N;"),
        Some(x) => enc_value(x, out),
    }
}

fn enc_value_vec(v: &[Value], out: &mut String) {
    out.push('[');
    for x in v {
        enc_value(x, out);
    }
    out.push(']');
}

/// Card の _enc_into（フィールドは Python の dataclass 宣言順）。
fn enc_card(c: &Card, out: &mut String) {
    out.push('(');
    enc_i64(c.cid, out);
    enc_str(&c.defn, out);
    enc_i64(c.owner, out);
    enc_str(&c.zone, out);
    enc_i64(c.gen, out);
    enc_i64(c.controller, out);
    enc_bool(c.tapped, out);
    enc_bool(c.face_up, out);
    enc_bool(c.face_down, out);
    enc_i64(c.entered_turn, out);
    out.push('[');
    for x in &c.under {
        enc_i64(*x, out);
    }
    out.push(']');
    enc_i64(c.top_of, out);
    out.push('[');
    for x in &c.seals {
        enc_i64(*x, out);
    }
    out.push(']');
    enc_i64(c.seal_of, out);
    enc_i64(c.face, out);
    enc_i64(c.entered_seq, out);
    enc_opt_value(&c.crossed, out);
    enc_opt_value(&c.exlife_of, out);
    enc_opt_value(&c.sforce_of, out);
    enc_opt_value(&c.fortifies, out);
    enc_bool(c.no_untap_next, out);
    enc_i64(c.link, out);
    enc_bool(c.hyper, out);
    enc_bool(c.strigger_off, out);
    enc_bool(c.strigger_on, out);
    enc_bool(c.sst, out);
    enc_bool(c.stp, out);
    enc_bool(c.odrive, out);
    enc_value_vec(&c.odrive_civs, out);
    enc_value_vec(&c.summon_tapped, out);
    enc_value_vec(&c.summon_fuel, out);
    enc_i64(c.bazurenda, out);
    enc_i64(c.drawn_turn, out);
    enc_bool(c.vivid, out);
    enc_bool(c.dswitched, out);
    out.push(')');
}

/// GameState の _enc_into（フィールドは Python の dataclass 宣言順）。
fn enc_state(s: &GameState, out: &mut String) {
    out.push('(');
    out.push('[');
    for c in &s.cards {
        enc_card(c, out);
    }
    out.push(']');
    // zones: dict（キー repr 順）
    out.push('{');
    let mut zkeys: Vec<&String> = s.zones.keys().collect();
    zkeys.sort_by(|a, b| py_repr_str(a).cmp(&py_repr_str(b)));
    for k in zkeys {
        enc_str(k, out);
        out.push('[');
        for col in &s.zones[k] {
            out.push('[');
            for x in col {
                enc_i64(*x, out);
            }
            out.push(']');
        }
        out.push(']');
    }
    out.push('}');
    out.push('[');
    for x in &s.hold {
        enc_i64(*x, out);
    }
    out.push(']');
    enc_i64(s.turn, out);
    enc_i64(s.active, out);
    enc_i64(s.first_player, out);
    enc_str(&s.step, out);
    out.push_str(&format!("i{};", s.rng));
    enc_value_vec(&s.pending, out);
    out.push('[');
    for x in &s.windows {
        enc_i64(*x, out);
    }
    out.push(']');
    enc_value_vec(&s.continuous, out);
    enc_value_vec(&s.delayed, out);
    enc_value_vec(&s.step_mods, out);
    enc_value_vec(&s.tasks, out);
    enc_opt_value(&s.waiting, out);
    enc_opt_value(&s.result, out);
    enc_i64(s.seq, out);
    out.push('[');
    for x in &s.extra_turns {
        enc_i64(*x, out);
    }
    out.push(']');
    enc_value(&Value::Object(s.turn_counters.clone()), out);
    enc_value(&Value::Object(s.prev_counters.clone()), out);
    enc_value(&Value::Object(s.game_counters.clone()), out);
    enc_value(&Value::Object(s.declares.clone()), out);
    enc_i64(s.ev_seq, out);
    enc_i64(s.steps_this_turn, out);
    enc_bool(s.skip_rest, out);
    out.push('[');
    for x in &s.deck_emptied {
        enc_i64(*x, out);
    }
    out.push(']');
    enc_value_vec(&s.r#pub, out);
    out.push('[');
    for col in &s.sba_held {
        out.push('[');
        for x in col {
            enc_i64(*x, out);
        }
        out.push(']');
    }
    out.push(']');
    match &s.trace {
        None => out.push_str("N;"),
        Some(t) => enc_value_vec(t, out),
    }
    out.push(')');
}
