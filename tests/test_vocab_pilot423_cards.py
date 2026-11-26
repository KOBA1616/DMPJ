"""語彙パイロット第423弾（cards 側）:
trigger_after_battle_win_or_lose。

対象 dm10-013 粛清者アイザク（pure 1件、multi にも
現れない）。partial は骨格＋keywords [blocker,
cannot_attack_player] まで構築済みで text は公式全文
（補完なし）。提出形は第3条項を確立部品の組み合わせで
足す形: trigger {when: {event: block, subject: self},
effect: [may [choose {select: {zone: bz, owner: you,
filter: {types: [creature]}, count: 1}, as: pick},
delayed_trigger {when: {event: battle_end,
subject: self}, effect: [untap {select:
{ref: pick}}]}]]}（block 誘発は第401・422弾、
choose の as 束縛は第414・422弾、battle_end は
第211弾、delayed_trigger は 603.6 の確立 op で
vars スナップショットにより pick が遅延効果に届く）。
形の根拠は本体テストの docstring 参照（ドリフト）。
alias は無し（canon は対象自身）。

ラウンド458で登録済み（登録形は提出形と完全一致、
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
TARGET = "dm10-013"
GAP = "trigger_after_battle_win_or_lose"
NAME = "粛清者アイザク"

FORM = [
    {"kind": "trigger",
     "when": {"event": "block", "subject": "self"},
     "effect": [{"op": "may", "body": [
         {"op": "choose",
          "select": {"zone": "bz", "owner": "you",
                     "filter": {"types": ["creature"]}, "count": 1},
          "as": "pick"},
         {"op": "delayed_trigger",
          "when": {"event": "battle_end", "subject": "self"},
          "effect": [{"op": "untap", "select": {"ref": "pick"}}]}]}]},
]
FULL_TEXT = ("ブロッカー\n"
             "このクリーチャーは、相手プレイヤーを攻撃できない。\n"
             "このクリーチャーがブロックする時、バトルゾーンにある"
             "自分のクリーチャーを１体選んでもよい。このクリーチャーの"
             "バトルの後、選んだクリーチャーをアンタップする。")
SUBMIT = {"id": TARGET, "name": NAME, "types": ["creature"],
          "civs": ["light"], "cost": 4, "power": 4000,
          "races": ["ソルトルーパー"], "mana": 1,
          "keywords": ["blocker", "cannot_attack_player"],
          "text": FULL_TEXT, "abilities": FORM}


def test_target_registered_and_family_cleared():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 1908
    mine = {r["id"]: r for r in rows}
    assert TARGET not in mine            # 対象行は登録で解消
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    conv = all_cards(CONVERTED)
    assert len({c["id"] for c in conv}) == 10403
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形は提出形と完全一致
    assert len(c["abilities"]) == 1      # abilities 1件ちょうど
    assert c["keywords"] == ["blocker", "cannot_attack_player"]
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    # 判断待ちの stale 行には触っていない
    assert mine["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


def test_submit_form_parses_and_matches_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    assert FORM[0] in d.abilities
    p = proto_card("T1199")
    for key in ("name", "types", "civs", "cost", "power", "races",
                "mana", "keywords", "text", "abilities"):
        assert SUBMIT[key] == p[key]


def test_official_row_matches_skeleton():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/10.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    row = next(r for r in rows if r["id"] == TARGET)
    assert row["name"] == NAME == SUBMIT["name"]
    assert row["card_type"] == "クリーチャー"
    assert row["civilization"] == "光" and SUBMIT["civs"] == ["light"]
    assert int(row["cost"]) == SUBMIT["cost"] == 4
    assert int(row["power"]) == SUBMIT["power"] == 4000
    assert int(row["mana"]) == SUBMIT["mana"] == 1
    assert row["race"].split("/") == SUBMIT["races"]
    assert row["text"] == SUBMIT["text"] == FULL_TEXT
