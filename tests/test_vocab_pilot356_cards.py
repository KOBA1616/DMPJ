"""語彙パイロット第356弾の対象カード（登録形の検証）。

対象は pure な destroy_after_attack の全1件で、
ラウンド391で登録:
- dm24rp2-064 プランタ＝ランター
（partial は骨格のみ〔keywords: blocker〕で、条項は
第356弾の確立形〔第319弾形Aの攻撃後自壊＋dm21-s04 先例の
条件つき static スレイヤー付与〕で組んだ。
登録形は確立形と完全一致）

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
_conv_cache を直接使う（第319弾以降の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import all_cards, proto_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)

TRIGGER_A = {"kind": "trigger",
             "when": {"event": "attack", "subject": "self"},
             "effect": [{"op": "delayed_trigger",
                         "when": {"event": "attack_end",
                                  "subject": "self"},
                         "duration": "during_attack",
                         "effect": [{"op": "destroy",
                                     "select": {"ref": "self"}}]}]}
STATIC_SLAYER = {"kind": "static", "affects": "self",
                 "if": {"exists": {"zone": "bz", "owner": "you",
                                   "filter": {"race_has": "超化獣"}}},
                 "mod": {"grant": ["slayer"]}}
FORM = [TRIGGER_A, STATIC_SLAYER]


def test_target_registered():
    conv = all_cards(CONVERTED)
    c = next(x for x in conv if x["id"] == "dm24rp2-064")
    assert c["abilities"] == FORM
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.keywords == ["blocker"]


def test_proto_form_matches():
    assert proto_card("T1070")["abilities"] == FORM
