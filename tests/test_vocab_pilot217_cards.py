"""第217弾の登録カード（ラウンド253）の確認。

- 5枚が converted.yaml の登録形で parse できる（dm25ex4-s02 / dm26ex4-015 /
  dm26ex4-018 は本文の超次元条項が範囲外のため差し戻し）
- dm24ex3-rp3001 正義の逆転撃: 攻撃時に無料で唱えて1ドロー、次の自分の
  ターンのはじめに {ll03}（合計3・光2枚）を払う
- dm24ex3-rp3007 伝説の逆転撃: 選んだ2体をバトルさせ、次の自分のターンの
  はじめに {ff02}（合計2・火2枚）を払う
- dm26ex3-032 深淵の逆転撃: 相手クリーチャーのパワーを -∞ して破壊し、
  支払い（[dd03]）ができなければ次の自分のターンのはじめに負ける
"""
import os
from pathlib import Path

import pytest

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.scenario import build  # noqa: E402
import tests._conv_cache as _conv_cache  # noqa: E402

TABLES = load_tables()
CONVERTED = Path(__file__).parent.parent / "data" / "cards" / "converted.yaml"
IDS = ("dm24ex3-rp3001", "dm24ex3-rp3003", "dm24ex3-rp3007",
       "dm24ex3-rp3009", "dm26ex3-032")


@pytest.fixture(scope="module")
def converted():
    return {c["id"]: c for c in _conv_cache.all_cards(str(CONVERTED))}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_build_forms_parse(converted):
    for cid in IDS:
        assert cid in converted, cid
        parse_card(converted[cid], TABLES)


def _run(e, attack_turns=(2,), stop_turn=None, max_iter=900):
    """P1 が attack_turns にプレイヤー攻撃し、P0 の declare はすべて使う。"""
    log = []
    for _ in range(max_iter):
        if e.s.result is not None:
            break
        if stop_turn is not None and e.s.turn > stop_turn:
            break
        d = e.advance()
        if d is None:
            break
        kind, p = d["kind"], d.get("player")
        keys = [o["key"] for o in d["options"]]
        log.append((e.s.turn, kind, p, tuple(keys)))
        if kind == "declare_attack" and p == 0:
            e.answer([i for i, k in enumerate(keys) if k.startswith("declare:")])
        elif kind == "attack" and p == 1 and e.s.turn in attack_turns:
            k = next(k for k in keys if k.startswith("attack:") and k.endswith(":player"))
            e.answer([keys.index(k)])
        elif kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return log


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _tapped_mana(e, p):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def test_rp3001_casts_and_pays(rules):
    e = build(rules, {"p0": {"hand": ["dm24ex3-rp3001"],
                             "mana": ["T004", "T004", "T001", "T001"]},
                      "p1": {"bz": ["T001"]}, "filler": "T002"})
    _run(e, stop_turn=3)
    assert "dm24ex3-rp3001" in _defns(e, "graveyard", 0)
    assert _tapped_mana(e, 0) == 3   # {ll03}: 合計3・光2枚ぶんをタップ
    assert e.s.result is None


def test_rp3007_battle_and_pays(rules):
    e = build(rules, {"p0": {"hand": ["dm24ex3-rp3007"], "bz": ["T001"],
                             "mana": ["T556", "T556"]},
                      "p1": {"bz": ["T001"]}, "filler": "T002"})
    _run(e, stop_turn=3)
    # 攻撃してきた T001 と自分の T001 がバトルして相打ち（ともにパワー2000）
    assert "T001" in _defns(e, "graveyard", 0)
    assert "T001" in _defns(e, "graveyard", 1)
    assert _tapped_mana(e, 0) == 2   # {ff02}: 合計2・火2枚
    assert e.s.result is None


def test_032_destroys_and_unpaid_loses(rules):
    e = build(rules, {"p0": {"hand": ["dm26ex3-032"],
                             "mana": ["T004", "T004", "T001", "T001"]},
                      "p1": {"bz": ["T001"]}, "filler": "T002"})
    _run(e)
    # パワー -∞ で攻撃クリーチャーは破壊され、闇マナが無いので支払えず敗北
    assert "T001" in _defns(e, "graveyard", 1)
    assert e.s.result is not None and e.s.result["winner"] == 1
