"""語彙パイロット第367弾の対象カード（登録形の検証）。

対象は pure な always_win_battles の全1件で、
ラウンド402で登録:
- dm14-s01 太陽の精霊マルシアス
（partial は骨格〔abilities 無し、keywords 無し〕で、
未解決は unsupported の本 gap 1件だけだった。提出形は
partial の骨格に第367弾の確立形〔static {affects: self,
mod: {win_all_battles: true}}〕1能力を足し、unsupported を
外したもの。partial に欠けた要素は無い＝補完なし。単面
カードで未検証の面は無い。alias は無い。登録形は提出形と
完全一致）

正本判定（ラウンド402で実施）: 対象 id dm14-s01 を
real.yaml / real_akashic.yaml / real_vocab.yaml /
real_zone.yaml / proto.yaml / converted.yaml と照合し、
いずれにも登録なし（proto.yaml のヒットは T1104 の notes 内
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
TARGET = "dm14-s01"

STATIC = {"kind": "static", "affects": "self",
          "mod": {"win_all_battles": True}}
FORM = [STATIC]


def test_target_registered():
    c = find(CONVERTED, TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert not c.get("aliases")          # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    # 登録形は提出形と完全一致: 1能力ちょうど、keywords は無いまま
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("keywords")
    assert c["name"] == "太陽の精霊マルシアス"
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 5 and c["power"] == 2000
    assert c["races"] == ["エンジェル・コマンド"]
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities


def test_proto_form_matches():
    assert proto_card("T1104")["abilities"] == FORM
