"""chars_scope: 状態を変えない区間だけ chars() を使い回す。古い値を返さないことの検証。"""
import random

from conftest import setup

from dmsim import Engine
from dmsim.engine.play import random_policy, run


def test_scope_returns_same_as_uncached_and_copies(rules):
    e = setup(rules, {"bz": ["T001"], "hand": ["T001"]})
    cid = e.zlist("bz", 0)[0]
    base = e.chars(cid)
    with e.chars_scope():
        a = e.chars(cid)
        a["power"] += 999          # 呼び出し側の書き換えがキャッシュに混ざらない
        a["keywords"].append("x") if isinstance(a["keywords"], list) else a["keywords"].add("x")
        a["deny"].append("junk")
        b = e.chars(cid)
    assert b == base and e.chars(cid) == base


def test_scope_ends_and_sees_changes(rules):
    e = setup(rules, {"bz": ["T001"]})
    cid = e.zlist("bz", 0)[0]
    with e.chars_scope():
        e.chars(cid)
    assert e._chcache is None
    e._raw_move(cid, "graveyard")      # 区間の外では常に再計算する
    assert e.chars(cid)["power"] == e.fdef(cid).power


def test_full_games_with_check_mode(rules):
    """DMSIM_CHECK=1（テスト既定）では使い回した値を毎回再計算と比べる。ランダム対戦を最後まで回して食い違いがないこと。"""
    ids = [c for c in rules.cards if c.startswith("T")]
    assert len(ids) >= 5
    for seed in range(6):
        deck = [ids[(i * 3 + seed) % len(ids)] for i in range(40)]
        e = Engine.new_game(rules, [deck, deck], seed)
        assert e.check
        pol = random_policy(random.Random(seed))
        run(e, [pol, pol])
