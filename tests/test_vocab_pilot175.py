"""語彙パイロット第175弾: accel（アクセル）。

「アクセル（このクリーチャーにクロスギアがクロスされている時、このクリーチャーは
次の能力を得る）」— クロスギアがクロスされている間だけ、書かれた能力を得る。

- 能力フラグ `accel: true`（defs ABILITY_KEYS。true だけ。sforce / fort_e /
  odrive と同型のゲート）。`core.abilities()` が `_accel_active`（この
  クリーチャーにクロスされているギアがあるか。状態だけを見るので chars() の
  評価中でも再帰しない）で絞る。static / trigger / replace のいずれの種別にも
  付けられる。
- 静的形は既存の mod（power / grant / add_races）で書く。誘発形は既存の when
  （attack / attack_end の blocked: false / move の destroy 置換 / break 置換）
  で書く。
- proto T382（静的パワー＋スピードアタッカー・dm28-097型）/ T383（静的パワー
  ＋種族追加・dm15-037型）/ T384（攻撃時ドロー・dmpcd02-a10型）/ T385
  （ブロックされなかった時バウンス・dm28-083型）/ T386（ブロックされない＋
  破壊身代わり・dm15-009型）/ T387（ブレイク置換でマナへ・dm15-018型）。
  試験ギアは T100（ホストのパワー・キーワードに影響しない）。
"""
import pytest
import yaml
from pathlib import Path

from conftest import answer, setup

from dmsim.defs import DefError, load_tables, parse_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent
IDS = ("T382", "T383", "T384", "T385", "T386", "T387")
GEAR = "T100"


def _proto_card(cid):
    with open(ROOT / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)
    assert _proto_card("T382")["abilities"][0]["accel"] is True
    assert _proto_card("T382")["abilities"][0]["mod"] == {"power": 3000, "grant": ["speed_attacker"]}
    assert _proto_card("T383")["abilities"][0]["mod"] == {"power": 3000, "add_races": ["エンジェル・コマンド"]}
    assert _proto_card("T384")["abilities"][0]["when"] == {"event": "attack", "subject": "self"}
    assert _proto_card("T385")["abilities"][0]["when"] == {"event": "attack_end", "subject": "self", "target": "player", "blocked": False}
    assert _proto_card("T386")["abilities"][1]["when"] == {"event": "move", "from": "bz", "to": "graveyard", "reason": "destroy", "subject": "self"}
    assert _proto_card("T387")["abilities"][0]["when"] == {"event": "break", "subject": "self"}


