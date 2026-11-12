"""語彙パイロット第192弾: choose_player（プレイヤーを1人選ぶ）。

「プレイヤーを1人選ぶ。そのプレイヤーは〜」を表す語彙。

- 新 op `choose_player {as: 名前}`: 効果の使用者がプレイヤーを1人選び、変数に
  相対指定 "you"/"opp" を入れる。「選んでもよい」は may の body に入れて表す。
- プレイヤー指定の変数参照 {var: 名前}: op の player / players、セレクタの
  owner / chooser で使える。解決は Engine._rel が変数を引いて行う。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import DefError, load_tables, parse_card

TABLES = load_tables()

IDS = ("T469", "T470", "T471", "T472")


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)
    t469 = parse_card(_proto_card("T469"), TABLES)
    ops = t469.abilities[0]["effect"]
    assert ops[0] == {"op": "choose_player", "as": "tp"}
    assert ops[1]["select"]["owner"] == {"var": "tp"}
    assert ops[2] == {"op": "shuffle", "player": {"var": "tp"}}


def test_invalid_forms():
    base = {"id": "test-cp-bad", "name": "試験選別不良", "types": ["spell"],
            "civs": ["water"], "cost": 2, "mana": 1,
            "source": {"official": "test-cp-bad", "review": "pending"}}
    bad_spells = (
        [{"op": "draw", "player": {"var": 3}, "count": 1}],          # var は文字列
        [{"op": "draw", "player": {"bogus": "tp"}, "count": 1}],     # var 以外のキー
        [{"op": "move", "select": {"zone": "hand", "owner": {"var": 3}, "count": 1},
          "to": "graveyard", "reason": "discard"}],                  # owner の var 不正
        [{"op": "move", "select": {"zone": "hand", "owner": "you",
                                   "chooser": {"var": 3}, "count": 1},
          "to": "graveyard", "reason": "discard"}],                  # chooser の var 不正
        [{"op": "choose_player"}],                                   # as が無い
        [{"op": "choose_player", "as": 3}],                          # as は文字列
    )
    for spell in bad_spells:
        with pytest.raises(DefError):
            parse_card({**base, "spell": spell}, TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _defns(e, zone, player=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, player)]


def _drive(e, plan, limit=300):
    """plan: {決定種別: [回答の列, ...]}。回答はキーの列か添字の列（第190弾と同じ）。"""
    plan = {k: list(v) for k, v in plan.items()}
    seen = {}
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return seen
        seen[d["kind"]] = seen.get(d["kind"], 0) + 1
        if d["kind"] in ("main", "attack", "charge") and not any(plan.values()):
            return seen
        keys = _keys(d)
        queue = plan.get(d["kind"])
        if queue:
            want = queue.pop(0)
            ans = [keys.index(w) if isinstance(w, str) else w for w in want]
            e.answer(sorted(set(ans)))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("drive did not finish")


def test_choose_you_shuffles_own_graveyard(rules):
    """T469: 自分を選ぶと自分の墓地が山札に戻る。相手の墓地はそのまま（判別）。"""
    e = setup(rules, {"hand": ["T469"], "mana": ["T030", "T030", "T030"],
                      "graveyard": ["T001", "T001"]},
              {"graveyard": ["T001"]}, filler="T002")
    _drive(e, {"main": [["play:T469"]], "choose_player": [["you"]]})
    assert _defns(e, "graveyard", 0) == []
    assert _defns(e, "deck", 0).count("T001") == 2
    assert len(_defns(e, "graveyard", 1)) == 1


def test_choose_opp_shuffles_opp_graveyard(rules):
    """T469: 相手を選ぶと相手の墓地が山札に戻る。自分の墓地はそのまま（判別）。
    駆動は相手ターンのチャージ決定まで進むため、相手のターン開始ドローで
    山札→手札に移った分も合わせて数える。"""
    e = setup(rules, {"hand": ["T469"], "mana": ["T030", "T030", "T030"],
                      "graveyard": ["T001", "T001"]},
              {"graveyard": ["T001"]}, filler="T002")
    _drive(e, {"main": [["play:T469"]], "choose_player": [["opp"]]})
    assert _defns(e, "graveyard", 1) == []
    moved = _defns(e, "deck", 1).count("T001") + _defns(e, "hand", 1).count("T001")
    assert moved == 1, "相手の墓地の1枚が相手の山札（＋開始ドローで手札）にある"
    assert len(_defns(e, "graveyard", 0)) == 2


def test_spell_draw_and_discard_by_chosen_player(rules):
    """T470: 選んだプレイヤーが2枚引いて1枚捨てる（捨てる札はそのプレイヤーが選ぶ）。"""
    e = setup(rules, {"hand": ["T470"], "mana": ["T030", "T030", "T030"]},
              {"hand": ["T001"]})
    _drive(e, {"main": [["play:T470"]], "choose_player": [["opp"]]})
    # 駆動は相手ターンのチャージ決定まで進むので、相手の手札は開始ドロー込み
    assert len(_defns(e, "hand", 1)) == 3, "相手: 1+2-1（捨てた）+1（ターン開始ドロー）"
    assert len(_defns(e, "graveyard", 1)) == 1, "捨てた1枚が墓地にある"
    assert _defns(e, "hand", 0) == []
    e2 = setup(rules, {"hand": ["T470"], "mana": ["T030", "T030", "T030"]},
               {"hand": ["T001"]})
    _drive(e2, {"main": [["play:T470"]], "choose_player": [["you"]]})
    assert len(_defns(e2, "hand", 0)) == 1, "自分: 0+2-1"
    assert sorted(_defns(e2, "graveyard", 0)) == ["T001", "T470"], \
        "捨てた1枚＋解決後に墓地へ行った呪文自身"
    assert len(_defns(e2, "hand", 1)) == 2, "相手は無関係（初期1枚＋ターン開始ドロー1枚）"


def test_may_choose_player_graveyard_under_deck(rules):
    """T471: 「選んでもよい」→ may の中で選ぶ。相手の墓地が山札の下へ。"""
    e = setup(rules, {"hand": ["T471"], "mana": ["T001", "T001", "T001"]},
              {"graveyard": ["T003", "T003"]}, filler="T002")
    _drive(e, {"main": [["play:T471"]], "yes_no": [["yes"]],
               "choose_player": [["opp"]]})
    assert _defns(e, "graveyard", 1) == []
    deck1 = _defns(e, "deck", 1)
    assert deck1[-2:] == ["T003", "T003"], "墓地の2枚が山札の下に置かれている"


def test_may_decline_keeps_graveyard(rules):
    """T471: may を辞退すると何も起きない（対照）。"""
    e = setup(rules, {"hand": ["T471"], "mana": ["T001", "T001", "T001"]},
              {"graveyard": ["T003", "T003"]}, filler="T002")
    _drive(e, {"main": [["play:T471"]], "yes_no": [["no"]]})
    assert len(_defns(e, "graveyard", 1)) == 2


def test_pick_from_chosen_players_graveyard(rules):
    """T472: 選んだプレイヤーの墓地から1枚選んで持ち主の山札の下へ。引く。"""
    e = setup(rules, {"hand": ["T472"], "mana": ["T005", "T005", "T005"],
                      "graveyard": ["T001"]},
              {"graveyard": ["T003"]}, filler="T002")
    _drive(e, {"main": [["play:T472"]], "choose_player": [["opp"]],
               "choose_cards": [[0]]})
    assert _defns(e, "graveyard", 1) == []
    assert _defns(e, "deck", 1)[-1] == "T003"
    assert len(_defns(e, "hand", 0)) == 1, "選んだら1ドロー"
    assert len(_defns(e, "graveyard", 0)) == 1, "自分の墓地はそのまま"


def test_pick_nothing_no_draw(rules):
    """T472: 墓地のカードを選ばなければ引かない（対照）。"""
    e = setup(rules, {"hand": ["T472"], "mana": ["T005", "T005", "T005"]},
              {"graveyard": ["T003"]}, filler="T002")
    _drive(e, {"main": [["play:T472"]], "choose_player": [["opp"]],
               "choose_cards": [[]]})
    assert len(_defns(e, "graveyard", 1)) == 1
    assert _defns(e, "hand", 0) == []
