"""語彙パイロット第173弾: deck_evolution（デッキ進化）。

デッキ進化は進化クリーチャーの出し方の一種。召喚する時、山札の上から
めくり、そのカードがクリーチャーであれば重ねて出す。クリーチャー以外
なら手札に戻る（召喚は不成立）。めくりは支払いの前に行う（801.1a の
進化元選択と同じく、召喚の可否を決める手順はコスト支払いに先行する）。

- 面フィールド `deck_evolution: {count?, rest_to?, blind?, shuffle_first?}`
  - `{count: 1}`: デッキ進化（上から1枚。クリーチャー以外なら手札へ）
  - `{count: 3, rest_to: graveyard}`: Mデッキ進化（上から3枚。1体選び、
    残りは墓地へ。クリーチャーが無ければ手札へ戻し、3枚とも墓地へ）
  - `{count: 1, blind: true, shuffle_first: true}`: OMGデッキ進化
    （シャッフルしてから一番上に裏向きのまま重ねる。種類を問わない）
- 効果で「このクリーチャーの上に置く」時は move の `stack_evo: true` に
  `evo_source: {ref: self}` を併記する（put_stacked が重ね先を固定し、
  進化元の適格性も照合する。従来の put_under は選んだカードを「下に」
  置く別機構で、「上に置く」には使えない）。
- 破壊された時の下のカードは from_under 機構で拾う（第156弾）。
  下のカード自身の移動レコードに宿主が載り、宿主の誘発が発火する。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()

IDS = tuple(f"T{n}" for n in range(369, 378))


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    parsed = {cid: parse_card(_proto_card(cid), TABLES) for cid in IDS}
    assert parsed["T369"].deck_evolution == {"count": 1}
    assert parsed["T370"].deck_evolution == {"count": 1}
    assert parsed["T371"].deck_evolution == {"count": 3, "rest_to": "graveyard"}
    assert parsed["T372"].deck_evolution == {"count": 1, "blind": True, "shuffle_first": True}
    t373 = _proto_card("T373")
    mv = t373["abilities"][0]["effect"][0]["body"][1]
    assert mv["op"] == "move" and mv["stack_evo"] is True
    assert mv["evo_source"] == {"ref": "self"}
    assert _proto_card("T375")["abilities"][0]["when"]["from_under"] == "self"
    assert _proto_card("T376")["abilities"][0]["effect"][1]["body"][1]["evo_source"] == {"ref": "self"}


def test_invalid_forms():
    base = {"id": "test-de-bad", "name": "試験進化不良", "types": ["creature", "evolution"],
            "civs": ["fire"], "cost": 5, "power": 3000, "mana": 1,
            "evolve_from": {"types": ["creature"]},
            "source": {"official": "test-de-bad", "review": "pending"}}
    bad_des = ("1", {"count": 0}, {"count": "1"}, {"count": 1, "rest_to": "hand2"},
               {"count": 1, "blind": "yes"}, {"count": 1, "shuffle_first": 1},
               {"count": 1, "extra": True})
    for bad in bad_des:
        with pytest.raises(DefError) as e:
            parse_card({**base, "deck_evolution": bad}, TABLES)
        assert "deck_evolution" in str(e.value)
    bad_move = {"op": "move", "select": {"zone": "deck", "owner": "you", "count": 1},
                "to": "bz", "reason": "put", "evo_source": {"ref": "self"}}
    with pytest.raises(DefError) as e:
        parse_card({**base, "abilities": [{"kind": "trigger",
                                            "when": {"event": "move", "to": "bz", "subject": "self"},
                                            "effect": [bad_move]}]}, TABLES)
    assert "evo_source" in str(e.value)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _defns(e, zone, player=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, player)]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _arrange_deck(e, p, top_defns):
    """山札の上から top_defns の順に並べ替え（第163弾の流儀。setup の deck 指定は所属だけで順序は保証しない）。"""
    rest = list(e.s.zones["deck"][p])
    chosen = []
    for dfn in top_defns:
        c = next(c for c in rest if e.s.cards[c].defn == dfn)
        rest.remove(c)
        chosen.append(c)
    e.s.zones["deck"][p] = chosen + rest
    return chosen


def _drive(e, play_keys, max_steps=300):
    """決定が出るたびに方針どおりに答え、play_keys の選択肢をメイン決定で順に使い、
    使い終わってメイン／チャージ／攻撃の決定で落ち着いたら返す。"""
    play_keys = list(play_keys)
    played = set()
    saw_main = False
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended before settling"
        keys = _keys(d)
        kind = d["kind"]
        if kind == "main" and d["player"] == 0:
            if not saw_main:
                saw_main = True
                missing = [k for k in play_keys if k not in keys]
                assert not missing, f"main options lack {missing}: {keys}"
            nxt = next((k for k in play_keys if k not in played and k in keys), None)
            if nxt is not None:
                played.add(nxt)
                e.answer([keys.index(nxt)])
                continue
            if played or not play_keys:
                return
        if played and kind in ("charge", "attack"):
            return
        if kind == "pay_mana":
            e.answer([0])
        elif kind in ("choose_cards", "choose_shields"):
            e.answer(list(range(d["min"])))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("did not settle")


def _to_attack(e):
    d = e.advance()
    while d["kind"] in ("charge", "main"):
        e.answer([_keys(d).index("pass")])
        d = e.advance()
    assert d["kind"] == "attack", d["kind"]
    return d


def _settle(e, max_steps=120):
    for _ in range(max_steps):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            return d
        if d["kind"] == "yes_no":
            e.answer([_keys(d).index("yes")])
        else:
            e.answer([0])
    raise AssertionError("did not settle")


def _destroy_and_answer_may(e, c):
    # 待機中 Decision の回答は、積んだタスクが終わってから消費される。破壊で選択肢が変わる
    # Decision（attack 等）では回答 index が陳腐化するため、破壊は手札に影響しない相手の
    # charge Decision で待っている状態で呼ぶこと。
    if e.s.waiting is not None:
        d = e.s.waiting
        e.answer([_keys(d).index("pass")] if "pass" in _keys(d) else 0)
    e._push(e.ev_task({"ev": "move", "subject": e.s.ref(c), "to": "graveyard", "reason": "destroy"}))
    for _ in range(60):
        d = e.advance()
        if d is None:
            break
        if d["kind"] == "yes_no":
            e.answer([_keys(d).index("yes")])
            continue
        if d["kind"] in ("charge", "main", "attack"):
            break
        e.answer([0])


def _to_opponent_charge(e):
    """自分のターンを終わらせ、相手のチャージ Decision まで進める。"""
    for _ in range(120):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if d["kind"] == "charge" and d["player"] == 1:
            return d
        keys = _keys(d)
        if d["kind"] == "yes_no":
            e.answer([keys.index("yes")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("did not settle")


def _mana7():
    return ["T005"] + ["T001"] * 6


def test_deck_evo_success_and_conditional_power(rules):
    """T369: 山札の上がクリーチャーなら重ねて出る。マナ7を払う。下は T001。
    他のアーマード・ドラゴンがいれば +3000（11000）、いなければ 8000。"""
    e = setup(rules, {"hand": ["T369"], "deck": ["T001"], "mana": _mana7(), "bz": ["T369"]}, {})
    _arrange_deck(e, 0, ["T001"])
    _drive(e, ["play:T369"])
    tops = e.bz_tops(0)
    assert len(tops) == 2
    assert all(e.chars_ro(c)["power"] == 11000 for c in tops), "互いに他のドラゴンがいるので両方 +3000"
    # 進化で出た方は entered_turn=-1（_stack が召喚酔いを消す。801.3）なので下の有無で判別する
    new_top = next(c for c in tops if e.s.cards[c].under)
    assert [e.s.cards[u].defn for u in e.s.cards[new_top].under] == ["T001"]
    assert all(e.s.cards[c].tapped for c in e.zlist("mana", 0)), "コスト7を払っている"
    e = setup(rules, {"hand": ["T369"], "deck": ["T001"], "mana": _mana7()}, {})
    _drive(e, ["play:T369"])
    top = _bz(e, 0, "T369")
    assert e.chars_ro(top)["power"] == 8000, "他のドラゴンがいなければ +3000 されない（対照）"


def test_deck_evo_fail_returns_to_hand(rules):
    """T370: 山札の上が呪文なら手札に戻る。マナは払わず、山札の上も動かない。"""
    e = setup(rules, {"hand": ["T370"], "deck": ["T003"], "mana": ["T005", "T001", "T001", "T001"]}, {})
    _drive(e, ["play:T370"])
    assert "T370" in _defns(e, "hand"), "手札に戻っている"
    assert "T370" not in _defns(e, "bz"), "出ていない"
    assert not any(e.s.cards[c].tapped for c in e.zlist("mana", 0)), "支払い前に失敗するのでマナは払わない"
    assert e.s.cards[e.zlist("deck", 0)[0]].defn == "T003", "山札の上は動かない"


def test_deck_evo_empty_deck_loses(rules):
    """T371: めくり失敗で山札が空になると、そのままドロー負けする（703.4b。山札0枚は SBA で敗北）。
    開始時に山札が空だと1ターン目のドローで負けるため、失敗で空になる形で確認する。
    なお _can_play_face の空山札チェックは防御（空の状態で main に到達することはない）。"""
    e = setup(rules, {"hand": ["T371"], "deck": ["T003", "T003", "T003"],
                      "mana": ["T005"] + ["T001"] * 4}, {}, deck_left=[3, None])
    _arrange_deck(e, 0, ["T003", "T003", "T003"])
    d = e.advance()
    while d["kind"] != "main":
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys else 0)
        d = e.advance()
    assert "play:T371" in _keys(d), "最初は出せる"
    e.answer([_keys(d).index("play:T371")])
    for _ in range(120):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] in ("choose_cards", "choose_shields"):
            e.answer(list(range(d["min"])))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert d is None, "山札が空になったのでゲームが終わる"
    assert e.s.result["reason"] == "deck_out" and e.s.result["winner"] == 1
    assert "T371" in _defns(e, "hand"), "失敗したので手札に残る"
    assert len(e.zlist("deck", 0)) == 0, "めくった3枚が墓地へ行って山札は空"


def test_m_deck_evo_success(rules):
    """T371: 上から3枚めくり、クリーチャー2体から1体を選んで重ねる。
    選ばなかった分（呪文＋クリーチャー）は墓地へ。"""
    e = setup(rules, {"hand": ["T371"], "deck": ["T001", "T003", "T005"],
                      "mana": ["T005"] + ["T001"] * 4}, {})
    _arrange_deck(e, 0, ["T001", "T003", "T005"])
    _drive(e, ["play:T371"])
    top = _bz(e, 0, "T371")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T001"], "先頭の候補を選ぶ"
    assert "T003" in _defns(e, "graveyard") and "T005" in _defns(e, "graveyard"), "残りは墓地へ"
    assert len(e.zlist("deck", 0)) == 15, "めくった3枚が山札を離れている"


def test_m_deck_evo_fail(rules):
    """T371: 上3枚にクリーチャーが無ければ手札に戻り、3枚とも墓地へ。マナは払わない。"""
    e = setup(rules, {"hand": ["T371"], "deck": ["T003", "T003", "T003"],
                      "mana": ["T005"] + ["T001"] * 4}, {})
    _arrange_deck(e, 0, ["T003", "T003", "T003"])
    _drive(e, ["play:T371"])
    assert "T371" in _defns(e, "hand")
    assert _defns(e, "graveyard").count("T003") == 3, "めくった3枚はすべて墓地へ"
    assert not any(e.s.cards[c].tapped for c in e.zlist("mana", 0))


def test_omg_deck_evo_blind(rules):
    """T372: シャッフルしてから一番上に裏向きのまま重ねる。呪文でも重ねられる。"""
    e = setup(rules, {"hand": ["T372"], "deck": ["T003"],
                      "mana": ["T005"] + ["T001"] * 4}, {})
    _drive(e, ["play:T372"])
    top = _bz(e, 0, "T372")
    assert len(e.s.cards[top].under) == 1, "種類を問わず1枚重ねる"
    assert len(e.zlist("deck", 0)) == 15, "山札の上1枚が下になった"
    assert all(e.s.cards[c].tapped for c in e.zlist("mana", 0)), "コスト5を払っている"


def test_fixed_stack_on(rules):
    """T373: 起動で山札から T374 を選び、このクリーチャーの上に置く。
    T374 が上になり、起動した T373 が下になる。"""
    e = setup(rules, {"bz": ["T373"], "deck": ["T374"]}, {})
    e.s.cards[_bz(e, 0, "T373")].entered_turn = -1
    d = _to_attack(e)
    act = next(k for k in _keys(d) if k.startswith("activate:T373"))
    e.answer([_keys(d).index(act)])
    _settle(e)
    top = _bz(e, 0, "T374")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T373"], "T373 が T374 の下になる"
    assert "T373" not in [e.s.cards[c].defn for c in e.bz_tops(0)]


def test_fixed_stack_on_picks_activated_host(rules):
    """T373: T373 が2体いても、起動した方に重ねる（もう一方は上のまま）。"""
    e = setup(rules, {"bz": ["T373", "T373"], "deck": ["T374"]}, {})
    cids = [c for c in e.bz_tops(0) if e.s.cards[c].defn == "T373"]
    for c in cids:
        e.s.cards[c].entered_turn = -1
    d = _to_attack(e)
    opts = [o for o in d["options"] if o["key"].startswith("activate:T373")]
    assert len(opts) == 2
    second = cids[1]
    e.answer([d["options"].index(next(o for o in opts if o["cid"] == second))])
    _settle(e)
    top = _bz(e, 0, "T374")
    assert e.s.cards[top].under == [second], "起動した2体目が下になる"
    assert cids[0] in e.bz_tops(0), "もう一方は上のまま"


def test_fixed_stack_on_without_target(rules):
    """T373: 山札に T374 が無ければ何も重ならない（対照）。"""
    e = setup(rules, {"bz": ["T373"], "deck": ["T001"]}, {})
    e.s.cards[_bz(e, 0, "T373")].entered_turn = -1
    d = _to_attack(e)
    act = next(k for k in _keys(d) if k.startswith("activate:T373"))
    e.answer([_keys(d).index(act)])
    _settle(e)
    assert "T373" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert e.s.cards[_bz(e, 0, "T373")].under == []


def test_from_under_destroy(rules):
    """T375: デッキ進化で出した後、破壊されると下のカードが墓地から出る。"""
    e = setup(rules, {"hand": ["T375"], "deck": ["T001"],
                      "mana": ["T005"] + ["T001"] * 4}, {})
    _arrange_deck(e, 0, ["T001"])
    _drive(e, ["play:T375"])
    top = _bz(e, 0, "T375")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T001"]
    _to_opponent_charge(e)
    _destroy_and_answer_may(e, top)
    assert "T375" in _defns(e, "graveyard")
    assert "T001" in [e.s.cards[c].defn for c in e.bz_tops(0)], "下のカードがバトルゾーンに出る"


def test_cip_stack_evo(rules):
    """T376: 出た時、上から4枚を見て、進化できるコスト6以下のクリーチャー1体を
    このクリーチャーの上に置く。残りは好きな順序で山札の下へ。"""
    e = setup(rules, {"hand": ["T376"], "deck": ["T377", "T001", "T001", "T001"],
                      "mana": ["T005"] + ["T001"] * 4}, {})
    _arrange_deck(e, 0, ["T377", "T001", "T001", "T001"])
    _drive(e, ["play:T376"])
    top = _bz(e, 0, "T377")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T376"]
    assert len(e.zlist("deck", 0)) == 18, "T377 が出て残り3枚が下へ"
    assert all(e.s.cards[c].defn == "T001" for c in e.zlist("deck", 0))


def test_cip_stack_evo_without_candidate(rules):
    """T376: 上4枚に進化できるクリーチャーが無ければ何も重ねず、4枚とも下へ（対照）。"""
    e = setup(rules, {"hand": ["T376"], "deck": ["T001", "T001", "T001", "T001"],
                      "mana": ["T005"] + ["T001"] * 4}, {})
    _arrange_deck(e, 0, ["T001", "T001", "T001", "T001"])
    _drive(e, ["play:T376"])
    top = _bz(e, 0, "T376")
    assert e.s.cards[top].under == []
    assert len(e.zlist("deck", 0)) == 19, "4枚とも下へ行くので山札の枚数は変わらない"
