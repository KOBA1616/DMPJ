"""再変換ラウンド353（第318弾 shield_to_hand_strigger_deny）の記録テスト。

- 新規登録2件: dm24ex3-or1 超天使 ゴルドラン・ゴルギーニ
  （形A2）/ dmrp22-031 エメラルの海幻（形A1）。
- alias 畳み込み1件分: dm24ex3-or1 の alias 4件
  （dm24ex3-rp3or1 / dm24ex3-rp3sec01 / dm24rp3-or01 /
  dm24rp3-sec001）は登録エントリの source.aliases への
  畳み込みで、独立エントリにも reject 行にも無い。
  dmrp22-031 は alias 無し。正本判定は identity の
  canon_id 実測で2件とも自 ID。
- stale クリーンアップ0件・差し戻し0件。
- 対象2行は gaps = [shield_to_hand_strigger_deny] のため
  reopen で外してから submit（reopen の出力は対象2件
  ちょうどだった）。
- converted 10,258→10,260 / rejects 2,059→2,057、
  canonical 重なり0・漏れ0。shield_to_hand_strigger_deny
  はファミリーがこの2件だけだったため完全に解消。

登録形は第318弾の確立形と完全一致（submit の連結・
merge_split 由来の混入なし）: 両件とも abilities は
2件ちょうどで、手札へ加える move にだけ strigger: "off"
の印が付く。dmrp22-031 の text は partial が切れて
いたため公式全文に差し替えた。

実挙動は登録カード自身で固定する（第318弾本体の観点を
登録形で再現）。ドライバは scenario.build の薄い包みで、
tests.conftest は import しない（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

GAP = "shield_to_hand_strigger_deny"
ALIASES_OR1 = ["dm24ex3-rp3or1", "dm24ex3-rp3sec01",
               "dm24rp3-or01", "dm24rp3-sec001"]

TEXT_OR1 = ("ハイパーエナジー（このクリーチャーを召喚する時、コストが異なる"
            "自分のクリーチャーを好きな数タップしてもよい。こうしてタップした"
            "クリーチャー１体につき、このクリーチャーの召喚コストを２少なく"
            "する。ただし、コストは０以下にはならない）\n"
            "ブロッカーT・ブレイカー\n"
            "このクリーチャーが出た時、次の自分のターンのはじめまで、"
            "このクリーチャーは離れない。\n"
            "自分のクリーチャーが攻撃する時、自分の山札の上から１枚目を"
            "シールド化してもよい。その後、自分のシールドが10以上あれば、"
            "自分のシールドを好きな数選び、表向きにする。その中から"
            "クリーチャーをすべて出し、残りを手札に加える。ただし、"
            "その「S・トリガー」は使えない。")
TEXT_031 = ("シンカライズ：このタマシードがクリーチャーであるかのように、"
            "この上に進化クリーチャーを置いてもよい。\n"
            "このタマシードが出た時、カードを１枚引く。\n"
            "シンカパワー：このタマシードが進化する時、自分の手札を１枚"
            "シールド化し、その後、自分のシールドを１つ選んで手札に加える。"
            "ただし、その「S・トリガー」は使えない。")

ABILITIES_OR1 = [
    {"kind": "trigger",
     "when": {"event": "move", "to": "bz", "subject": "self"},
     "effect": [{"op": "modify", "select": {"ref": "self"},
                 "mod": {"no_leave": True},
                 "duration": "until_next_own_turn_start"}]},
    {"kind": "trigger",
     "when": {"event": "attack",
              "subject": {"owner": "you",
                          "filter": {"types": ["creature"]}}},
     "effect": [
         {"op": "may",
          "body": [{"op": "move",
                    "select": {"zone": "deck", "owner": "you",
                               "from_top": 1, "count": 1},
                    "to": "shield", "reason": "charge"}]},
         {"op": "if",
          "cond": {"cmp": [{"count": {"zone": "shield", "owner": "you"}},
                           ">=", 10]},
          "then": [
              {"op": "choose",
               "select": {"zone": "shield", "owner": "you",
                          "count": "any"},
               "as": "shs"},
              {"op": "flip_up",
               "select": {"bundle_of": "shs", "count": "all"}},
              {"op": "choose",
               "select": {"bundle_of": "shs", "count": "all"},
               "as": "fc"},
              {"op": "move",
               "select": {"ref": "fc",
                          "filter": {"types": ["creature"]},
                          "count": "all"},
               "to": "bz", "reason": "put"},
              {"op": "move",
               "select": {"ref": "fc",
                          "filter": {"not_types": ["creature"]},
                          "count": "all"},
               "to": "hand", "reason": "put",
               "strigger": "off"}]}]},
]
ABILITIES_031 = [
    {"kind": "trigger",
     "when": {"event": "move", "to": "bz", "subject": "self"},
     "effect": [{"op": "draw", "count": 1}]},
    {"kind": "trigger",
     "when": {"event": "evolve_base", "subject": "self"},
     "effect": [
         {"op": "move",
          "select": {"zone": "hand", "owner": "you", "count": 1},
          "to": "shield", "reason": "charge"},
         {"op": "move",
          "select": {"zone": "shield", "owner": "you", "count": 1},
          "to": "hand", "reason": "put", "strigger": "off"}]},
]

FORMS = {
    "dm24ex3-or1": {"name": "超天使 ゴルドラン・ゴルギーニ",
                    "types": ["creature"], "civs": ["light"], "cost": 10,
                    "power": 14000,
                    "races": ["メカ・エンジェル・コマンド"], "mana": 1,
                    "text": TEXT_OR1,
                    "keywords": ["hyper_energy", "blocker", "triple_breaker"],
                    "abilities": ABILITIES_OR1, "proto": "T977",
                    "aliases": ALIASES_OR1},
    "dmrp22-031": {"name": "エメラルの海幻",
                   "types": ["tamaseed"], "civs": ["water"], "cost": 3,
                   "power": None,
                   "races": ["サイバーロード", "レクスターズ"], "mana": 1,
                   "text": TEXT_031,
                   "keywords": ["shinka_rise"],
                   "abilities": ABILITIES_031, "proto": "T975",
                   "aliases": None},
}


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


def test_round353_disposition():
    rej = _reject_rows()
    assert len(rej) == 2057
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10260
    assert not (ids & set(rej))          # canonical 重なり0
    for tid, spec in FORMS.items():
        # 漏れ0: 正本は登録され reject 行に残っていない
        assert tid in ids and tid not in rej, tid
        for a in spec["aliases"] or []:
            assert a not in ids and a not in rej, a
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None
        assert not (c.get("source") or {}).get("unsupported")
        assert (c.get("source") or {}).get("aliases") == spec["aliases"], tid
        # 登録形の完全一致（連結・merge_split 由来の混入なし）
        for k in ("name", "types", "civs", "cost", "power", "races",
                  "mana", "text", "keywords", "abilities"):
            assert c.get(k) == spec[k], (tid, k)
        assert len(c["abilities"]) == 2, tid
        d = parse_card(c, TABLES)
        assert d.abilities == parse_card(proto_card(spec["proto"]),
                                         TABLES).abilities, tid
    # shield_to_hand_strigger_deny は完全に解消（ファミリーはこの2件だけ）
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(
        rules, {"p0": p0, "p1": p1, "filler": "T007", "seed": 1,
                "deck_size": 20, "deck_exact": [True, True]})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _fallback(e, d, keys):
    if "pass" in keys:
        e.answer([keys.index("pass")])
    elif d["min"] == 0:
        e.answer([])
    else:
        e.answer(list(range(d["min"])))


def test_registered_form_a1_return_suppresses_strigger(rules):
    """登録形A1: dmrp22-031 のシンカパワーで手札に加えた
    シールド（T960）は宣言できない。"""
    e = _build(rules,
               {"bz": ["dmrp22-031"], "hand": ["T077", "T001", "T002"],
                "mana": ["T010", "T001", "T001"],
                "shield": ["T960", "T001", "T001", "T001", "T001"],
                "deck": ["T002"] * 6},
               {"deck": ["T002"] * 8})
    t960 = next(c for c in e.zlist("shield", 0)
                if e.cdef(c).id == "T960")
    seen = []
    played = False
    for _ in range(600):
        if t960 in e.zlist("hand", 0) and _quiet(e):
            break
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        seen.append(kind)
        keys = [o["key"] for o in d["options"]]
        if kind == "declare_strigger":
            e.answer([])          # 宣言しない（機会の有無だけを見る）
        elif kind == "main" and not played:
            hit = [i for i, k in enumerate(keys) if k == "play:T077"]
            if hit:
                played = True
                e.answer([hit[0]])
            else:
                _fallback(e, d, keys)
        elif kind == "choose_evo_source":
            hit = [i for i, k in enumerate(keys)
                   if k.startswith("bz:dmrp22-031")]
            e.answer([hit[0]] if hit else [0])
        elif kind == "choose_cards":
            hit = [i for i, o in enumerate(d["options"])
                   if o["cid"] == t960]
            if hit:
                e.answer(hit[:1])
            else:
                t1 = [i for i, o in enumerate(d["options"])
                      if e.cdef(o["cid"]).id == "T001"]
                e.answer(t1[:1] if t1 else list(range(d.get("min", 0))))
        elif kind == "pay_mana":
            e.answer([0])
        elif kind == "yes_no":
            e.answer([keys.index("yes")])
        else:
            _fallback(e, d, keys)
    assert "T960" in _defns(e, "hand", 0)
    assert "declare_strigger" not in seen
    assert e.s.cards[t960].strigger_off is True     # 印が付いている
    assert len(e.zlist("shield", 0)) == 5           # 化1＋戻し1で不変
    top = next(c for c in e.bz_tops(0) if e.cdef(c).id == "T077")
    assert e.s.cards[e.s.cards[top].under[0]].defn == "dmrp22-031"


def test_registered_form_a2_split_suppresses_strigger(rules):
    """登録形A2: dm24ex3-or1 の攻撃誘発で表向きにした束:
    クリーチャー（T001）は場へ、呪文（T960）は手札へ。
    T960 は宣言できない。"""
    e = _build(rules,
               {"bz": ["dm24ex3-or1"],
                "shield": ["T960", "T001"] + ["T002"] * 8,
                "deck": ["T002"] * 6},
               {"shield": ["T001"] * 5, "deck": ["T002"] * 8})
    t960 = next(c for c in e.zlist("shield", 0)
                if e.cdef(c).id == "T960")
    t001 = next(c for c in e.zlist("shield", 0)
                if e.cdef(c).id == "T001")
    seen = []
    attacked = False
    for _ in range(800):
        if t960 in e.zlist("hand", 0) and _quiet(e):
            break
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        seen.append(kind)
        keys = [o["key"] for o in d["options"]]
        if kind == "declare_strigger":
            e.answer([])          # 宣言しない（機会の有無だけを見る）
        elif kind == "attack":
            hit = [i for i, k in enumerate(keys)
                   if k == "attack:dm24ex3-or1:player"]
            if hit and not attacked:
                attacked = True
                e.answer([hit[0]])
            else:
                _fallback(e, d, keys)
        elif kind == "yes_no":
            e.answer([keys.index("yes")])   # シールド化する
        elif kind == "choose_cards":
            hit = [i for i, o in enumerate(d["options"])
                   if o["cid"] in (t960, t001)]
            if hit:
                e.answer(hit)
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            e.answer([keys.index("no_block")] if "no_block" in keys
                     else list(range(d.get("min", 0))))
        else:
            _fallback(e, d, keys)
    assert "T960" in _defns(e, "hand", 0)
    assert t001 in e.bz_tops(0)                     # 選んだ獣は場へ
    assert "declare_strigger" not in seen
    assert e.s.cards[t960].strigger_off is True     # 印が付いている
