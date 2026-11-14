"""雛形: 「このクリーチャーがシールドをブレイクする時、相手はそのシールドを手札に加えるかわりに〈墓地／マナ／山札の下〉に置く」。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import rule_convert  # noqa: E402
import unconverted_report  # noqa: E402,F401  読み込めること

from dmsim.cards.defs import load_tables, parse_card


def _row(text):
    return {"id": "t-001", "name": "試験", "card_type": "クリーチャー", "civilization": "火", "cost": "7",
            "power": "7000", "race": "アーマード・ドラゴン", "mana": "1", "text": text}


@pytest.mark.parametrize("tail,to,pos", [
    ("墓地に置く。", "graveyard", None),
    ("マナゾーンに置く。", "mana", None),
    ("自身の山札の一番下に置く。", "deck", "bottom"),
])
def test_break_replace(tail, to, pos):
    card = rule_convert.convert(_row("W・ブレイカー\nこのクリーチャーが相手のシールドをブレイクする時、相手はそのシールドを手札に加えるかわりに" + tail))
    assert card["keywords"] == ["double_breaker"]
    (ab,) = card["abilities"]
    assert ab["kind"] == "replace" and ab["when"] == {"event": "break", "subject": "self"}
    (op,) = ab["instead"]
    assert op["to"] == to and op["select"] == {"ref": "event.shield", "count": 1} and op.get("position") == pos
    parse_card(card, load_tables())


def test_condition_not_swallowed():
    # 条件つき（シビルカウント等）や続く文がある形は雛形で通さない
    assert rule_convert.convert(_row("このクリーチャーがシールドをブレイクする時、自分のクリーチャーが3体以上あれば、相手はそのシールドを手札に加えるかわりに墓地に置く。")) is None
