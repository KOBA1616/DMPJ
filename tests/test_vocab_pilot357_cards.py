"""語彙パイロット第357弾の対象カード（登録形の検証）。

対象は pure な return_any_number の全1件で、
ラウンド392で登録:
- dmex08-049 十極 ジョバンチュ / Genesis of Drillball
（ツインパクト。partial は faces がプレースホルダの stub で、
未解決は unsupported の return_any_number 1件だけだった。
クリーチャー面は第357弾の確立形〔turn_end 誘発 →
choose {count: any, filter cost_le/cost_ge 9} →
move hand〕＋keywords [blocker, cannot_attack_player]。
呪文面はラウンド392で検証し、move {zone: deck,
from_top: 2} → shield ＋ modify {select: {zone: shield,
owner: you}, mod: {allow: [s_trigger]}, dynamic: true,
duration: until_next_own_turn_start} で正確に表現できた。
登録形は提出形と完全一致）

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
_conv_cache を直接使う（第319弾以降の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import find, proto_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
TARGET = "dmex08-049"

FORM = [{"kind": "trigger",
         "when": {"event": "turn_end", "player": "you"},
         "effect": [
             {"op": "choose",
              "select": {"zone": "graveyard", "owner": "you",
                         "filter": {"cost_le": 9, "cost_ge": 9},
                         "count": "any"},
              "as": "pick"},
             {"op": "move",
              "select": {"ref": "pick", "count": "all"},
              "to": "hand", "reason": "return"}]}]
KEYWORDS = ["blocker", "cannot_attack_player"]
SPELL_FORM = [{"op": "move",
               "select": {"zone": "deck", "owner": "you", "from_top": 2},
               "to": "shield", "reason": "put"},
              {"op": "modify",
               "select": {"zone": "shield", "owner": "you"},
               "mod": {"allow": ["s_trigger"]},
               "dynamic": True,
               "duration": "until_next_own_turn_start"}]


def test_target_registered():
    c = find(CONVERTED, TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    f0, f1 = c["faces"]
    assert f0["abilities"] == FORM
    assert f0["keywords"] == KEYWORDS
    assert f1["spell"] == SPELL_FORM
    d = parse_card(c, TABLES)
    assert d.faces[0].keywords == KEYWORDS
    trig = [a for a in d.faces[0].abilities if a.get("kind") == "trigger"]
    assert trig[0]["when"] == {"event": "turn_end", "player": "you"}
    assert trig[0]["effect"] == FORM[0]["effect"]


def test_proto_form_matches():
    assert proto_card("T1073")["abilities"] == FORM
    assert proto_card("T1073")["keywords"] == KEYWORDS
