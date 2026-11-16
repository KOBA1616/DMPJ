"""mod を持つ常在型は affects を明示する（無いとエンジンは場の全カードに効かせる。#471 オリーブオイルの誤り）。"""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import convert_cards as cc  # noqa: E402
from dmsim.cards.cardfiles import card_files  # noqa: E402


def test_every_static_mod_has_affects():
    bad = []
    for f in card_files():
        for c in (yaml.safe_load(Path(f).read_text(encoding="utf-8")) or {}).get("cards") or []:
            bad += [f"{Path(f).name} {c['id']}: {e}" for e in cc.static_scope_errors(c)]
    assert not bad, "\n".join(bad[:20])


def test_validate_rejects_missing_affects():
    card = {"id": "x", "name": "x", "abilities": [{"kind": "static", "mod": {"deny": ["attack_player"]}}]}
    assert cc.static_scope_errors(card)
    card["abilities"][0]["affects"] = "self"
    assert not cc.static_scope_errors(card)
