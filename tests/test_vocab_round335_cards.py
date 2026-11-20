"""再変換ラウンド335（第300弾 skip_turn_remainder）の記録テスト。

- 新規登録2件: dm26ex4-031 切札混成 ゴッド・タイム（canon）/
  dmr21-021 時の宮殿 ベルファーレ。
- alias 畳み込み1件: dm26ex4-sec012（ゴッド・タイムの別印刷）は
  validate の aliases_for で dm26ex4-031 の alias に畳み込まれた
  （独立エントリではなく、reject 行も残らない）。
- 差し戻し・stale 解消は0件。
- converted 10,227→10,229 / rejects 2,096→2,093、重なり0・漏れ0。
  skip_turn_remainder は rejects に残らない。

登録形の要点（第300弾で実挙動固定した形どおり）:
- ゴッド・タイム = キーワード3件（ex_life / speed_attacker /
  triple_breaker）＋ CIP（dm23bd1-005 の destroy マクロ形、
  power_le 5000）＋ 形A（{event: move, from: shield,
  subject: {exlife_of: self}} ＋ may end_turn）。submit の連結・
  merge_split 由来の混入が無いことを abilities の完全一致で固定。
- ベルファーレ = partial の革命チェンジ declare ＋ 形B（破壊された時
  end_turn、条件なし）＋ 形C（自分のシールドがブレイクされた時、
  if {exists: {ref: self, filter: {tapped: true}}} で end_turn）。
  「タップしていれば」は第2節にのみ付く解釈（公式FAQに個別裁定なし、
  第300弾の文法判断を採用。docs 参照）。本文1行目「マナゾーンに
  置く時、このカードはタップして置く」は dm10-037 の先例どおり
  追加フィールドなし。

実挙動は登録カード自身で固定する（形A=破壊置換経路、形B=破壊、
形C=タップ中ブレイク／アンタップ判別）。ドライバは第300弾の
プロトテストと同形（scenario.build の薄い包み。tests.conftest は
import しない）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine.scenario import build  # noqa: E402


def setup(rules, p0, p1=None, filler="T002", seed=1, deck_size=20):
    """round334 と同じ build の薄い包み（tests.conftest は import しない）。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": seed, "deck_size": deck_size})


TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

GOD = "dm26ex4-031"
GOD_ALIAS = "dm26ex4-sec012"
BEL = "dmr21-021"

FORM_A = {"kind": "trigger",
          "when": {"event": "move", "from": "shield",
                   "subject": {"exlife_of": "self"}},
          "effect": [{"op": "may", "body": [{"op": "end_turn"}]}]}
FORM_B = {"kind": "trigger",
          "when": {"event": "move", "from": "bz", "to": "graveyard",
                   "reason": "destroy", "subject": "self"},
          "effect": [{"op": "end_turn"}]}
FORM_C = {"kind": "trigger",
          "when": {"event": "break", "player": "you"},
          "if": {"exists": {"ref": "self", "filter": {"tapped": True}}},
          "effect": [{"op": "end_turn"}]}
CIP_GOD_TIME = {"kind": "trigger",
                "when": {"event": "move", "to": "bz", "subject": "self"},
                "effect": [{"op": "destroy",
                            "select": {"zone": "bz", "owner": "opp",
                                       "filter": {"types": ["creature"],
                                                  "power_le": 5000},
                                       "count": "all"}}]}
DECLARE_BEL = {"kind": "declare", "zone": "hand",
               "when": {"event": "attack",
                        "subject": {"owner": "you",
                                    "filter": {"civs": ["light", "water"],
                                               "race_has": "ドラゴン"}}},
               "effect": [{"op": "swap",
                           "out": {"ref": "event.subject"},
                           "in": {"ref": "self"}}]}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round335_disposition():
    rej = _reject_rows()
    assert len(rej) == 2093
    god = _conv(GOD)
    assert god is not None
    assert god["keywords"] == ["ex_life", "speed_attacker", "triple_breaker"]
    assert god["abilities"] == [CIP_GOD_TIME, FORM_A]   # 混入・重複なし
    assert (god.get("source") or {}).get("aliases") == [GOD_ALIAS]
    assert not (god.get("source") or {}).get("unsupported")
    parse_card(god, TABLES)
    bel = _conv(BEL)
    assert bel is not None
    assert bel["keywords"] == ["double_breaker"]
    assert bel["abilities"] == [DECLARE_BEL, FORM_B, FORM_C]
    assert not (bel.get("source") or {}).get("unsupported")
    parse_card(bel, TABLES)
    # alias 畳み込み: 独立エントリではなく、reject 行も残らない
    assert _conv(GOD_ALIAS) is None
    for cid in (GOD, GOD_ALIAS, BEL):
        assert cid not in rej, cid
    # skip_turn_remainder は解消、converted と rejects の重なり0
    assert not [r for r in rej.values()
                if "skip_turn_remainder" in (r.get("gaps") or [])]
    ids = {x["id"] for x in _conv_cache.all_cards(CONVERTED)}
    assert len(ids) == 10229
    assert not (ids & set(rej))


