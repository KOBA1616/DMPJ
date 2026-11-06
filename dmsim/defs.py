"""カード・ゾーン・キーワード定義の読み込みと検証。

効果DSLは閉じた語彙（設計判断④）。ここで未知の op / 引数 / イベント / 能力種別 / mod を弾くことで、
LLM が変換したカードデータの機械チェックを兼ねる。op の引数の型は registry の OP_ARGS が正。
"""
from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DATA = Path(__file__).resolve().parent.parent / "data"


def core_ops() -> dict[str, dict[str, str]]:
    """コア語彙 = エンジンに登録された op と引数の型。ここに無い op はマクロ（op_macros.yaml）で定義されていなければエラー。"""
    from .engine.registry import OP_ARGS
    from .engine import ops  # noqa: F401  登録を確実にする
    return OP_ARGS

EVENTS = {"move", "draw", "cast", "summon", "attack", "block", "break", "tap", "untap",
          "turn_start", "turn_end", "battle_win", "choose", "battle", "battle_start", "attack_end", "lose", "mugon_used"}
ABILITY_KINDS = {"trigger", "replace", "static", "declare", "activate", "silent", "state", "partner"}   # state: 状態を常に見て、満たされたら勝敗が決まる常在効果（if と effect: [win/lose]）。partner: [P]能力（単独では機能せず、キズナ等で「使う」ことで解決する）
ABILITY_KEYS = {"kind", "when", "if", "effect", "instead", "optional", "affects", "mod", "zone", "keyword", "cost", "id",
                "once_per_turn", "first_time", "sst", "stp", "odrive", "choukon", "bazurenda", "any_attacker"}
REASONS = {"put", "destroy", "return", "discard", "charge", "summon", "cast", "break",
           "draw", "battle", "sba", "resolve", "evolve", "seal"}
VIAS = {"revolution_change", "generate"}   # 出し方の印（「革命チェンジによって出た時」など）
DURATIONS_FIXED = {"end_of_turn", "during_attack", "permanent", "until_next_own_turn_start"}
MOD_KEYS = {"power", "grant", "allow", "deny", "breaks", "breaks_per_power", "battle_power", "power_when", "cost", "cost_min", "cost_may", "sac_reduce", "opt_reduce", "ignore", "ignore_ids", "gain", "require", "add_of", "add_races", "no_leave", "must_be_attacked", "battle_indestructible", "win_all_battles", "add_civs", "indestructible"}
REQUIRES = {"attack", "block"}   # 強制（506.1b 攻撃しなければならない, 507.1b ブロックしなければならない）
POSITIONS = {"top", "bottom"}
PERMANENT_TYPES = {"tamaseed", "field", "cross_gear"}   # 手札から実行してバトルゾーンに出るクリーチャー以外のカード（315, 308, 303）
CARD_TYPES = {"creature", "spell", "evolution"} | PERMANENT_TYPES
CIVS = {"light", "water", "darkness", "fire", "nature", "zero"}
SELECTOR_KEYS = {"zone", "owner", "owner_of", "filter", "count", "up_to", "from_top", "chooser", "ref", "other",
                 "under_of", "look", "exlife_of", "total_cost_le", "total_cost_ge"}   # look: 非公開ゾーン（山札など）の中身を見て選ぶ。total_cost_*: コストの合計が上限以下／下限以上になるように好きな数選ぶ
FILTER_KEYS = {"any_of", "types", "not_types", "civs", "civs_all", "not_civs", "races", "race_has", "not_race_has", "name", "name_has", "not_name",
               "cost_le", "cost_ge", "power_le", "power_ge", "tapped", "keyword", "multicolor", "colorless", "face_down", "face_up", "neo", "vanilla", "sealed", "evolution", "mugen_climb", "twinpact", "vividraw", "fushigi", "linked_god", "entered_this_turn"}
