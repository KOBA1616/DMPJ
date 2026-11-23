"""語彙パイロット第334弾: play_from_deck_top（pure 2件）。

対象:
- dm22rp2x-002 アカシック・ヴィジョン（タマシード）: 「自分の
  ターン中、自分の山札の上から１枚目をいつでも見てもよい。
  自分のターン中、呪文またはタマシードを自分の山札の上から
  使ってもよい」
- dm26sd1-j009 斬龍電融 オロチリュウセイ: 「自分のターン中、
  クリーチャーを１体、自分の山札の上から召喚してもよい。
  （コストは支払う）」（＋スピードアタッカー付与は partial で
  表現済み）
- dmrp22-005 は multi（reveal_stay＋play_from_deck_top）のため
  本弾の対象外。reveal_stay が解けてから扱う。

結論はエンジン拡張（山札の上からのプレイ）: _play_options は
手札・マナ・墓地からの選択肢しか出さなかった。本弾で
- permissions.yaml に summon/cast/generate_from_deck_top を追加
  （default: false。第226弾の墓地版と同じ許可型）。
- turn.py _play_options に山札の一番上だけを見るブロックを追加
  （_deck_top_grant で許可を確認し、_can_play_face で支払いを
  確認して play:{id}:dtop を出す。once 付きは once_src を渡す）。
- h_play は from_zone を汎用に読むため、山札からの召喚・唱え・
  生成に変更は要らない。summon_once の消費条件に "deck" を
  加えただけ（cast/generate の once は消費する側の印が無いため
  今回は使わない）。
- static の形は {kind: static, affects: {zone: deck, owner: you,
  filter: {types: [...] }}, if: {is_turn: you}, mod: {allow: [...]}}。
  allow は山札全体に付くが、選択肢に出るのは一番上だけなので
  from_top の指定は要らない。

「いつでも見てもよい」は既存12枚と同じく原文のみ（エンジンに
山札の可視性の語彙は無い）。「クリーチャーを１体」は
once: true で読む（ターン1回）。

proto:
- T1013: dm22rp2x-002 型（水タマシード）。
- T1014: dm26sd1-j009 型（水/火/自然クリーチャー）。

ドライバは tests.conftest を import せず scenario.build を直接
使う（第329弾以降の作法）。山札の上は zlist("deck", p)[0]。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

ALLOW_002 = {
    "kind": "static",
    "affects": {"zone": "deck", "owner": "you",
                "filter": {"types": ["spell", "tamaseed"]}},
    "if": {"is_turn": "you"},
    "mod": {"allow": [{"action": "cast_from_deck_top"},
                      {"action": "generate_from_deck_top"}]}}

SPEED_ALL = {
    "kind": "static",
    "affects": {"owner": "you", "filter": {"types": ["creature"]}},
    "mod": {"grant": ["speed_attacker"]}}

ALLOW_J009 = {
    "kind": "static",
    "affects": {"zone": "deck", "owner": "you",
                "filter": {"types": ["creature"]}},
    "if": {"is_turn": "you"},
    "mod": {"allow": [{"action": "summon_from_deck_top", "once": True}]}}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _set_deck_top(e, p, defn):
    """山札の指定カードを一番上（zlist の先頭）へ置く。"""
    deck = e.s.zones["deck"][p]
    cid = next(c for c in deck if e.s.cards[c].defn == defn)
    deck.remove(cid)
    deck.insert(0, cid)
    return cid


def _play_options(e, p):
    return [o["key"] for o in e._play_options(p)]


def _drive_to(e, kind, player):
    for _ in range(400):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] == kind and d.get("player") == player:
            return d
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError(f"did not reach {kind} p{player}")


def test_proto_forms():
    c = proto_card("T1013")
    assert c["abilities"] == [ALLOW_002]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = proto_card("T1014")
    assert c["abilities"] == [SPEED_ALL, ALLOW_J009]
    assert c["keywords"] == ["ex_life", "triple_breaker"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 2


def test_bad_allow_action_rejected():
    base = proto_card("T1013")
    for bad in ("summon_from_deck", "cast_from_deck_top_x"):
        b = dict(base)
        b["abilities"] = [dict(ALLOW_002, mod={"allow": [{"action": bad}]})]
        with pytest.raises(DefError):
            parse_card(b, TABLES)
    b = dict(base)
    b["abilities"] = [dict(ALLOW_002, mod={"allow": [{"action": "cast_from_deck_top", "once": "yes"}]})]
    with pytest.raises(DefError):
        parse_card(b, TABLES)


def test_vision_casts_top_spell(rules):
    e = _build(rules, {"bz": ["T1013"], "mana": ["T009"] * 2, "deck": ["T003"]}, {})
    _set_deck_top(e, 0, "T003")
    opts = _play_options(e, 0)
    assert "play:T003:dtop" in opts
    # メインステップで唱える
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and "play:T003:dtop" in keys:
            e.answer([keys.index("play:T003:dtop")])
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    else:
        raise AssertionError("did not reach main")
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] in ("charge", "main", "attack"):
            break
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert _in_zone(e, 0, "graveyard", "T003")
    assert not _in_zone(e, 0, "deck", "T003")


def test_vision_generates_top_tamaseed(rules):
    e = _build(rules, {"bz": ["T1013"], "deck": ["T1009"],
                       "mana": ["T004", "T004", "T053"]}, {})
    _set_deck_top(e, 0, "T1009")
    opts = _play_options(e, 0)
    assert "play:T1009:dtop" in opts
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and "play:T1009:dtop" in keys:
            e.answer([keys.index("play:T1009:dtop")])
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    else:
        raise AssertionError("did not reach main")
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] in ("charge", "main", "attack"):
            break
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert _in_zone(e, 0, "bz", "T1009")


def test_vision_unlimited_and_top_only(rules):
    # 2枚目も同じターンに使える（once 無し）。一番上以外は出ない
    e = _build(rules, {"bz": ["T1013"], "deck": ["T024", "T1009"],
                       "mana": ["T009", "T004", "T004", "T053"]},
               {"bz": ["T004"]})
    _set_deck_top(e, 0, "T024")
    deck = e.s.zones["deck"][0]
    second = next(c for c in deck if e.s.cards[c].defn == "T1009")
    deck.remove(second)
    deck.insert(1, second)
    opts = _play_options(e, 0)
    assert "play:T024:dtop" in opts
    assert "play:T1009:dtop" not in opts    # まだ一番上ではない
    # T024 を唱えた後、T1009 が一番上になり、同じターンに出せる
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and "play:T024:dtop" in keys:
            e.answer([keys.index("play:T024:dtop")])
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    else:
        raise AssertionError("did not reach main")
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] in ("charge", "main", "attack"):
            break
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert "play:T1009:dtop" in _play_options(e, 0)


def test_no_vision_no_dtop(rules):
    e = _build(rules, {"mana": ["T009"] * 2, "deck": ["T003"]}, {})
    _set_deck_top(e, 0, "T003")
    assert "play:T003:dtop" not in _play_options(e, 0)


def test_orochi_summons_top_creature_once(rules):
    e = _build(rules, {"bz": ["T1014"], "mana": ["T001"] * 4, "deck": ["T001", "T001"]}, {})
    _set_deck_top(e, 0, "T001")
    deck = e.s.zones["deck"][0]
    second = next(c for c in deck if e.s.cards[c].defn == "T001")
    deck.remove(second)
    deck.insert(1, second)
    assert "play:T001:dtop" in _play_options(e, 0)
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and "play:T001:dtop" in keys:
            e.answer([keys.index("play:T001:dtop")])
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    else:
        raise AssertionError("did not reach main")
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] in ("charge", "main", "attack"):
            break
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert _in_zone(e, 0, "bz", "T001")
    # 1体まで: 次の T001 は同じターンに出せない
    assert "play:T001:dtop" not in _play_options(e, 0)
    # 次の自分のターンにはまた出せる（2枚目の T001 はターン開始の
    # ドローで手札に来るため、新しい一番上は T002 になる）
    _drive_to(e, "charge", 0)
    assert "play:T002:dtop" in _play_options(e, 0)


def test_orochi_ignores_top_spell(rules):
    e = _build(rules, {"bz": ["T1014"], "mana": ["T009"] * 2, "deck": ["T003"]}, {})
    _set_deck_top(e, 0, "T003")
    assert "play:T003:dtop" not in _play_options(e, 0)
