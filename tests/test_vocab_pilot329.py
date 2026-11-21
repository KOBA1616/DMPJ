"""語彙パイロット第329弾 shield_placement_trigger の検証。

対象は pure 2件:
- dm26ex4-cho047 DARK MEMORY CONTAINER（ブロッカー／CIP で2枚引く
  ／カードが自分のシールドゾーンに置かれた時、このクリーチャーを
  自分の墓地から出してもよい）
- dm26rp1-tr002 楯教の求道者 ザゼ・ゼーン（ブロッカー／W・ブレイ
  カー／タップして出て、自分のターンのはじめにアンタップしない
  ／カードが自分のシールドゾーンに置かれた時、このクリーチャーを
  アンタップし、その後1回選ぶ: 1枚引く／相手のクリーチャーを1体
  タップし次の相手のターンのはじめにアンタップしない／次の自分の
  ターンのはじめまで、このクリーチャーは離れない）

結論はドリフト（追加語彙なし）。シールド配置の誘発は
{event: move, to: shield, subject: {owner: you}} の確立形
（dm24ex3-004 等44件。dm24ex3-004 は同文の「置かれた時」条項を
持つ）。墓地で機能する誘発は zone: graveyard（217件）。墓地から
の自己登場は may＋play_free {ref: self}。「タップして出る」は
キーワード enters_tapped、「自分のターンのはじめにアンタップ
しない」は static {deny: [untap_at_start]}（dmrp18-025）。
タップ＋アンタップしないは tap op の no_untap_next（dmr11-038）。
「離れない」は mod {no_leave: true}（第143弾）を
duration: until_next_own_turn_start で。

proto T998 = cho047 型、T999 = tr002 型、T1000 = 駆動用の
シールド追加呪文（move to: shield reason: charge、dm22ex2-068）。
"""
import os

os.environ.setdefault("DMSIM_SKIP_CONVERTED", "1")

from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402
from tests.conftest import setup  # noqa: E402

TABLES = load_tables()

CIP = {"kind": "trigger", "when": {"event": "move", "to": "bz",
                                   "subject": "self"},
       "effect": [{"op": "draw", "count": 2}]}

GY_TRIGGER = {"kind": "trigger", "zone": "graveyard",
              "when": {"event": "move", "to": "shield",
                       "subject": {"owner": "you"}},
              "effect": [{"op": "may",
                          "body": [{"op": "play_free",
                                    "select": {"ref": "self"}}]}]}

NO_UNTAP = {"kind": "static", "affects": "self",
            "mod": {"deny": ["untap_at_start"]}}

MODAL = {"op": "modal", "count": 1, "modes": [
    [{"op": "draw", "count": 1}],
    [{"op": "choose",
      "select": {"zone": "bz", "owner": "opp",
                 "filter": {"types": ["creature"]}},
      "as": "chosen"},
     {"op": "tap", "select": {"ref": "chosen"},
      "no_untap_next": True}],
    [{"op": "modify", "select": {"ref": "self"},
      "mod": {"no_leave": True},
      "duration": "until_next_own_turn_start"}],
]}

SHIELD_TRIGGER = {"kind": "trigger",
                  "when": {"event": "move", "to": "shield",
                           "subject": {"owner": "you"}},
                  "effect": [{"op": "untap", "select": {"ref": "self"}},
                             MODAL]}


def test_proto_parse_and_forms():
    c998 = proto_card("T998")
    assert c998["keywords"] == ["blocker"]
    assert c998["abilities"] == [CIP, GY_TRIGGER]
    d = parse_card(c998, TABLES)
    assert len(d.abilities) == 3      # blocker の static 展開＋誘発2つ
    c999 = proto_card("T999")
    assert c999["keywords"] == ["blocker", "double_breaker",
                                "enters_tapped"]
    assert c999["abilities"] == [NO_UNTAP, SHIELD_TRIGGER]
    d = parse_card(c999, TABLES)
    assert len(d.abilities) >= 3     # blocker 展開＋static＋誘発
    c1000 = proto_card("T1000")
    assert c1000["spell"] == [{"op": "move",
                               "select": {"zone": "deck", "owner": "you",
                                          "from_top": 1},
                               "to": "shield", "reason": "charge"}]
    parse_card(c1000, TABLES)


