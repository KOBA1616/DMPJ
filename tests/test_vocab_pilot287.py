"""語彙パイロット第287弾: 山札の一番下へのアクセス（deck_bottom_card /
deck_bottom_reveal）。

2つのギャップ名は同じ欠落を指している: 山札の「一番下」を選ぶ手段が無い。
本弾の新語彙は3点で、いずれも最小の拡張:

- セレクタキー `from_bottom`（defs の SELECTOR_KEYS + selectors の候補計算）。
  山札リストは上が先頭（from_top が lst[:n]）なので、一番下は末尾の N 枚。
  from_top と同じく、count を書かなければ候補をそのまま返す（決定を出さない）。
- `play_free` の `player` 引数（任意、既定は効果の使用者）。
  「相手はそれをバトルゾーンに出してもよい」（dm32-019）は、出す主体が
  相手でなければならない。選択は select の chooser: opp、実行は player: opp。
- 敗北置換の発生源走査（events._lose_candidates）に手札を追加。
  zone: hand を宣言した lose 置換だけが手札から働く（_replacement の
  「バトルゾーン外の発生源は、そのゾーンを宣言した置換だけ」と同じ規則）。
  《一王二命三眼槍》（dm26rp3-tr007 / dm26sd1-c001）の
  「手札にあるこのカードを表向きにし、山札の下に置いてもよい」のため。

形は5つ:
- 形A（T822、dmr06-002 の末尾節）: 一番下の1枚を手札に加える。
- 形B（T823、一王二命三眼槍の鬼エンド / dmrp05-007）: シールド0の
  プレイヤーがいる時、一番下を墓地に置き、それがコスト5以下の
  クリーチャーなら出してもよい。
- 形C（T824、dm26rp3-018 キング・ザ・ベスト）: 攻撃時、下から3枚を
  表向きにし、条件に合う1体を出し、残りを好きな順序で上に置く。
- 形D（T825、dm32-019 サイバーX・ザナドゥ）: 離れた時、相手が自身の
  山札の一番下を表向きにし、進化ではないクリーチャーなら相手が出す。
- 形E（T826、一王二命三眼槍の敗北置換）: 相手のターンに負ける時、
  マナに闇と火があれば、手札のこのカードを山札の下に表向きで置く。

Rust: from_bottom は Rust 側セレクタの許可キー一覧に無いため、その選択は
Python フォールバックになる。敗北置換はもともと Rust の game_lose が
諮問を持たない（単純パス対象外）。新規 GameState フィールドなし。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card
from dmsim.engine.scenario import build

TABLES = load_tables()
IDS = ("T822", "T823", "T824", "T825", "T826", "T827", "T828")

GATE = {"any": [{"cmp": [{"count": {"zone": "shield", "owner": "you"}}, "==", 0]},
                {"cmp": [{"count": {"zone": "shield", "owner": "opp"}}, "==", 0]}]}

FORM_A = {"kind": "trigger",
          "when": {"event": "move", "to": "bz", "subject": "self"},
          "effect": [{"op": "move",
                      "select": {"zone": "deck", "owner": "you", "from_bottom": 1},
                      "to": "hand", "reason": "draw"}]}

FORM_B = {"kind": "trigger",
          "when": {"event": "move", "to": "bz", "subject": "self"},
          "if": GATE,
          "effect": [{"op": "move",
                      "select": {"zone": "deck", "owner": "you", "from_bottom": 1},
                      "to": "graveyard", "reason": "put", "as": "bot"},
                     {"op": "if",
                      "cond": {"exists": {"ref": "bot",
                                          "filter": {"types": ["creature"],
                                                     "cost_le": 5}}},
                      "then": [{"op": "may",
                                "body": [{"op": "play_free",
                                          "select": {"ref": "bot"}}]}]}]}

FORM_C = {"kind": "trigger",
          "when": {"event": "attack", "subject": "self"},
          "effect": [{"op": "choose",
                      "select": {"zone": "deck", "owner": "you", "from_bottom": 3,
                                 "look": True, "count": "all"},
                      "as": "pile", "reveal": True},
                     {"op": "play_free",
                      "select": {"ref": "pile",
                                 "filter": {"types": ["creature"],
                                            "races": ["ジョーカーズ"],
                                            "cost_le": 8},
                                 "count": 1, "up_to": True}},
                     {"op": "move",
                      "select": {"ref": "pile", "count": "all"},
                      "to": "deck", "position": "top", "order": "choose",
                      "reason": "put"}]}

FORM_D = {"kind": "trigger",
          "when": {"event": "move", "from": "bz", "subject": "self"},
          "effect": [{"op": "choose",
                      "select": {"zone": "deck", "owner": "opp", "from_bottom": 1,
                                 "look": True, "count": "all"},
                      "as": "pile", "reveal": True},
                     {"op": "play_free",
                      "select": {"ref": "pile",
                                 "filter": {"types": ["creature"],
                                            "evolution": False},
                                 "count": 1, "up_to": True, "chooser": "opp"},
                      "player": "opp"}]}

FORM_E_REPLACE = {"kind": "replace", "zone": "hand", "optional": True,
                  "when": {"event": "lose"},
                  "if": {"all": [{"is_turn": "opp"},
                                 {"exists": {"zone": "mana", "owner": "you",
                                             "filter": {"civs": ["darkness"]}}},
                                 {"exists": {"zone": "mana", "owner": "you",
                                             "filter": {"civs": ["fire"]}}}]},
                  "instead": [{"op": "move", "select": {"ref": "self"},
                               "to": "deck", "position": "bottom",
                               "face_up": True, "reason": "put"}]}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)
    assert parse_card(_proto_card("T822"), TABLES).abilities == [FORM_A]
    assert parse_card(_proto_card("T823"), TABLES).abilities == [FORM_B]
    assert parse_card(_proto_card("T824"), TABLES).abilities == [FORM_C]
    assert parse_card(_proto_card("T825"), TABLES).abilities == [FORM_D]
    d = parse_card(_proto_card("T826"), TABLES)
    reps = [a for a in d.abilities if a["kind"] == "replace"]
    trigs = [a for a in d.abilities if a["kind"] == "trigger"]
    assert reps == [FORM_E_REPLACE]
    assert trigs == [FORM_B]


def setup_exact(rules, p0, p1=None, filler="T002"):
    """山札の中身を spec の deck リストだけにする（deck_exact）。
    山札の並びは seed でシャッフルされるため、テストは実状態を読む。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": 1, "deck_size": 20,
                         "deck_exact": [True, True]})


