//! ルール・カード定義（Python 側 dmsim/engine/rustcore.py の rules_bundle が書き出す JSON を読む）。
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
    pub types: Vec<String>,
    #[serde(default)]
    pub races: Vec<String>,
    #[serde(default)]
    pub keywords: Vec<String>,
    #[serde(default)]
    pub abil: Vec<serde_json::Value>,
    #[serde(default)]
    pub allow: Vec<String>,
    #[serde(default)]
    pub deny: Vec<String>,
    #[serde(default)]
    pub breaks: Vec<i64>,
    #[serde(default)]
    pub shield_allow: Vec<String>,
    #[serde(default)]
    pub spell: Vec<serde_json::Value>,      // 呪文の効果（plain な呪文だけ。Python の CardDef.spell）
    #[serde(default)]
    pub zt: bool,                           // バトルゾーン以外で働く誘発型能力を持つ（Python の zone_trigger_defs）
    #[serde(default = "default_resolve_to")]
    pub resolve_to: String,                 // 呪文の解決後の置き場所（チャージャーは mana）
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
    #[serde(default)]
    pub zt_zones: Vec<String>,              // zone_trigger_defs の全ゾーン（並びは Python と同じ sorted）
}

impl Rules {
    pub fn zone(&self, name: &str) -> &ZoneDef {
        &self.zones.iter().find(|(n, _)| n == name).expect("zone").1
    }
}

fn default_resolve_to() -> String {
    "graveyard".to_string()
}
