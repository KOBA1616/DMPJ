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
    #[serde(default)]
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
    pub allow_x: Vec<serde_json::Value>,   // 辞書形の allow（無条件の禁止があって効かないもの。特性に並べるだけ）
    #[serde(default)]
    pub deny_if: Vec<(serde_json::Value, Vec<String>)>,   // 条件つきの自分への禁止（条件, 禁止する行動）
    #[serde(default)]
    pub spell: Vec<serde_json::Value>,      // 呪文の効果（plain な呪文だけ。Python の CardDef.spell）
    #[serde(default)]
    pub zt: bool,                           // バトルゾーン以外で働く誘発型能力を持つ（Python の zone_trigger_defs）
    #[serde(default = "default_resolve_to")]
    pub resolve_to: String,                 // 呪文の解決後の置き場所（チャージャーは mana）
    #[serde(default)]
    pub faces: Vec<CardDef>,
    #[serde(default)]
    pub evolve_from: Option<serde_json::Value>,   // 進化元の条件（zone を除く filter）。進化でなければ None
    #[serde(default)]
    pub evolve_zone: String,
    #[serde(default)]
    pub evolve_count: i64,
    #[serde(default)]
    pub evolve_any: bool,
    #[serde(default)]
    pub cost_reduce_per_evo: i64,                // ツインパクトの面（0: クリーチャー側, 1: 呪文側。810）
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
