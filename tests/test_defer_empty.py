"""候補が空の play_free（後に回すものが無い _defer）の後でも、続く効果を処理する（暗黒貴族ウノドス・トレス型）。"""
from conftest import setup


def _run(e, ops):
    e.s.tasks.append(e._child(ops, {"you": 0, "self": None, "vars": {}}))
    while (d := e.advance()) is not None and d["kind"] != "main":
        e.answer(list(range(d["min"])))


def test_empty_play_free_does_not_skip_next_op(rules):
    e = setup(rules, {"hand": []}, {})
    n = len(e.zlist("hand", 0))
    _run(e, [{"op": "play_free", "select": {"zone": "graveyard", "owner": "you", "filter": {"types": ["creature"]}, "count": 1}},
             {"op": "draw", "count": 1}])
    assert len(e.zlist("hand", 0)) == n + 1
