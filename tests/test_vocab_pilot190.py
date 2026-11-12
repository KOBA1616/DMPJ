"""語彙パイロット第190弾（2026-11-12）の検証。

EXライフの残り節（本体のシールド化・離脱置換は実装済み）。
- 新語彙1点: when.subject {exlife_of: self}（「このクリーチャーの『EXライフ』シールドが
  離れた時」の誘発）。移動レコードの lki に exlife_of を載せ、_subject_match が
  移動前の紐付けで照合する（離れた後では紐付けは消えているため lki が要る）。
- 既存語彙の組合せ: シールド1つにつきパワー+1000 (power {amount, count})、
  多色でない呪文の効果で選ばれない (deny be_chosen + other filter)、
  相手クリーチャーの能力をすべて無視 (modify ignore [all] + dynamic)、
  文明1つにつきコスト-1 (cost {amount: -1, count: {civ_count: {ref: self}}})。
"""
from pathlib import Path

import yaml
from conftest import setup

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()
PROTOS = ("T461", "T462", "T463", "T464")


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _cid(e, player, defn):
    """bz は共有ゾーンなので、コントローラーまで見て対象側のカードを取る。"""
    return next(c for c in e.zlist("bz", player) if e.s.cards[c].defn == defn)


def _exlife_shield(e, player):
    return next(c for c in e.zlist("shield", player)
                if e.s.cards[c].exlife_of is not None)


