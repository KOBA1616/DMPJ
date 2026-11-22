"""カード・ゾーン・キーワード定義の読み込みと検証。

効果DSLは閉じた語彙（設計判断④）。ここで未知の op / 引数 / イベント / 能力種別 / mod を弾くことで、
LLM が変換したカードデータの機械チェックを兼ねる。op の引数の型は base/opvocab.py の OP_ARGS が正。
"""
from __future__ import annotations

import copy
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from ..base.store import REPO

DATA = REPO / "data"


def core_ops() -> dict[str, dict[str, str]]:
    """コア語彙 = base/opvocab.py の op と引数の型（実装はエンジンが登録する）。ここに無い op はマクロ（op_macros.yaml）で定義されていなければエラー。"""
    from ..base.opvocab import OP_ARGS
    return OP_ARGS

EVENTS = {"move", "draw", "cast", "summon", "attack", "block", "break", "tap", "untap",
          "turn_start", "turn_end", "battle_win", "battle_lose", "choose", "battle", "battle_start", "attack_end", "attack_unblocked", "break_before", "lose", "mugon_used", "evolve_base", "link_established",
          "use_s_trigger", "battle_end", "trigger", "janken"}   # trigger（第270弾）: 自身の出た時能力が誘発したこと。janken（第271弾）: ジャンケン1投の公開（両者の手・勝者）。あいこも1投として発表する
ABILITY_KINDS = {"trigger", "replace", "static", "declare", "activate", "silent", "state", "partner"}   # state: 状態を常に見て、満たされたら勝敗が決まる常在効果（if と effect: [win/lose]）。partner: [P]能力（単独では機能せず、キズナ等で「使う」ことで解決する）
ABILITY_KEYS = {"kind", "when", "if", "effect", "instead", "optional", "affects", "mod", "zone", "keyword", "cost", "id",
                "once_per_turn", "first_time", "sst", "stp", "odrive", "choukon", "bazurenda", "any_attacker", "continue", "dswitch", "sforce", "fort_e", "redirect", "accel", "no_lose", "mana_boost", "suppress_triggers", "untap_limit", "protect_hand", "mana_all_civs", "cast_limit", "group"}
REASONS = {"put", "destroy", "return", "discard", "charge", "summon", "cast", "break",
           "draw", "battle", "sba", "resolve", "evolve", "seal"}
LOSE_REASONS = {"direct_attack", "deck_out", "state", "effect"}   # 第188弾: 敗北イベントの reason（when の照合用。移動の reason とは別）
VIAS = {"revolution_change", "generate", "d_d_d", "rinne"}   # 出し方の印（「革命チェンジによって出た時」「D・D・Dによって出た時」「輪廻∞で唱えた時」など）
DURATIONS_FIXED = {"end_of_turn", "during_attack", "permanent", "until_next_own_turn_start", "until_next_own_turn_end", "until_next_opp_turn_end"}
MOD_KEYS = {"power", "power_set", "grant", "allow", "deny", "breaks", "breaks_add", "breaks_max", "breaks_per_power", "battle_power", "power_when", "cost", "cost_min", "cost_may", "sac_reduce", "opt_reduce", "ignore", "ignore_ids", "gain", "require", "add_of", "add_races", "add_names", "no_leave", "must_be_attacked", "must_be_chosen", "must_attack_creature", "battle_indestructible", "win_all_battles", "add_civs", "indestructible", "double_power", "crystal_soul", "mana_number", "evo_reduce", "cross_reduce", "player_rush", "trigger_double"}
REQUIRES = {"attack", "block"}   # 強制（506.1b 攻撃しなければならない, 507.1b ブロックしなければならない）
POSITIONS = {"top", "bottom"}
PERMANENT_TYPES = {"tamaseed", "field", "cross_gear"}   # 手札から実行してバトルゾーンに出るクリーチャー以外のカード（315, 308, 303）
CARD_TYPES = {"creature", "spell", "evolution", "d2_field", "dream_creature", "g_castle", "exile_creature", "dragonic_field"} | PERMANENT_TYPES   # d2_field: D2フィールドの型印（特殊タイプ D2。types には field と併記する。第151弾）。dream_creature: ドリーム・クリーチャーの型印（第174弾）。g_castle: G城の型印（第176弾）。exile_creature: エグザイル・クリーチャーの型印（第266弾。types には creature と併記する）。dragonic_field: ドラゴニック・フィールドの型印（第303弾。types には field と併記する）
CIVS = {"light", "water", "darkness", "fire", "nature", "zero"}
SELECTOR_KEYS = {"zone", "owner", "owner_of", "filter", "count", "up_to", "from_top", "from_bottom", "chooser", "ref", "other",
                 "under_of", "bundle_of", "look", "exlife_of", "castle_of", "total_cost_le", "total_cost_ge", "total_power_le", "total_power_ge",
                 "distinct_costs", "distinct_from", "distinct_names", "exclude", "extremal",
                 "crossed_to", "host_of"}   # crossed_to: 「そのクリーチャーにクロスされているギア」。host_of: 「そのギアをクロスしているクリーチャー」（第170弾）。castle_of: 「その城が要塞化しているシールド」（第178弾）
FILTER_KEYS = {"any_of", "types", "not_types", "civs", "civs_all", "not_civs", "races", "races_all", "race_has", "not_race_has", "name", "name_has", "not_name",
               "cost_le", "cost_ge", "power_le", "power_ge", "tapped", "keyword", "not_keyword", "multicolor", "colorless", "hyper", "face_down", "face_up", "neo", "vanilla", "sealed", "evolution", "ultimate_evolution", "mugen_climb", "partner", "twinpact", "vividraw", "fushigi", "linked_god", "entered_this_turn",
               "spell_cost_le", "spell_cost_ge",   # 呪文面（ツインパクトの呪文側）のコスト（第184弾）
               "crossed", "crossed_ge", "crossed_le", "crossed_name", "evo_source_of", "fortifying", "fortified", "exlife"}   # クロス状態（第170弾）: crossed はギアがクロスされているか、crossed_ge/le はその枚数、crossed_name はその名前のギアがクロスされているか。evo_source_of（第177弾）: そのクリーチャーの進化元になれるカード（値は "self" / 変数名）。fortifying（第178弾）: シールドを要塞化している城。fortified（第178弾）: 要塞化されたシールド。exlife（第237弾）: EXライフで紐付いたシールドか
FILTER_EXPR_KEYS = {"cost_le", "cost_ge", "power_le", "power_ge", "races", "civs", "not_civs", "name", "crossed_ge", "crossed_le", "spell_cost_le", "spell_cost_ge"}   # 値に式を書ける（解決時に計算）。civs / not_civs / name は宣言プリミティブ（{declared:}）の受け口（バンドB U3／バンドC2 U97）
# 履歴カウンタ（式 {turn_count: ...}）の kind 列挙（バンドC1 U19＋統一で追加した分）。
# owner に any を許すのは destroyed と attack だけ（他は you/opp）
TURN_COUNT_KINDS = {"shield_put", "shield_left", "mana_put", "cast", "summon", "attack", "destroyed",
                    "broke_by_self", "broke_by_self_attack", "draw", "broken", "enter", "discard", "leave", "tap", "untap", "untap_creature",
                    "block", "enter_unpaid", "attack_by", "attack_on", "dynamo_tap"}   # dynamo_tap: 第322弾。このターンに「ダイナモ」能力を使うためにタップした自分のダイナモの体数（op_modify の add_of 適用で記録。重複は数えない）
TURN_COUNT_ANY_KINDS = {"destroyed", "attack"}
ORD_KINDS = {"mana_put", "enter", "cast", "summon", "draw", "attack", "attack_by"}   # when の {ord: ...} で照合できる kind


def split_races(races) -> list[str]:
    """原本の種族は「A/B/C」のように「/」区切りの文字列。「/」で区切られた部分が1種族（・は種族名の一部）。"""
    return [r.strip() for x in races for r in str(x).split("/") if r.strip()]


class DefError(ValueError):
    pass


@dataclass
class Face:
    """カードの1つの面（ツインパクトのクリーチャー側・呪文側など。810）。"""
    name: str
    types: list[str]
    civs: list[str]
    cost: int
    power: int = 0
    races: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    abilities: list[dict] = field(default_factory=list)
    spell: list[dict] = field(default_factory=list)
    sst_spell: list[dict] = field(default_factory=list)   # スーパー・S・トリガーで得る追加の解決 ops
    stp_spell: list[dict] = field(default_factory=list)   # S・トリガー・プラスで得る追加の解決 ops
    odrive_spell: list[dict] = field(default_factory=list)   # O・ドライブで得る追加の解決 ops（呪文側）
    o_drive: dict | None = None                           # O・ドライブ: {civ, count} または {civs: {文明: 枚数}, each?} 召喚時に追加でタップできるマナ
    mugen_climb: dict | None = None                       # ムゲンクライム: {tap, cost, civs} 自分のクリーチャーをタップして手札/墓地から実行
    alt_cost: dict | None = None                          # 代替コスト: {cost, civs} または {do: [{zone, filter?, count, to, reason}...]}
    vividraw: dict | None = None                          # ビビッドロー: {cost, civs} 引いたターンに表向きにすると代替コストで実行できる
    fushigi: dict | None = None                           # フシギバース: {cost, civs, min} 自分のクリーチャー1体をタップしてマナに置き、差額を払って墓地から召喚
    recycle: dict | None = None                           # リサイクル: {cost, civs?} 墓地から代替コストで唱え、解決後は山札の一番下へ（第172弾）
    grave_cast: bool = False                              # 墓地から通常コストで唱えられる（解決後は山札の一番下へ。第226弾）
    rinne: bool = False                                     # 輪廻∞（第267弾）: 呪文側をバトルゾーンに置いたまま通常コストで唱えられる
    mana_bakutan: int | None = None                       # マナ爆誕: 自分のマナゾーンから固定コストで召喚できる（第191弾。0 は支払わずに召喚）
    link_to: list | None = None                           # G・リンク（名前指定・4方向。第197弾）: [{name, pos}]。pos は相手から見た自分の位置
    deck_evolution: dict | None = None                    # デッキ進化: {count?, rest_to?, blind?, shuffle_first?, stack_all?} 山札の上からめくって重ねて出す（第173弾。stack_all はデッキ進化GV: 上から count 枚を全部重ねる。第293弾）
    evolve_from: dict | None = None                       # 進化元の条件（801.1a）。filter 形式
    evolve_zone: str = "bz"                               # 進化元を探すゾーン（超無限墓地進化は graveyard）
    evolve_any: bool = False                              # 進化元を1体以上選べる（超無限墓地進化）
    evolve_count: int = 1                                 # 進化元をちょうどこの数だけ重ねる（進化GV は3体）
    evolve_max: int | None = None                         # evolve_any の上限（「3体まで」形マナ進化GV。第293弾）
    evolve_civs: tuple = ()                               # 超無限進化の文明条件: 選んだ進化元の集合がこの文明を全て含むこと（第218弾）
    evolve_zones: tuple = ()                              # 超無限進化Ω: 進化元を探すゾーンの集合（evolve_zone の代わり。第218弾）
    soul_shift: dict | None = None                        # ソウルシフト∞: {floor} 進化元の合計コストぶん軽減し、floor 未満にはならない（第218弾）
    cost_reduce_per_evo: int = 0                          # 進化元1体につき召喚コストをいくら減らすか
    tap_reduce: int = 0                                   # ハイパーエナジー: コストが異なる自分のクリーチャー1体をタップするごとに減るコスト
    s_back: str | dict | None = None                      # S・バック: 文明名（文字列）か、捨てるカードの条件（filter。第52弾で種族・複合文明・ツインパクトに対応）
    free_if: dict | None = None                           # 条件を満たす間はコストを支払わずに召喚できる（G・ゼロ）
    galaxy_shield: dict | None = None                     # ギャラクシールド: {cost, civs} 代替コストで表向きにシールド化する
    bazurenda: dict | None = None                         # バズレンダ: {cost, civs} 支払い時に追加でこのコストを好きな回数払える
    tap_entry: bool = False                               # タップして出してもよい（第259弾）: 召喚時にタップ状態で出すか選べる
    neo: bool = False                                     # NEO進化: 通常召喚も、evolve_from の上に重ねることもできる
    grave_evo: bool = False                               # 墓地進化: 通常召喚も、自分の墓地のクリーチャーの上に重ねて出すこともできる（evolve_zone: graveyard と併用）
    star: bool = False                                    # スター進化: 離れる時は一番上のカードだけが離れ、下は残る
    s_max: bool = False                                   # S-MAX進化: 進化元を必要とせず、通常のクリーチャーとして召喚できる
    ace: bool = False                                     # ACEタマシード: 条件を満たす間だけクリーチャーとして扱う（第179弾）
    hyper: bool = False                                   # ハイパー化（他の自分のクリーチャー1体をタップしてハイパーモードを解放できる）
    crystal_soul: int = 0                                 # 水晶ソウルN: 召喚／唱える時に裏向きマナの数字が N になる（0＝持たない）
    mana_boost: dict | None = None                        # マナブースト（第212弾）: このカードを出す支払いでのみ、条件に合うマナの数字を value にする {filter?, value, optional?}
    launcher: dict | None = None                          # ランチャーE（第233弾）: 唱える時に自分の条件クリーチャーを好きな数タップし、変数 launcher に渡す {filter}
    evo_base_reduce: dict | None = None                   # 進化元依存の軽減（第234弾）: 選んだ進化元が filter に合えば amount 軽減 {filter, amount, min?}
    evolve_total_cost_ge: int | None = None               # 超無限進化のコスト合計条件（第236弾）: 選んだ進化元の合計コストがこの値以上になるまで選ぶ
    resolve_to: str = "graveyard"                         # 呪文の解決後の置き場所（チャージャー等）
    resolve_face_down: bool = False                       # 解決後の置き場所に裏向きで置く（水晶チャージャー。第228弾）
    after_resolve: list[dict] = field(default_factory=list)

    def is_creature(self) -> bool:
        return "creature" in self.types

    def is_spell(self) -> bool:
        return "spell" in self.types

    def is_permanent(self) -> bool:
        """クリーチャーでなく、実行するとバトルゾーンに出るカード（タマシード・フィールド・クロスギア）。"""
        return not self.is_creature() and bool(PERMANENT_TYPES & set(self.types))

    def is_castle(self) -> bool:
        """G城: 実行するとシールドゾーンに表向きで置かれる（第176弾）。バトルゾーンには出ない。"""
        return "g_castle" in self.types


