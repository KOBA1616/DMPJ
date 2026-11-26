"""語彙パイロット第355弾の対象カード（登録形の検証）。

対象は pure な trigger_when_ally_is_blocked の全1件で、
ラウンド390で登録:
- dm21-048 肝っ玉メリー
（partial は骨格のみで、条項は第355弾の確立形で組んだ。
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

_VB = {"owner": "you", "filter": {"race_has": "ビークル・ビー"}}
TRIGGER = {"kind": "trigger",
           "when": {"event": "block", "attacker": _VB},
           "effect": [{"op": "delayed_trigger",
                       "when": {"event": "attack_end", "subject": _VB},
                       "duration": "during_attack",
                       "effect": [{"op": "destroy",
                                   "select": {"ref": "event.target"}}]}]}
FORM = [TRIGGER]


def test_target_registered():
    conv = all_cards(CONVERTED)
    c = next(x for x in conv if x["id"] == "dm21-048")
    assert c["abilities"] == FORM
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 1
    assert d.keywords == []


def test_proto_form_matches():
    assert proto_card("T1066")["abilities"] == FORM
