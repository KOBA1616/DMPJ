"""語彙パイロット第289弾のカード適用テスト（登録形）。

ラウンド324で graveyard_shuffle 純粋3件を新規登録:
- dmrp10-s03 緑知銀 グィムショウ: partial は abilities を持たず text も
  節だけに切れていた。text を reject 行の公式全文に戻し、形B（出た時、
  相手の墓地をシャッフルして相手の山札の一番下）＋第2節（自分のターン
  の終わりにタップしていたら1枚引いてもよい）＋形D（どこからでも墓地に
  置かれた時、墓地をシャッフルして自分の山札の一番下）を構築。
- dmx13-015 天頂のゼロ・エッグ: partial は abilities を持たない。
  形C（出た時、墓地をすべて山札に加えてシャッフル）＋形E（ターンの
  はじめ、一番下が進化ではない無色クリーチャーなら自分を破壊しても
  よく、そうしたらそれを召喚する）を構築。
- dmx22a-009 偽りの名 スネーク: partial の出た時誘発（1枚引いて上1枚を
  マナへ）は完全なため、形A（攻撃時、墓地をシャッフルして一番下）を
  足しただけ。alias: dmr04-004。text は split が None のため partial の
  「 / 」区切り形がそのまま登録される（内容は公式全文と一致）。
- converted 10,178 / rejects 2,152、重なり0・漏れ0。graveyard_shuffle
  は残り0件でファミリー解消。

プロトテスト（test_vocab_pilot289.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine.scenario import build  # noqa: E402


def setup(rules, p0, p1=None, filler="T001", seed=1, deck_size=20):
    """conftest の setup と同じ薄い包み。tests.conftest を import すると
    DMSIM_SKIP_CONVERTED が再設定されて converted が読めなくなるため、
    ここでは直接 scenario.build を包む（第286弾 cards と同じ）。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": seed, "deck_size": deck_size})


