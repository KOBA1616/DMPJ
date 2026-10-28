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
          "turn_start", "turn_end", "battle_win", "choose", "battle"}
ABILITY_KINDS = {"trigger", "replace", "static", "declare"}
ABILITY_KEYS = {"kind", "when", "if", "effect", "instead", "optional", "affects", "mod", "zone", "keyword"}
REASONS = {"put", "destroy", "return", "discard", "charge", "summon", "cast", "break",
           "draw", "battle", "sba", "resolve", "evolve"}
VIAS = {"revolution_change", "generate"}   # 出し方の印（「革命チェンジによって出た時」など）
DURATIONS_FIXED = {"end_of_turn", "during_attack", "permanent", "until_next_own_turn_start"}
MOD_KEYS = {"power", "grant", "allow", "deny", "breaks", "breaks_per_power", "battle_power", "cost", "cost_min", "sac_reduce", "opt_reduce", "ignore", "gain"}
POSITIONS = {"top", "bottom"}
PERMANENT_TYPES = {"tamaseed", "field", "cross_gear"}   # 手札から実行してバトルゾーンに出るクリーチャー以外のカード（315, 308, 303）
CARD_TYPES = {"creature", "spell", "evolution"} | PERMANENT_TYPES
CIVS = {"light", "water", "darkness", "fire", "nature", "zero"}
SELECTOR_KEYS = {"zone", "owner", "owner_of", "filter", "count", "up_to", "from_top", "chooser", "ref", "other",
                 "under_of", "look", "exlife_of"}   # look: 非公開ゾーン（山札など）の中身を見て選ぶ
FILTER_KEYS = {"types", "not_types", "civs", "not_civs", "races", "race_has", "name", "name_has", "not_name",
               "cost_le", "cost_ge", "power_le", "power_ge", "tapped", "keyword", "multicolor"}
