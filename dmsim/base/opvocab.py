"""効果DSLの op 語彙（名前と引数の型）の正本。データ側の知識なので S0 に置く（P1-S1 下ごしらえ）。

defs.py の検証と schema.py の JSON Schema 生成はここを読む（engine を import しない）。
engine/registry.py の @op はここにある名前に実装を登録する側で、型の宣言が食い違えば登録時にエラーになる。
新しい op は、ここに名前と引数の型を足してから engine 側で @op を付けて実装する。
（ここに無い名前を @op で登録した場合は、その場で OP_ARGS に足される。テスト用の拡張口）

引数の型（末尾 ? は省略可）: ARG_TYPES のいずれか。
"""
from __future__ import annotations

ARG_TYPES = {'ability', 'any', 'bool', 'cond', 'duration', 'expr', 'filter', 'int', 'mod', 'oplists', 'ops', 'player', 'players', 'position', 'reason', 'selector', 'step', 'str', 'zone'}

OP_ARGS: dict[str, dict[str, str]] = {
    'uncross': {'select': 'selector'},
    'cross_free': {'gear': 'selector', 'to': 'selector'},
    'move': {'select': 'selector', 'to': 'zone', 'reason': 'reason', 'position': 'position?', 'card_only': 'bool?', 'order': 'str?', 'tapped': 'bool?', 'face_up': 'bool?', 'face_down': 'bool?', 'seal': 'int?', 'stack_on': 'selector?', 'stack_evo': 'bool?', 'evo_source': 'selector?', 'strigger': 'str?', 'as': 'str?', 'no_trigger': 'bool?'},
    'together': {'body': 'ops'},
    'draw': {'player': 'players?', 'count': 'expr?'},
    'tap': {'select': 'selector', 'no_untap_next': 'bool?'},
    'untap': {'select': 'selector'},
    'hyper_release': {'select': 'selector'},
    'flip_down': {'select': 'selector'},
    'flip_up': {'select': 'selector'},
    'dswitch': {},
    'may': {'body': 'ops', 'label': 'str?', 'player': 'str?', 'else': 'ops?'},
    'modal': {'modes': 'oplists', 'count': 'int?', 'repeat': 'bool?'},
    'if': {'cond': 'cond', 'then': 'ops?', 'else': 'ops?'},
    'repeat': {'times': 'expr?', 'body': 'ops', 'over': 'str?', 'as': 'str?'},
    'break': {'player': 'player?', 'count': 'expr?', 'st_first': 'bool?'},
    'modify': {'select': 'selector', 'mod': 'mod', 'duration': 'duration?', 'dynamic': 'bool?'},
    'mark': {'name': 'str', 'of_self': 'bool?', 'scope': 'str?'},
    'rush': {'select': 'selector'},
    'use_entry_abilities': {'select': 'selector', 'count': 'int?'},
    'use_triggered_ability': {},
    'cancel_attack': {},
    'shuffle': {'player': 'player?', 'player_from': 'str?'},
    'win': {'player': 'player?'},
    'lose': {'player': 'player?'},
    'pay_or_lose': {'cost': 'int', 'civs': 'any?'},
    'untap_limit': {'player': 'player?', 'zone': 'str', 'count': 'int'},
    'action_limit': {'player': 'player?', 'attack': 'int?', 'block': 'int?', 'until': 'str'},
    'no_lose': {'player': 'players?', 'duration': 'duration?', 'once': 'bool?', 'deck_out_only': 'bool?'},
    'set_var': {'name': 'str', 'value': 'any?'},
    'extra_turn': {'player': 'player?'},
    'step_mod': {'player': 'player', 'step': 'step', 'mode': 'str', 'turns': 'int?'},
    'delayed_trigger': {'when': 'any', 'effect': 'ops', 'duration': 'duration?', 'once': 'bool?'},
    'play_free': {'select': 'selector', 'resolve_to': 'zone?', 'resolve_position': 'position?', 'face': 'str?', 'as': 'str?', 'player': 'player?'},
    'mekurade': {'filter': 'filter?', 'cost_le': 'int?', 'look': 'int?'},
    'janken': {'win': 'ops?', 'lose': 'ops?'},
    'move_under_to_event': {},
    'move_to_event': {'select': 'selector'},
    'shield_plus': {'each': 'bool?', 'count': 'int?'},
    'sforce_link': {},
    'castle_link': {},
    'opp_may': {'body': 'ops', 'label': 'str?'},
    'yobinion': {},
    'reveal_until': {'player': 'player?', 'player_from': 'str?', 'filter': 'filter', 'count': 'expr?', 'limit': 'expr?', 'as': 'str', 'rest_as': 'str?'},
    'gacha': {'kind': 'str', 'times': 'expr?'},
    'gachinko': {'times': 'expr?', 'until_lose': 'bool?', 'stoppable': 'bool?', 'by': 'str?', 'mine_as': 'str?', 'as': 'str?'},
    'cast_face': {'face': 'expr?', 'select': 'selector?'},
    'summon_self': {},
    'play_self': {'cost': 'int', 'civs': 'any?', 'via': 'any?'},
    'swap': {'out': 'selector', 'out_to': 'zone?', 'in': 'selector'},
    'invade': {'onto': 'selector'},
    'summon_on': {'parts': 'any', 'tapped': 'bool?'},
    'attach_seal': {'select': 'selector', 'count': 'int?'},
    'remove_seal': {'select': 'selector', 'count': 'int?'},
    'end_turn': {},
    'use_partner': {'of': 'str?', 'exclude_self': 'bool?', 'pending': 'bool?', 'any_number': 'bool?'},
    'use_cip': {'select': 'selector', 'optional': 'bool?'},
    'choose_player': {'as': 'str'},
    'choose': {'select': 'selector', 'reveal': 'bool?', 'as': 'str'},
    'strigger': {'select': 'selector', 'mode': 'str'},
    'choose_race': {'as': 'str'},
    'choose_number': {'min': 'int?', 'max': 'int?', 'as': 'str'},
    'choose_name': {'as': 'str'},
    'choose_civ': {'as': 'str'},
    'put_under': {'select': 'selector', 'onto': 'selector'},
    'battle_substitute': {'tap': 'bool?'},
    'force_battle': {'a': 'selector', 'b': 'selector?'},
}


def declare(name: str, args: dict[str, str]) -> None:
    """op の名前と引数の型を確かめて語彙に載せる。既にあれば宣言が一致するかだけ見る。"""
    for k, v in args.items():
        if v.rstrip("?") not in ARG_TYPES:
            raise ValueError(f"op '{name}': unknown arg type '{v}' for '{k}'")
    if name in OP_ARGS:
        if args and dict(args) != OP_ARGS[name]:
            raise ValueError(f"op '{name}': 引数の型が語彙 base/opvocab.py と食い違う: {dict(args)} != {OP_ARGS[name]}")
        return
    OP_ARGS[name] = dict(args)