@dataclass
class CardDef:
    id: str
    name: str
    types: list[str]
    civs: list[str]
    cost: int
    power: int = 0
    mana: int = 1                                         # マナゾーンでのマナの数値（112.2a）
    races: list[str] = field(default_factory=list)
    text: str = ""
    keywords: list[str] = field(default_factory=list)    # 持っているキーワード名（フィルタ用）
    abilities: list[dict] = field(default_factory=list)  # 展開済みの能力（キーワード由来も含む）
    spell: list[dict] = field(default_factory=list)      # 呪文の解決 ops
    sst_spell: list[dict] = field(default_factory=list)  # スーパー・S・トリガーで得る追加の解決 ops
    stp_spell: list[dict] = field(default_factory=list)  # S・トリガー・プラスで得る追加の解決 ops
    odrive_spell: list[dict] = field(default_factory=list)  # O・ドライブで得る追加の解決 ops（呪文側）
    o_drive: dict | None = None                         # O・ドライブ: {civ, count} または {civs: {文明: 枚数}, each?}
    mugen_climb: dict | None = None                     # ムゲンクライム: {tap, cost, civs}
    alt_cost: dict | None = None                        # 代替コスト
    vividraw: dict | None = None                        # ビビッドロー: {cost, civs}
    fushigi: dict | None = None                         # フシギバース: {cost, civs, min}
    recycle: dict | None = None                         # リサイクル: {cost, civs?}（第172弾）
    grave_cast: bool = False                            # 墓地から通常コストで唱えられる（第226弾）
    rinne: bool = False                                   # 輪廻∞（第267弾）: 呪文側をバトルゾーンに置いたまま通常コストで唱えられる
    mana_bakutan: int | None = None                     # マナ爆誕: 固定コスト（第191弾）
    link_to: list | None = None                         # G・リンク（名前指定・4方向。第197弾）: [{name, pos}]
    deck_evolution: dict | None = None                  # デッキ進化: {count?, rest_to?, blind?, shuffle_first?, stack_all?}（第173弾／第293弾）
    evolve_from: dict | None = None
    evolve_zone: str = "bz"
    evolve_any: bool = False
    evolve_count: int = 1
    evolve_max: int | None = None
    evolve_civs: tuple = ()
    evolve_zones: tuple = ()
    soul_shift: dict | None = None
    cost_reduce_per_evo: int = 0
    tap_reduce: int = 0
    s_back: str | dict | None = None
    free_if: dict | None = None
    galaxy_shield: dict | None = None
    bazurenda: dict | None = None                         # バズレンダ: {cost, civs}
    tap_entry: bool = False                               # タップして出してもよい（第259弾）
    neo: bool = False
    grave_evo: bool = False
    star: bool = False
    s_max: bool = False
    ace: bool = False                                     # ACEタマシード（第179弾）
    hyper: bool = False
    crystal_soul: int = 0                                 # 水晶ソウルN（面の宣言。0＝持たない）
    mana_boost: dict | None = None                        # マナブースト（第212弾。面の宣言）
    launcher: dict | None = None                          # ランチャーE（第233弾。面の宣言）
    evo_base_reduce: dict | None = None                   # 進化元依存の軽減（第234弾。面の宣言）
    evolve_total_cost_ge: int | None = None               # 超無限進化のコスト合計条件（第236弾。面の宣言）
    resolve_to: str = "graveyard"
    resolve_face_down: bool = False                       # 水晶チャージャー（第228弾。面の宣言）
    after_resolve: list[dict] = field(default_factory=list)
    faces: list[Face] = field(default_factory=list)      # ツインパクト: [0]=クリーチャー側, [1]=呪文側
    source: dict = field(default_factory=dict)           # 出典（公式ID・取得日・確認者など）

    def is_creature(self) -> bool:
        return "creature" in self.types

    def is_spell(self) -> bool:
        return "spell" in self.types

    def is_permanent(self) -> bool:
        """クリーチャーでなく、実行するとバトルゾーンに出るカード（タマシード・フィールド・クロスギア）。"""
        return not self.is_creature() and bool(PERMANENT_TYPES & set(self.types))

    def is_castle(self) -> bool:
        """G城: 実行するとシールドゾーンに表向きで置かれる（第176弾）。バトルゾーンには出ない。"""
        return "g_castle" in self.types

    def face(self, i: int | None) -> "CardDef | Face":
        return self if i is None or not self.faces else self.faces[i]


@dataclass
class Rules:
    zones: dict
    keywords: dict
    macros: dict
    cards: dict[str, CardDef]
    actions: dict = field(default_factory=dict)
    steps: list[str] = field(default_factory=list)

    def __post_init__(self):
        # 無視効果を持つカード（608.4）。特性計算の高速化のために先に集めておく
        self.ignore_defs = {d.id for d in self.cards.values()
                            for f in ([d] + d.faces) for ab in f.abilities
                            if ab["kind"] == "static" and "ignore" in ab.get("mod", {})}
        # バトルゾーン以外（墓地など）で機能する誘発型能力を持つカード。誘発チェックでそのゾーンも見る
        self.zone_trigger_defs = {d.id: {ab.get("zone") for f in ([d] + d.faces) for ab in f.abilities
                                         if ab["kind"] == "trigger" and ab.get("zone", "bz") != "bz"}
                                  for d in self.cards.values()}
        self.zone_trigger_defs = {k: v for k, v in self.zone_trigger_defs.items() if v}


def _subst(obj, args, used=None):
    if isinstance(obj, str) and obj.startswith("$"):
        key = obj[1:]
        if key not in args:
            raise DefError(f"macro argument missing: {key}")
        if used is not None:
            used.add(key)
        return args[key]
    if isinstance(obj, dict):
        return {k: _subst(v, args, used) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_subst(v, args, used) for v in obj]
    return obj


def expand_ops(ops: list[dict], macros: dict, where: str) -> list[dict]:
    out = []
    core = core_ops()
    if not isinstance(ops, list):
        raise DefError(f"{where}: ops must be a list, got {ops!r}")
    for op in ops:
        name = op.get("op") if isinstance(op, dict) else None
        if name in core:
            op = dict(op)
            for k, ty in core[name].items():
                if ty.rstrip("?") == "ops" and k in op:
                    op[k] = expand_ops(op[k], macros, where)
                if ty.rstrip("?") == "oplists" and k in op:
                    op[k] = [expand_ops(m, macros, where) for m in op[k]]
                if ty.rstrip("?") == "mod" and k in op and "gain" in op[k]:
                    op[k] = dict(op[k], gain=[_expand_ability(a, macros, where) for a in op[k]["gain"]])
            out.append(op)
        elif name in macros:
            args = {k: v for k, v in op.items() if k != "op"}
            used: set = set()
            body = _subst(copy.deepcopy(macros[name]), args, used)
            rest = {k: v for k, v in args.items() if k not in used}
            if rest:   # 1つの op に展開されるマクロなら、残りの引数（as など）はその op に渡す
                if len(body) != 1:
                    raise DefError(f"{where}: macro '{name}' got extra args {sorted(rest)}")
                body[0].update(rest)
            out.extend(expand_ops(body, macros, where))
        else:
            raise DefError(f"{where}: unknown op '{name}'")
    return out


def _is_var_ref(v) -> bool:
    """プレイヤー指定の変数参照 {var: 名前}（第192弾。choose_player が入れた相対指定を引く）。"""
    return isinstance(v, dict) and set(v) == {"var"} and isinstance(v.get("var"), str)


