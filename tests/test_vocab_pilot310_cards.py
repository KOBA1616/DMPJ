"""語彙パイロット第310弾の対象カード検証（ラウンド345で登録済み）。

dmrp12-008 帝神龍装 ティーゾリス は opt_reduce_then_entry_destroy
の純粋1件だった。第264弾で離脱型 trigger_double と W・ブレイカーは
解けて partial に保存済みで、残余は
「このクリーチャーの召喚コストを２少なくしてもよい。そうしたら、
このターン、このクリーチャーがバトルゾーンに出た時、自分の
クリーチャーを１体破壊する」だけだった。従来の opt_reduce.then
（destroy / deck_bottom_draw）はターン終了時の処理しか無く、
軽減したかどうかを条件に出た時の破壊を書けなかった。

第310弾で then の第3形 **entry_destroy** を追加し（defs 検証・
スキーマ列挙・h_play の遅延誘発登録。実挙動は第310弾本体の
プロト T957 で固定）、ラウンド345で登録した。本ファイルは
登録形の固定に書き換えた（実挙動は
test_vocab_round345_cards.py が登録カード自身で固定）。

登録形は partial ＋ {kind: static, affects: self, zone: hand,
 mod: {opt_reduce: {amount: 2, then: entry_destroy}}} で、
abilities は [trigger_double 常在型, opt_reduce 常在型] の
2件ちょうど（連結・merge_split 由来の混入なし）。
正本判定は identity の実データ照合による: canon_id は
dmrp12-008 自身＝独立正本、aliases は無い。text は reject 行の
正式本文と同一。

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

TARGET = "dmrp12-008"

TEXT = ("このクリーチャーの召喚コストを２少なくしてもよい。そうしたら、このターン、"
        "このクリーチャーがバトルゾーンに出た時、自分のクリーチャーを１体破壊する。\n"
        "W・ブレイカー\n"
        "自分のクリーチャーが破壊された時またはバトルゾーンを離れた時にトリガーする"
        "自分のクリーチャーの能力はすべて、１度のかわりに２度トリガーする。")

TRIGGER_DOUBLE = {"kind": "static", "affects": "self",
                  "mod": {"trigger_double":
                          {"when": {"event": "move", "from": "bz",
                                    "subject": {"owner": "you",
                                                "filter": {"types": ["creature"]}}},
                           "source": {"owner": "you",
                                      "filter": {"types": ["creature"]}}}}}

OPT_REDUCE = {"kind": "static", "affects": "self", "zone": "hand",
              "mod": {"opt_reduce": {"amount": 2, "then": "entry_destroy"}}}

FORM = {"id": TARGET,
        "name": "帝神龍装 ティーゾリス",
        "types": ["creature"],
        "civs": ["darkness"],
        "cost": 6, "power": 7000, "mana": 1,
        "races": ["ドラゴンギルド", "マフィ・ギャング"],
        "keywords": ["double_breaker"],
        "text": TEXT,
        "abilities": [TRIGGER_DOUBLE, OPT_REDUCE]}


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_target_registered():
    rows = _rows()
    assert len(rows) == 2072
    assert TARGET not in rows  # 登録により reject 行は外れた
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10249
    assert not (ids & set(rows))          # canonical 重なり0
    aliases = set()
    for c in conv:
        aliases.update((c.get("source") or {}).get("aliases") or [])
    assert TARGET in ids and TARGET not in aliases
    c = next(c for c in conv if c["id"] == TARGET)
    assert not (c.get("source") or {}).get("unsupported")
    assert not (c.get("source") or {}).get("aliases")   # alias なし
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    for k in ("name", "types", "civs", "cost", "power", "mana",
              "races", "keywords", "text", "abilities"):
        assert c.get(k) == FORM[k], k
    assert len(c["abilities"]) == 2
    # opt_reduce_then_entry_destroy は解消
    assert not {rid for rid, r in rows.items()
                if "opt_reduce_then_entry_destroy" in (r.get("gaps") or [])}


def test_established_form_parses():
    d = parse_card(FORM, TABLES)
    assert d.cost == 6 and d.power == 7000
    statics = [a for a in FORM["abilities"] if a["kind"] == "static"]
    assert len(statics) == 2
    assert statics[1]["mod"]["opt_reduce"] == {"amount": 2, "then": "entry_destroy"}
    # 登録カード自身も parse できる
    c = _conv_cache.find(CONVERTED, TARGET)
    d2 = parse_card(c, TABLES)
    assert d2.cost == 6 and d2.power == 7000
