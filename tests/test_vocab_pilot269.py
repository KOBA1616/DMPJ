"""語彙パイロット第269弾: s_trigger_x（S・トリガーX）。

「S・トリガーX（このクロスギアをシールドゾーンから手札に加える時、
コストを支払わずにすぐジェネレートし、自分のクリーチャー１体にクロスしてもよい）」

新語彙はキーワード **`s_trigger_x`**（data/rules/keywords.yaml）。
通常の S・トリガーと同じくシールドゾーンからの allow: [s_trigger] を与えるので、
ブレイク時の declare_strigger の選択肢に出る。宣言して解決すると、通常の
S・トリガーと同じく play_task（free）でジェネレートされる。その直後に
h_resolve_pending が効果の子タスクを積み、生成されたギア（self_entered。
生成で gen が1増える）がバトルゾーンにあり、自分のクリーチャーがいれば
may で無償クロス（既存 op cross_free）を尋ねる。生成されなかった時や
自分のクリーチャーがいない時は尋ねない。

対象は s_trigger_x ギャップの6枚（dm23ex1-066 / dm29-034 / dm15-023 /
dm15-026 / dm15-029 / dm15-032）。うち4枚は単独ギャップ、残り2枚の
cross_free_op は第195弾の op cross_free で表せる。
"""
import pytest
from tests.conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card

TABLES = load_tables()


def _by_defn(e, zone, p):
    if zone == "bz":
        return {e.cdef(c).id: c for c in e.bz_tops(p)}
    return {e.cdef(c).id: c for c in e.zlist(zone, p)}


def _gear(e, p=1):
    by = _by_defn(e, "bz", p)
    for gid in ("T746", "T747"):
        if gid in by:
            return by[gid]
    return None


def _drive(e, stop, declare=None, cross_yes=True, limit=800):
    """ブレイク→S・トリガー宣言→生成→無償クロスまで進める汎用ドライバ。

    declare: declare_strigger で宣言する defn（None なら宣言しない）。
    cross_yes: S・トリガーXの may（yes_no）に yes と答えるか。
    """
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind in ("charge", "main"):
            e.answer([keys.index("pass")])
        elif kind == "attack":
            hit = [i for i, k in enumerate(keys) if k == "attack:T001:player"]
            e.answer([hit[0]] if hit else [keys.index("pass")])
        elif kind == "choose_breaker":
            e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
        elif kind == "choose_shields":
            e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            if declare is None:
                e.answer([])
            else:
                hit = [i for i, k in enumerate(keys) if k == f"strigger:{declare}"]
                assert hit, f"strigger:{declare} not in {keys}"
                e.answer(hit)
        elif kind == "declare_sback":
            e.answer([])
        elif kind == "yes_no":
            e.answer([keys.index("yes" if cross_yes else "no")])
        elif kind == "choose_cards":
            # タップ先（相手の T002。タップ済みの攻撃者を選ぶと無意味）と
            # クロス先（自分の T001）を区別する。クロス先は候補1枚なら自動回答され、
            # 決定としては現れない。
            tap = [i for i, o in enumerate(d["options"])
                   if e.cdef(o["cid"]).id == "T002"]
            own = [i for i, o in enumerate(d["options"])
                   if e.s.cards[o["cid"]].controller == 1]
            if tap:
                e.answer(tap[:1])
            elif own:
                e.answer(own[:1])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "order_pending":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if stop(e):
            return
    raise AssertionError("limit reached")


def _crossed(e):
    """ギアがバトルゾーンにあり、クロスが済んでいる（＋後続の効果タスクが無い）か。"""
    g = _gear(e)
    return (g is not None and e.s.cards[g].crossed is not None
            and not any(t.get("t") == "effect" for t in e.s.tasks))


# ---------- parse / validation ----------

