"""語彙パイロット第289弾: 墓地シャッフル（graveyard_shuffle）。

「墓地をシャッフルし、山札の一番下に置く」「墓地をすべて山札に加えて
シャッフルする」を表す語彙が無いとされていたが、不足は既存語彙の
組み合わせの確認だけだった（ギャップ名のドリフト）:

- move の order: shuffle は「動かす集合だけをシャッフルしてから置く」
  （第163弾で登録先例あり）。position: bottom と組で「墓地をシャッフルし、
  山札の一番下に置く」になる。
- 山札全体をシャッフルする形は move（墓地→山札）＋ {op: shuffle}。

形は5つ:
- 形A（T832、dmx22a-009 の攻撃時）: 自分の墓地すべて → 山札の一番下
  （集合をシャッフル）。
- 形B（T833、dmrp10-s03 の出た時）: 相手の墓地すべて → 相手の山札の
  一番下（集合をシャッフル）。count: all なので選択は無く、chooser は
  機械的に無関係。
- 形C（T834、dmx13-015 の出た時）: 自分の墓地すべて → 山札に加え、
  山札全体をシャッフル。
- 形D（T835、dmrp10-s03 の第3節）: どこからでも自分の墓地に置かれた時
  → 形A（墓地に着いた自分自身も含めて全部戻る）。
- 形E（T836、dmx13-015 の第2節）: 自分のターンのはじめに一番下を墓地に
  置き（第287弾 from_bottom）、進化ではない無色クリーチャーであれば
  （filter {colorless: true, evolution: false} の exists ゲート）自分を
  破壊してもよく、実際に墓地に置かれた時だけ（破壊 move の as で束縛した
  移動後の ref を exists {ref, zone: graveyard} で見るゲート。移動前の
  self ref は世代が変わり一致しない）そのカードを play_free で召喚する。

T833 の第2能力は dmrp10-s03 の第2節（自分のターンの終わりにタップして
いたら1枚引いてもよい）の検証も兼ねる（trigger turn_end + op-if で
self の tapped を見る形）。

新語彙・エンジン変更なし。新規 GameState フィールドなし。
"""
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card
from dmsim.engine.scenario import build

TABLES = load_tables()
IDS = ("T832", "T833", "T834", "T835", "T836")

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


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def _triggers(cid):
    d = parse_card(_proto_card(cid), TABLES)
    return [a for a in d.abilities if a["kind"] == "trigger"]


def test_proto_parse():
    assert _triggers("T832") == [TRIG_A]
    assert _triggers("T833") == [TRIG_B, TRIG_TURN_END]
    d = parse_card(_proto_card("T834"), TABLES)
    assert _triggers("T834") == [TRIG_C]
    assert "cannot_attack" in d.keywords
    assert _triggers("T835") == [TRIG_D]
    d = parse_card(_proto_card("T836"), TABLES)
    assert _triggers("T836") == [TRIG_E]
    assert "cannot_attack" in d.keywords
    assert "double_breaker" in parse_card(_proto_card("T832"), TABLES).keywords


def setup_exact(rules, p0, p1=None, filler="T002"):
    """山札の中身を spec の deck リストだけにする（deck_exact）。"""
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


def _defns(e, player, zone):
    return [_defn(e, c) for c in _zone(e, player, zone)]


def _deck_defns(e, player):
    """山札リスト（先頭 = 一番上、末尾 = 一番下）の defn 列。"""
    return [_defn(e, c) for c in e.s.zones["deck"][player]]


def _drive(e, on_decision, limit=600):
    """汎用ドライバ。on_decision の戻り値: "stop" / "ok" / None（汎用回答）。"""
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


# ---------- 形A: 攻撃時、自分の墓地 → 山札の一番下（シャッフル） ----------

def _attack_t832(e, snap):
    """T832 で攻撃を宣言し、誘発解決直後の最初の決定で止めるハンドラ。"""

    def on_dec(e, d):
        keys = [o["key"] for o in d["options"]]
        if snap.get("answered"):
            return "stop"   # 誘発は宣言時に解決済み（次の決定で観測）
        if d["kind"] == "attack" and d.get("player") == 0 \
                and "attack:T832:player" in keys:
            snap["deck"] = _deck_defns(e, 0)
            snap["answered"] = True
            e.answer([keys.index("attack:T832:player")])
            return "ok"
        return None

    return on_dec


