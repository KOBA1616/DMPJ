"""語彙パイロット第318弾: 「ただし、その『S・トリガー』は使えない」
（shield_to_hand_strigger_deny）。

センサス（rejects 2,059件）: 純粋ファミリーの大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone 105 /
dragheart 45 / psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 / pandora_shift 4）
か評価済み DEEP・重い・延期。範囲内・未評価で最小の
shield_to_hand_strigger_deny（純粋2件）を選定した:
dmrp22-031 エメラルの海幻 / dm24ex3-or1 超天使 ゴルドラン・
ゴルギーニ。両行とも partial は完成済みで、未解決は
「効果で自分のシールドを手札に加える時、その『S・トリガー』は
使えない」の1節のみ。

結論はドリフト（追加語彙なし）: 第296弾の形A＝move 引数
strigger: "off"（S・トリガーの印）がそのまま効く。効果の
shield→hand 移動は break タスク（phase 1・fire_break: False）
へ回り、印のある束は宣言諮問の肢から消える（第296弾で CIP の
素の move 形、ラウンド331で変換済みエメラル2件の修繕形を
実挙動で固定済み）。本弾は対象2行の形で再検証する:

- 形A1（dmrp22-031）: シールド化（hand→shield）の直後に、
  改めて選んだシールドを手札に戻す連続形。戻す move は
  as 束縛でなく素の zone 選択で、ゲート（may/if）も無い。
- 形A2（dm24ex3-or1）: 選んだシールド束を表向きにし、
  bundle_of＋filter で分割する形（クリーチャーは場へ、
  残りは手札へ）。印は ref＋filter 経由の分割 move でも
  効かなければならない。

プロト T975（形A1）/ T976（形A1の対照: 印なし）/
T977（形A2）/ T978（形A2の対照: 印なし）。シールド役は
既存 T960（光・S・トリガー呪文）と T001（クリーチャー）。
"""
import copy

from dmsim.cards.defs import load_tables, parse_card
from tests.conftest import setup

TABLES = load_tables()

CIP_DRAW = {"kind": "trigger",
            "when": {"event": "move", "to": "bz", "subject": "self"},
            "effect": [{"op": "draw", "count": 1}]}
SHIELDIZE = {"op": "move",
             "select": {"zone": "hand", "owner": "you", "count": 1},
             "to": "shield", "reason": "charge"}
RETURN_OFF = {"op": "move",
              "select": {"zone": "shield", "owner": "you", "count": 1},
              "to": "hand", "reason": "put", "strigger": "off"}
RETURN_PLAIN = {"op": "move",
                "select": {"zone": "shield", "owner": "you", "count": 1},
                "to": "hand", "reason": "put"}
FORM_A1 = {"kind": "trigger",
           "when": {"event": "evolve_base", "subject": "self"},
           "effect": [SHIELDIZE, RETURN_OFF]}
FORM_A1_CONTROL = {"kind": "trigger",
                   "when": {"event": "evolve_base", "subject": "self"},
                   "effect": [SHIELDIZE, RETURN_PLAIN]}

CIP_NO_LEAVE = {"kind": "trigger",
                "when": {"event": "move", "to": "bz", "subject": "self"},
                "effect": [{"op": "modify", "select": {"ref": "self"},
                            "mod": {"no_leave": True},
                            "duration": "until_next_own_turn_start"}]}


def _attack_trigger(hand_move):
    return {"kind": "trigger",
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
                 "cond": {"cmp": [{"count": {"zone": "shield",
                                             "owner": "you"}},
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
                     hand_move]}]}


HAND_OFF = {"op": "move",
            "select": {"ref": "fc",
                       "filter": {"not_types": ["creature"]},
                       "count": "all"},
            "to": "hand", "reason": "put", "strigger": "off"}
HAND_PLAIN = {"op": "move",
              "select": {"ref": "fc",
                         "filter": {"not_types": ["creature"]},
                         "count": "all"},
              "to": "hand", "reason": "put"}

EXPECTED = {
    "T975": [CIP_DRAW, FORM_A1],
    "T976": [CIP_DRAW, FORM_A1_CONTROL],
    "T977": [CIP_NO_LEAVE, _attack_trigger(HAND_OFF)],
    "T978": [CIP_NO_LEAVE, _attack_trigger(HAND_PLAIN)],
}


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _drive_a1(e, base_defn, pick_cid):
    """T077 を base_defn の上に進化させ、evolve_base 誘発の
    シールド化（手札は T001 を選ぶ）→戻し（pick_cid を選ぶ）
    まで進める。現れた Decision の kind 列を返す。"""
    seen = []
    played = False
    for _ in range(600):
        if pick_cid in e.zlist("hand", 0) and _quiet(e):
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
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "choose_evo_source":
            hit = [i for i, k in enumerate(keys)
                   if k.startswith(f"bz:{base_defn}")]
            e.answer([hit[0]] if hit else [0])
        elif kind == "choose_cards":
            hit = [i for i, o in enumerate(d["options"])
                   if o["cid"] == pick_cid]
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
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return seen


