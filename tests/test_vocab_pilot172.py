"""語彙パイロット第172弾: recycle（リサイクル）。

「リサイクル N（この呪文を墓地からコストNを支払って唱えてもよい。そうして唱えた
後、墓地に置くかわりに自分の山札の一番下に置く）」と「リサイクル [ll04]（この呪文
を自分の墓地から「リサイクル」コストを支払って唱えてもよい。こうして唱えた後、
墓地のかわりに山札の下に置く）」の2形。

- 面フィールド `recycle: {cost, civs?}`（civs 省略時はカード自身の文明。
  alt_cost と同じ支払い規約）。`[ll04]` は cost 6＋civs [light, light]
  （光マナ2枚を含む6マナ）と読む。
- 墓地からの唱えはメインステップの選択肢 `play:<id>:recycle`（払えなければ出ない）。
  唱えは通常の play タスク（cost_override＝リサイクルコスト）で、解決後の行き先
  だけ `resolve_to: deck, resolve_position: bottom` に変える。
- 手札からの通常唱え・アタック・チャンスの無料唱え（play_free）は recycle の印
  が付かないので、解決後は従来どおり墓地へ行く（干渉しない）。

置換 idiom（第169弾の zone: hold の replace）を使わなかった理由: 置換は「墓地
から唱えて墓地へ行く」移動すべてに反応するため、リサイクル以外の経路（play_free
等）で墓地から唱えた時にも山札の下へ行ってしまい、テキストの「そうして唱えた後」
（リサイクルで唱えた時に限る）と合わない。タスクの印で行き先を変える方式なら、
リサイクル選択肢で唱えた時にだけ行き先が変わる。
"""
from pathlib import Path

import pytest
import yaml
from conftest import answer, setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()

IDS = ("T365", "T366", "T367", "T368")


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    t365 = parse_card(_proto_card("T365"), TABLES)
    assert t365.recycle == {"cost": 3}
    t366 = parse_card(_proto_card("T366"), TABLES)
    assert t366.recycle == {"cost": 8}
    t367 = parse_card(_proto_card("T367"), TABLES)
    assert t367.recycle == {"cost": 6, "civs": ["light", "light"]}
    decl = [a for a in t367.abilities if a["kind"] == "declare"]
    assert len(decl) == 1 and decl[0]["effect"][0]["op"] == "play_free"
    t368 = parse_card(_proto_card("T368"), TABLES)
    assert t368.recycle == {"cost": 2}


def test_invalid_forms():
    base = {"id": "test-rc-bad", "name": "試験再唱呪文不良", "types": ["spell"],
            "civs": ["water"], "cost": 2, "mana": 1,
            "spell": [{"op": "draw", "player": "you", "count": 1}],
            "source": {"official": "test-rc-bad", "review": "pending"}}
    bad_recycles = ("3", {"civs": ["water"]}, {"cost": "3"},
                    {"cost": 3, "civs": ["unknown"]}, {"cost": 3, "civs": "water"},
                    {"cost": 3, "civs": ["water", "unknown"]})
    for bad in bad_recycles:
        card = {**base, "recycle": bad}
        with pytest.raises(DefError) as e:
            parse_card(card, TABLES)
        assert "recycle" in str(e.value)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _defns(e, zone, player=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, player)]


def _deck_bottom(e, player=0):
    return e.s.cards[e.zlist("deck", player)[-1]].defn


def _drive(e, play_keys, max_steps=300):
    """決定が出るたびに方針どおりに答え、play_keys の選択肢をメイン決定で順に使い、
    使い終わってメイン／チャージ／攻撃の決定で落ち着いたら返す。最初のメイン決定で
    要求した選択肢が無ければ、その場で失敗する（払えない時の不出現もここで検出）。"""
    play_keys = list(play_keys)
    played = set()
    saw_main = False
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended before settling"
        keys = _keys(d)
        kind = d["kind"]
        if kind == "main" and d["player"] == 0:
            if not saw_main:
                saw_main = True
                missing = [k for k in play_keys if k not in keys]
                assert not missing, f"main options lack {missing}: {keys}"
            nxt = next((k for k in play_keys if k not in played and k in keys), None)
            if nxt is not None:
                played.add(nxt)
                e.answer([keys.index(nxt)])
                continue
            if played or not play_keys:
                return
        if played and kind in ("charge", "attack"):
            return
        if kind == "pay_mana":
            e.answer([0])
        elif kind in ("choose_cards", "choose_shields"):
            e.answer(list(range(d["min"])))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("did not settle")


def _main_keys(e, max_steps=60):
    """最初のメイン決定（player 0）の選択肢キー一覧を返す。チャージはパスする。
    setup 直後はマナがタップ状態なので、実決定まで進めてから見る。"""
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None
        if d["kind"] == "main" and d["player"] == 0:
            return _keys(d)
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("main step not reached")


def test_recycle_cast_goes_to_deck_bottom(rules):
    """T365: 墓地からコスト3で唱え、ドローして山札の一番下へ行く。墓地には残らない。"""
    e = setup(rules, {"graveyard": ["T365"], "mana": ["T030", "T030", "T030"]}, {})
    _drive(e, ["play:T365:recycle"])
    assert "T365" not in _defns(e, "graveyard")
    assert _deck_bottom(e) == "T365"
    assert len(_defns(e, "hand")) == 1, "ドロー1枚が解決している"
    assert all(e.s.cards[c].tapped for c in e.zlist("mana", 0)), "コスト3を払っている"


