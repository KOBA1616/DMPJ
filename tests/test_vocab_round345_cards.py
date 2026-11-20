"""再変換ラウンド345（第310弾 opt_reduce_then_entry_destroy）の記録テスト。

- 新規登録1件: dmrp12-008 帝神龍装 ティーゾリス。
  alias 畳み込み・stale クリーンアップ・差し戻しは0件。
- 正本判定は identity の実データ照合による: canon_id は
  dmrp12-008 自身＝独立正本、aliases_for は空（alias なし）。
- converted 10,248→10,249 / rejects 2,073→2,072、
  canonical 重なり0・漏れ0。opt_reduce_then_entry_destroy は解消。
- reopen（opt_reduce_then_entry_destroy）は対象1件だけを外した。

登録形は第310弾の確立形 FORM と完全一致（submit の連結・
merge_split 由来の混入なし、abilities は [trigger_double
常在型, opt_reduce 常在型] の2件ちょうど）:
- partial（第264弾で離脱型 trigger_double と W・ブレイカーを
  解決して保存済み）＋ {kind: static, affects: self,
  zone: hand, mod: {opt_reduce: {amount: 2,
  then: entry_destroy}}}。unsupported は除去。
- text は reject 行の正式本文と同一。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の
作法）。相手役・破壊対象役はプロト T001 / T002 を使う。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

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


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round345_disposition():
    rej = _reject_rows()
    assert len(rej) == 2072
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10249
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv(TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert TARGET not in rej             # 漏れ0
    assert not (c.get("source") or {}).get("aliases")   # alias なし
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    for k in ("name", "types", "civs", "cost", "power", "mana",
              "races", "keywords", "text", "abilities"):
        assert c.get(k) == FORM[k], k
    assert len(c["abilities"]) == 2      # [trigger_double, opt_reduce]
    d = parse_card(c, TABLES)
    assert d.cost == 6 and d.power == 7000
    # opt_reduce_then_entry_destroy は解消
    holders = {rid for rid, r in rej.items()
               if "opt_reduce_then_entry_destroy" in (r.get("gaps") or [])}
    assert holders == set(), holders


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(
        rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                "deck_size": 20, "deck_exact": [True, True]})


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)
            if zone != "bz" or e.s.cards[c].controller == p]


def _tapped_mana(e, p):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def _play(e, *, reduce, destroy=None, done, limit=600):
    """登録カードを出し、done() が真になったら止める（ターンを
    進めるとマナがアンタップされて支払い枚数を読めなくなるため、
    状態で止める）。destroy は破壊対象の defn 名。"""
    for _ in range(limit):
        if done():
            return True
        d = e.advance()
        if d is None:
            return done()
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and f"play:{TARGET}" in keys:
            e.answer([keys.index(f"play:{TARGET}")])
            continue
        if d["kind"] == "choose_cards" and "reduce" in keys:
            e.answer([keys.index("reduce" if reduce else "normal")])
            continue
        if d["kind"] == "choose_cards" and destroy is not None:
            idx = [i for i, o in enumerate(d["options"])
                   if f":{destroy}:" in o["key"]]
            if idx:
                e.answer(idx[:1])
                destroy = None
                continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["min"] == 0:
            e.answer([])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("play did not finish")


# ---------- 実挙動（登録形） ----------

def test_registered_reduce_then_destroy_other(rules):
    """dmrp12-008: 軽減して出すと、出た時に自分のクリーチャー
    1体を破壊する（他を選べる。支払いは 6-2=4 枚）。"""
    e = _build(rules, {"hand": [TARGET], "bz": ["T001"],
                       "mana": ["T008", "T001", "T001", "T001"],
                       "deck": ["T002"] * 6},
               {"deck": ["T002"] * 6})
    assert _play(e, reduce=True, destroy="T001",
                 done=lambda: "T001" in _defns(e, "graveyard", 0))
    assert TARGET in _defns(e, "bz", 0)
    assert "T001" in _defns(e, "graveyard", 0)
    assert "T001" not in _defns(e, "bz", 0)
    assert _tapped_mana(e, 0) == 4          # 6 - 2 = 4 枚支払い


def test_registered_normal_play_no_destroy(rules):
    """dmrp12-008: 軽減しなければ出た時の破壊は起きない
    （全額6枚支払い）。"""
    e = _build(rules, {"hand": [TARGET], "bz": ["T001"],
                       "mana": ["T008", "T001", "T001", "T001",
                                "T001", "T001"],
                       "deck": ["T002"] * 6},
               {"deck": ["T002"] * 6})
    assert _play(e, reduce=False,
                 done=lambda: TARGET in _defns(e, "bz", 0))
    assert TARGET in _defns(e, "bz", 0)
    assert "T001" in _defns(e, "bz", 0)
    assert _defns(e, "graveyard", 0) == []
    assert _tapped_mana(e, 0) == 6
