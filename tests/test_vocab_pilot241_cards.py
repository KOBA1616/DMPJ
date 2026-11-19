"""ラウンド276 登録形: cross_cost_reduction（第241弾）。"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build


def _setup(p0, p1=None):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": "T001", "seed": 1, "deck_size": 20})


def _drive(e, stop, limit=120, attack_with=None):
    for _ in range(limit):
        if stop():
            return True
        d = e.advance()
        if d is None:
            return stop()
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "yes_no":
            e.answer([0])
        elif d["kind"] == "pay_mana":
            sizes = [len(o["key"].split(",")) if o["key"] != "mana:" else 0 for o in d["options"]]
            e.answer([sizes.index(min(sizes))])
        elif any(k.startswith("cross:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("cross:"))])
        elif attack_with and any(k.startswith(f"attack:{attack_with}:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith(f"attack:{attack_with}:"))])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return stop()


def _tapped_mana(e, p=0):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def _cid(e, defn, p=0, zone="bz"):
    return next((c for c in e.zlist(zone, p) if e.s.cards[c].defn == defn), None)


def test_dm17_021_host_reduce():
    e = _setup({"bz": ["dm17-021", "T656"], "mana": ["T002"] * 4})
    ok = _drive(e, lambda: e.s.cards[_cid(e, "T656")].crossed)
    assert ok and _tapped_mana(e) == 1   # 3 - 2（最大軽減） = 1


def test_dm15_016_global_reduce_cross():
    e = _setup({"bz": ["dm15-016", "T656", "T002"], "mana": ["T002"] * 4})
    ok = _drive(e, lambda: e.s.cards[_cid(e, "T656")].crossed)
    assert ok and _tapped_mana(e) == 2   # 3 - 1 = 2


def test_dmc45_009_crossed_attack_trigger():
    e = _setup({"bz": ["dmc45-009", "T201"], "mana": ["T551"] * 3},
               {"bz": ["T002"]})
    host = _cid(e, "T201")
    gear = _cid(e, "dmc45-009")
    assert _drive(e, lambda: e.s.cards[gear].crossed)
    # ホストが攻撃 → パワーが小さい相手クリーチャーを破壊し、ホスト自身も破壊される
    assert _drive(e, lambda: _cid(e, "T002", 1, "graveyard") is not None
                  and host in e.zlist("graveyard", 0), limit=200, attack_with="T201")
