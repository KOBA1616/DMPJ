"""拡張可能特徴量（Phase 26-4 拡張）。

attributes.py（294 次元）の後継設計。旧属性はカード単位の集計で、
能力の条件（if）が丸ごと欠落し、mod は 6 種の粗い分類までしか
区別できなかった（cast_limit 等の妨害は「mod がある」という数に
潰れる）。本モジュールは単位を能力（束）ごとに改め、条件・置換・
常在効果の中身まで特徴量化する。

設計（ユーザー承認済み）:

1. レジストリ方式: 特徴の枠は語彙定義側から自動生成する。
   能力種別・イベント・理由・mod キー・セレクタ/フィルタのキー・
   履歴カウンタ種・ord 種は dmsim/cards/defs.py の定数、op は
   dmsim/base/opvocab.py の OP_ARGS と data/rules/op_macros.yaml、
   ゾーン・キーワード・アクションは data/rules/ の各 yaml、
   面のフィールドは defs.Face の dataclass 定義から取る。
   変換トラックがプリミティブを足せば、特徴にも枠が増える。
2. 単位は能力ブロック: 能力 1 つを固定長ブロックにする
   （種別、when、if、effect、instead、mod、キーワード、代替
   コスト系キー等）。呪文面の効果リストも疑似ブロックとして
   並べる。カードは能力ブロックの集合として表現する。
3. 条件（if）は原子の和で表す: 条件式・式（expr）を再帰走査し、
   「参照種別 × カウンタ種 × 所有者 × 比較 × 閾値バケット」を
   部品ごとの多値として数える。部品の組み合わせは枠を増やさず
   表現できるが、論理構造（and/or の入れ子そのもの）は弱まる。
4. 数値はバケット化（個数 0..5,6+ / コスト等 0..9,10+ /
   パワーは帯域 / 修整値は符号つき帯域）。
5. 全グループに「その他」枠: 未知のプリミティブは黙って落ちず
   other として数える。coverage_report でその他率を測れる。
6. スキーマは末尾追加のみ: v1 の語彙スナップショット
   （BASE_VOCABULARIES）を凍結し、現在の語彙で増えたプリミ
   ティブの特徴は末尾にだけ足す。旧スキーマの特徴名列が新
   スキーマの接頭辞になることをテストで担保する。特徴名と
   スキーマ版は行列と一緒に返す（モデルファイルへの同梱用）。

カードレベルの互換出力として、能力ブロック列（注意モデル用）
に加え、ヘッダ（カード固有の静的特徴）＋ブロックの平均/最大
プーリングを連結したカードベクトルも出す（現行 AttrModel の
入力として使える形）。

既知の限界:
- 静的キーワード（ブロッカー等）の能力は keywords.yaml 側に
  定義があり、カードデータの abilities には現れない。本
  モジュールはデータに現れる能力だけをブロック化し、キー
  ワードは名前の特徴としてのみ扱う（旧属性と同じ）。
- 条件の原子の和は「A かつ B」と「A または B」の区別や、
  比較の左右の対応を弱める。厳密な論理構造が要る場合は
  条件をサブトークンとして注意で読む形が別途要る。
"""
from __future__ import annotations

import dataclasses
from collections import Counter

import numpy as np

from ..base.opvocab import OP_ARGS
from ..cards import defs as _defs
from .attributes import BREAKERS

SCHEMA_VERSION = 1

# ---- 数値バケット ----
NB7 = ["0", "1", "2", "3", "4", "5", "6p"]                    # 個数
NB11 = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10p"]  # コスト・閾値
POWER_B = ["0", "1_999", "1000_2999", "3000_4999", "5000_7999",
           "8000_11999", "12000p"]
SIGNED_B = ["n3000p", "n1000", "n100", "0", "p100", "p1000",
            "p3000", "p6000p"]
CMP_NAMES = {"<": "lt", "<=": "le", "==": "eq", ">=": "ge", ">": "gt"}
ORD_CMPS = ["eq", "ge", "gt", "le", "lt"]
OWNERS = ["you", "opp", "any"]
LIST_KINDS = ["ability", "spell", "sst_spell", "stp_spell", "odrive_spell"]
SPELL_LIST_KEYS = [("spell", "spell"), ("sst_spell", "sst_spell"),
                   ("stp_spell", "stp_spell"),
                   ("odrive_spell", "odrive_spell")]

# defs.Checker.cond / .expr が受理するキー。defs 側に定数が無いため
# 写しを持つ（増えた場合は coverage の other として検出される）。
COND_KINDS = ["exists", "cmp", "not", "all", "any", "marked",
              "self_marked", "is_turn", "face_up", "hyper", "alt_paid",
              "vivid_paid", "ddd_paid", "subject_tapped", "power_ge",
              "extra_turn"]
EXPR_KINDS = ["count", "civ_count", "distinct_cost_count",
              "distinct_type_count", "total_cost", "total_power",
              "max_power", "entered", "drew", "bundles", "turn_count",
              "used_count", "prev_shield_added", "declared", "var",
              "cost_of", "power_of", "name_of", "races_of", "civs_of",
              "race", "link_count", "seals", "seals_on",
              "crossed_count", "sum", "mul"]

# 構造的に符号化する能力キー（残りは abkey グループで存在ビット化）
STRUCTURAL_AB_KEYS = {"kind", "when", "if", "effect", "instead", "mod"}
# 面フィールドのうち存在ビット化しない基本項目
BASIC_FACE_FIELDS = {"name", "types", "civs", "cost", "power",
                     "races", "keywords"}
MOVE_FLAGS = ["tapped", "face_up", "face_down", "seal", "no_trigger",
              "card_only"]
WHEN_FLAGS = ["blocked", "battle", "emblem", "turn_draw", "cause",
              "sealed_from", "from_under"]


def _b7(n) -> str:
    return NB7[min(max(int(n), 0), 6)]


def _b11(n) -> str:
    return NB11[min(max(int(n), 0), 10)]


def _bpower(p) -> str:
    p = int(p)
    if p <= 0:
        return POWER_B[0]
    if p < 1000:
        return POWER_B[1]
    if p < 3000:
        return POWER_B[2]
    if p < 5000:
        return POWER_B[3]
    if p < 8000:
        return POWER_B[4]
    if p < 12000:
        return POWER_B[5]
    return POWER_B[6]


def _bsigned(v) -> str:
    v = int(v)
    if v <= -3000:
        return SIGNED_B[0]
    if v <= -1000:
        return SIGNED_B[1]
    if v < 0:
        return SIGNED_B[2]
    if v == 0:
        return SIGNED_B[3]
    if v < 1000:
        return SIGNED_B[4]
    if v < 3000:
        return SIGNED_B[5]
    if v < 6000:
        return SIGNED_B[6]
    return SIGNED_B[7]


def _cap3(x: float) -> float:
    return min(x, 3.0) / 3.0


# ------------------------------------------------------------------
# レジストリ（語彙）
# ------------------------------------------------------------------
def _race_top(rules) -> list[str]:
    """種族の採用リスト（attributes.py と同じ: 頻度1以上、上位64）。"""
    races: Counter = Counter()
    for cd in rules.cards.values():
        for u in (list(cd.faces) if getattr(cd, "faces", None) else [cd]):
            for r in getattr(u, "races", None) or []:
                races[r] += 1
    items = [(k, c) for k, c in races.items() if c >= 1]
    items.sort(key=lambda kv: (-kv[1], kv[0]))
    return [k for k, _ in items[:64]]


def current_vocabularies(rules) -> dict[str, list[str]]:
    """現在の語彙定義からレジストリを組み立てる（ソート済み）。"""
    zones, keywords, macros, actions, _steps = _defs.load_tables()
    return {
        "kind": sorted(_defs.ABILITY_KINDS),
        "event": sorted(_defs.EVENTS),
        "zone": sorted(zones),
        "reason": sorted(_defs.REASONS | _defs.LOSE_REASONS),
        "via": sorted(_defs.VIAS),
        "filter_key": sorted(_defs.FILTER_KEYS),
        "selector_key": sorted(_defs.SELECTOR_KEYS),
        "ord_kind": sorted(_defs.ORD_KINDS),
        "tc_kind": sorted(_defs.TURN_COUNT_KINDS),
        "op": sorted(set(OP_ARGS) | set(macros)),
        "mod_key": sorted(_defs.MOD_KEYS),
        "duration": sorted(_defs.DURATIONS_FIXED),
        "action": sorted(actions),
        "keyword": sorted(keywords),
        "abkey": sorted(set(_defs.ABILITY_KEYS) - STRUCTURAL_AB_KEYS),
        "card_type": sorted(_defs.CARD_TYPES),
        "civ": sorted(_defs.CIVS),
        "cond_kind": list(COND_KINDS),
        "expr_kind": list(EXPR_KINDS),
        "face_field": [f.name for f in dataclasses.fields(_defs.Face)],
        "race": _race_top(rules),
    }


