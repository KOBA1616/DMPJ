"""combo_hunt3（dmsim/discovery/hunt3.py）の純粋ロジックのテスト。ルール読み込みはしない。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.discovery.hunt3 import (_accum_caps, _accum_stop_reason, _delta_zones,  # noqa: E402
                                   _identity, _laps_estimate, _reductions, engine_type,
                                   pair_conversions3)


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


# --- 蓄積段の停止条件（増分ベクトルから決まる汎用形） ---

_SNAP0 = {"hand": 3, "graveyard": 5, "mana": 5, "deck": 30, "shield": 5, "bz": 0}
_HAND_DELTA = {"deck:0": -1, "hand:0": 1}          # サガ+XENARCH（手札型）
_GY_DELTA = {"deck:0": -1, "graveyard:0": 1}       # サガ単独（墓地型）


def test_delta_zones():
    gained, consumed = _delta_zones(_HAND_DELTA)
    assert gained == {"hand": 1} and consumed == {"deck": 1}
    gained, consumed = _delta_zones({"mana_untapped:0": 2, "deck:1": -1})
    assert gained == {"mana": 2} and consumed == {}    # 相手側の増減は数えない
    assert _delta_zones(None) == ({}, {})


def test_accum_caps():
    assert _accum_caps(_HAND_DELTA, _SNAP0, 12) == {"hand": 3 + 12}
    assert _accum_caps(_GY_DELTA, _SNAP0, 12) == {"graveyard": 5 + 12}
    assert _accum_caps(None, _SNAP0, 12) == {}


def test_laps_estimate():
    snap = {**_SNAP0, "hand": 13, "deck": 20}
    assert _laps_estimate(_HAND_DELTA, _SNAP0, snap) == 10
    snap = {**_SNAP0, "graveyard": 17, "deck": 18}
    assert _laps_estimate(_GY_DELTA, _SNAP0, snap) == 12
    assert _laps_estimate(None, _SNAP0, snap) == 0.0


def test_accum_stop_reason():
    # 周回上限に達したら止める
    snap = {**_SNAP0, "hand": 15, "deck": 18}
    assert _accum_stop_reason(_HAND_DELTA, _SNAP0, snap, 12) == "lap_cap"
    # 減るゾーンがあと2周分まで減ったら止める（周回上限に届いていない局面で確認）
    snap = {**_SNAP0, "hand": 8, "deck": 2}
    assert _accum_stop_reason(_HAND_DELTA, _SNAP0, snap, 40) == "consumed_floor:deck"
    # どちらでもなければ止めない
    snap = {**_SNAP0, "hand": 8, "deck": 25}
    assert _accum_stop_reason(_HAND_DELTA, _SNAP0, snap, 12) is None
    # 増分が無ければ止める理由はない
    assert _accum_stop_reason(None, _SNAP0, _SNAP0, 12) is None
