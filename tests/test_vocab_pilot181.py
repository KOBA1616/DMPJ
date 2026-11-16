"""語彙パイロット第181弾: lost_prism（ロスト・プリズム）。

「このクリーチャーをバトルゾーンに出した時、自分の山札の上から１枚目を表向きに
してもよい。それが多色カードであれば、手札に加える」を、既存 op reveal_until
の拡張で表す。reveal_until に limit（公開する合計枚数の上限。式）を追加し、
limit: 1, count: 1, filter: {multicolor: true} で「上から1枚だけ公開し、
多色なら hit に束縛する」と書く。合わなかった公開分（rest）は山札に残るので
移動しない。limit が無ければ従来どおり「合うカードが count 枚出るまで」公開
し続ける。任意性は {op: may, body: [...]}（誘発の optional は置換の辞退に
しか効かない。第179弾の教訓）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()
PROTOS = ("T413", "T414", "T415", "T416", "T417")


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in PROTOS:
        assert parse_card(_proto_card(cid), TABLES) is not None
    t413 = parse_card(_proto_card("T413"), TABLES)
    op0 = t413.abilities[0]["effect"][0]["body"][0]
    assert op0["op"] == "reveal_until" and op0["limit"] == 1
    assert op0["filter"] == {"multicolor": True} and op0["as"] == "hit"
    assert parse_card(_proto_card("T414"), TABLES).keywords == ["speed_attacker"]
    assert parse_card(_proto_card("T416"), TABLES).keywords == ["s_trigger"]


def test_invalid_reveal_until_limit():
    base = {"id": "test-lp-bad", "name": "試験公開不良", "types": ["spell"],
            "civs": ["water"], "cost": 3,
            "source": {"official": "test-lp-bad", "review": "pending"}}
    for bad in ({"op": "reveal_until", "filter": {"types": ["creature"]},
                 "as": "hit", "limit": "x"},
                {"op": "reveal_until", "filter": {"types": ["creature"]},
                 "as": "hit", "limit": {"bogus": 1}}):
        with pytest.raises(DefError):
            parse_card({**base, "spell": [bad]}, TABLES)


def _cid(e, player, defn, zone="bz"):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _arrange_deck(e, p, top_defns):
    """山札の上から top_defns の順に並べ替え、その cid リストを返す。"""
    rest = list(e.s.zones["deck"][p])
    chosen = []
    for dfn in top_defns:
        c = next(c for c in rest if e.s.cards[c].defn == dfn)
        rest.remove(c)
        chosen.append(c)
    e.s.zones["deck"][p] = chosen + rest
    return chosen


def _play(e, tid, max_steps=400, yes_no="yes"):
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
            return   # 出した側のメインが終わった = CIP まで解決済み
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


def test_hit_multicolor_to_hand(rules):
    """T413: 上が多色なら手札に加わり、その下は山札に残る。"""
    e = setup(rules, {"hand": ["T413"], "mana": ["T004", "T001", "T001", "T001"],
                      "deck": ["T030", "T001"]}, {})
    top, below = _arrange_deck(e, 0, ["T030", "T001"])
    _play(e, "T413", yes_no="yes")
    assert e.s.cards[top].zone == "hand"
    assert e.s.cards[below].zone == "deck"
    assert e.s.zones["deck"][0][0] == below   # 下のカードが一番上になる


def test_miss_stops_after_one(rules):
    """T413: 上が単色なら何も手札に行かず、2枚目（多色）は公開されない。
    limit が無ければ reveal_until は多色が出るまで公開し続けてしまう。"""
    e = setup(rules, {"hand": ["T413"], "mana": ["T004", "T001", "T001", "T001"],
                      "deck": ["T001", "T030"]}, {})
    top, second = _arrange_deck(e, 0, ["T001", "T030"])
    _play(e, "T413", yes_no="yes")
    assert e.s.cards[top].zone == "deck"
    assert e.s.zones["deck"][0][0] == top   # 1枚目がそのまま一番上
    assert e.s.cards[second].zone == "deck"   # 2枚目は手札に行かない
    assert len(e.zlist("hand", 0)) == 0


def test_decline_reveals_nothing(rules):
    """T413: may を辞退すれば何も公開されず、上が多色でも手札に行かない。"""
    e = setup(rules, {"hand": ["T413"], "mana": ["T004", "T001", "T001", "T001"],
                      "deck": ["T030", "T001"]}, {})
    top, _below = _arrange_deck(e, 0, ["T030", "T001"])
    _play(e, "T413", yes_no="no")
    assert e.s.cards[top].zone == "deck"
    assert e.s.zones["deck"][0][0] == top
    assert len(e.zlist("hand", 0)) == 0


def test_single_card_deck_miss(rules):
    """T413: 山札が1枚だけでも CIP は無事に終わる。単色の1枚目は山札に残る。
    （山札0枚は SBA で即敗北するため、空の山札での CIP はこのエンジンでは
    試験できない。第163弾の山札切れ試験と同型の境界条件。）"""
    e = setup(rules, {"hand": ["T413"], "mana": ["T004", "T001", "T001", "T001"],
                      "deck": ["T001"]}, {}, deck_left=[1, None])
    assert len(e.s.zones["deck"][0]) == 1
    only = e.s.zones["deck"][0][0]
    assert e.s.cards[only].defn == "T001"
    _play(e, "T413", yes_no="yes")
    assert len(e.zlist("hand", 0)) == 0
    assert e.s.cards[only].zone == "deck"
    assert e.s.zones["deck"][0][0] == only
    assert e.s.cards[_cid(e, 0, "T413")].zone == "bz"


def test_speed_attacker_and_turn_end_untap(rules):
    """T414: ロスト・プリズムで多色が手札へ。スピードアタッカーで出たターンに
    攻撃でき、攻撃でタップされても自分のターンの終わりにアンタップする。"""
    e = setup(rules, {"hand": ["T414"], "mana": ["T004", "T005", "T001", "T001", "T001", "T001"],
                      "deck": ["T030", "T001"]}, {})
    top, _below = _arrange_deck(e, 0, ["T030", "T001"])
    _play(e, "T414", yes_no="yes")
    t414 = _cid(e, 0, "T414")
    assert e.s.cards[top].zone == "hand"
    attacked = False
    for _ in range(600):
        if e.s.active == 1 and not e.s.cards[t414].tapped:
            break   # ターンが相手に渡り、アンタップ済み
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack" and not attacked:
            assert "attack:T414:player" in keys   # 出たターンに攻撃可
            e.answer([keys.index("attack:T414:player")])
            attacked = True
        elif kind == "attack":
            e.answer([keys.index("pass")])
        elif kind == "choose_shields":
            e.answer([0])   # T414 は1ブレイク。先頭のシールドをブレイクする
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif kind == "choose_breaker":
            e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
        elif kind in ("charge", "main"):
            e.answer([keys.index("pass")])
        elif kind == "yes_no":
            e.answer([keys.index("yes")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert attacked
    assert e.s.active == 1
    assert not e.s.cards[t414].tapped   # ターン終了時アンタップ


def test_s_trigger_lost_prism_hit(rules):
    """T416: S・トリガー付きでもロスト・プリズムは同じ形で働く。"""
    e = setup(rules, {"hand": ["T416"], "mana": ["T005", "T001", "T001", "T001", "T001"],
                      "deck": ["T030", "T001"]}, {})
    top, below = _arrange_deck(e, 0, ["T030", "T001"])
    _play(e, "T416", yes_no="yes")
    assert e.s.cards[top].zone == "hand"
    assert e.s.cards[below].zone == "deck"


def _destroy_with_spell(e, target_defn, choose_pick=None, stop=None, max_steps=600):
    """手札の T307（クリーチャー1体を破壊）で target_defn を破壊する。
    置換は replace を選び、探索の choose_cards には choose_pick があれば使う。
    stop() が真になったら止まる。"""
    played = False
    for _ in range(max_steps):
        if stop is not None and stop():
            return True
        d = e.advance()
        if d is None:
            return stop() if stop is not None else False
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "main" and not played and "play:T307" in keys:
            played = True
            e.answer([keys.index("play:T307")])
            continue
        if kind == "pay_mana":
            e.answer([0])
        elif kind == "choose_cards":
            if choose_pick is not None:
                e.answer(choose_pick(d))
            else:
                idx = [i for i, o in enumerate(d["options"])
                       if o.get("cid") is not None
                       and e.s.cards[o["cid"]].defn == target_defn]
                assert idx, f"target {target_defn} not in {keys}"
                e.answer(idx[:d["min"]])
        elif kind == "choose_replacement":
            rep = [i for i, k in enumerate(keys) if k.startswith("replace:")]
            e.answer([rep[0]] if rep else [keys.index("decline")])
        elif kind == "yes_no":
            e.answer([keys.index("yes")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return stop() if stop is not None else False


def test_destroy_replacement_to_hand(rules):
    """T415: 破壊される時、墓地に置くかわりに手札に戻る。"""
    e = setup(rules, {"bz": ["T415"], "hand": ["T307"], "mana": ["T005", "T063", "T001", "T001", "T001", "T001", "T001"]}, {})
    t415 = _cid(e, 0, "T415")
    assert _destroy_with_spell(e, "T415", stop=lambda: e.s.cards[t415].zone == "hand")
    assert e.s.cards[t415].zone == "hand"


def test_on_destroy_search_to_bz(rules):
    """T417: 破壊された時、山札から自然または水のコスト3以下のクリーチャーを
    2体まで選び、バトルゾーンに出す。残りの山札はシャッフルされる。"""
    e = setup(rules, {"bz": ["T417"], "hand": ["T307"], "mana": ["T005", "T063", "T001", "T001", "T001", "T001", "T001"],
                      "deck": ["T001", "T063"]}, {})
    t417 = _cid(e, 0, "T417")
    picked = {}

    def pick_search(d):
        defns = [e.s.cards[o["cid"]].defn for o in d["options"]
                 if o.get("cid") is not None]
        if "T417" in defns:
            return [defns.index("T417")]
        # 探索の選択: T001 を1体と T063 を1体
        idx = []
        if "T001" in defns:
            idx.append(defns.index("T001"))
        if "T063" in defns:
            idx.append(defns.index("T063"))
        picked["cids"] = [d["options"][i]["cid"] for i in idx]
        return idx

    done = _destroy_with_spell(
        e, "T417", choose_pick=pick_search,
        stop=lambda: picked.get("cids") and all(
            e.s.cards[c].zone == "bz" for c in picked["cids"]))
    assert done
    assert e.s.cards[t417].zone == "graveyard"
    assert len(picked["cids"]) == 2
