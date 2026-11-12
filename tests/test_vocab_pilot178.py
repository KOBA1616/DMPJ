"""語彙パイロット第178弾: castle_fortify（城・要塞化）。

城は出す時に自分のシールドを1枚選び、要塞化する（op castle_link が自分の
fortifies に要塞化先の参照を刻む）。要塞化されたシールドがシールドゾーンを
離れると、城は状況起因処理で墓地に置かれる。城の能力はバトルゾーンにある間は
要塞化の有無を問わず機能する。「この城を付けて要塞化されたシールド」は
セレクタ castle_of / when の subject 辞書キー castle_of・castle_only /
when の shield キーで指す。
"""
from pathlib import Path

import yaml
from conftest import setup

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    for cid in ("T398", "T399", "T400", "T401", "T402"):
        parse_card(_proto_card(cid), TABLES)
    kinds = [(a["kind"]) for a in parse_card(_proto_card("T398"), TABLES).abilities]
    assert "trigger" in kinds and "static" in kinds
    rep = next(a for a in parse_card(_proto_card("T399"), TABLES).abilities if a["kind"] == "replace")
    assert rep["when"]["shield"] == {"castle_of": "self", "castle_only": "self"}
    st = next(a for a in parse_card(_proto_card("T402"), TABLES).abilities if a["kind"] == "static")
    assert st["affects"] == {"zone": "shield", "owner": "you", "filter": {"fortified": True}}
    assert st["mod"] == {"allow": ["s_trigger"]}


def _cid(e, player, defn, zone="bz"):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _play(e, tid, max_steps=400, shield_pick=0):
    """手札から tid を出し、城の要塞化選択まで処理して落ち着かせる。
    shield_pick: 要塞化で選ぶシールドの添字。None なら選ばない（城は 1枚必須なので
    シールドがある時は使わない。0枚の時のみ到達しない）。"""
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
            e.answer([shield_pick] if shield_pick is not None else [])
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")] if "no" in keys else [0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def _settle_until(e, pred, max_steps=100):
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


