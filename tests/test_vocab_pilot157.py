"""hyper_release（効果によるハイパーモード解放）。

設計ノート: pilot156-hyper-release-design.md（ツリー内では第157弾として実装する）。

- 新 op `hyper_release {select}` の1点だけが拡張。旗（Card.hyper）と寿命
  （コントローラーの次のターンのはじめに st_start が解除＝「次の自分のターンのはじめまで」）は既存の仕組み。
- ハイパー面を持たない対象には旗を立てない（選択自体は文面どおり行う）。
- 解放にタップ等のコストは伴わない（hyper_act のタップ手順は走らない）。
- proto T215〜T222（設計ノートの T203〜T210 を現行の空き番号へずらした）。
"""
from pathlib import Path

import yaml
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def _by_defn(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p) if e.cdef(c).id == defn)


def _drive(e, done, main_keys=(), choose_defn=None, yes=True, counter=None, max_steps=300):
    """done() になるまで進める。main_keys は main/attack で優先する選択肢キー、
    choose_defn は choose_cards で優先する defn 名。"""
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        if counter is not None:
            counter(d)
        keys = [o["key"] for o in d["options"]]
        hit = [i for i, k in enumerate(keys) if k in main_keys]
        if hit and d["kind"] in ("main", "attack"):
            e.answer([hit[0]])
        elif d["kind"] == "yes_no":
            e.answer([keys.index("yes" if yes else "no")])
        elif choose_defn and d["kind"] in ("choose_cards", "choose_evo_source"):
            idx = [i for i, k in enumerate(keys) if choose_defn in k]
            e.answer(idx[:max(d["min"], 1)] if idx else list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return done()


def _play(e, defn, **kw):
    return _drive(e, lambda: any(e.cdef(c).id == defn for c in e.bz_tops(0)),
                  main_keys=(f"play:{defn}",), **kw)


def test_proto_parse():
    for cid in ("T215", "T216", "T217", "T218", "T219", "T220", "T221", "T222"):
        parse_card(_proto_card(cid), TABLES)
    t216 = parse_card(_proto_card("T216"), TABLES)
    assert t216.abilities[0]["effect"] == [
        {"op": "hyper_release", "select": {"zone": "bz", "owner": "you", "count": 1,
                                           "filter": {"types": ["creature"], "race_has": "超化獣"}}}]
    t218 = parse_card(_proto_card("T218"), TABLES)
    assert t218.hyper is False and "超化獣" in t218.races
    t220 = parse_card(_proto_card("T220"), TABLES)
    trig = [a for a in t220.abilities if a["kind"] == "trigger"]
    assert trig and trig[0]["if"] == {"hyper": True}
    assert trig[0]["effect"][0]["select"]["count"] == "all"


def test_attack_release(rules):
    """(1) T216 の攻撃時誘発で T215 が解放され、ハイパー面のパワー修整が働く。"""
    e = setup(rules, {"hand": ["T215", "T216"], "mana": ["T001", "T005"] * 5}, {})
    assert _play(e, "T215") and _play(e, "T216")
    t215 = _by_defn(e, "bz", 0, "T215")
    assert not e.is_hyper(t215) and e.chars(t215)["power"] == 5000
    shields = len(e.zlist("shield", 1))
    ok = _drive(e, lambda: len(e.zlist("shield", 1)) < shields,
                main_keys=("attack:T216:player",), choose_defn="T215")
    assert ok   # 攻撃が通りシールドが割れた
    assert e.is_hyper(t215) and e.chars(t215)["power"] == 9000


def test_release_no_candidates(rules):
    """(2) 自分の場に超化獣がいない時、解放の選択は出ずに攻撃が進む（不発）。"""
    e = setup(rules, {"hand": ["T216"], "mana": ["T005"] * 9}, {})
    assert _play(e, "T216")
    seen = {"choose_cards": 0}

    def counter(d):
        if d["kind"] == "choose_cards":
            seen["choose_cards"] += 1

    shields = len(e.zlist("shield", 1))
    ok = _drive(e, lambda: len(e.zlist("shield", 1)) < shields,
                main_keys=("attack:T216:player",), counter=counter)
    assert ok and seen["choose_cards"] == 0


def test_release_already_hyper(rules):
    """(3) 既にハイパーの対象を選び直しても変化なし（再解放は空振り）。"""
    e = setup(rules, {"hand": ["T215", "T216", "T217"], "mana": ["T001", "T005"] * 5}, {})
    assert _play(e, "T215") and _play(e, "T216")
    t215 = _by_defn(e, "bz", 0, "T215")
    # 2ターン目: T217 で解放してから、攻撃時誘発で同じ対象を選び直す
    ok = _drive(e, lambda: e.is_hyper(t215), main_keys=("play:T217",), choose_defn="T215")
    assert ok and e.chars(t215)["power"] == 9000
    shields = len(e.zlist("shield", 1))
    ok = _drive(e, lambda: len(e.zlist("shield", 1)) < shields,
                main_keys=("attack:T216:player",), choose_defn="T215")
    assert ok and e.is_hyper(t215) and e.chars(t215)["power"] == 9000


def test_release_duration_own_turn(rules):
    """(4) 自ターン中に解放した旗は、そのターンの残りと相手ターン中を通じて立ち、
    次の自分のターンのはじめに解ける（設計 §6 (4)。公式 QA 44820）。

    旗の寿命は st_start の解除に任せる（§3.3）。解除範囲は「そのターンのプレイヤーが
    コントロールするカードだけ」で、相手ターンのはじめでは解けない。"""
    e = setup(rules, {"hand": ["T215", "T217"], "mana": ["T001"] * 8}, {})
    assert _play(e, "T215")
    t215 = _by_defn(e, "bz", 0, "T215")
    assert _drive(e, lambda: e.is_hyper(t215), main_keys=("play:T217",), choose_defn="T215")
    release_turn = e.s.turn
    samples = []   # 解放後の (turn, hyper) 観測
    cleared = {"seen": False}
    for _ in range(300):
        samples.append((e.s.turn, e.is_hyper(t215)))
        if e.s.turn >= release_turn + 2 and e.s.active == 0:
            cleared["seen"] = not e.is_hyper(t215)   # 次の自分のターンのはじめに解けている
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    own_rest = [h for t, h in samples if t == release_turn]
    opp_turn = [h for t, h in samples if t == release_turn + 1]
    assert own_rest and all(own_rest)   # 解放したターンの残りはずっと立っていた
    assert opp_turn and all(opp_turn)   # 相手ターン中も立ったまま
    assert cleared["seen"]              # 次の自分のターンのはじめに解けた


def test_release_duration_opp_turn(rules):
    """(5) コントローラー（プレイヤー1）が自分のターン中に唱えて解放した場合も、
    旗はそのターンの残りと相手（プレイヤー0）ターン中を通じて立ち、
    コントローラーの次のターンのはじめに解ける（寿命は test_release_duration_own_turn と同じ）。"""
    e = setup(rules, {}, {"bz": ["T215"], "hand": ["T217"], "mana": ["T001"] * 4})
    t215 = _by_defn(e, "bz", 1, "T215")
    cast = {"done": False, "turn": None, "released": False}
    samples = []
    cleared = {"seen": False}
    for _ in range(300):
        if cast["done"] and e.is_hyper(t215):
            cast["released"] = True
        if cast["released"]:
            samples.append((e.s.turn, e.is_hyper(t215)))
            if e.s.turn >= cast["turn"] + 2:
                cleared["seen"] = not e.is_hyper(t215)
                break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not cast["done"] and d["kind"] == "main" and d["player"] == 1 and "play:T217" in keys:
            e.answer([keys.index("play:T217")])
            cast["done"] = True
            cast["turn"] = e.s.turn
        elif d["kind"] in ("choose_cards",):
            idx = [i for i, k in enumerate(keys) if "T215" in k]
            e.answer(idx[:1] if idx else list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert cast["released"]
    same_turn = [h for t, h in samples if t == cast["turn"]]
    opp_turn = [h for t, h in samples if t == cast["turn"] + 1]
    assert same_turn and all(same_turn)   # 解放したターンの残りはずっと立っていた
    assert opp_turn and all(opp_turn)     # 相手ターン中も立ったまま
    assert cleared["seen"]                # コントローラーの次のターンのはじめに解けた


def test_self_release(rules):
    """(6) T219 は出た時に自身を解放し、次の自分のターンのはじめまでハイパー面のパワーになる
    （相手ターンを挟んで維持される。寿命は test_release_duration_own_turn と同じ）。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T219"], "mana": ["T009"] * 6}, {})
    samples = []

    def counter(d):
        t219 = next((c for c in e.s.cards if c.defn == "T219"), None)
        if t219 is not None and t219.zone == "bz":
            samples.append((e.s.turn, e.is_hyper(t219.cid), e.chars(t219.cid)["power"]))

    assert _play(e, "T219", counter=counter)
    _drive(e, lambda: e.s.turn >= 3 and e.s.active == 0, counter=counter, max_steps=200)
    turn1 = [s for s in samples if s[0] == 1]
    assert turn1 and all(h and p == 9000 for _, h, p in turn1)   # 出たターン中は解放されている
    turn2 = [s for s in samples if s[0] == 2]
    assert turn2 and all(h and p == 9000 for _, h, p in turn2)   # 相手ターン中も解放されたまま
    turn3 = [s for s in samples if s[0] == 3]
    assert turn3 and not any(h for _, h, _ in turn3)             # 次の自分のターンのはじめに解けている


def test_release_all_and_guard(rules):
    """(7) ハイパー時の攻撃で自分の超化獣すべてを解放する。ハイパー面を持たない
    超化獣（T218）には旗が立たない。"""
    e = setup(rules, {"bz": ["T215", "T218"], "hand": ["T220", "T217"], "mana": ["T001"] * 8}, {})
    assert _play(e, "T220")
    t215 = _by_defn(e, "bz", 0, "T215")
    t218 = _by_defn(e, "bz", 0, "T218")
    t220 = _by_defn(e, "bz", 0, "T220")
    ok = _drive(e, lambda: e.is_hyper(t220), main_keys=("play:T217",), choose_defn="T220")
    assert ok
    shields = len(e.zlist("shield", 1))
    ok = _drive(e, lambda: len(e.zlist("shield", 1)) <= shields - 2,
                main_keys=("attack:T220:player",))
    assert ok   # W・ブレイカーで2枚割れた＝攻撃時誘発が解決した
    assert e.is_hyper(t215) and e.chars(t215)["power"] == 9000
    assert not e.is_hyper(t218)   # ハイパー面を持たない対象には旗を立てない
    assert e.is_hyper(t220)


def test_release_all_not_triggered_when_not_hyper(rules):
    """(7) 対照: ハイパーでない T220 の攻撃では誘発せず、何も解放されない。"""
    e = setup(rules, {"bz": ["T215"], "hand": ["T220"], "mana": ["T001"] * 8}, {})
    assert _play(e, "T220")
    t215 = _by_defn(e, "bz", 0, "T215")
    shields = len(e.zlist("shield", 1))
    ok = _drive(e, lambda: len(e.zlist("shield", 1)) <= shields - 2,
                main_keys=("attack:T220:player",))
    assert ok and not e.is_hyper(t215)


def test_conditional_release_and_battle(rules):
    """(8) T221: 超化獣を選ぶと解放してからバトルする。"""
    e = setup(rules, {"bz": ["T215"], "hand": ["T221"], "mana": ["T005"] * 4},
              {"bz": ["T005"]})
    t215 = _by_defn(e, "bz", 0, "T215")
    opp = _by_defn(e, "bz", 1, "T005")
    ok = _drive(e, lambda: e.s.cards[opp].zone == "graveyard",
                main_keys=("play:T221",), choose_defn="T215", yes=True)
    assert ok
    assert e.is_hyper(t215) and e.s.cards[t215].zone == "bz"   # 9000 vs 3000 で勝ち残る


def test_conditional_no_release_battle_still_offered(rules):
    """(8) T221: 超化獣でないクリーチャーを選ぶと解放は起きないが、バトルの選択は提示される。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T221"], "mana": ["T005"] * 4},
              {"bz": ["T005"]})
    seen = {"yes_no": 0}

    def counter(d):
        if d["kind"] == "yes_no":
            seen["yes_no"] += 1

    ok = _drive(e, lambda: seen["yes_no"] >= 1, main_keys=("play:T221",),
                choose_defn="T001", yes=False, counter=counter)
    assert ok   # 解放しなくてもバトルの may が提示された
    assert not any(e.is_hyper(c) for c in e.bz_tops(0))
    assert _by_defn(e, "bz", 1, "T005") is not None   # バトルを断ったので相手は残る


def test_entry_release_and_blocker(rules):
    """(9) T222: 手札から出した超化獣を解放しブロッカーを与える。解放もブロッカー付与も
    次の自分のターンのはじめまで続く。

    観測点: 呪文解決後に同じターンで現れる攻撃ステップの決定（場の T001 が攻撃できる）
    で旗と付与を確認し、その後、次の自分のターンの頭で両方が解けていることを見る。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T215", "T222"], "mana": ["T004"] * 5}, {})
    seen = {}

    def counter(d):
        t215 = next((c for c in e.s.cards if c.defn == "T215"), None)
        if t215 is not None and t215.zone == "bz" and e.s.turn == 1 and "in_turn" not in seen:
            seen["in_turn"] = (e.is_hyper(t215.cid), e.chars(t215.cid)["power"],
                               "blocker" in e.chars(t215.cid)["keywords"])

    ok = _drive(e, lambda: "in_turn" in seen, main_keys=("play:T222",),
                choose_defn="T215", yes=True, counter=counter, max_steps=80)
    assert ok
    assert seen["in_turn"] == (True, 9000, True)   # 出たターン中: 解放され、ブロッカーも付いている
    t215 = _by_defn(e, "bz", 0, "T215")
    for _ in range(120):
        d = e.advance()
        if d is None:
            break
        if e.s.turn >= 3 and e.s.active == 0:
            break   # 次の自分のターンに入った
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert not e.is_hyper(t215)
    assert "blocker" not in e.chars(t215)["keywords"]


def test_entry_may_decline(rules):
    """(9) T222: may を断ると出さず・解放せず・付与しない（参照 ent が空で空振り）。"""
    e = setup(rules, {"hand": ["T215", "T222"], "mana": ["T004"] * 5}, {})
    ok = _drive(e, lambda: any(e.cdef(c).id == "T222" for c in e.zlist("graveyard", 0)),
                main_keys=("play:T222",), yes=False)
    assert ok
    assert _by_defn(e, "hand", 0, "T215") is not None   # 手札に残ったまま
    assert not any(e.cdef(c).id == "T215" for c in e.bz_tops(0))
