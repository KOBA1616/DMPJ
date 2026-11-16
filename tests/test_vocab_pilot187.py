"""語彙パイロット第187弾: friend_burst（フレンド・バースト）。

「X・フレンド・バースト（このクリーチャーが出た時、自分の他のX・クリーチャーを
１体タップしてもよい。そうしたら、このクリーチャーの呪文側を、バトルゾーンに
置いたままコストを支払わずに唱える。）」。新エンジン語彙は要らない。第14弾・
第184弾の op cast_face（自分の呪文面を置いたまま無料で唱える）と既存 op の
組合せだけのイディオム・パイロット（第180弾の Jトルネードと同型）。

カードの型（クリーチャー面の CIP 誘発）:
  {kind: trigger, when: {event: move, to: bz, subject: self}, effect: [
    {op: if, cond: {exists: {zone: bz, owner: you,
      filter: {types: [creature], race_has: <X>, tapped: false}, exclude: {ref: self}}},
     then: [{op: may, body: [
       {op: tap, select: {zone: bz, owner: you,
         filter: {types: [creature], race_has: <X>, tapped: false}, exclude: {ref: self}, count: 1}},
       {op: cast_face}]}]}]}
race_has: <X> は「X・フレンド・バースト」の X（スノーフェアリー／メカ／アビス／
アーマード／ジャイアント／マジック）。部分一致のため「コマンド」類と同型
（第183弾）。「・」で結ばれた複合種族は両方の種族を持つ扱いのため、例えば
race_has: スノーフェアリー はジャイアント・スノーフェアリーにも当たる。
tapped: false はガードと選択の両方に入れる。タップ済みのクリーチャーはタップ
し直せないため「そうしたら」の条件を満たさず、候補に入れない。ガードが無いと
他の X クリーチャーが全員タップ済みの時に may だけが出る（第180弾の教訓）。
types: [creature] はタマシード等の同種族クリーチャー以外を除くため。
exclude: {ref: self} は「他の」を表す（第180弾と同型）。
"""
from pathlib import Path

import yaml
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()
PROTOS = ("T446", "T447", "T448", "T449", "T450")


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def _fb_trigger(face):
    """クリーチャー面のフレンド・バースト誘発（CIP）。"""
    trig = [a for a in face.abilities
            if a["kind"] == "trigger"
            and a.get("when") == {"event": "move", "to": "bz", "subject": "self"}]
    assert len(trig) == 1
    return trig[0]


def test_proto_parse():
    for cid in PROTOS:
        assert parse_card(_proto_card(cid), TABLES) is not None
    t446 = parse_card(_proto_card("T446"), TABLES)
    trig = _fb_trigger(t446.faces[0])
    eff = trig["effect"][0]
    assert eff["op"] == "if"
    assert eff["then"][0]["op"] == "may"
    body = eff["then"][0]["body"]
    assert body[0] == {"op": "tap", "select": {
        "zone": "bz", "owner": "you",
        "filter": {"types": ["creature"], "race_has": "マジック", "tapped": False},
        "exclude": {"ref": "self"}, "count": 1}}
    assert body[1] == {"op": "cast_face"}
    assert parse_card(_proto_card("T448"), TABLES).faces[0].keywords == [
        "blocker", "double_breaker"]
    assert parse_card(_proto_card("T449"), TABLES).faces[0].keywords == ["blocker"]
    assert parse_card(_proto_card("T450"), TABLES).faces[0].keywords == [
        "guardman", "double_breaker"]
    t447 = parse_card(_proto_card("T447"), TABLES)
    static = [a for a in t447.faces[0].abilities if a["kind"] == "static"]
    assert any(a["mod"] == {"power": 2000} for a in static)
    t449 = parse_card(_proto_card("T449"), TABLES)
    static = [a for a in t449.faces[0].abilities if a["kind"] == "static"]
    assert any(a["mod"] == {"cost": -2} for a in static)


def _cid(e, player, defn, zone="bz"):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _tap(e, player, defn):
    """bz は共有ゾーンなので、コントローラーまで見て対象側のカードをタップする。"""
    c = _cid(e, player, defn)
    e.s.cards[c].tapped = True


