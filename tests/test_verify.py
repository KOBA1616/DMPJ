"""一括検証ハーネス（dmsim.verify）の検査。"""
from dmsim.engine.verify import greedy_policy, verify_all, verify_card


def test_verify_all_real_cards_run_without_error(rules):
    """real.yaml の全カードが「試す」シナリオで例外なく数百手回せること。"""
    res = verify_all(rules, steps=200)
    assert res, "results are empty"
    bad = [r for r in res if r["status"] != "ok"]
    assert not bad, f"failed cards: {[(r['id'], r['detail'][:120]) for r in bad]}"


def test_verify_card_reports_error(rules):
    """存在しないカードはエラーとして報告すること（握り潰さない）。"""
    r = verify_card(rules, "no-such-card")
    assert r["status"] == "error" and "no-such-card" in r["detail"]


def test_greedy_policy_avoids_pass_when_playable(rules):
    """main で出せるカードがあれば pass ではなくそれを選ぶ。"""
    from tests.conftest import setup
    e = setup(rules, {"hand": ["dm01-080", "dm01-080"], "mana": ["dm01-080", "dm01-080", "dm01-080"]})
    d = e.advance()          # charge: 1枚目をチャージして main へ
    a = greedy_policy(e, d)
    assert [d["options"][i]["key"] for i in a] == ["charge:dm01-080"]
    e.answer(a)
    d = e.advance()          # main（2枚目は play できる）
    assert d["kind"] == "main"
    a = greedy_policy(e, d)
    keys = [d["options"][i]["key"] for i in a]
    assert keys and keys[0].startswith("play:")