def test_form_a_attack_trigger(rules):
    e = setup(rules, {"bz": ["T832"], "graveyard": ["T001", "T003", "T004"]},
              {"bz": ["T001"]})
    snap = {}
    _drive(e, _attack_t832(e, snap))
    assert _defns(e, 0, "graveyard") == []
    deck = _deck_defns(e, 0)
    assert len(deck) == len(snap["deck"]) + 3
    assert deck[:-3] == snap["deck"]               # 既存の山札の順序は不変
    assert sorted(deck[-3:]) == ["T001", "T003", "T004"]   # 一番下に集合として


def test_form_a_no_graveyard_no_change(rules):
    e = setup(rules, {"bz": ["T832"]}, {"bz": ["T001"]})
    snap = {}
    _drive(e, _attack_t832(e, snap))
    assert _deck_defns(e, 0) == snap["deck"]


# ---------- 形B: 出た時、相手の墓地 → 相手の山札の一番下（シャッフル） ----------

def test_form_b_opponent_graveyard(rules):
    e = setup(rules, {"hand": ["T833"], "mana": ["T030", "T001", "T001"],
                      "bz": ["T001"]},
              {"graveyard": ["T001", "T008"], "bz": ["T001"]})
    snap = {}
    handler, played = _play_and_pay(
        "play:T833", 0,
        on_play=lambda e: snap.update(deck1=_deck_defns(e, 1),
                                      deck0=_deck_defns(e, 0)))

    def stopper(e, d):
        # 召喚と CIP はメイン内で解決する。次の自分の攻撃決定で観測する
        # （相手ターンのドローを跨ぐと山札枚数がずれる）
        if played and d["kind"] == "attack" and d.get("player") == 0:
            return "stop"
        return None

    _drive(e, _chain(handler, stopper))
    assert _defns(e, 1, "graveyard") == []
    deck1 = _deck_defns(e, 1)
    assert len(deck1) == len(snap["deck1"]) + 2
    assert deck1[:-2] == snap["deck1"]
    assert sorted(deck1[-2:]) == ["T001", "T008"]
    assert _deck_defns(e, 0) == snap["deck0"]       # 自分の山札は不変
    assert _defns(e, 0, "graveyard") == []


# ---------- 形C: 出た時、自分の墓地 → 山札に加えてシャッフル ----------

def test_form_c_shuffle_into_deck(rules):
    e = setup(rules, {"hand": ["T834"], "mana": ["T008"] * 6,
                      "graveyard": ["T001", "T003"], "bz": ["T001"]},
              {"bz": ["T001"]})
    snap = {}
    handler, played = _play_and_pay(
        "play:T834", 0, on_play=lambda e: snap.update(deck=_deck_defns(e, 0)))

    def stopper(e, d):
        if played and d["kind"] == "attack" and d.get("player") == 0:
            return "stop"
        return None

    _drive(e, _chain(handler, stopper))
    assert _defns(e, 0, "graveyard") == []
    assert sorted(_deck_defns(e, 0)) == sorted(snap["deck"] + ["T001", "T003"])


# ---------- 形D: どこからでも墓地に置かれた時（自分も含め全部戻る） ----------

def test_form_d_destroy_returns_whole_graveyard(rules):
    e = setup(rules, {"bz": ["T835"], "graveyard": ["T001", "T003"]},
              {"hand": ["T056"], "mana": ["T082"] * 3, "bz": ["T001"]})
    snap = {"deck": _deck_defns(e, 0)}
    handler, played = _play_and_pay("play:T056", 1)

    def pick(e, d):
        if d["kind"] == "choose_cards" and d.get("player") == 1:
            for i, o in enumerate(d["options"]):
                if o.get("cid") is not None and _defn(e, o["cid"]) == "T835":
                    e.answer([i])
                    return "ok"
        return None

    def stopper(e, d):
        if played and not _zone(e, 0, "graveyard") \
                and not _zone(e, 0, "bz"):
            return "stop"
        return None

    _drive(e, _chain(handler, pick, stopper))
    assert _defns(e, 0, "graveyard") == []
    assert "T835" not in _defns(e, 0, "bz")
    deck = _deck_defns(e, 0)
    assert len(deck) == len(snap["deck"]) + 3
    assert deck[:-3] == snap["deck"]
    assert sorted(deck[-3:]) == ["T001", "T003", "T835"]


