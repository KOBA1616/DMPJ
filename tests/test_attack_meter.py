"""攻撃型の目盛り（dmsim/eval/attack.py）の印と集計（2026-11-14）。"""
from dmsim.eval import attack as A


def test_marks_last_turn():
    log = [
        {"p": 0, "kind": "charge", "keys": ["charge:x"]},
        {"p": 0, "kind": "main", "keys": ["play:a"]},
        {"p": 0, "kind": "pay_mana", "keys": ["mana:x"]},
        {"p": 1, "kind": "charge", "keys": ["charge:y"]},
        {"p": 0, "kind": "charge", "keys": ["charge:x"]},
        {"p": 0, "kind": "main", "keys": ["play:b"]},           # 払わずに出た（踏み倒し）
        {"p": 0, "kind": "attack", "keys": ["attack:b:player"]},  # 出してすぐ攻撃
        {"p": 0, "kind": "attack", "keys": ["attack:a:player"]},
        {"p": 0, "kind": "attack", "keys": ["attack:a:player"]},  # 同じ体の再攻撃
    ]
    m = A.marks(log)
    assert m == {"attacks": 3, "attackers": 2, "haste": 1, "repeat": 1, "played": 1, "free": 1}
    assert A.accumulated(m)


def test_summarize_rates():
    rows = [{"kill_turn": 4, "via": "beat", "opp": "strigger12", "error": None, "marks": {"haste": 1}},
            {"kill_turn": 6, "via": "beat", "opp": "strigger12", "error": None, "marks": {}},
            {"kill_turn": None, "via": None, "opp": "strigger12", "error": None, "marks": {}}]
    s = A.summarize(rows)
    assert s["kill"][4]["k"] == 1 and s["kill"][3]["k"] == 0 and s["dist"][6] == 1 and s["no_kill"] == 1
    assert s["kill"][4]["accumulated"] == 1
