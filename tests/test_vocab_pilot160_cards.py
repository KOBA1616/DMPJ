"""語彙パイロット第160弾: first_attack_taunt の対象1件の検証（再変換ラウンド196で登録）。

dm26sd1-m001 アビスベル＝覇＝ロード: ラウンド195で途中まで変換した partial に
「各ターン、相手のクリーチャーがはじめて攻撃するなら、可能ならこのクリーチャーを
攻撃する」を static {affects: self, mod: {must_be_attacked: {first_only: true}}}
として足し、unsupported を外したものが登録形。
dm25ex3-rp4s05「K」-9+9+9 の同型条項（need: must_be_attacked_first_only）も
同じ形で解けるが、enter_effects_ignored が残るため今回は対象外。
"""
import yaml
from pathlib import Path

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()
CONVERTED = Path(__file__).parent.parent / "data" / "cards" / "converted.yaml"

TAUNT = {"kind": "static", "affects": "self", "mod": {"must_be_attacked": {"first_only": True}}}


def test_m001_registered():
    data = yaml.safe_load(CONVERTED.read_text(encoding="utf-8"))
    card = next(c for c in data["cards"] if c["id"] == "dm26sd1-m001")
    assert not (card.get("source") or {}).get("unsupported"), "unsupported が残る"
    assert TAUNT in (card.get("abilities") or []), "first_only 誘引の常在型が登録形と違う"
    parsed = parse_card(card, TABLES)
    statics = [a for a in parsed.abilities if a["kind"] == "static"]
    assert any((a.get("mod") or {}).get("must_be_attacked") == {"first_only": True} for a in statics)