class Checker:
    """展開済みの op 列・能力・mod の型検査。"""

    def __init__(self, zones, keywords, actions, steps):
        self.zones, self.keywords, self.actions, self.steps = zones, keywords, actions, steps

    def ops(self, ops, where):
        spec = core_ops()
        for op in ops:
            name = op["op"]
            args = spec[name]
            for k in op:
                if k != "op" and k not in args:
                    raise DefError(f"{where}: op '{name}' has unknown arg '{k}' (allowed: {sorted(args)})")
            for k, ty in args.items():
                opt = ty.endswith("?")
                ty = ty.rstrip("?")
                if k not in op:
                    if not opt:
                        raise DefError(f"{where}: op '{name}' missing arg '{k}'")
                    continue
                self.value(ty, op[k], f"{where}: {name}.{k}")
            if name == "move" and "stack_on" in op:
                # シールドの上に重ねて置く（第148弾）: 行き先はシールドゾーンだけ、対象の束は1つだけ
                if op.get("to") != "shield":
                    raise DefError(f"{where}: move.stack_on needs to: shield")
                so = op["stack_on"]
                if isinstance(so, dict) and "count" in so and so["count"] != 1:
                    raise DefError(f"{where}: move.stack_on selector count must be 1")
            if name == "move" and "stack_evo" in op:
                # 重ね出し（put_evolution_stacking）: 真値のみ、行き先はバトルゾーンだけ、
                # シールド用の stack_on とは併記しない（あちらは束の上に置く別機構）
                if op["stack_evo"] is not True:
                    raise DefError(f"{where}: move.stack_evo must be true")
                if op.get("to") != "bz":
                    raise DefError(f"{where}: move.stack_evo needs to: bz")
                if "stack_on" in op:
                    raise DefError(f"{where}: move.stack_evo cannot combine with stack_on")
            if name == "move" and "evo_source" in op:
                # 重ね出しの進化元を固定する（第173弾）: 「このクリーチャーの上に置く」等、重ね先が
                # 指定されている時に使う。stack_evo と併記しなければ意味がない
                if op.get("stack_evo") is not True:
                    raise DefError(f"{where}: move.evo_source needs stack_evo")
            if name == "play_self" and "via" in op:
                # 出し方の印（第149弾）: 値は when の via と同じ VIAS のものだけ
                if op["via"] not in VIAS:
                    raise DefError(f"{where}: play_self.via unknown via '{op['via']}'")
            if name == "gacha":
                # ガチャの種類（第268弾）: 今はドギラゴン・ガチャのみ
                if op["kind"] not in ("dogiragon",):
                    raise DefError(f"{where}: gacha.kind unknown kind '{op['kind']}'")

    def value(self, ty, v, where):
        if ty == "filter":
            return self.filter(v, where)
        if ty == "zone" and v not in self.zones:
            raise DefError(f"{where}: unknown zone '{v}'")
        if ty == "reason" and v not in REASONS:
            raise DefError(f"{where}: unknown reason '{v}'")
        if ty == "player" and v not in ("you", "opp") and not _is_var_ref(v):
            raise DefError(f"{where}: player must be you/opp or {{var: name}}, got '{v}'")
        if ty == "players" and v not in ("you", "opp", "each") and not _is_var_ref(v):
            raise DefError(f"{where}: players must be you/opp/each or {{var: name}}, got '{v}'")
        if ty == "position" and v not in POSITIONS:
            raise DefError(f"{where}: unknown position '{v}'")
        if ty == "step" and v not in self.steps:
            raise DefError(f"{where}: unknown step '{v}'")
        if ty == "duration":
            self.duration(v, where)
        if ty == "ops":
            self.ops(v, where)
        if ty == "oplists":
            if not isinstance(v, list) or len(v) < 2:
                raise DefError(f"{where}: modes needs a list of 2 or more ops lists")
            for m in v:
                self.ops(m, where)
        if ty == "selector":
            self.selector(v, where)
        if ty == "mod":
            self.mod(v, where)
        if ty == "cond":
            self.cond(v, where)
        if ty == "ability":
            self.ability(v, where)
        if ty == "int" and not isinstance(v, int):
            raise DefError(f"{where}: expected int, got {v!r}")
        if ty == "bool" and not isinstance(v, bool):
            raise DefError(f"{where}: expected bool, got {v!r}")
        if ty == "str" and not isinstance(v, str):
            raise DefError(f"{where}: expected str, got {v!r}")
        if ty == "expr":
            self.expr(v, where)

    def duration(self, v, where):
        if v in DURATIONS_FIXED:
            return
        raise DefError(f"{where}: unknown duration '{v}'")

    def selector(self, sel, where):
        if not isinstance(sel, dict):
            raise DefError(f"{where}: selector must be a mapping, got {sel!r}")
        bad = set(sel) - SELECTOR_KEYS
        if bad:
            raise DefError(f"{where}: unknown selector keys {sorted(bad)}")
        if "owner" in sel and "owner_of" in sel:
            raise DefError(f"{where}: owner and owner_of are exclusive")
        if "under_of" not in sel and "bundle_of" not in sel and "exlife_of" not in sel and "castle_of" not in sel and "ref" not in sel \
                and "crossed_to" not in sel and "host_of" not in sel and "zone" not in sel:
            raise DefError(f"{where}: selector needs zone or ref")
        for z in ([sel["zone"]] if isinstance(sel.get("zone"), str) else sel.get("zone", [])):
            if z != "any" and z not in self.zones:   # any = すべてのゾーン、配列 = そのうちのどれか
                raise DefError(f"{where}: unknown zone '{z}'")
        if sel.get("owner", "you") not in ("you", "opp", "any") and not _is_var_ref(sel.get("owner")):
            raise DefError(f"{where}: bad owner '{sel['owner']}'")
        if "chooser" in sel and sel["chooser"] not in ("you", "opp", "opponent", "random") \
                and not _is_var_ref(sel["chooser"]):
            raise DefError(f"{where}: bad chooser '{sel['chooser']}'")
        for k in ("total_cost_le", "total_cost_ge", "total_power_le", "total_power_ge"):
            if k in sel:
                self.expr(sel[k], where)
        if "distinct_costs" in sel and sel["distinct_costs"] is not True:
            raise DefError(f"{where}: distinct_costs must be true")
        if "distinct_names" in sel and sel["distinct_names"] is not True:
            raise DefError(f"{where}: distinct_names must be true")
        if "distinct_from" in sel:
            self.selector(sel["distinct_from"], where)   # 参照集合は通常のセレクタとして再帰検証する
        if "exclude" in sel:
            ex = sel["exclude"]
            if not isinstance(ex, (dict, list)):
                raise DefError(f"{where}: exclude must be a selector or a list of selectors")
            for sub in (ex if isinstance(ex, list) else [ex]):
                self.selector(sub, where)   # 除外指定（単体または リスト形）も通常のセレクタとして再帰検証する
        if "bundle_of" in sel and isinstance(sel["bundle_of"], dict):
            self.selector(sel["bundle_of"], where)   # 束のトップを指すセレクタとして再帰検証する（文字列なら "self" / 変数名）
        if "extremal" in sel:
            if sel["extremal"] not in ("min_power", "max_power"):
                raise DefError(f"{where}: extremal must be min_power or max_power")
            if any(k in sel for k in ("ref", "under_of", "bundle_of", "exlife_of", "castle_of", "crossed_to", "host_of")):
                raise DefError(f"{where}: extremal needs a zone selector")
        if "distinct_costs" in sel or "distinct_from" in sel or "distinct_names" in sel:
            # 「コストが異なる」／「名前が異なる」制約は選択にだけ付く。count: all 単独は「選んだことにならない」ため不可
            # （count: all + up_to: true は any 相当の選択になるので許す）
            if "count" not in sel:
                raise DefError(f"{where}: distinct_costs/distinct_from/distinct_names needs count")
            if sel.get("count") == "all" and not sel.get("up_to"):
                raise DefError(f"{where}: distinct_costs/distinct_from/distinct_names with count: all needs up_to: true")
        self.filter(sel.get("filter", {}), where)

    def filter(self, f, where):
        bad = set(f) - FILTER_KEYS
        if bad:
            raise DefError(f"{where}: unknown filter keys {sorted(bad)}")
        if "any_of" in f:
            if not isinstance(f["any_of"], list) or not f["any_of"]:
                raise DefError(f"{where}: any_of must be a non-empty list of filters")
            for sub in f["any_of"]:
                self.filter(sub, where)
        for k in ("civs", "not_civs"):
            if k in f and not isinstance(f[k], dict) and set(f[k]) - CIVS:   # 辞書値は式として扱い、リテラル照合を素通りさせる（バンドB U3 の追加ガード）
                raise DefError(f"{where}: unknown civs {f[k]}")
        if "keyword" in f and f["keyword"] not in self.keywords:
            raise DefError(f"{where}: unknown keyword '{f['keyword']}'")
        if "crossed" in f and not isinstance(f["crossed"], bool):
            raise DefError(f"{where}: crossed must be a bool")
        if "ultimate_evolution" in f and not isinstance(f["ultimate_evolution"], bool):
            raise DefError(f"{where}: ultimate_evolution must be a bool")
        if "crossed_name" in f and not isinstance(f["crossed_name"], str):
            raise DefError(f"{where}: crossed_name must be a card name")
        if "evo_source_of" in f and not isinstance(f["evo_source_of"], str):
            raise DefError(f"{where}: evo_source_of must be 'self' or a variable name")
        for k in FILTER_EXPR_KEYS & set(f):
            if k in ("races", "civs", "not_civs") and isinstance(f[k], list):
                continue   # リテラル（種族・文明のリスト）は上の照合で検証済み
            if k == "name" and isinstance(f[k], str):
                continue   # リテラル（カード名の文字列）
            if isinstance(f[k], dict) and set(f[k]) == {"ref"} and isinstance(f[k]["ref"], str):
                continue   # {ref: 変数名} の参照指定形（既存の変換データの形。式ではないので検証対象外）
            self.expr(f[k], where)

    def expr(self, x, where):
        if isinstance(x, int):
            return
        if isinstance(x, dict) and len(x) == 1:
            k, v = next(iter(x.items()))
            if k == "count":
                return self.selector(v, where)
            if k == "civ_count":   # 対象カード群にある文明の種類数（多色はそれぞれ数える）
                return self.selector(v, where)
            if k == "distinct_cost_count":   # 対象カード群にあるコストの種類数（同じコストは1つに数える。第145弾）
                return self.selector(v, where)
            if k == "distinct_type_count":   # 対象カード群にあるカードタイプの種類数（第212弾）
                return self.selector(v, where)
            if k in ("total_cost", "total_power"):   # 対象カード群のコスト／パワーの合計（公開集合の保持。バンドC1 U39）
                return self.selector(v, where)
            if k == "max_power":   # 対象カード群の最大パワー（第219弾）
                return self.selector(v, where)
            if k == "entered":   # このターンに出したクリーチャーの数 {owner, other?}
                if not isinstance(v, dict) or set(v) - {"owner", "other"} or v.get("owner", "you") not in ("you", "opp"):
                    raise DefError(f"{where}: entered needs {{owner: you/opp, other?: bool}}")
                return
            if k == "drew":   # このターンに引いたカードの枚数 {owner}（第142弾）
                if not isinstance(v, dict) or set(v) - {"owner"} or v.get("owner", "you") not in ("you", "opp"):
                    raise DefError(f"{where}: drew needs {{owner: you/opp}}")
                return
            if k == "bundles":   # シールドの束の数 {owner, face_up?}（束の中身のカードは数えない。113.2。face_up は「表向きのカードを含む束か」）
                if not isinstance(v, dict) or set(v) - {"owner", "face_up"} or v.get("owner", "you") not in ("you", "opp") \
                        or ("face_up" in v and not isinstance(v["face_up"], bool)):
                    raise DefError(f"{where}: bundles needs {{owner: you/opp, face_up?: bool}}")
                return
            if k == "turn_count":   # このターンに〜した回数 {kind, owner?, other?, filter?, ref?, from?}（履歴カウンタ基盤。バンドC1 U19。from は第214弾）
                if not isinstance(v, dict) or set(v) - {"kind", "owner", "other", "filter", "ref", "from"} \
                        or v.get("kind") not in TURN_COUNT_KINDS \
                        or ("from" in v and not isinstance(v["from"], str)):
                    raise DefError(f"{where}: turn_count needs {{kind: <history kind>, owner?: you/opp/any, other?: bool, filter?: <filter>, ref?: str, from?: <zone>}}")
                kind = v["kind"]
                if kind in ("attack_by", "attack_on"):
                    if set(v) - {"kind", "ref"} or not isinstance(v.get("ref"), (str, dict)):
                        raise DefError(f"{where}: turn_count kind {kind} needs {{kind, ref}} (ref は \"self\" か変数名)")
                    if isinstance(v.get("ref"), dict) and set(v["ref"]) != {"ref"}:
                        raise DefError(f"{where}: turn_count ref must be \"self\", a var name, or {{ref: name}}")
                else:
                    if "ref" in v:
                        raise DefError(f"{where}: turn_count ref is only for attack_by / attack_on")
                    owner = v.get("owner", "you")
                    if owner not in ("you", "opp", "any") or (owner == "any" and kind not in TURN_COUNT_ANY_KINDS):
                        raise DefError(f"{where}: turn_count owner must be you/opp (any は destroyed / attack だけ)")
                    if kind in ("broke_by_self", "broke_by_self_attack") and set(v) != {"kind"}:
                        raise DefError(f"{where}: turn_count {kind} takes no owner/other/filter (self 固定)")
                    if "other" in v and (kind != "attack" or not isinstance(v["other"], bool)):
                        raise DefError(f"{where}: turn_count other is only for kind: attack, as a bool")
                    if "filter" in v:
                        if kind != "attack":
                            raise DefError(f"{where}: turn_count filter is only for kind: attack")
                        self.filter(v["filter"], where)
                return
            if k == "used_count":   # 「使った」履歴の特性つき数え {owner?, filter?}（バンドC1 U19）
                if not isinstance(v, dict) or set(v) - {"owner", "filter"} or v.get("owner", "you") not in ("you", "opp"):
                    raise DefError(f"{where}: used_count needs {{owner?: you/opp, filter?: <filter>}}")
                if "filter" in v:
                    self.filter(v["filter"], where)
                return
            if k == "prev_shield_added":   # 前のターンにシールドを加えた回数 {owner}（バンドB U18）
                if not isinstance(v, dict) or set(v) - {"owner"} or v.get("owner", "you") not in ("you", "opp"):
                    raise DefError(f"{where}: prev_shield_added needs {{owner: you/opp}}")
                return
            if k == "declared":   # 宣言した値 {declared: 名前}（バンドC2 U97。値は宣言 op の as の名前）
                if not isinstance(v, str):
                    raise DefError(f"{where}: declared needs a name")
                return
            if k in ("var", "cost_of", "power_of", "name_of", "races_of", "civs_of", "race"):   # name_of は従来 filter 経由で未検証だった分（T169）。他と同じく受理する。civs_of は第288弾
                return
            if k == "link_count":   # リンクしているカードの枚数（値は self 固定で無視される）
                return
            if k == "seals":   # そのプレイヤーの封印の総数 {owner: you/opp}
                if not isinstance(v, dict) or set(v) - {"owner"} or v.get("owner", "you") not in ("you", "opp"):
                    raise DefError(f"{where}: seals needs {{owner: you/opp}}")
                return
            if k == "seals_on":   # self に付いている封印の数（値は self 固定で無視される）
                return
            if k == "crossed_count":   # そのカードにクロスされているギアの数（第170弾）。値は "self" / 変数名 / {ref: 名前} / "crossed"（このギアをクロスしているクリーチャー）
                if isinstance(v, str):
                    return
                if isinstance(v, dict) and set(v) == {"ref"} and isinstance(v["ref"], str):
                    return
                raise DefError(f"{where}: crossed_count needs \"self\", a var name, or {{ref: name}}")
            if k in ("sum", "mul"):   # 加算・乗算（mul は「2 - X」を sum:[2, mul:[-1, X]] と書くため）
                for e in v:
                    self.expr(e, where)
                return
        raise DefError(f"{where}: bad expr {x!r}")

    def cond(self, c, where):
        if not isinstance(c, dict) or len(c) != 1:
            raise DefError(f"{where}: bad cond {c!r}")
        k, v = next(iter(c.items()))
        if k == "exists":
            return self.selector(v, where)
        if k == "cmp":
            if len(v) != 3 or v[1] not in ("<", "<=", "==", ">=", ">"):
                raise DefError(f"{where}: bad cmp {v!r}")
            self.expr(v[0], where)
            self.expr(v[2], where)
            return
        if k == "not":
            return self.cond(v, where)
        if k in ("all", "any"):
            for x in v:
                self.cond(x, where)
            return
        if k in ("marked", "self_marked"):
            if k == "marked" and isinstance(v, dict):   # スコープつき {name, scope?: turn/attack/game}（バンドB 基盤 mark-scope）
                if set(v) - {"name", "scope"} or not isinstance(v.get("name"), str) \
                        or v.get("scope", "turn") not in ("turn", "attack", "game"):
                    raise DefError(f"{where}: marked dict needs {{name: str, scope?: turn/attack/game}}")
                return
            if not isinstance(v, str):
                raise DefError(f"{where}: marked needs a name")
            return
        if k == "is_turn":
            if v not in ("you", "opp"):
                raise DefError(f"{where}: is_turn must be you/opp")
            return
        if k == "face_up":
            if not isinstance(v, bool):
                raise DefError(f"{where}: face_up must be bool")
            return
        if k == "hyper":
            if not isinstance(v, bool):
                raise DefError(f"{where}: hyper must be bool")
            return
        if k == "alt_paid":
            if not isinstance(v, bool):
                raise DefError(f"{where}: alt_paid must be bool")
            return
        if k == "vivid_paid":
            if not isinstance(v, bool):
                raise DefError(f"{where}: vivid_paid must be bool")
            return
        if k == "ddd_paid":
            if not isinstance(v, bool):
                raise DefError(f"{where}: ddd_paid must be bool")
            return
        if k == "subject_tapped":   # イベントの対象が移動直前にタップしていたか（第330弾）
            if not isinstance(v, bool):
                raise DefError(f"{where}: subject_tapped must be bool")
            return
        if k == "power_ge":
            if not isinstance(v, int) or isinstance(v, bool):
                raise DefError(f"{where}: power_ge must be an int")
            return
        if k == "extra_turn":   # このターンが追加ターンか（第263弾。龍マナ武装の「これが追加ターンでなければ」）
            if not isinstance(v, bool):
                raise DefError(f"{where}: extra_turn must be a bool")
            return
        raise DefError(f"{where}: unknown cond '{k}'")

    def count_spec(self, v, where):
        """mod の count: セレクタ（体数）か、civ_count / distinct_cost_count / sum / bundles / 履歴式を含む式（文明・コストの種類数、束の数、このターン〜した数など）。"""
        if isinstance(v, dict) and any(k in v for k in ("civ_count", "distinct_cost_count", "sum", "mul", "bundles",
                                                         "turn_count", "used_count", "prev_shield_added", "declared",
                                                         "crossed_count", "total_cost", "total_power", "max_power")):
            return self.expr(v, where)
        return self.selector(v, where)

    def mod(self, m, where):
        bad = set(m) - MOD_KEYS
        if bad:
            raise DefError(f"{where}: unknown mod keys {sorted(bad)}")
        if "double_power" in m and m["double_power"] is not True:
            raise DefError(f"{where}: double_power must be true")
        if "power" in m and isinstance(m["power"], dict):
            pm = m["power"]
            amt = pm.get("amount")
            amt_ok = isinstance(amt, int) or _is_var_ref(amt) \
                or (isinstance(amt, dict) and set(amt) == {"power_of"})
            if set(pm) - {"amount", "count"} or not amt_ok:
                raise DefError(f"{where}: power needs amount (int, {{var: name}}, or {{power_of: ref}}) and optional count")
            if isinstance(amt, dict) and "power_of" in amt:
                self.expr(amt, where)   # パワー移転（第333弾）: op_modify の生成時ベイクでリテラルに固定する。常在型に直接書くと chars が整数を前提とするため使えない
            if "count" in pm:
                self.count_spec(pm["count"], where)
        if "power_set" in m and not isinstance(m["power_set"], int):   # 第272弾: パワー置換は整数
            raise DefError(f"{where}: power_set must be an integer")
        if "add_races" in m:
            if not isinstance(m["add_races"], list) or not all(isinstance(x, (str, dict)) for x in m["add_races"]):
                raise DefError(f"{where}: add_races must be a list of race names or expressions")
        if "add_names" in m:
            if not isinstance(m["add_names"], list) or not m["add_names"] or not all(isinstance(x, str) for x in m["add_names"]):
                raise DefError(f"{where}: add_names must be a non-empty list of card names")
        if "breaks" in m:
            b = m["breaks"]
            if isinstance(b, dict):
                if "base" in b and not (isinstance(b["base"], int) and b["base"] >= 0):   # base（既定1）: ブレイク数の土台（第145弾）
                    raise DefError(f"{where}: breaks base must be an int >= 0")
                if "count" in b:   # {count: セレクタ, amount?: 係数}（クルー・ブレイカー等）: base + amount × 数
                    if set(b) - {"amount", "count", "base"} or ("amount" in b and not isinstance(b["amount"], int)):
                        raise DefError(f"{where}: breaks dict with count takes only amount/count/base")
                    self.count_spec(b["count"], where)
                else:   # 式形式（{civ_count: セレクタ}、第79弾）: base + 式の値
                    keys = set(b) - {"base"}
                    if keys not in ({"civ_count"}, {"distinct_cost_count"}):
                        raise DefError(f"{where}: breaks must be an int, {{count: <selector>}}, {{civ_count: <selector>}}, or {{distinct_cost_count: <selector>}}")
                    self.count_spec(b[next(iter(keys))], where)
            elif not isinstance(b, int):
                raise DefError(f"{where}: breaks must be an int or a dict (base + value)")
        if "breaks_add" in m:
            ba = m["breaks_add"]
            if isinstance(ba, dict):   # {amount, count}（第170弾）: 「〜1枚につき、さらに1枚ブレイクする」
                if _is_var_ref(ba):   # {var: 名前}（第324弾）: set_var で数えた値を生成時に焼く（op_modify の _bake_refs）
                    pass
                elif set(ba) - {"amount", "count"} or not isinstance(ba.get("amount"), int):
                    raise DefError(f"{where}: breaks_add dict needs amount (int) and optional count")
                elif "count" in ba:
                    self.count_spec(ba["count"], where)
            elif not isinstance(ba, int) or isinstance(ba, bool):
                raise DefError(f"{where}: breaks_add must be an int or {{amount, count}}")
        if "breaks_max" in m:   # ブレイク数の上限（第336弾）: 「攻撃1回につきシールドをN枚しかブレイクできない」
            if not isinstance(m["breaks_max"], int) or isinstance(m["breaks_max"], bool) or m["breaks_max"] < 0:
                raise DefError(f"{where}: breaks_max must be an int >= 0")
        if "evo_reduce" in m:   # 進化元からの軽減の付与（第234弾）: このカードから進化するクリーチャーのコストを減らす
            er = m["evo_reduce"]
            if not isinstance(er, dict) or set(er) - {"amount", "min"} or not isinstance(er.get("amount"), int) \
                    or ("min" in er and not isinstance(er["min"], int)):
                raise DefError(f"{where}: evo_reduce must be {{amount: int, min?: int}}")
        if "cross_reduce" in m:   # クロスのコスト軽減（第241弾）: ギア側・ホスト側どちらの常在型からもよい
            cr = m["cross_reduce"]
            if not isinstance(cr, dict) or set(cr) - {"amount", "min", "host", "gear", "may"} or not isinstance(cr.get("amount"), int) \
                    or ("min" in cr and not isinstance(cr["min"], int)) or ("may" in cr and not isinstance(cr["may"], bool)):
                raise DefError(f"{where}: cross_reduce must be {{amount: int, min?: int, host?: filter, gear?: filter, may?: bool}}")
            for fk in ("host", "gear"):
                if fk in cr:
                    self.filter(cr[fk], where + ".cross_reduce." + fk)
        if "cost_may" in m:
            cm = m["cost_may"]
            if not isinstance(cm, dict) or set(cm) - {"amount", "once", "min", "must"} or not isinstance(cm.get("amount"), int) \
                    or ("once" in cm and not isinstance(cm["once"], bool)) or ("min" in cm and not isinstance(cm["min"], int)) \
                    or ("must" in cm and not isinstance(cm["must"], bool)):
                raise DefError(f"{where}: cost_may must be {{amount: int, once?: bool, min?: int, must?: bool}}")
        if "sac_reduce" in m:   # ササゲール系の生贄軽減（第201弾は int 形＝ディスペクター専用。dict 形は2系統: {amount, cost_min}＝自己受益・下限つき（dmex01-042 の既存形）と {amount, for}＝対象フィルタつき（第292弾））
            sr = m["sac_reduce"]
            if isinstance(sr, dict):
                if not isinstance(sr.get("amount"), int) or isinstance(sr.get("amount"), bool):
                    raise DefError(f"{where}: sac_reduce dict needs amount: int")
                if set(sr) == {"amount", "for"}:
                    self.filter(sr["for"], where + ".sac_reduce.for")
                elif not (set(sr) == {"amount", "cost_min"} and isinstance(sr.get("cost_min"), int)):
                    raise DefError(f"{where}: sac_reduce dict must be {{amount: int, for: filter}} or {{amount: int, cost_min: int}}")
            elif not isinstance(sr, int) or isinstance(sr, bool):
                raise DefError(f"{where}: sac_reduce must be an int or a dict {{amount, for}} / {{amount, cost_min}}")
        if "no_leave" in m:
            nl = m["no_leave"]
            if nl is not True and not (isinstance(nl, dict) and set(nl) <= {"except_destroy", "by_opp", "except_battle", "by_opp_spell"}
                                       and all(isinstance(v, bool) for v in nl.values())):
                raise DefError(f"{where}: no_leave must be true or {{except_destroy?: bool, by_opp?: bool, except_battle?: bool, by_opp_spell?: bool}}")
        if "must_be_attacked" in m:
            mba = m["must_be_attacked"]
            if mba is not True and not (isinstance(mba, dict) and set(mba) == {"first_only"} and mba["first_only"] is True):
                raise DefError(f"{where}: must_be_attacked must be true or {{first_only: true}}")
        if "player_rush" in m:   # 出たターンにプレイヤーだけは攻撃できる（第261弾）
            if m["player_rush"] is not True:
                raise DefError(f"{where}: player_rush must be true")
        if "trigger_double" in m:   # 誘発の2度トリガー（第264弾）: この常在型がある間、条件に合う誘発型能力は2度トリガーする
            td = m["trigger_double"]
            if not isinstance(td, dict) or set(td) - {"when", "source", "source_subject", "may", "once_per_turn",
                                                      "first_per_turn", "cost"} or "when" not in td:
                raise DefError(f"{where}: trigger_double needs {{when: <when>, source?: <subject>, source_subject?: bool, may?: bool, once_per_turn?: bool, first_per_turn?: bool, cost?: <ops>}}")
            self.when(td["when"], where + ".trigger_double.when")
            if "source" in td:   # 能力の発生源カードへの条件（"self" か、subject と同じ形。owner / filter / other だけ認める）
                src = td["source"]
                if src == "self":
                    pass
                elif not isinstance(src, dict) or set(src) - {"owner", "filter", "other"} \
                        or src.get("owner", "any") not in ("you", "opp", "any") \
                        or ("other" in src and not isinstance(src["other"], bool)):
                    raise DefError(f"{where}: trigger_double.source must be 'self' or {{owner?: you/opp/any, filter?: <filter>, other?: bool}}")
                elif "filter" in src:
                    self.filter(src["filter"], where + ".trigger_double.source.filter")
            for bk in ("source_subject", "may", "once_per_turn", "first_per_turn"):
                if bk in td and not isinstance(td[bk], bool):
                    raise DefError(f"{where}: trigger_double.{bk} must be a bool")
            if "cost" in td:
                if not td.get("may"):
                    raise DefError(f"{where}: trigger_double.cost needs may (コストは任意の2度トリガーの決定時に支払う)")
                self.ops(td["cost"], where + ".trigger_double.cost")
        if "must_be_chosen" in m:   # 「相手が選ぶ時、可能ならこのクリーチャーを選ぶ」（第199弾）: 選択先の強制
            if m["must_be_chosen"] is not True:
                raise DefError(f"{where}: must_be_chosen must be true")
        if "must_attack_creature" in m:   # 「可能ならクリーチャーを攻撃する」（第171弾）: 攻撃できるクリーチャーがいればプレイヤーを攻撃できない
            mac = m["must_attack_creature"]
            if mac is not True and not (isinstance(mac, dict) and set(mac) == {"first_only"} and mac["first_only"] is True):
                raise DefError(f"{where}: must_attack_creature must be true or {{first_only: true}}")
        if "battle_indestructible" in m:
            bi = m["battle_indestructible"]
            if bi is not True and not (isinstance(bi, dict) and set(bi) == {"opponent_filter"}):
                raise DefError(f"{where}: battle_indestructible must be true or {{opponent_filter: <filter>}}")
            if isinstance(bi, dict):
                self.filter(bi["opponent_filter"], where)
        if "win_all_battles" in m and m["win_all_battles"] is not True:
            raise DefError(f"{where}: win_all_battles must be true")
        if "indestructible" in m and m["indestructible"] is not True:
            raise DefError(f"{where}: indestructible must be true")
        if "add_civs" in m:
            ac = m["add_civs"]
            if not isinstance(ac, list) or not ac or not all(c in CIVS for c in ac):
                raise DefError(f"{where}: add_civs must be a non-empty list of civilizations")
        if "ignore_ids" in m:
            if not isinstance(m["ignore_ids"], list) or not all(isinstance(x, str) for x in m["ignore_ids"]):
                raise DefError(f"{where}: ignore_ids must be a list of ability id strings")
        if "opt_reduce" in m:
            o = m["opt_reduce"]
            if not isinstance(o, dict) or not isinstance(o.get("amount"), int):
                raise DefError(f"{where}: opt_reduce needs amount (int)")
            if set(o) - {"amount", "then", "floor", "per", "do"}:
                raise DefError(f"{where}: opt_reduce has unknown keys {sorted(set(o) - {'amount', 'then', 'floor', 'per', 'do'})}")
            if "then" in o and o["then"] not in ("destroy", "deck_bottom_draw", "entry_destroy"):
                raise DefError(f"{where}: opt_reduce.then must be destroy / deck_bottom_draw / entry_destroy")
            if "do" in o:
                do = o["do"]
                if not isinstance(do, dict) or set(do) - {"select", "selects", "move_to", "shuffle", "min", "max", "tap", "strigger_off"}:
                    raise DefError(f"{where}: opt_reduce.do needs select/selects and optional move_to/shuffle/min/max/tap/strigger_off")
                if ("select" in do) == ("selects" in do):
                    raise DefError(f"{where}: opt_reduce.do needs exactly one of select / selects")
                if "select" in do:
                    self.selector(do["select"], where)
                else:
                    if not isinstance(do["selects"], list) or not do["selects"]:
                        raise DefError(f"{where}: opt_reduce.do.selects must be a non-empty list")
                    for e in do["selects"]:
                        if not isinstance(e, dict) or set(e) - {"select", "min", "max"} or "select" not in e:
                            raise DefError(f"{where}: opt_reduce.do.selects entry needs select and optional min/max")
                        self.selector(e["select"], where)
                if "move_to" in do and do["move_to"] not in self.zones:
                    raise DefError(f"{where}: opt_reduce.do.move_to must be a zone")
                if "strigger_off" in do and not isinstance(do["strigger_off"], bool):
                    raise DefError(f"{where}: opt_reduce.do.strigger_off must be a bool")
        for kw in m.get("grant", []):
            if kw not in self.keywords:
                raise DefError(f"{where}: unknown keyword '{kw}'")
        if "add_of" in m and m["add_of"] != "self":
            raise DefError(f"{where}: add_of は self だけ")
        for k in ("allow", "deny"):
            for e in m.get(k, []):
                act = e if isinstance(e, str) else e.get("action")
                if act not in self.actions:
                    raise DefError(f"{where}: unknown action '{act}'")
                if isinstance(e, dict):
                    self.filter(e.get("other", {}), where)
                    if "once" in e and not isinstance(e["once"], bool):
                        raise DefError(f"{where}: allow/deny entry 'once' must be a boolean")
                    if "max_per_turn" in e and not (isinstance(e["max_per_turn"], int) and not isinstance(e["max_per_turn"], bool)
                                                     and e["max_per_turn"] >= 1):
                        raise DefError(f"{where}: allow/deny entry 'max_per_turn' must be an int >= 1")
                    if "count" in e and e["count"] not in TURN_COUNT_KINDS:
                        raise DefError(f"{where}: allow/deny entry 'count' must be a history kind")
                    if "only" in e and not (isinstance(e["only"], dict) and set(e["only"]) == {"var"}
                                            and isinstance(e["only"]["var"], str)):
                        raise DefError(f"{where}: allow/deny entry 'only' must be {{var: <name>}} (第275弾: 特定のカードだけへの許可・禁止。継続的効果の生成時にベイクされる)")
                    if set(e) - {"action", "other", "once", "max_per_turn", "count", "only"}:
                        raise DefError(f"{where}: allow/deny entry has unknown keys {sorted(set(e) - {'action', 'other', 'once', 'max_per_turn', 'count', 'only'})}")
        if "cost" in m:   # 支払うコストの増減: 整数、または {amount: N, count: <selector>}（1体につきN。amount が負なら軽減）
            cm = m["cost"]
            if isinstance(cm, dict):
                if set(cm) - {"amount", "count"} or not isinstance(cm.get("amount"), int):
                    raise DefError(f"{where}: cost needs amount (int) and optional count (selector)")
                if "count" in cm:
                    self.count_spec(cm["count"], where)
            elif not isinstance(cm, int):
                raise DefError(f"{where}: cost must be int or {{amount, count}}")
        if "cost_min" in m and not isinstance(m["cost_min"], int):
            raise DefError(f"{where}: cost_min must be int")
        if "crystal_soul" in m and not (isinstance(m["crystal_soul"], int) and not isinstance(m["crystal_soul"], bool) and m["crystal_soul"] >= 1):
            raise DefError(f"{where}: crystal_soul must be an int >= 1")
        if "mana_number" in m and not (isinstance(m["mana_number"], int) and not isinstance(m["mana_number"], bool) and m["mana_number"] >= 0):
            raise DefError(f"{where}: mana_number must be an int >= 0")
        if "power_when" in m:   # 攻撃中／ブロック中のパワー修整: {amount: N, count: <selector>, when: attacking|blocking|not_attacking}。バトルをしていない間（プレイヤーを攻撃中など）も含む。not_attacking は「攻撃していない時」（第280弾）
            pw = m["power_when"]
            if not isinstance(pw, dict) or set(pw) - {"amount", "count", "when"} or not isinstance(pw.get("amount"), int) \
                    or pw.get("when") not in ("attacking", "blocking", "not_attacking"):
                raise DefError(f"{where}: power_when needs amount (int), when: attacking|blocking|not_attacking and optional count (selector)")
            if "count" in pw:
                self.count_spec(pw["count"], where)
        if "battle_power" in m:   # バトル中だけのパワー修整: {amount: N, count: <selector>, only: attacking}（ハンティング。バトル中だけ。「攻撃中」「ブロック中」は power_when）
            bp = m["battle_power"]
            if not isinstance(bp, dict) or set(bp) - {"amount", "count", "only", "opponent_filter"} or not isinstance(bp.get("amount"), int):
                raise DefError(f"{where}: battle_power needs amount (int) and optional count (selector) / only: attacking / opponent_filter (filter)")
            if bp.get("only", "attacking") != "attacking":
                raise DefError(f"{where}: battle_power only must be attacking")
            if "count" in bp:
                self.count_spec(bp["count"], where)
            if "opponent_filter" in bp:
                self.filter(bp["opponent_filter"], where)
        for k in m.get("require", []):
            if k not in REQUIRES:
                raise DefError(f"{where}: bad require '{k}' (allowed: {sorted(REQUIRES)})")
        for k in m.get("ignore", []):
            if k not in ("trigger", "static", "replace", "all"):
                raise DefError(f"{where}: bad ignore '{k}'")
        for ab in m.get("gain", []):   # 能力を得る（「〜時、かわりに〜」などを継続的効果で与える）
            self.ability(ab, where)

    def when(self, w, where):
        ev = w.get("event")
        if ev not in EVENTS:
            raise DefError(f"{where}: unknown event '{ev}'")
        for k in ("from", "to"):
            if k in w:
                vals = w[k] if isinstance(w[k], list) else [w[k]]
                for v in vals:
                    if v not in self.zones:
                        raise DefError(f"{where}: unknown zone '{v}'")
        if "reason" in w:
            vals = w["reason"] if isinstance(w["reason"], list) else [w["reason"]]
            allowed = REASONS | LOSE_REASONS if ev == "lose" else REASONS
            for v in vals:
                if v not in allowed:
                    raise DefError(f"{where}: unknown reason '{v}'")
        if "not_reason" in w:   # 理由の否定（第256弾）: 「召喚以外の方法で出た時」など
            vals = w["not_reason"] if isinstance(w["not_reason"], list) else [w["not_reason"]]
            allowed = REASONS | LOSE_REASONS if ev == "lose" else REASONS
            for v in vals:
                if v not in allowed:
                    raise DefError(f"{where}: unknown not_reason '{v}'")
        if "position" in w and w["position"] not in POSITIONS:   # 置かれた位置（山札の上か下か。第290弾: 「山札の一番下に置かれた時」）
            raise DefError(f"{where}: unknown position '{w['position']}'")
        tg = w.get("target")
        if tg is not None and tg not in ("player", "creature", "self") and not isinstance(tg, dict):
            raise DefError(f"{where}: bad target '{tg}'")
        if w.get("attacker") is not None and w["attacker"] not in ("self", "crossed") and not isinstance(w["attacker"], dict):
            raise DefError(f"{where}: bad attacker '{w['attacker']}'")
        if w.get("opponent") is not None and w["opponent"] not in ("self", "crossed") and not isinstance(w["opponent"], dict):
            raise DefError(f"{where}: bad opponent '{w['opponent']}'")
        if "via" in w and w["via"] not in VIAS:
            raise DefError(f"{where}: unknown via '{w['via']}'")
        if "by" in w and w["by"] not in ("you", "opp"):
            raise DefError(f"{where}: bad by '{w['by']}'")
        if "opp_hand" in w and w["opp_hand"] not in ("rock", "scissors", "paper"):   # ジャンケンで相手が出した手（第271弾）
            raise DefError(f"{where}: opp_hand must be rock/scissors/paper")
        if "cause" in w:   # そのイベントを起こした効果の帰属 {by?: you/opp, kind?: spell/ability かそのリスト（第290弾: 「呪文の効果またはクリーチャーの能力によって」）, defn?: 発生源の defn, name_has?: 発生源の名前の一部（第246弾）}（効果帰属レコード基盤B1。バンドC2 U108）
            cw = w["cause"]
            kinds = cw.get("kind", "spell") if isinstance(cw, dict) else None
            kind_ok = kinds in ("spell", "ability") or (isinstance(kinds, list) and bool(kinds)
                                                        and all(k in ("spell", "ability") for k in kinds))
            if not isinstance(cw, dict) or not cw or set(cw) - {"by", "kind", "defn", "name_has"} \
                    or cw.get("by", "you") not in ("you", "opp") or not kind_ok \
                    or ("defn" in cw and not (isinstance(cw["defn"], str)
                        or (isinstance(cw["defn"], list) and cw["defn"] and all(isinstance(x, str) for x in cw["defn"])))) \
                    or ("name_has" in cw and not isinstance(cw["name_has"], str)):
                raise DefError(f"{where}: cause needs {{by?: you/opp, kind?: spell/ability, defn?: str|[str], name_has?: str}}")
        if "blocked" in w and not isinstance(w["blocked"], bool):
            raise DefError(f"{where}: blocked must be bool")
        if "battle" in w and not isinstance(w["battle"], bool):   # バトルで負けて破壊された移動か（第332弾）
            raise DefError(f"{where}: battle must be bool")
        if "emblem" in w and not isinstance(w["emblem"], bool):   # 裁きの紋章だったか（第169弾）
            raise DefError(f"{where}: emblem must be bool")
        if "turn_draw" in w and not isinstance(w["turn_draw"], bool):   # ターンのはじめのドローそのものか（第219弾）
            raise DefError(f"{where}: turn_draw must be bool")
        if "ord" in w:   # その出来事のこのターンでの通し番号 {kind, 比較1つ}（履歴カウンタ基盤。バンドC1 U19）
            o = w["ord"]
            cmps = [k for k in ("eq", "ge", "gt", "le", "lt") if k in o]
            if not isinstance(o, dict) or set(o) - {"kind", "eq", "ge", "gt", "le", "lt"} \
                    or o.get("kind") not in ORD_KINDS or len(cmps) != 1 \
                    or not isinstance(o[cmps[0]], int) or isinstance(o[cmps[0]], bool) or o[cmps[0]] < 1:
                raise DefError(f"{where}: ord needs {{kind: <ord kind>, <one of eq/ge/gt/le/lt>: <positive int>}}")
        if w.get("sealed_from") is not None and w["sealed_from"] not in ("self",) and not isinstance(w["sealed_from"], dict):
            raise DefError(f"{where}: bad sealed_from '{w['sealed_from']}'")
        if "from_under" in w:   # 移動直前に他のカードの下にあったか: true / false（下になかった）/ self / {owner?, filter?, other?}（from_under 機構。第156弾の event.under と対）
            fu = w["from_under"]
            if isinstance(fu, dict):
                bad = set(fu) - {"owner", "filter", "other"}
                if bad:
                    raise DefError(f"{where}: bad from_under keys {sorted(bad)}")
                if fu.get("owner", "any") not in ("you", "opp", "any"):
                    raise DefError(f"{where}: bad from_under owner '{fu.get('owner')}'")
                if "filter" in fu:
                    self.filter(fu["filter"], where)
            elif fu is not True and fu is not False and fu != "self":
                raise DefError(f"{where}: bad from_under '{fu}'")

    def ability(self, ab, where):
        kind = ab.get("kind")
        if kind not in ABILITY_KINDS:
            raise DefError(f"{where}: unknown ability kind '{kind}'")
        bad = set(ab) - ABILITY_KEYS
        if bad:
            raise DefError(f"{where}: unknown ability keys {sorted(bad)}")
        if "id" in ab and not isinstance(ab["id"], str):
            raise DefError(f"{where}: ability id must be a string")
        if kind in ("trigger", "replace", "declare"):
            self.when(ab.get("when", {}), where)
        if "continue" in ab:   # ブレイクの割り込み型（第146弾）: 置換の instead の後もブレイクが続く。break の置換だけに書ける
            if kind != "replace" or ab.get("when", {}).get("event") != "break" or not isinstance(ab["continue"], bool):
                raise DefError(f"{where}: continue is only for replace of break, as a bool")
        if "dswitch" in ab:   # Dスイッチ（第151弾）: trigger に true を付け、効果の先頭に may＋{op: dswitch} を置く型だけ
            if kind != "trigger" or ab["dswitch"] is not True:
                raise DefError(f"{where}: dswitch is only for trigger, as true")
        if "accel" in ab:   # アクセル（第175弾）: クロスギアがクロスされている間だけ得る能力。true だけ
            if ab["accel"] is not True:
                raise DefError(f"{where}: accel is only for abilities, as true")
        if "no_lose" in ab:   # 第188弾: 敗北の防止（常在型）。static だけ。true か {deck_out_only?: bool}
            if kind != "static":
                raise DefError(f"{where}: no_lose is only for static")
            nl = ab["no_lose"]
            if nl is not True and not (isinstance(nl, dict) and set(nl) <= {"deck_out_only"}
                                       and isinstance(nl.get("deck_out_only", False), bool)):
                raise DefError(f"{where}: no_lose must be true or {{deck_out_only?: bool}}")
        if "fort_e" in ab:   # フォートE（第168弾）: 召喚時にタップしたマナの種族で得る能力
            fe = ab["fort_e"]
            if not isinstance(fe, dict) or not isinstance(fe.get("races"), list) or not fe["races"] \
                    or not all(isinstance(r, str) for r in fe["races"]) \
                    or set(fe) - {"races", "as"} or ("as" in fe and not isinstance(fe["as"], str)):
                raise DefError(f"{where}: fort_e needs {{races: [種族...], as?: 変数名}}")
        if "mana_boost" in ab:   # マナブースト（第212弾）: 自分の支払い時にマナの数字を任意で置き換える常在型
            if kind != "static":
                raise DefError(f"{where}: mana_boost is only for static")
            mb = ab["mana_boost"]
            if not isinstance(mb, dict) or set(mb) - {"value", "values", "filter", "scope", "if"} \
                    or ("value" in mb) == ("values" in mb) \
                    or ("value" in mb and (not isinstance(mb["value"], int) or isinstance(mb["value"], bool) or mb["value"] < 2)) \
                    or ("values" in mb and (not isinstance(mb["values"], list) or not mb["values"]
                        or any(not isinstance(v, int) or isinstance(v, bool) or v < 2 for v in mb["values"]))) \
                    or ("scope" in mb and mb["scope"] not in ("spell",)):
                raise DefError(f"{where}: mana_boost needs {{value: int >= 2}} or {{values: [int >= 2, ...]}}, plus optional filter / scope / if")
            if "filter" in mb:
                self.filter(mb["filter"], where)
            if "if" in mb:
                self.cond(mb["if"], where)
        if "suppress_triggers" in ab:   # 誘発抑制（第213弾）: 相手のクリーチャーが出た時／攻撃した時に誘発する相手の能力を誘発させない常在型
            if kind != "static":
                raise DefError(f"{where}: suppress_triggers is only for static")
            st = ab["suppress_triggers"]
            if not isinstance(st, dict) or set(st) - {"whose", "events", "if"} \
                    or st.get("whose", "opp") != "opp" \
                    or not isinstance(st.get("events"), list) or not st["events"] \
                    or any(v not in ("enter", "attack") for v in st["events"]):
                raise DefError(f"{where}: suppress_triggers needs {{whose: opp, events: [enter / attack, ...], if?}}")
            if "if" in st:
                self.cond(st["if"], where)
        if "protect_hand" in ab:   # 手札破棄の保護（第253弾）: 相手の呪文またはクリーチャーの能力によって、自分の手札は捨てられない常在型
            if kind != "static" or ab["protect_hand"] is not True:
                raise DefError(f"{where}: protect_hand is only for static and must be true")
        if "mana_all_civs" in ab:   # マナの全文明扱い（第260弾）: 支払い時にマナカードをすべての文明を持つかのようにタップできる常在型
            if kind != "static":
                raise DefError(f"{where}: mana_all_civs is only for static")
            mac = ab["mana_all_civs"]
            if not isinstance(mac, dict) or set(mac) - {"for"}:
                raise DefError(f"{where}: mana_all_civs needs {{for?: filter}}")
            if "for" in mac:
                self.filter(mac["for"], where)
        if "group" in ab:   # 宣言のグループ（第262弾）: 同じ group の宣言は、1回の攻撃につきプレイヤーごとに1回まで（ニンジャ・チェンジの「この攻撃中に自分がニンジャ能力を使っていなければ」）
            if kind != "declare" or not isinstance(ab["group"], str) or not ab["group"]:
                raise DefError(f"{where}: group is only for declare and must be a non-empty str")
        if "cast_limit" in ab:   # 呪文を唱える回数の制限（第261弾）: この常在型がある間、相手は各ターン count 回までしか呪文を唱えられない
            if kind != "static":
                raise DefError(f"{where}: cast_limit is only for static")
            cl = ab["cast_limit"]
            if not isinstance(cl, dict) or set(cl) - {"count"} \
                    or not isinstance(cl.get("count"), int) or isinstance(cl.get("count"), bool) \
                    or cl["count"] < 0:
                raise DefError(f"{where}: cast_limit needs {{count: int}}")
        if "untap_limit" in ab:   # アンタップ制限（第227弾）: 相手のターン開始時に、そのゾーンのアンタップを count 枚までに制限する常在型
            if kind != "static":
                raise DefError(f"{where}: untap_limit is only for static")
            ul = ab["untap_limit"]
            if not isinstance(ul, dict) or set(ul) - {"zone", "count"} \
                    or ul.get("zone") not in ("bz", "mana") \
                    or not isinstance(ul.get("count"), int) or isinstance(ul.get("count"), bool) \
                    or ul["count"] < 0:
                raise DefError(f"{where}: untap_limit needs {{zone: bz / mana, count: int >= 0}}")
        if kind == "state":
            if "if" not in ab or not all(o.get("op") in ("win", "lose") for o in ab.get("effect", [])) or not ab.get("effect"):
                raise DefError(f"{where}: state は if と effect（win / lose だけ）が要る")
        if kind == "static" and "mod" in ab:
            self.mod(ab["mod"], where)
        if kind in ("static", "trigger") and ab.get("zone", "bz") not in self.zones:
            raise DefError(f"{where}: unknown zone '{ab['zone']}'")
        aff = ab.get("affects")
        if isinstance(aff, dict):
            if aff.get("zone", "bz") not in self.zones:
                raise DefError(f"{where}: unknown zone '{aff['zone']}'")
            self.filter(aff.get("filter", {}), where)
        if "redirect" in ab:   # 攻撃先変更（第171弾）: アンタップをコストに攻撃先を変える起動型能力だけ
            if kind != "activate":
                raise DefError(f"{where}: redirect is only for activate")
            rd = ab["redirect"]
            if rd is not True and not (isinstance(rd, dict) and set(rd) <= {"include_cost"}
                                       and isinstance(rd.get("include_cost", True), bool)):
                raise DefError(f"{where}: redirect must be true or {{include_cost?: bool}}")
        if kind == "activate":   # 起動型能力（602）。cost: {tap: self} か {tap: {filter}}（攻撃する代わりにタップして使う。602.3a）
            c = ab.get("cost")   # tap_mana: 自分のマナゾーンのタップされていないカードをその枚数追加でタップする（DM24系の複合コスト）
            # under: このクリーチャーの下にあるカードをその枚数墓地に置く（メテオバーン「攻撃できる時」形。第53弾。tap と併用可、tap_mana とは併用不可）
            # untap: タップしているクリーチャーをアンタップする（攻撃先変更形。第171弾。redirect と組でだけ使う）
            if not isinstance(c, dict) or not set(c) <= {"tap", "tap_mana", "under", "untap"} \
                    or not ("tap" in c or "under" in c or "untap" in c):
                raise DefError(f"{where}: activate needs cost: {{tap: self | <filter>, tap_mana?: int, under?: int}} or {{untap: self | <filter>}}")
            if "tap_mana" in c and not (isinstance(c["tap_mana"], int) and c["tap_mana"] >= 1):
                raise DefError(f"{where}: cost.tap_mana must be a positive int")
            if "under" in c and not (isinstance(c["under"], int) and c["under"] >= 1):
                raise DefError(f"{where}: cost.under must be a positive int")
            if "under" in c and "tap_mana" in c:
                raise DefError(f"{where}: cost.under cannot combine with tap_mana")
            if "tap" in c and c["tap"] != "self":
                if isinstance(c["tap"], dict) and set(c["tap"]) == {"ref"} and c["tap"]["ref"] == "crossed":
                    pass   # {ref: crossed}（第170弾）: このギアをクロスしているクリーチャーをタップする
                elif not isinstance(c["tap"], dict):
                    raise DefError(f"{where}: cost.tap must be 'self' or a filter")
                else:
                    self.filter(c["tap"], where)
            if "untap" in c:
                if "tap" in c or "under" in c or "tap_mana" in c:
                    raise DefError(f"{where}: cost.untap cannot combine with tap/under/tap_mana")
                if "redirect" not in ab:
                    raise DefError(f"{where}: cost.untap needs redirect")
                if c["untap"] != "self":
                    if not isinstance(c["untap"], dict):
                        raise DefError(f"{where}: cost.untap must be 'self' or a filter")
                    self.filter(c["untap"], where)
            if "redirect" in ab:
                if "effect" in ab:
                    raise DefError(f"{where}: redirect cannot combine with effect")
            elif "effect" not in ab:
                raise DefError(f"{where}: activate needs effect")
        elif "cost" in ab:
            raise DefError(f"{where}: cost is only for activate")
        if kind == "silent" and "effect" not in ab:   # サイレントスキル（501.1a）: ターンのはじめにタップされていたら、アンタップしないかわりに使ってもよい
            raise DefError(f"{where}: silent needs effect")
        if kind == "partner" and "effect" not in ab:   # [P]能力: キズナ等で使われる効果だけを持つ
            raise DefError(f"{where}: partner needs effect")
        if "if" in ab:
            self.cond(ab["if"], where)
        for k in ("effect", "instead"):
            if k in ab:
                self.ops(ab[k], where)