def _deck(e, player=0):
    return list(e.s.zones["deck"][player])


def _defn(e, cid):
    return e.cdef(cid).id


def _zone_of(e, cid):
    return e.s.cards[cid].zone


def _drive(e, on_decision, limit=600):
    """汎用ドライバ。on_decision(e, d) の戻り値:
    "stop" = ここで止める / "ok" = ハンドラが回答済み / None = 汎用回答
    （チャージは pass、ブロックは no_block、その他は pass か最小限）。"""
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
            e.answer([keys.index("pass")])   # チャージはしない（pass も1つの選択肢）
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("driver limit reached")


def _stop_at(kind, player=None):
    def on_dec(e, d):
        if d["kind"] == kind and (player is None or d.get("player") == player):
            return "stop"
        return None
    return on_dec


def _play_and_pay(play_key, player=0, on_play=None):
    """main で play_key を実行し、pay_mana に答えるハンドラ部品。
    戻り値: (handler, played リスト)。on_play は実行直後に呼ばれる
    （ターン開始ドローを済ませた時点の状態を掴むため）。"""
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


# ---------- セレクタ: from_bottom の候補計算 ----------

def test_from_bottom_candidates(rules):
    e = setup_exact(rules, {"deck": ["T827", "T003", "T828", "T827", "T003"]},
                    {"deck": ["T827"] * 3})
    deck = _deck(e, 0)
    assert len(deck) == 5
    env = {"you": 0, "vars": {}}
    assert e.candidates({"zone": "deck", "owner": "you", "from_top": 2}, env) \
        == deck[:2]
    assert e.candidates({"zone": "deck", "owner": "you", "from_bottom": 2}, env) \
        == deck[-2:]
    assert e.candidates({"zone": "deck", "owner": "you", "from_bottom": 1}, env) \
        == deck[-1:]
    # 山札より大きい指定は全体を返す（from_top と同じ）
    assert e.candidates({"zone": "deck", "owner": "you", "from_bottom": 99}, env) \
        == deck
    # フィルタは「下から N 枚」の中だけで効く
    assert e.candidates({"zone": "deck", "owner": "you", "from_bottom": 2,
                         "filter": {"types": ["spell"]}}, env) \
        == [c for c in deck[-2:] if _defn(e, c) == "T003"]