# v1 の語彙スナップショット（凍結）。現在の語彙で増えたプリミティブは
# _resolve_vocab が各グループの末尾に足し、特徴名はさらに末尾追加で
# 解決するため、この並びは将来も壊さない。
BASE_VOCABULARIES = {
 "kind": [
  "activate",
  "declare",
  "partner",
  "replace",
  "silent",
  "state",
  "static",
  "trigger"
 ],
 "event": [
  "attack",
  "attack_end",
  "attack_unblocked",
  "battle",
  "battle_end",
  "battle_lose",
  "battle_start",
  "battle_win",
  "block",
  "break",
  "break_before",
  "cast",
  "choose",
  "draw",
  "evolve_base",
  "janken",
  "link_established",
  "lose",
  "move",
  "mugon_used",
  "summon",
  "tap",
  "trigger",
  "turn_end",
  "turn_start",
  "untap",
  "use_s_trigger"
 ],
 "zone": [
  "abyss",
  "bz",
  "deck",
  "gr",
  "graveyard",
  "hand",
  "hyper",
  "mana",
  "shield"
 ],
 "reason": [
  "battle",
  "break",
  "cast",
  "charge",
  "deck_out",
  "destroy",
  "direct_attack",
  "discard",
  "draw",
  "effect",
  "evolve",
  "put",
  "resolve",
  "return",
  "sba",
  "seal",
  "state",
  "summon"
 ],
 "via": [
  "d_d_d",
  "generate",
  "revolution_change",
  "rinne"
 ],
 "filter_key": [
  "any_of",
  "civs",
  "civs_all",
  "colorless",
  "cost_ge",
  "cost_le",
  "crossed",
  "crossed_ge",
  "crossed_le",
  "crossed_name",
  "entered_this_turn",
  "evo_source_of",
  "evolution",
  "evolves_from",
  "exlife",
  "face_down",
  "face_up",
  "fortified",
  "fortifying",
  "fushigi",
  "hyper",
  "keyword",
  "linked_god",
  "mugen_climb",
  "multicolor",
  "name",
  "name_has",
  "neo",
  "not_civs",
  "not_keyword",
  "not_name",
  "not_race_has",
  "not_types",
  "partner",
  "power_ge",
  "power_le",
  "race_has",
  "races",
  "races_all",
  "sealed",
  "spell_cost_ge",
  "spell_cost_le",
  "tapped",
  "twinpact",
  "types",
  "ultimate_evolution",
  "vanilla",
  "vividraw"
 ],
 "selector_key": [
  "bundle_of",
  "castle_of",
  "chooser",
  "count",
  "crossed_to",
  "distinct_costs",
  "distinct_from",
  "distinct_names",
  "exclude",
  "exlife_of",
  "extremal",
  "filter",
  "from_bottom",
  "from_top",
  "host_of",
  "look",
  "other",
  "owner",
  "owner_of",
  "ref",
  "total_cost_ge",
  "total_cost_le",
  "total_power_ge",
  "total_power_le",
  "under_of",
  "up_to",
  "zone"
 ],
 "ord_kind": [
  "attack",
  "attack_by",
  "cast",
  "draw",
  "enter",
  "mana_put",
  "summon"
 ],
 "tc_kind": [
  "attack",
  "attack_by",
  "attack_on",
  "block",
  "broke_by_self",
  "broke_by_self_attack",
  "broken",
  "cast",
  "destroyed",
  "discard",
  "draw",
  "dynamo_tap",
  "enter",
  "enter_unpaid",
  "leave",
  "mana_put",
  "shield_left",
  "shield_put",
  "summon",
  "tap",
  "untap",
  "untap_creature"
 ],
 "op": [
  "action_limit",
  "attach_seal",
  "battle_substitute",
  "bounce",
  "break",
  "cancel_attack",
  "cast_face",
  "castle_link",
  "choose",
  "choose_civ",
  "choose_name",
  "choose_number",
  "choose_player",
  "choose_race",
  "cross_free",
  "delayed_trigger",
  "destroy",
  "discard",
  "draw",
  "dswitch",
  "end_turn",
  "extra_turn",
  "flip_down",
  "flip_up",
  "force_battle",
  "gacha",
  "gachinko",
  "hyper_release",
  "if",
  "invade",
  "janken",
  "lose",
  "mana_put",
  "mark",
  "may",
  "mekurade",
  "mill",
  "modal",
  "modify",
  "move",
  "move_to_event",
  "move_under_to_event",
  "no_lose",
  "opp_may",
  "pay_or_lose",
  "play_free",
  "play_self",
  "put_under",
  "remove_seal",
  "repeat",
  "reveal_until",
  "rush",
  "set_var",
  "sforce_link",
  "shield_plus",
  "shuffle",
  "step_mod",
  "strigger",
  "summon_on",
  "summon_self",
  "swap",
  "tap",
  "together",
  "uncross",
  "untap",
  "untap_limit",
  "use_cip",
  "use_entry_abilities",
  "use_partner",
  "use_triggered_ability",
  "win",
  "yobinion"
 ],
 "mod_key": [
  "add_civs",
  "add_names",
  "add_of",
  "add_races",
  "allow",
  "battle_indestructible",
  "battle_power",
  "breaks",
  "breaks_add",
  "breaks_max",
  "breaks_per_power",
  "cost",
  "cost_may",
  "cost_min",
  "cross_reduce",
  "crystal_soul",
  "deny",
  "double_power",
  "evo_reduce",
  "gain",
  "grant",
  "ignore",
  "ignore_ids",
  "indestructible",
  "mana_number",
  "must_attack_creature",
  "must_be_attacked",
  "must_be_chosen",
  "no_leave",
  "opt_reduce",
  "player_rush",
  "power",
  "power_set",
  "power_when",
  "require",
  "sac_reduce",
  "trigger_double",
  "win_all_battles"
 ],
 "duration": [
  "during_attack",
  "end_of_turn",
  "permanent",
  "until_next_opp_turn_end",
  "until_next_own_turn_end",
  "until_next_own_turn_start"
 ],
 "action": [
  "attack_creature",
  "attack_player",
  "attack_summoning_sick",
  "be_attacked",
  "be_blocked",
  "be_chosen",
  "block",
  "cast",
  "cast_free",
  "cast_from_deck_top",
  "cast_from_graveyard",
  "cross_free",
  "d_switch",
  "enter_bz",
  "evolve_base",
  "evolve_base_any",
  "evolve_civ_any",
  "generate",
  "generate_from_deck_top",
  "guardman",
  "s_trigger",
  "slayer",
  "summon",
  "summon_from_deck_top",
  "summon_from_graveyard",
  "summon_from_mana",
  "untap_at_start"
 ],
 "keyword": [
  "abyss_rush",
  "blocker",
  "cannot_attack",
  "cannot_attack_player",
  "cannot_be_attacked",
  "cannot_block",
  "cannot_untap",
  "center_g_link",
  "charger",
  "crystal_charger",
  "cyclone",
  "double_breaker",
  "dynamo",
  "enters_tapped",
  "escape",
  "eternal_kappa",
  "eternal_omega",
  "evo_charger",
  "ex_life",
  "extra_ex_life",
  "freeze",
  "g_breaker",
  "g_neo",
  "g_strike",
  "guardman",
  "hunting",
  "hyper_energy",
  "infinite_breaker",
  "infinite_power_attacker",
  "kizuna",
  "kizuna_plus",
  "last_burst",
  "left_g_link",
  "mana_boost_cip",
  "mega_last_burst",
  "meteor_burn",
  "must_attack",
  "null_breaker",
  "opp_mana_tapped",
  "powered_breaker",
  "quad_breaker",
  "rensa",
  "right_g_link",
  "s_back_darkness",
  "s_back_fire",
  "s_back_light",
  "s_back_nature",
  "s_back_water",
  "s_trigger",
  "s_trigger_plus",
  "s_trigger_x",
  "shield_go",
  "shield_saver",
  "shinka_rise",
  "silent_skill",
  "slayer",
  "speed_attacker",
  "spell_to_hand",
  "summon_from_graveyard",
  "summon_from_mana",
  "super_s_trigger",
  "triple_breaker",
  "true_escape",
  "turbo_rush",
  "unblockable",
  "wave_striker",
  "world_breaker",
  "yobinion",
  "z_rush"
 ],
 "abkey": [
  "accel",
  "affects",
  "any_attacker",
  "bazurenda",
  "cast_limit",
  "choukon",
  "continue",
  "cost",
  "dswitch",
  "first_time",
  "fort_e",
  "group",
  "id",
  "keyword",
  "mana_all_civs",
  "mana_boost",
  "no_lose",
  "odrive",
  "once_per_turn",
  "optional",
  "protect_hand",
  "redirect",
  "sforce",
  "sst",
  "stp",
  "suppress_triggers",
  "untap_limit",
  "zone"
 ],
 "card_type": [
  "creature",
  "cross_gear",
  "d2_field",
  "dragonic_field",
  "dream_creature",
  "evolution",
  "exile_creature",
  "field",
  "g_castle",
  "spell",
  "tamaseed"
 ],
 "civ": [
  "darkness",
  "fire",
  "light",
  "nature",
  "water",
  "zero"
 ],
 "cond_kind": [
  "exists",
  "cmp",
  "not",
  "all",
  "any",
  "marked",
  "self_marked",
  "is_turn",
  "face_up",
  "hyper",
  "alt_paid",
  "vivid_paid",
  "ddd_paid",
  "subject_tapped",
  "power_ge",
  "extra_turn"
 ],
 "expr_kind": [
  "count",
  "civ_count",
  "distinct_cost_count",
  "distinct_type_count",
  "total_cost",
  "total_power",
  "max_power",
  "entered",
  "drew",
  "bundles",
  "turn_count",
  "used_count",
  "prev_shield_added",
  "declared",
  "var",
  "cost_of",
  "power_of",
  "name_of",
  "races_of",
  "civs_of",
  "race",
  "link_count",
  "seals",
  "seals_on",
  "crossed_count",
  "sum",
  "mul"
 ],
 "face_field": [
  "name",
  "types",
  "civs",
  "cost",
  "power",
  "races",
  "keywords",
  "abilities",
  "spell",
  "sst_spell",
  "stp_spell",
  "odrive_spell",
  "o_drive",
  "mugen_climb",
  "alt_cost",
  "vividraw",
  "fushigi",
  "recycle",
  "grave_cast",
  "rinne",
  "mana_bakutan",
  "link_to",
  "deck_evolution",
  "evolve_from",
  "evolve_zone",
  "evolve_any",
  "evolve_count",
  "evolve_max",
  "evolve_civs",
  "evolve_zones",
  "soul_shift",
  "cost_reduce_per_evo",
  "tap_reduce",
  "s_back",
  "free_if",
  "galaxy_shield",
  "bazurenda",
  "tap_entry",
  "neo",
  "grave_evo",
  "star",
  "s_max",
  "ace",
  "hyper",
  "crystal_soul",
  "mana_boost",
  "launcher",
  "evo_base_reduce",
  "evolve_total_cost_ge",
  "resolve_to",
  "resolve_face_down",
  "after_resolve"
 ],
 "race": [
  "テスト",
  "ジョーカーズ",
  "アーマード・ドラゴン",
  "エンジェル・コマンド",
  "デーモン・コマンド",
  "レクスターズ",
  "ハンター",
  "革命軍",
  "メタリカ",
  "マフィ・ギャング",
  "ビーストフォーク",
  "グランセクト",
  "エイリアン",
  "ビートジョッキー",
  "ヒューマノイド",
  "侵略者",
  "ムートピア",
  "アビスロイヤル",
  "サムライ",
  "リキッド・ピープル",
  "ファイアー・バード",
  "ディスペクター",
  "ナイト",
  "ドリームメイト",
  "ガーディアン",
  "ディスタス",
  "グレートメカオー",
  "サイバーロード",
  "ジャイアント",
  "ドラゴン・ゾンビ",
  "シノビ",
  "スノーフェアリー",
  "オリジン",
  "ソニック・コマンド",
  "ダークロード",
  "アウトレイジ",
  "アンノウン",
  "アーク・セラフィム",
  "グランド・デビル",
  "ティラノ・ドレイク",
  "エンジェル・コマンド・ドラゴン",
  "イニシエート",
  "オラクル",
  "デモニオ",
  "デスパペット",
  "ゴースト",
  "ゴッド",
  "サイバー・ウイルス",
  "ジャイアント・インセクト",
  "アース・ドラゴン",
  "アウトレイジMAX",
  "ワイルド・ベジーズ",
  "ライトブリンガー",
  "チーム切札",
  "超化獣",
  "鬼札王国",
  "デーモン・コマンド・ドラゴン",
  "メカ・デル・ソル",
  "フュージョナー",
  "ファンキー・ナイトメア",
  "ヘドリアン",
  "メガ・コマンド・ドラゴン",
  "アーマロイド",
  "ヒューマノイド爆"
 ]
}