# G城の型ルール（第176弾）: 表向きでシールドゾーンを離れる時、かわりに墓地に置く。
# シールド・ゴー（data/rules/keywords.yaml）の2つ目の置換と同型。types に g_castle を
# 含む面すべてに _load_face で自動で付くため、データ側に書かない
_G_CASTLE_LEAVE = [
    {"kind": "replace", "zone": "shield",
     "when": {"event": "move", "from": "shield", "subject": "self"},
     "if": {"face_up": True},
     "instead": [{"op": "move", "select": {"ref": "self"}, "to": "graveyard", "reason": "put"}]},
]


def _expand_ability(ab, macros, where):
    ab = dict(ab)
    for k in ("effect", "instead"):
        if k in ab:
            ab[k] = expand_ops(ab[k], macros, where)
    return ab


def _load_face(raw, keywords, macros, chk: Checker, where) -> dict:
    names, abilities = [], []
    props = {"resolve_to": "graveyard", "resolve_face_down": False, "after_resolve": []}
    for kw in raw.get("keywords", []):
        if kw not in keywords:
            raise DefError(f"{where}: unknown keyword '{kw}'")
        names.append(kw)
        abilities += [dict(_expand_ability(a, macros, where), keyword=kw) for a in keywords[kw]["abilities"]]
        for k, v in keywords[kw].get("card", {}).items():
            props[k] = expand_ops(v, macros, where) if k == "after_resolve" else v
    props["resolve_to"] = raw.get("resolve_to", props["resolve_to"])   # 唱えた後の置き場所を直接指定（シールドに加わる呪文など）
    props["resolve_face_down"] = bool(raw.get("resolve_face_down", props["resolve_face_down"]))   # 裏向きで置く（水晶チャージャー）
    chk.ops(props["after_resolve"], where)
    if props["resolve_to"] not in chk.zones:
        raise DefError(f"{where}: unknown zone '{props['resolve_to']}'")
    if "s_back" in raw:   # S・バックの対象指定は面に直接書ける（キーワードの文明名形と併用可。第52弾）
        props["s_back"] = raw["s_back"]
    sb = props.get("s_back")
    if sb is not None:
        if isinstance(sb, str):
            if sb not in CIVS:
                raise DefError(f"{where}: s_back civ '{sb}' is unknown")
        elif isinstance(sb, dict):
            chk.filter(sb, where)
        else:
            raise DefError(f"{where}: s_back must be a civ name or a filter")
    if "g_castle" in raw.get("types", []):
        # G城の型ルール（第176弾）: 表向きでシールドゾーンを離れる時、かわりに墓地に置く
        abilities += [dict(_expand_ability(a, macros, where), keyword="g_castle") for a in _G_CASTLE_LEAVE]
    abilities += [_expand_ability(a, macros, where) for a in raw.get("abilities", [])]
    for a in abilities:
        chk.ability(a, where)
    spell = expand_ops(raw.get("spell", []), macros, where)
    chk.ops(spell, where)
    sst_spell = expand_ops(raw.get("sst_spell", []), macros, where)
    chk.ops(sst_spell, where)
    stp_spell = expand_ops(raw.get("stp_spell", []), macros, where)
    chk.ops(stp_spell, where)
    odrive_spell = expand_ops(raw.get("odrive_spell", []), macros, where)
    chk.ops(odrive_spell, where)
    if "o_drive" in raw:
        od = raw["o_drive"]
        legacy = isinstance(od, dict) and set(od) <= {"civ", "count"} and od.get("civ") in CIVS and isinstance(od.get("count"), int)
        multi = isinstance(od, dict) and set(od) <= {"civs", "each"} and isinstance(od.get("civs"), dict) and bool(od["civs"]) \
            and all(cv in CIVS and isinstance(n, int) and n >= 1 for cv, n in od["civs"].items())
        if not (legacy or multi):
            raise DefError(f"{where}: o_drive needs {{civ: <civ>, count: int}} or {{civs: {{<civ>: int, ...}}, each?: bool}}")
    if "mugen_climb" in raw:
        mc = raw["mugen_climb"]
        if not isinstance(mc, dict) or not isinstance(mc.get("tap"), int) or not isinstance(mc.get("cost"), int) \
                or set(mc.get("civs", [])) - CIVS:
            raise DefError(f"{where}: mugen_climb needs {{tap: int, cost: int, civs: [...]}}")
    for t in raw["types"]:
        if t not in CARD_TYPES:
            raise DefError(f"{where}: unknown type '{t}'")
    if set(raw["civs"]) - CIVS:
        raise DefError(f"{where}: unknown civs {raw['civs']}")
    if "evolution" in raw["types"]:
        if "evolve_from" not in raw and not raw.get("s_max"):
            raise DefError(f"{where}: evolution creature needs evolve_from")
        ef = raw.get("evolve_from") or {}
        for f in (ef if isinstance(ef, list) else [ef]):   # 進化V: フィルタのリスト（1つずつ重ねる）
            if "zone" in f and f["zone"] not in chk.zones:   # 第293弾: リスト形の zone はその進化元を探すゾーン（進化GV・Ω）
                raise DefError(f"{where}: unknown evolve_from zone '{f['zone']}'")
            chk.filter({k: v for k, v in f.items() if k != "zone"}, where)
    zone = raw.get("evolve_zone", "bz")
    if zone not in chk.zones:
        raise DefError(f"{where}: unknown evolve_zone '{zone}'")
    ecivs = raw.get("evolve_civs") or []
    for cv in ecivs:
        if cv not in CIVS:
            raise DefError(f"{where}: unknown evolve_civs '{cv}'")
    if ecivs and not raw.get("evolve_any"):
        raise DefError(f"{where}: evolve_civs needs evolve_any")
    for z in raw.get("evolve_zones") or []:
        if z not in chk.zones:
            raise DefError(f"{where}: unknown evolve_zones '{z}'")
    if "evolve_max" in raw:   # 「N体まで」形（第293弾）: evolve_any の上限
        if not isinstance(raw["evolve_max"], int) or isinstance(raw["evolve_max"], bool) or raw["evolve_max"] < 1:
            raise DefError(f"{where}: evolve_max must be a positive int")
        if not raw.get("evolve_any"):
            raise DefError(f"{where}: evolve_max needs evolve_any")
    ss = raw.get("soul_shift")
    if ss is not None:
        if not isinstance(ss, dict) or set(ss) - {"floor"} or not isinstance(ss.get("floor"), int) or ss["floor"] < 0:
            raise DefError(f"{where}: soul_shift must be {{floor: int>=0}}")
        if "evolve_from" not in raw:
            raise DefError(f"{where}: soul_shift needs evolve_from")
    if "free_if" in raw:
        chk.cond(raw["free_if"], where)
    if "galaxy_shield" in raw:
        gs = raw["galaxy_shield"]
        if not isinstance(gs, dict) or not isinstance(gs.get("cost"), int) or set(gs.get("civs", [])) - CIVS:
            raise DefError(f"{where}: galaxy_shield needs {{cost: int, civs: [...]}}")
    if "bazurenda" in raw:
        bz = raw["bazurenda"]
        if not isinstance(bz, dict) or not isinstance(bz.get("cost"), int) or set(bz.get("civs", [])) - CIVS:
            raise DefError(f"{where}: bazurenda needs {{cost: int, civs: [...]}}")
    if "alt_cost" in raw:
        ac = raw["alt_cost"]
        if not isinstance(ac, dict) or not ({"cost", "do"} & set(ac)):
            raise DefError(f"{where}: alt_cost needs {{cost, civs}} or {{do: [...]}}")
        if "cost" in ac and (not isinstance(ac["cost"], int) or set(ac.get("civs", [])) - CIVS):
            raise DefError(f"{where}: alt_cost needs {{cost: int, civs: [...]}}")
        for step in ac.get("do", []):
            if step.get("zone") not in chk.zones or not isinstance(step.get("count"), int):
                raise DefError(f"{where}: alt_cost do step needs {{zone, count: int, to, reason}} or {{zone, count: int, tap: true}}")
            if step.get("tap"):
                # タップで支払う（第57弾）: to/reason は不要
                pass
            elif step.get("to") not in chk.zones:
                raise DefError(f"{where}: alt_cost do step needs {{zone, count: int, to, reason}} or {{zone, count: int, tap: true}}")
            if "filter" in step:
                chk.filter(step["filter"], where)
            if step.get("owner", "you") not in ("you", "opp"):
                raise DefError(f"{where}: alt_cost do step owner は you/opp のみ（第292弾で owner を honor するようになった）")
        if "if" in ac:
            chk.cond(ac["if"], where + ": alt_cost.if")
    if "vividraw" in raw:
        vd = raw["vividraw"]
        if not isinstance(vd, dict) or not isinstance(vd.get("cost"), int) or set(vd.get("civs", [])) - CIVS:
            raise DefError(f"{where}: vividraw needs {{cost: int, civs: [...]}}")
    if "fushigi" in raw:
        fg = raw["fushigi"]
        if not isinstance(fg, dict) or not isinstance(fg.get("cost"), int) or set(fg.get("civs", [])) - CIVS \
                or not isinstance(fg.get("min", 1), int):
            raise DefError(f"{where}: fushigi needs {{cost: int, civs: [...], min: int}}")
    if "recycle" in raw:   # リサイクル（第172弾）: 墓地から代替コストで唱える。civs 省略時はカード自身の文明
        rc = raw["recycle"]
        if not isinstance(rc, dict) or not isinstance(rc.get("cost"), int) or set(rc.get("civs", [])) - CIVS:
            raise DefError(f"{where}: recycle needs {{cost: int, civs: [...]}}")
    if "grave_cast" in raw:   # 墓地から通常コストで唱える（第226弾）: 真偽値のみ
        if not isinstance(raw["grave_cast"], bool):
            raise DefError(f"{where}: grave_cast must be a bool")
    if "rinne" in raw:   # 輪廻∞（第267弾）: 真偽値のみ。ツインパクトのクリーチャー側に付ける
        if not isinstance(raw["rinne"], bool):
            raise DefError(f"{where}: rinne must be a bool")
    if "mana_bakutan" in raw:   # マナ爆誕（第191弾）: 自分のマナゾーンから固定コストで召喚する代替コスト（0 も可）
        mb = raw["mana_bakutan"]
        if not isinstance(mb, int) or isinstance(mb, bool) or mb < 0:
            raise DefError(f"{where}: mana_bakutan must be an int >= 0")
    if "launcher" in raw:   # ランチャーE（第233弾）: 唱える時に自分の条件クリーチャーを好きな数タップする
        lc = raw["launcher"]
        if not isinstance(lc, dict) or set(lc) - {"filter"}:
            raise DefError(f"{where}: launcher must be {{filter}}")
        if "filter" in lc:
            filter(lc["filter"], where)
    if "evo_base_reduce" in raw:   # 進化元依存の軽減（第234弾）: 選んだ進化元が条件に合えば召喚コストを減らす
        eb = raw["evo_base_reduce"]
        if not isinstance(eb, dict) or set(eb) - {"filter", "amount", "min"} \
                or not isinstance(eb.get("amount"), int) or ("min" in eb and not isinstance(eb["min"], int)):
            raise DefError(f"{where}: evo_base_reduce must be {{filter?, amount: int, min?: int}}")
        if "filter" in eb:
            filter(eb["filter"], where)
    if "evolve_total_cost_ge" in raw:   # 超無限進化のコスト合計条件（第236弾）
        if not isinstance(raw["evolve_total_cost_ge"], int) or raw["evolve_total_cost_ge"] < 1:
            raise DefError(f"{where}: evolve_total_cost_ge must be a positive int")
    if "link_to" in raw:   # G・リンク（名前指定・4方向。第197弾）: 「《A》の右横、《B》の上側」の形
        # 第250弾: {side: left|center|right} エントリも可（「中央/右 G・リンクを持つゴッド」の指定）
        lt = raw["link_to"]
        if not isinstance(lt, list) or not lt or any(
                not isinstance(e, dict) or set(e) - {"name", "pos", "side"}
                or ("name" in e and (not isinstance(e.get("name"), str)
                                     or e.get("pos") not in ("right", "left", "up", "down")))
                or ("name" not in e and e.get("side") not in ("left", "center", "right"))
                or ("side" in e and "name" in e) for e in lt):
            raise DefError(f"{where}: link_to needs [{{name: str, pos: right|left|up|down}} | {{side: left|center|right}}]")
    de = None
    if "deck_evolution" in raw:   # デッキ進化（第173弾）: 山札の上から count 枚めくり、進化元にできる
        # クリーチャーがいれば重ねて出す。いなければ手札に戻る（支払い前にめくる。801.1a の進化元
        # 選択と同じく、召喚の可否を決める手順はコスト支払いに先行する）。count>1 は Mデッキ進化
        # （選ばなかった分は rest_to へ）。blind は OMGデッキ進化（めくらず裏向きのまま重ねる）。
        # shuffle_first はめくる前に山札をシャッフルする（OMG）。True は {count: 1} と読む。
        de = raw["deck_evolution"]
        if de is True:
            de = {"count": 1}
        if not isinstance(de, dict) or set(de) - {"count", "rest_to", "blind", "shuffle_first", "stack_all"} \
                or not isinstance(de.get("count", 1), int) or isinstance(de.get("count", 1), bool) \
                or de.get("count", 1) < 1 \
                or ("rest_to" in de and de["rest_to"] not in chk.zones) \
                or not isinstance(de.get("blind", False), bool) \
                or not isinstance(de.get("shuffle_first", False), bool) \
                or not isinstance(de.get("stack_all", False), bool):
            raise DefError(f"{where}: deck_evolution needs {{count?: int >= 1, rest_to?: zone, blind?: bool, shuffle_first?: bool, stack_all?: bool}}")
    if "crystal_soul" in raw:
        cs = raw["crystal_soul"]
        if not isinstance(cs, int) or isinstance(cs, bool) or cs < 1:
            raise DefError(f"{where}: crystal_soul must be an int >= 1")
    if "mana_boost" in raw:
        mb = raw["mana_boost"]
        if not isinstance(mb, dict) or set(mb) - {"filter", "value", "optional"} \
                or not isinstance(mb.get("value"), int) or isinstance(mb.get("value"), bool) or mb.get("value", 0) < 2 \
                or ("optional" in mb and not isinstance(mb["optional"], bool)):
            raise DefError(f"{where}: mana_boost needs {{value: int >= 2, filter?, optional?}}")
        if "filter" in mb:
            chk.filter(mb["filter"], where)
    if raw.get("ace"):   # ACEタマシード（第179弾）: タマシードの面にだけ付く
        if "tamaseed" not in raw["types"]:
            raise DefError(f"{where}: ace needs tamaseed in types")
        if raw["ace"] is not True:
            raise DefError(f"{where}: ace must be true")
    return dict(name=raw["name"], types=raw["types"], civs=raw["civs"], cost=raw["cost"],
                power=raw.get("power", 0), races=split_races(raw.get("races", [])), keywords=names,
                abilities=abilities, spell=spell, sst_spell=sst_spell, stp_spell=stp_spell, odrive_spell=odrive_spell, o_drive=raw.get("o_drive"), mugen_climb=raw.get("mugen_climb"), alt_cost=raw.get("alt_cost"), vividraw=raw.get("vividraw"), fushigi=raw.get("fushigi"), recycle=raw.get("recycle"), grave_cast=bool(raw.get("grave_cast")), rinne=bool(raw.get("rinne")), mana_bakutan=raw.get("mana_bakutan"), link_to=raw.get("link_to"), deck_evolution=de, evolve_from=raw.get("evolve_from"),
                evolve_zone=zone, evolve_any=bool(raw.get("evolve_any", False)),
                evolve_count=(len(raw["evolve_from"]) if isinstance(raw.get("evolve_from"), list)
                              else int(raw.get("evolve_count", 1))),
                evolve_max=(int(raw["evolve_max"]) if raw.get("evolve_max") is not None else None),
                evolve_civs=tuple(raw.get("evolve_civs") or ()), evolve_zones=tuple(raw.get("evolve_zones") or ()),
                soul_shift=raw.get("soul_shift"),
                cost_reduce_per_evo=int(raw.get("cost_reduce_per_evo", 0)),
                free_if=raw.get("free_if"), galaxy_shield=raw.get("galaxy_shield"), bazurenda=raw.get("bazurenda"), tap_entry=bool(raw.get("tap_entry", False)), neo=bool(raw.get("neo", False)), grave_evo=bool(raw.get("grave_evo", False)), star=bool(raw.get("star", False)), s_max=bool(raw.get("s_max", False)), ace=bool(raw.get("ace", False)), hyper=bool(raw.get("hyper", False)), crystal_soul=int(raw.get("crystal_soul", 0)), mana_boost=raw.get("mana_boost"), launcher=raw.get("launcher"), evo_base_reduce=raw.get("evo_base_reduce"), evolve_total_cost_ge=raw.get("evolve_total_cost_ge"), **{"tap_reduce": 0, "s_back": None, **props})


