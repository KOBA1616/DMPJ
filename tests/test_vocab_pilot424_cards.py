"""語彙パイロット第424弾（cards 側）: entry_turn_attack。

対象 dmbd07-a-006 ガンバＧ/ガガン・ガン・ガガン
（pure 1件、multi にも現れない。ツインパクト）。
partial はクリーチャー面の骨格のみ（name は
ガンバＧ、text は第2条項の断片、keywords・
abilities・faces 無し）。**補完あり: faces 構造＋
text＋keywords**（両面とも公式全文。最上位 text は
両面を「 ／ 」で連結）。提出形は確立部品のみ:
クリーチャー面は keywords [double_breaker] ＋
static {affects: self, if: {exists: {ref: self,
filter: {entered_this_turn: true}}}, mod:
{player_rush: true}}（第261弾の player_rush の
self 形。登録済み promoy17-sp4d01 と同一文面・
同形。第392弾の「確立形が未確認」という見送りは
登録先例の見落としだった）、呪文面は spell
[move {select: {zone: graveyard, owner: you,
filter: {race_has: ジョーカーズ}, count: 1},
to: mana, reason: put}]（登録済み dm23bd5-042 の
呪文形。必須1枚で up_to 無し、種別指定が無いため
types フィルタ無し）。呪文面の文明は公式データで
空文字だが、同 product のツインパクトで明示される
場合はクリーチャー面と同一（dmbd07-b-010）のため
両面とも zero とする。形の根拠は本体テストの
docstring 参照（ドリフト）。alias は dmsd04-002 /
promoy17-035 / promoy17-sp4d02 の3件（rejects に
独自行なし、canon は対象自身）。

ラウンド459で登録済み（登録形は提出形と完全一致、
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
TARGET = "dmbd07-a-006"
GAP = "entry_turn_attack"
ALIASES = ["dmsd04-002", "promoy17-035", "promoy17-sp4d02"]
NAME = "ガンバＧ/ガガン・ガン・ガガン"

STATIC = {"kind": "static", "affects": "self",
          "if": {"exists": {"ref": "self",
                            "filter": {"entered_this_turn": True}}},
          "mod": {"player_rush": True}}
SPELL = [{"op": "move",
          "select": {"zone": "graveyard", "owner": "you",
                     "filter": {"race_has": "ジョーカーズ"}, "count": 1},
          "to": "mana", "reason": "put"}]
CREATURE_TEXT = ("W・ブレイカー（このクリーチャーはシールドを"
                 "２つブレイクする）\n"
                 "このクリーチャーは、バトルゾーンに出たターンの間、"
                 "相手プレイヤーを攻撃できる。")
SPELL_TEXT = "ジョーカーズを１枚、自分の墓地からマナゾーンに置く。"
FULL_TEXT = CREATURE_TEXT + " ／ " + SPELL_TEXT
SUBMIT = {"id": TARGET, "name": NAME, "mana": 1, "text": FULL_TEXT,
          "faces": [
              {"name": "ガンバＧ", "types": ["creature"],
               "civs": ["zero"], "cost": 6, "power": 6000,
               "races": ["ジョーカーズ"], "text": CREATURE_TEXT,
               "keywords": ["double_breaker"], "abilities": [STATIC]},
              {"name": "ガガン・ガン・ガガン", "types": ["spell"],
               "civs": ["zero"], "cost": 2, "text": SPELL_TEXT,
               "spell": SPELL}]}


def test_target_registered_and_family_cleared():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) <= 1907  # 件数は減る一方（スナップショット固定をやめた）
    mine = {r["id"]: r for r in rows}
    assert TARGET not in mine            # 対象行は登録で解消
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    for a in ALIASES:
        assert a not in mine             # alias に独自行なし
    assert canon_id(TARGET) == TARGET
    for a in ALIASES:
        assert canon_id(a) == TARGET
    assert sorted(aliases_for(NAME, TARGET)) == sorted(ALIASES)
    conv = all_cards(CONVERTED)
    assert len({c["id"] for c in conv}) >= 10404  # 件数は増える一方
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形は提出形と完全一致
    f0, f1 = c["faces"]
    assert f0["abilities"] == [STATIC]   # クリーチャー面 static 1件ちょうど
    assert f0["keywords"] == ["double_breaker"]
    assert f1["spell"] == SPELL and len(f1["spell"]) == 1
    assert c["text"] == FULL_TEXT        # 公式全文（両面「 ／ 」連結）
    for a in ALIASES:
        assert find(CONVERTED, a) is None  # alias は独立エントリでない
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert sorted(src.get("aliases") or []) == sorted(ALIASES)
    # 判断待ちの stale 行には触っていない
    assert mine["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


def test_submit_form_parses_and_matches_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    pf0, pf1 = d.faces
    assert STATIC in pf0.abilities
    # double_breaker はキーワード展開で static が1件増える
    assert len(pf0.abilities) == 2
    assert pf0.keywords == ["double_breaker"]
    assert pf1.spell == SPELL
    p = proto_card("T1200")
    assert SUBMIT["name"] == p["name"]
    assert SUBMIT["mana"] == p["mana"]
    assert SUBMIT["text"] == p["text"]
    sf0, sf1 = SUBMIT["faces"]
    pr0, pr1 = p["faces"]
    for key in ("name", "types", "civs", "cost", "power", "races",
                "text", "keywords", "abilities"):
        assert sf0[key] == pr0[key]
    for key in ("name", "types", "civs", "cost", "text", "spell"):
        assert sf1[key] == pr1[key]


def test_official_row_matches_skeleton():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/bd07.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    row = next(r for r in rows if r["id"] == TARGET)
    assert row["name"] == NAME
    assert row["card_type"] == "クリーチャー"
    assert row["civilization"] == "ゼロ"
    assert int(row["cost"]) == 6 and int(row["power"]) == 6000
    assert int(row["mana"]) == 1
    assert row["race"] == "ジョーカーズ"
    assert row["text"] == CREATURE_TEXT
    f1 = row["faces"][1]
    assert f1["card_type"] == "呪文" and int(f1["cost"]) == 2
    assert f1["civilization"] == ""      # 公式データの欠落（本文参照）
    assert f1["text"] == SPELL_TEXT
