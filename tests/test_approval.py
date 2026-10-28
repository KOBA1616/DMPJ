import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import auto_approve as aa  # noqa: E402
from dmsim import approval as ap  # noqa: E402
from dmsim.defs import DATA, load_tables  # noqa: E402

CARD = {"id": "dm01-s01", "name": "x", "types": ["creature"], "civs": ["light"], "cost": 3, "power": 1000,
        "keywords": ["blocker"], "text": "ブロッカー",
        "source": {"official": "dm01-s01", "review": "pending", "notes": "ルールのみで変換（モデル不使用）"}}


def _files(tmp_path, card):
    f = tmp_path / "c.yaml"
    f.write_text(yaml.safe_dump({"cards": [card]}, allow_unicode=True), encoding="utf-8")
    return [f, DATA / "cards" / "proto.yaml"]


def test_def_hash_ignores_review_only():
    a = ap.def_hash(CARD)
    b = {**CARD, "source": {**CARD["source"], "review": "approved", "review_note": "ok"}}
    assert ap.def_hash(b) == a
    assert ap.def_hash({**CARD, "cost": 4}) != a


def test_auto_approve_then_invalidate(tmp_path):
    files = _files(tmp_path, CARD)
    led = tmp_path / "a.json"
    st = aa.run(files[:1], ledger_path=led, rule_files=files)
    assert st["approved"] == 1 and ap.load(led)["dm01-s01"]["by"] == "rule"
    assert aa.run(files[:1], ledger_path=led, rule_files=files)["approved"] == 0   # 承認済みは触らない
    files = _files(tmp_path, {**CARD, "cost": 4})                                  # 定義が変わると承認が戻る
    st = aa.run(files[:1], ledger_path=led, rule_files=files)
    assert st["invalidated"] == 1 and st["approved"] == 1


def test_vocab_change_invalidates_only_users():
    raw = CARD
    v = ap.vocab_versions(load_tables())
    e = ap.entry(raw, "approved", "rule", v)
    assert ap.stale_reason(e, raw, v) is None
    v2 = {**v, "kw:blocker": "changed"}
    assert ap.stale_reason(e, raw, v2) == "語彙の定義が変わった"
    assert ap.stale_reason(e, raw, {**v, "kw:double_breaker": "x"}) is None


def test_split_cards_roundtrip(tmp_path):
    import split_cards
    from dmsim.cardfiles import card_files
    src = tmp_path / "converted.yaml"
    cards = [{**CARD, "id": "dm01-s01"}, {**CARD, "id": "dm01-s02"}, {**CARD, "id": "dm02-001"}]
    src.write_text(yaml.safe_dump({"cards": cards}, allow_unicode=True), encoding="utf-8")
    assert split_cards.split(src) == {"dm01": 2, "dm02": 1}
    src.unlink()
    got = [c["id"] for f in card_files(tmp_path) for c in yaml.safe_load(f.read_text(encoding="utf-8"))["cards"]]
    assert got == ["dm01-s01", "dm01-s02", "dm02-001"]
