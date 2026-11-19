"""語彙パイロット第288弾: 文明の一致（civilization_match）。

「そのカードの文明と同じ文明のカードが自分のマナゾーンにあれば」の判定が
欠けていた。不足は1点だけで、既存の参照特性式（cost_of / power_of /
name_of / races_of）の対になる式 `civs_of` を足す:

- selectors.eval_expr に `civs_of`（参照カードの文明の和集合。races_of と同形）
- selectors._EXPR_KEYS と _chars_val の再入時辞書に civs を追加
- ops._bake_refs のベイク対象に追加（継続的効果のフィルタ用。races_of と同じ）
- defs の式検証と schema.py の expr 定義に受理を追加し、スキーマを再生成

フィルタの civs は辞書値を式として解決時に評価する既存の経路
（candidates の各分岐）を通るため、{civs: {civs_of: 変数名}} と書ける。
条件は eval_cond の exists で受ける。破壊・捨て札の対象は move の as で
移動後の参照を束縛するので、墓地に置かれた後のカードでも文明を読める。

形は3つ:
- 形A（T829、dm27-026 暗黒螺旋）: 相手が手札を1枚選んで捨てる（chooser: opp、
  as で束縛）→ {op: if, cond: exists（自分のマナに civs_of の文明）} で
  相手が自分のマナを1枚選んで墓地に置く。
- 形B（T830、dm27-047 デビル・スモーク）: 相手のタップされていない
  クリーチャーを破壊（as で束縛）→ 一致すればカードを1枚引いてもよい。
- 形C（T831、dmr21-002 ワルスラ・プリンスS）: 自分の他のクリーチャーを
  召喚した時（when の reason: summon。play_free は 112.3g で召喚に当たる
  ため reason: summon を持ち、reason: put の「出す」は当たらない）、
  may で破壊し、実際に墓地に置かれた時だけ（exists {ref, zone: graveyard}
  のゲート）山札の上から1枚を表向きにし（choose + reveal）、破壊した
  クリーチャーと同じ文明を持つクリーチャーならバトルゾーンに出し、
  そうでなければ手札に加える。

Rust: civs_of を含むフィルタは解決時評価が要るため Python パス。
新規 GameState フィールドなし。
"""
import copy

import pytest
from conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card
from dmsim.engine.scenario import build

TABLES = load_tables()
IDS = ("T829", "T830", "T831")

FORM_A_OPS = [
    {"op": "move",
     "select": {"zone": "hand", "owner": "opp", "chooser": "opp", "count": 1},
     "to": "graveyard", "reason": "discard", "as": "dropped"},
    {"op": "if",
     "cond": {"exists": {"zone": "mana", "owner": "you",
                         "filter": {"civs": {"civs_of": "dropped"}}}},
     "then": [{"op": "move",
               "select": {"zone": "mana", "owner": "opp", "chooser": "opp",
                          "count": 1},
               "to": "graveyard", "reason": "put"}]},
]

FORM_B_OPS = [
    {"op": "move",
     "select": {"zone": "bz", "owner": "opp",
                "filter": {"types": ["creature"], "tapped": False}, "count": 1},
     "to": "graveyard", "reason": "destroy", "as": "victim"},
    {"op": "if",
     "cond": {"exists": {"zone": "mana", "owner": "you",
                         "filter": {"civs": {"civs_of": "victim"}}}},
     "then": [{"op": "may",
               "body": [{"op": "draw", "count": 1}]}]},
]

FORM_C = {"kind": "trigger",
          "when": {"event": "move", "to": "bz", "reason": "summon",
                   "subject": {"owner": "you", "other": True,
                               "filter": {"types": ["creature"]}}},
          "effect": [
              {"op": "may",
               "body": [
                   {"op": "move",
                    "select": {"ref": "event.subject"},
                    "to": "graveyard", "reason": "destroy", "as": "sac"},
                   {"op": "if",
                    "cond": {"exists": {"ref": "sac", "zone": "graveyard"}},
                    "then": [
                        {"op": "choose",
                         "select": {"zone": "deck", "owner": "you",
                                    "from_top": 1},
                         "reveal": True, "as": "top"},
                        {"op": "if",
                         "cond": {"exists": {"ref": "top",
                                             "filter": {
                                                 "types": ["creature"],
                                                 "civs": {"civs_of": "sac"}}}},
                         "then": [{"op": "move", "select": {"ref": "top"},
                                   "to": "bz", "reason": "put"}],
                         "else": [{"op": "move", "select": {"ref": "top"},
                                   "to": "hand", "reason": "draw"}]}]}]}]}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)
    assert parse_card(_proto_card("T829"), TABLES).spell == FORM_A_OPS
    assert parse_card(_proto_card("T830"), TABLES).spell == FORM_B_OPS
    d = parse_card(_proto_card("T831"), TABLES)
    assert [a for a in d.abilities if a["kind"] == "trigger"] == [FORM_C]
    assert "double_breaker" in d.keywords