FILTER_EXPR_KEYS = {"cost_le", "cost_ge", "power_le", "power_ge", "races"}   # 値に式を書ける（解決時に計算）


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
    evolve_from: dict | None = None                       # 進化元の条件（801.1a）。filter 形式
    evolve_zone: str = "bz"                               # 進化元を探すゾーン（超無限墓地進化は graveyard）
    evolve_any: bool = False                              # 進化元を1体以上選べる（超無限墓地進化）
    evolve_count: int = 1                                 # 進化元をちょうどこの数だけ重ねる（進化GV は3体）
    cost_reduce_per_evo: int = 0                          # 進化元1体につき召喚コストをいくら減らすか
    tap_reduce: int = 0                                   # ハイパーエナジー: コストが異なる自分のクリーチャー1体をタップするごとに減るコスト
    s_back: str | dict | None = None                      # S・バック: 文明名（文字列）か、捨てるカードの条件（filter。第52弾で種族・複合文明・ツインパクトに対応）
    free_if: dict | None = None                           # 条件を満たす間はコストを支払わずに召喚できる（G・ゼロ）
    galaxy_shield: dict | None = None                     # ギャラクシールド: {cost, civs} 代替コストで表向きにシールド化する
    bazurenda: dict | None = None                         # バズレンダ: {cost, civs} 支払い時に追加でこのコストを好きな回数払える
    neo: bool = False                                     # NEO進化: 通常召喚も、evolve_from の上に重ねることもできる
    grave_evo: bool = False                               # 墓地進化: 通常召喚も、自分の墓地のクリーチャーの上に重ねて出すこともできる（evolve_zone: graveyard と併用）
    star: bool = False                                    # スター進化: 離れる時は一番上のカードだけが離れ、下は残る
    s_max: bool = False                                   # S-MAX進化: 進化元を必要とせず、通常のクリーチャーとして召喚できる
    hyper: bool = False                                   # ハイパー化（他の自分のクリーチャー1体をタップしてハイパーモードを解放できる）
    resolve_to: str = "graveyard"                         # 呪文の解決後の置き場所（チャージャー等）
    after_resolve: list[dict] = field(default_factory=list)

    def is_creature(self) -> bool:
        return "creature" in self.types

    def is_spell(self) -> bool:
        return "spell" in self.types

    def is_permanent(self) -> bool:
        """クリーチャーでなく、実行するとバトルゾーンに出るカード（タマシード・フィールド・クロスギア）。"""
        return not self.is_creature() and bool(PERMANENT_TYPES & set(self.types))


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
    evolve_from: dict | None = None
    evolve_zone: str = "bz"
    evolve_any: bool = False
    evolve_count: int = 1
    cost_reduce_per_evo: int = 0
    tap_reduce: int = 0
    s_back: str | dict | None = None
    free_if: dict | None = None
    galaxy_shield: dict | None = None
    bazurenda: dict | None = None                         # バズレンダ: {cost, civs}
    neo: bool = False
    grave_evo: bool = False
    star: bool = False
    s_max: bool = False
    hyper: bool = False
    resolve_to: str = "graveyard"
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

    def value(self, ty, v, where):
        if ty == "filter":
            return self.filter(v, where)
        if ty == "zone" and v not in self.zones:
            raise DefError(f"{where}: unknown zone '{v}'")
        if ty == "reason" and v not in REASONS:
            raise DefError(f"{where}: unknown reason '{v}'")
        if ty == "player" and v not in ("you", "opp"):
            raise DefError(f"{where}: player must be you/opp, got '{v}'")
        if ty == "players" and v not in ("you", "opp", "each"):
            raise DefError(f"{where}: players must be you/opp/each, got '{v}'")
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
        if "under_of" not in sel and "exlife_of" not in sel and "ref" not in sel and "zone" not in sel:
            raise DefError(f"{where}: selector needs zone or ref")
        for z in ([sel["zone"]] if isinstance(sel.get("zone"), str) else sel.get("zone", [])):
            if z != "any" and z not in self.zones:   # any = すべてのゾーン、配列 = そのうちのどれか
                raise DefError(f"{where}: unknown zone '{z}'")
        if sel.get("owner", "you") not in ("you", "opp", "any"):
            raise DefError(f"{where}: bad owner '{sel['owner']}'")
        for k in ("total_cost_le", "total_cost_ge"):
            if k in sel:
                self.expr(sel[k], where)
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
            if k in f and set(f[k]) - CIVS:
                raise DefError(f"{where}: unknown civs {f[k]}")
        if "keyword" in f and f["keyword"] not in self.keywords:
            raise DefError(f"{where}: unknown keyword '{f['keyword']}'")
        for k in FILTER_EXPR_KEYS & set(f):
            if not (k == "races" and isinstance(f[k], list)):
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
            if k == "entered":   # このターンに出したクリーチャーの数 {owner, other?}
                if not isinstance(v, dict) or set(v) - {"owner", "other"} or v.get("owner", "you") not in ("you", "opp"):
                    raise DefError(f"{where}: entered needs {{owner: you/opp, other?: bool}}")
                return
            if k in ("var", "cost_of", "power_of", "races_of", "race"):
                return
            if k == "link_count":   # リンクしているカードの枚数（値は self 固定で無視される）
                return
            if k == "seals":   # そのプレイヤーの封印の総数 {owner: you/opp}
                if not isinstance(v, dict) or set(v) - {"owner"} or v.get("owner", "you") not in ("you", "opp"):
                    raise DefError(f"{where}: seals needs {{owner: you/opp}}")
                return
            if k == "seals_on":   # self に付いている封印の数（値は self 固定で無視される）
                return
            if k == "sum":
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
        raise DefError(f"{where}: unknown cond '{k}'")

    def count_spec(self, v, where):
        """mod の count: セレクタ（体数）か、civ_count / sum を含む式（文明の種類数など）。"""
        if isinstance(v, dict) and ("civ_count" in v or "sum" in v):
            return self.expr(v, where)
        return self.selector(v, where)

    def mod(self, m, where):
        bad = set(m) - MOD_KEYS
        if bad:
            raise DefError(f"{where}: unknown mod keys {sorted(bad)}")
        if "power" in m and isinstance(m["power"], dict):
            pm = m["power"]
            if set(pm) - {"amount", "count"} or not isinstance(pm.get("amount"), int):
                raise DefError(f"{where}: power needs amount (int) and optional count")
            if "count" in pm:
                self.count_spec(pm["count"], where)
        if "add_races" in m:
            if not isinstance(m["add_races"], list) or not all(isinstance(x, str) for x in m["add_races"]):
                raise DefError(f"{where}: add_races must be a list of race names")
        if "breaks" in m:
            b = m["breaks"]
            if isinstance(b, dict):
                if "count" in b:   # {count: セレクタ, amount?: 係数}（クルー・ブレイカー等）: 1 + amount × 数
                    if set(b) - {"amount", "count"} or ("amount" in b and not isinstance(b["amount"], int)):
                        raise DefError(f"{where}: breaks dict with count takes only amount/count")
                    self.count_spec(b["count"], where)
                else:   # 式形式（{civ_count: セレクタ}、第79弾）: 1 + 文明の種類数
                    if set(b) != {"civ_count"}:
                        raise DefError(f"{where}: breaks must be an int, {{count: <selector>}}, or {{civ_count: <selector>}}")
                    self.count_spec(b["civ_count"], where)
            elif not isinstance(b, int):
                raise DefError(f"{where}: breaks must be an int or a dict (1 + value)")
        if "cost_may" in m:
            cm = m["cost_may"]
            if not isinstance(cm, dict) or set(cm) - {"amount", "once", "min", "must"} or not isinstance(cm.get("amount"), int) \
                    or ("once" in cm and not isinstance(cm["once"], bool)) or ("min" in cm and not isinstance(cm["min"], int)) \
                    or ("must" in cm and not isinstance(cm["must"], bool)):
                raise DefError(f"{where}: cost_may must be {{amount: int, once?: bool, min?: int, must?: bool}}")
        if "no_leave" in m:
            nl = m["no_leave"]
            if nl is not True and not (isinstance(nl, dict) and set(nl) <= {"except_destroy", "by_opp", "except_battle"}
                                       and all(isinstance(v, bool) for v in nl.values())):
                raise DefError(f"{where}: no_leave must be true or {{except_destroy?: bool, by_opp?: bool, except_battle?: bool}}")
        if "must_be_attacked" in m and m["must_be_attacked"] is not True:
            raise DefError(f"{where}: must_be_attacked must be true")
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
            if "then" in o and o["then"] not in ("destroy", "deck_bottom_draw"):
                raise DefError(f"{where}: opt_reduce.then must be destroy / deck_bottom_draw")
            if "do" in o:
                do = o["do"]
                if not isinstance(do, dict) or "select" not in do or set(do) - {"select", "move_to", "shuffle", "min", "max", "tap"}:
                    raise DefError(f"{where}: opt_reduce.do needs select and optional move_to/shuffle/min/max/tap")
                self.selector(do["select"], where)
                if "move_to" in do and do["move_to"] not in self.zones:
                    raise DefError(f"{where}: opt_reduce.do.move_to must be a zone")
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
        if "power_when" in m:   # 攻撃中／ブロック中のパワー修整: {amount: N, count: <selector>, when: attacking|blocking}。バトルをしていない間（プレイヤーを攻撃中など）も含む
            pw = m["power_when"]
            if not isinstance(pw, dict) or set(pw) - {"amount", "count", "when"} or not isinstance(pw.get("amount"), int) \
                    or pw.get("when") not in ("attacking", "blocking"):
                raise DefError(f"{where}: power_when needs amount (int), when: attacking|blocking and optional count (selector)")
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
            for v in vals:
                if v not in REASONS:
                    raise DefError(f"{where}: unknown reason '{v}'")
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
        if w.get("sealed_from") is not None and w["sealed_from"] not in ("self",) and not isinstance(w["sealed_from"], dict):
            raise DefError(f"{where}: bad sealed_from '{w['sealed_from']}'")

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
        if kind == "activate":   # 起動型能力（602）。cost: {tap: self} か {tap: {filter}}（攻撃する代わりにタップして使う。602.3a）
            c = ab.get("cost")   # tap_mana: 自分のマナゾーンのタップされていないカードをその枚数追加でタップする（DM24系の複合コスト）
            # under: このクリーチャーの下にあるカードをその枚数墓地に置く（メテオバーン「攻撃できる時」形。第53弾。tap と併用可、tap_mana とは併用不可）
            if not isinstance(c, dict) or not set(c) <= {"tap", "tap_mana", "under"} or not ("tap" in c or "under" in c):
                raise DefError(f"{where}: activate needs cost: {{tap: self | <filter>, tap_mana?: int, under?: int}}")
            if "tap_mana" in c and not (isinstance(c["tap_mana"], int) and c["tap_mana"] >= 1):
                raise DefError(f"{where}: cost.tap_mana must be a positive int")
            if "under" in c and not (isinstance(c["under"], int) and c["under"] >= 1):
                raise DefError(f"{where}: cost.under must be a positive int")
            if "under" in c and "tap_mana" in c:
                raise DefError(f"{where}: cost.under cannot combine with tap_mana")
            if "tap" in c and c["tap"] != "self":
                if not isinstance(c["tap"], dict):
                    raise DefError(f"{where}: cost.tap must be 'self' or a filter")
                self.filter(c["tap"], where)
            if "effect" not in ab:
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