def test_bad_forms_rejected():
    base = _proto_card("T382")
    for bad_val in ("yes", False, 1):
        bad = dict(base)
        bad["abilities"] = [dict(base["abilities"][0], accel=bad_val)]
        with pytest.raises(DefError):
            parse_card(bad, TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _cross(e, gear_defn, host_defn, player=0):
    """gear_defn のギアを host_defn のクリーチャーにクロスさせる（直接の紐付け）。"""
    e.s.cards[_bz(e, player, gear_defn)].crossed = e.s.ref(_bz(e, player, host_defn))


def _find(e, p, defn):
    """そのプレイヤーのカードをゾーンを問わず探す（手札へ戻った後などの確認用）。"""
    return next(i for i, c in enumerate(e.s.cards) if c.defn == defn and c.controller == p)


def _attack_player(e, attacker_defn):
    """attack 決定まで進み（charge / main は pass）、attacker をプレイヤーへ攻撃させる。
    手札が空だと charge / main は一意選択肢で自動回答されるため、決定種別を見て進める。"""
    for _ in range(20):
        d = e.advance()
        assert d is not None, "game ended before attack"
        if d["kind"] == "attack":
            keys = _keys(d)
            e.answer([keys.index(f"attack:{attacker_defn}:player")])
            return
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("attack decision did not appear")


def _drive_combat(e, max_steps=120):
    """攻撃の解決が終わる（次の charge / main / attack 決定かゲーム終了）まで進める。
    yes_no には yes、choose には先頭から min 個、declare_strigger は空で答える。"""
    for _ in range(max_steps):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            return d
        keys = _keys(d)
        if d["kind"] == "yes_no":
            e.answer([keys.index("yes")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif d["kind"] == "pay_mana":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("combat did not settle")


def _destroy_and_answer_may(e, c):
    # 待機中 Decision の回答は、積んだタスクが終わってから消費される。破壊で選択肢が
    # 変わる Decision（attack 等）では回答 index が陳腐化するため、破壊は手札に
    # 影響しない相手の charge Decision で待っている状態で呼ぶこと（第173弾の流儀）。
    if e.s.waiting is not None:
        d = e.s.waiting
        e.answer([_keys(d).index("pass")] if "pass" in _keys(d) else 0)
    e._push(e.ev_task({"ev": "move", "subject": e.s.ref(c), "to": "graveyard", "reason": "destroy"}))
    for _ in range(60):
        d = e.advance()
        if d is None:
            break
        if d["kind"] == "yes_no":
            e.answer([_keys(d).index("yes")])
            continue
        if d["kind"] in ("charge", "main", "attack"):
            break
        e.answer([0])


def test_static_power_and_speed_attacker(rules):
    """T382: ギアが無ければパワー2000・召喚酔いあり。クロスすれば+3000と
    スピードアタッカーを得て、出たターンに攻撃できる。"""
    e = setup(rules, {"bz": ["T382", GEAR]}, {"bz": ["T001"]})
    c = _bz(e, 0, "T382")
    assert e.chars(c)["power"] == 2000
    assert "speed_attacker" not in e.chars(c)["keywords"]
    e.s.cards[c].entered_turn = e.s.turn  # このターンに出たことにする（召喚酔い）
    assert "attack:T382:player" not in [o["key"] for o in e._attack_options(0)]
    _cross(e, GEAR, "T382")
    assert e.chars(c)["power"] == 5000
    assert "speed_attacker" in e.chars(c)["keywords"]
    assert "attack:T382:player" in [o["key"] for o in e._attack_options(0)]


def test_static_add_race(rules):
    """T383: クロスしている間だけパワー+3000と種族エンジェル・コマンド追加。"""
    e = setup(rules, {"bz": ["T383", GEAR]}, {})
    c = _bz(e, 0, "T383")
    assert e.chars(c)["power"] == 2000
    assert "エンジェル・コマンド" not in e.chars(c)["races"]
    _cross(e, GEAR, "T383")
    assert e.chars(c)["power"] == 5000
    assert "エンジェル・コマンド" in e.chars(c)["races"]
    assert "イニシエート" in e.chars(c)["races"]


def test_attack_trigger_draw(rules):
    """T384: クロスしていれば攻撃時に1枚引く。していなければ引かない。"""
    e = setup(rules, {"bz": ["T384", GEAR]}, {})
    e.s.cards[_bz(e, 0, "T384")].entered_turn = -1
    _cross(e, GEAR, "T384")
    hand_before = len(e.zlist("hand", 0))
    _attack_player(e, "T384")
    _drive_combat(e)
    assert len(e.zlist("hand", 0)) == hand_before + 1
    e = setup(rules, {"bz": ["T384", GEAR]}, {})
    e.s.cards[_bz(e, 0, "T384")].entered_turn = -1
    hand_before = len(e.zlist("hand", 0))
    _attack_player(e, "T384")
    _drive_combat(e)
    assert len(e.zlist("hand", 0)) == hand_before


def test_unblocked_bounce(rules):
    """T385: クロスしていれば、ブロックされなかった攻撃の終わりに自分よりパワーの
    小さい相手クリーチャーを手札に戻せる。していなければ戻らない。"""
    e = setup(rules, {"bz": ["T385", GEAR]}, {"bz": ["T002"]})
    e.s.cards[_bz(e, 0, "T385")].entered_turn = -1
    _cross(e, GEAR, "T385")
    _attack_player(e, "T385")
    _drive_combat(e)
    assert e.s.cards[_find(e, 1, "T002")].zone == "hand"
    e = setup(rules, {"bz": ["T385", GEAR]}, {"bz": ["T002"]})
    e.s.cards[_bz(e, 0, "T385")].entered_turn = -1
    _attack_player(e, "T385")
    _drive_combat(e)
    assert e.s.cards[_find(e, 1, "T002")].zone == "bz"


def test_destroy_replace_sacrifices_gear(rules):
    """T386: クロスしていればブロックされず、破壊される時にギア1枚を墓地に置く
    ことで身代わりになる。していなければ普通に破壊される。"""
    e = setup(rules, {"bz": ["T386", GEAR]}, {})
    _cross(e, GEAR, "T386")
    c = _bz(e, 0, "T386")
    g = _bz(e, 0, GEAR)
    assert "unblockable" in e.chars(c)["keywords"]
    _destroy_and_answer_may(e, c)
    assert e.s.cards[c].zone == "bz"
    assert e.s.cards[g].zone == "graveyard"
    e = setup(rules, {"bz": ["T386"]}, {})
    c = _bz(e, 0, "T386")
    assert "unblockable" not in e.chars(c)["keywords"]
    _destroy_and_answer_may(e, c)
    assert e.s.cards[c].zone == "graveyard"


def test_break_replace_to_mana(rules):
    """T387: クロスしていれば、ブレイクしたシールドは相手の手札ではなく相手の
    マナゾーンに置かれる。していなければ手札に行く。"""
    e = setup(rules, {"bz": ["T387", GEAR]}, {})
    e.s.cards[_bz(e, 0, "T387")].entered_turn = -1
    _cross(e, GEAR, "T387")
    hand_before = len(e.zlist("hand", 1))
    mana_before = len(e.s.zones["mana"][1])
    _attack_player(e, "T387")
    _drive_combat(e)
    assert len(e.s.zones["shield"][1]) == 3  # W・ブレイカーで2枚ブレイク
    assert len(e.s.zones["mana"][1]) == mana_before + 2
    assert len(e.zlist("hand", 1)) == hand_before + 1  # +1 は相手ターンの開始ドローだけ
    e = setup(rules, {"bz": ["T387", GEAR]}, {})
    e.s.cards[_bz(e, 0, "T387")].entered_turn = -1
    hand_before = len(e.zlist("hand", 1))
    mana_before = len(e.s.zones["mana"][1])
    _attack_player(e, "T387")
    _drive_combat(e)
    assert len(e.s.zones["shield"][1]) == 3
    assert len(e.s.zones["mana"][1]) == mana_before
    assert len(e.zlist("hand", 1)) == hand_before + 3  # ブレイク2枚＋相手ターンの開始ドロー