# ---------- T833 第2節: ターン終わりにタップしていたら引いてもよい ----------

def _attack_with_t833(e, d, state):
    keys = [o["key"] for o in d["options"]]
    if d["kind"] == "attack" and d.get("player") == 0 \
            and "attack:T833:player" in keys:
        state["attacked"] = True
        e.answer([keys.index("attack:T833:player")])
        return "ok"
    return None


def test_turn_end_draw_when_tapped(rules):
    e = setup(rules, {"bz": ["T833"]}, {"bz": ["T001"]})
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

    _drive(e, _chain(lambda e, d: _attack_with_t833(e, d, state),
                     watcher, _yes_no(True, seen), stopper))
    assert state.get("attacked") and seen
    assert len(_zone(e, 0, "hand")) == hand_at_offer["n"] + 1


def test_turn_end_no_draw_when_untapped(rules):
    e = setup(rules, {"bz": ["T833"]}, {"bz": ["T001"]})
    seen = []

    def stopper(e, d):
        if d["kind"] == "charge" and d.get("player") == 1:
            return "stop"
        return None

    _drive(e, _chain(_yes_no(True, seen), stopper))
    assert seen == []   # 攻撃せずアンタップのままなら諮問自体が起きない


# ---------- 形E: ターンのはじめ、一番下が無色クリーチャーなら ----------

def _drive_until_p1_charge(e, extra):
    """相手の最初の charge まで進める（自分の1ターン目の開始時誘発が
    ちょうど1回だけ解決した時点で観測する）。"""

    def stopper(e, d):
        if d["kind"] == "charge" and d.get("player") == 1:
            return "stop"
        return None

    _drive(e, _chain(extra, stopper))


def test_form_e_colorless_bottom_summoned(rules):
    e = setup_exact(rules, {"bz": ["T836"], "deck": ["T423"] * 8},
                    {"bz": ["T001"], "deck": ["T001"] * 8})
    seen = []
    _drive_until_p1_charge(e, _yes_no(True, seen))
    assert seen                       # 破壊してもよいかの諮問があった
    assert "T423" in _defns(e, 0, "bz")        # 一番下の無色獣が召喚された
    assert "T836" not in _defns(e, 0, "bz")
    assert _defns(e, 0, "graveyard") == ["T836"]   # T423 は墓地を離れた


def test_form_e_decline_keeps_both(rules):
    e = setup_exact(rules, {"bz": ["T836"], "deck": ["T423"] * 8},
                    {"bz": ["T001"], "deck": ["T001"] * 8})
    seen = []
    _drive_until_p1_charge(e, _yes_no(False, seen))
    assert seen
    assert "T836" in _defns(e, 0, "bz")
    assert "T423" not in _defns(e, 0, "bz")
    assert _defns(e, 0, "graveyard") == ["T423"]


def test_form_e_colored_bottom_no_offer(rules):
    e = setup_exact(rules, {"bz": ["T836"], "deck": ["T001"] * 8},
                    {"bz": ["T001"], "deck": ["T001"] * 8})
    seen = []
    _drive_until_p1_charge(e, _yes_no(True, seen))
    assert seen == []                 # 有色クリーチャーでは諮問が起きない
    assert "T836" in _defns(e, 0, "bz")
    assert _defns(e, 0, "graveyard") == ["T001"]   # 一番下は墓地に置かれる


def test_form_e_spell_bottom_no_offer(rules):
    e = setup_exact(rules, {"bz": ["T836"], "deck": ["T003"] * 8},
                    {"bz": ["T001"], "deck": ["T001"] * 8})
    seen = []
    _drive_until_p1_charge(e, _yes_no(True, seen))
    assert seen == []
    assert "T836" in _defns(e, 0, "bz")
    assert _defns(e, 0, "graveyard") == ["T003"]


def test_form_e_evolution_bottom_no_offer(rules):
    e = setup_exact(rules, {"bz": ["T836"], "deck": ["T562"] * 8},
                    {"bz": ["T001"], "deck": ["T001"] * 8})
    seen = []
    _drive_until_p1_charge(e, _yes_no(True, seen))
    assert seen == []                 # 無色でも進化クリーチャーは対象外
    assert "T836" in _defns(e, 0, "bz")
    assert _defns(e, 0, "graveyard") == ["T562"]