# ---------- 実挙動ドライバ（第300弾のものと同形） ----------

def _exlife_shield(e, p):
    return next((c for c in e.zlist("shield", p)
                 if e.s.cards[c].exlife_of is not None), None)


def _bz(e, p, defn):
    return [c for c in e.zlist("bz", p) if e.s.cards[c].defn == defn
            and e.s.cards[c].controller == p]


def _drive(e, hook, limit=900):
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        ans = hook(e, d, keys)
        if ans == "stop":
            return
        if ans is not None:
            e.answer(ans)
            continue
        kind = d["kind"]
        if kind == "pay_mana":
            e.answer([0])
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("drive did not finish")


def _chain(*hooks):
    def hook(e, d, keys):
        for h in hooks:
            ans = h(e, d, keys)
            if ans is not None:
                return ans
        return None
    return hook


def _play_hook(tid, st):
    def hook(e, d, keys):
        if d["kind"] == "main" and not st.get("played") \
                and f"play:{tid}" in keys:
            st["played"] = True
            return [keys.index(f"play:{tid}")]
        return None
    return hook


def _p1_attack_hook(st):
    def hook(e, d, keys):
        if d["kind"] == "attack" and d.get("player") == 1 \
                and "attack:T001:player" in keys:
            st["p1_attacks"] = st.get("p1_attacks", 0) + 1
            return [keys.index("attack:T001:player")]
        return None
    return hook


def _recorder(st):
    def hook(e, d, keys):
        if st.get("event"):
            st.setdefault("after", []).append((d["kind"], d.get("player")))
        return None
    return hook


def _charge_watch(st, turn):
    def hook(e, d, keys):
        if d["kind"] == "charge" and d.get("player") == 0 \
                and st.get("event") and e.s.turn == turn:
            st["p0_charge_turn"] = e.s.turn
            return "stop"
        return None
    return hook


def _no_p1_main_or_attack_after(st):
    return not [x for x in st.get("after", [])
                if x[1] == 1 and x[0] in ("main", "attack")]


# ---------- 形A（登録形）: 破壊置換経路で EXライフシールド離脱 ----------

def test_registered_god_time_form_a_destroy_route(rules):
    """dm26ex4-031（登録形）: 相手の破壊呪文 → EXライフ置換で
    シールドが墓地に離れる → 「とばしてもよい」に yes → 唱えた
    相手のターンは終わる。本体は置換で場に残る。"""
    e = setup(rules, {"hand": [GOD], "mana": ["T010"] * 4 + ["T034"] * 3},
              {"hand": ["T056"], "mana": ["T008"] * 3, "bz": ["T001"]},
              filler="T002")
    st = {}

    def cast_hook(e, d, keys):
        if d["kind"] == "main" and d.get("player") == 1 \
                and not st.get("cast") and "play:T056" in keys:
            st["cast"] = True
            st["event"] = True
            return [keys.index("play:T056")]
        return None

    def may_hook(e, d, keys):
        if d["kind"] == "yes_no" and st.get("cast") \
                and not st.get("may_done"):
            st["may_done"] = True
            st["may_asked"] = True
            return [keys.index("yes")]
        return None

    _drive(e, _chain(_recorder(st), _charge_watch(st, 3),
                     _play_hook(GOD, st), cast_hook, may_hook,
                     _p1_attack_hook(st)))
    assert st.get("played") and st.get("may_asked")
    assert _bz(e, 0, GOD)                          # 置換で残った
    assert _exlife_shield(e, 0) is None            # 盾は盾ゾーンに無い
    assert len(e.zlist("graveyard", 0)) == 1       # かわりにシールドが墓地へ
    assert st["p0_charge_turn"] == 3
    assert st.get("p1_attacks", 0) == 0
    assert _no_p1_main_or_attack_after(st)


