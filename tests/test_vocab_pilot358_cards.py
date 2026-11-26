"""語彙パイロット第358弾の対象カード（登録形の検証）。

対象は pure な destroy_after_attacking_on_entry_turn の全1件で、
ラウンド393で登録:
- dm22rp1-039 落下男
（partial は骨格のみで keywords [slayer]、未解決は
unsupported の destroy_after_attacking_on_entry_turn
1件だけだった。第358弾の確立形〔攻撃誘発の第三者観測形
{event: attack, subject: {owner: opp, filter:
{entered_this_turn: true}}} → delayed_trigger
{when: {event: attack_end, subject: 同形},
duration: during_attack} → destroy
{select: {ref: event.subject}}〕1能力を足したもの。
登録形は提出形と完全一致）

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import find, proto_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
TARGET = "dm22rp1-039"

_OPP_NEW = {"owner": "opp", "filter": {"entered_this_turn": True}}
FORM = [{"kind": "trigger",
         "when": {"event": "attack", "subject": _OPP_NEW},
         "effect": [{"op": "delayed_trigger",
                     "when": {"event": "attack_end",
                              "subject": _OPP_NEW},
                     "duration": "during_attack",
                     "effect": [{"op": "destroy",
                                 "select": {"ref": "event.subject"}}]}]}]
KEYWORDS = ["slayer"]


def test_target_registered():
    c = find(CONVERTED, TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert not c.get("aliases")          # alias 畳み込み0件
    assert c["abilities"] == FORM
    assert c["keywords"] == KEYWORDS
    assert c["name"] == "落下男"
    assert c["cost"] == 2 and c["power"] == 2000
    assert c["races"] == ["ヘドリアン"]
    d = parse_card(c, TABLES)
    assert d.keywords == KEYWORDS
    # キーワード slayer は parse で static 1件に展開されるため、
    # 誘発は「展開形が含まれる」ことで照合する（第358弾本体と同形）
    parsed_trigger = copy.deepcopy(FORM[0])
    parsed_trigger["effect"][0]["effect"] = [
        {"op": "move", "select": {"ref": "event.subject"},
         "to": "graveyard", "reason": "destroy"}]
    assert parsed_trigger in d.abilities


def test_proto_form_matches():
    assert proto_card("T1076")["abilities"] == FORM
    assert proto_card("T1076")["keywords"] == KEYWORDS
