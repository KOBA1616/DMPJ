"""第254弾の登録形: attack_limit 3件（ラウンド288）。"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card
from dmsim.scenario import build

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)


def _converted(cid):
    import yaml
    for c in yaml.safe_load(open(CONVERTED))["cards"]:
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def test_registered_forms():
    for cid in ("dm24rp3-061", "dmrp16-015", "dmrp22-014"):
        parse_card(copy.deepcopy(_converted(cid)), TABLES)
    assert _converted("dm24rp3-061")["spell"][0]["op"] == "action_limit"
    assert _converted("dmrp16-015")["spell"][0]["attack"] == 2
    assert _converted("dmrp16-015")["spell"][0]["block"] == 2


def _play_and_pass(e, turns=1):
    """P0 が呪文を唱え、相手のターンが始まるまで進める（攻撃はしない）。"""
    seen_active = e.s.active
    changes = 0
    for _ in range(400):
        if changes >= turns and e.s.active == 1:
            return
        d = e.advance()
        assert d is not None, "game ended"
        if e.s.active != seen_active:
            seen_active = e.s.active
            changes += 1
        keys = [o["key"] for o in d["options"]]
        if any(k.startswith("play:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:"))])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "yes_no":
            e.answer([0])
        else:
            e.answer(list(range(d.get("min", 0))))


def test_registered_musai_limits_attacks_to_two():
    rules = load_rules()
    e = build(rules, {"p0": {"hand": ["dmrp16-015"], "mana": ["T010"] * 5},
                      "p1": {"bz": ["T001", "T002", "T034"], "deck": ["T001"] * 10},
                      "filler": "T001", "seed": 1, "deck_size": 14})
    _play_and_pass(e)
    assert e.s.action_limits, "制限が保留されていない"
    # P1 のターン: 攻撃は2回まで（3回目の攻撃諮問は来ない）
    attacks = 0
    turn = e.s.turn
    for _ in range(500):
        if e.s.turn != turn:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and d.get("player") == 1 and any(k.startswith("attack:") for k in keys):
            attacks += 1
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("attack:") and k.endswith(":player"))])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif d["kind"] == "choose_breaker":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert attacks == 2, attacks
