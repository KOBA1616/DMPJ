import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import audit_cards
from dmsim.dataaudit import new_violations
from dmsim.defs import _dedupe_abilities


def test_no_new_data_violations():
    """原文と構造化データの食い違いが、基準線（data/audit/baseline.json）より増えていない。"""
    assert audit_cards.main([]) == 0


def test_new_violations_ratchet():
    assert new_violations({"a": ["1", "2"]}, {"a": ["1"]}) == {"a": ["2"]}
    assert new_violations({"a": ["1"]}, {"a": ["1", "2"]}) == {}


def test_dedupe_abilities_removes_exact_duplicates():
    ab = {"kind": "static", "affects": "self", "mod": {"power_when": {"amount": 3000, "when": "attacking"}}}
    raw = {"id": "x", "abilities": [ab, {"kind": "static", "mod": {}}, dict(ab)]}
    _dedupe_abilities(raw)
    assert len(raw["abilities"]) == 2


def test_keyword_annotations_do_not_glue_together():
    """「スレイヤー（注釈）W・ブレイカー」の注釈を除いても2語が1語にくっつかず、キーワードに変換できる（効果が空になった49枚の主因）。"""
    import rule_convert
    row = {"id": "x-1", "name": "試験", "card_type": "クリーチャー", "civilization": "闇", "cost": "7", "power": "8000",
           "race": "ドラゴン", "mana": "1",
           "text": "スレイヤー（このクリーチャーがバトルする時、バトルの後、相手クリーチャーを破壊する）W・ブレイカー（このクリーチャーはシールドを２枚ブレイクする）"}
    card = rule_convert.convert(row)
    assert card is not None and set(card["keywords"]) == {"slayer", "double_breaker"}


def test_audit_counts_structural_fields_and_twin_faces(monkeypatch):
    """converted.yaml（テストでは既定で除外）も含めて、効果が空の札が無い。G・ゼロ等の構造化特性は効果ありと数える。"""
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)
    from dmsim.dataaudit import audit_rules
    from dmsim.defs import load_rules
    r = load_rules()
    found = audit_rules(r)
    assert not found.get("text_but_no_effect"), found.get("text_but_no_effect")
    assert not audit_cards.load_baseline().get("text_but_no_effect")
    assert r.cards["dm26rp3-069"].faces                      # ツインパクトの呪文側が落ちていない


def test_converter_validate_dedupes_abilities():
    """変換器の入口（validate）で同じ能力の二重化を除く。元データ88枚の重複の再発防止。"""
    import convert_cards as cc
    from dmsim.defs import load_tables
    ab = {"kind": "static", "affects": "self", "mod": {"power_when": {"amount": 3000, "when": "attacking"}}}
    raw = {"id": "dup-1", "name": "重複", "types": ["creature"], "civs": ["fire"], "cost": 3, "power": 3000,
           "abilities": [ab, dict(ab)]}
    out = cc.validate(raw, {"id": "dup-1", "name": "重複"}, load_tables())
    assert len(out["abilities"]) == 1
    card = cc.merge_split({"abilities": [dict(ab)]}, {"text": "x"}, ([], "", [dict(ab)]))
    assert len(card["abilities"]) == 1


def test_no_duplicate_abilities_in_converted_data(monkeypatch):
    import dmsim.defs as defs
    monkeypatch.setattr(defs, "REPAIRED", {})       # 他のテストが記録した読み込み時の修復を持ち込まない
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)
    from dmsim.dataaudit import audit_rules
    from dmsim.defs import load_rules
    assert not audit_rules(load_rules()).get("duplicate_ability")