def load_tables():
    def y(name):
        return yaml.safe_load((DATA / "rules" / name).read_text(encoding="utf-8"))
    zones = y("zones.yaml")["zones"]
    keywords = y("keywords.yaml")["keywords"]
    macros = y("op_macros.yaml")["macros"]
    actions = y("permissions.yaml")["actions"]
    steps = [s["name"] for s in y("turn.yaml")["steps"]]
    return zones, keywords, macros, actions, steps


def parse_card(raw: dict, tables, where: str | None = None) -> CardDef:
    zones, keywords, macros, actions, steps = tables
    chk = Checker(zones, keywords, actions, steps)
    where = where or str(raw.get("id"))
    for kw in keywords.values():
        for a in kw.get("abilities", []):
            chk.ability(_expand_ability(a, macros, "keywords.yaml"), "keywords.yaml")
    if "faces" in raw:   # ツインパクト（810）。カード全体の特性は両面を合わせたもの
        faces = [Face(**_load_face(f, keywords, macros, chk, f"{where}/face{i}")) for i, f in enumerate(raw["faces"])]
        if len(faces) != 2:
            raise DefError(f"{where}: twinpact needs exactly 2 faces")
        civs = sorted({c for f in faces for c in f.civs}, key=["light", "water", "darkness", "fire", "nature", "zero"].index)
        return CardDef(id=raw["id"], name="／".join(f.name for f in faces),
                       types=sorted({t for f in faces for t in f.types}), civs=civs,
                       cost=faces[0].cost, power=faces[0].power, mana=raw.get("mana", 1),
                       races=faces[0].races, text=raw.get("text", ""),
                       keywords=sorted({k for f in faces for k in f.keywords}),
                       s_back=next((f.s_back for f in faces if f.s_back is not None), None),
                       abilities=[], spell=[], faces=faces, source=raw.get("source", {}))
    f = _load_face(raw, keywords, macros, chk, where)
    return CardDef(id=raw["id"], mana=raw.get("mana", 1), text=raw.get("text", ""),
                   source=raw.get("source", {}), **f)


