//! ゲーム状態。Python 版 dmsim/state.py と同じ形の純データ（JSON で相互に変換できる）。
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
    pub gen: i64,
    pub hyper: bool,
    pub link: i64,
    pub no_untap_next: bool,
    pub odrive: bool,
    pub odrive_civs: Vec<Value>,
    pub owner: i64,
    pub seal_of: i64,
    pub seals: Vec<i64>,
    pub sst: bool,
    pub stp: bool,
    pub strigger_off: bool,
    pub strigger_on: bool,
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
            gen: 0, hyper: false, link: 0, no_untap_next: false, odrive: false, odrive_civs: vec![],
            owner, seal_of: -1, seals: vec![], sst: false, stp: false, strigger_off: false, strigger_on: false, tapped: false, top_of: -1,
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
}
