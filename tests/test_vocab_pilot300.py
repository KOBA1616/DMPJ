"""語彙パイロット第300弾（2026-11-20）の検証。

skip_turn_remainder（純粋3件: dm26ex4-031 / dm26ex4-sec012 =
切札混成 ゴッド・タイムの2印刷、dmr21-021 = 時の宮殿 ベルファーレ）。
3件の partial はいずれも「ターンの残りをとばす処理を表す語彙が無い」と
書いているが、効果本体は既存の op end_turn（s.skip_rest を立て、
現在の効果の解決を終えてから次のプレイヤーのターンへ進む。
ターン終了時の誘発は起きない = 公式ルールどおり）で足り、
converted に14件の使用先例＋第203弾プロト T510 の遅延形がある。
**ギャップ名のドリフト**。本弾は新語彙・エンジン変更なしで、
残っていた3つの誘発形を実挙動で固定する:

- 形A（ゴッド・タイム）: EXライフシールド離脱の共通誘発
  {event: move, from: shield, subject: {exlife_of: self}}（第291弾）と
  効果先頭の {op: may, body: [end_turn]}（任意誘発の正規形）。
  ブレイク経路と破壊置換経路の両方で固定する。
- 形B（ベルファーレ第1節）: 破壊された時 {event: move, from: bz,
  to: graveyard, reason: destroy, subject: self} + [end_turn]（必須）。
- 形C（ベルファーレ第2節）: 自分のシールドがブレイクされた時
  {event: break, player: you} + if {exists: {ref: self,
  filter: {tapped: true}}}（第290弾 dm25bd2-003 の ref＋filter 形）+
  [end_turn]（必須）。条件「このクリーチャーがタップしていれば」は
  文法上、第2のタイミング句に直結するため破壊側には付けない
  （解釈判断として docs に記録。ラウンド335で再確認する）。
"""
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()
PROTOS = ("T907", "T908", "T909")

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


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def _exlife_shield(e, p):
    return next((c for c in e.zlist("shield", p)
                 if e.s.cards[c].exlife_of is not None), None)


def _bz(e, p, defn):
    return [c for c in e.zlist("bz", p) if e.s.cards[c].defn == defn
            and e.s.cards[c].controller == p]


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


def _pick_shield_hook(st, which):
    """choose_shields のたびに、which="ex" なら EXライフシールド、
    "normal" ならそれ以外のシールドを選ぶ（2回目のブレイクで
    EXライフシールドを誤って割らないため毎回選ぶ）。"""
    def hook(e, d, keys):
        if d["kind"] == "choose_shields":
            ex = _exlife_shield(e, 0)
            for i, o in enumerate(d["options"]):
                if (o.get("cid") == ex) == (which == "ex"):
                    if not st.get("broke"):
                        st["broke"] = True
                        st["broken_cid"] = o["cid"]
                    return [i]
            return None
        return None
    return hook


def _p1_attack_hook(st):
    """相手（P1）の T001 のプレイヤー攻撃を数えながら実行する。"""
    def hook(e, d, keys):
        if d["kind"] == "attack" and d.get("player") == 1 \
                and "attack:T001:player" in keys:
            st["p1_attacks"] = st.get("p1_attacks", 0) + 1
            if st["p1_attacks"] >= 2:
                st["event"] = True     # 判別テストの停止条件用
            return [keys.index("attack:T001:player")]
        return None
    return hook


def _may_hook(st, answer_yes):
    def hook(e, d, keys):
        if d["kind"] == "yes_no" and st.get("broke") \
                and not st.get("may_done"):
            st["may_done"] = True
            st["may_asked"] = True
            st["event"] = True
            return [keys.index("yes" if answer_yes else "no")]
        return None
    return hook


def _recorder(st):
    """イベント発生後の決定を記録する（とばされた側の決定が
    出ていないことの確認用）。"""
    def hook(e, d, keys):
        if st.get("event"):
            st.setdefault("after", []).append((d["kind"], d.get("player")))
        return None
    return hook


def _charge_watch(st, turn):
    """イベント後、P0 の charge（ターン turn）で止める。"""
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


def test_parse_protos():
    for cid in PROTOS:
        parse_card(_proto_card(cid), TABLES)
    assert FORM_A in parse_card(_proto_card("T907"), TABLES).abilities
    assert FORM_B in parse_card(_proto_card("T908"), TABLES).abilities
    assert FORM_C in parse_card(_proto_card("T909"), TABLES).abilities


# ---------- 形A: EXライフシールド離脱 → may でターンの残りをとばす ----------

def _form_a_game(rules, answer_yes, which="ex"):
    e = setup(rules, {"hand": ["T907"], "mana": ["T010"] * 5},
              {"bz": ["T001", "T001"], "mana": ["T034"] * 4},
              filler="T002")
    st = {}
    _drive(e, _chain(_recorder(st), _charge_watch(st, 3),
                     _play_hook("T907", st), _pick_shield_hook(st, which),
                     _may_hook(st, answer_yes), _p1_attack_hook(st)))
    return e, st