FILTER_EXPR_KEYS = {"cost_le", "cost_ge", "power_le", "power_ge"}   # 値に式を書ける（解決時に計算）


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
    evolve_from: dict | None = None                       # 進化元の条件（801.1a）。filter 形式
    evolve_zone: str = "bz"                               # 進化元を探すゾーン（超無限墓地進化は graveyard）
    evolve_any: bool = False                              # 進化元を1体以上選べる（超無限墓地進化）
    cost_reduce_per_evo: int = 0                          # 進化元1体につき召喚コストをいくら減らすか
    tap_reduce: int = 0                                   # ハイパーエナジー: コストが異なる自分のクリーチャー1体をタップするごとに減るコスト
    free_if: dict | None = None                           # 条件を満たす間はコストを支払わずに召喚できる（G・ゼロ）
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
    evolve_from: dict | None = None
    evolve_zone: str = "bz"
    evolve_any: bool = False
    cost_reduce_per_evo: int = 0
    tap_reduce: int = 0
    free_if: dict | None = None
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
        self.filter(sel.get("filter", {}), where)

    def filter(self, f, where):
        bad = set(f) - FILTER_KEYS
        if bad:
            raise DefError(f"{where}: unknown filter keys {sorted(bad)}")
        for k in ("civs", "not_civs"):
            if k in f and set(f[k]) - CIVS:
                raise DefError(f"{where}: unknown civs {f[k]}")
        if "keyword" in f and f["keyword"] not in self.keywords:
            raise DefError(f"{where}: unknown keyword '{f['keyword']}'")
        for k in FILTER_EXPR_KEYS & set(f):
            self.expr(f[k], where)

    def expr(self, x, where):
        if isinstance(x, int):
            return
        if isinstance(x, dict) and len(x) == 1:
            k, v = next(iter(x.items()))
            if k == "count":
                return self.selector(v, where)
            if k == "var":
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
        if k == "marked":
            if not isinstance(v, str):
                raise DefError(f"{where}: marked needs a name")
            return
        if k == "is_turn":
            if v not in ("you", "opp"):
                raise DefError(f"{where}: is_turn must be you/opp")
            return
        raise DefError(f"{where}: unknown cond '{k}'")

    def mod(self, m, where):
        bad = set(m) - MOD_KEYS
        if bad:
            raise DefError(f"{where}: unknown mod keys {sorted(bad)}")
        for kw in m.get("grant", []):
            if kw not in self.keywords:
                raise DefError(f"{where}: unknown keyword '{kw}'")
        for k in ("allow", "deny"):
            for e in m.get(k, []):
                act = e if isinstance(e, str) else e.get("action")
                if act not in self.actions:
                    raise DefError(f"{where}: unknown action '{act}'")
                if isinstance(e, dict):
                    self.filter(e.get("other", {}), where)
        if "cost" in m:   # 支払うコストの増減: 整数、または {amount: N, count: <selector>}（1体につきN。amount が負なら軽減）
            cm = m["cost"]
            if isinstance(cm, dict):
                if set(cm) - {"amount", "count"} or not isinstance(cm.get("amount"), int):
                    raise DefError(f"{where}: cost needs amount (int) and optional count (selector)")
                if "count" in cm:
                    self.selector(cm["count"], where)
            elif not isinstance(cm, int):
                raise DefError(f"{where}: cost must be int or {{amount, count}}")
        if "cost_min" in m and not isinstance(m["cost_min"], int):
            raise DefError(f"{where}: cost_min must be int")
        if "battle_power" in m:   # バトル中だけのパワー修整: {amount: N, count: <selector>, only: attacking|blocking}（ハンティング。attacking は「攻撃中」＝攻撃側のときだけ、blocking は「ブロック中」＝ブロックしたクリーチャーのときだけ）
            bp = m["battle_power"]
            if not isinstance(bp, dict) or set(bp) - {"amount", "count", "only"} or not isinstance(bp.get("amount"), int):
                raise DefError(f"{where}: battle_power needs amount (int) and optional count (selector) / only: attacking|blocking")
            if "only" in bp and bp["only"] not in ("attacking", "blocking"):
                raise DefError(f"{where}: battle_power only must be attacking or blocking")
            if "count" in bp:
                self.selector(bp["count"], where)
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
            if k in w and w[k] not in self.zones:
                raise DefError(f"{where}: unknown zone '{w[k]}'")
        if "reason" in w and w["reason"] not in REASONS:
            raise DefError(f"{where}: unknown reason '{w['reason']}'")
        if "via" in w and w["via"] not in VIAS:
            raise DefError(f"{where}: unknown via '{w['via']}'")

    def ability(self, ab, where):
        kind = ab.get("kind")
        if kind not in ABILITY_KINDS:
            raise DefError(f"{where}: unknown ability kind '{kind}'")
        bad = set(ab) - ABILITY_KEYS
        if bad:
            raise DefError(f"{where}: unknown ability keys {sorted(bad)}")
        if kind in ("trigger", "replace", "declare"):
            self.when(ab.get("when", {}), where)
        if kind == "static" and "mod" in ab:
            self.mod(ab["mod"], where)
        if kind in ("static", "trigger") and ab.get("zone", "bz") not in self.zones:
            raise DefError(f"{where}: unknown zone '{ab['zone']}'")
        aff = ab.get("affects")
        if isinstance(aff, dict):
            if aff.get("zone", "bz") not in self.zones:
                raise DefError(f"{where}: unknown zone '{aff['zone']}'")
            self.filter(aff.get("filter", {}), where)
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
    abilities += [_expand_ability(a, macros, where) for a in raw.get("abilities", [])]
    for a in abilities:
        chk.ability(a, where)
    spell = expand_ops(raw.get("spell", []), macros, where)
    chk.ops(spell, where)
    for t in raw["types"]:
        if t not in CARD_TYPES:
            raise DefError(f"{where}: unknown type '{t}'")
    if set(raw["civs"]) - CIVS:
        raise DefError(f"{where}: unknown civs {raw['civs']}")
    if "evolution" in raw["types"]:
        if "evolve_from" not in raw:
            raise DefError(f"{where}: evolution creature needs evolve_from")
        chk.filter({k: v for k, v in raw["evolve_from"].items() if k != "zone"}, where)
    zone = raw.get("evolve_zone", "bz")
    if zone not in chk.zones:
        raise DefError(f"{where}: unknown evolve_zone '{zone}'")
    if "free_if" in raw:
        chk.cond(raw["free_if"], where)
    return dict(name=raw["name"], types=raw["types"], civs=raw["civs"], cost=raw["cost"],
                power=raw.get("power", 0), races=raw.get("races", []), keywords=names,
                abilities=abilities, spell=spell, evolve_from=raw.get("evolve_from"),
                evolve_zone=zone, evolve_any=bool(raw.get("evolve_any", False)),
                cost_reduce_per_evo=int(raw.get("cost_reduce_per_evo", 0)),
                free_if=raw.get("free_if"), **{"tap_reduce": 0, **props})


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
