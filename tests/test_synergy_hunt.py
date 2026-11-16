"""直接つながる2枚組の発見（dmsim/discovery/synergy_hunt.py）の静的な部分（2026-11-16）。"""
from types import SimpleNamespace as N

from dmsim.discovery import synergy_hunt as SH


def card(**kw):
    base = dict(id="x", name="x", types=["creature"], civs=["fire"], races=[], cost=3, abilities=[], spell=None, faces=None)
    base.update(kw)
    return N(**base)


def test_specific_and_admits():
    assert not SH.specific({"types": ["creature"]})
    assert SH.specific({"races": ["ドラゴン"]}) and SH.specific({"civs": ["fire"], "cost_le": 3})
    b = card(races=["アーマード・ドラゴン"], cost=4)
    assert SH.admits({"race_has": "ドラゴン"}, b) and not SH.admits({"race_has": "ジョーカーズ"}, b)
    assert not SH.admits({"races": ["ドラゴン"], "unknown_key": 1}, b)      # 知らない条件は合わないとみなす
    assert SH.admits({"civs": ["fire"], "cost_le": 4}, b) and not SH.admits({"civs": ["fire"], "cost_le": 3}, b)


def test_links_kinds():
    a = card(abilities=[
        {"kind": "static", "affects": {"owner": "you", "zone": "hand", "filter": {"race_has": "ドラゴン"}}, "mod": {"cost": -1}},
        {"kind": "static", "affects": {"owner": "you", "filter": {"races": ["ドラゴン"]}}, "mod": {"grant": ["speed_attacker"]}},
        {"kind": "trigger", "when": {"event": "attack", "subject": {"owner": "you", "filter": {"races": ["ドラゴン"]}}}, "effect": []},
        {"kind": "trigger", "when": {"event": "put", "subject": "self"},
         "effect": [{"op": "move", "select": {"zone": "hand", "owner": "you", "filter": {"races": ["ドラゴン"]}}, "to": "bz"}]},
    ])
    kinds = sorted(k for k, _ in SH.links(a))
    assert kinds == ["cheat", "grant", "reduce", "trigger"]


def test_strong_from_yaml():
    y = {"screened_attack": [{"enabler": "A", "payoff": "B", "synergy_level1": {"broken": {"main_a": 0.5, "main_b": 0.1}}}]}
    assert SH._strong_from_yaml(y, 0.3) == {"A"}
