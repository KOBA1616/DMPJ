"""再変換ラウンド351（第316弾 filter_not_keyword）の記録テスト。

- 新規登録1件: dm18-022 ジャスティス・バインド。
- alias 畳み込み1件: dm06-016 → dm18-022（identity の
  canon_id 実測で dm18-022 が正本。partial の aliases
  記録だけで決めたのではない）。
- stale クリーンアップ0件・差し戻し0件。
- 対象2行は gaps = [filter_not_keyword] を持つため
  reopen で外してから submit。
- converted 10,254→10,255 / rejects 2,064→2,062、
  canonical 重なり0・漏れ0。filter_not_keyword は
  ファミリーがこの2行だけだったため完全に解消。

登録形は第316弾の確立形と完全一致（submit の連結・
merge_split 由来の混入なし、spell は [tap 1件] ちょうど
で filter が {types: [creature], not_keyword: blocker}、
keywords は [s_trigger] のまま）:
- dm18-022 の partial は tap 形が完成済みで、filter に
  not_keyword: blocker を追加し unsupported を除去。
- dm06-016 は同じ spell を補った形で alias として畳み込み。

実挙動は登録カード自身で固定する（対照には第316弾プロト
T971〔ブロッカー付与〕と既存 T001〔バニラ〕/ T004
〔印刷ブロッカー〕を使う）。ドライバは scenario.build の
薄い包みで、tests.conftest は import しない（第319弾
以降の作法）。
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

TARGET = "dm18-022"
ALIAS = "dm06-016"
GAP = "filter_not_keyword"

TEXT = ("S・トリガー(この呪文をシールドゾーンから手札に加える時、"
        "コストを支払わずにすぐ唱えてもよい)\n"
        "バトルゾーンにある、「ブロッカー」以外のクリーチャーをすべてタップする。")

SPELL = [{"op": "tap",
          "select": {"zone": "bz", "owner": "any",
                     "filter": {"types": ["creature"],
                                "not_keyword": "blocker"},
                     "count": "all"}}]

FORM = {"id": TARGET,
        "name": "ジャスティス・バインド",
        "types": ["spell"],
        "civs": ["light"],
        "cost": 4,
        "mana": 1,
        "text": TEXT,
        "spell": SPELL,
        "keywords": ["s_trigger"]}


def _reject_rows():
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


def test_round351_disposition():
    rej = _reject_rows()
    assert len(rej) == 2062
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10255
    assert not (ids & set(rej))          # canonical 重なり0
    # 漏れ0: 正本は登録され、alias は独立エントリにも
    # reject 行にも残っていない
    assert TARGET in ids and TARGET not in rej
    assert ALIAS not in ids and ALIAS not in rej
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == [ALIAS]
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    for k in ("name", "types", "civs", "cost", "mana", "text",
              "spell", "keywords"):
        assert c.get(k) == FORM[k], k
    assert len(c["spell"]) == 1          # tap 1件ちょうど
    assert c["spell"][0]["select"]["filter"] == {
        "types": ["creature"], "not_keyword": "blocker"}
    d = parse_card(c, TABLES)
    assert d.types == ["spell"] and d.civs == ["light"]
    assert d.keywords == ["s_trigger"] and d.spell == SPELL
    # filter_not_keyword は完全に解消（ファミリーはこの2行だけ）
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


# ---------- 実挙動ドライバ（scenario.build 直包み、第316弾本体と同型） ----------

CARD = TARGET


def _build(rules, p0, p1):
    return scenario.build(
        rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                "deck_size": 20, "deck_exact": [True, True]})


def _by_defn(e, zone, defn, player=0):
    return [c for c in e.zlist(zone, player)
            if e.s.cards[c].defn == defn
            and (zone != "bz" or e.s.cards[c].controller == player)]


def _run(e, handler, limit=900, done=None):
    for _ in range(limit):
        if e.s.result is not None or (done and done()):
            return
        d = e.advance()
        if d is None:
            return
        r = handler(e, d)
        if r is not None:
            e.answer(r)
            continue
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["min"] == 0:
            e.answer([])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("run did not finish")


def _cast_handler(e, d):
    keys = [o["key"] for o in d["options"]]
    if d["kind"] == "main" and d["player"] == 0 and f"play:{CARD}" in keys:
        return [keys.index(f"play:{CARD}")]
    if d["kind"] == "pay_mana":
        return [0]
    return None


def _tapped(e, zone, defn, player):
    cs = _by_defn(e, zone, defn, player)
    assert len(cs) == 1, (zone, defn, player, cs)
    return e.s.cards[cs[0]].tapped


def _cast(e):
    _run(e, _cast_handler,
         done=lambda: len(_by_defn(e, "graveyard", CARD, 0)) == 1)


# ---------- 実挙動（登録形） ----------

def test_registered_taps_all_non_blockers_both_sides(rules):
    """dm18-022: 自分・相手どちらのバニラもタップし、
    印刷ブロッカーはどちらの側もタップしない。"""
    e = _build(rules,
               {"hand": [CARD], "mana": ["T004"] * 4,
                "bz": ["T001", "T004"], "deck": ["T002"] * 8},
               {"bz": ["T001", "T004"], "deck": ["T002"] * 8})
    _cast(e)
    assert _tapped(e, "bz", "T001", 0) is True
    assert _tapped(e, "bz", "T004", 0) is False
    assert _tapped(e, "bz", "T001", 1) is True
    assert _tapped(e, "bz", "T004", 1) is False


def test_registered_granted_blocker_is_not_tapped(rules):
    """T971 の静的でブロッカーを得た T001 は「ブロッカー
    以外」に入らない（付与分を含む特性値で判定）。T971
    本体は付与対象外かつ印刷ブロッカーも無いのでタップ
    する。相手のバニラは通常どおりタップする。"""
    e = _build(rules,
               {"hand": [CARD], "mana": ["T004"] * 4,
                "bz": ["T971", "T001"], "deck": ["T002"] * 8},
               {"bz": ["T001"], "deck": ["T002"] * 8})
    _cast(e)
    assert _tapped(e, "bz", "T001", 0) is False   # 付与ブロッカー
    assert _tapped(e, "bz", "T971", 0) is True    # 本体は対象
    assert _tapped(e, "bz", "T001", 1) is True
