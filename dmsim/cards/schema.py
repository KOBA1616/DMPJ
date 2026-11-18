"""カードDSLの JSON Schema を registry と data/rules から生成する。

LLM にカードテキストを変換させる時のスキーマとして渡し、出力の一次チェックにも使う
（最終的な検査は defs.parse_card。こちらは op の引数の型と語彙の一覧を機械可読にしたもの）。

    python -m dmsim.schema > data/schema/card.schema.json   （新名 python -m dmsim.cards.schema でも同じ）
"""
from __future__ import annotations

import json

from .defs import ABILITY_KEYS, CARD_TYPES, CIVS, DURATIONS_FIXED, EVENTS, FILTER_KEYS, LOSE_REASONS, MOD_KEYS, POSITIONS, REASONS, TURN_COUNT_KINDS, VIAS, \
    core_ops, load_tables


VAR_REF = {"type": "object", "properties": {"var": {"type": "string"}},
           "required": ["var"], "additionalProperties": False}   # プレイヤー指定の変数参照 {var: 名前}（第192弾）


def _build() -> dict:
    zones, keywords, macros, actions, steps = load_tables()
    ops = core_ops()
    ref = lambda n: {"$ref": f"#/$defs/{n}"}  # noqa: E731
    arg = {
        "selector": ref("selector"), "zone": {"enum": sorted(zones)}, "reason": {"enum": sorted(REASONS)},
        "expr": ref("expr"), "cond": ref("cond"), "ops": ref("ops"), "oplists": {"type": "array", "minItems": 2, "items": ref("ops")}, "player": {"anyOf": [{"enum": ["you", "opp"]}, VAR_REF]},
        "players": {"anyOf": [{"enum": ["you", "opp", "each"]}, VAR_REF]}, "mod": ref("mod"), "duration": {"enum": sorted(DURATIONS_FIXED)}, "position": {"enum": sorted(POSITIONS)},
        "step": {"enum": steps}, "str": {"type": "string"}, "int": {"type": "integer"},
        "bool": {"type": "boolean"}, "any": {}, "ability": ref("ability"), "filter": ref("filter"),
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
                      {"type": "object", "properties": {"action": {"enum": sorted(actions)}, "other": ref("filter"), "once": {"type": "boolean"},
                                                       "max_per_turn": {"type": "integer", "minimum": 1},
                                                       "count": {"enum": sorted(TURN_COUNT_KINDS)}},
                       "required": ["action"], "additionalProperties": False}]}
    face_props = {
        "name": {"type": "string"}, "types": {"type": "array", "items": {"enum": sorted(CARD_TYPES)}},
        "civs": {"type": "array", "items": {"enum": sorted(CIVS)}}, "cost": {"type": "integer"},
        "power": {"type": "integer"}, "races": {"type": "array", "items": {"type": "string"}},
        "keywords": {"type": "array", "items": {"enum": sorted(keywords)}},
        "abilities": {"type": "array", "items": ref("ability")}, "spell": ref("ops"),
        "evolve_from": {"anyOf": [{"type": "object", "properties": {k: {} for k in sorted(FILTER_KEYS | {"zone"})}, "additionalProperties": False}, {"type": "array", "items": {"type": "object"}}]}, "free_if": ref("cond"),
        "evolve_civs": {"type": "array", "items": {"enum": sorted(CIVS)}}, "evolve_zones": {"type": "array", "items": {"type": "string"}}, "soul_shift": {"type": "object", "properties": {"floor": {"type": "integer", "minimum": 0}}, "required": ["floor"], "additionalProperties": False},
        "galaxy_shield": {"type": "object", "properties": {"cost": {"type": "integer"}, "civs": {"type": "array", "items": {"enum": sorted(CIVS)}}}, "required": ["cost", "civs"], "additionalProperties": False}, "neo": {"type": "boolean"}, "grave_evo": {"type": "boolean"}, "star": {"type": "boolean"}, "s_max": {"type": "boolean"}, "ace": {"type": "boolean"}, "hyper": {"type": "boolean"}, "crystal_soul": {"type": "integer", "minimum": 1}, "mana_boost": {"type": "object", "properties": {"filter": ref("filter"), "value": {"type": "integer", "minimum": 2}, "optional": {"type": "boolean"}}, "additionalProperties": False}, "mana_bakutan": {"type": "integer", "minimum": 0}, "link_to": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "pos": {"enum": ["right", "left", "up", "down"]}}, "required": ["name", "pos"], "additionalProperties": False}},
    }
    for k in ("text", "mana", "evolve_count", "evolve_zone", "evolve_any", "cost_reduce_per_evo", "resolve_to", "resolve_face_down", "alt_cost", "s_back", "bazurenda",
              "fushigi", "vividraw", "mugen_climb", "o_drive", "odrive_spell", "sst_spell", "stp_spell", "recycle", "grave_cast", "deck_evolution"):   # defs.parse_card が読む面の項目
        face_props.setdefault(k, {})
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
                "exlife_of": {"type": "string"}, "castle_of": {"type": "string"}, "under_of": {}, "bundle_of": {}, "owner": {"anyOf": [{"enum": ["you", "opp", "any"]}, VAR_REF]}, "owner_of": {"type": "string"},
                "crossed_to": {}, "host_of": {},
                "filter": ref("filter"),
                "count": {"anyOf": [ref("expr"), {"type": "object", "properties": {"upto": ref("expr")}, "additionalProperties": False}, {"const": "all"}, {"const": "any"}, {"const": "rest"}]}, "up_to": {"type": "boolean"},
                "from_top": ref("expr"), "chooser": {"anyOf": [{"enum": ["you", "opp", "opponent", "random"]}, VAR_REF]}, "ref": {"type": "string"},
                "total_cost_le": ref("expr"), "total_cost_ge": ref("expr"),
                "total_power_le": ref("expr"), "total_power_ge": ref("expr"),
                "distinct_costs": {"type": "boolean"}, "distinct_from": ref("selector"),
                "extremal": {"enum": ["min_power", "max_power"]},
                "exclude": {"anyOf": [ref("selector"), {"type": "array", "items": ref("selector")}]},
                "other": {"type": "boolean"}, "look": {"type": "boolean"}}, "additionalProperties": False},
            "expr": {"anyOf": [{"type": "integer"}, {"type": "object", "properties": {
                "count": ref("selector"), "civ_count": ref("selector"), "distinct_cost_count": ref("selector"), "distinct_type_count": ref("selector"), "total_cost": ref("selector"), "total_power": ref("selector"), "max_power": ref("selector"), "entered": {"type": "object", "properties": {"owner": {"type": "string"}, "other": {"type": "boolean"}}, "additionalProperties": False}, "bundles": {"type": "object", "properties": {"owner": {"type": "string"}, "face_up": {"type": "boolean"}}, "additionalProperties": False}, "var": {"type": "string"}, "cost_of": {"anyOf": [{"type": "string"}, {"type": "object", "properties": {"ref": {"type": "string"}}, "additionalProperties": False}]}, "power_of": {"anyOf": [{"type": "string"}, {"type": "object", "properties": {"ref": {"type": "string"}}, "additionalProperties": False}]}, "name_of": {"type": "string"}, "races_of": {"type": "string"}, "race": {"type": "string"}, "link_count": {"type": "string"}, "sum": {"type": "array", "items": ref("expr")}, "mul": {"type": "array", "items": ref("expr")}, "seals": {"type": "object", "properties": {"owner": {"type": "string"}}, "additionalProperties": False}, "seals_on": {},
                "turn_count": {"type": "object", "properties": {"kind": {"type": "string"}, "owner": {"type": "string"}, "other": {"type": "boolean"}, "filter": ref("filter"), "ref": {"type": "string"}}, "required": ["kind"], "additionalProperties": False}, "used_count": {"type": "object", "properties": {"owner": {"type": "string"}, "filter": ref("filter")}, "additionalProperties": False}, "prev_shield_added": {"type": "object", "properties": {"owner": {"type": "string"}}, "additionalProperties": False}, "declared": {"type": "string"}, "crossed_count": {"anyOf": [{"type": "string"}, {"type": "object", "properties": {"ref": {"type": "string"}}, "additionalProperties": False}]}},
                "minProperties": 1, "maxProperties": 1, "additionalProperties": False}]},
            "cond": {"type": "object", "minProperties": 1, "maxProperties": 1, "properties": {
                "exists": ref("selector"), "cmp": {"type": "array", "minItems": 3, "maxItems": 3},
                "not": ref("cond"), "all": {"type": "array", "items": ref("cond")},
                "any": {"type": "array", "items": ref("cond")}, "is_turn": {"enum": ["you", "opp"]},
                "marked": {"anyOf": [{"type": "string"}, {"type": "object", "properties": {"name": {"type": "string"}, "scope": {"enum": ["turn", "attack", "game"]}}, "required": ["name"], "additionalProperties": False}]}, "self_marked": {"type": "string"}, "face_up": {"type": "boolean"}, "vivid_paid": {}, "alt_paid": {}, "ddd_paid": {}, "hyper": {"type": "boolean"}, "power_ge": {"type": "integer"}},
                "additionalProperties": False},
            "mod": {"type": "object", "properties": {
                "power": {"anyOf": [{"type": "integer"}, {"type": "object", "properties": {"amount": {"type": "integer"}, "count": {"anyOf": [ref("selector"), ref("expr")]}}, "required": ["amount"], "additionalProperties": False}]}, "grant": {"type": "array", "items": {"enum": sorted(keywords)}},
                "allow": {"type": "array", "items": perm}, "deny": {"type": "array", "items": perm},
                "require": {"type": "array", "items": {"enum": ["attack", "block"]}}, "add_of": {"const": "self"}, "double_power": {"type": "boolean"}, "add_races": {"type": "array", "items": {"anyOf": [{"type": "string"}, {"type": "object"}]}}, "add_names": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "breaks": {"type": "integer"}, "breaks_add": {"anyOf": [{"type": "integer"}, {"type": "object", "properties": {"amount": {"type": "integer"}, "count": {"anyOf": [ref("selector"), ref("expr")]}}, "required": ["amount"], "additionalProperties": False}]}, "breaks_per_power": {"type": "integer"},
                "cost": {"anyOf": [{"type": "integer"}, {"type": "object", "properties": {"amount": {"type": "integer"}, "cost_min": {"type": "integer"}, "count": {"anyOf": [ref("selector"), ref("expr")]}}, "required": ["amount"], "additionalProperties": False}]},
                "cost_min": {"type": "integer"}, "crystal_soul": {"type": "integer", "minimum": 1},
                "power_when": {"type": "object", "properties": {"amount": {"type": "integer"}, "count": {"anyOf": [ref("selector"), ref("expr")]}, "when": {"enum": ["attacking", "blocking"]}}, "required": ["amount", "when"], "additionalProperties": False},
                "battle_power": {"type": "object", "properties": {"amount": {"type": "integer"}, "count": {"anyOf": [ref("selector"), ref("expr")]}, "only": {"enum": ["attacking"]}, "opponent_filter": ref("filter")}, "required": ["amount"], "additionalProperties": False},
                "sac_reduce": {"type": "integer"}, "cost_may": {"type": "object", "properties": {"amount": {"type": "integer"}, "once": {"type": "boolean"}, "must": {"type": "boolean"}, "min": {"type": "integer", "minimum": 0}}, "required": ["amount"], "additionalProperties": False}, "opt_reduce": {"type": "object", "properties": {"amount": {"type": "integer"}, "then": {"enum": ["destroy", "deck_bottom_draw"]}, "floor": {"type": "integer", "minimum": 0}, "per": {"type": "boolean"}, "do": {"type": "object", "properties": {"select": ref("selector"), "selects": {"type": "array", "items": {"type": "object", "properties": {"select": ref("selector"), "min": {"type": "integer", "minimum": 0}, "max": {"type": "integer", "minimum": 0}}, "required": ["select"], "additionalProperties": False}}, "move_to": {"type": "string"}, "shuffle": {"type": "boolean"}, "tap": {"type": "boolean"}, "strigger_off": {"type": "boolean"}, "min": {"type": "integer", "minimum": 0}, "max": {"type": "integer", "minimum": 0}}, "additionalProperties": False}}, "required": ["amount"], "additionalProperties": False},
                "ignore": {"type": "array", "items": {"enum": ["trigger", "static", "replace", "all"]}},
                "ignore_ids": {"type": "array", "items": {"type": "string"}},
                "gain": {"type": "array", "items": ref("ability")}},
                "additionalProperties": False, "propertyNames": {"enum": sorted(MOD_KEYS)}},
            "when": {"type": "object", "properties": {
                "event": {"enum": sorted(EVENTS)}, "from": {"anyOf": [{"enum": sorted(zones)}, {"type": "array", "items": {"enum": sorted(zones)}}]}, "to": {"anyOf": [{"enum": sorted(zones)}, {"type": "array", "items": {"enum": sorted(zones)}}]},
                "reason": {"anyOf": [{"enum": sorted(REASONS | LOSE_REASONS)}, {"type": "array", "items": {"enum": sorted(REASONS | LOSE_REASONS)}}]}, "player": {"enum": ["you", "opp"]}, "by": {"enum": ["you", "opp"]}, "cause": {"type": "object", "properties": {"by": {"enum": ["you", "opp"]}, "kind": {"enum": ["spell", "ability"]}}, "additionalProperties": False}, "unpaid": {"type": "boolean"}, "target": {}, "attacker": {}, "opponent": {}, "ord": {"type": "object", "properties": {"kind": {"type": "string"}, "eq": {"type": "integer"}, "ge": {"type": "integer"}, "gt": {"type": "integer"}, "le": {"type": "integer"}, "lt": {"type": "integer"}}, "required": ["kind"], "additionalProperties": False},
                "via": {"enum": sorted(VIAS)}, "subject": {}, "shield": {}, "stacked": {}, "sealed_from": {}, "from_under": {}, "face_up": {}, "broke": {}, "blocked": {}, "vivid": {}, "emblem": {"type": "boolean"}, "turn_draw": {"type": "boolean"}},
                "required": ["event"], "additionalProperties": False},
            "ability": {"type": "object", "properties": {
                "kind": {"enum": ["trigger", "replace", "static", "declare", "activate", "silent", "state", "partner"]}, "when": ref("when"),
                "if": ref("cond"), "effect": ref("ops"), "instead": ref("ops"), "optional": {"type": "boolean"},
                "continue": {"type": "boolean"},
                "once_per_turn": {"type": "boolean"}, "first_time": {"type": "boolean"}, "id": {"type": "string"},
                "affects": {}, "mod": ref("mod"), "cost": {"type": "object", "properties": {"tap": {}, "tap_mana": {}, "under": {}, "untap": {}}, "additionalProperties": False}, "zone": {"enum": sorted(set(zones) | {"hold"})}},
                "required": ["kind"], "additionalProperties": False},
        },
    }


def build() -> dict:
    s = _build()
    props = s["$defs"]["ability"]["properties"]
    for k in sorted(ABILITY_KEYS):   # defs.ABILITY_KEYS が正。型を書いていない項目は何でも受ける
        props.setdefault(k, {})
    mods = s["$defs"]["mod"]["properties"]
    for k in sorted(MOD_KEYS):   # defs.MOD_KEYS が正。型を書いていない項目は何でも受ける
        mods.setdefault(k, {})
    mods["cost_min"] = {"anyOf": [{"type": "integer"}, {"type": "object"}]}
    mods["sac_reduce"] = {"anyOf": [{"type": "integer"}, {"type": "object"}]}
    mods["breaks"] = {"anyOf": [{"type": "integer"}, {"type": "object"}]}
    return s


def main() -> None:
    print(json.dumps(build(), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