def test_form_a_break_yes_skips_rest_of_turn(rules):
    """相手の攻撃で EXライフシールドが割れる → 「とばしてもよい」に
    yes → 相手のターンはその場で終わり、2体目は攻撃できない。"""
    e, st = _form_a_game(rules, True)
    assert st.get("may_asked") and st.get("broke")
    assert st["p1_attacks"] == 1
    assert st["p0_charge_turn"] == 3
    assert _no_p1_main_or_attack_after(st)
    assert _bz(e, 0, "T907")          # 本体は場に残る（割れたのは盾だけ）


def test_form_a_break_no_continues_turn(rules):
    """may に no → ターンは続き、相手の2体目も攻撃する（判別）。"""
    e, st = _form_a_game(rules, False)
    assert st.get("may_asked")
    assert st["p1_attacks"] == 2
    assert st["p0_charge_turn"] == 3


def test_form_a_normal_shield_break_does_not_fire(rules):
    """EXライフでない普通のシールドが割れても発火しない（判別）。"""
    e, st = _form_a_game(rules, True, which="normal")
    assert st.get("broke") and not st.get("may_asked")
    assert st["p1_attacks"] == 2


def test_form_a_destroy_route_yes_skips(rules):
    """破壊呪文 → EXライフ置換でシールドが墓地に離れる → yes →
    呪文を唱えた相手のターンは終わる（攻撃も追加のメインも出ない）。
    本体は置換で場に残る。"""
    e = setup(rules, {"hand": ["T907"], "mana": ["T010"] * 5},
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
        # 破壊先は T907 のみで自動確定する（候補1件は決定を出さない）。
        # 置換→誘発の may が最初の yes_no。
        if d["kind"] == "yes_no" and st.get("cast") \
                and not st.get("may_done"):
            st["may_done"] = True
            st["may_asked"] = True
            return [keys.index("yes")]
        return None

    _drive(e, _chain(_recorder(st), _charge_watch(st, 3),
                     _play_hook("T907", st), cast_hook, may_hook,
                     _p1_attack_hook(st)))
    assert st.get("may_asked")
    assert _bz(e, 0, "T907")                       # 置換で残った
    assert _exlife_shield(e, 0) is None            # 盾は盾ゾーンに無い
    assert len(e.zlist("graveyard", 0)) == 1       # かわりにシールドが墓地へ
    assert st["p0_charge_turn"] == 3
    assert st.get("p1_attacks", 0) == 0
    assert _no_p1_main_or_attack_after(st)


# ---------- 形B: 破壊された時 → ターンの残りをとばす（必須） ----------

def _form_b_game(rules, target_defn):
    e = setup(rules, {"bz": ["T908", "T001"]},
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
            hit = [i for i, k in enumerate(keys) if target_defn in k]
            if hit:
                st["targeted"] = True
                return [hit[0]]
        return None

    _drive(e, _chain(_recorder(st), _charge_watch(st, 3), cast_hook,
                     _p1_attack_hook(st)))
    return e, st


def test_form_b_destroyed_skips_rest_of_turn(rules):
    """相手ターンに T908 が破壊される → そのターンの残りがとび、
    相手は攻撃できない。"""
    e, st = _form_b_game(rules, "T908")
    assert not _bz(e, 0, "T908")
    assert [c for c in e.zlist("graveyard", 0)
            if e.s.cards[c].defn == "T908"]
    assert st.get("p1_attacks", 0) == 0
    assert st["p0_charge_turn"] == 3
    assert _no_p1_main_or_attack_after(st)


def test_form_b_other_creature_destroyed_does_not_fire(rules):
    """他のクリーチャーが破壊されても発火しない（判別）。
    相手は通常通り攻撃まで行う。"""
    e, st = _form_b_game(rules, "T001")
    assert _bz(e, 0, "T908")
    assert st["p1_attacks"] == 1
    assert st["p0_charge_turn"] == 3


# ---------- 形C: 自分の盾ブレイク＋自身タップ → ターンの残りをとばす ----------

def test_form_c_tapped_break_skips_rest_of_turn(rules):
    """T909 が攻撃してタップした状態で相手ターンに自分のシールドが
    ブレイクされる → ターンの残りがとび、相手の2体目は攻撃できない。"""
    e = setup(rules, {"bz": ["T909"]}, {"bz": ["T001", "T001"]}, filler="T002")
    st = {}

    def p0_attack_hook(e, d, keys):
        if d["kind"] == "attack" and d.get("player") == 0 \
                and e.s.turn == 3 and not st.get("p0_attacked"):
            st["p0_attacked"] = True
            if "attack:T909:player" in keys:
                return [keys.index("attack:T909:player")]
            return [keys.index("pass")]         # 攻撃決定の min は1
        return None

    def p1_hook(e, d, keys):
        if d["kind"] == "attack" and d.get("player") == 1:
            if not st.get("p0_attacked"):
                return [keys.index("pass")]     # 2ターン目は攻撃しない
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


def test_form_c_untapped_break_does_not_skip(rules):
    """T909 がタップしていなければ、自分のシールドがブレイクされても
    発火せず、相手の2体目も攻撃する（判別）。"""
    e = setup(rules, {"bz": ["T909"]}, {"bz": ["T001", "T001"]}, filler="T002")
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