def test_unknown_expr_key_rejected():
    bad = copy.deepcopy(_proto_card("T829"))
    bad["spell"][1]["cond"]["exists"]["filter"]["civs"] = {"civs_off": "dropped"}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def setup_exact(rules, p0, p1=None, filler="T002"):
    """山札の中身を spec の deck リストだけにする（deck_exact）。
    山札の並びは seed でシャッフルされるため、テストは実状態を読む。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": 1, "deck_size": 20,
                         "deck_exact": [True, True]})


def _zone(e, player, zone):
    lst = list(e.zlist(zone, player))
    if zone == "bz":   # バトルゾーンは共有リストなので controller で絞る
        lst = [c for c in lst if e.s.cards[c].controller == player]
    return lst


def _defn(e, cid):
    return e.cdef(cid).id


def _zone_of(e, cid):
    return e.s.cards[cid].zone


def _drive(e, on_decision, limit=600):
    """汎用ドライバ（第287弾と同形）。on_decision の戻り値:
    "stop" = ここで止める / "ok" = ハンドラが回答済み / None = 汎用回答。"""
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


def _play_and_pay(play_key, player=0):
    played = []

    def handler(e, d):
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == player \
                and play_key in keys:
            played.append(True)
            e.answer([keys.index(play_key)])
            return "ok"
        if played and d["kind"] == "pay_mana":
            e.answer([0])
            return "ok"
        return None

    return handler, played


def _pick_defn(want_defn, player):
    """choose_cards で want_defn のカードを選ぶハンドラ部品。"""
    def handler(e, d):
        if d["kind"] == "choose_cards" and d.get("player") == player:
            for i, o in enumerate(d["options"]):
                if o.get("cid") is not None and _defn(e, o["cid"]) == want_defn:
                    e.answer([i])
                    return "ok"
        return None
    return handler


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


def _chain(*handlers, stop=None):
    def on_dec(e, d):
        for h in handlers:
            r = h(e, d)
            if r:
                return r
        if stop and stop(e, d):
            return "stop"
        return None
    return on_dec


def _stop_at_charge(player):
    def stop(e, d):
        return d["kind"] == "charge" and d.get("player") == player
    return stop


# ---------- 式とフィルタ: civs_of の評価 ----------

def test_civs_of_expr_and_filter(rules):
    e = setup(rules, {"mana": ["T034", "T001"]},
              {"graveyard": ["T010", "T030", "T008"]})
    gy = { _defn(e, c): c for c in _zone(e, 1, "graveyard") }
    env = {"you": 0, "vars": {"v": [e.s.ref(gy["T010"])]}}
    assert e.eval_expr({"civs_of": "v"}, env) == ["water"]
    # 自分のマナに水は無いので一致しない
    assert e.candidates({"zone": "mana", "owner": "you",
                         "filter": {"civs": {"civs_of": "v"}}}, env) == []
    # 多色カードは文明の和集合を返す
    env["vars"]["v"] = [e.s.ref(gy["T030"])]
    assert e.eval_expr({"civs_of": "v"}, env) == ["light", "water"]
    # 火のカードを指せば、自分のマナの火が一致する
    env["vars"]["v"] = [e.s.ref(_zone(e, 0, "mana")[0])]
    hit = e.candidates({"zone": "mana", "owner": "you",
                        "filter": {"civs": {"civs_of": "v"}}}, env)
    assert [_defn(e, c) for c in hit] == ["T034"]


# ---------- 形A: 捨てたカードの文明 ----------

def _cast_a(rules, p0_mana, p1_hand, discard_defn):
    e = setup(rules, {"hand": ["T829"], "mana": p0_mana},
              {"hand": p1_hand, "mana": ["T001", "T001"]})
    handler, played = _play_and_pay("play:T829")
    seen_choose = []

    def watch(e, d):
        if d["kind"] == "choose_cards":
            seen_choose.append((d.get("player"),
                                [_defn(e, o["cid"]) for o in d["options"]
                                 if o.get("cid") is not None]))
        return None

    on_dec = _chain(watch, handler, _pick_defn(discard_defn, 1),
                    stop=_stop_at_charge(1))
    _drive(e, on_dec)
    assert played
    return e, seen_choose


def test_form_a_match_mana_to_graveyard(rules):
    # 自分のマナに火がある。相手が火のカードを捨てる → 相手のマナが墓地へ
    e, seen = _cast_a(rules, ["T008", "T034", "T001", "T001", "T001"],
                      ["T034", "T010"], "T034")
    assert len(_zone(e, 1, "mana")) == 1
    gy = [_defn(e, c) for c in _zone(e, 1, "graveyard")]
    assert gy.count("T034") == 1 and gy.count("T001") == 1
    # 選択は2回とも相手（捨て札とマナ）
    assert [p for p, _ in seen] == [1, 1]


def test_form_a_no_match(rules):
    # 自分のマナに火が無い → 第2文は不発。相手のマナは不変
    e, seen = _cast_a(rules, ["T008", "T010", "T010", "T001", "T001"],
                      ["T034", "T001"], "T034")
    assert len(_zone(e, 1, "mana")) == 2
    assert [_defn(e, c) for c in _zone(e, 1, "graveyard")] == ["T034"]
    assert len(seen) == 1   # 捨て札の選択だけ


def test_form_a_multicolor_discard_matches_by_one_civ(rules):
    # 捨てた多色（光/水）は、自分のマナの水だけでも一致する
    e, seen = _cast_a(rules, ["T008", "T010", "T001", "T001", "T001"],
                      ["T030", "T001"], "T030")
    assert len(_zone(e, 1, "mana")) == 1
    assert "T030" in [_defn(e, c) for c in _zone(e, 1, "graveyard")]


# ---------- 形B: 破壊したクリーチャーの文明 ----------

def _cast_b(rules, p0_mana, p1_bz, draw_answer=None):
    e = setup(rules, {"hand": ["T830"], "mana": p0_mana}, {"bz": p1_bz})
    handler, played = _play_and_pay("play:T830")
    seen_yes_no = []
    parts = [handler]
    if draw_answer is not None:
        parts.append(_yes_no(draw_answer, seen_yes_no))
    else:
        def watch(e, d):
            if d["kind"] == "yes_no":
                seen_yes_no.append(d)
                return "stop"
            return None
        parts.append(watch)
    _drive(e, _chain(*parts, stop=_stop_at_charge(1)))
    assert played
    return e, seen_yes_no


def test_form_b_match_and_draw(rules):
    e, seen = _cast_b(rules, ["T008", "T034", "T001", "T001", "T001"],
                      ["T034"], draw_answer=True)
    assert len(seen) == 1
    assert _zone(e, 1, "graveyard") and \
        _defn(e, _zone(e, 1, "graveyard")[0]) == "T034"
    assert len(_zone(e, 0, "hand")) == 1   # 引いた1枚だけが手札にある


def test_form_b_match_and_decline(rules):
    e, seen = _cast_b(rules, ["T008", "T034", "T001", "T001", "T001"],
                      ["T034"], draw_answer=False)
    assert len(seen) == 1
    assert len(_zone(e, 0, "hand")) == 0


def test_form_b_no_match_no_offer(rules):
    e, seen = _cast_b(rules, ["T008", "T034", "T010", "T010", "T034"],
                      ["T001"], draw_answer=None)
    assert seen == []                       # 諮問自体が起きない
    assert _defn(e, _zone(e, 1, "graveyard")[0]) == "T001"
    assert len(_zone(e, 0, "hand")) == 0


def test_form_b_tapped_creature_excluded(rules):
    e = setup(rules, {"bz": ["T831"]}, {"bz": ["T001", "T034"]})
    bz1 = _zone(e, 1, "bz")
    tapped = next(c for c in bz1 if _defn(e, c) == "T034")
    e.s.cards[tapped].tapped = True
    env = {"you": 0, "vars": {}}
    cands = e.candidates({"zone": "bz", "owner": "opp",
                          "filter": {"types": ["creature"], "tapped": False}},
                         env)
    assert [_defn(e, c) for c in cands] == ["T001"]


# ---------- 形C: 召喚した時、破壊したクリーチャーと同じ文明 ----------

def _summon_with_t831(rules, deck, answer_yes=True):
    e = setup_exact(rules, {"bz": ["T831"], "hand": ["T001"],
                            "mana": ["T001", "T001"], "deck": deck},
                    {"deck": ["T827"] * 3})
    handler, played = _play_and_pay("play:T001")
    seen_yes_no = []
    snap = []

    def watch(e, d):
        if played and not snap:
            snap.append(list(_zone(e, 0, "deck")))
        return None

    on_dec = _chain(watch, handler, _yes_no(answer_yes, seen_yes_no),
                    stop=_stop_at_charge(1))
    _drive(e, on_dec)
    assert played
    summoned = next(c for c in _zone(e, 0, "graveyard")
                    if _defn(e, c) == "T001") if answer_yes else None
    return e, seen_yes_no, snap[0], summoned


def test_form_c_match_puts_top_into_bz(rules):
    e, seen, snap, summoned = _summon_with_t831(rules, ["T827"] * 8)
    assert len(seen) == 1                    # 破壊の諮問が1度だけ
    top = snap[0]
    assert _zone_of(e, top) == "bz"          # 同じ文明（自然）の獣は場に出る
    assert e.s.cards[top].controller == 0
    assert summoned is not None              # 召喚した獣は破壊された


def test_form_c_other_civ_goes_to_hand(rules):
    e, seen, snap, summoned = _summon_with_t831(rules, ["T034"] * 8)
    top = snap[0]
    assert _zone_of(e, top) == "hand"        # 火は自然と一致しない
    assert summoned is not None


def test_form_c_spell_goes_to_hand(rules):
    e, seen, snap, summoned = _summon_with_t831(rules, ["T003"] * 8)
    top = snap[0]
    assert _zone_of(e, top) == "hand"        # クリーチャーでなければ手札へ
    assert summoned is not None


def test_form_c_decline_keeps_everything(rules):
    e, seen, snap, _ = _summon_with_t831(rules, ["T827"] * 8, answer_yes=False)
    assert len(seen) == 1
    assert any(_defn(e, c) == "T001" for c in _zone(e, 0, "bz"))
    assert _zone(e, 0, "deck") == snap       # 山札は動かない


def test_form_c_no_trigger_on_own_summon(rules):
    # T831 自身の召喚では誘発しない（other: true）
    e = setup(rules, {"hand": ["T831"], "mana": ["T010"] * 6}, {})
    handler, played = _play_and_pay("play:T831")
    seen_yes_no = []
    _drive(e, _chain(handler, _yes_no(True, seen_yes_no),
                     stop=_stop_at_charge(1)))
    assert played and seen_yes_no == []


def test_form_c_no_trigger_on_opponent_summon(rules):
    # 相手の召喚では誘発しない（owner: you）
    e = setup(rules, {"bz": ["T831"]},
              {"hand": ["T001"], "mana": ["T001", "T001"]})
    handler, played = _play_and_pay("play:T001", player=1)
    seen_yes_no = []
    _drive(e, _chain(handler, _yes_no(True, seen_yes_no),
                     stop=_stop_at_charge(0)))
    assert played and seen_yes_no == []


def test_form_c_reason_gate(rules):
    # 「召喚した時」は reason: summon の移動だけ。当てるのは _match_when の
    # レコード照合（subject の照合は _pattern_match 側で別に行われる）
    e = setup(rules, {"bz": ["T831", "T001"]}, {})
    when = FORM_C["when"]
    bz = _zone(e, 0, "bz")
    self_ref = e.s.ref(next(c for c in bz if _defn(e, c) == "T831"))
    subj_ref = e.s.ref(next(c for c in bz if _defn(e, c) == "T001"))
    env = {"you": 0, "self": self_ref}
    base = {"ev": "move", "to": "bz", "subject": subj_ref}
    assert e._match_when(when, {**base, "reason": "summon"}, env) is True
    assert e._match_when(when, {**base, "reason": "put"}, env) is False
