"""語彙パイロット第224弾: cross_gear_effect（「これをクロスしたクリーチャー」への付与・誘発）。

新規語彙なしのイディオム確認: ホストへの常在付与は affects: crossed（第22弾）、
ホストの攻撃誘発は when subject: crossed（第170弾）。proto T586-T591。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests._conv_cache import proto_card as _proto_card
from tests.conftest import setup


def test_proto_parse():
    t586 = _proto_card("T586")
    assert t586["abilities"][0]["affects"] == "crossed"
    assert t586["abilities"][0]["mod"] == {"power": 9000, "grant": ["powered_breaker"]}
    assert t586["abilities"][1]["when"] == {"event": "attack", "subject": "crossed"}
    assert _proto_card("T587")["free_if"] == {
        "exists": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"]}}}
    assert _proto_card("T588")["abilities"][0]["mod"] == {"power": 2000, "breaks_add": 1}
    for cid in ("T589", "T590", "T591"):
        _proto_card(cid)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _cid(e, p, defn, zone="bz"):
    return next(c for c in e.zlist(zone, p) if e.s.cards[c].defn == defn)


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _cross(e, gear, host, p=0):
    e.s.cards[_cid(e, p, gear)].crossed = e.s.ref(_cid(e, p, host))


def _attack_with(e, host_defn, picks=2, stop_when=None):
    """攻撃ステップまで進め、host_defn でプレイヤーを攻撃し、解決まで進める。"""
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        if stop_when is not None and stop_when(e):
            return
        keys = _keys(d)
        kind = d["kind"]
        atk = f"attack:{host_defn}:player"
        if kind == "attack" and atk in keys:
            e.answer([keys.index(atk)])
            continue
        if e.s.turn > 1:
            return
        if kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif kind == "choose_cards":
            e.answer(list(range(min(d["max"], picks))))
        elif kind == "choose_shields":
            e.answer(list(range(d["min"])))
        elif kind == "yes_no":
            e.answer([0])
        elif kind.startswith("declare"):
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("did not settle")


def test_586_host_power_and_powered_breaker(rules):
    e = setup(rules, {"bz": ["T002", "T586"]}, {}, filler="T001", seed=1)
    host = _cid(e, 0, "T002")
    assert e.chars(host)["power"] == 1000          # クロス前は素のパワー
    _cross(e, "T586", "T002")
    ch = e.chars(host)
    assert ch["power"] == 10000                    # +9000
    assert "powered_breaker" in ch["keywords"]


def test_586_attack_trigger_destroy_and_break(rules):
    e = setup(rules, {"bz": ["T002", "T586"]}, {"bz": ["T060"]},
              filler="T001", seed=1)
    _cross(e, "T586", "T002")
    _attack_with(e, "T002")
    assert "T060" in _defns(e, "graveyard", 1)     # パワーが小さい相手を破壊
    # 誘発のブレイク1＋攻撃のブレイク2（パワード: 10000 → 1+1）= 3枚割れて残り2
    assert len(_defns(e, "shield", 1)) == 2


def test_588_breaks_add_and_mana_burn(rules):
    e = setup(rules, {"bz": ["T201", "T588"]},
              {"mana": ["T001", "T001", "T001"]}, filler="T001", seed=1)
    _cross(e, "T588", "T201")
    ch = e.chars(_cid(e, 0, "T201"))
    assert ch["power"] == 11000 and ch["breaks"] == 2
    _attack_with(e, "T201")
    assert len(_defns(e, "mana", 1)) == 1          # 2枚まで選んで墓地へ
    assert len(_defns(e, "graveyard", 1)) == 2
    assert len(_defns(e, "shield", 1)) == 3        # ブレイク2


def test_589_blocker_grant_and_random_discard(rules):
    e = setup(rules, {"bz": ["T002", "T589"]},
              {"hand": ["T001", "T002", "T006"]}, filler="T001", seed=1)
    _cross(e, "T589", "T002")
    ch = e.chars(_cid(e, 0, "T002"))
    assert ch["power"] == 5000 and "blocker" in ch["keywords"]
    # 誘発（攻撃時）が解決した時点で止める（その後のブレイクで割れたシールドが手札に混ざるため）
    _attack_with(e, "T002", stop_when=lambda e: len(_defns(e, "graveyard", 1)) == 1)
    assert len(_defns(e, "hand", 1)) == 2          # 見ないで1枚捨てさせる
    assert len(_defns(e, "graveyard", 1)) == 1


def test_590_attack_may_draw(rules):
    e = setup(rules, {"bz": ["T002", "T590"]}, {}, filler="T001", seed=1)
    _cross(e, "T590", "T002")
    _attack_with(e, "T002")
    assert len(_defns(e, "hand", 0)) == 1          # 攻撃時に1枚引く


def test_591_attack_may_mana_put(rules):
    e = setup(rules, {"bz": ["T002", "T591"]}, {}, filler="T001", seed=1)
    _cross(e, "T591", "T002")
    _attack_with(e, "T002")
    assert len(_defns(e, "mana", 0)) == 1          # 山札上をマナゾーンへ


def test_587_g_zero_generate(rules):
    e = setup(rules, {"bz": ["T002"], "hand": ["T587"]}, {},
              filler="T001", seed=1)
    for _ in range(60):
        d = e.advance()
        assert d is not None
        keys = _keys(d)
        if d["kind"] == "main":
            play = next((k for k in keys if k.startswith("play:T587")), None)
            assert play is not None, keys            # マナ0でも G・ゼロで出せる
            e.answer([keys.index(play)])
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    for _ in range(60):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "attack"):
            break
        keys = _keys(d)
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "T587" in _defns(e, "bz", 0)