def test_pilot269_protos_parse():
    rules = load_rules()
    t746 = rules.cards["T746"]
    assert "s_trigger_x" in t746.keywords
    assert t746.abilities[0] == {"kind": "static", "zone": "shield",
                                 "affects": "self", "mod": {"allow": ["s_trigger"]},
                                 "keyword": "s_trigger_x"}
    assert t746.abilities[1] == {"kind": "static", "affects": "crossed",
                                 "mod": {"power": 1000}}
    assert rules.cards["T747"].abilities[1]["effect"] == [
        {"op": "tap",
         "select": {"zone": "bz", "owner": "opp",
                    "filter": {"types": ["creature"]}, "count": 1},
         "no_untap_next": True}]
    base = {"id": "TX", "name": "x", "types": ["cross_gear"],
            "civs": ["light"], "cost": 2, "races": ["サムライ"],
            "keywords": ["s_trigger_x"],
            "abilities": [{"kind": "static", "affects": "crossed",
                           "mod": {"power": 1000}}]}
    parse_card(dict(base), TABLES)
    with pytest.raises(DefError):
        bad = dict(base)
        bad["keywords"] = ["s_trigger_y"]
        parse_card(bad, TABLES)


# ---------- 実挙動 ----------

def test_strigger_x_declares_and_crosses(rules):
    """宣言すると無料でジェネレートされ、選んだ自分のクリーチャーにクロスする。"""
    e = setup(rules, {"bz": ["T001"]}, {"shield": ["T746"], "bz": ["T001"]})
    _drive(e, _crossed, declare="T746")
    g = _gear(e)
    host = _by_defn(e, "bz", 1)["T001"]
    assert e.s.cards[g].zone == "bz"
    assert list(e.s.cards[g].crossed) == list(e.s.ref(host))
    assert e.chars_ro(host)["power"] == 3000   # 2000 + クロス先の +1000
    assert _by_defn(e, "hand", 1).get("T746") is None


def test_strigger_x_decline_cross_leaves_gear_uncrossed(rules):
    """クロスを断ると、ギアはバトルゾーンに残り、クロスされない。"""
    e = setup(rules, {"bz": ["T001"]}, {"shield": ["T746"], "bz": ["T001"]})

    def stop(ev):
        g = _gear(ev)
        return (g is not None
                and not any(t.get("t") == "effect" for t in ev.s.tasks))
    _drive(e, stop, declare="T746", cross_yes=False)
    g = _gear(e)
    assert e.s.cards[g].zone == "bz"
    assert e.s.cards[g].crossed is None
    host = _by_defn(e, "bz", 1)["T001"]
    assert e.chars_ro(host)["power"] == 2000


def test_strigger_x_no_creature_asks_nothing(rules):
    """自分のクリーチャーがいない時は、クロスを尋ねずにジェネレートだけする。"""
    e = setup(rules, {"bz": ["T001"]}, {"shield": ["T746"]})

    def stop(ev):
        g = _gear(ev)
        return (g is not None
                and not any(t.get("t") == "effect" for t in ev.s.tasks))
    _drive(e, stop, declare="T746")
    g = _gear(e)
    assert e.s.cards[g].zone == "bz"
    assert e.s.cards[g].crossed is None


def test_strigger_x_entry_trigger_still_fires(rules):
    """S・トリガーXで出たギアの「出た時」誘発も解決する（T747: 相手をタップ）。"""
    e = setup(rules, {"bz": ["T001", "T002"]},
              {"shield": ["T747"], "bz": ["T001"]})

    def stop(ev):
        g = _gear(ev)
        if g is None or e.s.cards[g].crossed is None:
            return False
        tgt = _by_defn(ev, "bz", 0).get("T002")
        return tgt is not None and ev.s.cards[tgt].tapped
    _drive(e, stop, declare="T747")
    g = _gear(e)
    host = _by_defn(e, "bz", 1)["T001"]
    assert list(e.s.cards[g].crossed) == list(e.s.ref(host))
    tgt = _by_defn(e, "bz", 0)["T002"]
    assert e.s.cards[tgt].tapped
