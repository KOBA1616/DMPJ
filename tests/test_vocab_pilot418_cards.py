"""語彙パイロット第418弾（cards 側）: all_civilizations_mana。

対象 dm26sd1-u010 怪盗妖精カサブランカ /
「信じていたのに裏切られるなんて！」（pure 1件、
multi にも現れない）。partial は骨格のみ（types
[creature] のみで faces 無し、text は第2条項の
断片、abilities 無し）。**補完あり: faces 構造＋
text**（両面とも公式全文。最上位 text は両面を
「 ／ 」で連結）。alias は dm24bd5-010 /
dm25ex3-tf27 / dm25rp4-t09 の3件（rejects に
独自行なし）。形の根拠は本体テストの docstring
参照（ドリフト: 第1条項は第376弾の move 形、
第2条項は第376弾の add_civs 静的、第3条項は
登録済み dm24bd5-033 の監視誘発から first_time と
multicolor フィルタを外し from: hand を足した形、
呪文面は s_trigger＋bounce count: all）。

ラウンド453で登録済み（登録形は提出形と完全一致、
source 以外の全フィールドを照合）。本ファイルは
登録形に書き換え済み。
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
TARGET = "dm26sd1-u010"
GAP = "all_civilizations_mana"
ALIASES = ["dm24bd5-010", "dm25ex3-tf27", "dm25rp4-t09"]
NAME = "怪盗妖精カサブランカ / 「信じていたのに裏切られるなんて！」"

CREATURE_ABILITIES = [
    {"kind": "trigger",
     "when": {"event": "move", "to": "bz", "subject": "self"},
     "effect": [{"op": "move",
                 "select": {"zone": "deck", "owner": "you", "from_top": 1},
                 "to": "mana", "reason": "put"}]},
    {"kind": "static",
     "affects": {"zone": "mana", "owner": "you"},
     "mod": {"add_civs": ["light", "water", "darkness",
                          "fire", "nature"]}},
    {"kind": "trigger",
     "when": {"event": "move", "from": "hand", "to": "mana",
              "subject": {"owner": "you"}},
     "effect": [{"op": "untap", "select": {"ref": "event.subject"}}]},
]
SPELL = [{"op": "bounce",
          "select": {"zone": "bz", "owner": "any",
                     "filter": {"types": ["creature"], "cost_ge": 5},
                     "count": "all"}}]
CREATURE_TEXT = ("このクリーチャーが出た時、自分の山札の上から１枚を"
                 "マナゾーンに置く。\n"
                 "自分のマナゾーンにあるカードは、すべての文明を持つ。\n"
                 "カードを自分の手札からマナゾーンに置いた時、"
                 "そのカードをアンタップする。")
SPELL_TEXT = ("S・トリガー（このカードを自分のシールドゾーンから"
              "手札に加える時、コストを支払わずにすぐ実行してもよい）\n"
              "コスト５以上のクリーチャーをすべて持ち主の手札に戻す。")
FULL_TEXT = CREATURE_TEXT + " ／ " + SPELL_TEXT
SUBMIT = {"id": TARGET, "name": NAME, "mana": 1, "text": FULL_TEXT,
          "faces": [
              {"name": "怪盗妖精カサブランカ", "types": ["creature"],
               "civs": ["nature"], "cost": 3, "power": 2000,
               "races": ["スノーフェアリー"], "text": CREATURE_TEXT,
               "abilities": CREATURE_ABILITIES},
              {"name": "「信じていたのに裏切られるなんて！」",
               "types": ["spell"], "civs": ["water"], "cost": 6,
               "text": SPELL_TEXT, "keywords": ["s_trigger"],
               "spell": SPELL}]}


def test_target_registered_and_family_cleared():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 1913
    mine = {r["id"]: r for r in rows}
    assert TARGET not in mine            # 対象行は登録で解消
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    for a in ALIASES:
        assert a not in mine
    assert canon_id(TARGET) == TARGET
    for a in ALIASES:
        assert canon_id(a) == TARGET
    assert sorted(aliases_for(NAME, TARGET)) == sorted(ALIASES)
    conv = all_cards(CONVERTED)
    assert len({c["id"] for c in conv}) == 10398
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形は提出形と完全一致
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert sorted(src.get("aliases") or []) == sorted(ALIASES)


def test_submit_form_parses_and_matches_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    pf0, pf1 = d.faces
    assert len(pf0.abilities) == 3
    for a in CREATURE_ABILITIES:
        assert a in pf0.abilities
    assert pf1.keywords == ["s_trigger"]
    p = proto_card("T1189")
    sf0, sf1 = SUBMIT["faces"]
    pr0, pr1 = p["faces"]
    for key in ("name", "types", "civs", "cost", "text", "abilities"):
        assert sf0[key] == pr0[key]
    assert sf0["power"] == pr0["power"] == 2000
    assert sf0["races"] == pr0["races"] == ["スノーフェアリー"]
    for key in ("name", "types", "civs", "cost", "text", "keywords",
                "spell"):
        assert sf1[key] == pr1[key]
    assert SUBMIT["text"] == p["text"] == FULL_TEXT
    assert SUBMIT["name"] == p["name"] == NAME
    assert SUBMIT["mana"] == p["mana"] == 1


def test_official_row_matches_skeleton():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/26sd1.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    row = next(r for r in rows if r["id"] == TARGET)
    assert row["name"] == NAME
    assert int(row["mana"]) == 1
    f0, f1 = row["faces"]
    s0, s1 = SUBMIT["faces"]
    assert f0["name"] == s0["name"] and f0["text"] == s0["text"]
    assert int(f0["cost"]) == s0["cost"] and int(f0["power"]) == s0["power"]
    assert f0["civilization"] == "自然" and s0["civs"] == ["nature"]
    assert f0["card_type"] == "クリーチャー" and s0["types"] == ["creature"]
    assert f0["race"] == "スノーフェアリー" and s0["races"] == [f0["race"]]
    assert f1["name"] == s1["name"] and f1["text"] == s1["text"]
    assert int(f1["cost"]) == s1["cost"]
    assert f1["civilization"] == "水" and s1["civs"] == ["water"]
    assert f1["card_type"] == "呪文" and s1["types"] == ["spell"]
