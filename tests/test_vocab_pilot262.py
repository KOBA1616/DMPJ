"""第262弾: declare group（ニンジャ・チェンジは1回の攻撃に1回まで）。"""
from tests.conftest import setup
from dmsim.cards.defs import load_rules


def _run(e, plan, seen=None, limit=600):
    """plan: {attack_with: defn, block_with: defn|None, declare: bool}
    declare の提示履歴を返す。"""
    if seen is None:
        seen = {"declare_attack": [], "declare_block": []}
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] in seen:
            seen[d["kind"]].append(list(keys))
            hit = next((i for i, k in enumerate(keys) if k.startswith("declare:T706")), None)
            if hit is not None and plan.get("declare", True):
                e.answer([hit])
            else:
                e.answer([])
        elif d["kind"] == "attack":
            atk = next((i for i, k in enumerate(keys)
                        if k.startswith(f"attack:{plan['attack_with']}")), None)
            if atk is not None and e.s.active == plan["attacker"]:
                e.answer([atk])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif d["kind"] == "block":
            bw = plan.get("block_with")
            hit = next((i for i, k in enumerate(keys) if bw and k.startswith(f"bz:{bw}")), None)
            if hit is not None:
                e.answer([hit])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if plan.get("stop") and plan["stop"](e):
            break
    return seen


def _in_bz(e, p, defn):
    return any(e.s.cards[c].defn == defn and e.s.cards[c].controller == p for c in e.zlist("bz", p))


def _in_hand(e, p, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist("hand", p))


def test_defender_ninja_change_on_attack():
    e = setup(load_rules(), {"bz": ["T707"], "hand": ["T706"]}, {"bz": ["T001"]})
    seen = _run(e, {"attack_with": "T001", "attacker": 1,
                    "stop": lambda e: _in_bz(e, 0, "T706")})
    assert _in_bz(e, 0, "T706") and _in_hand(e, 0, "T707")
    assert any(any(k.startswith("declare:T706") for k in ks) for ks in seen["declare_attack"])


def test_ninja_group_once_per_attack():
    # 手札に忍者が2枚あっても、1回の攻撃で使えるのは1枚まで（両方選んでも1枚だけ宣言される）
    e = setup(load_rules(), {"bz": ["T707", "T004"], "hand": ["T706", "T706"]}, {"bz": ["T001"]})
    for _ in range(300):
        if _in_bz(e, 0, "T706"):
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "declare_attack":
            e.answer(list(range(len(keys))))   # 両方選んでみる
        elif d["kind"] == "attack":
            atk = next((i for i, k in enumerate(keys) if k.startswith("attack:T001")), None)
            if atk is not None and e.s.active == 1:
                e.answer([atk])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    ninjas_in_bz = sum(1 for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T706")
    assert ninjas_in_bz == 1 and _in_hand(e, 0, "T706") and _in_hand(e, 0, "T707")


def test_attacker_ninja_change_on_block():
    e = setup(load_rules(), {"bz": ["T707"], "hand": ["T706"]}, {"bz": ["T004"]})
    seen = _run(e, {"attack_with": "T707", "attacker": 0, "block_with": "T004",
                    "stop": lambda e: _in_bz(e, 0, "T706") and not _in_bz(e, 1, "T004")})
    assert any(any(k.startswith("declare:T706") for k in ks) for ks in seen["declare_block"])
    # 入れ替わった忍者が攻撃クリーチャーになり、ブロッカー（3000）を倒す
    assert _in_bz(e, 0, "T706") and _in_hand(e, 0, "T707") and not _in_bz(e, 1, "T004")
