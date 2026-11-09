"""from_under 機構（移動直前に他のカードの下にあったカードの move レコード）。

背景: 第156弾の event.under（離脱側から下を見る）に対して、下のカード側から見る形。
従来、スタックが一緒に離れる時に下のカードには move レコード自体が出ず、下のカードが
単独で動く時も「どのカードの下にあったか」がレコードに載らなかった。本機構では:

- _apply_one: スタック一括移動で、一緒に動いた下のカードにも move レコードを出す。
  レコードには宿主（上にいたカード）の移動直前の姿を host（ref）/ host_lki として載せる。
  下のカードが単独で動く場合は、そのレコード自体に host / host_lki を載せる（_record_for も同じ）。
  シールドの束（from が shield）は対象外（バトルゾーンの重なりだけを見る）。
- when の新キー from_under: true（下にあった）/ self（発生源自身の下にあった）/
  {owner, filter}（宿主への条件。subject と同じ形で宿主の lki に当てる）。
- _collect_triggers: 下のカードのレコードでは宿主も lki 発生源に加える。ただし宿主の能力は
  from_under を書いたものだけを見る（宿主の通常の観測誘発が下のカードの枚数だけ重複しないため）。
- _record_history: 下のカードのレコードは「特性を持たないカード」の移動として、
  クリーチャー単位の leave / destroyed の数えに入れない。

対象文面（rejects の from_under_trigger 10件）の型:
- A（dm34 系5件）: カード自身の誘発＋宿主フィルタ {types: [evolution]} → T280/T281/T282
- B（dmsd06-012）: 観測者＋subject フィルタ＋from_under: true → T286
- C（邪眼帝2件）: 宿主自身の誘発＋from_under: self → T283
- D（dm25ex3-or4）: 観測者＋宿主の owner 照合 → T285
- 単独移動（dm25rp4-033 の G-NEO 置換やメテオバーンのコスト）: T284 でコスト移動を観測

発火の観測はエンジンの trace（解決された誘発の因果記録）で発生源 defn の解決回数を数える。
"""
from collections import Counter
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import DefError, load_tables, parse_card

TABLES = load_tables()

P1_DESTROY = {"hand": ["T056"], "mana": ["T009", "T008", "T008", "T008"]}


def _setup(*args, **kwargs):
    e = setup(*args, **kwargs)
    e.s.trace = []      # 誘発の因果記録を有効にする（発火回数の実測用）
    return e


def _fires(e, defn):
    return Counter(t["src"] for t in e.s.trace if t["ev"] == "move")[defn]


def _by_defn(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p) if e.cdef(c).id == defn)


def _stack(e, top, unders):
    e.s.cards[top].under = list(unders)
    for u in unders:
        e.s.cards[u].top_of = top


def _settle(e, done, drive=None, max_steps=300):
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if drive and drive(e, d, keys):
            continue
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    return done()


def _flush(e, steps=60):
    """待機中の誘発が解決しきるまでだけ進める（ターンを進めない）。"""
    for _ in range(steps):
        if not e.s.pending:
            return
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))


def _destroy(e, player, target_cid):
    """player が T056 を唱えて target_cid を破壊し、誘発を解決しきる。"""
    def drive(e, d, keys):
        if d["kind"] == "main" and d["player"] == player and "play:T056" in keys:
            e.answer([keys.index("play:T056")])
            return True
        if d["kind"] not in ("main", "attack") \
                and any(o.get("cid") == target_cid for o in d["options"]):
            idx = [i for i, o in enumerate(d["options"]) if o.get("cid") == target_cid]
            e.answer(idx[:max(d["min"], 1)])
            return True
        return False
    assert _settle(e, lambda: e.s.cards[target_cid].zone == "graveyard", drive)
    _flush(e)


