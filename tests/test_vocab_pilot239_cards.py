"""第239弾の登録形テスト: break_pre_trigger 再変換（ラウンド275）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["dm26sd1-i001", "dm26sd1-o003", "dm26sd1-s004", "dm23rp1-1b", "dmrp22-019"]


def _game(p0, p1):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                         "deck_size": 20})


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def test_all_registered():
    e = _game({}, {})
    for cid in IDS:
        assert cid in e.rules.cards, cid


def test_o003_shieldize_before_break():
    e = _game({"hand": ["dm26sd1-o003"], "mana": ["T030"] * 6}, {})
    shields0 = len(e.zlist("shield", 0))
    opp0 = len(e.zlist("shield", 1))
    for _ in range(200):
        if len(e.zlist("shield", 0)) == shields0 + 2 and len(e.zlist("shield", 1)) == opp0 - 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:dm26sd1-o003") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:dm26sd1-o003"))])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "attack" and "attack:dm26sd1-o003:player" in keys:
            e.answer([keys.index("attack:dm26sd1-o003:player")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert len(e.zlist("shield", 1)) == opp0 - 2          # パワード・ブレイカー（パワー10000で2枚）
    assert len(e.zlist("shield", 0)) == shields0 + 2      # ブレイクの前に1枚ずつシールド化


def test_1b_saver_grant_protects_dragon():
    # セイバー：ドラゴン（mod gain の replace）が実際に働くか。
    # 1b 自身はアーマード・ドラゴン（付与する側）で、セイバーを持つのはファイアー・バード（T624）
    e = _game({"bz": ["dm23rp1-1b", "T624", "T532"]},
              {"hand": ["T006"], "mana": ["T551"] * 3})
    # T532（ドラゴン、コスト1）を相手が T006 で破壊しようとする → T624 のセイバーが身代わり
    for _ in range(200):
        if "T624" in _defns(e, "graveyard", 0):
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:T006") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T006"))])
        elif d["kind"] == "choose_replacement":
            e.answer([0])    # 置換を使う
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "T532" in _defns(e, "bz", 0)                   # ドラゴンは残る
    assert "T624" in _defns(e, "graveyard", 0)            # セイバーが身代わりになった