# libyaml があれば C 実装の安全ローダを使う（純 Python 版の十数倍速い）。構文の解釈は SafeLoader と同じ
_YamlLoader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def card_yaml_files() -> list[Path]:
    """読み込むカード定義の YAML。環境変数 DMSIM_SKIP_CONVERTED があれば、確認前の変換結果（converted.yaml）は除く（テストを軽くする）。"""
    from .cardfiles import card_files
    skip = os.environ.get("DMSIM_SKIP_CONVERTED")
    return [f for f in card_files() if not (skip and (f.name == "converted.yaml" or f.parent.name == "converted"))]


def _fix_evolution_type(raw: dict) -> None:
    """カードテキストに「進化：／進化-」の行があり evolve_from もあるのに types に evolution が無い札（変換漏れ）を補う。
    抜けるとエンジンが進化元なしで出せてしまい、強いカードが過大評価される。"""
    types = raw.get("types") or []
    if "evolution" in types or raw.get("neo") or raw.get("grave_evo") or raw.get("s_max") or not raw.get("evolve_from"):
        return
    if any(re.match(r"(スター)?進化[：:\-－ー―]", ln.lstrip()) for ln in str(raw.get("text") or "").splitlines()):
        raw["types"] = list(types) + ["evolution"]


REPAIRED: dict[str, list[str]] = {}      # 読み込み時に補った変換の不備（違反コード → カードID）。dataaudit が基準線と照らす


