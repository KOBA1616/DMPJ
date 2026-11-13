"""語彙パイロット第56弾: 条件付き代替コスト（alt_cost の if）。

「〜があれば、このクリーチャーを[コスト]支払って召喚してもよい」の形。
alt_cost に if（条件式）を付けられ、条件成立時のみ :alt の選択肢が提示される。
条件不成立時は通常コストでの召喚のみ。

エンジンの turn.py では、:alt 選択肢の提示時に if 条件を eval_cond で評価し、
不成立なら選択肢を出さない（continue）。
"""
import sys
sys.path.insert(0, '.')
from dmsim import load_rules
from dmsim.engine import scenario


def _setup():
    rules = load_rules()
    e = scenario.build(rules, {"p0": {"bz": ["T001"], "hand": ["T153"], "mana": ["T072", "T072"]},
                               "p1": {}, "filler": "T001",
                               "seed": 1, "deck_size": 20, "deck_left": None})
    cid = e.zlist("hand", 0)[0]
    d = e.cdef(cid)
    env = {"you": 0, "self": e.s.ref(cid), "vars": {}}
    return e, d, env


def test_conditional_alt_cost_available(rules):
    """T153: タップしている自分のクリーチャーがあれば条件が成立する。"""
    e, d, env = _setup()
    assert "if" in d.alt_cost
    for c in e.zlist("bz", 0):
        e.s.cards[c].tapped = True
    assert e.eval_cond(d.alt_cost["if"], env)


def test_conditional_alt_cost_unavailable(rules):
    """T153: タップしている自分のクリーチャーがなければ条件は不成立。"""
    e, d, env = _setup()
    assert "if" in d.alt_cost
    # T001はアンタップ状態
    assert not e.eval_cond(d.alt_cost["if"], env)
