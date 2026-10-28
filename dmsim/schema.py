"""カードDSLの JSON Schema を registry と data/rules から生成する。

LLM にカードテキストを変換させる時のスキーマとして渡し、出力の一次チェックにも使う
（最終的な検査は defs.parse_card。こちらは op の引数の型と語彙の一覧を機械可読にしたもの）。

    python -m dmsim.schema > data/schema/card.schema.json
"""
from __future__ import annotations

import json

from .defs import CARD_TYPES, CIVS, DURATIONS_FIXED, EVENTS, FILTER_KEYS, MOD_KEYS, POSITIONS, REASONS, VIAS, \
    core_ops, load_tables


def build() -> dict:
    zones, keywords, macros, actions, steps = load_tables()
    ops = core_ops()
    ref = lambda n: {"$ref": f"#/$defs/{n}"}  # noqa: E731
    arg = {
        "selector": ref("selector"), "zone": {"enum": sorted(zones)}, "reason": {"enum": sorted(REASONS)},
        "expr": ref("expr"), "cond": ref("cond"), "ops": ref("ops"), "oplists": {"type": "array", "minItems": 2, "items": ref("ops")}, "player": {"enum": ["you", "opp"]},
        "players": {"enum": ["you", "opp", "each"]}, "mod": ref("mod"), "duration": {"enum": sorted(DURATIONS_FIXED)}, "position": {"enum": sorted(POSITIONS)},
        "step": {"enum": steps}, "str": {"type": "string"}, "int": {"type": "integer"},
        "bool": {"type": "boolean"}, "any": {}, "ability": ref("ability"),
    }
    op_schemas = []
    for name, args in sorted(ops.items()):
        props = {"op": {"const": name}}
        req = ["op"]
        for k, ty in args.items():
            props[k] = arg[ty.rstrip("?")]
            if not ty.endswith("?"):
                req.append(k)
        op_schemas.append({"type": "object", "properties": props, "required": req, "additionalProperties": False})
    for name in sorted(macros):   # マクロは引数を展開後に検査するので、ここでは名前だけ
        op_schemas.append({"type": "object", "properties": {"op": {"const": name}}, "required": ["op"],
                           "description": f"macro: {json.dumps(macros[name], ensure_ascii=False)}"})
    perm = {"anyOf": [{"enum": sorted(actions)},
                      {"type": "object", "properties": {"action": {"enum": sorted(actions)}, "other": ref("filter")},
                       "required": ["action"], "additionalProperties": False}]}
    face_props = {
        "name": {"type": "string"}, "types": {"type": "array", "items": {"enum": sorted(CARD_TYPES)}},
        "civs": {"type": "array", "items": {"enum": sorted(CIVS)}}, "cost": {"type": "integer"},
        "power": {"type": "integer"}, "races": {"type": "array", "items": {"type": "string"}},
        "keywords": {"type": "array", "items": {"enum": sorted(keywords)}},
        "abilities": {"type": "array", "items": ref("ability")}, "spell": ref("ops"),
        "evolve_from": {"type": "object", "properties": {k: {} for k in sorted(FILTER_KEYS | {"zone"})}, "additionalProperties": False}, "free_if": ref("cond"),
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "DMPJ card definition",
        "type": "object",
        "properties": {"id": {"type": "string"}, "mana": {"type": "integer"}, "text": {"type": "string"},
                       "source": {"type": "object"},
                       "faces": {"type": "array", "items": ref("face"), "minItems": 2, "maxItems": 2},
                       **face_props},
        "required": ["id"],
        "$defs": {
            "face": {"type": "object", "properties": face_props, "required": ["name", "types", "civs", "cost"],
                     "additionalProperties": False},
            "ops": {"type": "array", "items": {"anyOf": op_schemas}},
            "filter": {"type": "object", "properties": {k: {} for k in sorted(FILTER_KEYS)},
                       "additionalProperties": False},
            "selector": {"type": "object", "properties": {
                "zone": {"anyOf": [{"enum": sorted(zones) + ["any"]}, {"type": "array", "items": {"enum": sorted(zones)}}]},
                "exlife_of": {"type": "string"}, "under_of": {}, "owner": {"enum": ["you", "opp", "any"]}, "owner_of": {"type": "string"},
                "filter": ref("filter"),
                "count": {"anyOf": [ref("expr"), {"const": "all"}]}, "up_to": {"type": "boolean"},
                "from_top": ref("expr"), "chooser": {"enum": ["you", "opp"]}, "ref": {"type": "string"},
                "other": {"type": "boolean"}, "look": {"type": "boolean"}}, "additionalProperties": False},
            "expr": {"anyOf": [{"type": "integer"}, {"type": "object", "properties": {
                "count": ref("selector"), "var": {"type": "string"}, "cost_of": {"type": "string"}, "races_of": {"type": "string"}, "race": {"type": "string"}, "sum": {"type": "array", "items": ref("expr")}},
                "minProperties": 1, "maxProperties": 1, "additionalProperties": False}]},
            "cond": {"type": "object", "minProperties": 1, "maxProperties": 1, "properties": {
                "exists": ref("selector"), "cmp": {"type": "array", "minItems": 3, "maxItems": 3},
                "not": ref("cond"), "all": {"type": "array", "items": ref("cond")},
                "any": {"type": "array", "items": ref("cond")}, "is_turn": {"enum": ["you", "opp"]},
                "marked": {"type": "string"}},
                "additionalProperties": False},
            "mod": {"type": "object", "properties": {
                "power": {"type": "integer"}, "grant": {"type": "array", "items": {"enum": sorted(keywords)}},
                "allow": {"type": "array", "items": perm}, "deny": {"type": "array", "items": perm},
                "breaks": {"type": "integer"}, "breaks_per_power": {"type": "integer"},
                "cost": {"anyOf": [{"type": "integer"}, {"type": "object", "properties": {"amount": {"type": "integer"}, "count": ref("selector")}, "required": ["amount"], "additionalProperties": False}]},
                "cost_min": {"type": "integer"},
                "battle_power": {"type": "object", "properties": {"amount": {"type": "integer"}, "count": ref("selector"), "only": {"enum": ["attacking"]}}, "required": ["amount"], "additionalProperties": False},
                "sac_reduce": {"type": "integer"}, "opt_reduce": {"type": "object", "required": ["amount"]},
                "ignore": {"type": "array", "items": {"enum": ["trigger", "static", "replace", "all"]}},
                "gain": {"type": "array", "items": ref("ability")}},
                "additionalProperties": False, "propertyNames": {"enum": sorted(MOD_KEYS)}},
            "when": {"type": "object", "properties": {
                "event": {"enum": sorted(EVENTS)}, "from": {"enum": sorted(zones)}, "to": {"enum": sorted(zones)},
                "reason": {"enum": sorted(REASONS)}, "player": {"enum": ["you", "opp"]}, "unpaid": {"type": "boolean"}, "target": {"enum": ["player", "creature"]},
                "via": {"enum": sorted(VIAS)}, "subject": {}},
                "required": ["event"], "additionalProperties": False},
            "ability": {"type": "object", "properties": {
                "kind": {"enum": ["trigger", "replace", "static", "declare"]}, "when": ref("when"),
                "if": ref("cond"), "effect": ref("ops"), "instead": ref("ops"), "optional": {"type": "boolean"},
                "affects": {}, "mod": ref("mod"), "zone": {"enum": sorted(zones)}},
                "required": ["kind"], "additionalProperties": False},
        },
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=1))