# ---------- 形A: 一番下を手札に ----------

def test_form_a_bottom_to_hand(rules):
    e = setup_exact(rules, {"hand": ["T822"], "mana": ["T001"] * 3,
                            "deck": ["T827", "T003", "T828", "T827"]},
                    {"deck": ["T827"] * 3})
    snap = []
    handler, played = _play_and_pay(
        "play:T822", on_play=lambda e: snap.append(_deck(e, 0)))

    def on_dec(e, d):
        r = handler(e, d)
        if r:
            return r
        # 召喚したターンの攻撃ステップは決定を出さない（召喚酔い）ため、
        # 次の相手ターンのチャージ決定を観測点にする（自分の山札は動かない）
        if played and d["kind"] == "charge":
            return "stop"
        return None

    _drive(e, on_dec)
    deck0 = snap[0]                       # 召喚時点（ドロー後）の山札
    bottom, second = deck0[-1], deck0[-2]
    assert _zone_of(e, bottom) == "hand"          # 一番下が手札に来た
    assert _deck(e, 0) == deck0[:-1]              # 残りの並びは不変
    assert _deck(e, 0)[-1] == second


# ---------- 形B: 一番下を墓地に置き、出してもよい ----------

def _summon_and_watch(e, play_key, watch_kinds=("yes_no",)):
    """play_key の獣を召喚し、watch_kinds の決定が出たら ((kind, d), snap)
    を返す。出なければ (None, snap)。snap は召喚時点（ドロー後）の山札。"""
    seen = []
    snap = []
    handler, played = _play_and_pay(
        play_key, on_play=lambda e: snap.append(_deck(e, 0)))

    def on_dec(e, d):
        r = handler(e, d)
        if r:
            return r
        if d["kind"] in watch_kinds:
            seen.append((d["kind"], d))
            return "stop"
        if played and d["kind"] == "charge":
            return "stop"          # 次の相手ターンの開始 = 解決済みの観測点
        return None

    _drive(e, on_dec)
    return (seen[0] if seen else None), snap[0]


def test_form_b_plays_bottom_creature(rules):
    e = setup_exact(rules, {"hand": ["T823"],
                            "mana": ["T034", "T001", "T001", "T001"],
                            "shield": [], "deck": ["T827"] * 3},
                    {"deck": ["T827"] * 3})
    hit, snap = _summon_and_watch(e, "play:T823")
    bottom = snap[-1]
    assert hit is not None and hit[0] == "yes_no"   # 「出してもよい」の諮問
    e.answer([0])                                    # yes（第1選択肢）
    _drive(e, _stop_at("charge", player=1))
    card = e.s.cards[bottom]
    assert card.zone == "bz" and card.controller == 0
    assert _deck(e, 0) == snap[:-1]


