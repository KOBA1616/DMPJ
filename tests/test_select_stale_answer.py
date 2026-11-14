"""隠れた札を条件で絞る選択で、答えの添字が今の候補の外を指しても落ちないこと（2026-11-14、U・S・A・ELEKI の IndexError）。

公平探索では山札の上など隠れた札の中身が、決定を出した時と答えを当てる時で違うことがある。その時に候補の数が変わり、
古い答えの添字が範囲外になっていた。範囲外の答えは捨てて、今の候補で聞き直す。"""
from dmsim.engine import Engine


def test_out_of_range_answer_is_asked_again(rules):
    eng = Engine.new_game(rules, [["T001"] * 40, ["T001"] * 40], 1, 0)
    eng.advance()
    sel = {"zone": ["hand", "deck"], "from_top": 1, "owner": "you", "filter": {}, "count": 1}
    env = {"you": 0, "vars": {}}
    n = len(eng.candidates(sel, env))
    t = {"t": "effect", "answer": [n + 3]}
    got, d = eng.select(t, sel, env)
    assert got is None and d["kind"] == "choose_cards" and len(d["options"]) == n
    t2 = {"t": "effect", "answer": [0]}
    got, d = eng.select(t2, sel, env)
    assert d is None and len(got) == 1
