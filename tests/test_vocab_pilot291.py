"""語彙パイロット第291弾（2026-11-19）の検証。

EXライフシールドの追跡（ex_life_shield_tracking、純粋3件）。
「このクリーチャーの『EXライフ』シールドが自分のシールドゾーンを離れた時」の
誘発は第190弾の when.subject {exlife_of: self} で実装済みで、登録先例も
dmrp17-s08（離れた時、相手クリーチャーすべてをタップ＋凍結）等がある。
対象3件の partial はいずれも「追跡する語彙が無い」と書いており、ギャップ名の
ドリフト。本弾は新語彙なしで、残っていた実挙動の検証を行う:

- 形A（dm23bd1-005）: 誘発＋ if {is_turn: opp} のターンゲート＋
  tap {zone: mana, owner: opp, count: all, no_untap_next: true}。
  第190弾は合成 move イベントの push でしか検証していなかったため、
  本弾では実際のブレイク経路と、バトル敗北→EXライフ置換経路で固定する。
- 形B（dm23ex2-024）: 誘発＋ tap 1体＋ no_untap_next（dmrp17-s08 の
  count: all を count: 1 にした形）。破壊置換経路とブレイク経路の両方。
- 形C（dmrp17-s06）: 誘発＋ modify {mod: {no_leave: true},
  duration: end_of_turn}。置換で残った場合も付与され、そのターンの
  2度目の破壊を（置換ではなく）no_leave が止めること、ターン経過で
  切れることを固定する。
"""
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()
PROTOS = ("T847", "T848", "T849", "T850")

FORM_A = {"kind": "trigger",
          "when": {"event": "move", "from": "shield",
                   "subject": {"exlife_of": "self"}},
          "if": {"is_turn": "opp"},
          "effect": [{"op": "tap",
                      "select": {"zone": "mana", "owner": "opp", "count": "all"},
                      "no_untap_next": True}]}

FORM_B = {"kind": "trigger",
          "when": {"event": "move", "from": "shield",
                   "subject": {"exlife_of": "self"}},
          "effect": [{"op": "tap",
                      "select": {"zone": "bz", "owner": "opp",
                                 "filter": {"types": ["creature"]}, "count": 1},
                      "no_untap_next": True}]}

FORM_C = {"kind": "trigger",
          "when": {"event": "move", "from": "shield",
                   "subject": {"exlife_of": "self"}},
          "effect": [{"op": "modify", "select": {"ref": "self"},
                      "mod": {"no_leave": True}, "duration": "end_of_turn"}]}


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def _exlife_shield(e, p):
    return next((c for c in e.zlist("shield", p)
                 if e.s.cards[c].exlife_of is not None), None)


def _bz(e, p, defn):
    return [c for c in e.zlist("bz", p) if e.s.cards[c].defn == defn
            and e.s.cards[c].controller == p]


def _mana_states(e, p):
    return [(e.s.cards[c].tapped, e.s.cards[c].no_untap_next)
            for c in e.zlist("mana", p)]


def _drive(e, hook, limit=900):
    """hook(e, d, keys) は答えのリスト / None（既定） / "stop" を返す。"""
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


def _play_hook(tid, st):
    def hook(e, d, keys):
        if d["kind"] == "main" and not st.get("played") and f"play:{tid}" in keys:
            st["played"] = True
            return [keys.index(f"play:{tid}")]
        return None
    return hook


def _pick_shield_hook(st, which):
    """choose_shields で、which="ex" なら EXライフシールド、"normal" なら
    それ以外のシールドを選ぶ。"""
    def hook(e, d, keys):
        if d["kind"] == "choose_shields" and not st.get("broke"):
            ex = _exlife_shield(e, 0)
            for i, o in enumerate(d["options"]):
                if (o.get("cid") == ex) == (which == "ex"):
                    st["broke"] = True
                    st["broken_cid"] = o["cid"]
                    return [i]
            return None
        return None
    return hook


def _chain(*hooks):
    def hook(e, d, keys):
        for h in hooks:
            ans = h(e, d, keys)
            if ans is not None:
                return ans
        return None
    return hook