def _play(e, tid, yes_no=("yes",), max_steps=400):
    """手札から tid を出す。yes_no は yes_no 決定への回答の列（尽きたら yes）。
    出した側の攻撃決定で止める。戻り値は出た決定種別の回数。"""
    yes_no = list(yes_no)
    played = False
    seen = {"yes_no": 0, "choose_cards": 0}
    for _ in range(max_steps):
        d = e.advance()
        if d is None:
            return seen
        keys = [o["key"] for o in d["options"]]
        play_keys = [k for k in keys
                     if k == f"play:{tid}" or k.startswith(f"play:{tid}:")]
        if d["kind"] == "main" and not played and play_keys:
            played = True
            e.answer([keys.index(play_keys[0])])
            continue
        if played and (d["kind"] in ("main", "attack") or d["player"] != 0):
            return seen
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_cards":
            seen["choose_cards"] += 1
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            seen["yes_no"] += 1
            a = yes_no.pop(0) if yes_no else "yes"
            e.answer([keys.index(a)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("play did not finish")


def _drive(e, plan, limit=300):
    """plan: {決定種別: [回答の列, ...]}。回答はキーの列か添字の列。
    main/attack（自プレイヤー）で止める。戻り値は出た決定種別の回数。"""
    plan = {k: list(v) for k, v in plan.items()}
    seen = {}
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return seen
        seen[d["kind"]] = seen.get(d["kind"], 0) + 1
        if d["kind"] in ("main", "attack", "charge") and not any(plan.values()):
            return seen
        keys = [o["key"] for o in d["options"]]
        queue = plan.get(d["kind"])
        if queue:
            want = queue.pop(0)
            ans = [keys.index(w) if isinstance(w, str) else w for w in want]
            e.answer(sorted(set(ans)))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("drive did not finish")


def test_parse_protos():
    for cid in PROTOS:
        parse_card(_proto_card(cid), TABLES)


def test_t461_tap_triggers(rules):
    """T461: 攻撃宣言でタップ → 誘発。マナ/墓地から1枚手札へ＋相手は1枚捨てる。"""
    e = setup(rules, {"hand": ["T461"], "mana": ["T460"] * 6,
                      "graveyard": ["T001"]},
              {"hand": ["T001", "T001"], "bz": ["T001"]})
    _play(e, "T461")
    assert e.s.cards[_exlife_shield(e, 0)].exlife_of is not None
    target = _cid(e, 1, "T001")
    e.s.cards[target].tapped = True   # 505.2: 攻撃できるのはタップ状態のクリーチャーだけ
    seen = _drive(e, {"attack": [["attack:T461:T001"]],
                      "yes_no": [["yes"]],
                      "choose_cards": [[0], [0]]})
    assert seen.get("yes_no", 0) == 1
    assert len(e.zlist("hand", 0)) == 2          # ターン開始ドロー1枚＋戻した1枚
    assert len(e.zlist("hand", 1)) == 3          # 2＋相手ターン1ドロー1－捨て1＋相手ターン2ドロー1
    assert len(e.zlist("graveyard", 1)) == 2     # 捨てた1枚＋バトルで死んだ T001
    assert e.s.cards[_cid(e, 0, "T461")].zone == "bz"
    assert "T001" in [e.s.cards[c].defn for c in e.zlist("graveyard", 1)]


def test_t461_exlife_shield_leave_triggers(rules):
    """T461: EXライフシールドが墓地へ離れる → 誘発する。"""
    e = setup(rules, {"hand": ["T461", "T001"], "mana": ["T460"] * 6,
                      "graveyard": ["T001"]},
              {"hand": ["T001", "T001"]})
    _play(e, "T461")
    ex = _exlife_shield(e, 0)
    e._push(e.ev_task({"ev": "move", "subject": e.s.ref(ex),
                       "to": "graveyard", "reason": "put"}))
    seen = _drive(e, {"yes_no": [["yes"]], "choose_cards": [[0], [0]]})
    assert seen.get("yes_no", 0) == 1
    assert len(e.zlist("hand", 0)) == 2
    assert len(e.zlist("hand", 1)) == 2          # 2＋相手ターン1ドロー1－捨て1


def test_t461_normal_shield_leave_does_not_trigger(rules):
    """T461: EXライフでない普通のシールドが離れても誘発しない（判別）。"""
    e = setup(rules, {"hand": ["T461", "T001"], "mana": ["T460"] * 6,
                      "graveyard": ["T001"]},
              {"hand": ["T001", "T001"]})
    _play(e, "T461")
    normal = next(c for c in e.zlist("shield", 0)
                  if e.s.cards[c].exlife_of is None)
    e._push(e.ev_task({"ev": "move", "subject": e.s.ref(normal),
                       "to": "graveyard", "reason": "put"}))
    # charge を1回消費してからでないと、待機中の決定に先に止まって ev_task が走らない
    seen = _drive(e, {"charge": [["pass"]]})
    assert seen.get("yes_no", 0) == 0
    assert len(e.zlist("hand", 0)) == 1
    assert len(e.zlist("hand", 1)) == 3          # 2＋相手ターン1ドロー1（捨て無し）


def test_t462_exlife_shield_leave_destroys(rules):
    """T462: EXライフシールドが離れる → 相手クリーチャー1体破壊。"""
    e = setup(rules, {"hand": ["T462", "T001"], "mana": ["T460"] * 6},
              {"bz": ["T001"]})
    _play(e, "T462")
    ex = _exlife_shield(e, 0)
    e._push(e.ev_task({"ev": "move", "subject": e.s.ref(ex),
                       "to": "graveyard", "reason": "put"}))
    seen = _drive(e, {"choose_cards": [[0]]})
    assert seen.get("choose_cards", 0) == 1
    assert "T001" in [e.s.cards[c].defn for c in e.zlist("graveyard", 1)]


def test_t462_chosen_protection_scoped(rules):
    """T462: 単色呪文の効果では選ばれない（解決カードが呪文の時だけ）。
    クリーチャー由来の選択では選べる（判別）。"""
    e = setup(rules, {"bz": ["T462", "T001", "T002"]},
              {"bz": ["T001"], "hand": ["T003"]})
    mine = _cid(e, 0, "T462")
    other = _cid(e, 0, "T001")
    # 単色呪文（水 T003）を解決カードとして destroy を選ばせる
    t003 = next(c for c in e.zlist("hand", 1) if e.s.cards[c].defn == "T003")
    ops = [{"op": "move",
            "select": {"zone": "bz", "owner": "opp",
                       "filter": {"types": ["creature"]}, "count": 1},
            "to": "graveyard", "reason": "destroy"}]
    e.s.tasks.append(e._child(ops, {"you": 1, "self": e.s.ref(t003), "vars": {}}))
    d = e.advance()
    assert d is not None and d["kind"] == "choose_cards", d
    keys = [o["key"] for o in d["options"]]
    assert not any("T462" in k for k in keys), keys
    assert any("T001" in k for k in keys), keys
    e.answer([keys.index(next(k for k in keys if "T001" in k))])
    e.advance()
    assert e.s.cards[mine].zone == "bz"
    assert e.s.cards[other].zone == "graveyard"
    # 判別: クリーチャー由来なら T462 も選べる
    e2 = setup(rules, {"bz": ["T462", "T001", "T002"]}, {"bz": ["T001"]})
    mine2 = _cid(e2, 0, "T462")
    src = next(c for c in e2.zlist("bz", 1) if e2.s.cards[c].defn == "T001")
    e2.s.tasks.append(e2._child(ops, {"you": 1, "self": e2.s.ref(src), "vars": {}}))
    d = e2.advance()
    assert d is not None and d["kind"] == "choose_cards", d
    keys = [o["key"] for o in d["options"]]
    assert any("T462" in k for k in keys), keys


def test_t463_power_per_shield_and_cip(rules):
    """T463: シールド1つにつき+1000（5+EXライフ1=6枚で+6000）。
    CIPで相手クリーチャーを山札の下へ。"""
    e = setup(rules, {"hand": ["T463"], "mana": ["T460"] * 6},
              {"bz": ["T001"]})
    _play(e, "T463")
    assert e.s.cards[_cid(e, 1, "T001")].zone == "bz"   # CIP は辞退（既定で min=0）
    me = _cid(e, 0, "T463")
    assert e.chars(me)["power"] == 6000 + 1000 * 6
    # CIP を選ぶ版: もう一度、選んで下へ送る
    e2 = setup(rules, {"hand": ["T463"], "mana": ["T460"] * 6},
               {"bz": ["T001"]})
    target2 = _cid(e2, 1, "T001")
    _drive(e2, {"main": [["play:T463"]], "choose_cards": [[0]]})
    assert e2.s.cards[target2].zone == "deck"
    assert e2.zlist("deck", 1)[-1] == target2


def test_t463_attack_trigger_shieldize(rules):
    """T463: 攻撃時、山札上2枚を見て1枚シールド化・もう1枚手札へ。"""
    e = setup(rules, {"hand": ["T463"], "mana": ["T460"] * 6},
              {"bz": ["T001"]})
    _play(e, "T463")
    shields_before = len(e.zlist("shield", 0))
    deck_before = len(e.zlist("deck", 0))
    target = _cid(e, 1, "T001")
    e.s.cards[target].tapped = True   # 505.2: 攻撃できるのはタップ状態のクリーチャーだけ
    seen = _drive(e, {"attack": [["attack:T463:T001"]],
                      "yes_no": [["yes"]],
                      "choose_cards": [[0]]})
    assert seen.get("yes_no", 0) == 1
    assert len(e.zlist("shield", 0)) == shields_before + 1
    assert len(e.zlist("deck", 0)) == deck_before - 3   # ターン開始ドロー1＋めくった2
    assert len(e.zlist("hand", 0)) == 2   # ターン開始ドロー1＋手札へ1
    assert e.s.cards[_cid(e, 0, "T463")].zone == "bz"


def test_t464_ignore_and_opp_summon_trigger(rules):
    """T464: CIPで相手クリーチャーの能力を無視（T002のCIPが働かない）。
    相手ターンに相手がコスト9以下を召喚 → 1ドロー＋手札の呪文を無料で唱える。
    無視は次の自分のターンのはじめまでなので、T002 は相手ターン1に召喚する。"""
    e = setup(rules, {"hand": ["T464", "T003"], "mana": ["T460"] * 6},
              {"hand": ["T002"], "mana": ["T001", "T001"]})
    _play(e, "T464")
    seen = _drive(e, {"main": [["play:T002"]],
                      "yes_no": [["yes"], ["yes"]],
                      "choose_cards": [[0]]})
    assert seen.get("yes_no", 0) == 2
    assert len(e.zlist("mana", 1)) == 2          # T002 の CIP（マナ+1）が無視された
    assert len(e.zlist("hand", 0)) == 4          # T003－1、ドロー+1+2、ターン2ドロー+1
    assert "T003" in [e.s.cards[c].defn for c in e.zlist("graveyard", 0)]
