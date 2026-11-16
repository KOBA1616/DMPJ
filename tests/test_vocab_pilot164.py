"""語彙パイロット第164弾: chosen_protection_scoped（範囲つきの「選ばれない」）。

「選ばれない」は従来 mod の deny: [be_chosen]（無範囲）。範囲つきは deny の
辞書形 {action: be_chosen, other: <発生源フィルタ>} で表す（第126弾の other
フィルタ基盤。式値は保護される側を self として評価される）。第164弾の変更は
select() が選択の発生源（解決中のカード = env の self）を permits の other に
渡すことだけ:

- 呪文からだけ: other: {types: [spell]}
- コスト4以下の呪文から: other: {types: [spell], cost_le: 4}
- 多色ではないクリーチャーの能力または呪文から: other: {any_of: [{types: [creature]},
  {types: [spell]}], multicolor: false}
- 自分以下のコストのカードから: other: {cost_le: {cost_of: {ref: self}}}
付与（modify の mod）や集団への常在型（affects）でも同じ辞書形が使える。
"""
from pathlib import Path

import yaml
from conftest import setup, answer

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in ("T302", "T303", "T304", "T305", "T306", "T307"):
        parse_card(_proto_card(cid), TABLES)
    t302 = parse_card(_proto_card("T302"), TABLES)
    assert t302.abilities[0]["mod"]["deny"] == [{"action": "be_chosen", "other": {"types": ["spell"]}}]


def test_invalid_scoped_deny():
    base = {"id": "test-cp-bad", "name": "試験範囲不良", "types": ["creature"],
            "civs": ["light"], "cost": 3, "power": 2000,
            "source": {"official": "test-cp-bad", "review": "pending"}}
    for bad_mod in ({"deny": [{"action": "be_chosen", "other": {"types": ["spell"], "bogus_key": 1}}]},
                    {"deny": [{"action": "no_such_action", "other": {"types": ["spell"]}}]}):
        card = {**base, "abilities": [{"kind": "static", "affects": "self", "mod": bad_mod}]}
        try:
            parse_card(card, TABLES)
            raise AssertionError(f"should have raised: {bad_mod}")
        except DefError:
            pass


def _cid(e, player, defn, nth=0):
    return [c for c in e.zlist("bz", player)
            if e.s.cards[c].defn == defn and e.s.cards[c].controller == player][nth]


def _zone(e, cid):
    return e.s.cards[cid].zone


def _advance_default(e, d):
    keys = [o["key"] for o in d["options"]]
    if "pass" in keys:
        e.answer([keys.index("pass")])
    elif d["kind"] == "block" and "no_block" in keys:
        e.answer([keys.index("no_block")])
    else:
        e.answer(list(range(d["min"])))


def _play_and_capture_choice(e, defn, done):
    """唱えて／出して、解決が終わる（done()）までの最初の choose_cards 決定の
    選択肢 cid 集合を返す（選択肢が自動で決まった場合は None）。"""
    answer(e, "charge", "pass")
    answer(e, "main", f"play:{defn}")
    for _ in range(80):
        if done():
            return None
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if d["kind"] == "choose_cards":
            cids = {o["cid"] for o in d["options"] if "cid" in o}
            e.answer([0])
            return cids
        _advance_default(e, d)
    return None


def _settle_until(e, cond, max_steps=300):
    for _ in range(max_steps):
        if cond():
            return
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        _advance_default(e, d)
    raise AssertionError("condition not reached")


MANA_W3 = ["T063", "T001", "T001"]
MANA_7_MULTI = ["T005", "T063", "T001", "T001", "T001", "T001", "T001"]


def test_spell_scope_blocks_spell(rules):
    """T302（呪文からだけ選ばれない）は、呪文 T300 の選択肢に入らない
    （候補が T001 だけになるので選択は自動で決まり、T302 は残る）。"""
    e = setup(rules, {"hand": ["T300"], "mana": MANA_W3}, {"bz": ["T302", "T001"]})
    t302, t001 = _cid(e, 1, "T302"), _cid(e, 1, "T001")
    offered = _play_and_capture_choice(e, "T300", lambda: _zone(e, t001) == "graveyard")
    assert offered is None or (t001 in offered and t302 not in offered)
    _settle_until(e, lambda: _zone(e, t001) == "graveyard")
    assert _zone(e, t302) == "bz"


def test_spell_scope_allows_creature_source(rules):
    """T302 はクリーチャーの能力（T295 の出た時）からは選べる（破壊される）。"""
    e = setup(rules, {"hand": ["T295"], "mana": ["T005", "T001", "T001", "T001"]}, {"bz": ["T302"]})
    t302 = _cid(e, 1, "T302")
    answer(e, "charge", "pass")
    answer(e, "main", "play:T295")
    _settle_until(e, lambda: _zone(e, t302) == "graveyard")


