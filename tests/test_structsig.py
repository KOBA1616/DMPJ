"""structsig（dmsim/discovery/structsig.py）の純粋ロジックのテスト。ルール読み込みはしない。"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.discovery import structsig  # noqa: E402
from dmsim.engine.zone_graph import Bundle, Move, Premise  # noqa: E402


def _bundle(prem, moves, once=False):
    b = Bundle("x", "x", prem, moves)
    b.once = once
    return b


def test_interceptor_xenarch():
    # XENARCH 本人: 墓地で「自分の札が手札→墓地」を受け、自分を墓地→手札に戻す
    b = _bundle(Premise("move", "graveyard", "hand", {"owner": "you"}, None, "graveyard"),
                [Move("graveyard", "hand", True)])
    assert structsig.interceptor_kind(b) == "self_return"


def test_interceptor_variants():
    bz = _bundle(Premise("move", "graveyard", "hand", "self", None, "graveyard"),
                 [Move("graveyard", "bz", True)])
    assert structsig.interceptor_kind(bz) == "self_return_bz"
    any_src = _bundle(Premise("move", "graveyard", None, {"owner": "you"}, None, "graveyard"),
                      [Move("graveyard", "hand", True)])
    assert structsig.interceptor_kind(any_src) == "any_source_self_return"


def test_interceptor_rejects():
    # ブラックXENARCH の墓地の束: ターン終了前提で自分を場へ（傍受ではない）
    black = _bundle(Premise("turn_end", None, None, "self", None, "graveyard"),
                    [Move("graveyard", "bz", True)])
    assert structsig.interceptor_kind(black) is None
    # ターン1回制限は同一ターン内の多周回に追随できない
    once = _bundle(Premise("move", "graveyard", "hand", {"owner": "you"}, None, "graveyard"),
                   [Move("graveyard", "hand", True)], once=True)
    assert structsig.interceptor_kind(once) is None
    # 相手の札の移動では発火しない
    opp = _bundle(Premise("move", "graveyard", "hand", {"owner": "opp"}, None, "graveyard"),
                  [Move("graveyard", "hand", True)])
    assert structsig.interceptor_kind(opp) is None
    # 場で働く能力は墓地の傍受にならない
    on_bz = _bundle(Premise("move", "graveyard", "hand", {"owner": "you"}, None, "bz"),
                    [Move("graveyard", "hand", True)])
    assert structsig.interceptor_kind(on_bz) is None


def _saga_card():
    return SimpleNamespace(types=["creature"], races=["ゴッド", "オリジン"], cost=3,
                           civs=["water", "darkness"])


def _saga_bundle(with_self_gy=True, flt=None):
    moves = [Move("deck", "hand", False, draw=True),
             Move("hand", "graveyard", False),
             Move("graveyard", "bz", False, flt or {"types": ["creature"],
                                                    "races": ["ゴッド", "オリジン"],
                                                    "cost_le": 5})]
    if with_self_gy:
        moves.append(Move("bz", "graveyard", True))
    return _bundle(Premise("move", "bz", None, "self", None, "bz"), moves)


def test_saga_like_strict():
    h = structsig.saga_like(_saga_bundle(), _saga_card())
    assert h is not None and h["tier"] == "strict" and h["self_ok"]


def test_saga_like_tiers():
    h = structsig.saga_like(_saga_bundle(with_self_gy=False), _saga_card())
    assert h is not None and h["tier"] == "no_self_gy"
    alien = SimpleNamespace(types=["creature"], races=["エイリアン"], cost=3, civs=["darkness"])
    h2 = structsig.saga_like(_saga_bundle(), alien)
    assert h2 is not None and h2["tier"] == "no_self" and not h2["self_ok"]


def test_saga_like_rejects_router():
    # draw＋discard だけ（蘇生なし）は自己回帰の配線ではない
    b = _bundle(Premise("move", "bz", None, "self", None, "bz"),
                [Move("deck", "hand", False, draw=True), Move("hand", "graveyard", False)])
    assert structsig.saga_like(b, _saga_card()) is None


def test_filter_matches():
    card = _saga_card()
    assert structsig._filter_matches({}, card)
    assert structsig._filter_matches({"cost_le": 5}, card)
    assert not structsig._filter_matches({"cost_le": 2}, card)
    assert not structsig._filter_matches({"races": ["ドラゴン"]}, card)
