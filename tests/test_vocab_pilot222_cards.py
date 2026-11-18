"""ラウンド258: 第222弾 mana_placement_reveal の登録形テスト。

対象5件（dm26ex2-030 / 031 / 032 / 033 / 035。dm26ex2-046 は誤タグの
ため対象外で rejects に残る）。各カードは (a) 呪文本体と (b) 手札から
マナゾーンに置いた時の公開→アンタップ誘発（zone: hand の move 誘発、
reveal choose、{ref: self_moved} のアンタップ）を持つ。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import scenario  # noqa: E402

IDS = ("dm26ex2-030", "dm26ex2-031", "dm26ex2-032", "dm26ex2-033", "dm26ex2-035")
MANA6 = ["T030", "T030", "T050", "T050", "T060", "T060"]  # 光/水/闇/火をカバー


def _rules():
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _bz(e, p):
    return [e.s.cards[c].defn for c in e.zlist("bz", p)
            if e.s.cards[c].controller == p and e.s.cards[c].top_of < 0]


def _drive(e, handler=None, turns=1, max_steps=500):
    for _ in range(max_steps):
        if e.s.turn > turns:
            break
        d = e.advance()
        if d is None:
            break
        if handler and handler(e, d):
            continue
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return e


def _handler(play=None, picks=(), charge=None):
    state = {"played": False, "charged": False, "picks": list(picks)}

    def h(e, d):
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "charge" and charge and not state["charged"]:
            for i, k in enumerate(keys):
                if charge in k:
                    state["charged"] = True
                    e.answer([i])
                    return True
            return False
        if kind == "main" and play and not state["played"]:
            for i, k in enumerate(keys):
                if k.startswith("play:" + play):
                    state["played"] = True
                    e.answer([i])
                    return True
            return False
        if kind == "choose_cards" and state["picks"]:
            # 工程の一部は候補1件で自動解決され決定が出ないため、順序固定でなく
            # 「残りの picks のうち候補に現れたもの」を答える
            for want in list(state["picks"]):
                for i, k in enumerate(keys):
                    if want in k:
                        state["picks"].remove(want)
                        e.answer([i])
                        return True
            if d.get("min", 0) == 0:
                e.answer([])
                return True
            return False
        if kind == "yes_no":
            e.answer([0])
            return True
        return False

    return h


def _game(p0, p1=None):
    return scenario.build(_rules(), {"p0": p0, "p1": p1 or {},
                                     "filler": "T002", "seed": 1, "deck_size": 20})


def test_all_five_registered_with_spell_and_trigger():
    rules = _rules()
    for cid in IDS:
        d = rules.cards[cid]
        assert d.spell, cid
        trig = [a for a in d.abilities
                if a.get("kind") == "trigger" and a.get("zone") == "hand"]
        assert trig, cid
        w = trig[0]["when"]
        assert w["event"] == "move" and w["from"] == "hand" and w["to"] == "mana"


def test_030_draw_two_and_bounce_by_hand_count():
    e = _game({"hand": ["dm26ex2-030"], "mana": MANA6},
              {"bz": ["T002", "T201"]})
    _drive(e, _handler(play="dm26ex2-030"))
    assert len(_defns(e, "hand", 0)) == 2          # 2枚引いた
    assert "T002" in _defns(e, "hand", 1)          # コスト2以下は全て戻る
    assert _bz(e, 1) == ["T201"]                   # コスト9は残る


def test_032_destroy_then_put_god_from_graveyard():
    e = _game({"hand": ["dm26ex2-032"], "mana": MANA6,
               "graveyard": ["dm25ex2-013"]},
              {"bz": ["T201"]})
    _drive(e, _handler(play="dm26ex2-032", picks=["dm25ex2-013"]))
    assert "T201" in _defns(e, "graveyard", 1)     # 選んだ相手を破壊
    assert "dm25ex2-013" in _bz(e, 0)              # コスト7<9 のゴッドを出した


def test_032_decline_god_then_draw_two():
    e = _game({"hand": ["dm26ex2-032"], "mana": MANA6}, {"bz": ["T201"]})
    _drive(e, _handler(play="dm26ex2-032"))
    assert "T201" in _defns(e, "graveyard", 1)
    assert len(_defns(e, "hand", 0)) == 2          # 出さなかったので2枚引く


def test_033_mana_put_and_sonic_command_with_blocker():
    mana = ["T030", "T060", "T002", "dm23bd3-016", "T030", "T060"]
    e = _game({"hand": ["dm26ex2-033"], "mana": mana})
    _drive(e, _handler(play="dm26ex2-033", picks=["dm23bd3-016"]))
    assert "dm23bd3-016" in _bz(e, 0)              # マナから出した
    assert len(_defns(e, "mana", 0)) == 6          # 山札上1枚がマナへ（6+1-1）
    cid = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "dm23bd3-016")
    assert "blocker" in e.chars(cid)["keywords"]   # 次の自分のターン開始までブロッカー


def test_035_discard_destroy_and_put_tamaseed():
    e = _game({"hand": ["dm26ex2-035", "T002"],
               "mana": ["T050", "T060", "T002", "T050", "T060", "T002"],
               "graveyard": ["dm22rp1-031"]},
              {"bz": ["T002"]})
    _drive(e, _handler(play="dm26ex2-035", picks=["T002", "dm22rp1-031"]))
    assert "T002" in _defns(e, "graveyard", 0)     # 手札を1枚捨てた
    assert "T002" in _defns(e, "graveyard", 1)     # 捨てた以下コストの相手を破壊
    assert "dm22rp1-031" in _bz(e, 0)              # タマシードを出した


def test_031_look_three_shieldize_hand_graveyard_destroy():
    e = _game({"hand": ["dm26ex2-031"], "mana": MANA6}, {"bz": ["T002"]})
    shields_before = len(_defns(e, "shield", 0))
    _drive(e, _handler(play="dm26ex2-031", picks=["T002", "T002"]))
    assert len(_defns(e, "shield", 0)) == shields_before + 1  # 1枚シールド化
    assert _defns(e, "hand", 0) == ["T002"]                   # 1枚は手札へ
    assert "T002" in _defns(e, "graveyard", 0)                # 1枚は墓地へ
    assert "T002" in _defns(e, "graveyard", 1)                # 墓地以下コストを破壊


def test_030_mana_placement_reveal_untaps():
    # 相手の T582 でチャージがタップで置かれる。公開すればアンタップ。
    e = _game({"hand": ["dm26ex2-030", "dm26ex2-030"]}, {"bz": ["T582"]})
    _drive(e, _handler(charge="dm26ex2-030", picks=["dm26ex2-030"]))
    placed = [e.s.cards[c] for c in e.zlist("mana", 0)
              if e.s.cards[c].defn == "dm26ex2-030"]
    assert len(placed) == 1
    assert placed[0].tapped is False
