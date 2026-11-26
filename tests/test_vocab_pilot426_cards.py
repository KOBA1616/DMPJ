"""語彙パイロット第426弾（cards 側）: must_be_blocked。

対象 dmex08-291 薩摩の超人（pure 1件、multi にも
現れない）。partial は骨格完備（mana 1、keywords
[triple_breaker]、第2条項の trigger 構築済み）で
text は公式全文（補完なし）。未解決は unsupported の
must_be_blocked 1件だけで、提出形は abilities 2件
（文面の条項順）: 第1条項 static {affects: {zone: bz,
owner: you, filter: {types: [creature], races:
[ジャイアント]}}, mod: {must_be_blocked: true}}
（新規語彙・最小）＋第2条項は partial の trigger
そのまま。alias は dm31-s03（partial の
source.aliases のみ、自前の reject 行は無い。
canon は対象自身）。形の根拠は本体テストの
docstring 参照。

ラウンド461で登録済み（登録形は提出形と完全一致、
source 以外の全フィールドを照合。別刷り dm31-s03 は
source.aliases にのみ収載）。本ファイルは登録形に
書き換え済み。ファミリーは完全解消。
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
TARGET = "dmex08-291"
ALIAS = "dm31-s03"
GAP = "must_be_blocked"
NAME = "薩摩の超人"

STATIC = {"kind": "static",
          "affects": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["creature"],
                                 "races": ["ジャイアント"]}},
          "mod": {"must_be_blocked": True}}
TRIGGER = {"kind": "trigger",
           "when": {"event": "battle_win",
                    "subject": {"owner": "you",
                                "filter": {"races": ["ジャイアント"]}}},
           "if": {"is_turn": "you"},
           "effect": [{"op": "break", "player": "opp", "count": 1}]}
FULL_TEXT = ("T・ブレイカー\n"
             "自分のジャイアントはすべて、可能ならブロックされる。\n"
             "自分のターン中、自分のジャイアントがバトルに勝った時、"
             "相手のシールドを１つブレイクする。")
SUBMIT = {"id": TARGET, "name": NAME, "types": ["creature"],
          "civs": ["nature"], "cost": 9, "power": 13000,
          "races": ["ジャイアント", "サムライ"], "mana": 1,
          "text": FULL_TEXT, "keywords": ["triple_breaker"],
          "abilities": [STATIC, TRIGGER]}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    assert len(rows) == 1905
    mine = {r["id"]: r for r in rows}
    assert TARGET not in mine            # 対象行は登録で解消
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert ALIAS not in mine             # 別刷りに自前の行は無い
    assert canon_id(TARGET) == TARGET
    assert canon_id(ALIAS) == TARGET
    assert aliases_for(NAME, TARGET) == [ALIAS]
    conv = all_cards(CONVERTED)
    assert len({c["id"] for c in conv}) == 10406
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形は提出形と完全一致
    # 登録後は abilities が2件ちょうど（static 1＋trigger 1）・
    # keywords [triple_breaker] のまま
    assert c["abilities"] == [STATIC, TRIGGER]
    assert len(c["abilities"]) == 2
    assert c["keywords"] == ["triple_breaker"]
    assert c["text"] == FULL_TEXT        # 公式全文
    assert find(CONVERTED, ALIAS) is None   # 別刷りは独立エントリでない
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == [ALIAS]    # source.aliases にのみ収載
    # 判断待ちの stale 行には触っていない
    assert mine["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


def test_submit_form_parses_and_matches_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    assert STATIC in d.abilities and TRIGGER in d.abilities
    assert d.types == ["creature"] and d.civs == ["nature"]
    assert d.cost == 9 and d.power == 13000
    assert d.races == ["ジャイアント", "サムライ"]
    assert d.keywords == ["triple_breaker"]
    proto = proto_card("T1204")
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "text", "keywords", "abilities"):
        assert proto[k] == SUBMIT[k]


def test_official_row_matches_skeleton_and_text():
    off = None
    for line in (ROOT / "data/cards/raw/by_product/ex08.jsonl") \
            .read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("id") == TARGET:
            off = r
            break
    assert off is not None
    assert off["name"] == NAME
    assert off["text"] == FULL_TEXT
    assert int(off["cost"]) == 9 and int(off["power"]) == 13000
    assert off["race"] == "ジャイアント/サムライ"
    assert int(off["mana"]) == 1
