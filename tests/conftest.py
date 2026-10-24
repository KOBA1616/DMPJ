import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim import Engine, load_rules  # noqa: E402


@pytest.fixture(scope="session")
def rules():
    return load_rules()


def setup(rules, p0: dict, p1: dict | None = None, filler="T001", seed=1, deck_size=20, deck_left=None):
    """指定した配置から始まる局面を作る。p0/p1 は {ゾーン名: [カードID,...]}。
    残りの山札は filler で埋める。先攻1ターン目のメインステップ直前（マナチャージの決定）で返す。"""
    p1 = p1 or {}
    decks = []
    for spec in (p0, p1):
        named = [c for z in spec.values() for c in z]
        decks.append(named + [filler] * deck_size)
    e = Engine.new_game(rules, decks, seed)
    s = e.s
    # 準備で配られた手札とシールドを山札に戻し、指定どおりに置き直す
    for p, spec in enumerate((p0, p1)):
        for z in ("hand", "shield"):
            for c in list(s.zones[z][p]):
                e._raw_move(c, "deck")
        pool = list(s.zones["deck"][p])
        for z, ids in spec.items():
            for cid_name in ids:
                cid = next(c for c in pool if s.cards[c].defn == cid_name)
                pool.remove(cid)
                e._raw_move(cid, z, controller=p)
                if z == "bz":
                    s.cards[cid].entered_turn = 0   # 召喚酔いなし
        if "shield" not in spec:
            for _ in range(5):
                c = next(c for c in s.zones["deck"][p] if s.cards[c].defn == filler)
                e._raw_move(c, "shield")
        if deck_left and deck_left[p] is not None:
            for c in list(s.zones["deck"][p])[deck_left[p]:]:
                e._raw_move(c, "graveyard")
    return e


def find_option(d, key):
    keys = [o["key"] for o in d["options"]]
    assert key in keys, f"{key} not in {keys}"
    return keys.index(key)


def answer(e, kind, key):
    d = e.advance()
    assert d is not None and d["kind"] == kind, (d and d["kind"], kind, d and [o["key"] for o in d["options"]])
    e.answer([find_option(d, key)])
    return d
