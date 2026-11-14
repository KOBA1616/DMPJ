"""語彙パイロット第200弾のカード適用テスト（登録形＋差し戻し状態）。

ラウンド236: cast_resolution_destination 単独9件を処理した。
- 新規登録3件: dm25ex3-031（resolve_to: mana）、dm24ex3-rp1008
  （resolve_to: deck/bottom）、dm25ex1-021（常在勝利 kind: state）
- 陳腐化クリーンアップ1件: dm24ex3-td04 は real.yaml の dmbd13-010
  （同名・完全な手変換）として登録済みだったため、reject 行の削除のみ
- 精緻化して差し戻し5件: 解けた節は partial に残り、unsupported は
  新ギャップ1件だけになっている
"""
import copy
import json
from pathlib import Path

import yaml

from dmsim.cards import cardstore

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
ROOT = Path(__file__).parent.parent
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"
REAL = ROOT / "data" / "cards" / "real.yaml"

REGISTERED = ("dm25ex3-031", "dm24ex3-rp1008", "dm25ex1-021")
BOUNCED = {"dm25ex2-070": "shield_pile_attach",
           "dm25ex4-s10": "choujigen_shoukan",
           "dm25ex2-103": "cast_destination_conditional",
           "dm25ex4-041": "before_break_cast",
           "dm25ex4-tr11": "hyperdimensional_zone"}


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject(cid):
    for line in open(REJECTS, encoding="utf-8"):
        r = json.loads(line)
        if r["id"] == cid:
            return r
    raise KeyError(cid)


def test_registered_forms():
    for cid in REGISTERED:
        parse_card(copy.deepcopy(_converted(cid)), TABLES)
    c = _converted("dm25ex1-021")
    assert any(a.get("kind") == "state" for a in c["abilities"])


def test_stale_cleanup_td04():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    assert not [r for r in rows if r["id"] == "dm24ex3-td04"]
    real = yaml.safe_load(open(REAL, encoding="utf-8"))
    card = next(c for c in real["cards"] if c["id"] == "dmbd13-010")
    assert card["name"] == "龍素記号Sr スペルサイクリカ"
    assert any("resolve_to" in json.dumps(a) for a in card["abilities"])


def test_bounced_state():
    for cid, gap in BOUNCED.items():
        r = _reject(cid)
        assert r["gaps"] == [gap], cid
        unsup = (r["partial"].get("source") or {}).get("unsupported")
        assert [u["need"] for u in unsup] == [gap], cid
        parse_card(copy.deepcopy(r["partial"]), TABLES)


def test_family_cleared():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    assert not [r for r in rows
                if "cast_resolution_destination" in (r.get("gaps") or [])]
