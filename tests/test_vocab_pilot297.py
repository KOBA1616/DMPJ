"""語彙パイロット第297弾: 「ブレイクしたシールドは墓地に置く」
（break_replacement_graveyard / break_to_graveyard / shield_break_to_graveyard）。

3つのギャップ名に分かれた同一条項「このクリーチャーがシールドを
ブレイクする時、相手はそのシールドを手札に加えるかわりに墓地に置く」
の純粋6件（dm25ex2-018 / dmr04-018 / dm26ex4-002 /
dm26sd1-g005 / dmex17-w06 / dm24bd6-037）。不足は無く、ギャップ名と
語彙名のドリフトだった（新規 op・面フィールド・GameState フィールド
なし＝ state.rs 変更なし、スキーマ再生成なし）。

機構は既存: ブレイクの置換諮問 _break_consult（第146弾）が、割る
シールド1枚ずつ chosen 確定後・S・トリガー宣言の前に置換を諮り、
レコード {ev: break, subject: ブレイクしたクリーチャー, shield: その
シールド, player: victim} で照合する。登録済み先例が6件以上ある形:

  {kind: replace, when: {event: break, subject: self},
   instead: [{op: move, select: {ref: event.shield, count: 1},
              to: graveyard, reason: put}]}

（dm24ex2-chog06 / dm24ex2-014 / dm25ex2-014 / dmrp18-s07 /
dm24ex2-dm04 / dmex15-a027。条件つき変形は promoy8-002 の if 形。）
置換されたシールドは「ブレイクされた」ことにならない（QA 33466 の
設計判断、第146弾）: chosen から外れ、break_before も S・トリガー
宣言も S・バックも起こらず、ブレイク枚数にも数えない。任意でない
置換は諮問の決定自体が出ない（候補1件・辞退肢なし）。

形は3つ:
- 形A（無条件、4件）: 上記の先例形そのまま。
- 形B（相手の手札0枚、dmr04-018）: 形A ＋
  if {cmp: [{count: {zone: hand, owner: opp}}, "==", 0]}。
  if は諮問時点（割る前）で評価される。
- 形C（水晶武装4、dm24bd6-037）: 形A ＋
  if {cmp: [{count: {zone: mana, owner: you,
              filter: {face_down: true}}}, ">=", 4]}。
  count＋face_down フィルタの形は第283弾 eternal_kappa の if ゲートと同形。

プロト T895（形A）/ T896（形Aの対照: 置換なし）/ T897（形B）/
T898（形C）。シールド役は既存プロト T279（闇・S・トリガー持ち）と
T207（光・同）を使う。なお dm26ex4-sec005 / dm26ex4-025 は同じ条項を
break_replacement_by_breaker の名で持ち、残りギャップ
enter_bz_summon_only が別にあるため本弾では解放されない（形は同じ。
ラウンド332で partial に銀行できる）。
"""
import copy

import pytest

from dmsim.cards.defs import DefError, load_tables, parse_card
from tests.conftest import setup

TABLES = load_tables()

INSTEAD = [{"op": "move", "select": {"ref": "event.shield", "count": 1},
            "to": "graveyard", "reason": "put"}]
FORM_A = {"kind": "replace", "when": {"event": "break", "subject": "self"},
          "instead": copy.deepcopy(INSTEAD)}
FORM_B = {"kind": "replace", "when": {"event": "break", "subject": "self"},
          "if": {"cmp": [{"count": {"zone": "hand", "owner": "opp"}}, "==", 0]},
          "instead": copy.deepcopy(INSTEAD)}
FORM_C = {"kind": "replace", "when": {"event": "break", "subject": "self"},
          "if": {"cmp": [{"count": {"zone": "mana", "owner": "you",
                                    "filter": {"face_down": True}}}, ">=", 4]},
          "instead": copy.deepcopy(INSTEAD)}

