"""語彙パイロット第57弾: タップによる代替コスト（alt_cost の do に tap: true）。

「コストを支払うかわりに、自分のクリーチャーをN体タップして、このクリーチャーを召喚してもよい」の形。
alt_cost の do ステップに tap: true を指定でき、ゾーン移動ではなくタップで支払う。
"""
import sys
sys.path.insert(0, '.')
from dmsim import load_rules, scenario
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()


def test_tap_alt_cost_def_valid():
    """alt_cost do ステップの tap: true が parse を通る。"""
    raw = {"id": "T154T", "name": "t", "types": ["creature"], "civs": ["water"],
           "cost": 6, "power": 3000,
           "alt_cost": {"do": [{"zone": "bz", "filter": {"types": ["creature"]},
                                "count": 2, "tap": True}]}}
    parse_card(raw, TABLES)


def test_tap_alt_cost_def_invalid():
    """tap も to もない do ステップはエラー。"""
    raw = {"id": "T154X", "name": "t", "types": ["creature"], "civs": ["water"],
           "cost": 6, "power": 3000,
           "alt_cost": {"do": [{"zone": "bz", "count": 2}]}}
    try:
        parse_card(raw, TABLES)
        assert False, "should raise DefError"
    except Exception:
        pass  # 期待どおり
