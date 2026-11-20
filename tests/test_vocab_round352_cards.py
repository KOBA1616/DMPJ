"""再変換ラウンド352（第317弾 all_civilizations_condition）の記録テスト。

- 新規登録3件: dm26sd1-b013 フェアリー・ミラクル（形A）/
  dm27-050 ゴレン・キャノン（形B）/ dm26sd1-b005 魔誕と
  光喜と楽識と炎怒と哀樹の決断（形C）。
- alias 畳み込み: 登録エントリへの記録のみで、alias 側の
  reject 行は元々無し（b013 の17件・b005 の4件は
  aliases_for の記録。dm27-050 は alias 無し）。正本判定は
  identity の canon_id 実測で3件とも自 ID。
- stale クリーンアップ0件・差し戻し0件。
- 対象3行は gaps = [all_civilizations_condition] のため
  reopen で外してから submit（reopen の出力は対象3件
  ちょうどだった）。
- converted 10,255→10,258 / rejects 2,062→2,059、
  canonical 重なり0・漏れ0。all_civilizations_condition は
  ファミリーがこの3件だけだったため完全に解消。

登録形は第317弾の確立形と完全一致（submit の連結・
merge_split 由来の混入なし）:
- 形A/B の spell は2ステップ（本体＋ if）、形C は if 1件
  ちょうど。形C の条件は「自分のエレメント」で、総合
  ルール403.1により zone: bz で数える（第317弾で確定）。

実挙動は登録カード自身で固定する（第317弾本体の観点を
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

GAP = "all_civilizations_condition"
CIVS5 = ["light", "water", "darkness", "fire", "nature"]

ALIASES = {
    "dm26sd1-b013": ["dm24bd4-015", "dm27-053", "dm27-053cc",
                     "dmart03-003", "dmbd01-015", "dmex06-095",
                     "dmex08-099", "dmrp18-a13", "dmrp18-b13",
                     "dmx01-039", "dmx14-080", "dmx16-070",
                     "dmx22b-078", "dmx26-026", "promoy17-056",
                     "promoy23-070", "promoy23-073"],
    "dm27-050": [],
    "dm26sd1-b005": ["dm24ex3-rp4011", "dm24ex3-rp4sec15",
                     "dm24rp4-011", "dm24rp4-sec15"],
}


def _all_civs(zone):
    return {"all": [{"cmp": [{"count": {"zone": zone, "owner": "you",
                                         "filter": {"civs": [c]}}},
                             ">=", 1]}
                    for c in CIVS5]}


MANA_PUT_TOP = {"op": "mana_put",
                "select": {"zone": "deck", "owner": "you", "from_top": 1}}
DESTROY_3000 = {"op": "destroy",
                "select": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"],
                                      "power_le": 3000},
                           "count": 1}}
SPELL_A = [MANA_PUT_TOP,
           {"op": "if", "cond": _all_civs("mana"), "then": [MANA_PUT_TOP]}]
SPELL_B = [DESTROY_3000,
           {"op": "if", "cond": _all_civs("mana"), "then": [DESTROY_3000]}]

MODES = [
    [{"op": "move",
      "select": {"zone": "deck", "owner": "you", "from_top": 1},
      "to": "shield", "reason": "charge"}],
    [{"op": "draw", "count": 2}],
    [{"op": "discard",
      "select": {"zone": "hand", "owner": "opp", "count": 1,
                 "chooser": "random"}}],
    [{"op": "destroy",
      "select": {"zone": "bz", "owner": "opp",
                 "filter": {"cost_le": 6}, "count": 1}}],
    [MANA_PUT_TOP,
     {"op": "may",
      "body": [{"op": "move",
                "select": {"zone": "mana", "owner": "you", "count": 1},
                "to": "hand", "reason": "return"}]}],
]
_MODAL_ALL = {"op": "modal", "count": 5, "modes": MODES}
_MODAL_TWO = {"op": "modal", "count": 2, "repeat": True, "modes": MODES}
SPELL_C = [{"op": "if", "cond": _all_civs("bz"),
            "then": [{"op": "may", "body": [_MODAL_ALL],
                      "else": [_MODAL_TWO]}],
            "else": [_MODAL_TWO]}]

TEXT_A = ("自分の山札の上から１枚をマナゾーンに置く。"
          "自分のマナゾーンにすべての文明が揃っていれば、"
          "自分の山札の上からもう１枚、マナゾーンに置く。")
TEXT_B = ("相手のパワー3000以下のクリーチャーを１体破壊する。\n"
          "自分のマナゾーンにすべての文明が揃っていれば、"
          "相手のパワー3000以下のクリーチャーをもう１体、破壊する。")
TEXT_C = ("次の中から２回選ぶ。同じものを選んでもよい。"
          "自分のエレメントにすべての文明が揃っていれば、"
          "かわりにすべてを１回ずつ使ってもよい。\n"
          "▶自分の山札の上から１枚をシールド化する。\n"
          "▶カードを２枚引く。\n"
          "▶相手の手札を１枚見ないで選び、捨てさせる。\n"
          "▶相手のコスト６以下のエレメントを１つ選び、破壊する。\n"
          "▶自分の山札の上から１枚をマナゾーンに置く。"
          "その後、カードを１枚、自分のマナゾーンから手札に戻してもよい。")

FORMS = {
    "dm26sd1-b013": {"name": "フェアリー・ミラクル",
                     "civs": ["nature"], "cost": 3,
                     "text": TEXT_A, "spell": SPELL_A, "proto": "T972"},
    "dm27-050": {"name": "ゴレン・キャノン",
                 "civs": ["fire"], "cost": 5,
                 "text": TEXT_B, "spell": SPELL_B, "proto": "T973"},
    "dm26sd1-b005": {"name": "魔誕と光喜と楽識と炎怒と哀樹の決断",
                     "civs": CIVS5, "cost": 5,
                     "text": TEXT_C, "spell": SPELL_C, "proto": "T974"},
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


def test_round352_disposition():
    rej = _reject_rows()
    assert len(rej) == 2059
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10258
    assert not (ids & set(rej))          # canonical 重なり0
    for tid, spec in FORMS.items():
        # 漏れ0: 正本は登録され reject 行に残っていない。
        # alias は独立エントリにも reject 行にも無い
        assert tid in ids and tid not in rej, tid
        for a in ALIASES[tid]:
            assert a not in ids and a not in rej, a
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None
        assert not (c.get("source") or {}).get("unsupported")
        assert (c.get("source") or {}).get("aliases") \
            == (ALIASES[tid] or None), tid
        # 登録形の完全一致（連結・merge_split 由来の混入なし）
        for k in ("name", "civs", "cost", "text", "spell"):
            assert c.get(k) == spec[k], (tid, k)
        assert c["types"] == ["spell"] and c["mana"] == 1, tid
        assert not c.get("keywords"), tid
        # 形A/B は2ステップ、形C は if 1件ちょうど
        assert len(c["spell"]) == (1 if tid == "dm26sd1-b005" else 2), tid
        d = parse_card(c, TABLES)
        assert d.spell == parse_card(proto_card(spec["proto"]),
                                     TABLES).spell, tid
    # all_civilizations_condition は完全に解消（ファミリーはこの3件だけ）
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


# ---------- 実挙動ドライバ（scenario.build 直包み、第351弾と同型） ----------

def _build(rules, p0, p1):
    return scenario.build(
        rules, {"p0": p0, "p1": p1, "filler": "T007", "seed": 1,
                "deck_size": 20, "deck_exact": [True, True]})


def _by_defn(e, zone, defn, player=0):
    return [c for c in e.zlist(zone, player)
            if e.s.cards[c].defn == defn
            and (zone != "bz" or e.s.cards[c].controller == player)]


def _count(e, zone, player=0):
    return len(e.zlist(zone, player))


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


def _cast_hook(card, extra=None):
    def hook(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d["player"] == 0 \
                and f"play:{card}" in keys:
            return [keys.index(f"play:{card}")]
        if d["kind"] == "pay_mana":
            return [0]
        if extra:
            return extra(e, d, keys)
        return None
    return hook


# ---------- 形A（登録形） ----------

def test_registered_form_a_second_put_when_completed_by_first(rules):
    # マナは火だけ欠け、山札の上（spec の末尾）が火。
    # 1枚目を置いた時点で揃うため、もう1枚置く
    e = _build(rules,
               {"hand": ["dm26sd1-b013"],
                "mana": ["T004", "T010", "T008", "T001"],
                "deck": ["T002", "T034"]},
               {"deck": ["T002"] * 8})
    _run(e, _cast_hook("dm26sd1-b013"),
         done=lambda: len(_by_defn(e, "graveyard", "dm26sd1-b013", 0)) == 1)
    mana = [e.s.cards[c].defn for c in e.zlist("mana", 0)]
    assert len(mana) == 6, mana
    assert "T034" in mana and "T002" in mana


def test_registered_form_a_no_second_put_when_still_missing(rules):
    # 山札の上が既にある自然では火が揃わず、2枚目は置かない
    e = _build(rules,
               {"hand": ["dm26sd1-b013"],
                "mana": ["T004", "T010", "T008", "T001"],
                "deck": ["T002", "T001"]},
               {"deck": ["T002"] * 8})
    _run(e, _cast_hook("dm26sd1-b013"),
         done=lambda: len(_by_defn(e, "graveyard", "dm26sd1-b013", 0)) == 1)
    mana = [e.s.cards[c].defn for c in e.zlist("mana", 0)]
    assert len(mana) == 5, mana
    assert "T034" not in mana


# ---------- 形B（登録形） ----------

def test_registered_form_b_destroys_twice_when_all_civs(rules):
    e = _build(rules,
               {"hand": ["dm27-050"],
                "mana": ["T004", "T010", "T008", "T034", "T001"],
                "deck": ["T002"] * 8},
               {"bz": ["T001", "T004", "T010"], "deck": ["T002"] * 8})
    _run(e, _cast_hook("dm27-050"),
         done=lambda: len(_by_defn(e, "graveyard", "dm27-050", 0)) == 1)
    assert len(_by_defn(e, "graveyard", "T001", 1)) == 1
    assert len(_by_defn(e, "graveyard", "T004", 1)) == 1
    assert len(_by_defn(e, "bz", "T010", 1)) == 1   # パワー4000は対象外


def test_registered_form_b_destroys_once_without_all_civs(rules):
    e = _build(rules,
               {"hand": ["dm27-050"], "mana": ["T034"] * 5,
                "deck": ["T002"] * 8},
               {"bz": ["T001", "T004"], "deck": ["T002"] * 8})
    _run(e, _cast_hook("dm27-050"),
         done=lambda: len(_by_defn(e, "graveyard", "dm27-050", 0)) == 1)
    dead = len(_by_defn(e, "graveyard", "T001", 1)) \
        + len(_by_defn(e, "graveyard", "T004", 1))
    alive = len(_by_defn(e, "bz", "T001", 1)) \
        + len(_by_defn(e, "bz", "T004", 1))
    assert dead == 1 and alive == 1


# ---------- 形C（登録形） ----------

def test_registered_form_c_all_modes_once_when_bz_all_civs(rules):
    # 場のエレメントに全文明が揃い、全モード使用を選ぶと
    # 5モードが書かれた順に1回ずつ解決する
    st = {}

    def extra(e, d, keys):
        if d["kind"] == "yes_no":
            st["yes_no"] = st.get("yes_no", 0) + 1
            return [0]                       # すべて使う／回収する
        if d["kind"] == "choose_mode":
            return list(range(len(keys)))    # 全選択（自動決定の保険）
        return None

    e = _build(rules,
               {"hand": ["dm26sd1-b005"],
                "mana": ["T004", "T010", "T008", "T034", "T001"],
                "bz": ["T030", "T008", "T034", "T001"],
                "deck": ["T002"] * 8},
               {"hand": ["T001", "T001"], "bz": ["T001"],
                "deck": ["T002"] * 8})
    _run(e, _cast_hook("dm26sd1-b005", extra),
         done=lambda: len(_by_defn(e, "graveyard", "dm26sd1-b005", 0)) == 1
         and _count(e, "hand", 0) == 3)
    assert st.get("yes_no") == 2             # 全使用の may＋回収の may
    assert _count(e, "shield", 0) == 6       # モード1: シールド化
    assert _count(e, "hand", 0) == 3         # モード2: 2ドロー＋モード5: 回収1
    assert _count(e, "hand", 1) == 1         # モード3: 見ないで1枚捨て
    assert len(_by_defn(e, "graveyard", "T001", 1)) == 2  # 捨て札＋モード4の破壊
    assert _count(e, "mana", 0) == 5         # 5＋1（モード5）−1（回収）


def test_registered_form_c_mana_all_civs_is_not_enough(rules):
    # 判別テスト: マナに全文明が揃っていても、場の
    # エレメントが揃っていなければ置換は提示されない
    # （条件はバトルゾーン参照。403.1）
    st = {"modes": [], "yes_no": 0}

    def extra(e, d, keys):
        if d["kind"] == "yes_no":
            st["yes_no"] += 1
            return [0]
        if d["kind"] == "choose_mode":
            st["modes"].append(1)
            return [keys.index("mode:1")]   # ドローを2回選ぶ
        return None

    e = _build(rules,
               {"hand": ["dm26sd1-b005"],
                "mana": ["T004", "T010", "T008", "T034", "T001"],
                "deck": ["T002"] * 8},
               {"hand": ["T001"], "deck": ["T002"] * 8})
    _run(e, _cast_hook("dm26sd1-b005", extra),
         done=lambda: len(_by_defn(e, "graveyard", "dm26sd1-b005", 0)) == 1
         and _count(e, "hand", 0) == 4)
    assert st["yes_no"] == 0                 # 置換の may は出ない
    assert st["modes"] == [1, 1]             # 通常の2回選択（同選択可）
    assert _count(e, "hand", 0) == 4
    assert _count(e, "shield", 0) == 5


def test_registered_form_c_decline_falls_back_to_two_picks(rules):
    # 場が揃っていても全使用を断れば通常の2回選択になる
    st = {"yes_no": 0, "modes": []}

    def extra(e, d, keys):
        if d["kind"] == "yes_no":
            st["yes_no"] += 1
            return [1]                       # 断る
        if d["kind"] == "choose_mode":
            st["modes"].append(1)
            return [keys.index("mode:1")]
        return None

    e = _build(rules,
               {"hand": ["dm26sd1-b005"],
                "mana": ["T004", "T010", "T008", "T034", "T001"],
                "bz": ["T030", "T008", "T034", "T001"],
                "deck": ["T002"] * 8},
               {"hand": ["T001"], "deck": ["T002"] * 8})
    _run(e, _cast_hook("dm26sd1-b005", extra),
         done=lambda: len(_by_defn(e, "graveyard", "dm26sd1-b005", 0)) == 1
         and _count(e, "hand", 0) == 4)
    assert st["yes_no"] == 1                 # 置換の may は提示された
    assert st["modes"] == [1, 1]
    assert _count(e, "hand", 0) == 4
    assert _count(e, "shield", 0) == 5       # シールド化はしていない