EXPECTED = {"T895": FORM_A, "T897": FORM_B, "T898": FORM_C}


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _attack_out(e, attacker, targets, stop, limit=500):
    """attacker でプレイヤーを攻撃し、targets を優先して2枚割り、
    stop(e) が真になるまで進める。現れた Decision の kind 列を返す。"""
    seen = []
    for _ in range(limit):
        if stop(e):
            return seen
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        seen.append(kind)
        keys = [o["key"] for o in d["options"]]
        if kind in ("charge", "main"):
            e.answer([keys.index("pass")])
        elif kind == "attack":
            hit = [i for i, k in enumerate(keys) if k == f"attack:{attacker}:player"]
            if not hit:
                e.answer([keys.index("pass")])
                break
            e.answer([hit[0]])
        elif kind == "choose_breaker":
            if "breaks:2" in keys:
                e.answer([keys.index("breaks:2")])
            else:
                e.answer([max(range(len(keys)),
                              key=lambda i: int(keys[i].split(":")[1]))])
        elif kind == "choose_shields":
            n = d["min"]
            hit = [i for i, o in enumerate(d["options"])
                   if e.cdef(o["cid"]).id in targets]
            rest = [i for i in range(len(d["options"])) if i not in hit]
            e.answer((hit + rest)[:n])
        elif kind == "choose_replacement":
            e.answer([0])
        elif kind in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif kind == "yes_no":
            e.answer([keys.index("yes")])
        elif kind == "block":
            e.answer([keys.index("no_block")] if "no_block" in keys
                     else list(range(d.get("min", 0))))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("limit reached")


# ---------- parse / validation ----------

def test_pilot297_protos_parse(rules):
    for cid, want in EXPECTED.items():
        d = rules.cards[cid]
        assert want in d.abilities, cid
    d = rules.cards["T896"]
    assert not [a for a in d.abilities if a.get("kind") == "replace"]


def test_pilot297_forms_raw_parse():
    for form in (FORM_A, FORM_B, FORM_C):
        d = parse_card({"id": "TX297", "name": "x", "types": ["creature"],
                        "civs": ["fire"], "cost": 5, "power": 5000,
                        "abilities": [copy.deepcopy(form)]}, TABLES)
        assert form in d.abilities


def test_pilot297_validation():
    # instead の未知 op は拒否される
    bad = copy.deepcopy(FORM_A)
    bad["instead"] = [{"op": "move_shield_to_grave", "select": {"ref": "event.shield"}}]
    with pytest.raises(DefError):
        parse_card({"id": "TX297", "name": "x", "types": ["creature"],
                    "civs": ["fire"], "cost": 5, "power": 5000,
                    "abilities": [bad]}, TABLES)
    # if の count セレクタの未知キーは拒否される
    bad2 = copy.deepcopy(FORM_B)
    bad2["if"] = {"cmp": [{"count": {"zone": "hand", "owner": "opp",
                                     "bogus": 1}}, "==", 0]}
    with pytest.raises(DefError):
        parse_card({"id": "TX297", "name": "x", "types": ["creature"],
                    "civs": ["fire"], "cost": 5, "power": 5000,
                    "abilities": [bad2]}, TABLES)


# ---------- 実挙動: 形A（無条件） ----------