def _proto(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    c = parse_card(_proto("T280"), TABLES)
    trig = [a for a in c.abilities if a["kind"] == "trigger"]
    assert trig[0]["when"] == {"event": "move", "to": "graveyard", "subject": "self",
                               "from_under": {"filter": {"types": ["evolution"]}}}
    c = parse_card(_proto("T283"), TABLES)
    assert c.abilities[0]["when"] == {"event": "move", "from_under": "self"}
    c = parse_card(_proto("T285"), TABLES)
    assert c.abilities[0]["when"] == {"event": "move", "subject": {"owner": "you"},
                                      "from_under": {"owner": "you"}}
    c = parse_card(_proto("T286"), TABLES)
    assert c.abilities[0]["when"]["from_under"] is True


def test_from_under_validation():
    base = {"id": "XFU", "name": "検証用", "types": ["creature"], "civs": ["fire"], "cost": 2,
            "power": 1000, "text": "x",
            "abilities": [{"kind": "trigger",
                           "when": {"event": "move", "from_under": True},
                           "effect": [{"op": "draw", "count": 1}]}]}
    parse_card(base, TABLES)   # true は通る
    parse_card(dict(base, abilities=[{"kind": "trigger",
                                      "when": {"event": "move", "from_under": False},
                                      "effect": [{"op": "draw", "count": 1}]}]), TABLES)   # false（否定形）も通る
    for bad in ("other", {"owner": "nobody"}, {"bogus": 1}):
        card = dict(base, abilities=[{"kind": "trigger",
                                      "when": {"event": "move", "from_under": bad},
                                      "effect": [{"op": "draw", "count": 1}]}])
        with pytest.raises(DefError):
            parse_card(card, TABLES)


def test_under_records_direct(rules):
    """レコードの形そのもの: 一緒に離れる下のカードに host / host_lki が載る（判別の中核）。"""
    e = setup(rules, {"bz": ["T281", "T287"]}, {})
    top = _by_defn(e, "bz", 0, "T281")
    und = _by_defn(e, "bz", 0, "T287")
    _stack(e, top, [und])
    top_ref = e.s.ref(top)
    recs = e._apply_one({"ev": "move", "subject": top_ref, "to": "graveyard", "reason": "destroy"})
    assert len(recs) == 2
    main, under = recs
    assert main["subject"][0] == top and "host" not in main
    assert under["subject"][0] == und and under["from"] == "bz" and under["to"] == "graveyard"
    assert under["host"] == top_ref and under["host_lki"]["defn"] == "T281"
    assert under["lki"]["defn"] == "T287"
    # 下のカード単独の移動（_record_for）でも宿主が載る
    e2 = setup(rules, {"bz": ["T281", "T287"]}, {})
    top2 = _by_defn(e2, "bz", 0, "T281")
    und2 = _by_defn(e2, "bz", 0, "T287")
    _stack(e2, top2, [und2])
    rec = e2._record_for({"ev": "move", "subject": e2.s.ref(und2), "to": "graveyard", "reason": "put"})
    assert rec["host"] == e2.s.ref(top2) and rec["host_lki"]["defn"] == "T281"


def test_under_records_history_counts(rules):
    """下のカードはクリーチャー単位の destroyed / leave の数えに入らない（トップだけ数える）。"""
    e = setup(rules, {"bz": ["T281", "T287"]}, {})
    top = _by_defn(e, "bz", 0, "T281")
    und = _by_defn(e, "bz", 0, "T287")
    _stack(e, top, [und])
    e.apply_batch([{"ev": "move", "subject": e.s.ref(top), "to": "graveyard", "reason": "destroy"}])
    tc = e.s.turn_counters
    assert tc.get("hist:destroyed:0") == 1
    assert tc.get("hist:leave:0") == 1


def test_a_under_draw_on_stack_destroy(rules):
    """A: 進化クリーチャーが破壊され、下の T280 も一緒に墓地へ → T280 の誘発が1回発火する。"""
    e = _setup(rules, {"bz": ["T281", "T280"]}, dict(P1_DESTROY))
    top = _by_defn(e, "bz", 0, "T281")
    und = _by_defn(e, "bz", 0, "T280")
    _stack(e, top, [und])
    _destroy(e, 1, top)
    assert e.s.cards[top].zone == "graveyard" and e.s.cards[und].zone == "graveyard"
    assert _fires(e, "T280") == 1


def test_a_no_draw_when_not_under(rules):
    """A 対照: 下にない T280 が破壊されても発火しない（from_under が付かない）。"""
    e = _setup(rules, {"bz": ["T280"]}, dict(P1_DESTROY))
    top = _by_defn(e, "bz", 0, "T280")
    _destroy(e, 1, top)
    assert e.s.cards[top].zone == "graveyard"
    assert _fires(e, "T280") == 0


def test_a_no_draw_when_host_not_evolution(rules):
    """A 対照: 宿主が進化クリーチャーでなければ発火しない（宿主フィルタの判別）。"""
    e = _setup(rules, {"bz": ["T282", "T280"]}, dict(P1_DESTROY))
    top = _by_defn(e, "bz", 0, "T282")
    und = _by_defn(e, "bz", 0, "T280")
    _stack(e, top, [und])
    _destroy(e, 1, top)
    assert e.s.cards[und].zone == "graveyard"
    assert _fires(e, "T280") == 0


def test_c_host_draws_per_under_on_destroy(rules):
    """C: 宿主 T283 が下2枚ごと破壊されると、宿主の誘発が下のカード1枚につき1回（計2回）。

    宿主は既に墓地にいるため、発生源は host_lki 経由でしか届かない（本機構の判別点）。"""
    e = _setup(rules, {"bz": ["T283", "T287", "T287"]}, dict(P1_DESTROY))
    top = _by_defn(e, "bz", 0, "T283")
    unds = [c for c in e.zlist("bz", 0) if e.cdef(c).id == "T287"]
    assert len(unds) == 2
    _stack(e, top, unds)
    _destroy(e, 1, top)
    assert e.s.cards[top].zone == "graveyard"
    assert all(e.s.cards[u].zone == "graveyard" for u in unds)
    assert _fires(e, "T283") == 2


def test_c_host_alone_no_draw(rules):
    """C 対照: 下のない T283 が破壊されても発火しない（自分の移動では from_under は付かない）。"""
    e = _setup(rules, {"bz": ["T283"]}, dict(P1_DESTROY))
    top = _by_defn(e, "bz", 0, "T283")
    _destroy(e, 1, top)
    assert e.s.cards[top].zone == "graveyard"
    assert _fires(e, "T283") == 0


def test_c_host_not_triggered_by_other_stack(rules):
    """C 対照: 別のクリーチャーの下のカードが離れても、T283 の from_under: self は発火しない。"""
    e = _setup(rules, {"bz": ["T283", "T281", "T287"]}, dict(P1_DESTROY))
    host = _by_defn(e, "bz", 0, "T281")
    und = _by_defn(e, "bz", 0, "T287")
    _stack(e, host, [und])
    _destroy(e, 1, host)
    assert e.s.cards[und].zone == "graveyard"
    assert _fires(e, "T283") == 0


def test_d_observer_draws_for_own_under(rules):
    """D: 自分のクリーチャーの下のカードが離れると、観測者 T285 が1回発火する。"""
    e = _setup(rules, {"bz": ["T285", "T281", "T287"]}, dict(P1_DESTROY))
    top = _by_defn(e, "bz", 0, "T281")
    und = _by_defn(e, "bz", 0, "T287")
    _stack(e, top, [und])
    _destroy(e, 1, top)
    assert e.s.cards[und].zone == "graveyard"
    assert _fires(e, "T285") == 1


def test_d_observer_no_draw_for_opp_under(rules):
    """D 対照: 相手のクリーチャーの下のカードが離れても発火しない（宿主・subject の owner 判別）。"""
    e = _setup(rules, {"bz": ["T285"], "hand": ["T056"], "mana": ["T009", "T008", "T008"]},
               {"bz": ["T281", "T287"]})
    top = _by_defn(e, "bz", 1, "T281")
    und = _by_defn(e, "bz", 1, "T287")
    _stack(e, top, [und])
    _destroy(e, 0, top)
    assert e.s.cards[und].zone == "graveyard"
    assert _fires(e, "T285") == 0


def test_b_observer_draws_for_under_to_graveyard(rules):
    """B: 自分のテスト（種族）が下から墓地に置かれると、観測者 T286 が1回発火する。"""
    e = _setup(rules, {"bz": ["T286", "T281", "T287"]}, dict(P1_DESTROY))
    top = _by_defn(e, "bz", 0, "T281")
    und = _by_defn(e, "bz", 0, "T287")
    _stack(e, top, [und])
    _destroy(e, 1, top)
    assert e.s.cards[und].zone == "graveyard"
    assert _fires(e, "T286") == 1


def test_b_no_draw_for_other_race(rules):
    """B 対照: 下のカードが対象の種族でなければ発火しない（subject フィルタの判別）。"""
    e = _setup(rules, {"bz": ["T286", "T281", "T277"]}, dict(P1_DESTROY))
    top = _by_defn(e, "bz", 0, "T281")
    und = _by_defn(e, "bz", 0, "T277")   # 竜試験兵（種族はアーマード・ドラゴン、能力なし）
    _stack(e, top, [und])
    _destroy(e, 1, top)
    assert e.s.cards[und].zone == "graveyard"
    assert _fires(e, "T286") == 0


def test_b2_stack_destroy_fires_once_not_twice(rules):
    """B 実物型（マイケル・ギャンドル）: 下のカードが宿主ごと破壊されても発火は1回だけ。

    破壊側の誘発は from_under: false で下からの分を除くため、「破壊された時」と
    「下から墓地に置かれた時」が同じ移動で重ならない（判別: false が効かないと2回になる）。
    宿主は対象種族を持たない T277（宿主自身の破壊ではどちらの誘発も発火しない）。"""
    e = _setup(rules, {"bz": ["T288", "T277", "T280"]}, dict(P1_DESTROY))
    top = _by_defn(e, "bz", 0, "T277")
    und = _by_defn(e, "bz", 0, "T280")
    _stack(e, top, [und])
    _destroy(e, 1, top)
    assert e.s.cards[und].zone == "graveyard"
    assert _fires(e, "T288") == 1


def test_b2_plain_destroy_fires_once(rules):
    """B 実物型: 下にない自分のテストが破壊された時は、破壊側の誘発が1回発火する。"""
    e = _setup(rules, {"bz": ["T288", "T280"]}, dict(P1_DESTROY))
    top = _by_defn(e, "bz", 0, "T280")
    _destroy(e, 1, top)
    assert e.s.cards[top].zone == "graveyard"
    assert _fires(e, "T288") == 1


def test_a_alone_move_by_under_cost(rules):
    """単独移動: メテオバーン型コストで下の T280 だけが墓地へ行くと、T280 の誘発も発火する。"""
    e = _setup(rules, {"bz": ["T284", "T280"]}, {"bz": ["T001"]})
    top = _by_defn(e, "bz", 0, "T284")
    und = _by_defn(e, "bz", 0, "T280")
    _stack(e, top, [und])

    def drive(e, d, keys):
        if "activate:T284:0" in keys:
            e.answer([keys.index("activate:T284:0")])
            return True
        return False
    assert _settle(e, lambda: e.s.cards[und].zone == "graveyard", drive)
    _flush(e)
    assert e.s.cards[top].zone == "bz"
    assert _fires(e, "T280") == 1


def test_alone_move_control_plain_under(rules):
    """単独移動の対照: 能力のない下のカードをコストに使っても、何も発火しない。"""
    e = _setup(rules, {"bz": ["T284", "T287"]}, {"bz": ["T001"]})
    top = _by_defn(e, "bz", 0, "T284")
    und = _by_defn(e, "bz", 0, "T287")
    _stack(e, top, [und])

    def drive(e, d, keys):
        if "activate:T284:0" in keys:
            e.answer([keys.index("activate:T284:0")])
            return True
        return False
    assert _settle(e, lambda: e.s.cards[und].zone == "graveyard", drive)
    _flush(e)
    assert _fires(e, "T287") == 0 and _fires(e, "T280") == 0