# ------------------------------------------------------------------
# スキーマ（特徴名の並び。末尾追加のみ）
# ------------------------------------------------------------------
def _resolve_vocab(base: list[str], current: list[str]) -> list[str]:
    """凍結した並びを保ち、増えたプリミティブを末尾に足す。"""
    seen = set(base)
    return list(base) + sorted(x for x in current if x not in seen)


def _append_only(base_names: list[str], desired_names: list[str]) -> list[str]:
    """base_names を接頭辞として保ち、desired の新規分を末尾に足す。"""
    seen = set(base_names)
    return list(base_names) + [n for n in desired_names if n not in seen]


def _vg(voc: dict, group: str, prefix: str) -> list[str]:
    """語彙グループの特徴名（語彙分＋その他）。

    SELECTOR_KEYS のように語彙自体に "other" を含むグループでは、
    その他枠を兼用する（未知キーは検証で弾かれるため実害はない）。
    """
    names = [f"{prefix}{x}" for x in voc[group]]
    if "other" not in voc[group]:
        names.append(f"{prefix}other")
    return names


def _sel_base(p: str, voc: dict) -> list[str]:
    """セレクタ自体の特徴名（zone/owner/キー/フィルタ/個数）。"""
    out = _vg(voc, "zone", f"{p}zone.")
    out += [f"{p}owner.{o}" for o in OWNERS] + [f"{p}owner.other"]
    out += _vg(voc, "selector_key", f"{p}key.")
    out += _vg(voc, "filter_key", f"{p}filter.")
    out += _vg(voc, "card_type", f"{p}filter_type.")
    out += _vg(voc, "civ", f"{p}filter_civ.")
    out += [f"{p}count.{b}" for b in NB11] + [f"{p}count.all"]
    return out


def _expr_flat(p: str, voc: dict) -> list[str]:
    """式自体の特徴名（入れ子のセレクタを含まない部分）。"""
    out = _vg(voc, "expr_kind", f"{p}expr.") + [f"{p}expr.int"]
    out += [f"{p}num.{b}" for b in NB11]
    out += _vg(voc, "tc_kind", f"{p}tc.")
    out += [f"{p}tc_owner.{o}" for o in OWNERS]
    out += [f"{p}tc_filter"]
    out += _vg(voc, "filter_key", f"{p}tcfilter.")
    out += _vg(voc, "zone", f"{p}tc_from.")
    out += [f"{p}cnt_owner.{o}" for o in OWNERS]
    return out


def _sel_names(p: str, voc: dict) -> list[str]:
    """セレクタの部分特徴名 = 基底 ＋ 個数式のフラット部。

    セレクタと式は互いに入れ子になるため、規約として
    「セレクタは基底＋式フラット（個数式の引数セレクタは同じ
    スロットへ統合）」「式は式フラット＋セレクタ1段」とし、
    それより深い入れ子は浅い段の特徴としてのみ数える。
    """
    return _sel_base(p, voc) + _expr_flat(p, voc)


def _expr_names(p: str, voc: dict) -> list[str]:
    """式の部分特徴名 = 式フラット ＋ 引数セレクタ（_sel_names）。"""
    return _expr_flat(p, voc) + _sel_names(f"{p}sel.", voc)


def _cond_names(p: str, voc: dict) -> list[str]:
    out = _vg(voc, "cond_kind", f"{p}kind.")
    out += [f"{p}cmp.{c}" for c in CMP_NAMES.values()]
    out += [f"{p}is_turn.{o}" for o in ("you", "opp")]
    out += [f"{p}power_ge.{b}" for b in POWER_B]
    out += _expr_names(p, voc)
    return out


def _mod_names(p: str, voc: dict) -> list[str]:
    out = _vg(voc, "mod_key", f"{p}key.")
    out += [f"{p}breaks.{b}" for b in NB11]
    out += [f"{p}breaks_add.{b}" for b in NB11]
    out += [f"{p}power.{b}" for b in SIGNED_B] + [f"{p}power.power_of"]
    out += [f"{p}power_set.{b}" for b in POWER_B]
    out += [f"{p}cost.{b}" for b in SIGNED_B]
    out += [f"{p}cost_min.{b}" for b in SIGNED_B]
    out += _vg(voc, "keyword", f"{p}grant_kw.")
    out += [f"{p}grant_n.{b}" for b in NB7]
    out += _vg(voc, "action", f"{p}deny.")
    out += _vg(voc, "action", f"{p}allow.")
    out += [f"{p}no_leave.except_destroy"]
    out += [f"{p}add_races_n.{b}" for b in NB7]
    out += _sel_names(f"{p}breaks_sel.", voc)
    out += _sel_names(f"{p}power_sel.", voc)
    return out