def test_cost_scoped_spell(rules):
    """T303（コスト4以下の呪文から選ばれない）: コスト3の呪文では選べず、コスト7の呪文では選べる。"""
    e = setup(rules, {"hand": ["T300"], "mana": MANA_W3}, {"bz": ["T303", "T001"]})
    t303, t001 = _cid(e, 1, "T303"), _cid(e, 1, "T001")
    offered = _play_and_capture_choice(e, "T300", lambda: _zone(e, t001) == "graveyard")
    assert offered is None or (t001 in offered and t303 not in offered)
    _settle_until(e, lambda: _zone(e, t001) == "graveyard")
    assert _zone(e, t303) == "bz"

    e = setup(rules, {"hand": ["T307"], "mana": MANA_7_MULTI}, {"bz": ["T303"]})
    t303 = _cid(e, 1, "T303")
    answer(e, "charge", "pass")
    answer(e, "main", "play:T307")
    _settle_until(e, lambda: _zone(e, t303) == "graveyard")


def test_nonmulticolor_scope(rules):
    """T304（多色ではないクリーチャーの能力または呪文で選べない）:
    単色の呪文・単色のクリーチャーからは選べず、多色の呪文からは選べる。"""
    e = setup(rules, {"hand": ["T300"], "mana": MANA_W3}, {"bz": ["T304", "T001"]})
    t304, t001 = _cid(e, 1, "T304"), _cid(e, 1, "T001")
    offered = _play_and_capture_choice(e, "T300", lambda: _zone(e, t001) == "graveyard")
    assert offered is None or (t001 in offered and t304 not in offered)
    _settle_until(e, lambda: _zone(e, t001) == "graveyard")
    assert _zone(e, t304) == "bz"

    e = setup(rules, {"hand": ["T295"], "mana": ["T005", "T001", "T001", "T001"]}, {"bz": ["T304"]})
    t304 = _cid(e, 1, "T304")
    answer(e, "charge", "pass")
    answer(e, "main", "play:T295")
    _settle_until(e, lambda: any(e.s.cards[c].defn == "T295" for c in e.zlist("bz", 0)))
    assert _zone(e, t304) == "bz"   # 候補から外れて破壊が不発

    e = setup(rules, {"hand": ["T307"], "mana": MANA_7_MULTI}, {"bz": ["T304"]})
    t304 = _cid(e, 1, "T304")
    answer(e, "charge", "pass")
    answer(e, "main", "play:T307")
    _settle_until(e, lambda: _zone(e, t304) == "graveyard")


def test_relative_cost_scope(rules):
    """T305（コスト5。自分以下のコストのカードによって選ばれない）:
    コスト3の呪文では選べず、コスト7の呪文では選べる。"""
    e = setup(rules, {"hand": ["T300"], "mana": MANA_W3}, {"bz": ["T305", "T001"]})
    t305, t001 = _cid(e, 1, "T305"), _cid(e, 1, "T001")
    offered = _play_and_capture_choice(e, "T300", lambda: _zone(e, t001) == "graveyard")
    assert offered is None or (t001 in offered and t305 not in offered)
    _settle_until(e, lambda: _zone(e, t001) == "graveyard")
    assert _zone(e, t305) == "bz"

    e = setup(rules, {"hand": ["T307"], "mana": MANA_7_MULTI}, {"bz": ["T305"]})
    t305 = _cid(e, 1, "T305")
    answer(e, "charge", "pass")
    answer(e, "main", "play:T307")
    _settle_until(e, lambda: _zone(e, t305) == "graveyard")


def test_group_scope_from_opponent_spell(rules):
    """T306 の常在型: 自分のテスト・クリーチャーは相手の呪文で選ばれない（相手ターンに検証）。"""
    e = setup(rules, {"bz": ["T306", "T001"]},
              {"hand": ["T300"], "mana": MANA_W3})
    mine = {_cid(e, 0, "T306"), _cid(e, 0, "T001")}
    played = False
    captured = None
    for _ in range(400):
        if any(e.s.cards[c].defn == "T300" for c in e.zlist("graveyard", 1)):
            break
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_cards":
            captured = {o["cid"] for o in d["options"] if "cid" in o}
            e.answer([0])
        elif d["player"] == 1 and d["kind"] == "main" and not played and "play:T300" in keys:
            e.answer([keys.index("play:T300")])
            played = True
        else:
            _advance_default(e, d)
    assert played
    assert captured is None or not (captured & mine)   # 自分のクリーチャーは選択肢に入らない
    assert all(_zone(e, c) == "bz" for c in mine)