def test_parse_protos():
    for cid in PROTOS:
        parse_card(_proto_card(cid), TABLES)
    assert FORM_A in parse_card(_proto_card("T847"), TABLES).abilities
    assert FORM_B in parse_card(_proto_card("T848"), TABLES).abilities
    assert FORM_C in parse_card(_proto_card("T849"), TABLES).abilities


# ---------- 形A: ブレイク経路＋凍結の持続 ----------

def test_form_a_break_freezes_all_opponent_mana(rules):
    """相手の攻撃で EXライフシールドが割れる → 相手のマナすべてが
    タップ＋凍結。次の相手のターンのはじめにアンタップせず（印は消費）、
    さらに次の相手のターンのはじめに通常通りアンタップする。"""
    e = setup(rules, {"hand": ["T847"], "mana": ["T034"] * 5},
              {"bz": ["T001"], "mana": ["T010"] * 4, "hand": ["T001"]})
    st = {"snaps": []}

    def hook(e, d, keys):
        a = _play_hook("T847", st)(e, d, keys)
        if a is not None:
            return a
        a = _pick_shield_hook(st, "ex")(e, d, keys)
        if a is not None:
            return a
        if d["kind"] == "attack" and d["player"] == 1 \
                and not st.get("attacked"):
            if "attack:T001:player" in keys:
                st["attacked"] = True
                return [keys.index("attack:T001:player")]
            return None
        if st.get("broke") and "just_after" not in st:
            st["just_after"] = _mana_states(e, 1)
        if st.get("broke") and d["kind"] == "charge" and d["player"] == 1:
            st["snaps"].append(_mana_states(e, 1))
            if len(st["snaps"]) >= 2:
                return "stop"
        return None

    _drive(e, hook)
    assert st.get("attacked") and st.get("broke")
    assert st["just_after"] == [(True, True)] * 4     # 全マナがタップ＋凍結
    assert st["snaps"][0] == [(True, False)] * 4      # 次の相手ターン開始: 凍結で起きない（印は消費）
    assert st["snaps"][1] == [(False, False)] * 4     # さらに次は通常通りアンタップ


def test_form_a_normal_shield_break_does_not_fire(rules):
    """EXライフでない普通のシールドが割れても発火しない（判別）。"""
    e = setup(rules, {"hand": ["T847"], "mana": ["T034"] * 5},
              {"bz": ["T001"], "mana": ["T010"] * 4, "hand": ["T001"]})
    st = {}

    def hook(e, d, keys):
        a = _play_hook("T847", st)(e, d, keys)
        if a is not None:
            return a
        a = _pick_shield_hook(st, "normal")(e, d, keys)
        if a is not None:
            return a
        if d["kind"] == "attack" and d["player"] == 1 and not st.get("attacked"):
            if "attack:T001:player" in keys:
                st["attacked"] = True
                return [keys.index("attack:T001:player")]
            return None
        if st.get("broke"):
            st.setdefault("after", []).append(_mana_states(e, 1))
            if len(st["after"]) >= 2:
                return "stop"
        return None

    _drive(e, hook)
    assert st.get("broke")
    assert _exlife_shield(e, 0) is not None           # EXライフシールドは残っている
    for snap in st["after"]:
        assert snap == [(False, False)] * 4           # 相手のマナは無傷