# ---------- ドライバ ----------

def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _cast_shield_add(e, may_answer="yes"):
    """T1000 を唱えてシールド配置を起こし、誘発の may まで処理する。"""
    cast = False
    for _ in range(160):
        d = e.advance()
        assert d is not None, "game ended before shield add"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and "play:T1000" in keys:
            e.answer([keys.index("play:T1000")])
            cast = True
            continue
        if cast and d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if cast and d["kind"] == "yes_no":
            e.answer([keys.index(may_answer)])
            continue
        if cast and d["kind"] in ("charge", "main", "attack"):
            return
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("shield add did not resolve")


def test_graveyard_trigger_may_bring_out():
    """T998（墓地）: 自分のシールドゾーンにカードが置かれた時、
    may で墓地から出る。出たら CIP で2枚引く。no なら墓地に残る。"""
    rules = load_rules()
    e = setup(rules, {"graveyard": ["T998"], "hand": ["T1000"],
                      "mana": ["T001"]}, {})
    _cast_shield_add(e, may_answer="yes")
    t998 = _bz(e, 0, "T998")
    assert e.s.cards[t998].zone == "bz"
    # CIP で2枚引いた（手札は T1000 を唱えて0→2枚）
    assert len(e.zlist("hand", 0)) == 2

    e = setup(rules, {"graveyard": ["T998"], "hand": ["T1000"],
                      "mana": ["T001"]}, {})
    _cast_shield_add(e, may_answer="no")
    gy = [c for c in e.zlist("graveyard", 0)
          if e.s.cards[c].defn == "T998"]
    assert len(gy) == 1


def test_enters_tapped_and_no_untap_at_own_turn_start():
    """T999: タップして出て（enters_tapped）、自分のターンのはじめ
    にもアンタップしない（deny untap_at_start）。"""
    rules = load_rules()
    e = setup(rules, {"hand": ["T999"], "mana": ["T004", "T001"]}, {})
    played = False
    seen_p1 = False
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if played and d.get("player") == 1:
            seen_p1 = True   # 相手のターンを挟んだ = 自分のターン開始を通過
        if d["kind"] == "main" and d.get("player") == 0:
            if not played and "play:T999" in keys:
                e.answer([keys.index("play:T999")])
                played = True
                continue
            if played and seen_p1:
                break        # 次の自分の main = 1周した
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert played
    t999 = _bz(e, 0, "T999")
    assert e.s.cards[t999].tapped is True


def _cast_shield_add_modal(e, mode_idx):
    """T1000 を唱え、T999 の誘発の modal で mode_idx を選ぶ。"""
    cast = False
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended before modal"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and "play:T1000" in keys:
            e.answer([keys.index("play:T1000")])
            cast = True
            continue
        if cast and d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if cast and d["kind"] == "choose_mode":
            e.answer([keys.index(f"mode:{mode_idx}")])
            continue
        if cast and d["kind"] == "choose_cards":
            e.answer([0])
            continue
        if cast and d["kind"] in ("charge", "main", "attack"):
            return
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("modal did not resolve")


def test_shield_trigger_untap_and_modal_draw():
    """T999: シールド配置でアンタップし、モード0で1枚引く。"""
    rules = load_rules()
    e = setup(rules, {"bz": ["T999"], "hand": ["T1000", "T002"],
                      "mana": ["T001"]}, {"bz": ["T004"]})
    t999 = _bz(e, 0, "T999")
    e.s.cards[t999].tapped = True
    _cast_shield_add_modal(e, 0)
    assert e.s.cards[t999].tapped is False
    # 手札: T1000 を唱えて1枚減り、ドローで1枚増える = 2枚
    assert len(e.zlist("hand", 0)) == 2


def test_shield_trigger_modal_tap_opponent():
    """T999: モード1で相手のクリーチャーを1体タップする。"""
    rules = load_rules()
    e = setup(rules, {"bz": ["T999"], "hand": ["T1000"],
                      "mana": ["T001"]}, {"bz": ["T004"]})
    t999 = _bz(e, 0, "T999")
    e.s.cards[t999].tapped = True
    _cast_shield_add_modal(e, 1)
    assert e.s.cards[t999].tapped is False
    t004 = _bz(e, 1, "T004")
    assert e.s.cards[t004].tapped is True
