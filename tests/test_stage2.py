"""段2の自動選択: 蓄積（ゾーンの増減）から勝ち手段を索引で引く。札名は決め打ちしない。"""
from dmsim.cards.defs import load_rules
from dmsim.discovery import stage2 as S2


def test_loop_gains_reads_last_lap():
    cert = {"zone_deltas": [{"you": {"deck": -3, "hand": 0}, "opp": {"shield": 0}}, {"you": {"deck": -2, "hand": 1}, "opp": {"shield": -1}}]}
    assert S2.loop_gains(cert) == {("you", "deck"): -2, ("you", "hand"): 1, ("opp", "shield"): -1}
    assert S2.loop_gains({}) == {}


def test_pick_wins_finds_deck_out_win_for_own_deck_loss(monkeypatch):
    """自分の山札が減る蓄積からは、山札を条件にする特殊勝利の札が引かれる（中核に収まる札が先）。"""
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)
    rules = load_rules(only_approved=False)
    core = ["dm25sd1-001", "dm20-013"]
    hits = S2.pick_wins(rules, {("you", "deck"): -3}, core, top=3)
    assert hits and all(h["id"] not in core and "you:deck:-" in " ".join(h["why"]) for h in hits)