def _expand_ability(ab, macros, where):
    ab = dict(ab)
    for k in ("effect", "instead"):
        if k in ab:
            ab[k] = expand_ops(ab[k], macros, where)
    return ab


def _load_face(raw, keywords, macros, chk: Checker, where) -> dict:
    names, abilities = [], []
    props = {"resolve_to": "graveyard", "after_resolve": []}
    for kw in raw.get("keywords", []):
        if kw not in keywords:
            raise DefError(f"{where}: unknown keyword '{kw}'")
        names.append(kw)
        abilities += [dict(_expand_ability(a, macros, where), keyword=kw) for a in keywords[kw]["abilities"]]
        for k, v in keywords[kw].get("card", {}).items():
            props[k] = expand_ops(v, macros, where) if k == "after_resolve" else v
    props["resolve_to"] = raw.get("resolve_to", props["resolve_to"])   # 唱えた後の置き場所を直接指定（シールドに加わる呪文など）
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
            chk.filter({k: v for k, v in f.items() if k != "zone"}, where)
    zone = raw.get("evolve_zone", "bz")
    if zone not in chk.zones:
        raise DefError(f"{where}: unknown evolve_zone '{zone}'")
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
    return dict(name=raw["name"], types=raw["types"], civs=raw["civs"], cost=raw["cost"],
                power=raw.get("power", 0), races=split_races(raw.get("races", [])), keywords=names,
                abilities=abilities, spell=spell, sst_spell=sst_spell, stp_spell=stp_spell, odrive_spell=odrive_spell, o_drive=raw.get("o_drive"), mugen_climb=raw.get("mugen_climb"), alt_cost=raw.get("alt_cost"), vividraw=raw.get("vividraw"), fushigi=raw.get("fushigi"), evolve_from=raw.get("evolve_from"),
                evolve_zone=zone, evolve_any=bool(raw.get("evolve_any", False)),
                evolve_count=(len(raw["evolve_from"]) if isinstance(raw.get("evolve_from"), list)
                              else int(raw.get("evolve_count", 1))),
                cost_reduce_per_evo=int(raw.get("cost_reduce_per_evo", 0)),
                free_if=raw.get("free_if"), galaxy_shield=raw.get("galaxy_shield"), bazurenda=raw.get("bazurenda"), neo=bool(raw.get("neo", False)), grave_evo=bool(raw.get("grave_evo", False)), star=bool(raw.get("star", False)), s_max=bool(raw.get("s_max", False)), hyper=bool(raw.get("hyper", False)), **{"tap_reduce": 0, "s_back": None, **props})


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


