"""第261弾: use_entry_abilities / cast_limit / player_rush。"""
from tests.conftest import setup
from dmsim.cards.defs import load_rules


def _drive(e, branches, limit=400):
    for _ in range(limit):
        if branches.get("stop") and branches["stop"](e):
            return True
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        for name, pred, ans in branches["rules"]:
            hit = next((i for i, k in enumerate(keys) if pred(k, d)), None)
            if hit is not None:
                e.answer([hit] if not isinstance(ans, list) else ans)
                break
        else:
            if d["kind"] == "use_entry":
                e.answer([branches.get("use_entry_pick", 0)])
            elif d["kind"] == "yes_no":
                e.answer([0])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
    return branches.get("stop") and branches["stop"](e)


def test_use_entry_abilities_draw():
    # T701 が出た時、相手の T702 の「引く」能力を使うと自分が引く
    e = setup(load_rules(), {"hand": ["T701"], "mana": ["T010"] * 4},
              {"bz": ["T702", "T003"]})
    hand0 = len(e.zlist("hand", 0))
    ok = _drive(e, {"rules": [("play", lambda k, d: k.startswith("play:"), None)],
                    "stop": lambda e: len(e.zlist("hand", 0)) > hand0,
                    "use_entry_pick": 0})
    assert ok


def test_cast_limit_one_per_turn():
    # 相手の場に T703 がいると、呪文は1ターンに1回まで（build はメインが繰り返し聞かれる）
    from dmsim.scenario import build
    e = build(load_rules(), {"p0": {"hand": ["T705", "T705"], "mana": ["T010"] * 3, "deck": ["T001"] * 10},
                             "p1": {"bz": ["T703"], "deck": ["T001"] * 10},
                             "filler": "T001", "seed": 1, "deck_size": 14})
    # 1回唱えた同じターンでは、2枚目が提示されるメインは二度と現れない（提示ゼロでメイン自体が飛ぶ）
    cast_turn = {"t": None}
    offered_after = {"v": False}
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if cast_turn["t"] is not None and e.s.turn > cast_turn["t"]:
            break
        if d["kind"] == "main" and cast_turn["t"] is not None \
                and any(o["key"].startswith("play:T705") for o in d["options"]):
            offered_after["v"] = True
        if any(k.startswith("play:T705") for k in keys) and cast_turn["t"] is None:
            cast_turn["t"] = e.s.turn
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T705"))])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    gy = sum(1 for c in e.zlist("graveyard", 0) if e.s.cards[c].defn == "T705")
    assert cast_turn["t"] is not None and gy == 1 and not offered_after["v"]


def test_player_rush_can_attack_player_on_entry_turn():
    e = setup(load_rules(), {"hand": ["T704"], "mana": ["T007"] * 3}, {"bz": ["T003"]})
    seen = {"player": False, "creature": False, "done": False}
    for _ in range(300):
        if seen["done"]:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if any(k.startswith("play:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:"))])
        elif d["kind"] == "attack":
            seen["player"] = any(k == "attack:T704:player" for k in keys)
            seen["creature"] = any(k.startswith("attack:T704:T") for k in keys)
            seen["done"] = True
            e.answer([keys.index("pass")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert seen["done"] and seen["player"] and not seen["creature"]