def test_form_a_two_shields_to_graveyard(rules):
    """T895 が W・ブレイカーで2枚割ると、2枚とも墓地に置かれ、
    S・トリガー宣言も置換諮問の決定も出ない。"""
    e = setup(rules, {"bz": ["T895"]},
              {"shield": ["T279", "T207", "T001", "T001", "T001"]})
    seen = _attack_out(e, "T895", {"T279", "T207"},
                       lambda ev: "T279" in _defns(ev, "graveyard", 1)
                       and "T207" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T279" in _defns(e, "graveyard", 1)
    assert "T207" in _defns(e, "graveyard", 1)
    assert "T279" not in _defns(e, "hand", 1)
    assert "T207" not in _defns(e, "hand", 1)
    assert len(_defns(e, "shield", 1)) == 3
    assert "declare_strigger" not in seen
    assert "choose_replacement" not in seen   # 任意でない置換は決定が出ない


def test_form_a_control_shields_to_hand(rules):
    """対照 T896（置換なし）: 割ったシールドは手札に加わり、宣言できる。"""
    e = setup(rules, {"bz": ["T896"]},
              {"shield": ["T279", "T207", "T001", "T001", "T001"]})
    seen = _attack_out(e, "T896", {"T279", "T207"},
                       lambda ev: "T279" in _defns(ev, "hand", 1)
                       and "T207" in _defns(ev, "hand", 1) and _quiet(ev))
    assert "T279" in _defns(e, "hand", 1)
    assert "T207" in _defns(e, "hand", 1)
    assert "declare_strigger" in seen
    assert not _defns(e, "graveyard", 1)


def test_form_a_bundle_under_follows_to_graveyard(rules):
    """束の下のカードは、上のカードと一緒に墓地へ動く
    （_shield_plus_tuck と同じ作法で束を作って固定。先例6件と同一挙動）。"""
    e = setup(rules, {"bz": ["T895"]},
              {"shield": ["T279", "T001", "T001", "T001", "T001"]})
    s = e.s
    top = next(c for c in e.zlist("shield", 1) if e.cdef(c).id == "T279")
    tucked = s.zones["deck"][1][0]
    e._raw_move(tucked, "shield")
    lst = e.mut_zlist("shield", 1)
    if tucked in lst:
        lst.remove(tucked)
    s.mut_card(top).under.append(tucked)
    s.mut_card(tucked).top_of = top
    seen = _attack_out(e, "T895", {"T279"},
                       lambda ev: "T279" in _defns(ev, "graveyard", 1)
                       and _quiet(ev))
    assert s.cards[top].zone == "graveyard"
    assert s.cards[tucked].zone == "graveyard"   # 下のカードも一緒に墓地へ
    assert "declare_strigger" not in seen


# ---------- 実挙動: 形B（相手の手札0枚） ----------

def test_form_b_empty_hand_to_graveyard(rules):
    """相手の手札が0枚なら、割ったシールドは墓地に置かれる。"""
    e = setup(rules, {"bz": ["T897"]},
              {"shield": ["T279", "T001", "T001", "T001", "T001"]})
    seen = _attack_out(e, "T897", {"T279"},
                       lambda ev: "T279" in _defns(ev, "graveyard", 1)
                       and _quiet(ev))
    assert "T279" in _defns(e, "graveyard", 1)
    assert "T279" not in _defns(e, "hand", 1)
    assert "declare_strigger" not in seen


def test_form_b_with_hand_to_hand(rules):
    """相手の手札が1枚でもあれば条件不成立で、通常どおり手札に加わる。"""
    e = setup(rules, {"bz": ["T897"]},
              {"hand": ["T001"],
               "shield": ["T279", "T001", "T001", "T001", "T001"]})
    seen = _attack_out(e, "T897", {"T279"},
                       lambda ev: "T279" in _defns(ev, "hand", 1)
                       and _quiet(ev))
    assert "T279" in _defns(e, "hand", 1)
    assert "T279" not in _defns(e, "graveyard", 1)
    assert "declare_strigger" in seen


# ---------- 実挙動: 形C（水晶武装4） ----------

def _flip_mana(e, n):
    for c in e.zlist("mana", 0)[:n]:
        e.s.cards[c].face_down = True


def test_form_c_four_face_down_to_graveyard(rules):
    """裏向きマナが4枚以上あれば、割ったシールドは墓地に置かれる。"""
    e = setup(rules, {"bz": ["T898"], "mana": ["T001"] * 5},
              {"shield": ["T279", "T001", "T001", "T001", "T001"]})
    _flip_mana(e, 4)
    seen = _attack_out(e, "T898", {"T279"},
                       lambda ev: "T279" in _defns(ev, "graveyard", 1)
                       and _quiet(ev))
    assert "T279" in _defns(e, "graveyard", 1)
    assert "T279" not in _defns(e, "hand", 1)
    assert "declare_strigger" not in seen


def test_form_c_three_face_down_to_hand(rules):
    """裏向きマナが3枚では条件不成立で、通常どおり手札に加わる。"""
    e = setup(rules, {"bz": ["T898"], "mana": ["T001"] * 5},
              {"shield": ["T279", "T001", "T001", "T001", "T001"]})
    _flip_mana(e, 3)
    seen = _attack_out(e, "T898", {"T279"},
                       lambda ev: "T279" in _defns(ev, "hand", 1)
                       and _quiet(ev))
    assert "T279" in _defns(e, "hand", 1)
    assert "T279" not in _defns(e, "graveyard", 1)
    assert "declare_strigger" in seen