def test_form_a_gate_blocks_on_own_turn(rules):
    """自分のターンにバトル敗北→EXライフ置換でシールドが離れても、
    if {is_turn: opp} のゲートで発火しない。"""
    e = setup(rules, {"hand": ["T847"], "mana": ["T034"] * 5},
              {"bz": ["T460"], "mana": ["T010"] * 4})
    t460 = _bz(e, 1, "T460")[0]
    e.s.cards[t460].tapped = True   # 自分のターン開始では相手の獣はアンタップされない
    st = {}

    def hook(e, d, keys):
        a = _play_hook("T847", st)(e, d, keys)
        if a is not None:
            return a
        if d["kind"] == "attack" and d["player"] == 0 and st.get("played") \
                and not st.get("attacked"):
            if "attack:T847:T460" in keys:
                st["attacked"] = True
                return [keys.index("attack:T847:T460")]
            return None
        if st.get("attacked"):
            st["seen"] = st.get("seen", 0) + 1
            if st["seen"] >= 4:
                return "stop"
        return None

    _drive(e, hook)
    assert st.get("attacked")
    assert _bz(e, 0, "T847")                          # 置換で場に残った
    assert len(e.zlist("graveyard", 0)) == 1          # かわりにシールドが墓地へ
    assert _exlife_shield(e, 0) is None
    assert _mana_states(e, 1) == [(False, False)] * 4  # ゲートで不発


# ---------- 形B: 置換経路とブレイク経路 ----------

def _form_b_fixture(rules):
    return setup(rules, {"hand": ["T848"], "mana": ["T030"] * 5},
                 {"bz": ["T001", "T001"], "hand": ["T056"], "mana": ["T082"] * 3})


def test_form_b_destroy_replacement_taps_and_freezes(rules):
    """相手の破壊呪文 → EXライフ置換でシールドが墓地へ → 相手の獣1体を
    タップ＋凍結。凍結した獣は次の相手のターンのはじめにアンタップしない。"""
    e = _form_b_fixture(rules)
    st = {}

    def hook(e, d, keys):
        a = _play_hook("T848", st)(e, d, keys)
        if a is not None:
            return a
        if d["kind"] == "main" and d["player"] == 1 and st.get("played") \
                and not st.get("cast") and "play:T056" in keys:
            st["cast"] = True
            return [keys.index("play:T056")]
        if d["kind"] == "choose_cards" and st.get("cast") \
                and not st.get("tap_pick"):
            for i, o in enumerate(d["options"]):
                if e.cdef(o["cid"]).id == "T001":
                    st["tap_pick"] = o["cid"]
                    return [i]
            return None
        if st.get("tap_pick") and "just_after" not in st:
            c = e.s.cards[st["tap_pick"]]
            st["just_after"] = (c.tapped, c.no_untap_next)
        if st.get("tap_pick") and d["kind"] == "charge" and d["player"] == 1:
            c = e.s.cards[st["tap_pick"]]
            st["next_start"] = (c.tapped, c.no_untap_next)
            return "stop"
        return None

    _drive(e, hook)
    assert st.get("cast") and st.get("tap_pick")
    assert _bz(e, 0, "T848")                          # 置換で場に残った
    assert len(e.zlist("graveyard", 0)) == 1          # シールドが墓地へ
    assert st["just_after"] == (True, True)           # タップ＋凍結
    assert st["next_start"] == (True, False)          # 次の相手ターン開始でもタップしたまま（印は消費）
    others = [c for c in _bz(e, 1, "T001") if c != st["tap_pick"]]
    assert len(others) == 1
    assert e.s.cards[others[0]].tapped is False       # もう1体は無傷


def test_form_b_spell_break_taps(rules):
    """ブレイク呪文（T850）で EXライフシールドが離れても発火する。
    割れたシールドは持ち主の手札に加わる。"""
    e = setup(rules, {"hand": ["T848"], "mana": ["T030"] * 5},
              {"bz": ["T001", "T001"], "hand": ["T850"], "mana": ["T082"]})
    st = {}

    def hook(e, d, keys):
        a = _play_hook("T848", st)(e, d, keys)
        if a is not None:
            return a
        a = _pick_shield_hook(st, "ex")(e, d, keys)
        if a is not None:
            return a
        if d["kind"] == "main" and d["player"] == 1 and st.get("played") \
                and not st.get("cast") and "play:T850" in keys:
            st["cast"] = True
            return [keys.index("play:T850")]
        if d["kind"] == "choose_cards" and st.get("broke") \
                and not st.get("tap_pick"):
            for i, o in enumerate(d["options"]):
                if e.cdef(o["cid"]).id == "T001":
                    st["tap_pick"] = o["cid"]
                    return [i]
            return None
        if st.get("tap_pick"):
            c = e.s.cards[st["tap_pick"]]
            st["just_after"] = (c.tapped, c.no_untap_next)
            return "stop"
        return None

    _drive(e, hook)
    assert st.get("cast") and st.get("broke") and st.get("tap_pick")
    assert st["just_after"] == (True, True)
    assert e.s.cards[st["broken_cid"]].zone == "hand"  # 割れたシールドは手札へ
    assert _bz(e, 0, "T848")