def test_form_b_decline_keeps_it_in_graveyard(rules):
    e = setup_exact(rules, {"hand": ["T823"],
                            "mana": ["T034", "T001", "T001", "T001"],
                            "shield": [], "deck": ["T827"] * 3},
                    {"deck": ["T827"] * 3})
    hit, snap = _summon_and_watch(e, "play:T823")
    bottom = snap[-1]
    assert hit is not None and hit[0] == "yes_no"
    keys = [o["key"] for o in hit[1]["options"]]
    e.answer([keys.index("no")] if "no" in keys else [1])
    _drive(e, _stop_at("charge", player=1))
    assert _zone_of(e, bottom) == "graveyard"
    assert _deck(e, 0) == snap[:-1]


def test_form_b_too_expensive_stays_in_graveyard(rules):
    """コスト6は「コスト5以下」ではない: 墓地に置かれるだけで諮問は無い。"""
    e = setup_exact(rules, {"hand": ["T823"],
                            "mana": ["T034", "T001", "T001", "T001"],
                            "shield": [], "deck": ["T828"] * 3},
                    {"deck": ["T827"] * 3})
    hit, snap = _summon_and_watch(e, "play:T823")
    bottom = snap[-1]
    assert hit is None                               # yes_no は提示されない
    assert _zone_of(e, bottom) == "graveyard"
    assert _deck(e, 0) == snap[:-1]


def test_form_b_gate_needs_a_shieldless_player(rules):
    """両プレイヤーにシールドがあれば鬼エンドは発動しない（対照）。"""
    e = setup_exact(rules, {"hand": ["T823"],
                            "mana": ["T034", "T001", "T001", "T001"],
                            "deck": ["T827"] * 3},
                    {"deck": ["T827"] * 3})
    hit, snap = _summon_and_watch(e, "play:T823")
    bottom = snap[-1]
    assert hit is None
    assert _zone_of(e, bottom) == "deck"
    assert _deck(e, 0) == snap


# ---------- 形C: 下から3枚を公開し、1体出し、残りを上に ----------

