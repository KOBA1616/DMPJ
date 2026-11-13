"""サガの入口への経路: 超神星DOOM・ドラゲリオンの墓地進化（進化元1体につきコスト-1）とメテオバーンでシャコガイルを場に出す。

#410 の「シャコガイルを場に出す道がデッキにない」の訂正。墓地のクリーチャー8体を進化元にすると DOOM はマナ4で出せ、
進化クリーチャーなので出たターンに攻撃でき、メテオバーンで下のシャコガイルを墓地に置いてそのまま墓地から出す。"""
from collections import Counter

import pytest

from dmsim.engine import scenario
from dmsim.eval import loop_entry as L

DOOM, SAGA, IWASHIN, SHAKO, IZANAGI = "dm22ex1-007", "dm22ex2-021", "dmrp03-036", "dmrp03-s03", "dm22ex1-025"


@pytest.fixture(scope="module")
def rules():
    import os
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        return load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old


def _board(rules):
    deck = L.deck_of(L.load("saga"))
    p0 = {"hand": [DOOM, SAGA, IWASHIN],
          "graveyard": [SHAKO, SAGA, SAGA, IWASHIN, IWASHIN, IZANAGI, IZANAGI, IZANAGI],
          "mana": ["dm01-080", "dm01-027", "dmex10-020", "dm01-080"],
          "shield": ["dmex10-020", "dmex10-020", "dm26ex2-071", "dmd08-015", "dm01-027"], "bz": []}
    left = Counter(deck)
    for v in p0.values():
        left.subtract(v)
    p0["deck"] = sorted(left.elements())
    spec = {"p0": p0, "p1": {"hand": ["T001"] * 5, "mana": ["T001"] * 3}, "deck_size": 40,
            "deck_exact": [True, False], "deck_left": [None, 27], "seed": 1}
    return scenario.build(rules, spec, first_player=0)


def _pick(e, prefix, all_=False):
    d = e.s.waiting or e.advance()
    idx = [i for i, o in enumerate(d["options"]) if o["key"].startswith(prefix)]
    assert idx, (prefix, d["kind"], [o["key"] for o in d["options"]])
    e.answer(idx[:d["max"]] if all_ else idx[:max(d["min"], 1)])


def _names(e, zone):
    return [e.s.cards[c].defn for c in e.s.zones[zone][0]]


def test_doom_cheats_shakogail_into_play(rules):
    e = _board(rules)
    _pick(e, "pass")                         # マナチャージしない（マナ4のまま）
    _pick(e, f"play:{DOOM}")                 # コスト12 - 進化元8 = 4
    _pick(e, "graveyard", all_=True)
    e.advance()
    assert DOOM in _names(e, "bz") and not e.s.zones["graveyard"][0]
    _pick(e, f"attack:{DOOM}")               # 進化クリーチャーは出たターンに攻撃できる
    _pick(e, "yes")                          # メテオバーン
    _pick(e, f"bz:{SHAKO}")                  # 下のシャコガイルを墓地へ → 進化でないクリーチャーとして墓地から出す
    e.advance()
    bz = _names(e, "bz")
    assert bz.count(SHAKO) == 1 and bz[-1] == SHAKO, bz


def _board12(rules, mana):
    deck = L.deck_of(L.load("saga"))
    gy = [SHAKO, SAGA, SAGA, SAGA, IWASHIN, IWASHIN, IWASHIN, IWASHIN, IZANAGI, IZANAGI, IZANAGI, IZANAGI]
    p0 = {"hand": [DOOM], "graveyard": gy, "mana": mana,
          "shield": ["dmex10-020", "dmex10-020", "dm26ex2-071", "dmd08-015", "dm01-027"], "bz": []}
    left = Counter(deck)
    for v in p0.values():
        left.subtract(v)
    p0["deck"] = sorted(left.elements())
    spec = {"p0": p0, "p1": {"hand": ["T001"] * 5, "mana": ["T001"] * 3}, "deck_size": 40,
            "deck_exact": [True, False], "deck_left": [None, 27], "seed": 1}
    return scenario.build(rules, spec, first_player=0)


def test_doom_cost_never_below_one(rules):
    """「ただし、コストは0以下にはならない」: 進化元12体でもコストは1（0マナでは出せない）。"""
    e = _board12(rules, [])
    _pick(e, "pass")
    d = e.s.waiting or e.advance()
    assert f"play:{DOOM}" not in [o["key"] for o in d["options"]]
    e = _board12(rules, ["dm01-027"])
    _pick(e, "pass")
    d = e.s.waiting or e.advance()
    assert f"play:{DOOM}" in [o["key"] for o in d["options"]]