def _fx_names(p: str, voc: dict) -> list[str]:
    out = _vg(voc, "op", f"{p}op.")
    out += [f"{p}nops.{b}" for b in NB7]
    out += [f"{p}depth.{d}" for d in ("0", "1", "2", "3", "4p")]
    out += _vg(voc, "zone", f"{p}move_to.")
    out += _vg(voc, "reason", f"{p}move_reason.")
    out += [f"{p}move_pos.top", f"{p}move_pos.bottom",
            f"{p}move_pos.other"]
    out += [f"{p}move_flag.{f}" for f in MOVE_FLAGS]
    out += _mod_names(f"{p}mod.", voc)
    out += _vg(voc, "duration", f"{p}duration.")
    out += _cond_names(f"{p}cond.", voc)
    out += _expr_names(p, voc)
    return out


def _ins_names(p: str, voc: dict) -> list[str]:
    """instead（置換先）の軽量版: 置換で何が起きるかだけを追う。"""
    out = _vg(voc, "op", f"{p}op.")
    out += [f"{p}nops.{b}" for b in NB7]
    out += [f"{p}depth.{d}" for d in ("0", "1", "2", "3", "4p")]
    out += _vg(voc, "zone", f"{p}move_to.")
    out += _vg(voc, "reason", f"{p}move_reason.")
    out += _sel_names(f"{p}sel.", voc)
    return out


def _block_names(voc: dict) -> list[str]:
    p = "ab."
    out = [f"{p}list.{lk}" for lk in LIST_KINDS]
    out += [f"{p}face.0", f"{p}face.1"]
    out += _vg(voc, "kind", f"{p}kind.")
    out += [f"{p}has.{k}" for k in
            ("when", "if", "effect", "instead", "mod", "cost")]
    out += _vg(voc, "abkey", f"{p}key.")
    out += [f"{p}affects.self", f"{p}affects.selector",
            f"{p}affects.other"]
    out += [f"{p}affects.owner.{o}" for o in OWNERS]
    out += _vg(voc, "zone", f"{p}affects.zone.")
    out += _vg(voc, "zone", f"{p}zone.")
    out += [f"{p}cost.{b}" for b in NB11] + [f"{p}cost.dict"]
    out += _vg(voc, "keyword", f"{p}kw.")
    out += [f"{p}limit.cast_limit.{b}" for b in NB7]
    out += [f"{p}limit.untap_limit.{b}" for b in NB7]
    # when
    out += _vg(voc, "event", f"{p}when.event.")
    out += [f"{p}when.player.{o}" for o in ("you", "opp")]
    out += [f"{p}when.by.{o}" for o in ("you", "opp")]
    out += _vg(voc, "zone", f"{p}when.from.")
    out += _vg(voc, "zone", f"{p}when.to.")
    out += _vg(voc, "reason", f"{p}when.reason.")
    out += _vg(voc, "reason", f"{p}when.not_reason.")
    out += [f"{p}when.position.top", f"{p}when.position.bottom",
            f"{p}when.position.other"]
    out += _vg(voc, "via", f"{p}when.via.")
    out += [f"{p}when.subj.self", f"{p}when.subj.selector",
            f"{p}when.subj.other"]
    out += _sel_names(f"{p}when.subj.", voc)
    out += [f"{p}when.has.target", f"{p}when.has.attacker",
            f"{p}when.has.opponent"]
    out += _sel_names(f"{p}when.tgt.", voc)
    out += [f"{p}when.ord"]
    out += _vg(voc, "ord_kind", f"{p}when.ord_kind.")
    out += [f"{p}when.ord_cmp.{c}" for c in ORD_CMPS]
    out += [f"{p}when.ord_num.{b}" for b in NB11]
    out += [f"{p}when.flag.{f}" for f in WHEN_FLAGS]
    out += [f"{p}when.cause_by.{o}" for o in ("you", "opp")]
    out += [f"{p}when.cause_kind.{k}" for k in ("spell", "ability")]
    # if / effect / instead / mod
    out += _cond_names(f"{p}if.", voc)
    out += _fx_names(f"{p}fx.", voc)
    out += _ins_names(f"{p}ins.", voc)
    out += _mod_names(f"{p}mod.", voc)
    return out


def _header_names(voc: dict) -> list[str]:
    p = "card."
    out = [f"{p}cost_min.{b}" for b in NB11]
    out += [f"{p}cost_max.{b}" for b in NB11]
    out += [f"{p}power_max.{b}" for b in POWER_B]
    out += [f"{p}breaker.{b}" for b in NB7]
    out += [f"{p}n_faces.{b}" for b in NB7]
    out += [f"{p}n_civs.{b}" for b in NB7]
    out += [f"{p}mana.{b}" for b in NB7]
    out += _vg(voc, "civ", f"{p}civ.")
    out += _vg(voc, "card_type", f"{p}type.")
    out += _vg(voc, "race", f"{p}race.")
    out += [f"{p}n_other_races.{b}" for b in NB7]
    out += [f"{p}n_races.{b}" for b in NB7]
    out += _vg(voc, "keyword", f"{p}kw.")
    out += [f"{p}n_other_kw.{b}" for b in NB7]
    out += [f"{p}n_kw.{b}" for b in NB7]
    out += [f"{p}face.{f}" for f in voc["face_field"]
            if f not in BASIC_FACE_FIELDS]
    out += [f"{p}alt.has_do"] + [f"{p}alt.cost.{b}" for b in NB11]
    out += _cond_names(f"{p}freeif.", voc)
    out += _vg(voc, "filter_key", f"{p}evofilter.")
    out += [f"{p}n_blocks.{b}" for b in NB7]
    out += [f"{p}n_spell_lists.{b}" for b in NB7]
    return out


class FeatureSchema:
    """語彙と特徴名の並び（版つき）。"""

    def __init__(self, vocabularies: dict[str, list[str]],
                 version: int = SCHEMA_VERSION):
        self.vocabs = vocabularies
        self.version = version
        base_block = _block_names(BASE_VOCABULARIES)
        base_header = _header_names(BASE_VOCABULARIES)
        self.block_names = _append_only(base_block,
                                        _block_names(vocabularies))
        self.header_names = _append_only(base_header,
                                         _header_names(vocabularies))
        base_card = (base_header + [f"mean.{n}" for n in base_block]
                     + [f"max.{n}" for n in base_block])
        desired_card = (self.header_names
                        + [f"mean.{n}" for n in self.block_names]
                        + [f"max.{n}" for n in self.block_names])
        self.card_names = _append_only(base_card, desired_card)
        assert len(set(self.block_names)) == len(self.block_names)
        assert len(set(self.card_names)) == len(self.card_names)

    @property
    def block_dim(self) -> int:
        return len(self.block_names)

    @property
    def card_dim(self) -> int:
        return len(self.card_names)


def default_schema(rules) -> FeatureSchema:
    """現在の語彙定義からスキーマを解決する（v1 を接頭辞に保つ）。"""
    cur = current_vocabularies(rules)
    voc = {g: _resolve_vocab(BASE_VOCABULARIES[g], cur.get(g, []))
           for g in BASE_VOCABULARIES}
    return FeatureSchema(voc)


# ------------------------------------------------------------------
# 符号化器（名前→値の dict を作る。組み立てはスキーマの並びで行う）
# ------------------------------------------------------------------
class _Acc:
    """カウント特徴（cap3 正規化）とフラグ特徴の蓄積器。"""

    def __init__(self):
        self.cnt: Counter = Counter()
        self.flg: set[str] = set()

    def C(self, name: str, v: float = 1.0):
        self.cnt[name] += v

    def F(self, name: str):
        self.flg.add(name)

    def dict(self) -> dict[str, float]:
        d = {k: _cap3(v) for k, v in self.cnt.items()}
        for k in self.flg:
            d[k] = 1.0
        return d


class _Voc:
    def __init__(self, vocabs: dict[str, list[str]]):
        self.order = vocabs
        self.sets = {g: set(v) for g, v in vocabs.items()}

    def map(self, group: str, prefix: str, value) -> str:
        if isinstance(value, str) and value in self.sets[group]:
            return f"{prefix}{value}"
        return f"{prefix}other"