# ---------- 形C: 置換経路の付与と、ブレイク経路＋失効 ----------

def test_form_c_replacement_grants_no_leave(rules):
    """破壊 → EXライフ置換で残り、離れたシールドの誘発で no_leave が付く。
    同じターンの2度目の破壊は、置換ではなく no_leave が止める。"""
    e = setup(rules, {"hand": ["T849"], "mana": ["T034"] * 5},
              {"bz": ["T001"], "hand": ["T056", "T056"], "mana": ["T082"] * 6})
    st = {"casts": 0}

    def hook(e, d, keys):
        a = _play_hook("T849", st)(e, d, keys)
        if a is not None:
            return a
        if d["kind"] == "main" and d["player"] == 1 and st.get("played") \
                and st["casts"] < 2 and "play:T056" in keys:
            if st["casts"] == 1 and "no_leave_mid" not in st:
                cid = _bz(e, 0, "T849")[0]
                st["no_leave_mid"] = bool(e.chars(cid)["no_leave"])
            st["casts"] += 1
            return [keys.index("play:T056")]
        if st["casts"] >= 2:
            st["seen"] = st.get("seen", 0) + 1
            if st["seen"] >= 3:
                return "stop"
        return None

    _drive(e, hook)
    assert st["casts"] == 2
    assert st["no_leave_mid"] is True                 # 1度目の解決後に no_leave が立っている
    assert _bz(e, 0, "T849")                          # 2度目の破壊も通らなかった
    assert len(e.zlist("graveyard", 0)) == 1          # 墓地はシールド1枚だけ
    assert len([c for c in e.zlist("graveyard", 1)
                if e.s.cards[c].defn == "T056"]) == 2


def test_form_c_break_grant_blocks_destroy_then_expires(rules):
    """ブレイク呪文でシールドが離れたターン中の破壊は no_leave が止め、
    次の相手のターンには失効して破壊が通る。"""
    e = setup(rules, {"hand": ["T849"], "mana": ["T034"] * 5},
              {"hand": ["T850", "T056", "T056"], "mana": ["T082"] * 7})
    st = {"casts": 0}

    def hook(e, d, keys):
        a = _play_hook("T849", st)(e, d, keys)
        if a is not None:
            return a
        a = _pick_shield_hook(st, "ex")(e, d, keys)
        if a is not None:
            return a
        if d["kind"] == "main" and d["player"] == 1 and st.get("played"):
            if not st.get("broke_spell") and "play:T850" in keys:
                st["broke_spell"] = True
                return [keys.index("play:T850")]
            if st.get("broke") and "play:T056" in keys:
                if st["casts"] == 0:
                    st["casts"] = 1
                    st["turn_cast1"] = e.s.turn
                    return [keys.index("play:T056")]
                if st["casts"] == 1 and e.s.turn != st["turn_cast1"]:
                    st["casts"] = 2
                    return [keys.index("play:T056")]
            return None
        if st["casts"] == 1 and "after_first" not in st \
                and d["kind"] in ("main", "charge", "attack"):
            st["after_first"] = bool(_bz(e, 0, "T849"))
        if st["casts"] == 2:
            st["seen"] = st.get("seen", 0) + 1
            if st["seen"] >= 3:
                return "stop"
        return None

    _drive(e, hook)
    assert st.get("broke") and st["casts"] == 2
    assert st["after_first"] is True                  # そのターンの破壊は止められた
    assert not _bz(e, 0, "T849")                      # 次のターンでは破壊が通った
    assert any(e.s.cards[c].defn == "T849" for c in e.zlist("graveyard", 0))
