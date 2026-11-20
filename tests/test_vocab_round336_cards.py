"""再変換ラウンド336（第301弾 reveal_stay）の記録テスト。

- 新規登録3件: dmr05-v03 黄金世代 鬼丸「爆」（形A＋第2節）/
  dmx15-006 夢幻界廊 ヴァリアント（形B）/ dmx16-006
  インフィニティ・ドラゴン（形C）。
- alias 畳み込み: dmx16-006 の別印刷4件（dm22-015 / dmc36-017 /
  dmc49-019 / dmx09-018）は partial の source.aliases 由来で
  dmx16-006 の alias に畳み込まれた（いずれも独立エントリではなく、
  reject 行も元々無い）。
- 差し戻し・stale 解消は0件。
- converted 10,229→10,232 / rejects 2,093→2,090、重なり0・漏れ0。
  reveal_stay は誤ラベルの dmrp22-005 にのみ残る（unsupported の
  実体は別条項＋play_from_deck_top。第301弾で記録のみとし、
  行には触っていない）。

登録形の要点（第301弾で実挙動固定した形どおり）:
- 3件とも新 op move_to_event を使う置換形。instead 内では
  「choose で束縛 → ref が生きている間に判定 → 移動を発行」の順。
- submit の連結・merge_split 由来の混入が無いことを、登録形の
  abilities・keywords の完全一致で固定する。

実挙動は登録カード自身で固定する（形A=公開で滞留／外れて破壊＋
第2節、形B=バウンス回避／再適用、形C=監視で滞留／外れて破壊）。
ドライバは第301弾のプロトテストと同形（scenario.build の薄い包み。
tests.conftest は import しない）。
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

V03 = "dmr05-v03"
X15 = "dmx15-006"
X16 = "dmx16-006"
X16_ALIASES = ["dm22-015", "dmc36-017", "dmc49-019", "dmx09-018"]
TARGETS = (V03, X15, X16)

FORM_A = {"kind": "replace",
          "when": {"event": "move", "from": "bz", "to": "graveyard",
                   "reason": "destroy", "subject": "self"},
          "instead": [
              {"op": "choose",
               "select": {"zone": "deck", "owner": "you", "from_top": 1,
                          "count": 1},
               "reveal": True, "as": "top"},
              {"op": "if",
               "cond": {"not": {"exists": {"ref": "top",
                                           "filter": {"race_has": "ヒューマノイド"}}}},
               "then": [{"op": "move_to_event",
                         "select": {"ref": "event.subject"}}]}]}
FORM_A_C2 = {"kind": "trigger",
             "when": {"event": "move", "from": "bz", "to": "graveyard",
                      "reason": "destroy", "subject": "self"},
             "effect": [{"op": "may", "body": [
                 {"op": "play_free",
                  "select": {"ref": "event.was_under",
                             "zone": "graveyard"}}]}]}
FORM_B = {"kind": "replace",
          "when": {"event": "move", "from": "bz", "subject": "self"},
          "instead": [
              {"op": "may", "body": [
                  {"op": "choose",
                   "select": {"zone": "deck", "owner": "you", "from_top": 1,
                              "count": 1},
                   "as": "picked"}]},
              {"op": "if",
               "cond": {"exists": {"ref": "picked"}},
               "then": [{"op": "move", "select": {"ref": "picked"},
                         "to": "graveyard", "reason": "put"}]},
              {"op": "if",
               "cond": {"not": {"exists": {"ref": "picked",
                                           "filter": {"race_has": "アウトレイジ"}}}},
               "then": [{"op": "move_to_event",
                         "select": {"ref": "event.subject"}}]}]}
FORM_C = {"kind": "replace",
          "when": {"event": "move", "from": "bz",
                   "subject": {"owner": "you",
                               "filter": {"types": ["creature"],
                                          "race_has": "ドラゴン"}}},
          "instead": [
              {"op": "choose",
               "select": {"zone": "deck", "owner": "you", "from_top": 1,
                          "count": 1},
               "as": "seen"},
              {"op": "move", "select": {"ref": "seen"},
               "to": "graveyard", "reason": "put"},
              {"op": "if",
               "cond": {"not": {"any": [
                   {"exists": {"ref": "seen",
                               "filter": {"race_has": "ドラゴン"}}},
                   {"exists": {"ref": "seen",
                               "filter": {"race_has": "ファイアー・バード"}}}]}},
               "then": [{"op": "move_to_event",
                         "select": {"ref": "event.subject"}}]}]}
FORMS = {V03: [FORM_A, FORM_A_C2], X15: [FORM_B], X16: [FORM_C]}
KEYWORDS = {V03: ["triple_breaker"], X15: ["double_breaker"],
            X16: ["double_breaker"]}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round336_disposition():
    rej = _reject_rows()
    assert len(rej) == 2090
    for tid in TARGETS:
        c = _conv(tid)
        assert c is not None, tid
        assert c["keywords"] == KEYWORDS[tid], tid
        assert c["abilities"] == FORMS[tid], tid   # 混入・重複なし
        assert not (c.get("source") or {}).get("unsupported"), tid
        parse_card(c, TABLES)
        assert tid not in rej, tid
    # alias 畳み込み: 独立エントリではなく、reject 行も無い
    assert (_conv(X16).get("source") or {}).get("aliases") == X16_ALIASES
    for a in X16_ALIASES:
        assert _conv(a) is None, a
        assert a not in rej, a
    # reveal_stay は誤ラベルの dmrp22-005 にのみ残る（行は不変）
    holders = {rid for rid, r in rej.items()
               if "reveal_stay" in (r.get("gaps") or [])}
    assert holders == {"dmrp22-005"}, holders
    assert "play_from_deck_top" in rej["dmrp22-005"]["gaps"]
    ids = {x["id"] for x in _conv_cache.all_cards(CONVERTED)}
    assert len(ids) == 10232
    assert not (ids & set(rej))


# ---------- 実挙動ドライバ（第301弾のものと同形） ----------

def _defns(e, zone, p=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _wire(e, host_defn, under_defns, p=0):
    host = next(c for c in e.zlist("bz", p) if e.s.cards[c].defn == host_defn
                and e.s.cards[c].top_of < 0)
    unders = []
    for ud in under_defns:
        u = next(c for c in e.zlist("bz", p) if e.s.cards[c].defn == ud
                 and e.s.cards[c].top_of < 0 and c != host)
        e.s.cards[u].top_of = host
        unders.append(u)
    e.s.cards[host].under = unders
    e.s.cards[host].stack_bases = list(unders)
    return host, unders


def _drive(e, done, cast=None, cast_player=1, target_defn=None,
           pick_defn=None, yes=True, steps=400):
    st = {"cast": False}
    for _ in range(steps):
        if done(e):
            return st
        d = e.advance()
        assert d is not None, "game ended before done"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "main" and cast and not st["cast"] \
                and d.get("player") == cast_player and f"play:{cast}" in keys:
            e.answer([keys.index(f"play:{cast}")])
            st["cast"] = True
        elif kind == "choose_cards":
            idx = None
            for want in (pick_defn, target_defn):
                if not want:
                    continue
                for o in d["options"]:
                    if e.s.cards[o["cid"]].defn == want:
                        idx = keys.index(o["key"])
                        break
                if idx is not None:
                    break
            e.answer([idx] if idx is not None else list(range(d["min"])))
        elif kind == "yes_no":
            want = "yes" if yes else "no"
            e.answer([keys.index(want)] if want in keys
                     else list(range(d["min"])))
        elif kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("drive budget exhausted")


def _pub(e, kind, defn=None):
    return [r for r in e.s.pub if r["kind"] == kind
            and (defn is None or r.get("defn") == defn)]


def _build_exact(rules, p0, deck_card, p1):
    spec0 = dict(p0)
    spec0["deck"] = [deck_card] * 4
    return scenario.build(
        rules, {"p0": spec0, "p1": p1, "filler": "T002", "seed": 1,
                "deck_exact": [True, False]})


P1_DESTROY = {"hand": ["T056"], "mana": ["T008"] * 3}
P1_BOUNCE = {"hand": ["T140"], "mana": ["T010"] * 3}


# ---------- 形A（登録形）: dmr05-v03 ----------

def test_registered_v03_form_a_match_stays(rules):
    """上がヒューマノイドなら破壊されずにとどまる（スタックも無事）。
    公開は記録され、第2節は誘発しない。"""
    e = _build_exact(rules, {"bz": [V03, "T001"]}, "T914", dict(P1_DESTROY))
    host, unders = _wire(e, V03, ["T001"])
    _drive(e, lambda e: "T056" in _defns(e, "graveyard", 1) and _quiet(e),
           cast="T056", target_defn=V03)
    assert V03 in _defns(e, "bz")
    assert e.s.cards[host].under == unders
    assert V03 not in _defns(e, "graveyard")
    assert "T001" not in _defns(e, "graveyard")
    assert _pub(e, "reveal", defn="T914")


def test_registered_v03_form_a_nomatch_destroyed_and_under_returns(rules):
    """上がヒューマノイドでなければ通常どおり破壊され（公開はされる）、
    再適用された破壊から第2節が誘発し、下にあったカードが戻る。"""
    e = _build_exact(rules, {"bz": [V03, "T001"]}, "T003", dict(P1_DESTROY))
    _wire(e, V03, ["T001"])
    _drive(e, lambda e: V03 in _defns(e, "graveyard") and _quiet(e),
           cast="T056", target_defn=V03)
    assert V03 in _defns(e, "graveyard")
    assert _pub(e, "reveal", defn="T003")
    assert "T001" in _defns(e, "bz")
    assert "T001" not in _defns(e, "graveyard")


# ---------- 形B（登録形）: dmx15-006 ----------

def test_registered_x15_form_b_match_stays(rules):
    """バウンスされても、墓地に置いた上がアウトレイジならとどまる。"""
    e = _build_exact(rules, {"bz": [X15]}, "T915", dict(P1_BOUNCE))
    _drive(e, lambda e: "T140" in _defns(e, "graveyard", 1) and _quiet(e),
           cast="T140", target_defn=X15, pick_defn=X15)
    assert X15 in _defns(e, "bz")
    assert X15 not in _defns(e, "hand")
    assert "T915" in _defns(e, "graveyard")


def test_registered_x15_form_b_nomatch_bounced(rules):
    """上がアウトレイジでなければ、元の移動（手札へ）が再適用される。"""
    e = _build_exact(rules, {"bz": [X15]}, "T003", dict(P1_BOUNCE))
    _drive(e, lambda e: X15 in _defns(e, "hand") and _quiet(e),
           cast="T140", target_defn=X15, pick_defn=X15)
    assert X15 in _defns(e, "hand")
    assert "T003" in _defns(e, "graveyard")


# ---------- 形C（登録形）: dmx16-006 ----------

def test_registered_x16_form_c_dragon_milled_stays(rules):
    """自分のドラゴンが破壊される時、置いた上がドラゴンならとどまる。"""
    e = _build_exact(rules, {"bz": [X16, "T913"]}, "T913", dict(P1_DESTROY))
    _drive(e, lambda e: "T056" in _defns(e, "graveyard", 1) and _quiet(e),
           cast="T056", target_defn="T913")
    assert "T913" in _defns(e, "bz")
    assert _defns(e, "graveyard").count("T913") == 1  # 落ちたのはミルの1枚


def test_registered_x16_form_c_nomatch_destroyed(rules):
    """上がドラゴンでもファイアー・バードでもなければ通常どおり破壊
    される（ミルは必須で起きる）。"""
    e = _build_exact(rules, {"bz": [X16, "T913"]}, "T003", dict(P1_DESTROY))
    _drive(e, lambda e: "T913" in _defns(e, "graveyard") and _quiet(e),
           cast="T056", target_defn="T913")
    assert "T913" not in _defns(e, "bz")
    assert "T003" in _defns(e, "graveyard")