def _encode_selector(acc: _Acc, voc: _Voc, sel, p: str):
    if not isinstance(sel, dict):
        return
    z = sel.get("zone")
    for zz in (z if isinstance(z, list) else [z]):
        if isinstance(zz, str):
            acc.C(voc.map("zone", f"{p}zone.", zz))
    owner = sel.get("owner")
    if isinstance(owner, str) and owner in OWNERS:
        acc.F(f"{p}owner.{owner}")
    elif owner is not None:
        acc.F(f"{p}owner.other")
    for key in sel:
        acc.C(voc.map("selector_key", f"{p}key.", key))
    f = sel.get("filter")
    if isinstance(f, dict):
        for fk in f:
            acc.C(voc.map("filter_key", f"{p}filter.", fk))
        for t in f.get("types") or []:
            acc.C(voc.map("card_type", f"{p}filter_type.", t))
        for c in f.get("civs") or []:
            acc.C(voc.map("civ", f"{p}filter_civ.", c))
    cnt = sel.get("count")
    if isinstance(cnt, int) and not isinstance(cnt, bool):
        acc.F(f"{p}count.{_b11(cnt)}")
    elif cnt == "all":
        acc.F(f"{p}count.all")
    elif isinstance(cnt, dict):
        # 個数式の引数セレクタは同じスロットへ統合する（_sel_names 規約）
        _encode_expr(acc, voc, cnt, p, p)


def _encode_expr(acc: _Acc, voc: _Voc, x, p: str, sel_p: str = None):
    """式の符号化。sel_p は引数セレクタを置く prefix（既定は p+"sel."）。

    セレクタの個数式など、置き場所がセレクタ自身しかない文脈では
    sel_p=p として同じスロットへ統合する。
    """
    if sel_p is None:
        sel_p = f"{p}sel."
    if isinstance(x, bool):
        return
    if isinstance(x, int):
        acc.C(f"{p}expr.int")
        acc.F(f"{p}num.{_b11(x)}")
        return
    if not isinstance(x, dict) or len(x) != 1:
        if isinstance(x, dict):
            acc.C(f"{p}expr.other")
        return
    k, v = next(iter(x.items()))
    acc.C(voc.map("expr_kind", f"{p}expr.", k))
    if k in ("count", "civ_count", "distinct_cost_count",
             "distinct_type_count", "total_cost", "total_power",
             "max_power"):
        _encode_selector(acc, voc, v, sel_p)
    elif k == "turn_count" and isinstance(v, dict):
        acc.C(voc.map("tc_kind", f"{p}tc.", v.get("kind")))
        owner = v.get("owner", "you")
        if owner in OWNERS:
            acc.C(f"{p}tc_owner.{owner}")
        if "filter" in v:
            acc.F(f"{p}tc_filter")
            if isinstance(v["filter"], dict):
                for fk in v["filter"]:
                    acc.C(voc.map("filter_key", f"{p}tcfilter.", fk))
        if "from" in v:
            acc.C(voc.map("zone", f"{p}tc_from.", v["from"]))
    elif k in ("entered", "drew", "used_count", "prev_shield_added",
               "bundles") and isinstance(v, dict):
        owner = v.get("owner", "you")
        if owner in OWNERS:
            acc.C(f"{p}cnt_owner.{owner}")
        if isinstance(v.get("filter"), dict):
            for fk in v["filter"]:
                acc.C(voc.map("filter_key", f"{p}tcfilter.", fk))
    elif k == "seals" and isinstance(v, dict):
        owner = v.get("owner", "you")
        if owner in OWNERS:
            acc.C(f"{p}cnt_owner.{owner}")
    elif k in ("sum", "mul") and isinstance(v, list):
        for e in v:
            _encode_expr(acc, voc, e, p, sel_p)


def _encode_cond(acc: _Acc, voc: _Voc, c, p: str):
    if not isinstance(c, dict) or len(c) != 1:
        if isinstance(c, dict):
            acc.C(f"{p}kind.other")
        return
    k, v = next(iter(c.items()))
    acc.C(voc.map("cond_kind", f"{p}kind.", k))
    if k in ("all", "any") and isinstance(v, list):
        for sub in v:
            _encode_cond(acc, voc, sub, p)
    elif k == "not":
        _encode_cond(acc, voc, v, p)
    elif k == "cmp" and isinstance(v, list) and len(v) == 3:
        if v[1] in CMP_NAMES:
            acc.F(f"{p}cmp.{CMP_NAMES[v[1]]}")
        _encode_expr(acc, voc, v[0], p)
        _encode_expr(acc, voc, v[2], p)
    elif k == "exists":
        _encode_selector(acc, voc, v, f"{p}sel.")
    elif k == "is_turn" and v in ("you", "opp"):
        acc.F(f"{p}is_turn.{v}")
    elif k == "power_ge" and isinstance(v, int) \
            and not isinstance(v, bool):
        acc.F(f"{p}power_ge.{_bpower(v)}")


def _encode_count_spec(acc: _Acc, voc: _Voc, cs, p: str):
    """mod の count: セレクタか式かを見て符号化する。"""
    if isinstance(cs, dict) and ("zone" in cs or "filter" in cs
                                  or "owner" in cs):
        _encode_selector(acc, voc, cs, p)
    elif isinstance(cs, dict):
        _encode_expr(acc, voc, cs, p, p)


def _encode_mod(acc: _Acc, voc: _Voc, mod, p: str, flag_keys: bool):
    if not isinstance(mod, dict):
        return
    for key in mod:
        name = voc.map("mod_key", f"{p}key.", key)
        if flag_keys:
            acc.F(name)
        else:
            acc.C(name)
    b = mod.get("breaks")
    if isinstance(b, int) and not isinstance(b, bool):
        acc.F(f"{p}breaks.{_b11(b)}")
    elif isinstance(b, dict):
        if isinstance(b.get("base"), int):
            acc.F(f"{p}breaks.{_b11(b['base'])}")
        if "count" in b:
            _encode_count_spec(acc, voc, b["count"], f"{p}breaks_sel.")
    ba = mod.get("breaks_add")
    if isinstance(ba, int) and not isinstance(ba, bool):
        acc.F(f"{p}breaks_add.{_b11(ba)}")
    elif isinstance(ba, dict) and isinstance(ba.get("amount"), int):
        acc.F(f"{p}breaks_add.{_b11(ba['amount'])}")
    pw = mod.get("power")
    if isinstance(pw, int) and not isinstance(pw, bool):
        acc.F(f"{p}power.{_bsigned(pw)}")
    elif isinstance(pw, dict):
        amt = pw.get("amount")
        if isinstance(amt, int) and not isinstance(amt, bool):
            acc.F(f"{p}power.{_bsigned(amt)}")
        elif isinstance(amt, dict) and "power_of" in amt:
            acc.F(f"{p}power.power_of")
        if "count" in pw:
            _encode_count_spec(acc, voc, pw["count"], f"{p}power_sel.")
    ps = mod.get("power_set")
    if isinstance(ps, int) and not isinstance(ps, bool):
        acc.F(f"{p}power_set.{_bpower(ps)}")
    for ck, nm in (("cost", "cost"), ("cost_min", "cost_min")):
        cv = mod.get(ck)
        if isinstance(cv, int) and not isinstance(cv, bool):
            acc.F(f"{p}{nm}.{_bsigned(cv)}")
    g = mod.get("grant")
    if isinstance(g, (list, tuple)):
        for kw in g:
            acc.C(voc.map("keyword", f"{p}grant_kw.", kw))
        acc.F(f"{p}grant_n.{_b7(len(g))}")
    elif isinstance(g, str):
        acc.C(voc.map("keyword", f"{p}grant_kw.", g))
        acc.F(f"{p}grant_n.{_b7(1)}")
    for ak in ("deny", "allow"):
        av = mod.get(ak)
        vals = av if isinstance(av, (list, tuple)) else [av]
        for a in vals:
            if isinstance(a, str):
                acc.C(voc.map("action", f"{p}{ak}.", a))
            elif isinstance(a, dict) \
                    and isinstance(a.get("action"), str):
                # 条件付き形 {'action': ..., 'other'/'once': ...}:
                # 行動名は取り出す（条件の中身は落とす）
                acc.C(voc.map("action", f"{p}{ak}.", a["action"]))
    nl = mod.get("no_leave")
    if isinstance(nl, dict) and nl.get("except_destroy"):
        acc.F(f"{p}no_leave.except_destroy")
    ar = mod.get("add_races")
    if isinstance(ar, (list, tuple)):
        acc.F(f"{p}add_races_n.{_b7(len(ar))}")


