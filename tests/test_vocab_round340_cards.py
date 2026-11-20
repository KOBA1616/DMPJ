"""再変換ラウンド340（第305弾 soul_shift）の記録テスト。

- 新規登録2件: dm26rp2-001（極まる九極 Q.9）/ dmex18-005
  （ケンゲキオージャ ～究極火焔～）。どちらもギャップ名
  soul_shift のドリフトで、機構は第218弾の面フィールド
  soul_shift {floor: 0}＋第274弾のクラシック単体進化への適用
  （第274弾の対象は表記の違う soulshift）で既存語彙。
- alias 畳み込み1件: dm35-004 / dmc64-013 → dmex18-005
  （登録カードの source.aliases に記録。どちらも reject 行は
  元々無かった）。stale 解消・converted 是正は0件。
- 正本判定は identity の実データ照合による: 対象2件はいずれも
  canon_id が自身＝独立正本。canon_id(dm35-004) =
  canon_id(dmc64-013) = dmex18-005 で、aliases_for（ケンゲキ
  オージャ）とも一致する。
- 差し戻し0件。converted 10,241→10,243 / rejects
  2,080→2,078、重なり0・漏れ0。soul_shift の純粋行は解消
  （ギャップ名自体は evolve_from_deck_onto_self 併記の
  dmc64-024 / dmc64-025 に残る）。

登録形は第305弾の確立形と完全一致（submit の連結・
merge_split 由来の混入なし）:
- dm26rp2-001: partial は骨格（types に evolution 無し・
  abilities 無し）のため、公式全文から types [creature,
  evolution] ＋ evolve_from {civs: [light], types: [creature]}
  ＋ soul_shift {floor: 0} ＋ 離脱誘発（第294弾
  event.was_under ゲート＋dmex18-s11 先例の look 形、
  order: shuffle）を構築。text は reject 行の正式本文。
- dmex18-005: partial ＋ soul_shift {floor: 0} ＋ 勝利誘発
  （第290弾 cause {by: opp, kind: [spell, ability]} ＋
  {op: win}）。text は reject 行の正式本文。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の
作法）。コスト0まで軽減された有色カードの支払い枚数は
112.2b を巡る第274弾 vs 第292弾の未解決競合に触れないため
断言しない（実効0のケースは場に出ることと束だけを見る）。
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

Q9 = "dm26rp2-001"
KEN = "dmex18-005"
TARGETS = (Q9, KEN)

LEAVE_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "subject": "self"},
    "if": {"exists": {"ref": "event.was_under",
                      "filter": {"types": ["creature"],
                                 "cost_le": 9, "cost_ge": 9}}},
    "effect": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "from_top": 9,
                    "look": True, "count": "all"},
         "reveal": True, "as": "pile"},
        {"op": "may", "body": [
            {"op": "play_free",
             "select": {"ref": "pile",
                        "filter": {"types": ["creature"], "civs": ["light"],
                                   "cost_le": 9, "cost_ge": 9},
                        "count": 1}}]},
        {"op": "move",
         "select": {"ref": "pile", "count": "all"},
         "to": "deck", "position": "bottom", "order": "shuffle",
         "reason": "put"},
    ],
}

WIN_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "subject": "self",
             "cause": {"by": "opp", "kind": ["spell", "ability"]}},
    "effect": [{"op": "win"}],
}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round340_disposition():
    rej = _reject_rows()
    assert len(rej) == 2078
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10243
    assert not (ids & set(rej))          # canonical 重なり0
    for tid in TARGETS:
        c = _conv(tid)
        assert c is not None, tid
        assert not (c.get("source") or {}).get("unsupported"), tid
        assert tid not in rej, tid       # 漏れ0
        parse_card(c, TABLES)
    q9 = _conv(Q9)
    assert q9["types"] == ["creature", "evolution"]
    assert q9["evolve_from"] == {"civs": ["light"], "types": ["creature"]}
    assert q9["soul_shift"] == {"floor": 0}
    # 登録形の完全一致（連結・merge_split 由来の混入なし。
    # partial に abilities が無かったので特にここを見る）
    assert q9["abilities"] == [LEAVE_TRIGGER]
    d = parse_card(q9, TABLES)
    assert sorted(d.keywords) == ["blocker", "g_strike", "triple_breaker"]
    assert q9["text"].startswith("{GS} G・ストライク")
    assert (q9.get("source") or {}).get("aliases") is None
    ken = _conv(KEN)
    assert ken["types"] == ["creature", "evolution"]
    assert ken["evolve_from"] == {"name_has": "ゴウケンオー"}
    assert ken["soul_shift"] == {"floor": 0}
    assert ken["abilities"] == [WIN_TRIGGER]
    d = parse_card(ken, TABLES)
    assert d.keywords == ["quad_breaker"]
    assert ken["text"].startswith("進化：名前に《ゴウケンオー》")
    # alias は source.aliases に記録（独立エントリ・reject 行なし）
    assert (ken.get("source") or {}).get("aliases") == \
        ["dm35-004", "dmc64-013"]
    for a in ("dm35-004", "dmc64-013"):
        assert _conv(a) is None, a
        assert a not in rej, a
    # soul_shift の純粋行は解消。併記2行だけが残る
    holders = {rid for rid, r in rej.items()
               if "soul_shift" in (r.get("gaps") or [])}
    assert holders == {"dmc64-024", "dmc64-025"}, holders
    for tid in ("dmc64-024", "dmc64-025"):
        assert rej[tid].get("gaps") == \
            ["soul_shift", "evolve_from_deck_onto_self"], tid


# ---------- 実挙動ドライバ（第305弾本体と同型、build 直包み） ----------

def _build(rules, p0, p1=None, deck_size=20):
    # filler は deck spec と重ならない defn にする（deck_exact は
    # filler と同じ defn の spec カードを取り除くため）
    return scenario.build(
        rules, {"p0": p0, "p1": p1 or {}, "filler": "T001", "seed": 1,
                "deck_size": deck_size, "deck_exact": [True, True]})


def _by_defn(e, zone, defn, player=0):
    return [c for c in e.zlist(zone, player)
            if e.s.cards[c].defn == defn
            and (zone != "bz" or e.s.cards[c].controller == player)]


def _tapped_mana(e, player=0):
    return [c for c in e.zlist("mana", player) if e.s.cards[c].tapped]


def _deck_defns(e, player):
    return [e.s.cards[c].defn for c in e.s.zones["deck"][player]]


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


def _play_handler(play_keys, evo_base=None, choose_cid=None, choose_defn=None):
    st = {"played": set()}

    def handler(e, d):
        p = d["player"]
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and p in play_keys and p not in st["played"]:
            if play_keys[p] in keys:
                st["played"].add(p)
                return [keys.index(play_keys[p])]
        if d["kind"] == "choose_evo_source" and evo_base is not None:
            for i, o in enumerate(d["options"]):
                if o.get("cid") == evo_base:
                    return [i]
        if d["kind"] == "pay_mana":
            return [0]
        if d["kind"] == "yes_no":
            return [0]
        if d["kind"] == "choose_cards":
            for i, o in enumerate(d["options"]):
                if choose_cid is not None and o.get("cid") == choose_cid:
                    return [i]
                if choose_defn is not None and o.get("defn") == choose_defn:
                    return [i]
        return None

    return handler


# ---------- 実挙動（登録形） ----------

def test_registered_soulshift_partial_reduction(rules):
    """dm26rp2-001: 光・コスト9 − 進化元（光・コスト5）= 4 を支払う。"""
    e = _build(rules, {"hand": [Q9], "bz": ["T934"],
                       "mana": ["T933", "T934", "T001", "T001", "T001"],
                       "deck": ["T002"] * 6},
               {"deck": ["T002"] * 6})
    top = _by_defn(e, "hand", Q9)[0]
    base = _by_defn(e, "bz", "T934")[0]
    _run(e, _play_handler({0: f"play:{Q9}"}, evo_base=base),
         done=lambda: e.s.cards[top].zone == "bz")
    assert e.s.cards[top].zone == "bz"
    assert e.s.cards[top].under == [base]
    assert len(_tapped_mana(e)) == 4


def test_registered_leave_trigger_plays_cost9_from_look(rules):
    """dm26rp2-001: 下にコスト9があれば上9枚を見て光のコスト9を出す。"""
    # build は deck spec を逆順に置く（spec の末尾が山札の一番上）
    e = _build(rules,
               {"hand": [Q9], "bz": ["T933"],
                "mana": ["T933", "T934", "T001", "T001", "T001"],
                "deck": ["T003"] * 14 + ["T933"]},
               {"hand": ["T056"], "mana": ["T008"] * 5,
                "deck": ["T003"] * 10})
    base = _by_defn(e, "bz", "T933")[0]
    top = _by_defn(e, "hand", Q9)[0]
    deck933 = _by_defn(e, "deck", "T933")[0]   # 山札の個体（ベースと別）
    deck_before = _deck_defns(e, 0)
    assert deck_before[0] == "T933" and len(deck_before) == 15
    _run(e, _play_handler({0: f"play:{Q9}", 1: "play:T056"},
                          evo_base=base, choose_cid=top,
                          choose_defn="T933"),
         done=lambda: e.s.cards[deck933].zone == "bz")
    assert e.s.cards[top].zone == "graveyard"
    assert e.s.cards[base].zone == "graveyard"
    assert e.s.cards[deck933].zone == "bz"
    # 残りはシャッフルして下へ（T003 は山札＋ドロー分で計14枚）
    assert all(d == "T003" for d in _deck_defns(e, 0))
    assert (len(_deck_defns(e, 0))
            + len(_by_defn(e, "hand", "T003"))) == 14


def test_registered_win_trigger_opponent_spell(rules):
    """dmex18-005: 相手の呪文で離れる時、自分はゲームに勝つ。"""
    e = _build(rules, {"bz": [KEN], "deck": ["T002"] * 6},
               {"hand": ["T056"], "mana": ["T008"] * 5,
                "deck": ["T002"] * 6})
    tgt = _by_defn(e, "bz", KEN)[0]
    _run(e, _play_handler({1: "play:T056"}, choose_cid=tgt))
    assert e.s.result is not None
    assert e.s.result["winner"] == 0


def test_registered_win_trigger_own_spell_does_not_win(rules):
    """dmex18-005: 自分の呪文で離れた時は cause が合わず勝利しない。"""
    e = _build(rules, {"hand": ["T938"], "bz": [KEN],
                       "mana": ["T008"] * 5, "deck": ["T002"] * 6},
               {"deck": ["T002"] * 6})
    tgt = _by_defn(e, "bz", KEN)[0]
    _run(e, _play_handler({0: "play:T938"}, choose_cid=tgt), limit=200,
         done=lambda: len(_by_defn(e, "graveyard", KEN)) == 1)
    assert len(_by_defn(e, "graveyard", KEN)) == 1
    assert e.s.result is None
