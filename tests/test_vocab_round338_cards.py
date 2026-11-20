"""再変換ラウンド338（第303弾 dragonic_field）の記録テスト。

- 新規登録2件: dm26ex3-067（龍世界 〜龍の降臨する地〜、形A）と
  dmex15-b027（切札の里、形B）。
- alias 畳み込み1件: dmex12-011（龍世界の旧印刷）。正本判定は
  identity の実データ照合による: canon_id(dmex12-011) =
  dm26ex3-067 で aliases_for にも含まれるため独立登録しない。
  067 の source.aliases は partial の5件（dm23bd4-034 /
  dm24rp1-td2 / dm25sp2-010 / dmex16-002 / dmrp22-tr10）に
  dmex12-011 を加えた6件。alias 側に reject 行があったのは
  dmex12-011 だけで、reopen で対象3件とともに外れた。
- 差し戻し・stale 解消・converted 是正は0件。
- converted 10,235→10,237 / rejects 2,087→2,084、重なり0・
  漏れ0。dragonic_field は rejects から解消。

登録形は第303弾の確立形 FORM_A / FORM_B と完全一致（submit の
連結・merge_split 由来の混入なし、keywords の追加なし）。
submit 時の助言 lint（dm26ex3-067 の play_free/reason: summon に
対し本文は「出す」）は、第303弾で固定した形（play_free の着地は
112.3g で召喚として数える）のため形は変えていない。

実挙動は登録カード自身で固定する。ドライバは scenario.build の
薄い包みで、tests.conftest は import しない（第319弾以降の作法）。
形Aの山札は deck_exact の均一デッキ（T921 ドラゴン）でトップを
確定させる。
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

F67 = "dm26ex3-067"
B027 = "dmex15-b027"
FOLDED = "dmex12-011"
ALIASES_067 = ["dm23bd4-034", "dm24rp1-td2", "dm25sp2-010",
               "dmex12-011", "dmex16-002", "dmrp22-tr10"]

FORM_A = {"kind": "trigger",
          "when": {"event": "turn_start", "player": "you"},
          "effect": [
              {"op": "move",
               "select": {"zone": "deck", "owner": "you", "from_top": 1},
               "to": "graveyard", "reason": "put", "as": "milled"},
              {"op": "if",
               "cond": {"exists": {"ref": "milled",
                                   "filter": {"race_has": "ドラゴン",
                                              "not_types": ["evolution"]}}},
               "then": [
                   {"op": "may", "body": [
                       {"op": "move", "select": {"ref": "self"},
                        "to": "graveyard", "reason": "destroy",
                        "as": "gone"}]},
                   {"op": "if", "cond": {"exists": {"ref": "gone"}},
                    "then": [{"op": "play_free",
                              "select": {"ref": "milled"}}]}]}]}

FORM_B = [
    {"kind": "static",
     "affects": {"owner": "you", "zone": "hand",
                 "filter": {"types": ["creature"],
                            "name_has": "ボルシャック"}},
     "mod": {"cost_may": {"amount": 2, "min": 1}}},
    {"kind": "static",
     "affects": {"owner": "you", "zone": "bz",
                 "filter": {"types": ["creature"],
                            "name_has": "ボルシャック"}},
     "mod": {"grant": ["speed_attacker"]}}]


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round338_disposition():
    rej = _reject_rows()
    assert len(rej) == 2084
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10237
    assert not (ids & set(rej))          # canonical 重なり0
    for tid in (F67, B027):
        c = _conv(tid)
        assert c is not None, tid
        assert not (c.get("source") or {}).get("unsupported"), tid
        assert c["types"] == ["field", "dragonic_field"], tid
        parse_card(c, TABLES)
        assert tid not in rej, tid       # 漏れ0
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    assert _conv(F67)["abilities"] == [FORM_A]
    assert _conv(F67).get("keywords") is None
    assert _conv(B027)["abilities"] == FORM_B
    assert _conv(B027).get("keywords") is None
    # alias 畳み込み: dmex12-011 は独立エントリではなく reject 行も無い
    assert (_conv(F67).get("source") or {}).get("aliases") == ALIASES_067
    assert _conv(FOLDED) is None
    assert FOLDED not in rej
    for a in ALIASES_067:
        assert _conv(a) is None, a
        assert a not in rej, a
    # b027 は独立正本（aliases 無し）
    assert (_conv(B027).get("source") or {}).get("aliases") is None
    # ファミリー解消
    holders = {rid for rid, r in rej.items()
               if "dragonic_field" in (r.get("gaps") or [])}
    assert holders == set(), holders


# ---------- 実挙動ドライバ ----------

def _defns(e, zone, p=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _build(rules, p0, p1):
    spec0 = dict(p0)
    spec1 = dict(p1)
    spec0.setdefault("deck", ["T002"] * 6)
    spec1.setdefault("deck", ["T002"] * 6)
    return scenario.build(
        rules, {"p0": spec0, "p1": spec1, "filler": "T001", "seed": 1,
                "deck_exact": [True, True]})


def _drive_turn1(e, yes_no=(), steps=300):
    yn = list(yes_no)
    for _ in range(steps):
        if e.s.turn > 1:
            break
        d = e.advance()
        if d is None or e.s.turn > 1:
            break
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "yes_no":
            e.answer([yn.pop(0) if yn else 0])
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif kind == "declare_strigger":
            e.answer([])
        elif kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


# ---------- 形A（登録形）: dm26ex3-067 ----------

def test_registered_form_a_accept(rules):
    """承諾: フィールドは破壊され、落ちたドラゴンが出る。"""
    e = _build(rules, {"bz": [F67], "deck": ["T921"] * 6}, {})
    _drive_turn1(e, yes_no=[0])
    assert F67 in _defns(e, "graveyard", 0)
    assert "T921" in _defns(e, "bz", 0)
    assert "T921" not in _defns(e, "graveyard", 0)


def test_registered_form_a_decline(rules):
    """辞退: フィールドは残り、ドラゴンは墓地に残る。"""
    e = _build(rules, {"bz": [F67], "deck": ["T921"] * 6}, {})
    _drive_turn1(e, yes_no=[1])
    assert F67 in _defns(e, "bz", 0)
    assert "T921" in _defns(e, "graveyard", 0)
    assert "T921" not in _defns(e, "bz", 0)


# ---------- 形B（登録形）: dmex15-b027 ----------

def _tapped_mana(e, p=0):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def _play(e, defn, choice):
    st = {"offer": False, "tapped": None}
    for _ in range(120):
        d = e.advance()
        if d is None:
            break
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "charge" and "pass" in keys:
            e.answer([keys.index("pass")])
        elif kind == "main" and f"play:{defn}" in keys:
            e.answer([keys.index(f"play:{defn}")])
        elif kind == "choose_cards" and "reduce" in keys:
            st["offer"] = True
            e.answer([keys.index(choice or "normal")])
        elif kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if defn in _defns(e, "bz", 0):
            st["tapped"] = _tapped_mana(e)
            break
    return st


def test_registered_form_b_pay_with_reduction(rules):
    """ボルシャック獣（コスト5）を軽減で出すと支払いは3。"""
    e = _build(rules, {"bz": [B027], "hand": ["T923"],
                       "mana": ["T034"] * 5}, {})
    st = _play(e, "T923", "reduce")
    assert st["offer"] and st["tapped"] == 3


def test_registered_form_b_reduction_floor_is_one(rules):
    """子竜（コスト2）に軽減を使っても床1（0以下にならない）。"""
    e = _build(rules, {"bz": [B027], "hand": ["T924"],
                       "mana": ["T034"] * 2}, {})
    st = _play(e, "T924", "reduce")
    assert st["offer"] and st["tapped"] == 1
