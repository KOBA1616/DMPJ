"""語彙パイロット第366弾の対象カード（登録形の検証）。

対象は pure な conditional_battle_indestructible の全1件で、
ラウンド401で登録:
- dm24rp2-054 ケルビ・チゼン
（partial は骨格〔keywords [blocker] のみ、abilities 無し〕で、
未解決は unsupported の本 gap 1件だけだった。提出形は partial の
骨格に第366弾の確立形〔static {affects: self, if: {exists:
{zone: bz, owner: you, filter: {race_has: 超化獣}}}, mod:
{battle_indestructible: true}}〕1能力を足し、unsupported を
外したもの。partial に欠けた要素は無い＝補完なし。単面
カードで未検証の面は無い。alias は無い。登録形は提出形と
完全一致）

正本判定（ラウンド401で実施）: 対象 id dm24rp2-054 を
real.yaml / real_akashic.yaml / real_vocab.yaml /
real_zone.yaml / proto.yaml / converted.yaml と照合し、
いずれにも登録なし（proto.yaml のヒットは T1101 の notes 内
参照のみ）。alias は無いため畳み込み0件。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import find, proto_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
TARGET = "dm24rp2-054"

STATIC = {"kind": "static", "affects": "self",
          "if": {"exists": {"zone": "bz", "owner": "you",
                            "filter": {"race_has": "超化獣"}}},
          "mod": {"battle_indestructible": True}}
FORM = [STATIC]


def test_target_registered():
    c = find(CONVERTED, TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert not c.get("aliases")          # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    # 登録形は提出形と完全一致: 1能力ちょうど、keywords は [blocker] のまま
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert c["keywords"] == ["blocker"]
    assert c["name"] == "ケルビ・チゼン"
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 2 and c["power"] == 1500
    assert c["races"] == ["メカ・デル・ディネロ"]
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities


def test_proto_form_matches():
    assert proto_card("T1101")["abilities"] == FORM
