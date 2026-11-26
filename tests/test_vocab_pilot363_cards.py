"""語彙パイロット第363弾の対象カード（登録形の検証）。

対象は pure な attack_on_entry_turn_punished の全1件で、
ラウンド398で登録:
- dm22rp2x-023 試練の大地ダン・ティラン
（partial はマッハファイターの展開形1能力を持ち、
未解決は unsupported の本 gap 1件だけだった。提出形は
partial の既存1能力に第363弾の確立形1能力を足した
2能力ちょうど。partial に欠けた要素は無い＝補完なし。
単面カードで未検証の面は無い。登録形は提出形と
完全一致）

正本判定（ラウンド398で実施）: 対象 id と alias
dm22rp2-023 の両方を real.yaml / real_akashic.yaml /
real_vocab.yaml / real_zone.yaml / proto.yaml /
converted.yaml と照合し、いずれにも登録なし
（proto.yaml のヒットは T1092 の notes 内参照のみ）。
identity の canon_id 実測で対象 id が正本そのもの、
alias の canon は対象 id、aliases_for(名前, 対象id)
= [dm22rp2-023]。登録エントリの source.aliases には
dm22rp2-023 が記録されたが、alias 側の rejects 行は
無かったため alias 畳み込みは0件。

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
TARGET = "dm22rp2x-023"

MACH = {"kind": "trigger",
        "when": {"event": "move", "to": "bz", "subject": "self"},
        "effect": [{"op": "modify", "select": {"ref": "self"},
                    "mod": {"allow": [{"action": "attack_creature",
                                       "other": {"tapped": False}}]},
                    "duration": "end_of_turn"}]}
TRIGGER = {"kind": "trigger",
           "when": {"event": "attack",
                    "subject": {"owner": "opp",
                                "filter": {"entered_this_turn": True}}},
           "effect": [{"op": "move",
                       "select": {"ref": "event.subject"},
                       "to": "mana", "reason": "put"}]}
FORM = [MACH, TRIGGER]


def test_target_registered():
    c = find(CONVERTED, TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert not c.get("aliases")          # alias 畳み込み0件
    assert (c.get("source") or {}).get("aliases") == ["dm22rp2-023"]
    # 登録形は提出形と完全一致: 2能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert c["name"] == "試練の大地ダン・ティラン"
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 4 and c["power"] == 5000
    assert c["races"] == ["ガイア・コマンド"]
    assert not c.get("keywords")
    d = parse_card(c, TABLES)
    assert TRIGGER in d.abilities
    assert MACH in d.abilities


def test_proto_form_matches():
    assert proto_card("T1092")["abilities"] == FORM
