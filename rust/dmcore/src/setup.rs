//! 対戦の準備（Python 版 Engine.new_game と同じ手順）。
use crate::state::{Card, GameState};
use serde::Deserialize;
use serde_json::{json, Map, Value};
use std::collections::{BTreeMap, HashMap};

/// Python 側（dmsim/rustcore.py）がルール・カード定義から作る、準備に必要な情報。
#[derive(Deserialize)]
pub struct NewGameSpec {
    pub decks: Vec<Vec<String>>,
    pub zones: Vec<String>,                  // rules.zones の名前
    pub public: HashMap<String, bool>,       // ゾーンごとの公開
    pub ordered: HashMap<String, bool>,      // ゾーンごとの順序の有無
    pub shared: HashMap<String, bool>,       // ゾーンごとの共有
    pub multi_civ: HashMap<String, bool>,    // カードごとに2文明以上か（マナにタップして置かれる）
    pub steps: Vec<String>,                  // rules.steps
    pub seed: u64,
    pub first_player: i64,
}

fn zlist<'a>(s: &'a mut GameState, spec: &NewGameSpec, z: &str, p: usize) -> &'a mut Vec<i64> {
    let idx = if *spec.shared.get(z).unwrap_or(&false) { 0 } else { p };
    &mut s.zones.get_mut(z).unwrap()[idx]
}

fn shuffle(s: &mut GameState, p: usize) {
    let n = s.zones["deck"][p].len();
    for i in (1..n).rev() {
        let j = s.rng_below((i + 1) as u64) as usize;
        s.zones.get_mut("deck").unwrap()[p].swap(i, j);
    }
}

/// イベントを通さない移動（ゲーム準備用の部分だけ。Python 版 _raw_move の準備で通る経路）。
fn raw_move(s: &mut GameState, spec: &NewGameSpec, cid: i64, to: &str) {
    let (owner, from, defn) = {
        let c = &s.cards[cid as usize];
        (c.owner as usize, c.zone.clone(), c.defn.clone())
    };
    {
        let lst = zlist(s, spec, &from, owner);
        if let Some(pos) = lst.iter().position(|&x| x == cid) {
            lst.remove(pos);
        }
    }
    {
        let c = &mut s.cards[cid as usize];
        c.gen += 1;
        c.face_down = false;
        c.zone = to.to_string();
        c.tapped = to == "mana" && *spec.multi_civ.get(&defn).unwrap_or(&false);
        c.face_up = *spec.public.get(to).unwrap_or(&false);
        c.controller = c.owner;
        c.entered_turn = -1;
        c.face = -1;
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
    let ordered = *spec.ordered.get(to).unwrap_or(&false);
    let dest = zlist(s, spec, to, owner);
    if ordered {
        dest.insert(0, cid); // position == "top"
    } else {
        dest.push(cid);
    }
}

pub fn new_game(spec: &NewGameSpec) -> GameState {
    let mut cards = vec![];
    let mut zones: BTreeMap<String, Vec<Vec<i64>>> = spec.zones.iter().map(|z| (z.clone(), vec![vec![], vec![]])).collect();
    for (p, deck) in spec.decks.iter().enumerate() {
        for d in deck {
            let cid = cards.len() as i64;
            cards.push(Card::new(cid, d, p as i64));
            zones.get_mut("deck").unwrap()[p].push(cid);
        }
    }
    let mut s = GameState {
        active: spec.first_player, cards, continuous: vec![], deck_emptied: vec![], declares: Map::new(), delayed: vec![], ev_seq: 0,
        extra_turns: vec![], first_player: spec.first_player, game_counters: Map::new(), hold: vec![], pending: vec![], prev_counters: Map::new(), r#pub: vec![], result: None,
        rng: spec.seed, sba_held: vec![], seq: 0, skip_rest: false, step: "start".to_string(), step_mods: vec![],
        steps_this_turn: 0, tasks: vec![], trace: None, turn: 1, turn_counters: Map::new(), waiting: None,
        windows: vec![], zones,
    };
    for p in 0..2usize {
        shuffle(&mut s, p);
        for _ in 0..5 {
            let c = s.zones["deck"][p][0];
            raw_move(&mut s, spec, c, "shield");
        }
        for _ in 0..5 {
            let c = s.zones["deck"][p][0];
            raw_move(&mut s, spec, c, "hand");
        }
    }
    s.deck_emptied = vec![];
    s.r#pub = vec![];
    let steps: Vec<Value> = spec.steps.iter().map(|x| Value::String(x.clone())).collect();
    s.tasks.push(json!({"t": "turn", "steps": steps, "i": 0, "sub": 0, "cp": true}));
    s
}
