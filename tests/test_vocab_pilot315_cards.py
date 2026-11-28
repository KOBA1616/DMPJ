"""語彙パイロット第315弾の対象カード検証（ラウンド350で登録済み）。

under_dragons_return_on_destroy は dmex12-s19 燃える侵略
レッドギラゴン の1件のみだった。gaps は空で、partial の
source.unsupported にだけギャップ名が残る監査行
（第312〜314弾の監査の継続）。

第315弾の結論はドリフト: 未解決条項は最終節「このクリーチャーが
破壊された時、その下に重ねてあった進化ではないドラゴンをすべて
バトルゾーンに出す」のみで、第294弾 form B（破壊トリガー＋
play_free {select: {ref: event.was_under, zone: graveyard,
filter: {race_has: ...}}}、登録済み dmex12-004 と同形）の
filter を {race_has: ドラゴン, not_types: [evolution]} に
するだけで正確に一致する。not_types は既存フィルタキー。
partial の他節（NEO進化・侵略 declare・攻撃の終わりの
下置き）は完成済み。

ラウンド350で登録した。登録形は partial ＋ 破壊誘発、
unsupported を外したもので、raw の abilities は
[攻撃の終わり誘発, 破壊誘発] の2件ちょうど（連結・
merge_split 由来の混入なし、keywords は double_breaker
のまま）。正本判定は identity の実データ照合による:
canon_id は自id、aliases_for は空（alias なし）。対象行は
gaps が空のため reopen では外れず直接 submit（第323・
343・347・348・349弾の先例）。converted 10,253→10,254 /
rejects 2,065→2,064、canonical 重なり0・漏れ0。
under_dragons_return_on_destroy はファミリー単独行だった
ため完全に解消。実挙動は test_vocab_round350_cards.py が
登録カード自身で固定。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"
TABLES = load_tables()

TARGET = "dmex12-s19"
GAP = "under_dragons_return_on_destroy"

TEXT = ("NEO進化：自分のドラゴン１体の上に置いてもよい。\n"
        "侵略：コスト５以上のドラゴン（自分のコスト５以上のドラゴンが攻撃する時、"
        "自分の手札にあるこのクリーチャーをその上に重ねてもよい）\n"
        "W・ブレイカー\n"
        "このクリーチャーの攻撃の終わりに、自分の山札の上から１枚目を表向きにして、"
        "このクリーチャーの下に重ねてもよい。\n"
        "このクリーチャーが破壊された時、その下に重ねてあった進化ではないドラゴンを"
        "すべてバトルゾーンに出す。")

ATTACK_END_TRIGGER = {"kind": "trigger",
                      "when": {"event": "attack_end", "subject": "self"},
                      "effect": [{"op": "may",
                                  "body": [{"op": "put_under",
                                            "select": {"zone": "deck",
                                                       "owner": "you",
                                                       "from_top": 1},
                                            "onto": {"ref": "self"}}]}]}

FORM_TRIGGER = {"kind": "trigger",
                "when": {"event": "move", "from": "bz", "to": "graveyard",
                         "reason": "destroy", "subject": "self"},
                "effect": [{"op": "play_free",
                            "select": {"ref": "event.was_under",
                                       "zone": "graveyard",
                                       "filter": {"race_has": "ドラゴン",
                                                  "not_types": ["evolution"]}}}]}

FORM = {"id": TARGET,
        "name": "燃える侵略 レッドギラゴン",
        "types": ["creature"],
        "civs": ["light", "darkness", "fire"],
        "cost": 6, "power": 9000,
        "races": ["メガ・コマンド・ドラゴン", "侵略者"],
        "mana": 1,
        "neo": True,
        "evolve_from": {"owner": "you", "races": ["ドラゴン"],
                        "types": ["creature"]},
        "declare": {"subject": {"owner": "you",
                                "filter": {"race_has": "ドラゴン",
                                           "cost_ge": 5,
                                           "types": ["creature"]}}},
        "text": TEXT,
        "abilities": [ATTACK_END_TRIGGER, FORM_TRIGGER],
        "keywords": ["double_breaker"]}


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _unsup(r):
    return [u.get("need") if isinstance(u, dict) else u
            for u in (((r.get("partial") or {}).get("source") or {})
                      .get("unsupported") or [])]


def test_target_registered():
    rows = _rows()
    assert len(rows) <= 2064  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10254  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    assert TARGET in ids and TARGET not in rows   # 漏れ0
    c = next(c for c in conv if c["id"] == TARGET)
    assert not (c.get("source") or {}).get("unsupported")
    assert not (c.get("source") or {}).get("aliases")   # alias なし
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "neo", "evolve_from", "declare", "text",
              "abilities", "keywords"):
        assert c.get(k) == FORM[k], k
    assert len(c["abilities"]) == 2       # [攻撃の終わり誘発, 破壊誘発]
    assert c["keywords"] == ["double_breaker"]
    # under_dragons_return_on_destroy は完全に解消（ファミリー単独行）
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


def test_established_form_parses():
    d = parse_card(FORM, TABLES)
    # parse 展開後はキーワード由来の static が先頭に付く
    assert [a.get("kind") for a in d.abilities] == ["static", "trigger", "trigger"]
    assert d.abilities[1]["when"]["event"] == "attack_end"
    assert d.abilities[2] == FORM_TRIGGER
    assert d.keywords == ["double_breaker"]
    assert d.neo and d.evolve_from == FORM["evolve_from"]
    # declare は CardDef の属性にはならず、登録形の raw 比較
    # （test_target_registered の FORM 照合）で固定する
    # 登録カード自身も parse でき、同じ展開になる
    c = _conv_cache.find(CONVERTED, TARGET)
    d2 = parse_card(c, TABLES)
    assert [a.get("kind") for a in d2.abilities] == ["static", "trigger", "trigger"]
    assert d2.abilities[2] == FORM_TRIGGER