def card_yaml_files() -> list[Path]:
    """読み込むカード定義の YAML。環境変数 DMSIM_SKIP_CONVERTED があれば、確認前の変換結果（converted.yaml）は除く（テストを軽くする）。"""
    from .cardfiles import card_files
    skip = os.environ.get("DMSIM_SKIP_CONVERTED")
    return [f for f in card_files() if not (skip and (f.name == "converted.yaml" or f.parent.name == "converted"))]


def load_rules(card_files: list[Path] | None = None, only_approved: bool | None = None) -> Rules:
    """only_approved: 承認済みのカードだけ読む（converted.yaml の未確認分を除く）。省略時は環境変数 DMSIM_ONLY_APPROVED=1 に従う。"""
    tables = load_tables()
    if only_approved is None:
        only_approved = bool(os.environ.get("DMSIM_ONLY_APPROVED"))
    if only_approved:
        from . import approval
        ledger, versions = approval.load(), approval.vocab_versions(tables)
    zones, keywords, macros, actions, steps = tables
    card_files = card_files or card_yaml_files()
    cards: dict[str, CardDef] = {}
    for f in card_files:
        for raw in yaml.safe_load(Path(f).read_text(encoding="utf-8")).get("cards") or []:
            if only_approved and not approval.is_usable(raw, ledger, versions):
                continue
            cd = parse_card(raw, tables)
            if cd.id in cards:
                raise DefError(f"duplicate card id {cd.id}")
            cards[cd.id] = cd
    from .identity import AliasDict
    aliases = {a: cid for cid, cd in cards.items() for a in (cd.source or {}).get("aliases", [])}
    return Rules(zones=zones, keywords=keywords, macros=macros, cards=AliasDict(cards, aliases), actions=actions, steps=steps)