def _attack_trigger_decisions(e, atk_key):
    """atk_key でプレイヤーを攻撃させ、誘発の最初の choose_cards /
    order_cards 決定で止めて (kind, d) を返す。"""
    seen = []
    attacked = []

    def on_dec(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and not attacked:
            if atk_key in keys:
                attacked.append(True)
                e.answer([keys.index(atk_key)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
            return "ok"
        if attacked and d["kind"] in ("choose_cards", "order_cards"):
            seen.append((d["kind"], d))
            return "stop"
        return None

    _drive(e, on_dec)
    assert seen, "trigger decision did not appear"
    return seen[0]


def test_form_c_plays_jokers_and_rest_on_top(rules):
    e = setup_exact(rules, {"bz": ["T824"], "deck": ["T828", "T003", "T827"]},
                    {"deck": ["T827"] * 3})
    kind, d = _attack_trigger_decisions(e, "attack:T824:player")
    assert kind == "choose_cards"
    # 出せるのは ジョーカーズ・コスト8以下だけ = T828 のみ
    assert [_defn(e, o["cid"]) for o in d["options"]] == ["T828"]
    e.answer([0])
    # 残り2枚の順序決定
    seen2 = []

    def on_dec2(e, d):
        if d["kind"] == "order_cards":
            seen2.append(d)
            return "stop"
        return None

    _drive(e, on_dec2)
    assert seen2, "order_cards decision expected"
    od = seen2[0]
    odefs = [_defn(e, o["cid"]) for o in od["options"]]
    assert sorted(odefs) == ["T003", "T827"]
    e.answer([1, 0])     # 提示順と逆に置く
    # 攻撃が完結し、次のターンのチャージ決定が来たら止める
    # （それまでは自分の山札は動かない）
    _drive(e, _stop_at("charge"))
    deck_defns = [_defn(e, c) for c in _deck(e, 0)]
    # 回答した順がそのまま上からの並びになる
    assert deck_defns == [odefs[1], odefs[0]]
    assert any(e.s.cards[c].defn == "T828" and e.s.cards[c].controller == 0
               for c in e.zlist("bz", 0))


def test_form_c_no_jokers_rest_all_on_top(rules):
    e = setup_exact(rules, {"bz": ["T824"], "deck": ["T827", "T003", "T827"]},
                    {"deck": ["T827"] * 3})
    before = [_defn(e, c) for c in _deck(e, 0)]
    kind, d = _attack_trigger_decisions(e, "attack:T824:player")
    # 出せるカードが無いので choose_cards は来ず、順序決定が先に来る
    assert kind == "order_cards"
    odefs = [_defn(e, o["cid"]) for o in d["options"]]
    assert odefs == before                      # 束は山札の並びどおり提示される
    e.answer([0, 1, 2])
    _drive(e, _stop_at("charge"))
    assert [_defn(e, c) for c in _deck(e, 0)] == before
    assert not any(e.s.cards[c].defn in ("T827", "T003")
                   for c in e.zlist("bz", 0) if e.cdef(c).id != "T824")


# ---------- 形D: 相手が自身の一番下を公開し、出してもよい ----------

def _destroy_825_scenario(e, opp_answer):
    """P1 が T056 で T825 を破壊する。相手（P1）の play_free 決定が
    来たら opp_answer(d) で答えて記録し、次の P0 のチャージ決定まで
    進めてから止める（play の解決が終わり、P1 の山札が次に動く前に
    観測するため）。戻り値: (play_free 決定 or None, 詠唱時点の P1 山札)。"""
    cast = []
    hit = []
    snap = []
    handler, _ = _play_and_pay(
        "play:T056", player=1, on_play=lambda e: snap.append(_deck(e, 1)))

    def on_dec(e, d):
        r = handler(e, d)
        if r:
            cast.append(True)
            return r
        if cast and d["kind"] == "choose_cards":
            tgt = [o for o in d["options"] if o.get("cid") is not None
                   and e.cdef(o["cid"]).id == "T825"]
            if tgt:      # 破壊対象の選択（使用者 P1 の決定）
                e.answer([d["options"].index(tgt[0])])
                return "ok"
            if d.get("player") == 1:   # 相手自身が出すかの選択
                hit.append(d)
                e.answer(opp_answer(d))
                return "ok"
        if cast and d["kind"] == "charge" and d.get("player") == 0:
            return "stop"          # 破壊と誘発の解決が終わった観測点
        return None

    _drive(e, on_dec)
    return (hit[0] if hit else None), snap[0]


def test_form_d_opponent_plays_own_bottom(rules):
    e = setup_exact(rules, {"bz": ["T825"], "deck": ["T827"] * 3},
                    {"hand": ["T056"], "mana": ["T082"] * 3,
                     "deck": ["T827"] * 3})
    hit, snap = _destroy_825_scenario(e, lambda d: [0])
    bottom = snap[-1]
    assert hit is not None
    card = e.s.cards[bottom]
    assert card.zone == "bz" and card.controller == 1   # 相手の獣として出る
    assert _deck(e, 1) == snap[:-1]
    assert any(e.s.cards[c].defn == "T825" for c in e.zlist("graveyard", 0))


def test_form_d_opponent_may_decline(rules):
    e = setup_exact(rules, {"bz": ["T825"], "deck": ["T827"] * 3},
                    {"hand": ["T056"], "mana": ["T082"] * 3,
                     "deck": ["T827"] * 3})
    hit, snap = _destroy_825_scenario(e, lambda d: [])
    bottom = snap[-1]
    assert hit is not None
    assert _zone_of(e, bottom) == "deck"
    assert _deck(e, 1) == snap


def test_form_d_spell_bottom_does_nothing(rules):
    e = setup_exact(rules, {"bz": ["T825"], "deck": ["T827"] * 3},
                    {"hand": ["T056"], "mana": ["T082"] * 3,
                     "deck": ["T003"] * 3})
    hit, snap = _destroy_825_scenario(e, lambda d: [0])
    assert hit is None                          # 呪文は出せないので諮問なし
    assert _deck(e, 1) == snap
    assert any(e.s.cards[c].defn == "T825" for c in e.zlist("graveyard", 0))


# ---------- 形E: 手札からの敗北置換 ----------

def _opp_direct_attack(e, on_lose):
    """P1 の T034 がシールド0の P0 を直接攻撃するドライバ。
    lose_replace 決定が来たら on_lose(e, d) で答える。"""
    attacked = []

    def on_dec(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "lose_replace":
            on_lose(e, d)
            return "stop"
        if d["kind"] == "attack" and d.get("player") == 1 and not attacked:
            if "attack:T034:player" in keys:
                attacked.append(True)
                e.answer([keys.index("attack:T034:player")])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
            return "ok"
        return None

    _drive(e, on_dec)


def test_form_e_hand_lose_replacement(rules):
    e = setup(rules, {"hand": ["T826"], "mana": ["T008", "T034"], "shield": []},
              {"bz": ["T034"], "mana": ["T001"] * 3}, filler="T002")
    t826 = next(c for c in e.zlist("hand", 0) if e.cdef(c).id == "T826")
    seen = []

    def on_lose(e, d):
        seen.append(d)
        keys = [o["key"] for o in d["options"]]
        assert any(k.startswith("lose_replace:T826") for k in keys)
        e.answer([next(i for i, k in enumerate(keys)
                       if k.startswith("lose_replace:T826"))])

    _opp_direct_attack(e, on_lose)
    assert seen, "lose_replace decision expected"
    # 置換の解決まで進める（敗北が無かったことになる）
    _drive(e, _stop_at("charge"))
    assert e.s.result is None                       # 敗北は置換された
    card = e.s.cards[t826]
    assert card.zone == "deck"
    assert _deck(e, 0)[-1] == t826                  # 山札の一番下
    # 「表向きにし」は置換の公開として扱う。山札内での表向き状態の保持は
    # _raw_move がゾーンの public 性で決める（山札は非公開）ため残らない。
    # これは deck_faceup 系（dm26rp2-s011）の領域で、本弾では扱わない。


def test_form_e_needs_darkness_and_fire_mana(rules):
    """火文明のマナが無ければ諮問自体が起きず、そのまま負ける（対照）。"""
    e = setup(rules, {"hand": ["T826"], "mana": ["T008", "T008"], "shield": []},
              {"bz": ["T034"], "mana": ["T001"] * 3}, filler="T002")
    seen = []
    _opp_direct_attack(e, lambda e, d: seen.append(d))
    assert not seen
    assert e.s.result is not None and e.s.result["winner"] == 1


def test_form_e_decline_loses(rules):
    e = setup(rules, {"hand": ["T826"], "mana": ["T008", "T034"], "shield": []},
              {"bz": ["T034"], "mana": ["T001"] * 3}, filler="T002")

    def on_lose(e, d):
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("decline")])

    _opp_direct_attack(e, on_lose)
    _drive(e, lambda e, d: None)        # decline の処理で敗北が確定するまで
    assert e.s.result is not None and e.s.result["winner"] == 1


def test_form_e_not_during_own_turn(rules):
    """自分のターンの山札切れでは is_turn: opp が満たされず諮問なし。"""
    e = setup_exact(rules, {"hand": ["T826"], "mana": ["T008", "T034"],
                            "deck": ["T827"]},
                    {"deck": ["T827"] * 5})
    seen = []

    def on_dec(e, d):
        if d["kind"] == "lose_replace":
            seen.append(d)
            e.answer([0])
            return "stop"
        return None

    _drive(e, on_dec)
    assert not seen
    assert e.s.result is not None and e.s.result["winner"] == 1
    t826 = next(c for c in e.zlist("hand", 0) if e.cdef(c).id == "T826")
    assert _zone_of(e, t826) == "hand"