def setup_exact(rules, p0, p1=None, filler="T002"):
    """山札の中身を spec の deck リストだけにする（deck_exact）。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": 1, "deck_size": 20,
                         "deck_exact": [True, True]})


TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

TARGETS = ["dmrp10-s03", "dmx13-015", "dmx22a-009"]

MOVE_A = {"op": "move",
          "select": {"zone": "graveyard", "owner": "you", "count": "all"},
          "to": "deck", "reason": "put", "position": "bottom",
          "order": "shuffle"}
MOVE_B = {"op": "move",
          "select": {"zone": "graveyard", "owner": "opp", "count": "all"},
          "to": "deck", "reason": "put", "position": "bottom",
          "order": "shuffle"}
FORM_C_OPS = [
    {"op": "move",
     "select": {"zone": "graveyard", "owner": "you", "count": "all"},
     "to": "deck", "reason": "put"},
    {"op": "shuffle"},
]
FORM_E_OPS = [
    {"op": "move",
     "select": {"zone": "deck", "owner": "you", "from_bottom": 1},
     "to": "graveyard", "reason": "put", "as": "bottom"},
    {"op": "if",
     "cond": {"exists": {"ref": "bottom", "zone": "graveyard",
                         "filter": {"types": ["creature"], "colorless": True,
                                    "evolution": False}}},
     "then": [
         {"op": "may",
          "body": [
              {"op": "move", "select": {"ref": "self"},
               "to": "graveyard", "reason": "destroy", "as": "fallen"},
              {"op": "if",
               "cond": {"exists": {"ref": "fallen", "zone": "graveyard"}},
               "then": [{"op": "play_free",
                         "select": {"ref": "bottom"}}]}]}]},
]

TRIG_A = {"kind": "trigger", "when": {"event": "attack", "subject": "self"},
          "effect": [MOVE_A]}
TRIG_B = {"kind": "trigger",
          "when": {"event": "move", "to": "bz", "subject": "self"},
          "effect": [MOVE_B]}
TRIG_TURN_END = {
    "kind": "trigger", "when": {"event": "turn_end", "player": "you"},
    "effect": [{"op": "if",
                "cond": {"exists": {"ref": "self", "zone": "bz",
                                    "filter": {"tapped": True}}},
                "then": [{"op": "may", "body": [{"op": "draw", "count": 1}]}]}]}
TRIG_C = {"kind": "trigger",
          "when": {"event": "move", "to": "bz", "subject": "self"},
          "effect": FORM_C_OPS}
TRIG_D = {"kind": "trigger",
          "when": {"event": "move", "to": "graveyard", "subject": "self"},
          "effect": [MOVE_A]}
TRIG_E = {"kind": "trigger", "when": {"event": "turn_start", "player": "you"},
          "effect": FORM_E_OPS}
ENTRY_009 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "you", "filter": {"types": ["creature"]}}},
    "effect": [{"op": "draw", "count": 1},
               {"op": "mana_put",
                "select": {"zone": "deck", "owner": "you", "from_top": 1}}]}
# parse 後は mana_put マクロが move に展開される
ENTRY_009_PARSED = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "you", "filter": {"types": ["creature"]}}},
    "effect": [{"op": "draw", "count": 1},
               {"op": "move",
                "select": {"zone": "deck", "owner": "you", "from_top": 1},
                "to": "mana", "reason": "put"}]}

TEXT_S03 = ("このクリーチャーがバトルゾーンに出た時、相手は自身の墓地を"
            "シャッフルし、山札の一番下に置く。\n"
            "自分のターンの終わりに、このクリーチャーがタップしていたら、"
            "カードを１枚引いてもよい。\n"
            "このクリーチャーが、どこからでも自分の墓地に置かれた時、墓地を"
            "シャッフルし、自分の山札の一番下に置く。")

TEXT_015 = ("このクリーチャーをバトルゾーンに出した時、自分の墓地のカードを"
            "すべて山札に加えてシャッフルする。\n"
            "自分のターンのはじめに、自分の山札の一番下のカードを墓地に置く。"
            "そのカードが進化ではない無色クリーチャーであれば、このクリーチャー"
            "を破壊してもよい。そうした場合、その無色クリーチャーをコストを"
            "支払わずに召喚する。\n"
            "このクリーチャーは攻撃することができない。")

TEXT_009 = ("マナゾーンに置く時、このカードはタップして置く。 / W・ブレイカー / "
            "このクリーチャーまたは自分の他のクリーチャーがバトルゾーンに出た時、"
            "カードを１枚引き、その後、自分の山札の上から１枚目をマナゾーンに置く。 / "
            "このクリーチャーが攻撃する時、自分の墓地のカードをシャッフルし、"
            "山札の一番下に置く。")


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _triggers(card_dict):
    d = parse_card(card_dict, TABLES)
    return [a for a in d.abilities if a["kind"] == "trigger"]


# ---------- 登録形 ----------

def test_registered_forms():
    rej = _reject_rows()
    for cid in TARGETS:
        assert cid not in rej, cid
        _converted(cid)
    # ファミリー解消: graveyard_shuffle を含む行は rejects に残らない
    assert not [r["id"] for r in rej.values()
                if "graveyard_shuffle" in (r.get("gaps") or [])]

    c = _converted("dmrp10-s03")
    assert c["abilities"] == [TRIG_B, TRIG_TURN_END, TRIG_D]
    assert c["text"] == TEXT_S03
    assert not c.get("keywords")
    assert "unsupported" not in (c.get("source") or {})
    assert (c.get("source") or {}).get("aliases") is None
    assert _triggers(c) == [TRIG_B, TRIG_TURN_END, TRIG_D]

    c = _converted("dmx13-015")
    assert c["abilities"] == [TRIG_C, TRIG_E]
    assert c["text"] == TEXT_015
    assert c["keywords"] == ["cannot_attack"]
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert [a for a in d.abilities if a["kind"] == "trigger"] == [TRIG_C, TRIG_E]
    assert "cannot_attack" in d.keywords

    c = _converted("dmx22a-009")
    assert c["abilities"] == [ENTRY_009, TRIG_A]
    assert c["text"] == TEXT_009
    assert c["keywords"] == ["double_breaker"]
    assert "unsupported" not in (c.get("source") or {})
    assert (c.get("source") or {}).get("aliases") == ["dmr04-004"]
    d = parse_card(c, TABLES)
    assert [a for a in d.abilities if a["kind"] == "trigger"] == [
        ENTRY_009_PARSED, TRIG_A]
    assert "double_breaker" in d.keywords
    # alias の dmr04-004 自体は converted の id にはならない
    cards = _conv_cache.all_cards(CONVERTED)
    assert "dmr04-004" not in {x["id"] for x in cards}


# ---------- 実挙動の共通部品（第289弾プロトと同じ型） ----------

def _zone(e, player, zone):
    lst = list(e.zlist(zone, player))
    if zone == "bz":   # バトルゾーンは共有リストなので controller で絞る
        lst = [c for c in lst if e.s.cards[c].controller == player]
    return lst


def _defns(e, player, zone):
    return [e.cdef(c).id for c in _zone(e, player, zone)]


def _deck_defns(e, player):
    """山札リスト（先頭 = 一番上、末尾 = 一番下）の defn 列。"""
    return [e.cdef(c).id for c in e.s.zones["deck"][player]]


def _drive(e, on_decision, limit=600):
    for _ in range(limit):
        if e.s.result is not None:
            return "result"
        d = e.advance()
        if d is None:
            return "done"
        r = on_decision(e, d)
        if r == "stop":
            return "stopped"
        if r == "ok":
            continue
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge" and "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("driver limit reached")


def _chain(*handlers):
    def on_dec(e, d):
        for h in handlers:
            r = h(e, d)
            if r:
                return r
        return None
    return on_dec


def _play_and_pay(play_key, player=0, on_play=None):
    played = []

    def handler(e, d):
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == player \
                and play_key in keys:
            played.append(True)
            if on_play:
                on_play(e)
            e.answer([keys.index(play_key)])
            return "ok"
        if played and d["kind"] == "pay_mana":
            e.answer([0])
            return "ok"
        return None

    return handler, played


def _yes_no(answer_yes, seen):
    def handler(e, d):
        if d["kind"] == "yes_no":
            seen.append(d)
            keys = [o["key"] for o in d["options"]]
            if "yes" in keys:
                e.answer([keys.index("yes" if answer_yes else "no")])
            else:
                e.answer([0] if answer_yes else [len(keys) - 1])
            return "ok"
        return None
    return handler


def _stop_at_own_attack(played):
    def stopper(e, d):
        # 召喚と CIP はメイン内で解決する。次の自分の攻撃決定で観測する
        # （相手ターンのドローを跨ぐと山札枚数がずれる）
        if played and d["kind"] == "attack" and d.get("player") == 0:
            return "stop"
        return None
    return stopper


# ---------- dmrp10-s03 形B: 出た時、相手の墓地 → 相手の山札の一番下 ----------

def test_s03_form_b_opponent_graveyard(rules):
    e = setup(rules, {"hand": ["dmrp10-s03"], "mana": ["T030", "T001", "T001"],
                      "bz": ["T001"]},
              {"graveyard": ["T001", "T008"], "bz": ["T001"]})
    snap = {}
    handler, played = _play_and_pay(
        "play:dmrp10-s03", 0,
        on_play=lambda e: snap.update(deck1=_deck_defns(e, 1),
                                      deck0=_deck_defns(e, 0)))
    _drive(e, _chain(handler, _stop_at_own_attack(played)))
    assert _defns(e, 1, "graveyard") == []
    deck1 = _deck_defns(e, 1)
    assert len(deck1) == len(snap["deck1"]) + 2
    assert deck1[:-2] == snap["deck1"]               # 相手の既存順序は不変
    assert sorted(deck1[-2:]) == ["T001", "T008"]    # 一番下に集合として
    assert _deck_defns(e, 0) == snap["deck0"]        # 自分の山札は不変
    assert _defns(e, 0, "graveyard") == []


# ---------- dmrp10-s03 第2節: ターン終わりにタップしていたら引く ----------

def _attack_with_s03(e, d, state):
    keys = [o["key"] for o in d["options"]]
    if d["kind"] == "attack" and d.get("player") == 0 \
            and "attack:dmrp10-s03:player" in keys:
        state["attacked"] = True
        e.answer([keys.index("attack:dmrp10-s03:player")])
        return "ok"
    return None


def test_s03_clause2_draw_when_tapped(rules):
    e = setup(rules, {"bz": ["dmrp10-s03"]}, {"bz": ["T001"]})
    state = {}
    seen = []
    hand_at_offer = {}

    def watcher(e, d):
        if d["kind"] == "yes_no" and d.get("player") == 0:
            hand_at_offer["n"] = len(_zone(e, 0, "hand"))
        return None

    def stopper(e, d):
        if seen and d["kind"] == "charge" and d.get("player") == 1:
            return "stop"
        return None

    _drive(e, _chain(lambda e, d: _attack_with_s03(e, d, state),
                     watcher, _yes_no(True, seen), stopper))
    assert state.get("attacked") and seen
    assert len(_zone(e, 0, "hand")) == hand_at_offer["n"] + 1


def test_s03_clause2_no_offer_when_untapped(rules):
    e = setup(rules, {"bz": ["dmrp10-s03"]}, {"bz": ["T001"]})
    seen = []

    def stopper(e, d):
        if d["kind"] == "charge" and d.get("player") == 1:
            return "stop"
        return None

    _drive(e, _chain(_yes_no(True, seen), stopper))
    assert seen == []   # 攻撃せずアンタップのままなら諮問自体が起きない


# ---------- dmrp10-s03 形D: 墓地に置かれた時、自分を含む全部が戻る ----------

def test_s03_form_d_destroy_returns_whole_graveyard(rules):
    e = setup(rules, {"bz": ["dmrp10-s03"], "graveyard": ["T001", "T003"]},
              {"hand": ["T056"], "mana": ["T082"] * 3, "bz": ["T001"]})
    snap = {"deck": _deck_defns(e, 0)}
    handler, played = _play_and_pay("play:T056", 1)

    def pick(e, d):
        if d["kind"] == "choose_cards" and d.get("player") == 1:
            for i, o in enumerate(d["options"]):
                if o.get("cid") is not None \
                        and e.cdef(o["cid"]).id == "dmrp10-s03":
                    e.answer([i])
                    return "ok"
        return None

    def stopper(e, d):
        if played and "dmrp10-s03" not in _defns(e, 0, "bz") \
                and not _zone(e, 0, "graveyard"):
            return "stop"
        return None

    _drive(e, _chain(handler, pick, stopper))
    assert _defns(e, 0, "graveyard") == []
    assert "dmrp10-s03" not in _defns(e, 0, "bz")
    deck = _deck_defns(e, 0)
    assert len(deck) == len(snap["deck"]) + 3
    assert deck[:-3] == snap["deck"]
    assert sorted(deck[-3:]) == ["T001", "T003", "dmrp10-s03"]


# ---------- dmx13-015 形C: 出た時、自分の墓地 → 山札に加えてシャッフル ----------

def test_015_form_c_shuffle_into_deck(rules):
    e = setup(rules, {"hand": ["dmx13-015"], "mana": ["T008"] * 6,
                      "graveyard": ["T001", "T003"], "bz": ["T001"]},
              {"bz": ["T001"]})
    snap = {}
    handler, played = _play_and_pay(
        "play:dmx13-015", 0,
        on_play=lambda e: snap.update(deck=_deck_defns(e, 0)))
    _drive(e, _chain(handler, _stop_at_own_attack(played)))
    assert _defns(e, 0, "graveyard") == []
    assert sorted(_deck_defns(e, 0)) == sorted(snap["deck"] + ["T001", "T003"])


# ---------- dmx13-015 形E: ターンのはじめ、一番下が無色クリーチャーなら ----------

def _drive_until_p1_charge(e, extra):
    """相手の最初の charge まで進める（自分の1ターン目の開始時誘発が
    ちょうど1回だけ解決した時点で観測する）。"""

    def stopper(e, d):
        if d["kind"] == "charge" and d.get("player") == 1:
            return "stop"
        return None

    _drive(e, _chain(extra, stopper))


def test_015_form_e_colorless_bottom_summoned(rules):
    e = setup_exact(rules, {"bz": ["dmx13-015"], "deck": ["T423"] * 8},
                    {"bz": ["T001"], "deck": ["T001"] * 8})
    seen = []
    _drive_until_p1_charge(e, _yes_no(True, seen))
    assert seen                       # 破壊してもよいかの諮問があった
    assert "T423" in _defns(e, 0, "bz")        # 一番下の無色獣が召喚された
    assert "dmx13-015" not in _defns(e, 0, "bz")
    assert _defns(e, 0, "graveyard") == ["dmx13-015"]   # T423 は墓地を離れた


def test_015_form_e_decline_keeps_both(rules):
    e = setup_exact(rules, {"bz": ["dmx13-015"], "deck": ["T423"] * 8},
                    {"bz": ["T001"], "deck": ["T001"] * 8})
    seen = []
    _drive_until_p1_charge(e, _yes_no(False, seen))
    assert seen
    assert "dmx13-015" in _defns(e, 0, "bz")
    assert "T423" not in _defns(e, 0, "bz")
    assert _defns(e, 0, "graveyard") == ["T423"]


def test_015_form_e_colored_bottom_no_offer(rules):
    e = setup_exact(rules, {"bz": ["dmx13-015"], "deck": ["T001"] * 8},
                    {"bz": ["T001"], "deck": ["T001"] * 8})
    seen = []
    _drive_until_p1_charge(e, _yes_no(True, seen))
    assert seen == []                 # 有色クリーチャーでは諮問が起きない
    assert "dmx13-015" in _defns(e, 0, "bz")
    assert _defns(e, 0, "graveyard") == ["T001"]   # 一番下は墓地に置かれる


# ---------- dmx22a-009 形A: 攻撃時、自分の墓地 → 山札の一番下 ----------

def test_009_form_a_attack_trigger(rules):
    e = setup(rules, {"bz": ["dmx22a-009"],
                      "graveyard": ["T001", "T003", "T004"]},
              {"bz": ["T001"]})
    snap = {}

    def on_dec(e, d):
        keys = [o["key"] for o in d["options"]]
        if snap.get("answered"):
            return "stop"   # 誘発は宣言時に解決済み（次の決定で観測）
        if d["kind"] == "attack" and d.get("player") == 0 \
                and "attack:dmx22a-009:player" in keys:
            snap["deck"] = _deck_defns(e, 0)
            snap["answered"] = True
            e.answer([keys.index("attack:dmx22a-009:player")])
            return "ok"
        return None

    _drive(e, on_dec)
    assert _defns(e, 0, "graveyard") == []
    deck = _deck_defns(e, 0)
    assert len(deck) == len(snap["deck"]) + 3
    assert deck[:-3] == snap["deck"]               # 既存の山札の順序は不変
    assert sorted(deck[-3:]) == ["T001", "T003", "T004"]   # 一番下に集合として


# ---------- dmx22a-009 出た時誘発: 自分の獣が出たら1枚引き、上1枚をマナへ ----------

def test_009_entry_trigger_draw_and_mana_put(rules):
    e = setup(rules, {"bz": ["dmx22a-009"], "hand": ["T001"],
                      "mana": ["T001", "T001"]},
              {"bz": ["T001"]})
    snap = {}
    handler, played = _play_and_pay(
        "play:T001", 0,
        on_play=lambda e: snap.update(deck=_deck_defns(e, 0)))
    _drive(e, _chain(handler, _stop_at_own_attack(played)))
    deck = _deck_defns(e, 0)
    assert deck == snap["deck"][2:]        # 1枚引いて、上1枚がマナへ
    assert _defns(e, 0, "hand") == [snap["deck"][0]]   # 引いた1枚だけが手札
    mana = _defns(e, 0, "mana")
    assert len(mana) == 3 and snap["deck"][1] in mana
