"""語彙パイロット第147弾: distinct 選択モード（「コストが異なる」選択の制約）。

セレクタの新キー2つ。土台は第38弾の積み上げ選択（total_cost_le/ge）と、ハイパーエナジー支払い
（turn.py）の「使用済みコストを候補から外す」述語。解釈はユーザー決定（2026-11-08）で確定済み:
- 型1（distinct_from: <セレクタ>）: 候補のコストが参照集合のコストと重ならない。参照集合は
  選択開始時に1回だけ評価する（＝出す前の場）。選んだカード同士のコスト重複は可。
- 型2（distinct_costs: true）: 選んだカード同士すべて異なるコスト。積み上げ分岐の _fits 述語で表す。
- 型3（型2＋count の {distinct_cost_count} 式）: 当てはまるものをすべて出す（公式QA 31610）。
  can_stop は distinct の時だけ必要数（need）に達するまで止められない。登場は op move の
  既存の逐次処理（409.1e）に乗り、「出た時」は全員出終わるまで待機する（公式QA 31611）。
進化クリーチャーの重ね出しは本弾では扱わない（設計ノート §5-1 の (a)）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _rule_card(cid):
    with open(Path(__file__).parent / "rule_cards.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _by_defn(e, zone, p):
    return {e.cdef(c).id: c for c in e.zlist(zone, p)}


# ---------- parse ----------

def test_distinct_select_parses():
    t180 = parse_card(_proto_card("T180"), TABLES)
    assert t180.abilities[0]["effect"][0]["select"]["distinct_costs"] is True
    t181 = parse_card(_proto_card("T181"), TABLES)
    sel = t181.abilities[0]["effect"][1]["select"]
    assert sel["distinct_from"] == {"zone": "bz", "owner": "you", "filter": {"types": ["creature"]}}
    t182 = parse_card(_proto_card("T182"), TABLES)
    sel = t182.abilities[0]["effect"][0]["body"][0]["select"]
    assert sel["distinct_costs"] is True and "distinct_cost_count" in sel["count"]
    assert parse_card(_rule_card("R105"), TABLES) is not None


def test_distinct_validation():
    """distinct 系は count 併記が必須で、count: all 単独は不可。distinct_costs は true のみ。"""
    base = {"id": "test-dist", "name": "試験", "types": ["creature"], "civs": ["fire"],
            "cost": 3, "power": 3000, "races": ["テスト"], "text": "",
            "source": {"official": "test-dist", "review": "pending"}}

    def card(sel):
        return dict(base, abilities=[{"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
                                      "effect": [{"op": "move", "select": sel, "to": "hand", "reason": "return"}]}])

    gy = {"zone": "graveyard", "owner": "you", "filter": {"types": ["creature"]}}
    with pytest.raises(DefError):   # count が無い
        parse_card(card(dict(gy, distinct_costs=True)), TABLES)
    with pytest.raises(DefError):   # distinct_costs は true のみ
        parse_card(card(dict(gy, count="any", distinct_costs=False)), TABLES)
    with pytest.raises(DefError):   # count: all 単独は「選んだことにならない」
        parse_card(card(dict(gy, count="all", distinct_from={"zone": "bz", "owner": "you"})), TABLES)
    with pytest.raises(DefError):   # distinct_from の中身もセレクタとして検証される
        parse_card(card(dict(gy, count="any", distinct_from={"zone": "nowhere"})), TABLES)
    # count: all + up_to: true は any 相当の選択になるので許す
    parse_card(card(dict(gy, count="all", up_to=True, distinct_costs=True)), TABLES)
    # distinct_from と total_cost_le の合成も検証を通る（設計 §6 (6)）
    parse_card(card(dict(gy, count="any", total_cost_le=10,
                         distinct_from={"zone": "bz", "owner": "you"})), TABLES)


# ---------- 実挙動: 型2 ----------

def _play_t180(e, choose):
    """T180 を手札から召喚し、出た時の選択（choose_cards）を choose(e, d) で答える。"""
    st = {"played": False, "asks": 0}
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "choose_cards" and st["played"]:
            st["asks"] += 1
            choose(e, d)
        elif kind == "main" and "play:T180" in keys and not st["played"]:
            st["played"] = True
            e.answer([keys.index("play:T180")])
        elif kind == "pay_mana":
            e.answer([0])
        elif kind == "attack":
            e.answer([keys.index("pass")])
            break
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return st


def test_type2_distinct_costs_selection(rr):
    """(1)(2) 型2: コスト3は1枚までしか選べず、残りが重複コストだけになったら自動で終わる。"""
    e = setup(rr, {"hand": ["T180"], "mana": ["T005"] * 5,
                   "graveyard": ["T004", "T005", "T019"]}, {})
    gy = _by_defn(e, "graveyard", 0)
    picks = [gy["T019"], gy["T004"]]   # コスト5 → コスト3 の順に選ぶ

    def choose(e, d):
        want = picks.pop(0)
        idx = [i for i, o in enumerate(d["options"]) if o["cid"] == want]
        assert idx, "選ぶはずのカードが候補に無い"
        e.answer(idx[:1])

    st = _play_t180(e, choose)
    assert st["asks"] == 2                                # 3回目の ask は出ない（自動で終わる）
    hand = [d for d in _defns(e, "hand", 0) if d != "T001"]   # T001 はターン開始時のドロー（filler）
    assert hand == ["T004", "T019"]                       # 選んだ2枚が手札へ
    assert _defns(e, "graveyard", 0) == ["T005"]          # 重複コストの T005 は残る


def test_type2_can_stop_at_zero(rr):
    """(1) 型2: 「好きな数」なので0枚で止められる。"""
    e = setup(rr, {"hand": ["T180"], "mana": ["T005"] * 5,
                   "graveyard": ["T004", "T019"]}, {})

    def choose(e, d):
        assert d["min"] == 0
        e.answer([])

    st = _play_t180(e, choose)
    assert st["asks"] == 1
    hand = [d for d in _defns(e, "hand", 0) if d != "T001"]   # T001 はターン開始時のドロー（filler）
    assert hand == []
    assert _defns(e, "graveyard", 0) == ["T004", "T019"]


# ---------- 実挙動: 型1 ----------

def test_type1_distinct_from(rr):
    """(3) 型1: 自分の場のコストと重なる候補は最初から出ない。選んだ同士の重複は可。"""
    e = setup(rr, {"bz": ["T181", "T084"], "deck": ["T043", "T019", "T038"]}, {})
    z = e.s.zones["deck"][0]   # 山札の上3枚を [T043, T019, T038] に固定する（上＝先頭）
    tops = []
    for defn in ("T043", "T019", "T038"):
        cid = next(c for c in z if e.s.cards[c].defn == defn)
        z.remove(cid)
        tops.append(cid)
    e.s.zones["deck"][0] = tops + z

    seen = {"checked": False}
    for _ in range(300):
        d = e.advance()
        if d is None:
            break
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "attack" and "attack:T181:player" in keys:
            e.answer([keys.index("attack:T181:player")])
        elif kind == "choose_cards":
            # 自分の場は T181（コスト7）と T084（コスト4）。コスト4の T043 は候補に出ない
            assert sorted(e.s.cards[o["cid"]].defn for o in d["options"]) == ["T019", "T038"]
            seen["checked"] = True
            e.answer(list(range(len(d["options"]))))   # コスト5を2枚とも選ぶ（同士の重複は可）
        elif kind in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif kind == "charge":
            break   # 相手のターンに入った＝この攻撃は終わった（次のターンの選択に触れない）
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert seen["checked"]
    assert "T019" in _defns(e, "bz", 0) and "T038" in _defns(e, "bz", 0)   # 2枚とも出た
    assert _defns(e, "graveyard", 0) == ["T043"]                            # 残りは墓地へ


# ---------- 実挙動: 型3 ----------

_GY8 = ["T009", "T001", "T004", "T005", "R105", "T019", "T021", "T020", "T052"]   # コスト1〜8＋コスト3の重複1枚


def _drive_to_turn_end(e, on_choose=None, on_yes_no=None):
    """自分のターンの終わりまで進める。choose_cards / yes_no はコールバックで答える。"""
    st = {"asks": 0, "yes_no": 0, "mins": []}
    for _ in range(500):
        d = e.advance()
        if d is None:
            break
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "choose_cards":
            st["asks"] += 1
            st["mins"].append(d["min"])
            if on_choose:
                on_choose(e, d, st)
            else:
                e.answer(list(range(d["min"])))
        elif kind == "yes_no":
            st["yes_no"] += 1
            e.answer([keys.index("yes") if (on_yes_no is None or on_yes_no()) else keys.index("no")])
        elif kind == "charge" and d["player"] == 1:
            break   # 相手のターンに入った＝自分のターンは終わった
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return st


def test_type3_all_costs_enter_and_triggers_wait(rr):
    """(4)(5) 型3: 8種すべてを1体ずつ選んで出し（途中で止められない）、出てくる順は選んだ順。

    「出た時」の待機（QA 31611）: 最初に選んだ R105 の出た時能力は、全員が出終わった後に
    解決されるため、最後に出た T052 も選択肢に含まれる。
    """
    e = setup(rr, {"bz": ["T182"], "graveyard": list(_GY8)}, {})
    gy = _by_defn(e, "graveyard", 0)
    order = ["R105", "T009", "T001", "T004", "T019", "T021", "T020", "T052"]
    picks = [gy[d] for d in order]
    state = {"etb_pick": False}

    def on_choose(e, d, st):
        if st["asks"] <= 7:
            want = picks.pop(0)
            idx = [i for i, o in enumerate(d["options"]) if o["cid"] == want]
            assert idx, "選ぶはずのカードが候補に無い"
            e.answer(idx[:1])
        else:
            # R105 の出た時: 最後に出た T052 が選択肢にある＝全員出終わるまで待機していた
            idx = [i for i, o in enumerate(d["options"]) if o["cid"] == gy["T052"]]
            assert idx, "最後に出た T052 が R105 の選択肢に無い（待機していない）"
            state["etb_pick"] = True
            e.answer(idx[:1])

    st = _drive_to_turn_end(e, on_choose=on_choose)
    assert st["yes_no"] == 1
    # 選択の ask は7回（すべて min 1＝必要数に達するまで止められない）。8枚目（T052）は候補が
    # 1枚だけになるため ask の一意自動決定で選ばれ、決定としては現れない。8回目の ask は R105 の出た時
    assert st["asks"] == 8
    assert st["mins"][:7] == [1] * 7
    assert state["etb_pick"]
    entered = [e.cdef(c).id for c in e.zlist("bz", 0) if e.cdef(c).id != "T182"]
    assert entered == order[:-1]              # 選んだ順に出て、T052 だけ R105 の効果で手札へ
    assert _defns(e, "hand", 0) == ["T052"]
    assert _defns(e, "graveyard", 0) == ["T005"]   # 重複コストの片方は残る


def test_type3_not_enough_distinct_costs(rr):
    """(4) 型3: 異なるコストが7種では発動しない。"""
    gy7 = ["T009", "T001", "T004", "T005", "T019", "T021", "T020", "T052"]   # 種類数は7（コスト3が2枚）
    e = setup(rr, {"bz": ["T182"], "graveyard": gy7}, {})
    st = _drive_to_turn_end(e)
    assert st["yes_no"] == 0 and st["asks"] == 0
    assert _defns(e, "graveyard", 0) == sorted(gy7)
    assert _defns(e, "bz", 0) == ["T182"]
