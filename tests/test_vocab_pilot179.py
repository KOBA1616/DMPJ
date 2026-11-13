"""語彙パイロット第179弾: ace_tamaseed_conditional_creature（ACEタマシード）。

ACEタマシードは「自分の、その文明のクリーチャーまたはタマシードが合計4つ以上
なければ、バトルゾーンにあるこのタマシードはクリーチャーとして扱わない」。
面フラグ `ace: true` を持ち、条件を満たす間だけ chars() の types に
"creature" が加わる（NEO進化の型追加と同型）。条件の数えは定義の特性
（fdef）だけで行うため chars() の評価中でも再帰しない。自分自身も数える。
ブロックはクリーチャーだけができる（507.1。combat.py の blockers に型要求を追加）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()
PROTOS = ("T403", "T404", "T405", "T406", "T407")


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    for cid in PROTOS:
        d = parse_card(_proto_card(cid), TABLES)
        assert d.ace is True
        assert d.types == ["tamaseed"]
    assert parse_card(_proto_card("T403"), TABLES).keywords == ["triple_breaker"]
    # 不正形: タマシードでない面の ace / 真でない ace は DefError
    bad = dict(_proto_card("T403"), types=["creature"])
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = dict(_proto_card("T403"), ace="yes")
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _cid(e, player, defn, zone="bz"):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _types(e, cid):
    return e.chars(cid)["types"]


def _settle_until(e, pred, max_steps=200):
    """pred が真になるまで advance する（SBA などのタスクを処理する）。"""
    for _ in range(max_steps):
        if pred():
            return True
        d = e.advance()
        if d is None:
            return pred()
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")] if "no" in keys else [0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return pred()


def _play(e, tid, max_steps=400, yes_no="no"):
    """手札から tid を出す。任意の誘発には yes_no の答えを使う。"""
    played = False
    for _ in range(max_steps):
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and not played and f"play:{tid}" in keys:
            played = True
            e.answer([keys.index(f"play:{tid}")])
            continue
        if played and (d["player"] != 0 or d["kind"] == "attack"):
            return   # 出した側のメインが終わった = 選択まで解決済み
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index(yes_no)] if yes_no in keys else [0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def _attack_out(e, attacker, shield_cids, on_block=None):
    """攻撃宣言から攻撃の終わりまで進め、現れた Decision の kind の列を返す。
    shield_cids: ブレイクするシールドの cid 列。on_block: ブロック決定の直前に
    呼ぶコールバック（攻撃中の継続的効果を観察する用）。"""
    seen = []
    for _ in range(600):
        d = e.advance()
        if d is None:
            break
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
            e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
        elif kind == "choose_shields":
            idx = [i for i, o in enumerate(d["options"]) if o.get("cid") in shield_cids]
            assert idx, f"no shield option for {shield_cids} in {keys}"
            e.answer(idx)
        elif kind == "block":
            if on_block is not None:
                on_block(d)
            e.answer([keys.index("no_block")])
        elif kind == "choose_replacement":
            e.answer([keys.index("decline")])
        elif kind in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif kind == "yes_no":
            e.answer([keys.index("yes")])
        elif kind == "choose_cards":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return seen


def test_ace_inactive_is_not_creature(rules):
    e = setup(rules, {"bz": ["T403"]}, {})
    me = _cid(e, 0, "T403")
    assert "creature" not in _types(e, me)
    assert not e._ace_active(me)
    # 攻撃の選択肢に出ない（攻撃ステップ自体は選択肢が pass だけなら自動で進むため、
    # _attack_options で直接確認する）
    assert not e._can_attack(me)
    assert e._attack_options(0) == []


def test_ace_active_with_three_others(rules):
    e = setup(rules, {"bz": ["T403", "T001", "T001", "T001"]}, {})
    me = _cid(e, 0, "T403")
    assert e._ace_active(me)
    assert "creature" in _types(e, me)
    assert e.chars(me)["power"] == 14000
    assert e.chars(me)["breaks"] == 3   # T・ブレイカー
    shields = e.zlist("shield", 1)[:3]
    mana_before = len(e.zlist("mana", 0))
    _attack_out(e, "T403", shields)
    assert all(e.s.cards[s].zone == "hand" for s in shields)   # 3枚ブレイク
    assert e.s.turn_counters.get("broken:1", 0) == 3
    assert len(e.zlist("mana", 0)) == mana_before + 1   # 攻撃時誘発で山札の上1枚をマナへ


def test_ace_counts_tamaseeds(rules):
    # タマシード同士も数える: T403 2体 + クリーチャー2体 = 4
    e = setup(rules, {"bz": ["T403", "T403", "T001", "T001"]}, {})
    mes = [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T403"]
    assert len(mes) == 2
    assert all("creature" in _types(e, c) for c in mes)


def test_ace_counts_only_own_civ(rules):
    # 他の文明は数えない: 自然 T403 + 火クリーチャー3体では条件を満たさない
    e = setup(rules, {"bz": ["T403", "T027", "T027", "T027"]}, {})
    me = _cid(e, 0, "T403")
    assert "creature" not in _types(e, me)
    # 相手の自然クリーチャーも数えない
    e2 = setup(rules, {"bz": ["T403"]}, {"bz": ["T001", "T001", "T001"]})
    me2 = _cid(e2, 0, "T403")
    assert "creature" not in _types(e2, me2)


def test_ace_loses_creature_when_count_drops(rules):
    e = setup(rules, {"bz": ["T403", "T001", "T001", "T001"]}, {})
    me = _cid(e, 0, "T403")
    assert "creature" in _types(e, me)
    victim = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T001")
    e._raw_move(victim, "graveyard")
    assert _settle_until(e, lambda: "creature" not in _types(e, me))
    assert not e._ace_active(me)


def test_ace_cip_works_when_inactive(rules):
    # タマシードの能力はクリーチャーでなくても働く: CIP でマナ4枚アンタップ
    e = setup(rules, {"hand": ["T403"], "mana": ["T001"] * 5}, {})
    _play(e, "T403")
    me = _cid(e, 0, "T403")
    assert e.s.cards[me].zone == "bz"
    assert "creature" not in _types(e, me)   # 数が足りないのでクリーチャーではない
    mana = e.zlist("mana", 0)
    assert sum(1 for c in mana if not e.s.cards[c].tapped) == 4   # 5枚払って4枚アンタップ


def _block_options(e, attacker_defn, max_steps=600):
    """相手の attacker_defn による攻撃まで進め、ブロック決定の選択肢の cid 列を返す。
    ブロック決定が出なければ None。"""
    for _ in range(max_steps):
        d = e.advance()
        if d is None:
            return None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] in ("charge", "main"):
            e.answer([keys.index("pass")])
        elif d["kind"] == "attack":
            hit = [i for i, k in enumerate(keys) if k == f"attack:{attacker_defn}:player"]
            if not hit:
                e.answer([keys.index("pass")])
                continue
            e.answer([hit[0]])
        elif d["kind"] == "block":
            return [o.get("cid") for o in d["options"]]
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return None


def test_ace_blocker_only_when_active(rules):
    # 条件を満たす時だけブロッカーとして選べる
    e = setup(rules, {"bz": ["T404", "T004", "T004", "T004"]},
              {"bz": ["T005"]})
    me = _cid(e, 0, "T404")
    assert "creature" in _types(e, me)
    opts = _block_options(e, "T005")
    assert opts is not None and me in opts
    # 条件を満たさない時はブロックの選択肢に T404 が出ない
    # （T004 を1体入れておかないと、選択肢が no_block だけでブロック決定自体が出ない）
    e2 = setup(rules, {"bz": ["T404", "T004"]}, {"bz": ["T005"]})
    me2 = _cid(e2, 0, "T404")
    assert "creature" not in _types(e2, me2)
    opts2 = _block_options(e2, "T005")
    assert opts2 is not None and me2 not in opts2


def test_ace_attack_grants_power_to_others(rules):
    # T405 の攻撃時誘発: 他のクリーチャーにターン終了まで+6000（自身は除く）
    # （相手にブロッカー T004 を置いておかないと、ブロック決定自体が出ない）
    e = setup(rules, {"bz": ["T405", "T027", "T027", "T027"]}, {"bz": ["T004"]})
    other = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T027")
    me = _cid(e, 0, "T405")
    assert "creature" in _types(e, me)
    assert e.chars(other)["power"] == 1000
    seen_power = {}

    def on_block(d):
        seen_power["other"] = e.chars(other)["power"]
        seen_power["me"] = e.chars(me)["power"]

    shields = e.zlist("shield", 1)[:2]
    _attack_out(e, "T405", shields, on_block=on_block)
    assert seen_power["other"] == 7000   # 攻撃中に+6000
    assert seen_power["me"] == 9000     # 自身は対象外
    assert all(e.s.cards[s].zone == "hand" for s in shields)   # W・ブレイカーで2枚


def test_ace_no_leave_only_on_own_turn(rules):
    # T406 の「自分のターン中、破壊以外の方法で離れない」は自ターンだけ
    e = setup(rules, {"bz": ["T406", "T008", "T008", "T008"]}, {})
    me = _cid(e, 0, "T406")
    assert "creature" in _types(e, me)
    assert e.chars(me)["no_leave"] == [{"except_destroy": True}]
    assert _settle_until(e, lambda: e.s.active == 1, max_steps=200)
    assert e.chars(me)["no_leave"] == []


def test_ace_cip_optional_draw_discard(rules):
    # T407 の CIP（任意）: 引いて3枚、捨てて2枚。断れば何も起きない
    e = setup(rules, {"hand": ["T407"], "mana": ["T009"] * 4}, {})
    _play(e, "T407", yes_no="yes")
    me = _cid(e, 0, "T407")
    assert e.s.cards[me].zone == "bz"
    assert len(e.zlist("graveyard", 0)) == 2   # 捨てた2枚
    e2 = setup(rules, {"hand": ["T407"], "mana": ["T009"] * 4}, {})
    _play(e2, "T407", yes_no="no")
    assert e2.s.cards[_cid(e2, 0, "T407")].zone == "bz"
    assert e2.zlist("graveyard", 0) == []
