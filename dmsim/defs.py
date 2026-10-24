"""カード・ゾーン・キーワード定義の読み込みと検証。

効果DSLは閉じた語彙（設計判断④）。ここで未知の op / イベント / 能力種別を弾くことで、
LLM が変換したカードデータの機械チェックを兼ねる。
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DATA = Path(__file__).resolve().parent.parent / "data"


def core_ops() -> set[str]:
    """コア語彙 = エンジンに登録された op。ここに無い op はマクロ（op_macros.yaml）で定義されていなければエラー。"""
    from .engine.registry import OPS
    from .engine import ops  # noqa: F401  登録を確実にする
    return set(OPS)

EVENTS = {"move", "draw", "cast", "summon", "attack", "block", "break", "tap", "untap",
          "turn_start", "turn_end"}
ABILITY_KINDS = {"trigger", "replace", "static"}
REASONS = {"put", "destroy", "return", "discard", "charge", "summon", "cast", "break",
           "draw", "battle", "sba", "resolve"}


class DefError(ValueError):
    pass


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
    keywords: list[str] = field(default_factory=list)   # marker 型キーワード
    abilities: list[dict] = field(default_factory=list)  # 展開済みの能力
    spell: list[dict] = field(default_factory=list)      # 呪文の解決 ops

    def is_creature(self) -> bool:
        return "creature" in self.types

    def is_spell(self) -> bool:
        return "spell" in self.types


@dataclass
class Rules:
    zones: dict
    keywords: dict
    macros: dict
    cards: dict[str, CardDef]


def _subst(obj, args):
    if isinstance(obj, str) and obj.startswith("$"):
        key = obj[1:]
        if key not in args:
            raise DefError(f"macro argument missing: {key}")
        return args[key]
    if isinstance(obj, dict):
        return {k: _subst(v, args) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_subst(v, args) for v in obj]
    return obj


def expand_ops(ops: list[dict], macros: dict, where: str) -> list[dict]:
    out = []
    core = core_ops()
    for op in ops:
        name = op.get("op")
        if name in core:
            op = dict(op)
            for k in ("body", "then", "else"):
                if k in op:
                    op[k] = expand_ops(op[k], macros, where)
            out.append(op)
        elif name in macros:
            args = {k: v for k, v in op.items() if k != "op"}
            out.extend(expand_ops(_subst(copy.deepcopy(macros[name]), args), macros, where))
        else:
            raise DefError(f"{where}: unknown op '{name}'")
    return out


def _check_ops(ops, zones, where):
    for op in ops:
        if op["op"] == "move":
            if op.get("to") not in zones:
                raise DefError(f"{where}: unknown zone '{op.get('to')}'")
            if op.get("reason") not in REASONS:
                raise DefError(f"{where}: unknown reason '{op.get('reason')}'")
        for k in ("body", "then", "else"):
            if k in op:
                _check_ops(op[k], zones, where)


def _expand_ability(ab, macros, zones, where):
    kind = ab.get("kind")
    if kind not in ABILITY_KINDS:
        raise DefError(f"{where}: unknown ability kind '{kind}'")
    ab = dict(ab)
    if kind in ("trigger", "replace"):
        ev = ab.get("when", {}).get("event")
        if ev not in EVENTS:
            raise DefError(f"{where}: unknown event '{ev}'")
    for k in ("effect", "instead"):
        if k in ab:
            ab[k] = expand_ops(ab[k], macros, where)
            _check_ops(ab[k], zones, where)
    return ab


def load_rules(card_files: list[Path] | None = None) -> Rules:
    zones = yaml.safe_load((DATA / "rules/zones.yaml").read_text(encoding="utf-8"))["zones"]
    keywords = yaml.safe_load((DATA / "rules/keywords.yaml").read_text(encoding="utf-8"))["keywords"]
    macros = yaml.safe_load((DATA / "rules/op_macros.yaml").read_text(encoding="utf-8"))["macros"]
    card_files = card_files or sorted((DATA / "cards").glob("*.yaml"))
    cards: dict[str, CardDef] = {}
    for f in card_files:
        for raw in yaml.safe_load(Path(f).read_text(encoding="utf-8"))["cards"]:
            where = f"{raw.get('id')}"
            markers, abilities = [], []
            for kw in raw.get("keywords", []):
                if kw not in keywords:
                    raise DefError(f"{where}: unknown keyword '{kw}'")
                if keywords[kw]["kind"] == "marker":
                    markers.append(kw)
                else:
                    abilities += [_expand_ability(a, macros, zones, where) for a in keywords[kw]["abilities"]]
            abilities += [_expand_ability(a, macros, zones, where) for a in raw.get("abilities", [])]
            spell = expand_ops(raw.get("spell", []), macros, where)
            _check_ops(spell, zones, where)
            cd = CardDef(id=raw["id"], name=raw["name"], types=raw["types"], civs=raw["civs"],
                         cost=raw["cost"], power=raw.get("power", 0), mana=raw.get("mana", 1), races=raw.get("races", []),
                         text=raw.get("text", ""), keywords=markers, abilities=abilities, spell=spell)
            if cd.id in cards:
                raise DefError(f"duplicate card id {cd.id}")
            cards[cd.id] = cd
    return Rules(zones=zones, keywords=keywords, macros=macros, cards=cards)
