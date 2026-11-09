//! ルール・カード定義（Python 側 dmsim/rustcore.py の rules_bundle が書き出す JSON を読む）。
//! 段階1では「plain」なカード（能力・キーワード・特殊な札の仕組みを一切持たないクリーチャー）だけを動かす。
//! plain でないカードが対戦に入っていたら、open の時点で Unsupported を返す（落とさず、移植の進み具合として数える）。
use serde::Deserialize;
use std::collections::HashMap;

#[derive(Deserialize, Clone, Debug)]
pub struct CardDef {
    pub name: String,
    pub civs: Vec<String>,
    pub cost: i64,
    pub power: i64,
    pub mana: i64,
    pub plain: bool,
    #[serde(default)]
    pub allow: Vec<String>,
    #[serde(default)]
    pub deny: Vec<String>,
    #[serde(default)]
    pub breaks: Vec<i64>,
}

#[derive(Deserialize, Clone, Debug)]
pub struct ZoneDef {
    pub public: bool,
    pub ordered: bool,
    pub shared: bool,
}

#[derive(Deserialize, Clone, Debug)]
pub struct Rules {
    pub actions: HashMap<String, bool>, // 各 action の既定（permits の既定値）
    pub zones: Vec<(String, ZoneDef)>,
    pub steps: Vec<String>,
    pub cards: HashMap<String, CardDef>,
}

impl Rules {
    pub fn zone(&self, name: &str) -> &ZoneDef {
        &self.zones.iter().find(|(n, _)| n == name).expect("zone").1
    }
}