def dedupe_list(abs_: list) -> list:
    """完全に同じ能力の2つ目以降を除く（順序は保つ）。変換器（convert_cards.validate / merge_split）と読み込みの両方が使う。"""
    seen, out = set(), []
    for ab in abs_:
        k = repr(sorted(ab.items(), key=lambda kv: kv[0])) if isinstance(ab, dict) else repr(ab)
        if k not in seen:
            seen.add(k)
            out.append(ab)
    return out


def _dedupe_abilities(raw: dict) -> None:
    """変換の重複（同じ能力が二重に入る）を除く。残すと誘発が2回起き、パワー修整が二重にかかる。
    変換器側でも除いている（validate）ので、ここで直すのは古い変換結果だけ。直したら REPAIRED に記録して監査が数える。"""
    abs_ = raw.get("abilities")
    if not abs_:
        return
    out = dedupe_list(abs_)
    if len(out) != len(abs_):
        raw["abilities"] = out
        REPAIRED.setdefault("duplicate_ability", []).append(str(raw.get("id")))


_RULES_CACHE: dict = {}


def _rules_cache_key(card_files, only_approved):
    sig = []
    for f in card_files:
        p = Path(f)
        try:
            st = p.stat()
            sig.append((str(p), st.st_mtime_ns, st.st_size))
        except OSError:
            sig.append((str(p), -1, -1))
    for name in ("zones.yaml", "keywords.yaml", "op_macros.yaml", "permissions.yaml", "turn.yaml"):
        p = DATA / "rules" / name
        try:
            st = p.stat()
            sig.append((name, st.st_mtime_ns, st.st_size))
        except OSError:
            sig.append((name, -1, -1))
    return (tuple(sig), bool(only_approved))


