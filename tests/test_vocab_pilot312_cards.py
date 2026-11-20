"""語彙パイロット第312弾の対象カード検証（ラウンド347で登録済み）。

dm26ex4-003 / dm26ex4-sec004 切札接続 ドールバロム 2件
（同一カードの2刷）。行の gaps は空で、ギャップ名
ex_life_shield_leave_trigger は partial.source.unsupported にのみある
NEO 期の行だった。partial は NEO進化・EXライフ・T・ブレイカーと
CIP 誘発＋モーダル3択まで完成済みで、欠けていたのは
「このクリーチャーの『EXライフ』シールドが離れた時」にも
同じモーダルが発火する第2誘発だけだった。

第312弾の結論は **ドリフト**（新規語彙・エンジン変更なし）:
離脱誘発は第190弾で実装され第291弾で登録先例のある
{event: move, from: shield, subject: {exlife_of: self}}。
確立形は partial の CIP 誘発に、その effect を共有する
離脱誘発を1件追加し、unsupported を外したもの。
実挙動は第312弾本体のプロト T963 で固定し、ラウンド347で
登録した。本ファイルは登録形の固定に書き換えた（実挙動は
test_vocab_round347_cards.py が登録カード自身で固定）。

登録形は partial ＋ 離脱誘発の追加で、abilities は
[CIP誘発, 離脱誘発] の2件ちょうど、両誘発の effect は同一
モーダル（連結・merge_split 由来の混入なし）。正本判定は
identity の実データ照合による: canon_id(dm26ex4-sec004)
= dm26ex4-003 で、sec004 は独立登録せず alias として
畳み込んだ（submit では sec004 の reject 行が外れなかった
ため、stale 行として行だけを除去した）。対象行は gaps が
空のため reopen では外れず直接 submit で登録した
（第323・343弾の先例）。text は reject 行の正式本文と同一。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活
するので _conv_cache を直接使う（第319弾以降の作法）。
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

TARGET = "dm26ex4-003"
ALIAS = "dm26ex4-sec004"
GAP = "ex_life_shield_leave_trigger"

TEXT = ("NEO進化：闇のクリーチャー１体の上に置いてもよい。\n"
        "EXライフT・ブレイカー\n"
        "このクリーチャーが出た時またはこのクリーチャーの「EXライフ」シールドが離れた時、"
        "次の中から１回選ぶ。\n"
        "▶相手は自身の手札を表向きにし、その中から闇ではないカードをすべて捨てる。\n"
        "▶闇ではないクリーチャーをすべて破壊する。\n"
        "▶相手のマナゾーンにある闇ではないカードはすべて、"
        "次の自分のターンのはじめまでアンタップしない。")

MODAL = {"op": "modal", "modes": [
    [{"op": "discard",
      "select": {"zone": "hand", "owner": "opp", "chooser": "opp",
                 "filter": {"not_civs": ["darkness"]}, "count": "all"}}],
    [{"op": "destroy",
      "select": {"zone": "bz", "owner": "any",
                 "filter": {"types": ["creature"],
                            "not_civs": ["darkness"]},
                 "count": "all"}}],
    [{"op": "modify",
      "select": {"zone": "mana", "owner": "opp",
                 "filter": {"not_civs": ["darkness"]}, "count": "all"},
      "mod": {"deny": ["untap_at_start"]},
      "duration": "until_next_own_turn_start"}]]}

CIP_TRIGGER = {"kind": "trigger",
               "when": {"event": "move", "to": "bz", "subject": "self"},
               "effect": [MODAL]}

LEAVE_TRIGGER = {"kind": "trigger",
                 "when": {"event": "move", "from": "shield",
                          "subject": {"exlife_of": "self"}},
                 "effect": [MODAL]}

FORM = {"id": TARGET,
        "name": "切札接続 ドールバロム",
        "types": ["creature"],
        "civs": ["darkness"],
        "cost": 10, "power": 15000,
        "races": ["ディスペクター", "デスパペット", "デーモン・コマンド"],
        "mana": 1,
        "neo": True,
        "evolve_from": {"civs": ["darkness"], "types": ["creature"]},
        "text": TEXT,
        "abilities": [CIP_TRIGGER, LEAVE_TRIGGER],
        "keywords": ["ex_life", "triple_breaker"]}


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_registered():
    rows = _rows()
    assert len(rows) == 2069
    assert TARGET not in rows and ALIAS not in rows  # 両行とも外れた
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10251
    assert not (ids & set(rows))          # canonical 重なり0
    aliases = set()
    for c in conv:
        aliases.update((c.get("source") or {}).get("aliases") or [])
    assert TARGET in ids
    assert ALIAS not in ids and ALIAS in aliases   # alias 畳み込み
    c = next(c for c in conv if c["id"] == TARGET)
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == [ALIAS]
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "neo", "evolve_from", "text", "abilities",
              "keywords"):
        assert c.get(k) == FORM[k], k
    assert len(c["abilities"]) == 2
    assert c["abilities"][0]["effect"] == c["abilities"][1]["effect"]
    # ex_life_shield_leave_trigger は解消
    def _unsup(r):
        return ((r.get("partial") or {}).get("source") or {}) \
            .get("unsupported") or []
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


def test_established_form_parses():
    d = parse_card(FORM, TABLES)
    trigs = [a for a in d.abilities if a["kind"] == "trigger"]
    assert len(trigs) == 2
    assert trigs[0]["when"] == {"event": "move", "to": "bz",
                                "subject": "self"}
    assert trigs[1]["when"] == {"event": "move", "from": "shield",
                                "subject": {"exlife_of": "self"}}
    assert trigs[0]["effect"] == trigs[1]["effect"]   # 同一モーダル
    modal = trigs[0]["effect"][0]
    assert modal["op"] == "modal" and len(modal["modes"]) == 3
    assert sorted(d.keywords) == ["ex_life", "triple_breaker"]
    assert d.civs == ["darkness"] and d.cost == 10
    # 登録カード自身も parse できる
    c = _conv_cache.find(CONVERTED, TARGET)
    d2 = parse_card(c, TABLES)
    assert len([a for a in d2.abilities if a["kind"] == "trigger"]) == 2
