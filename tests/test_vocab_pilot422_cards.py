"""語彙パイロット第422弾（cards 側）: block_event_target。

対象 dmrp12-046 凶鬼79号 ジュージュ（pure 1件、multi にも
現れない）。partial は骨格＋keywords [s_trigger, blocker]
まで構築済みで text は公式全文（補完なし）。提出形は
未構築の2条項を確立形で足す形: trigger {when:
{event: block, subject: self}, effect: [modify
{select: {ref: event.attacker}, mod: {power: -9000},
duration: end_of_turn}]}（第401弾のブロック誘発＋
第388弾の event 参照。対象は event.opponent ではなく
event.attacker＝block レコードの attacker キー、
登録済み dmr16g-015 の先例）と trigger {when:
{event: turn_end}, if: {exists: {ref: self, filter:
{tapped: true}}}, effect: [destroy {select:
{ref: self}}]}（登録済み dmrp15-069 の登録形）。
形の根拠は本体テストの docstring 参照（ドリフト）。
alias は無し（canon は対象自身）。

ラウンド457で登録済み（登録形は提出形と完全一致、
source 以外の全フィールドを照合）。本ファイルは
登録形に書き換え済み。ファミリーは完全解消。
"""
import copy
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.cards.identity import aliases_for, canon_id  # noqa: E402
from tests._conv_cache import all_cards, find, proto_card  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
TARGET = "dmrp12-046"
GAP = "block_event_target"
NAME = "凶鬼79号 ジュージュ"

FORM = [
    {"kind": "trigger",
     "when": {"event": "block", "subject": "self"},
     "effect": [{"op": "modify", "select": {"ref": "event.attacker"},
                 "mod": {"power": -9000}, "duration": "end_of_turn"}]},
    {"kind": "trigger",
     "when": {"event": "turn_end"},
     "if": {"exists": {"ref": "self", "filter": {"tapped": True}}},
     "effect": [{"op": "destroy", "select": {"ref": "self"}}]},
]
FULL_TEXT = ("S・トリガー（このクリーチャーをシールドゾーンから"
             "手札に加える時、コストを支払わずにすぐ召喚してもよい）\n"
             "ブロッカー（このクリーチャーをタップして、相手"
             "クリーチャーの攻撃先をこのクリーチャーに変更してもよい）\n"
             "このクリーチャーがブロックした時、このターン、その"
             "相手クリーチャーのパワーを－9000する。（パワー０以下の"
             "クリーチャーは破壊される）\n"
             "このターンの終わりに、このクリーチャーがタップしていたら、"
             "破壊する。")
SUBMIT = {"id": TARGET, "name": NAME, "types": ["creature"],
          "civs": ["darkness"], "cost": 6, "power": 2000,
          "races": ["マフィ・ギャング"], "mana": 1,
          "keywords": ["s_trigger", "blocker"],
          "text": FULL_TEXT, "abilities": FORM}


def test_target_registered_and_family_cleared():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) <= 1909  # 件数は減る一方（スナップショット固定をやめた）
    mine = {r["id"]: r for r in rows}
    assert TARGET not in mine            # 対象行は登録で解消
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    conv = all_cards(CONVERTED)
    assert len({c["id"] for c in conv}) >= 10402  # 件数は増える一方
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形は提出形と完全一致
    assert len(c["abilities"]) == 2      # abilities 2件ちょうど
    assert c["keywords"] == ["s_trigger", "blocker"]
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    # 判断待ちの stale 行には触っていない
    assert mine["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


def test_submit_form_parses_and_matches_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    assert FORM[0] in d.abilities
    # destroy は parse で move（to: graveyard, reason: destroy）に
    # 正規化される
    assert {"kind": "trigger",
            "when": {"event": "turn_end"},
            "if": {"exists": {"ref": "self", "filter": {"tapped": True}}},
            "effect": [{"op": "move", "select": {"ref": "self"},
                        "to": "graveyard", "reason": "destroy"}]} \
        in d.abilities
    p = proto_card("T1195")
    for key in ("name", "types", "civs", "cost", "power", "races",
                "mana", "keywords", "text", "abilities"):
        assert SUBMIT[key] == p[key]


def test_official_row_matches_skeleton():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/rp12.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    row = next(r for r in rows if r["id"] == TARGET)
    assert row["name"] == NAME == SUBMIT["name"]
    assert row["card_type"] == "クリーチャー"
    assert row["civilization"] == "闇" and SUBMIT["civs"] == ["darkness"]
    assert int(row["cost"]) == SUBMIT["cost"] == 6
    assert int(row["power"]) == SUBMIT["power"] == 2000
    assert int(row["mana"]) == SUBMIT["mana"] == 1
    assert row["race"].split("/") == SUBMIT["races"]
    assert row["text"] == SUBMIT["text"] == FULL_TEXT