def _encode_fx(acc: _Acc, voc: _Voc, ops, p: str):
    if isinstance(ops, dict):
        ops = [ops]
    if not isinstance(ops, (list, tuple)):
        return
    stat = [0, 0]  # op 総数、最大深さ

    def walk(lst, depth):
        for o in lst:
            if not isinstance(o, dict) or "op" not in o:
                continue
            stat[0] += 1
            stat[1] = max(stat[1], depth)
            op = o["op"]
            acc.C(voc.map("op", f"{p}op.", op))
            if op == "move":
                to = o.get("to")
                if isinstance(to, str):
                    acc.C(voc.map("zone", f"{p}move_to.", to))
                r = o.get("reason")
                if isinstance(r, str):
                    acc.C(voc.map("reason", f"{p}move_reason.", r))
                pos = o.get("position")
                if pos in ("top", "bottom"):
                    acc.F(f"{p}move_pos.{pos}")
                elif pos is not None:
                    acc.F(f"{p}move_pos.other")
                for fk in MOVE_FLAGS:
                    if fk in o:
                        acc.F(f"{p}move_flag.{fk}")
                _encode_selector(acc, voc, o.get("select"),
                                 f"{p}sel.")
            elif op == "modify":
                _encode_mod(acc, voc, o.get("mod"), f"{p}mod.",
                            flag_keys=False)
                dur = o.get("duration")
                if isinstance(dur, str):
                    acc.F(voc.map("duration", f"{p}duration.", dur))
            elif op == "if":
                _encode_cond(acc, voc, o.get("cond"), f"{p}cond.")
            for key in ("count", "times"):
                if isinstance(o.get(key), (dict, int)) \
                        and not isinstance(o.get(key), bool):
                    _encode_expr(acc, voc, o[key], p)
            for key in ("body", "else", "then", "win", "lose",
                        "effect"):
                v = o.get(key)
                if isinstance(v, list):
                    walk(v, depth + 1)
            modes = o.get("modes")
            if isinstance(modes, list):
                for m in modes:
                    if isinstance(m, list):
                        walk(m, depth + 1)

    walk(list(ops), 0)
    acc.F(f"{p}nops.{_b7(stat[0])}")
    d = stat[1]
    acc.F(f"{p}depth.{str(d) if d < 4 else '4p'}")


def _encode_fx_light(acc: _Acc, voc: _Voc, ops, p: str):
    """instead 用の軽量符号化: op 種・移動先・理由・対象だけを追う。"""
    if isinstance(ops, dict):
        ops = [ops]
    if not isinstance(ops, (list, tuple)):
        return
    n = 0

    def walk(lst, depth):
        nonlocal n
        if depth > 4:
            return
        acc.F(f"{p}depth.{min(depth, 4) if depth < 4 else '4p'}")
        for o in lst:
            if not isinstance(o, dict) or "op" not in o:
                continue
            n += 1
            acc.C(voc.map("op", f"{p}op.", o["op"]))
            if o["op"] == "move":
                if isinstance(o.get("to"), str):
                    acc.C(voc.map("zone", f"{p}move_to.", o["to"]))
                rs = o.get("reason")
                for r in (rs if isinstance(rs, list) else [rs]):
                    if isinstance(r, str):
                        acc.C(voc.map("reason", f"{p}move_reason.", r))
                _encode_selector(acc, voc, o.get("select"),
                                 f"{p}sel.")
            for key in ("body", "else", "then", "win", "lose",
                        "effect"):
                v = o.get(key)
                if isinstance(v, list):
                    walk(v, depth + 1)
            modes = o.get("modes")
            if isinstance(modes, list):
                for m in modes:
                    if isinstance(m, list):
                        walk(m, depth + 1)

    walk(list(ops), 0)
    acc.F(f"{p}nops.{_b7(n)}")


def _encode_ability(acc: _Acc, voc: _Voc, ab: dict, list_kind: str,
                    face_idx: int):
    p = "ab."
    acc.F(f"{p}list.{list_kind}")
    acc.F(f"{p}face.{min(face_idx, 1)}")
    if not isinstance(ab, dict):
        return
    kind = ab.get("kind")
    if isinstance(kind, str):
        acc.F(voc.map("kind", f"{p}kind.", kind))
    for k in ("when", "if", "effect", "instead", "mod", "cost"):
        if k in ab:
            acc.F(f"{p}has.{k}")
    for k in ab:
        if k not in STRUCTURAL_AB_KEYS:
            acc.F(voc.map("abkey", f"{p}key.", k))
    aff = ab.get("affects")
    if aff == "self":
        acc.F(f"{p}affects.self")
    elif isinstance(aff, dict):
        acc.F(f"{p}affects.selector")
        owner = aff.get("owner")
        if owner in OWNERS:
            acc.F(f"{p}affects.owner.{owner}")
        z = aff.get("zone")
        for zz in (z if isinstance(z, list) else [z]):
            if isinstance(zz, str):
                acc.C(voc.map("zone", f"{p}affects.zone.", zz))
    elif aff is not None:
        acc.F(f"{p}affects.other")
    zone = ab.get("zone")
    for zz in (zone if isinstance(zone, list) else [zone]):
        if isinstance(zz, str):
            acc.F(voc.map("zone", f"{p}zone.", zz))
    cost = ab.get("cost")
    if isinstance(cost, int) and not isinstance(cost, bool):
        acc.F(f"{p}cost.{_b11(cost)}")
    elif isinstance(cost, dict):
        acc.F(f"{p}cost.dict")
    kw = ab.get("keyword")
    if isinstance(kw, str):
        acc.F(voc.map("keyword", f"{p}kw.", kw))
    for lk in ("cast_limit", "untap_limit"):
        lv = ab.get(lk)
        if isinstance(lv, dict) and isinstance(lv.get("count"), int) \
                and not isinstance(lv.get("count"), bool):
            acc.F(f"{p}limit.{lk}.{_b7(lv['count'])}")
    w = ab.get("when")
    if isinstance(w, dict):
        ev = w.get("event")
        if isinstance(ev, str):
            acc.F(voc.map("event", f"{p}when.event.", ev))
        for key, nm in (("player", "player"), ("by", "by")):
            if w.get(key) in ("you", "opp"):
                acc.F(f"{p}when.{nm}.{w[key]}")
        for key, nm in (("from", "from"), ("to", "to")):
            vals = w.get(key)
            for zz in (vals if isinstance(vals, list) else [vals]):
                if isinstance(zz, str):
                    acc.F(voc.map("zone", f"{p}when.{nm}.", zz))
        for key, nm in (("reason", "reason"),
                        ("not_reason", "not_reason")):
            vals = w.get(key)
            for r in (vals if isinstance(vals, list) else [vals]):
                if isinstance(r, str):
                    acc.F(voc.map("reason", f"{p}when.{nm}.", r))
        pos = w.get("position")
        if pos in ("top", "bottom"):
            acc.F(f"{p}when.position.{pos}")
        elif pos is not None:
            acc.F(f"{p}when.position.other")
        via = w.get("via")
        if isinstance(via, str):
            acc.F(voc.map("via", f"{p}when.via.", via))
        subj = w.get("subject")
        if subj == "self":
            acc.F(f"{p}when.subj.self")
        elif isinstance(subj, dict):
            acc.F(f"{p}when.subj.selector")
            _encode_selector(acc, voc, subj, f"{p}when.subj.")
        elif subj is not None:
            acc.F(f"{p}when.subj.other")
        for tk in ("target", "attacker", "opponent"):
            if tk in w:
                acc.F(f"{p}when.has.{tk}")
                if isinstance(w[tk], dict):
                    _encode_selector(acc, voc, w[tk],
                                     f"{p}when.tgt.")
        o = w.get("ord")
        if isinstance(o, dict):
            acc.F(f"{p}when.ord")
            acc.F(voc.map("ord_kind", f"{p}when.ord_kind.",
                          o.get("kind")))
            for c in ORD_CMPS:
                if isinstance(o.get(c), int) \
                        and not isinstance(o.get(c), bool):
                    acc.F(f"{p}when.ord_cmp.{c}")
                    acc.F(f"{p}when.ord_num.{_b11(o[c])}")
        for f in WHEN_FLAGS:
            if f in w:
                acc.F(f"{p}when.flag.{f}")
        cause = w.get("cause")
        if isinstance(cause, dict):
            if cause.get("by") in ("you", "opp"):
                acc.F(f"{p}when.cause_by.{cause['by']}")
            ck = cause.get("kind")
            for k in (ck if isinstance(ck, list) else [ck]):
                if k in ("spell", "ability"):
                    acc.F(f"{p}when.cause_kind.{k}")
    if "if" in ab:
        _encode_cond(acc, voc, ab.get("if"), f"{p}if.")
    if "effect" in ab:
        _encode_fx(acc, voc, ab.get("effect"), f"{p}fx.")
    if "instead" in ab:
        _encode_fx_light(acc, voc, ab.get("instead"), f"{p}ins.")
    if "mod" in ab:
        _encode_mod(acc, voc, ab.get("mod"), f"{p}mod.",
                    flag_keys=True)


