"""語彙パイロット第180弾: j_tornado（Jトルネード）。

Jトルネードは定義語（「自分の他のジョーカーズ（・クリーチャー）を１体、手札に
戻す」）で、新エンジン語彙は要らない。核は既存語彙だけのイディオム:
攻撃時（またはブロック時）誘発 → if {exists: 他のジョーカーズ} ガード →
may [move (exclude self, as: jtornado), 後続]。「２回まで」は repeat {times: 2}
の各反復に may を置く。合計コスト形は cost_of が最大値を返すため 2 回分を
展開して jt1/jt2 に束縛し、cost_le: {sum: [cost_of jt1, cost_of jt2]} と書く。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()
PROTOS = ("T408", "T409", "T410", "T411", "T412")


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    for cid in PROTOS:
        assert parse_card(_proto_card(cid), TABLES) is not None
    assert parse_card(_proto_card("T409"), TABLES).keywords == ["blocker", "cannot_attack"]
    assert parse_card(_proto_card("T410"), TABLES).keywords == ["double_breaker"]
    assert parse_card(_proto_card("T411"), TABLES).keywords == ["s_trigger"]
    assert parse_card(_proto_card("T412"), TABLES).keywords == ["g_strike"]
    t408 = _proto_card("T408")
    assert t408["abilities"][0]["kind"] == "trigger"
    assert t408["abilities"][0]["when"] == {"event": "attack", "subject": "self"}


def _cid(e, player, defn, zone="bz"):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _drive_attack(e, attacker, shield_cids, yes_no_queue=None, mode_queue=None,
                  on_attack=None, stop=None, choose_pick=None, max_steps=600):
    """攻撃宣言から進め、stop が真になったら止まる。yes_no_queue は yes_no 決定への
    答えの列（'yes'/'no'。空なら 'yes'）。mode_queue は choose_mode への答えの列。
    攻撃は attacker で1回だけ行い、2回目の攻撃決定では pass して止める。
    choose_pick は choose_cards 決定への答えを決める関数（d -> index 列）。"""
    yes_no_queue = list(yes_no_queue or [])
    mode_queue = list(mode_queue or [])
    seen = []
    attacked = False
    for _ in range(max_steps):
        if stop is not None and stop():
            break
        d = e.advance()
        if d is None:
            break
        kind = d["kind"]
        seen.append(kind)
        keys = [o["key"] for o in d["options"]]
        if kind in ("charge", "main"):
            e.answer([keys.index("pass")])
        elif kind == "attack":
            if attacked:
                e.answer([keys.index("pass")])
                break
            if on_attack is not None:
                on_attack(d)
            hit = [i for i, k in enumerate(keys) if k == f"attack:{attacker}:player"]
            if not hit:
                e.answer([keys.index("pass")])
                break
            attacked = True
            e.answer([hit[0]])
        elif kind == "choose_breaker":
            e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
        elif kind == "choose_shields":
            idx = [i for i, o in enumerate(d["options"]) if o.get("cid") in shield_cids]
            assert idx, f"no shield option for {shield_cids} in {keys}"
            e.answer(idx)
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif kind == "choose_replacement":
            e.answer([keys.index("decline")])
        elif kind in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif kind == "yes_no":
            ans = yes_no_queue.pop(0) if yes_no_queue else "yes"
            e.answer([keys.index(ans)])
        elif kind == "choose_mode":
            m = mode_queue.pop(0) if mode_queue else 0
            e.answer([keys.index(f"mode:{m}")])
        elif kind == "choose_cards":
            if choose_pick is not None:
                e.answer(choose_pick(d))
            else:
                e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return seen


def _drive_block(e, blocker_defn, attacker_defn, yes_no_queue=None, stop=None,
                 on_attack=None, max_steps=600):
    """相手の attacker_defn の攻撃まで進め、blocker_defn でブロックする。
    こちらは攻撃しない。stop が真になったら止まる。on_attack は各攻撃決定の
    直前に呼ぶコールバック（ブロック前後のタップ状態を観察する用）。相手の
    2回目の攻撃決定では pass して止める。"""
    yes_no_queue = list(yes_no_queue or [])
    seen = []
    attacked = False
    for _ in range(max_steps):
        if stop is not None and stop():
            break
        d = e.advance()
        if d is None:
            break
        kind = d["kind"]
        seen.append(kind)
        keys = [o["key"] for o in d["options"]]
        if kind in ("charge", "main"):
            e.answer([keys.index("pass")])
        elif kind == "attack":
            if on_attack is not None:
                on_attack(d)
            if attacked:
                e.answer([keys.index("pass")])
                break
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker_defn}:player"]
            if not hit:
                e.answer([keys.index("pass")])
            else:
                attacked = True
                e.answer([hit[0]])
        elif kind == "block":
            tgt = [i for i, o in enumerate(d["options"])
                   if o.get("cid") is not None
                   and e.s.cards[o["cid"]].defn == blocker_defn]
            assert tgt, f"no blocker {blocker_defn} in {keys}"
            e.answer([tgt[0]])
        elif kind == "yes_no":
            ans = yes_no_queue.pop(0) if yes_no_queue else "yes"
            e.answer([keys.index(ans)])
        elif kind == "choose_cards":
            e.answer(list(range(d["min"])))
        elif kind in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif kind == "choose_replacement":
            e.answer([keys.index("decline")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return seen


def test_jtornado_attack_draw(rules):
    # T408 の攻撃時 Jトルネード: 承諾すると他のジョーカーズが手札に戻り、2ドロー
    e = setup(rules, {"bz": ["T408", "T408"]}, {})
    att = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T408")
    other = next(c for c in e.zlist("bz", 0)
                 if e.s.cards[c].defn == "T408" and c != att)
    shield = e.zlist("shield", 1)[:1]
    state = {}

    def on_attack(d):
        state["hand"] = len(e.zlist("hand", 0))

    _drive_attack(e, "T408", shield, on_attack=on_attack,
                 stop=lambda: e.s.cards[shield[0]].zone == "hand")
    assert e.s.cards[other].zone == "hand"   # 他のジョーカーズが手札へ
    assert e.s.cards[att].zone == "bz"
    # 手札: Jトルネードの2ドロー＋戻ったジョーカーズ1枚 = +3（先攻1ターン目はドローなし）
    assert len(e.zlist("hand", 0)) == state["hand"] + 3
    assert e.s.cards[shield[0]].zone == "hand"   # 1枚ブレイク


def test_jtornado_attack_decline(rules):
    # 辞退すると何も起きない（戻さず、引かず）
    e = setup(rules, {"bz": ["T408", "T408"]}, {})
    other = [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T408"]
    shield = e.zlist("shield", 1)[:1]
    state = {}

    def on_attack(d):
        state["hand"] = len(e.zlist("hand", 0))

    _drive_attack(e, "T408", shield, yes_no_queue=["no"], on_attack=on_attack,
                 stop=lambda: e.s.cards[shield[0]].zone == "hand")
    assert all(e.s.cards[c].zone == "bz" for c in other)
    assert len(e.zlist("hand", 0)) == state["hand"]   # ドローなし
    assert e.s.cards[shield[0]].zone == "hand"


def test_jtornado_no_other_joker(rules):
    # 他のジョーカーズが無ければ may が出ない（if ガード）
    e = setup(rules, {"bz": ["T408"]}, {})
    shield = e.zlist("shield", 1)[:1]
    seen = _drive_attack(e, "T408", shield,
                         stop=lambda: e.s.cards[shield[0]].zone == "hand")
    assert "yes_no" not in seen
    assert e.s.cards[shield[0]].zone == "hand"


def test_jtornado_block_untap(rules):
    # T409 のブロック時 Jトルネード: 承諾すると他のジョーカーズが手札に戻り、自アンタップ
    # （2体目の攻撃決定はまだ相手ターンのため、ターン開始アンタップより前に観測できる）
    e = setup(rules, {"bz": ["T409", "T408"]}, {"bz": ["T027", "T027"]})
    me = _cid(e, 0, "T409")
    other = _cid(e, 0, "T408")
    atts = [c for c in e.zlist("bz", 1) if e.s.cards[c].defn == "T027"]
    tapped_at_attack = []

    def on_attack(d):
        tapped_at_attack.append(e.s.cards[me].tapped)

    _drive_block(e, "T409", "T027", on_attack=on_attack)
    assert len(tapped_at_attack) == 3   # 自分の攻撃手順、相手の1回目、2回目
    assert tapped_at_attack[-1] is False   # 2回目の攻撃決定時点で既にアンタップ済み
    assert e.s.cards[other].zone == "hand"
    assert e.s.cards[me].zone == "bz"
    assert e.s.cards[atts[0]].zone == "graveyard"   # 5000 vs 1000 でバトルに勝つ
    assert e.s.cards[atts[1]].zone == "bz"   # 2体目は攻撃しなかった


def test_jtornado_block_no_other_joker(rules):
    # 他のジョーカーズが無ければ may が出ず、ブロッカーはタップされたまま残る
    # （2体目の攻撃決定はまだ相手ターンのため、ターン開始アンタップの影響を受けない）
    e = setup(rules, {"bz": ["T409"]}, {"bz": ["T027", "T027"]})
    me = _cid(e, 0, "T409")
    atts = [c for c in e.zlist("bz", 1) if e.s.cards[c].defn == "T027"]
    tapped_at_attack = []

    def on_attack(d):
        tapped_at_attack.append(e.s.cards[me].tapped)

    seen = _drive_block(e, "T409", "T027", on_attack=on_attack)
    assert "yes_no" not in seen
    # 攻撃決定は2回だけ（自分の攻撃手順は攻撃できるクリーチャーが無く決定が出ない）
    assert tapped_at_attack == [False, True]
    assert e.s.cards[me].zone == "bz"
    assert e.s.cards[atts[0]].zone == "graveyard"
    assert e.s.cards[atts[1]].zone == "bz"


def test_jtornado_repeat_two_casts(rules):
    # T410 の最大2回: 2体のジョーカーズを戻し、1回につき手札の呪文を1枚無料で唱える
    e = setup(rules, {"bz": ["T410", "T408", "T408"],
                      "hand": ["T003", "T003"]}, {})
    jokers = [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T408"]
    shields = e.zlist("shield", 1)[:2]
    state = {}

    def on_attack(d):
        state["hand"] = len(e.zlist("hand", 0))

    _drive_attack(e, "T410", shields, on_attack=on_attack,
                 stop=lambda: all(e.s.cards[s].zone == "hand" for s in shields))
    assert all(e.s.cards[c].zone == "hand" for c in jokers)   # 2体とも戻った
    assert [e.s.cards[c].defn for c in e.zlist("graveyard", 0)] == ["T003", "T003"]
    # 手札: 唱えた2枚 -2、唱えた呪文のドロー +4、戻ったジョーカーズ +2 = +4
    assert len(e.zlist("hand", 0)) == state["hand"] + 4
    assert all(e.s.cards[s].zone == "hand" for s in shields)   # W・ブレイカーで2枚


def test_jtornado_repeat_one_decline(rules):
    # 2回目の Jトルネードを辞退すると、1回分だけ戻って唱える
    e = setup(rules, {"bz": ["T410", "T408", "T408"],
                      "hand": ["T003"]}, {})
    jokers = [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T408"]
    shields = e.zlist("shield", 1)[:2]
    _drive_attack(e, "T410", shields,
                 yes_no_queue=["yes", "yes", "no"],
                 stop=lambda: all(e.s.cards[s].zone == "hand" for s in shields))
    moved = [c for c in jokers if e.s.cards[c].zone == "hand"]
    stayed = [c for c in jokers if e.s.cards[c].zone == "bz"]
    assert len(moved) == 1 and len(stayed) == 1
    assert [e.s.cards[c].defn for c in e.zlist("graveyard", 0)] == ["T003"]
    assert all(e.s.cards[s].zone == "hand" for s in shields)


def test_jtornado_sum_cast_hand(rules):
    # T412: 2体戻す（コスト2+2=4）と、手札の呪文を無料で唱え、解決後山札の下へ
    e = setup(rules, {"bz": ["T412", "T408", "T408"],
                      "hand": ["T003"]}, {})
    jokers = [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T408"]
    spell = _cid(e, 0, "T003", zone="hand")
    shield = e.zlist("shield", 1)[:1]
    state = {}

    def on_attack(d):
        state["hand"] = len(e.zlist("hand", 0))

    _drive_attack(e, "T412", shield, mode_queue=[0], on_attack=on_attack,
                 stop=lambda: e.s.cards[shield[0]].zone == "hand")
    assert all(e.s.cards[c].zone == "hand" for c in jokers)
    assert e.s.cards[spell].zone == "deck"
    assert e.zlist("deck", 0)[-1] == spell   # 山札の一番下
    assert e.zlist("graveyard", 0) == []
    # 手札: 唱えた1枚 -1、呪文のドロー +2、戻ったジョーカーズ +2 = +3
    assert len(e.zlist("hand", 0)) == state["hand"] + 3
    assert e.s.cards[shield[0]].zone == "hand"


def test_jtornado_sum_cast_graveyard(rules):
    # T412: 1体だけ戻す（コスト2）と、墓地の呪文を無料で唱え、解決後山札の下へ
    e = setup(rules, {"bz": ["T412", "T408"],
                      "graveyard": ["T003"]}, {})
    joker = _cid(e, 0, "T408")
    spell = _cid(e, 0, "T003", zone="graveyard")
    shield = e.zlist("shield", 1)[:1]
    _drive_attack(e, "T412", shield, mode_queue=[1],
                 stop=lambda: e.s.cards[shield[0]].zone == "hand")
    assert e.s.cards[joker].zone == "hand"
    assert e.s.cards[spell].zone == "deck"
    assert e.zlist("deck", 0)[-1] == spell
    assert e.zlist("graveyard", 0) == []
    assert e.s.cards[shield[0]].zone == "hand"


def test_jtornado_sum_too_small(rules):
    # 合計コスト2ではコスト3の呪文は唱えられない（唱えず、手札に残る）
    e = setup(rules, {"bz": ["T412", "T408"],
                      "hand": ["T006"]}, {})
    joker = _cid(e, 0, "T408")
    spell = _cid(e, 0, "T006", zone="hand")
    shield = e.zlist("shield", 1)[:1]
    _drive_attack(e, "T412", shield, mode_queue=[0],
                 stop=lambda: e.s.cards[shield[0]].zone == "hand")
    assert e.s.cards[joker].zone == "hand"
    assert e.s.cards[spell].zone == "hand"   # 唱えられなかった
    assert e.zlist("graveyard", 0) == []
    assert e.s.cards[shield[0]].zone == "hand"


def test_jtornado_draw_discard(rules):
    # T411: Jトルネードの後に3ドロー1捨て（捨てるのはダミー T001。戻ったジョーカーズを捨てない）
    e = setup(rules, {"bz": ["T411", "T408"]}, {})
    other = _cid(e, 0, "T408")
    shield = e.zlist("shield", 1)[:1]
    state = {}

    def on_attack(d):
        state["hand"] = len(e.zlist("hand", 0))

    def pick_filler(d):
        return [next(i for i, o in enumerate(d["options"])
                     if e.s.cards[o["cid"]].defn == "T001")]

    _drive_attack(e, "T411", shield, on_attack=on_attack,
                 choose_pick=pick_filler,
                 stop=lambda: e.s.cards[shield[0]].zone == "hand")
    assert e.s.cards[other].zone == "hand"
    assert len(e.zlist("graveyard", 0)) == 1   # 捨てた1枚
    # 手札: ドロー +3、捨て -1、戻ったジョーカーズ +1 = +3
    assert len(e.zlist("hand", 0)) == state["hand"] + 3
    assert e.s.cards[shield[0]].zone == "hand"