def _play(e, tid, yes_no=("yes",), modes=(), max_steps=400):
    """手札から tid を出す。yes_no は yes_no 決定への回答の列（尽きたら yes）。
    modes は choose_mode への回答の列（尽きたら mode:1）。出した側の攻撃決定で
    止める（相手ターン開始まで進むとアンタップやターン終了時効果で状態が消える）。
    戻り値は出た決定種別の回数。
    """
    yes_no = list(yes_no)
    modes = list(modes)
    played = False
    seen = {"yes_no": 0, "choose_cards": 0, "choose_mode": 0}
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
        elif d["kind"] == "choose_mode":
            seen["choose_mode"] += 1
            m = modes.pop(0) if modes else 1
            e.answer([keys.index(f"mode:{m}")])
        elif d["kind"] == "yes_no":
            seen["yes_no"] += 1
            a = yes_no.pop(0) if yes_no else "yes"
            e.answer([keys.index(a)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("play did not finish")


def test_friend_burst_taps_and_casts(rules):
    """T446: 他のマジックをタップして呪文面（3ドロー）を唱える。唱えた本体は残る。"""
    e = setup(rules, {"bz": ["T446"], "hand": ["T446", "T001"],
                      "mana": ["T003", "T001", "T001", "T001", "T001", "T001"]}, {})
    other = _cid(e, 0, "T446")
    seen = _play(e, "T446")
    assert seen["yes_no"] == 1
    assert e.s.cards[other].tapped is True
    assert len(e.zlist("hand", 0)) == 4                    # 出す -1、呪文面で +3、T001 が残る
    mine = [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T446"]
    assert len(mine) == 2
    assert all(e.s.cards[c].zone == "bz" for c in mine)


def test_friend_burst_decline(rules):
    """T446: may を辞退するとタップも唱えることもしない。"""
    e = setup(rules, {"bz": ["T446"], "hand": ["T446", "T001"],
                      "mana": ["T003", "T001", "T001", "T001", "T001", "T001"]}, {})
    other = _cid(e, 0, "T446")
    seen = _play(e, "T446", yes_no=("no",))
    assert seen["yes_no"] == 1
    assert e.s.cards[other].tapped is False
    assert len(e.zlist("hand", 0)) == 1


def test_no_other_friend_no_prompt(rules):
    """T446: 他のマジックがいなければ may 自体が出ない。"""
    e = setup(rules, {"hand": ["T446", "T001"],
                      "mana": ["T003", "T001", "T001", "T001", "T001", "T001"]}, {})
    seen = _play(e, "T446")
    assert seen["yes_no"] == 0
    assert len(e.zlist("hand", 0)) == 1


def test_tapped_friend_no_prompt(rules):
    """T446: 他のマジックがタップ済みなら may は出ない（タップし直せない）。
    ターン開始アンタップの後にタップすること（setup 直後だと消える）。"""
    e = setup(rules, {"bz": ["T446"], "hand": ["T446", "T001"],
                      "mana": ["T003", "T001", "T001", "T001", "T001", "T001"]}, {})
    d = e.advance()
    assert d["kind"] == "charge"
    _tap(e, 0, "T446")
    keys = [o["key"] for o in d["options"]]
    e.answer([keys.index("pass")])
    seen = _play(e, "T446")
    assert seen["yes_no"] == 0
    assert len(e.zlist("hand", 0)) == 1


def test_two_friends_choose_one(rules):
    """T446: 他のマジックが2体いれば1体を選んでタップする。選ばれなかった方は残る。"""
    e = setup(rules, {"bz": ["T446", "T446"], "hand": ["T446", "T001"],
                      "mana": ["T003", "T001", "T001", "T001", "T001", "T001"]}, {})
    others = [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T446"]
    seen = _play(e, "T446")
    assert seen["choose_cards"] >= 1
    tapped = [c for c in others if e.s.cards[c].tapped]
    assert len(tapped) == 1
    assert len(e.zlist("hand", 0)) == 4


def test_opponent_friend_not_tapped(rules):
    """T446: 相手のマジックは「自分の他の」ではないので may は出ない。"""
    e = setup(rules, {"hand": ["T446", "T001"],
                      "mana": ["T003", "T001", "T001", "T001", "T001", "T001"]},
              {"bz": ["T446"]})
    opp = _cid(e, 1, "T446")
    seen = _play(e, "T446")
    assert seen["yes_no"] == 0
    assert e.s.cards[opp].tapped is False
    assert len(e.zlist("hand", 0)) == 1


def test_armored_static_and_spell(rules):
    """T447: 他のアーマードをタップして呪文面（1捨て2ドロー）。他のファイアー・
    バード +2000 は互いに掛かり、2体とも 4000 になる。"""
    e = setup(rules, {"bz": ["T447"], "hand": ["T447", "T001"],
                      "mana": ["T431", "T001", "T001", "T001"]}, {})
    other = _cid(e, 0, "T447")
    _play(e, "T447")
    assert e.s.cards[other].tapped is True
    mine = [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T447"]
    assert len(mine) == 2
    assert all(e.chars(c)["power"] == 4000 for c in mine)
    assert len(e.zlist("hand", 0)) == 2                    # 出す -1、捨て -1、引く +2
    gy = e.zlist("graveyard", 0)
    assert len(gy) == 1 and e.s.cards[gy[0]].defn == "T001"


def test_mecha_modal_spell(rules):
    """T448: 他のメカをタップして呪文面。自分のクリーチャー2体につき modal を
    2回：1回目は相手をタップ、2回目は1ドロー。"""
    e = setup(rules, {"bz": ["T448"], "hand": ["T448", "T001"],
                      "mana": ["T004", "T001", "T001", "T001", "T001", "T001",
                               "T001", "T001"]},
              {"bz": ["T007"]})
    other = _cid(e, 0, "T448")
    opp = _cid(e, 1, "T007")
    seen = _play(e, "T448", modes=(0, 1))
    assert seen["choose_mode"] == 2
    assert e.s.cards[other].tapped is True
    assert e.s.cards[opp].tapped is True
    assert len(e.zlist("hand", 0)) == 2                    # 出す -1、modal のドロー +1、T001 が残る


def test_snow_fairy_graveyard_spell(rules):
    """T449: 他のスノーフェアリーをタップして呪文面。墓地の T450（ジャイアント・
    スノーフェアリー）を出し、このターン スピードアタッカーを与える。出した
    T450 の CIP（ジャイアント）は他のジャイアントが無いので出ない。"""
    e = setup(rules, {"bz": ["T449"], "hand": ["T449", "T001"], "graveyard": ["T450"],
                      "mana": ["T004", "T003", "T001", "T001", "T001", "T001",
                               "T001"]}, {})
    other = _cid(e, 0, "T449")
    _play(e, "T449")
    assert e.s.cards[other].tapped is True
    t450 = _cid(e, 0, "T450")
    assert e.s.cards[t450].zone == "bz"
    assert "speed_attacker" in e.chars(t450)["keywords"]
    assert len(e.zlist("graveyard", 0)) == 0


def test_giant_spell_power_and_decline_battle(rules):
    """T450: 他のジャイアントをタップして呪文面。自分のクリーチャー1体に +4000
    し、バトルの may は辞退する。相手はタップされない。"""
    e = setup(rules, {"bz": ["T450"], "hand": ["T450", "T001"],
                      "mana": ["T001", "T001", "T001", "T001", "T001", "T001",
                               "T001"]},
              {"bz": ["T007"]})
    other = _cid(e, 0, "T450")
    opp = _cid(e, 1, "T007")
    _play(e, "T450", yes_no=("yes", "no"))
    assert e.s.cards[other].tapped is True
    mine = [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T450"]
    assert sorted(e.chars(c)["power"] for c in mine) == [7000, 11000]
    assert e.s.cards[opp].tapped is False
    assert len(e.zlist("hand", 0)) == 1