def _units(cd) -> list:
    faces = getattr(cd, "faces", None)
    return list(faces) if faces else [cd]


def _card_blocks_as_dicts(cd, voc: _Voc) -> list[dict[str, float]]:
    """カードの能力ブロック列（名前→値の dict）。"""
    out: list[dict[str, float]] = []
    for fi, u in enumerate(_units(cd)):
        for ab in getattr(u, "abilities", None) or []:
            if isinstance(ab, dict):
                acc = _Acc()
                _encode_ability(acc, voc, ab, "ability", fi)
                out.append(acc.dict())
        for key, label in SPELL_LIST_KEYS:
            lst = getattr(u, key, None)
            if lst:
                acc = _Acc()
                _encode_ability(acc, voc, {"effect": lst}, label, fi)
                out.append(acc.dict())
    return out


def _encode_header(acc: _Acc, voc: _Voc, cd, n_blocks: int,
                   n_spell_lists: int):
    p = "card."
    units = _units(cd)
    costs = [int(getattr(u, "cost", 0) or 0) for u in units]
    powers = [int(getattr(u, "power", 0) or 0) for u in units]
    if costs:
        acc.F(f"{p}cost_min.{_b11(min(costs))}")
        acc.F(f"{p}cost_max.{_b11(max(costs))}")
    if powers:
        acc.F(f"{p}power_max.{_bpower(max(powers))}")
    breaker = 0
    for u in units:
        for k in getattr(u, "keywords", None) or []:
            if k in BREAKERS:
                breaker = max(breaker, BREAKERS[k])
        for ab in getattr(u, "abilities", None) or []:
            if not isinstance(ab, dict):
                continue
            stack = [ab]
            while stack:
                node = stack.pop()
                if isinstance(node, dict):
                    m = node.get("mod")
                    if isinstance(m, dict):
                        if isinstance(m.get("breaks"), int):
                            breaker = max(breaker, m["breaks"])
                        g = m.get("grant")
                        if isinstance(g, (list, tuple)):
                            for k in g:
                                if k in BREAKERS:
                                    breaker = max(breaker, BREAKERS[k])
                    stack.extend(node.values())
                elif isinstance(node, (list, tuple)):
                    stack.extend(node)
    types = set(getattr(cd, "types", None) or [])
    if breaker == 0 and types & {"creature", "evolution",
                                  "exile_creature", "dream_creature"}:
        breaker = 1
    acc.F(f"{p}breaker.{_b7(breaker)}")
    acc.F(f"{p}n_faces.{_b7(len(units))}")
    civs = getattr(cd, "civs", None) or []
    acc.F(f"{p}n_civs.{_b7(len(civs))}")
    acc.F(f"{p}mana.{_b7(int(getattr(cd, 'mana', 1) or 0))}")
    for c in civs:
        acc.F(voc.map("civ", f"{p}civ.", c))
    for t in types:
        acc.F(voc.map("card_type", f"{p}type.", t))
    races: set[str] = set()
    kws: set[str] = set()
    for u in units:
        races |= set(getattr(u, "races", None) or [])
        kws |= set(getattr(u, "keywords", None) or [])
    other_races = 0
    for r in races:
        if r in voc.sets["race"]:
            acc.F(f"{p}race.{r}")
        else:
            other_races += 1
    acc.F(f"{p}n_other_races.{_b7(other_races)}")
    acc.F(f"{p}n_races.{_b7(len(races))}")
    other_kw = 0
    for k in kws:
        if k in voc.sets["keyword"]:
            acc.F(f"{p}kw.{k}")
        else:
            other_kw += 1
    acc.F(f"{p}n_other_kw.{_b7(other_kw)}")
    acc.F(f"{p}n_kw.{_b7(len(kws))}")
    for f in voc.order["face_field"]:
        if f in BASIC_FACE_FIELDS:
            continue
        for u in units:
            v = getattr(u, f, None)
            if v not in (None, False, 0, [], {}, ""):
                acc.F(f"{p}face.{f}")
                break
    for u in units:
        ac = getattr(u, "alt_cost", None)
        if isinstance(ac, dict):
            if "do" in ac:
                acc.F(f"{p}alt.has_do")
            if isinstance(ac.get("cost"), int):
                acc.F(f"{p}alt.cost.{_b11(ac['cost'])}")
        fi = getattr(u, "free_if", None)
        if isinstance(fi, dict):
            _encode_cond(acc, voc, fi, f"{p}freeif.")
        ef = getattr(u, "evolve_from", None)
        if isinstance(ef, dict):
            for fk in ef:
                acc.C(voc.map("filter_key", f"{p}evofilter.", fk))
    acc.F(f"{p}n_blocks.{_b7(n_blocks)}")
    acc.F(f"{p}n_spell_lists.{_b7(n_spell_lists)}")


_SPELL_LIST_NAMES = {f"ab.list.{lk}" for lk in LIST_KINDS
                     if lk != "ability"}


def _card_as_dict(cd, voc: _Voc) -> dict[str, float]:
    blocks = _card_blocks_as_dicts(cd, voc)
    n_spell = sum(1 for b in blocks
                  if any(k in b for k in _SPELL_LIST_NAMES))
    acc = _Acc()
    _encode_header(acc, voc, cd, len(blocks), n_spell)
    d = acc.dict()
    if blocks:
        keys: set[str] = set()
        for b in blocks:
            keys |= set(b)
        for k in keys:
            vals = [b.get(k, 0.0) for b in blocks]
            d[f"mean.{k}"] = float(sum(vals) / len(vals))
            d[f"max.{k}"] = float(max(vals))
    return d


# ------------------------------------------------------------------
# 公開 API
# ------------------------------------------------------------------
def _voc_of(schema: FeatureSchema) -> _Voc:
    return _Voc(schema.vocabs)


def card_ability_blocks(cd, schema: FeatureSchema) -> np.ndarray:
    """能力ブロック列 [n_blocks, block_dim]（注意モデル用）。"""
    voc = _voc_of(schema)
    dicts = _card_blocks_as_dicts(cd, voc)
    mat = np.zeros((len(dicts), schema.block_dim), dtype=np.float32)
    idx = {n: i for i, n in enumerate(schema.block_names)}
    for r, d in enumerate(dicts):
        for k, v in d.items():
            j = idx.get(k)
            if j is not None:
                mat[r, j] = v
    return mat


def card_vector(cd, schema: FeatureSchema) -> np.ndarray:
    """プーリング済みカードベクトル [card_dim]（AttrModel 互換）。"""
    voc = _voc_of(schema)
    d = _card_as_dict(cd, voc)
    vec = np.zeros(schema.card_dim, dtype=np.float32)
    idx = {n: i for i, n in enumerate(schema.card_names)}
    for k, v in d.items():
        j = idx.get(k)
        if j is not None:
            vec[j] = v
    return vec


def build_card_matrix(rules, vocab, schema: FeatureSchema | None = None
                      ) -> tuple[np.ndarray, list[str], int]:
    """全カードのカードベクトル行列 [len(vocab), card_dim] と
    特徴名・スキーマ版を返す。行は vocab の添字（0 = PAD はゼロ行）。"""
    schema = schema or default_schema(rules)
    mat = np.zeros((len(vocab), schema.card_dim), dtype=np.float32)
    voc = _voc_of(schema)
    idx = {n: i for i, n in enumerate(schema.card_names)}
    for defn, i in vocab.index.items():
        d = _card_as_dict(rules.cards[defn], voc)
        for k, v in d.items():
            j = idx.get(k)
            if j is not None:
                mat[i, j] = v
    return mat, list(schema.card_names), schema.version


# ------------------------------------------------------------------
# カバレッジ測定
# ------------------------------------------------------------------
def _audit_selector(sel, cnt: dict[str, Counter]):
    if not isinstance(sel, dict):
        return
    z = sel.get("zone")
    for zz in (z if isinstance(z, list) else [z]):
        if isinstance(zz, str):
            cnt["zone"][zz] += 1
    for key in sel:
        cnt["selector_key"][key] += 1
    f = sel.get("filter")
    if isinstance(f, dict):
        for fk in f:
            cnt["filter_key"][fk] += 1
        for t in f.get("types") or []:
            cnt["card_type"][t] += 1
    cntv = sel.get("count")
    if isinstance(cntv, dict):
        _audit_expr(cntv, cnt)


def _audit_expr(x, cnt: dict[str, Counter]):
    if not isinstance(x, dict) or len(x) != 1:
        return
    k, v = next(iter(x.items()))
    cnt["expr_kind"][k] += 1
    if k in ("count", "civ_count", "distinct_cost_count",
             "distinct_type_count", "total_cost", "total_power",
             "max_power"):
        _audit_selector(v, cnt)
    elif k == "turn_count" and isinstance(v, dict):
        cnt["tc_kind"][str(v.get("kind"))] += 1
        if isinstance(v.get("filter"), dict):
            for fk in v["filter"]:
                cnt["filter_key"][fk] += 1
    elif isinstance(v, dict) and ("zone" in v or "filter" in v):
        _audit_selector(v, cnt)
    elif k in ("sum", "mul") and isinstance(v, list):
        for e in v:
            _audit_expr(e, cnt)