def load_rules(card_files: list[Path] | None = None, only_approved: bool | None = None) -> Rules:
    """only_approved: 承認済みのカードだけ読む（converted.yaml の未確認分を除く）。省略時は環境変数 DMSIM_ONLY_APPROVED=1 に従う。

    プロセス内キャッシュ: 入力ファイル（カード定義と rules テーブル）の mtime/size が
    同じなら、構築済みの Rules を deepcopy して返す（converted 込みの構築は約20秒、
    deepcopy は約1秒。テストスイートの繰り返し読み込み対策）。only_approved の時は
    承認台帳の変化を署名に含めないためキャッシュを使わない。"""
    if only_approved is None:
        only_approved = bool(os.environ.get("DMSIM_ONLY_APPROVED"))
    if only_approved:
        return _load_rules_impl(card_files, only_approved)
    files = card_files or card_yaml_files()
    key = _rules_cache_key(files, only_approved)
    hit = _RULES_CACHE.get(key)
    if hit is not None:
        return copy.deepcopy(hit)
    rules = _load_rules_impl(files, only_approved)
    _RULES_CACHE[key] = copy.deepcopy(rules)
    return rules


def _load_rules_impl(card_files: list[Path] | None = None, only_approved: bool | None = None) -> Rules:
    tables = load_tables()
    if only_approved is None:
        only_approved = bool(os.environ.get("DMSIM_ONLY_APPROVED"))
    if only_approved:
        from . import approval
        ledger, versions = approval.load(), approval.vocab_versions(tables)
    zones, keywords, macros, actions, steps = tables
    card_files = card_files or card_yaml_files()
    seen_files: set = set()   # 同じファイルを二度渡されても一度だけ読む（呼び出し側の環境変数の差で converted.yaml が重なる場合）
    card_files = [f for f in card_files if not (Path(f).resolve() in seen_files or seen_files.add(Path(f).resolve()))]
    cards: dict[str, CardDef] = {}
    for f in card_files:
        for raw in yaml.load(Path(f).read_text(encoding="utf-8"), Loader=_YamlLoader).get("cards") or []:
            if only_approved and not approval.is_usable(raw, ledger, versions):
                continue
            _fix_evolution_type(raw)
            _dedupe_abilities(raw)
            cd = parse_card(raw, tables)
            if cd.id in cards:
                raise DefError(f"duplicate card id {cd.id}")
            cards[cd.id] = cd
    from .identity import AliasDict
    aliases = {a: cid for cid, cd in cards.items() for a in (cd.source or {}).get("aliases", [])}
    return Rules(zones=zones, keywords=keywords, macros=macros, cards=AliasDict(cards, aliases), actions=actions, steps=steps)
