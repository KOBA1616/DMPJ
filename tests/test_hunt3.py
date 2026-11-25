"""combo_hunt3（dmsim/discovery/hunt3.py）の純粋ロジックのテスト。ルール読み込みはしない。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.discovery.hunt3 import _identity, _reductions, engine_type, pair_conversions3  # noqa: E402


def test_reductions():
    subs = list(_reductions({"a": 2, "b": 1}))
    assert {"a": 1, "b": 1} in subs          # 枚数を減らす
    assert {"b": 1} in subs                  # a を抜く
    assert {"a": 2} in subs                  # b を抜く
    assert list(_reductions({"a": 1})) == [{}]   # 抜くと空


def test_identity_by_delta():
    a = _identity({"delta": {"deck:0": -1, "graveyard:0": 1}, "win_by": None})
    b = _identity({"delta": {"deck:0": -1, "hand:0": 1}, "win_by": None})
    assert a != b                            # 増分が違えば別エンジン（サガ単独 vs サガ+XENARCH）
    assert a == _identity({"delta": {"graveyard:0": 1, "deck:0": -1}, "win_by": None})


def test_engine_type():
    assert engine_type({"deck:0": -1, "graveyard:0": 1}, ["growth"]) == "graveyard"
    assert engine_type({"deck:0": -1, "hand:0": 1}, ["growth"]) == "hand"
    assert engine_type({"mana_untapped:0": 2}, ["growth"]) == "mana"
    assert engine_type({"deck:0": -1}, ["burn"]) == "deck_thin"
    assert engine_type({"deck:1": -2}, ["pressure"]) == "pressure"


def _catalog():
    return [
        {"card": "c1", "name": "墓地特殊勝利", "special_win": True, "cost": 8, "zones": ["graveyard"]},
        {"card": "c2", "name": "手札消費フィニッシャー", "special_win": False, "cost": 3, "zones": ["hand"]},
        {"card": "c3", "name": "無関係な特殊勝利", "special_win": True, "cost": 3, "zones": ["bz"]},
        {"card": "c4", "name": "墓地利用", "special_win": False, "cost": 4, "zones": ["graveyard", "hand"]},
    ]


def test_pair_conversions_graveyard_engine():
    picked = pair_conversions3({"deck:0": -1, "graveyard:0": 1}, ["growth"], _catalog(), limit=2)
    assert picked[0]["card"] == "c1"         # 墓地型エンジンには墓地を使う特殊勝利が先頭
    assert picked[0]["engine_type"] == "graveyard"


def test_pair_conversions_hand_engine():
    picked = pair_conversions3({"deck:0": -1, "hand:0": 1}, ["growth"], _catalog(), limit=2)
    assert picked[0]["engine_type"] == "hand"
    assert picked[0]["card"] == "c2"         # 手札型エンジンには手札を使う候補が先頭（c1 は墓地のみ）
    assert all(p["card"] != "c1" or p["zones"] != ["graveyard"] for p in picked[:1])


def test_pair_conversions_win_engine_needs_none():
    assert pair_conversions3({"deck:1": -1}, ["win"], _catalog()) == []