def _attack_out(e, attacker, shield_cids, replace="decline", strigger_cids=()):
    """攻撃宣言から攻撃の終わりまで進め、現れた Decision の kind の列を返す。
    shield_cids: ブレイクするシールドの cid 列。replace: choose_replacement で
    "accept"（置換する）/ "decline"。strigger_cids: 宣言する S・トリガーの cid 列。"""
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
        elif kind == "choose_replacement":
            if replace == "accept":
                e.answer([next(i for i, k in enumerate(keys) if k.startswith("replace:"))])
            else:
                e.answer([keys.index("decline")])
        elif kind in ("declare_strigger", "declare_sback"):
            idx = [i for i, o in enumerate(d["options"]) if o.get("cid") in strigger_cids]
            e.answer(idx)
        elif kind == "yes_no":
            e.answer([keys.index("yes")])
        elif kind == "choose_cards":
            # 置換の instead の選択: ブレイク対象のシールド以外を選ぶ（対象自身を選ぶと
            # ブレイク自体が消滅するため。別シールドを犠牲にするのが趣旨）
            idx = [i for i, o in enumerate(d["options"]) if o.get("cid") not in shield_cids]
            e.answer([idx[0]] if idx else [0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return seen


def test_castle_link_fortifies_and_grants(rules):
    e = setup(rules, {"hand": ["T398"], "mana": ["T030"] * 2, "bz": ["T001"]}, {})
    _play(e, "T398", shield_pick=0)
    me = _cid(e, 0, "T398")
    shield = e.zlist("shield", 0)[0]
    assert list(e.s.cards[me].fortifies) == list(e.s.ref(shield))
    ch = e.chars(_cid(e, 0, "T001"))
    assert ch["power"] == 3000 and "blocker" in ch["keywords"]


def test_no_shields_castle_stays_and_still_grants(rules):
    e = setup(rules, {"hand": ["T398"], "mana": ["T030"] * 2, "bz": ["T001"], "shield": []}, {})
    _play(e, "T398")
    me = _cid(e, 0, "T398")
    assert e.s.cards[me].fortifies is None
    ch = e.chars(_cid(e, 0, "T001"))
    assert ch["power"] == 3000 and "blocker" in ch["keywords"]


def test_shield_leaves_sends_castle_to_graveyard(rules):
    e = setup(rules, {"hand": ["T398"], "mana": ["T030"] * 2}, {})
    _play(e, "T398", shield_pick=0)
    me = _cid(e, 0, "T398")
    shield = e.zlist("shield", 0)[0]
    assert list(e.s.cards[me].fortifies) == list(e.s.ref(shield))
    e._raw_move(shield, "hand")   # 効果でシールドを手札に加える形
    assert _settle_until(e, lambda: e.s.cards[me].zone == "graveyard")
    assert e.s.cards[me].fortifies is None


def test_break_of_fortified_shield_sends_castle_to_graveyard(rules):
    e = setup(rules, {"bz": ["T005", "T002"]}, {"bz": ["T398"], "shield": ["T001", "T001", "T001"]})
    castle = _cid(e, 1, "T398")
    fort = e.zlist("shield", 1)[0]
    e.s.cards[castle].fortifies = e.s.ref(fort)
    other = e.zlist("shield", 1)[1]
    _attack_out(e, "T005", [fort, other])
    assert e.s.cards[fort].zone == "hand"
    assert e.s.cards[other].zone == "hand"
    assert e.s.cards[castle].zone == "graveyard"
    assert e.s.turn_counters.get("broken:1", 0) == 2


def test_break_replacement_for_fortified_shield(rules):
    e = setup(rules, {"bz": ["T005", "T002"]}, {"bz": ["T399"], "shield": ["T001", "T001", "T001"]})
    castle = _cid(e, 1, "T399")
    fort = e.zlist("shield", 1)[0]
    e.s.cards[castle].fortifies = e.s.ref(fort)
    other = e.zlist("shield", 1)[1]
    third = e.zlist("shield", 1)[2]
    seen = _attack_out(e, "T005", [fort, other], replace="accept")
    assert "choose_replacement" in seen
    assert e.s.cards[fort].zone == "shield"      # 置換されたシールドはブレイクされない
    assert e.s.cards[other].zone == "hand"       # もう1枚は通常ブレイク
    assert e.s.cards[castle].zone == "bz"        # 要塞化先が残ったので城も残る
    assert e.s.turn_counters.get("broken:1", 0) == 1
    assert len(e.zlist("shield", 1)) == 1         # かわりに1枚が手札へ（要塞化先だけ残る）
    assert e.s.cards[third].zone == "hand"


def test_break_replacement_blocked_when_fortified_by_two_castles(rules):
    e = setup(rules, {"bz": ["T005", "T002"]}, {"bz": ["T399", "T398"], "shield": ["T001", "T001", "T001"]})
    c399 = _cid(e, 1, "T399")
    c398 = _cid(e, 1, "T398")
    fort = e.zlist("shield", 1)[0]
    e.s.cards[c399].fortifies = e.s.ref(fort)
    e.s.cards[c398].fortifies = e.s.ref(fort)   # 同じシールドを2枚の城が要塞化
    other = e.zlist("shield", 1)[1]
    seen = _attack_out(e, "T005", [fort, other])
    assert "choose_replacement" not in seen    # 他の城に要塞化されているので置換は出ない
    assert e.s.cards[fort].zone == "hand"
    assert e.s.cards[c399].zone == "graveyard"   # 要塞化先が離れたので両方の城が墓地へ
    assert e.s.cards[c398].zone == "graveyard"
    assert e.s.turn_counters.get("broken:1", 0) == 2


def test_break_of_unfortified_shield_offers_no_replacement(rules):
    e = setup(rules, {"bz": ["T005", "T002"]}, {"bz": ["T399"], "shield": ["T001", "T001", "T001"]})
    castle = _cid(e, 1, "T399")
    fort = e.zlist("shield", 1)[0]
    e.s.cards[castle].fortifies = e.s.ref(fort)
    other = e.zlist("shield", 1)[1]
    third = e.zlist("shield", 1)[2]
    seen = _attack_out(e, "T005", [other, third])
    assert "choose_replacement" not in seen
    assert e.s.cards[other].zone == "hand" and e.s.cards[third].zone == "hand"
    assert e.s.cards[castle].zone == "bz"      # 要塞化先は無事
    assert e.s.turn_counters.get("broken:1", 0) == 2


def test_fortify_trigger_discards(rules):
    e = setup(rules, {"hand": ["T400"], "mana": ["T008"] * 4}, {"hand": ["T001"]})
    victim = e.zlist("hand", 1)[0]
    _play(e, "T400", shield_pick=0)
    assert e.s.cards[victim].zone == "graveyard"   # 元の手札が捨てられた（相手のターン開始ドロー分は手札に残る）


def test_fortify_trigger_no_discard_without_shields(rules):
    e = setup(rules, {"hand": ["T400"], "mana": ["T008"] * 4, "shield": []}, {"hand": ["T001"]})
    victim = e.zlist("hand", 1)[0]
    _play(e, "T400")
    assert e.s.cards[victim].zone == "hand"        # 要塞化できなければ捨てさせない
    assert e.zlist("graveyard", 1) == []


def test_may_return_fortifying_castle(rules):
    e = setup(rules, {"hand": ["T401"], "mana": ["T030"] * 4, "bz": ["T398"]}, {})
    castle = _cid(e, 0, "T398")
    shield = e.zlist("shield", 0)[0]
    e.s.cards[castle].fortifies = e.s.ref(shield)
    played = False
    for _ in range(400):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and not played and "play:T401" in keys:
            played = True
            e.answer([keys.index("play:T401")])
            continue
        if played and e.s.cards[castle].zone == "hand":
            break
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "yes_no":
            e.answer([keys.index("yes")])
        elif d["kind"] == "choose_cards":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert e.s.cards[castle].zone == "hand"
    assert e.s.cards[_cid(e, 0, "T401")].zone == "bz"


def test_fortified_shield_grants_strigger(rules):
    e = setup(rules, {"bz": ["T005", "T002"]}, {"bz": ["T402"], "shield": ["T001", "T001"]})
    castle = _cid(e, 1, "T402")
    fort = e.zlist("shield", 1)[0]
    e.s.cards[castle].fortifies = e.s.ref(fort)
    other = e.zlist("shield", 1)[1]
    seen = _attack_out(e, "T005", [fort, other], strigger_cids=[fort])
    assert "declare_strigger" in seen
    assert e.s.cards[fort].zone == "bz"          # S・トリガーで召喚された
    assert e.s.cards[other].zone == "hand"
    assert e.s.cards[castle].zone == "graveyard"  # 要塞化先が離れたので城は墓地へ
    assert e.s.turn_counters.get("broken:1", 0) == 2
