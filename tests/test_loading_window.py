"""デッキとルール語彙の読み込みは窓口（cards.decks.load_deck / cards.defs.load_rule_table）を通る。"""
import re
from pathlib import Path

from dmsim.cards.decks import load_deck, load_deck_doc
from dmsim.cards.defs import load_rule_table

ROOT = Path(__file__).resolve().parent.parent


def test_load_deck_forms_and_relative_path(tmp_path, monkeypatch):
    d = load_deck("data/decks/saga.yaml")
    assert len(d) == 40 and all(isinstance(x, str) for x in d)
    monkeypatch.chdir(tmp_path)       # 実行場所に依らない
    assert load_deck("data/decks/saga.yaml") == d
    assert load_deck(ROOT / "data/decks/saga.yaml") == d
    f = tmp_path / "c.yaml"
    f.write_text("cards: {a: 2, b: 1}\n", encoding="utf-8")
    assert load_deck(f) == ["a", "a", "b"] and load_deck_doc(f)["cards"]["a"] == 2


def test_load_rule_table():
    assert "keywords" in load_rule_table("keywords.yaml") and "zones" in load_rule_table("zones.yaml")


def test_no_direct_yaml_read_of_decks_or_rule_tables():
    allow = {"dmsim/cards/decks.py", "dmsim/cards/defs.py"}
    pats = [re.compile(r"safe_load\([^\n]*\[\"deck\"\]"), re.compile(r"\[\"deck\"\]\s*$", re.M),
            re.compile(r"safe_load\([^\n]*\"rules\"[^\n]*\.yaml"), re.compile(r"safe_load\([^\n]*data/decks")]
    bad = []
    for d in ("dmsim", "tools"):
        for p in (ROOT / d).rglob("*.py"):
            rel = str(p.relative_to(ROOT))
            if rel in allow:
                continue
            t = p.read_text(encoding="utf-8")
            if any(x.search(t) for x in pats[:1] + pats[2:]) or re.search(r"safe_load\(open\([^\n]*decks", t):
                bad.append(rel)
    assert not bad, bad
