"""語彙パイロット第359弾の対象カード（登録形の検証）。

対象は pure な after_battle_bounce の全1件で、
ラウンド394で登録:
- dm27-042 パナオン
（partial は骨格のみで keywords [blocker, cannot_attack]、
未解決は unsupported の after_battle_bounce 1件だけだった。
第359弾の確立形〔trigger {event: block, subject: self} →
delayed_trigger {when: {event: attack_end, target: self},
duration: during_attack} → move {select:
{ref: event.subject}, to: hand, reason: return}〕1能力を
足したもの。登録形は提出形と完全一致）

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
TARGET = "dm27-042"

FORM = [{"kind": "trigger",
         "when": {"event": "block", "subject": "self"},
         "effect": [{"op": "delayed_trigger",
                     "when": {"event": "attack_end",
                              "target": "self"},
                     "duration": "during_attack",
                     "effect": [{"op": "move",
                                 "select": {"ref": "event.subject"},
                                 "to": "hand",
                                 "reason": "return"}]}]}]
KEYWORDS = ["blocker", "cannot_attack"]


def test_target_registered():
    c = find(CONVERTED, TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert not c.get("aliases")          # alias 畳み込み0件
    assert c["abilities"] == FORM
    assert c["keywords"] == KEYWORDS
    assert c["name"] == "パナオン"
    assert c["cost"] == 3 and c["power"] == 1000
    assert c["races"] == ["サイバーロード"]
    d = parse_card(c, TABLES)
    assert d.keywords == KEYWORDS
    # キーワード blocker / cannot_attack は parse で static に
    # 展開されるため、誘発は「展開形が含まれる」ことで照合する
    assert FORM[0] in d.abilities


def test_proto_form_matches():
    assert proto_card("T1079")["abilities"] == FORM
    assert proto_card("T1079")["keywords"] == KEYWORDS
