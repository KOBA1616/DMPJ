"""語彙パイロット第364弾の対象カード（登録形の検証）。

対象は pure な blocking_power の全1件で、
ラウンド399で登録:
- dm34-025 ワダツミ・フィッシュ
（partial は骨格（keywords [blocker, cannot_attack]、
abilities 無し）で、未解決は unsupported の本 gap
1件だけだった。提出形は partial の骨格に第364弾の
確立形〔static {affects: self, mod: {power_when:
{amount: 2000, when: blocking, opponent_filter:
{not_types: [evolution]}}}}〕1能力を足し、
unsupported を外したもの。partial に欠けた要素は
無い＝補完なし。単面カードで未検証の面は無い。
登録形は提出形と完全一致）

正本判定（ラウンド399で実施）: 対象 id dm34-025 を
real.yaml / real_akashic.yaml / real_vocab.yaml /
real_zone.yaml / proto.yaml / converted.yaml と
照合し、いずれにも登録なし（proto.yaml のヒットは
T1095 の notes 内参照のみ）。identity の canon_id
実測で対象 id が正本そのもの、aliases_for(名前,
対象id) = []（alias なし、alias 畳み込み0件）。

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
TARGET = "dm34-025"

STATIC = {"kind": "static", "affects": "self",
          "mod": {"power_when": {"amount": 2000, "when": "blocking",
                                 "opponent_filter":
                                     {"not_types": ["evolution"]}}}}
FORM = [STATIC]


def test_target_registered():
    c = find(CONVERTED, TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert not c.get("aliases")          # alias 畳み込み0件
    assert not (c.get("source") or {}).get("aliases")
    # 登録形は提出形と完全一致: 1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert c["name"] == "ワダツミ・フィッシュ"
    assert c["types"] == ["creature"] and c["civs"] == ["water"]
    assert c["cost"] == 3 and c["power"] == 3000
    assert c["races"] == ["フィッシュ", "オリジン"]
    assert c["keywords"] == ["blocker", "cannot_attack"]
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities


def test_proto_form_matches():
    assert proto_card("T1095")["abilities"] == FORM
    assert proto_card("T1095")["keywords"] == ["blocker", "cannot_attack"]