def _drive_a2(e, attacker_defn, pick_cids):
    """attacker_defn でプレイヤーを攻撃し、攻撃誘発の
    シールド選択で pick_cids を選び、ブレイクまで進める。
    現れた Decision の kind 列を返す。"""
    seen = []
    attacked = False
    for _ in range(800):
        if pick_cids[0] in e.zlist("hand", 0) and _quiet(e):
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
                   if k == f"attack:{attacker_defn}:player"]
            if hit and not attacked:
                attacked = True
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind in ("charge", "main"):
            e.answer([keys.index("pass")] if "pass" in keys
                     else list(range(d.get("min", 0))))
        elif kind == "yes_no":
            e.answer([keys.index("yes")])   # シールド化する
        elif kind == "choose_cards":
            hit = [i for i, o in enumerate(d["options"])
                   if o["cid"] in pick_cids]
            if hit:
                e.answer(hit)
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "choose_shields":
            e.answer(list(range(d["min"])))
        elif kind == "block":
            e.answer([keys.index("no_block")] if "no_block" in keys
                     else list(range(d.get("min", 0))))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return seen


# ---------- parse / validation ----------

def test_pilot318_protos_parse(rules):
    for cid, wants in EXPECTED.items():
        d = rules.cards[cid]
        for want in wants:
            assert want in d.abilities, cid


def test_pilot318_forms_raw_parse():
    for ab in (FORM_A1, _attack_trigger(HAND_OFF)):
        d = parse_card({"id": "TX318", "name": "x", "types": ["creature"],
                        "civs": ["light"], "cost": 4, "power": 4000,
                        "abilities": [copy.deepcopy(ab)]}, TABLES)
        assert ab in d.abilities


# ---------- 実挙動: 形A1（シールド化→戻しの連続形） ----------

def _setup_a1(rules, proto):
    e = setup(rules,
              {"bz": [proto], "hand": ["T077", "T001", "T002"],
               "mana": ["T010", "T001", "T001"],
               "shield": ["T960", "T001", "T001", "T001", "T001"]}, {})
    t960 = next(c for c in e.zlist("shield", 0)
                if e.cdef(c).id == "T960")
    return e, t960


def test_form_a1_return_suppresses_strigger(rules):
    """T975 のシンカパワーで手札に加えたシールド（T960）は
    宣言できない。"""
    e, t960 = _setup_a1(rules, "T975")
    seen = _drive_a1(e, "T975", t960)
    assert "T960" in _defns(e, "hand", 0)
    assert "declare_strigger" not in seen
    assert e.s.cards[t960].strigger_off is True     # 印が付いている
    assert len(e.zlist("shield", 0)) == 5           # 化1＋戻し1で不変
    top = next(c for c in e.bz_tops(0) if e.cdef(c).id == "T077")
    assert e.s.cards[e.s.cards[top].under[0]].defn == "T975"


def test_form_a1_control_offers_strigger(rules):
    """対照 T976（印なし）では同じ戻しでも宣言の機会がある。"""
    e, t960 = _setup_a1(rules, "T976")
    seen = _drive_a1(e, "T976", t960)
    assert "T960" in _defns(e, "hand", 0)
    assert "declare_strigger" in seen
    assert e.s.cards[t960].strigger_off is False


# ---------- 実挙動: 形A2（束の分割形） ----------

def _setup_a2(rules, proto):
    e = setup(rules,
              {"bz": [proto],
               "shield": ["T960", "T001"] + ["T002"] * 8},
              {"shield": ["T001"] * 5})
    t960 = next(c for c in e.zlist("shield", 0)
                if e.cdef(c).id == "T960")
    t001 = next(c for c in e.zlist("shield", 0)
                if e.cdef(c).id == "T001")
    return e, t960, t001


def test_form_a2_split_suppresses_strigger(rules):
    """T977 の攻撃誘発で表向きにした束: クリーチャー（T001）は
    場へ、呪文（T960）は手札へ。T960 は宣言できない。"""
    e, t960, t001 = _setup_a2(rules, "T977")
    seen = _drive_a2(e, "T977", [t960, t001])
    assert "T960" in _defns(e, "hand", 0)
    assert t001 in e.bz_tops(0)                     # 選んだ獣は場へ
    assert "declare_strigger" not in seen
    assert e.s.cards[t960].strigger_off is True     # 印が付いている


def test_form_a2_control_offers_strigger(rules):
    """対照 T978（印なし）では T960 の宣言の機会がある。"""
    e, t960, t001 = _setup_a2(rules, "T978")
    seen = _drive_a2(e, "T978", [t960, t001])
    assert "T960" in _defns(e, "hand", 0)
    assert t001 in e.bz_tops(0)
    assert "declare_strigger" in seen
    assert e.s.cards[t960].strigger_off is False