def test_recycle_not_offered_without_enough_mana(rules):
    """T365: マナ2枚ではコスト3を払えず、リサイクルの選択肢が出ない（対照）。
    手札の T003 が唱えられるのでメイン決定は出る。"""
    e = setup(rules, {"hand": ["T003"], "graveyard": ["T365"],
                      "mana": ["T030", "T030"]}, {})
    keys = _main_keys(e)
    assert "play:T003" in keys
    assert "play:T365:recycle" not in keys


def test_recycle_not_offered_from_hand(rules):
    """T365: 手札にある時は通常唱えの選択肢だけで、リサイクルの選択肢は出ない（対照）。"""
    e = setup(rules, {"hand": ["T365"], "mana": ["T030", "T030", "T030"]}, {})
    keys = _main_keys(e)
    assert "play:T365" in keys
    assert "play:T365:recycle" not in keys


def test_hand_cast_goes_to_graveyard(rules):
    """T365: 手札から通常コストで唱えると、解決後は墓地へ行く（山札の下ではない）。"""
    e = setup(rules, {"hand": ["T365"], "mana": ["T030", "T030"]}, {})
    _drive(e, ["play:T365"])
    assert "T365" in _defns(e, "graveyard")
    assert _deck_bottom(e) != "T365"


def test_recycle_big_cost(rules):
    """T366: リサイクル ⑧で唱え、マナブースト2枚が解決して山札の一番下へ行く。"""
    e = setup(rules, {"graveyard": ["T366"], "mana": ["T001"] * 8}, {})
    _drive(e, ["play:T366:recycle"])
    assert "T366" not in _defns(e, "graveyard")
    assert _deck_bottom(e) == "T366"
    assert len(e.zlist("mana", 0)) == 10, "払った8枚＋マナブースト2枚"


def test_ll04_civs_short(rules):
    """T367: 合計6マナあっても光が1枚では [ll04] を払えず、選択肢が出ない（対照）。
    手札の T003 が唱えられるのでメイン決定は出る。"""
    e = setup(rules, {"hand": ["T003"], "graveyard": ["T367"],
                      "mana": ["T030"] + ["T001"] * 5}, {})
    keys = _main_keys(e)
    assert "play:T003" in keys
    assert "play:T367:recycle" not in keys


def test_ll04_civs_enough(rules):
    """T367: 光2枚を含む6マナで [ll04] を払え、シールド化して山札の一番下へ行く。"""
    e = setup(rules, {"graveyard": ["T367"], "mana": ["T030", "T030"] + ["T001"] * 4}, {})
    _drive(e, ["play:T367:recycle"])
    assert "T367" not in _defns(e, "graveyard")
    assert _deck_bottom(e) == "T367"
    assert len(e.zlist("shield", 0)) == 6, "山札の上から1枚をシールド化した"


def test_recycle_destroy_blocker(rules):
    """T368: リサイクル ②で唱え、ブロッカーを破壊して山札の一番下へ行く。"""
    e = setup(rules, {"graveyard": ["T368"], "mana": ["T005", "T005"]},
              {"bz": ["T004"]})
    _drive(e, ["play:T368:recycle"])
    assert "T004" in _defns(e, "graveyard", 1), "ブロッカー T004 が破壊された"
    assert "T368" not in _defns(e, "graveyard")
    assert _deck_bottom(e) == "T368"


def _to_attack(e, player=0):
    """攻撃ステップの決定まで進める（チャージ／メインはパスする）。"""
    for _ in range(60):
        d = e.advance()
        assert d is not None
        if d["kind"] == "attack" and d["player"] == player:
            return d
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("attack step not reached")


def test_attack_chance_free_cast_goes_to_graveyard(rules):
    """T367: アタック・チャンスで手札から無料で唱えると、解決後は墓地へ行く。
    リサイクルの行き先（山札の下）とは干渉しない。"""
    e = setup(rules, {"bz": ["T357"], "hand": ["T367"]}, {"bz": []})
    d = _to_attack(e)
    answer(e, "attack", "attack:T357:player")
    d = e.advance()
    assert d["kind"] == "declare_attack" and d["player"] == 0
    assert any(k.startswith("declare:T367:") for k in _keys(d))
    e.answer([next(i for i, k in enumerate(_keys(d)) if k.startswith("declare:T367:"))])
    for _ in range(100):   # 攻撃を終わらせ、相手のターンに入るまで既定回答で進める
        d = e.advance()
        assert d is not None, "game ended before settling"
        if d["player"] == 1:
            break
        keys = _keys(d)
        if d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] in ("choose_cards",):
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    else:
        raise AssertionError("did not settle")
    assert "T367" in _defns(e, "graveyard"), "無料唱えの解決後は墓地へ行く"
    assert _deck_bottom(e) != "T367"
    assert len(e.zlist("shield", 0)) == 6, "シールド化が解決している"
