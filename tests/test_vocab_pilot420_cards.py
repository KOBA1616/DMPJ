"""語彙パイロット第420弾（cards 側）: does_not_untap。

対象 dm22rp1-011 予言者マンプクルト（pure 2件のうち
1件。ファミリーの残り1件 dm25ex2-031 は形が異なる
ため対象外で、ファミリーは解消しない）。partial は
骨格＋keywords [blocker] まで構築済みで text は
公式全文（補完なし）。提出形は abilities 3件
（static 2件＋trigger 1件）を足す形。形の根拠は
本体テストの docstring 参照（ドリフト: 第1条項は
第400弾・登録済み dmrp06-027 の形、第2条項は
登録済み dmrp21-072 の同文条項の登録形と完全一致、
第3条項は登録済み dm24rp4-031 の監視誘発の
subject をタマシードに替えた形）。alias は無し。

ラウンド455で登録済み（登録形は提出形と完全一致、
source 以外の全フィールドを照合）。本ファイルは
登録形に書き換え済み。dm25ex2-031 は reopen で
2件とも外れたが、unsupported を残した partial の
まま差し戻され、行全体が HEAD と同一であることを
本ファイルでも固定する。
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
TARGET = "dm22rp1-011"
BOUNCE = "dm25ex2-031"
GAP = "does_not_untap"
NAME = "予言者マンプクルト"

FORM = [
    {"kind": "static", "affects": "self",
     "mod": {"deny": ["untap_at_start"]}},
    {"kind": "static", "affects": "self",
     "if": {"not": {"exists": {"zone": "bz", "owner": "you",
                              "filter": {"types": ["tamaseed"]}}}},
     "mod": {"deny": ["attack_player"]}},
    {"kind": "trigger",
     "when": {"event": "move", "to": "bz",
              "subject": {"owner": "you",
                          "filter": {"types": ["tamaseed"]}}},
     "effect": [{"op": "untap", "select": {"ref": "self"}}]},
]
FULL_TEXT = ("ブロッカー（このクリーチャーをタップして、相手クリーチャーの"
             "攻撃先をこのクリーチャーに変更してもよい）\n"
             "このクリーチャーは、自分のターンのはじめにアンタップしない。\n"
             "自分のタマシードがなければ、このクリーチャーは相手プレイヤーを"
             "攻撃できない。\n"
             "自分のタマシードが出た時、このクリーチャーをアンタップする。")
SUBMIT = {"id": TARGET, "name": NAME, "types": ["creature"],
          "civs": ["light"], "cost": 1, "power": 3500,
          "races": ["ライトブリンガー"], "mana": 1,
          "text": FULL_TEXT, "keywords": ["blocker"],
          "abilities": FORM}


def test_target_registered_and_family_not_cleared():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) <= 1911  # 件数は減る一方（スナップショット固定をやめた）
    mine = {r["id"]: r for r in rows}
    assert TARGET not in mine            # 対象行は登録で解消
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == [BOUNCE]               # ファミリーは解消しない
    brow = mine[BOUNCE]                  # 差し戻し行は不変
    assert brow["gaps"] == [GAP] and brow["reason"] == "vocab"
    assert brow["partial"]["source"]["unsupported"] == [
        {"need": GAP, "text": "アンタップしない"}]
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    conv = all_cards(CONVERTED)
    assert len({c["id"] for c in conv}) >= 10400  # 件数は増える一方
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形は提出形と完全一致
    assert len(c["abilities"]) == 3      # abilities 3件ちょうど
    assert c["keywords"] == ["blocker"]  # keywords はそのまま
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")


def test_submit_form_parses_and_matches_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    for ab in FORM:
        assert ab in d.abilities
    p = proto_card("T1191")
    for key in ("name", "types", "civs", "cost", "power", "races",
                "mana", "text", "keywords", "abilities"):
        assert SUBMIT[key] == p[key]


def test_official_row_matches_skeleton():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/22rp1.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    row = next(r for r in rows if r["id"] == TARGET)
    assert row["name"] == NAME == SUBMIT["name"]
    assert row["card_type"] == "クリーチャー"
    assert row["civilization"] == "光" and SUBMIT["civs"] == ["light"]
    assert int(row["cost"]) == SUBMIT["cost"] == 1
    assert int(row["power"]) == SUBMIT["power"] == 3500
    assert int(row["mana"]) == SUBMIT["mana"] == 1
    assert row["race"].split("/") == SUBMIT["races"]
    assert row["text"] == SUBMIT["text"] == FULL_TEXT