def _audit_cond(c, cnt: dict[str, Counter]):
    if not isinstance(c, dict) or len(c) != 1:
        return
    k, v = next(iter(c.items()))
    cnt["cond_kind"][k] += 1
    if k in ("all", "any") and isinstance(v, list):
        for sub in v:
            _audit_cond(sub, cnt)
    elif k == "not":
        _audit_cond(v, cnt)
    elif k == "cmp" and isinstance(v, list) and len(v) == 3:
        _audit_expr(v[0], cnt)
        _audit_expr(v[2], cnt)
    elif k == "exists":
        _audit_selector(v, cnt)


def _audit_mod(mod, cnt: dict[str, Counter]):
    if not isinstance(mod, dict):
        return
    for key, v in mod.items():
        cnt["mod_key"][key] += 1
        if key == "grant" and isinstance(v, (list, tuple)):
            for kw in v:
                cnt["keyword"][str(kw)] += 1
        if key in ("deny", "allow"):
            for a in (v if isinstance(v, (list, tuple)) else [v]):
                if isinstance(a, dict) \
                        and isinstance(a.get("action"), str):
                    cnt["action"][a["action"]] += 1
                else:
                    cnt["action"][str(a)] += 1
        if isinstance(v, dict) and "count" in v:
            cs = v["count"]
            if isinstance(cs, dict) and ("zone" in cs
                                         or "filter" in cs):
                _audit_selector(cs, cnt)
            elif isinstance(cs, dict):
                _audit_expr(cs, cnt)


def _audit_fx(ops, cnt: dict[str, Counter]):
    if isinstance(ops, dict):
        ops = [ops]
    if not isinstance(ops, (list, tuple)):
        return
    for o in ops:
        if not isinstance(o, dict) or "op" not in o:
            continue
        cnt["op"][str(o["op"])] += 1
        if o["op"] == "move":
            if isinstance(o.get("to"), str):
                cnt["zone"][o["to"]] += 1
            if isinstance(o.get("reason"), str):
                cnt["reason"][o["reason"]] += 1
            _audit_selector(o.get("select"), cnt)
        elif o["op"] == "modify":
            _audit_mod(o.get("mod"), cnt)
            if isinstance(o.get("duration"), str):
                cnt["duration"][o["duration"]] += 1
        elif o["op"] == "if":
            _audit_cond(o.get("cond"), cnt)
        for key in ("body", "else", "then", "win", "lose", "effect"):
            v = o.get(key)
            if isinstance(v, list):
                _audit_fx(v, cnt)
        modes = o.get("modes")
        if isinstance(modes, list):
            for m in modes:
                if isinstance(m, list):
                    _audit_fx(m, cnt)


def coverage_report(rules) -> dict:
    """全カードを走査し、プリミティブごとの「その他」率と、
    旧属性（attributes.py）との表現力の差を測る。

    戻り値: {"groups": {グループ: {total, other, other_rate,
    top_other}}, "abilities": {...}, "old_schema": {...}}
    """
    voc = current_vocabularies(rules)
    reg = {g: set(v) for g, v in voc.items()}
    groups = ["kind", "event", "zone", "reason", "via", "filter_key",
              "selector_key", "ord_kind", "tc_kind", "op", "mod_key",
              "duration", "action", "keyword", "abkey", "card_type",
              "cond_kind", "expr_kind"]
    cnt: dict[str, Counter] = {g: Counter() for g in groups}
    ab_stats = Counter()
    mod_key_occ = 0
    mod_key_dedicated_old = 0
    OLD_MOD_DEDICATED = {"power", "grant", "deny", "allow", "no_leave",
                         "indestructible"}
    op_occ = 0
    event_occ = 0

    def audit_ability(ab):
        if not isinstance(ab, dict):
            return
        ab_stats["total"] += 1
        if isinstance(ab.get("kind"), str):
            cnt["kind"][ab["kind"]] += 1
        for k in ab:
            if k not in STRUCTURAL_AB_KEYS:
                cnt["abkey"][k] += 1
        if "if" in ab:
            ab_stats["with_if"] += 1
            _audit_cond(ab["if"], cnt)
            if "turn_count" in str(ab["if"]):
                ab_stats["with_if_turn_count"] += 1
        if "instead" in ab:
            ab_stats["with_instead"] += 1
        if "cast_limit" in ab:
            ab_stats["with_cast_limit"] += 1
        if "keyword" in ab:
            cnt["keyword"][str(ab["keyword"])] += 1
        w = ab.get("when")
        if isinstance(w, dict):
            if isinstance(w.get("event"), str):
                cnt["event"][w["event"]] += 1
            for key in ("from", "to"):
                vals = w.get(key)
                for zz in (vals if isinstance(vals, list) else [vals]):
                    if isinstance(zz, str):
                        cnt["zone"][zz] += 1
            for key in ("reason", "not_reason"):
                vals = w.get(key)
                for r in (vals if isinstance(vals, list) else [vals]):
                    if isinstance(r, str):
                        cnt["reason"][r] += 1
            if isinstance(w.get("via"), str):
                cnt["via"][w["via"]] += 1
            if "player" in w:
                ab_stats["with_when_player"] += 1
            if "not_reason" in w:
                ab_stats["with_not_reason"] += 1
            if "ord" in w:
                ab_stats["with_ord"] += 1
                if isinstance(w["ord"], dict):
                    cnt["ord_kind"][str(w["ord"].get("kind"))] += 1
            for sk in ("subject", "target", "attacker", "opponent"):
                if isinstance(w.get(sk), dict):
                    _audit_selector(w[sk], cnt)
        if "mod" in ab:
            _audit_mod(ab["mod"], cnt)
        for key in ("effect", "instead"):
            if key in ab:
                _audit_fx(ab[key], cnt)

    for cd in rules.cards.values():
        for u in _units(cd):
            for k in getattr(u, "keywords", None) or []:
                cnt["keyword"][k] += 1
            for t in getattr(u, "types", None) or []:
                cnt["card_type"][t] += 1
            fi = getattr(u, "free_if", None)
            if isinstance(fi, dict):
                ab_stats["with_free_if"] += 1
                _audit_cond(fi, cnt)
            for ab in getattr(u, "abilities", None) or []:
                audit_ability(ab)
            for key, _label in SPELL_LIST_KEYS:
                lst = getattr(u, key, None)
                if lst:
                    _audit_fx(lst, cnt)

    out_groups = {}
    for g in groups:
        total = sum(cnt[g].values())
        other = sum(v for k, v in cnt[g].items() if k not in reg[g])
        out_groups[g] = {
            "total": total,
            "other": other,
            "other_rate": (other / total) if total else 0.0,
            "top_other": [(k, v) for k, v in cnt[g].most_common()
                          if k not in reg[g]][:10],
        }
        if g == "op":
            op_occ = total
        if g == "event":
            event_occ = total
        if g == "mod_key":
            mod_key_occ = total
            mod_key_dedicated_old = sum(
                v for k, v in cnt[g].items() if k in OLD_MOD_DEDICATED)

    # 旧属性の採用リストでの被覆（頻度閾値で落ちる分の定量化）
    from . import attributes as _old
    corpus = _old._Corpus(rules)
    op_covered_old = sum(v for k, v in cnt["op"].items()
                         if k in corpus.op_idx)
    ev_covered_old = sum(v for k, v in cnt["event"].items()
                         if k in corpus.ev_idx)
    old_schema = {
        "op_occurrences": op_occ,
        "op_covered_by_dedicated": op_covered_old,
        "op_dedicated_rate": (op_covered_old / op_occ) if op_occ else 0.0,
        "event_occurrences": event_occ,
        "event_covered_by_dedicated": ev_covered_old,
        "event_dedicated_rate": (ev_covered_old / event_occ)
        if event_occ else 0.0,
        "mod_key_occurrences": mod_key_occ,
        "mod_key_dedicated_buckets": mod_key_dedicated_old,
        "mod_key_dedicated_rate": (mod_key_dedicated_old / mod_key_occ)
        if mod_key_occ else 0.0,
        "condition_atoms_total": sum(cnt["cond_kind"].values())
        + sum(cnt["expr_kind"].values()),
        "condition_coverage": 0.0,  # 旧属性は if を一切符号化しない
    }
    return {"groups": out_groups, "abilities": dict(ab_stats),
            "old_schema": old_schema}
