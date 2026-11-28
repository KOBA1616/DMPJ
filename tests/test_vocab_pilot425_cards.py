"""語彙パイロット第425弾（cards 側）: battle_power_filter。

対象 dmr08-009 巨体の守護者ランチュン（pure 1件、
multi にも現れない）。partial は骨格＋keywords
[blocker, cannot_attack_player] まで構築済みで
abilities は無く、text は公式全文（補完なし）。
未解決は第3条項「コスト６以下のクリーチャーと
バトル中、このクリーチャーのパワーは+2000される」
だけで、提出形は static {affects: self, mod:
{battle_power: {amount: 2000, opponent_filter:
{cost_le: 6}}}}（第122弾の battle_power
{amount, opponent_filter} のフィルタ差し替え版。
第377弾 civs 版・第378弾 power_ge 版と同型の
ドリフト）。alias は無し。形の根拠は本体テストの
docstring 参照。

ラウンド460で登録済み（登録形は提出形と完全一致、
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
TARGET = "dmr08-009"
GAP = "battle_power_filter"
NAME = "巨体の守護者ランチュン"

STATIC = {"kind": "static", "affects": "self",
          "mod": {"battle_power": {"amount": 2000,
                                   "opponent_filter": {"cost_le": 6}}}}
FULL_TEXT = ("ブロッカー(相手クリーチャーが攻撃する時、このクリーチャーをタップして、"
             "その攻撃を阻止してもよい。その後、その相手クリーチャーとバトルする)\n"
             "このクリーチャーは、相手プレイヤーを攻撃できない。\n"
             "コスト６以下のクリーチャーとバトル中、このクリーチャーのパワーは+2000される。")
SUBMIT = {"id": TARGET, "name": NAME, "types": ["creature"],
          "civs": ["light"], "cost": 3, "power": 4000,
          "races": ["ガーディアン"], "mana": 1, "text": FULL_TEXT,
          "keywords": ["blocker", "cannot_attack_player"],
          "abilities": [STATIC]}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    assert len(rows) <= 1906  # 件数は減る一方（スナップショット固定をやめた）
    mine = {r["id"]: r for r in rows}
    assert TARGET not in mine            # 対象行は登録で解消
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    conv = all_cards(CONVERTED)
    assert len({c["id"] for c in conv}) >= 10405  # 件数は増える一方
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形は提出形と完全一致
    # 登録後は abilities が static 1件ちょうど・
    # keywords [blocker, cannot_attack_player] のまま
    assert c["abilities"] == [STATIC]
    assert len(c["abilities"]) == 1
    assert c["keywords"] == ["blocker", "cannot_attack_player"]
    assert c["text"] == FULL_TEXT        # 公式全文
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")
    # 判断待ちの stale 行には触っていない
    assert mine["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


def test_submit_form_parses_and_matches_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    assert STATIC in d.abilities
    assert d.types == ["creature"] and d.civs == ["light"]
    assert d.cost == 3 and d.power == 4000
    assert d.races == ["ガーディアン"]
    assert d.keywords == ["blocker", "cannot_attack_player"]
    proto = proto_card("T1201")
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "text", "keywords", "abilities"):
        assert proto[k] == SUBMIT[k]


def test_official_row_matches_skeleton_and_text():
    off = None
    for line in (ROOT / "data/cards/raw/by_product/r08.jsonl") \
            .read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("id") == TARGET:
            off = r
            break
    assert off is not None
    assert off["name"] == NAME
    assert off["text"] == FULL_TEXT
    assert int(off["cost"]) == 3 and int(off["power"]) == 4000
    assert off["race"] == "ガーディアン"
    assert int(off["mana"]) == 1
