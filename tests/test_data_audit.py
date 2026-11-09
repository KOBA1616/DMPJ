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


def test_audit_counts_structural_fields_and_twin_faces():
    """G・ゼロ（free_if）などの構造化特性は効果ありと数える。基準線に text_but_no_effect を戻さない。"""
    base = audit_cards.load_baseline()
    assert not base.get("text_but_no_effect")
    from dmsim.defs import load_rules
    from dmsim.dataaudit import audit_card
    r = load_rules()
    assert "text_but_no_effect" not in audit_card(r, r.cards["dm23ex1-075"])      # G・ゼロ
    assert r.cards["dm26rp3-069"].faces                                            # ツインパクトの呪文側が落ちていない
