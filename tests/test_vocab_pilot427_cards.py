"""語彙パイロット第427弾（cards 側）: turn_history_attacked。

対象 dmd27-016 轟速 ザ・ゼット（pure 1件、multi にも
現れない）。partial は骨格＋keywords [speed_attacker,
double_breaker] まで構築済みで text は公式全文
（補完なし）。未解決は unsupported の
turn_history_attacked 1件だけで、提出形は abilities
1件: trigger {when: {event: turn_end, player: you},
if: {cmp: [{turn_count: {kind: attack_by, ref: self}},
">=", 1]}, effect: [destroy {select: {ref: self}}]}
（ドリフト。attack_by は第159・161弾の確立式、
turn_end + player: you は dm10-041 の確立形）。
alias は promoy15-052（partial の source.aliases
のみ、自前の reject 行は無い。canon は対象自身）。
形の根拠は本体テストの docstring 参照。

ラウンド462で登録済み（登録形は提出形と完全一致、
source 以外の全フィールドを照合。別刷り promoy15-052
は source.aliases にのみ収載）。本ファイルは登録形に
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
TARGET = "dmd27-016"
ALIAS = "promoy15-052"
GAP = "turn_history_attacked"
NAME = "轟速 ザ・ゼット"

TRIGGER = {"kind": "trigger",
           "when": {"event": "turn_end", "player": "you"},
           "if": {"cmp": [{"turn_count": {"kind": "attack_by",
                                          "ref": "self"}},
                          ">=", 1]},
           "effect": [{"op": "destroy", "select": {"ref": "self"}}]}
FULL_TEXT = ("スピードアタッカー（このクリーチャーは召喚酔いしない）"
             "W・ブレイカー（このクリーチャーはシールドを２つブレイクする）"
             "自分のターンの終わりに、そのターンこのクリーチャーが"
             "攻撃していたら、破壊する。")
SUBMIT = {"id": TARGET, "name": NAME, "types": ["creature"],
          "civs": ["fire"], "cost": 4, "power": 7000,
          "races": ["ソニック・コマンド", "侵略者"], "mana": 1,
          "text": FULL_TEXT,
          "keywords": ["speed_attacker", "double_breaker"],
          "abilities": [TRIGGER]}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    assert len(rows) == 1904
    mine = {r["id"]: r for r in rows}
    assert TARGET not in mine            # 対象行は登録で解消
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert ALIAS not in mine             # 別刷りに自前の行は無い
    assert canon_id(TARGET) == TARGET
    assert canon_id(ALIAS) == TARGET
    assert aliases_for(NAME, TARGET) == [ALIAS]
    conv = all_cards(CONVERTED)
    assert len({c["id"] for c in conv}) == 10407
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形は提出形と完全一致
    # 登録後は abilities が1件ちょうど（trigger 1）・
    # keywords [speed_attacker, double_breaker] のまま
    assert c["abilities"] == [TRIGGER]
    assert len(c["abilities"]) == 1
    assert c["keywords"] == ["speed_attacker", "double_breaker"]
    assert c["text"] == FULL_TEXT        # 公式全文
    assert find(CONVERTED, ALIAS) is None   # 別刷りは独立エントリでない
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == [ALIAS]    # source.aliases にのみ収載
    # 判断待ちの stale 行には触っていない
    assert mine["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


def test_submit_form_parses_and_matches_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    parsed = {"kind": "trigger",
              "when": {"event": "turn_end", "player": "you"},
              "if": {"cmp": [{"turn_count": {"kind": "attack_by",
                                             "ref": "self"}},
                             ">=", 1]},
              "effect": [{"op": "move", "select": {"ref": "self"},
                          "to": "graveyard", "reason": "destroy"}]}
    assert parsed in d.abilities   # destroy は move に正規化される
    assert d.types == ["creature"] and d.civs == ["fire"]
    assert d.cost == 4 and d.power == 7000
    assert d.races == ["ソニック・コマンド", "侵略者"]
    assert d.keywords == ["speed_attacker", "double_breaker"]
    proto = proto_card("T1205")
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "text", "keywords", "abilities"):
        assert proto[k] == SUBMIT[k]


def test_official_row_matches_skeleton_and_text():
    off = None
    for line in (ROOT / "data/cards/raw/by_product/d27.jsonl") \
            .read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("id") == TARGET:
            off = r
            break
    assert off is not None
    assert off["name"] == NAME
    assert off["text"] == FULL_TEXT
    assert int(off["cost"]) == 4 and int(off["power"]) == 7000
    assert off["race"] == "ソニック・コマンド/侵略者"
    assert int(off["mana"]) == 1
