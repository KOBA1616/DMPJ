"""語彙パイロット第310弾: opt_reduce_then_entry_destroy。

dmrp12-008 帝神龍装 ティーゾリス の残余条項:
「このクリーチャーの召喚コストを２少なくしてもよい。そうしたら、
このターン、このクリーチャーがバトルゾーンに出た時、自分の
クリーチャーを１体破壊する。」

従来の opt_reduce.then は destroy（ターン終了時に自身を破壊）/
deck_bottom_draw（終了時に自身を山札の下へ＋1ドロー）の2形だけで、
「出た時」の破壊は表せなかった（ラウンド299の差し戻し理由）。
本弾は then の第3形 **entry_destroy** を追加する:

- h_play の then 処理で、ターン終了時ではなく
  {event: move, to: bz, subject: self} の遅延誘発を積む。
  遅延誘発の登録（子タスク）は召喚の移動イベントより先に
  処理される（後に積んだタスクが先に動く）ため、出た時の
  照合に間に合う。持続は既定の end_of_turn、once も既定どおり
  （再入場は新しいオブジェクトとして扱い、再誘発しない）。
- 効果は「自分のクリーチャーを1体破壊する」= bz の自軍
  クリーチャー1体を選んで墓地へ（reason: destroy）。
  出た本人も対象に含む（本文に除外指定なし）。

プロト T957（ティーゾリス型: 闇コスト6・opt_reduce
{amount: 2, then: entry_destroy}）で固定する。
"""
import copy

import pytest
import yaml
from tests.conftest import answer, setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()


def _proto(cid):
    import pathlib
    path = pathlib.Path(__file__).parent.parent / "data" / "cards" / "proto.yaml"
    cards = yaml.safe_load(open(path, encoding="utf-8"))
    cards = cards if isinstance(cards, list) else cards["cards"]
    return next(c for c in cards if c["id"] == cid)


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)
            if zone != "bz" or e.s.cards[c].controller == p]


def _tapped_mana(e, p):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def _play(e, *, reduce, destroy=None, done, limit=400):
    """T957 を出し、done() が真になったら止める（ターンを進めると
    マナがアンタップされて支払い枚数を読めなくなるため、状態で止める）。
    destroy は破壊対象の defn 名。"""
    for _ in range(limit):
        if done():
            return True
        d = e.advance()
        if d is None:
            return done()
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and "play:T957" in keys:
            e.answer([keys.index("play:T957")])
            continue
        if d["kind"] == "choose_cards" and "reduce" in keys:
            e.answer([keys.index("reduce" if reduce else "normal")])
            continue
        if d["kind"] == "choose_cards" and destroy is not None:
            idx = next(i for i, o in enumerate(d["options"])
                       if f":{destroy}:" in o["key"])
            e.answer([idx])
            destroy = None
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["min"] == 0:
            e.answer([])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("play did not finish")


def test_entry_destroy_parse_and_validation():
    card = _proto("T957")
    d = parse_card(card, TABLES)
    assert d.cost == 6
    bad = copy.deepcopy(card)
    bad["abilities"][0]["mod"]["opt_reduce"]["then"] = "bogus"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def test_reduce_then_destroy_other(rules):
    """軽減して出すと、出た時に自分のクリーチャー1体を破壊する（他を選べる）。"""
    e = setup(rules, {"hand": ["T957"], "bz": ["T001"],
                      "mana": ["T008", "T001", "T001", "T001"]}, {})
    answer(e, "charge", "pass")
    assert _play(e, reduce=True, destroy="T001",
                 done=lambda: "T001" in _defns(e, "graveyard", 0))
    assert "T957" in _defns(e, "bz", 0)
    assert "T001" in _defns(e, "graveyard", 0)
    assert "T001" not in _defns(e, "bz", 0)
    assert _tapped_mana(e, 0) == 4          # 6 - 2 = 4 枚支払い
    # 遅延誘発は1回だけ: ターン終了時にもう1体破壊したりはしない
    for _ in range(200):
        d = e.advance()
        if d is None or e.s.turn > 1:
            break
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys
                 else list(range(d["min"])))
    assert "T957" in _defns(e, "bz", 0)


def test_reduce_then_destroy_self(rules):
    """対象が本人だけなら本人を破壊する（候補1件は自動決定）。"""
    e = setup(rules, {"hand": ["T957"],
                      "mana": ["T008", "T001", "T001", "T001"]}, {})
    answer(e, "charge", "pass")
    assert _play(e, reduce=True,
                 done=lambda: "T957" in _defns(e, "graveyard", 0))
    assert "T957" in _defns(e, "graveyard", 0)
    assert "T957" not in _defns(e, "bz", 0)
    assert _tapped_mana(e, 0) == 4


def test_normal_play_no_destroy(rules):
    """軽減しなければ出た時の破壊は起きない（全額6枚支払い）。"""
    e = setup(rules, {"hand": ["T957"], "bz": ["T001"],
                      "mana": ["T008", "T001", "T001", "T001", "T001", "T001"]}, {})
    answer(e, "charge", "pass")
    assert _play(e, reduce=False,
                 done=lambda: "T957" in _defns(e, "bz", 0))
    assert "T957" in _defns(e, "bz", 0)
    assert "T001" in _defns(e, "bz", 0)
    assert _defns(e, "graveyard", 0) == []
    assert _tapped_mana(e, 0) == 6