# ---------- 形B（登録形）: 破壊された時 → 必須でとばす ----------

def test_registered_belphaire_form_b_destroyed_skips(rules):
    """dmr21-021（登録形）: 相手ターンに破壊される → そのターンの
    残りがとび、相手は攻撃できない（条件なし=アンタップでも発火）。"""
    e = setup(rules, {"bz": [BEL, "T001"]},
              {"hand": ["T056"], "mana": ["T008"] * 3, "bz": ["T001"]},
              filler="T002")
    st = {}

    def cast_hook(e, d, keys):
        if d["kind"] == "main" and d.get("player") == 1 \
                and not st.get("cast") and "play:T056" in keys:
            st["cast"] = True
            st["event"] = True
            return [keys.index("play:T056")]
        if st.get("cast") and not st.get("targeted"):
            hit = [i for i, k in enumerate(keys) if BEL in k]
            if hit:
                st["targeted"] = True
                return [hit[0]]
        return None

    _drive(e, _chain(_recorder(st), _charge_watch(st, 3), cast_hook,
                     _p1_attack_hook(st)))
    assert not _bz(e, 0, BEL)
    assert [c for c in e.zlist("graveyard", 0)
            if e.s.cards[c].defn == BEL]
    assert st.get("p1_attacks", 0) == 0
    assert st["p0_charge_turn"] == 3
    assert _no_p1_main_or_attack_after(st)


# ---------- 形C（登録形）: タップ中ブレイクでとぶ／アンタップではとばない ----------

def test_registered_belphaire_form_c_tapped_break_skips(rules):
    """dmr21-021（登録形）: 自分が攻撃してタップした状態で相手ターンに
    自分のシールドがブレイクされる → ターンの残りがとび、相手の
    2体目は攻撃できない。"""
    e = setup(rules, {"bz": [BEL]}, {"bz": ["T001", "T001"]}, filler="T002")
    st = {}

    def p0_attack_hook(e, d, keys):
        if d["kind"] == "attack" and d.get("player") == 0 \
                and e.s.turn == 3 and not st.get("p0_attacked"):
            st["p0_attacked"] = True
            if f"attack:{BEL}:player" in keys:
                return [keys.index(f"attack:{BEL}:player")]
            return [keys.index("pass")]
        return None

    def p1_hook(e, d, keys):
        if d["kind"] == "attack" and d.get("player") == 1:
            if not st.get("p0_attacked"):
                return [keys.index("pass")]
            st["event"] = True
            st["p1_attacks"] = st.get("p1_attacks", 0) + 1
            if "attack:T001:player" in keys:
                return [keys.index("attack:T001:player")]
            return [keys.index("pass")]
        return None

    _drive(e, _chain(_recorder(st), _charge_watch(st, 5),
                     p0_attack_hook, p1_hook))
    assert st.get("p0_attacked")
    assert st["p1_attacks"] == 1
    assert st["p0_charge_turn"] == 5
    assert _no_p1_main_or_attack_after(st)


def test_registered_belphaire_form_c_untapped_does_not_skip(rules):
    """dmr21-021（登録形）: タップしていなければ、自分のシールドが
    ブレイクされても発火せず、相手の2体目も攻撃する（判別）。"""
    e = setup(rules, {"bz": [BEL]}, {"bz": ["T001", "T001"]}, filler="T002")
    st = {}

    def hook(e, d, keys):
        if d["kind"] == "charge" and d.get("player") == 0 \
                and e.s.turn == 3:
            st["p0_charge_turn"] = 3
            return "stop"
        if d["kind"] == "attack" and d.get("player") == 1 \
                and "attack:T001:player" in keys:
            st["event"] = True
            st["p1_attacks"] = st.get("p1_attacks", 0) + 1
            return [keys.index("attack:T001:player")]
        return None

    _drive(e, hook)
    assert st["p1_attacks"] == 2
    assert st["p0_charge_turn"] == 3
