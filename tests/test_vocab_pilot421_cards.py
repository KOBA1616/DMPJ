"""語彙パイロット第421弾（cards 側）: move_to_deck_bottom_trigger。

対象 dmex04-025 ヤッタレ総長（pure 1件、multi にも
現れない）。partial は骨格＋第1条項（cost_may の static）
まで構築済みで text は公式全文（補完なし）。提出形は
第2条項の trigger {when: {event: move, from: bz,
to: deck, position: bottom, subject: {owner: you}},
effect: [draw {count: 1}]} を足す形。形の根拠は
本体テストの docstring 参照（ドリフト: 第290弾の
position 照合＋登録済み dmrp06-001 形D、能動態の
読みは第418弾の先例、公式 QA 32439 / 31661 で裏付け）。
alias は dmex02-041 / dmrp04s-050 / promoy16-087
の3件（rejects に独自行なし、canon は対象自身）。

ラウンド456で登録済み（登録形は提出形と完全一致、
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
TARGET = "dmex04-025"
GAP = "move_to_deck_bottom_trigger"
NAME = "ヤッタレ総長"
ALIASES = ["dmex02-041", "dmrp04s-050", "promoy16-087"]

FORM = [
    {"kind": "static",
     "affects": {"owner": "you", "zone": "hand",
                 "filter": {"types": ["creature"],
                            "race_has": "ジョーカーズ", "cost_ge": 7}},
     "mod": {"cost_may": {"amount": 1, "min": 1}}},
    {"kind": "trigger",
     "when": {"event": "move", "from": "bz", "to": "deck",
              "position": "bottom", "subject": {"owner": "you"}},
     "effect": [{"op": "draw", "count": 1}]},
]
FULL_TEXT = ("自分のコスト７以上のジョーカーズを召喚するコストを"
             "１少なくしてもよい。ただし、コストは０以下にならない。\n"
             "バトルゾーンにあるカードを１枚、自分の山札の一番下に"
             "置いた時、カードを１枚引く。")
SUBMIT = {"id": TARGET, "name": NAME, "types": ["creature"],
          "civs": ["fire"], "cost": 3, "power": 3000,
          "races": ["ジョーカーズ"], "mana": 1,
          "text": FULL_TEXT, "abilities": FORM}


def test_target_registered_and_family_cleared():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 1910
    mine = {r["id"]: r for r in rows}
    assert TARGET not in mine            # 対象行は登録で解消
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    for a in ALIASES:
        assert a not in mine             # alias に独自行なし
    assert canon_id(TARGET) == TARGET
    for a in ALIASES:
        assert canon_id(a) == TARGET
    assert aliases_for(NAME, TARGET) == ALIASES
    conv = all_cards(CONVERTED)
    assert len({c["id"] for c in conv}) == 10401
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形は提出形と完全一致
    assert len(c["abilities"]) == 2      # abilities 2件ちょうど
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES
    # 判断待ちの stale 行には触っていない
    assert mine["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


def test_submit_form_parses_and_matches_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    for ab in FORM:
        assert ab in d.abilities
    p = proto_card("T1192")
    for key in ("name", "types", "civs", "cost", "power", "races",
                "mana", "text", "abilities"):
        assert SUBMIT[key] == p[key]


def test_official_row_matches_skeleton():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/ex04.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    row = next(r for r in rows if r["id"] == TARGET)
    assert row["name"] == NAME == SUBMIT["name"]
    assert row["card_type"] == "クリーチャー"
    assert row["civilization"] == "火" and SUBMIT["civs"] == ["fire"]
    assert int(row["cost"]) == SUBMIT["cost"] == 3
    assert int(row["power"]) == SUBMIT["power"] == 3000
    assert int(row["mana"]) == SUBMIT["mana"] == 1
    assert row["race"].split("/") == SUBMIT["races"]
    assert row["text"] == SUBMIT["text"] == FULL_TEXT
