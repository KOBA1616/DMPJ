"""第218弾の登録カード（ラウンド254）の確認。

- 7枚が converted.yaml の登録形で parse できる（dmr04-003 / dmex18-023 は差し戻し）
- dmx19-s14: 出た時、下のカード1枚につき1体まで手札に戻す
- dmr04-015: 各ターンのはじめに、そのターンのプレイヤーが自身の多色でない
  クリーチャーを1体破壊する（相手ターン分は相手が選ぶ）
- dmr08-001: 超無限進化Ω（墓地・マナ・場の無色を積む）＋攻撃時モード
- dmr08-007: 攻撃時に下のカードをシールド化し、そのターンの終わりにアンタップ
- dmrp21-tr3: 5文明カバーの超無限進化＋メテオバーンで多色を出す/唱える
- dmx15-v02: 攻撃時、このクリーチャーよりパワーが小さい相手をすべて破壊
- dmex17-012: ドラゴン進化で召喚し、メテオバーン（合計20以上）で追加ターン
"""
import os
from pathlib import Path

import pytest

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.scenario import build  # noqa: E402
import tests._conv_cache as _conv_cache  # noqa: E402

TABLES = load_tables()
CONVERTED = Path(__file__).parent.parent / "data" / "cards" / "converted.yaml"
IDS = ("dmex17-012", "dmr04-015", "dmr08-001", "dmr08-007",
       "dmrp21-tr3", "dmx15-v02", "dmx19-s14")


@pytest.fixture(scope="module")
def converted():
    return {c["id"]: c for c in _conv_cache.all_cards(str(CONVERTED))}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_build_forms_parse(converted):
    for cid in IDS:
        assert cid in converted, cid
        parse_card(converted[cid], TABLES)


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _run(e, play=None, evo=None, choose=None, attack=None, stop=None, max_iter=4000):
    """play: 出す play:キー。evo/choose: 決定 dict を受けて index 列を返す関数。
    attack: (turn, defn) で攻撃するプレイヤー攻撃キー。stop: 終了述語。"""
    st = {"played": False}
    for _ in range(max_iter):
        if stop and stop(e):
            break
        if e.s.result is not None:
            break
        d = e.advance()
        if d is None:
            break
        kind, p = d["kind"], d.get("player")
        keys = [o["key"] for o in d["options"]]
        if kind == "main" and play and not st["played"] and play in keys:
            st["played"] = True
            e.answer([keys.index(play)])
        elif kind == "choose_evo_source" and evo:
            e.answer(evo(e, d))
        elif kind == "pay_mana":
            e.answer([0])
        elif kind == "yes_no":
            e.answer([0])
        elif kind == "choose_cards" and choose:
            e.answer(choose(e, d))
        elif kind == "choose_mode":
            e.answer([0])
        elif kind == "attack" and attack and p == 0:
            turn, defn = attack
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{defn}:player" and e.s.turn == turn]
            e.answer([hit[0]] if hit else [keys.index("pass")] if "pass" in keys else list(range(d["min"])))
        elif kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif kind == "declare_attack":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return st


def test_fatal_spiral_cip_bounces_per_under(rules):
    e = build(rules, {"p0": {"hand": ["dmx19-s14"], "bz": ["T063", "T064"],
                             "mana": ["T063"] + ["T001"] * 6},
                      "p1": {"bz": ["T001", "T002"]}, "filler": "T002"})
    targets = {c for c in e.zlist("bz", 0) if e.s.cards[c].owner == 1}

    def choose(e, d):
        want = [i for i, o in enumerate(d["options"]) if o["cid"] in targets]
        return want[:1] if want else list(range(d["min"]))

    _run(e, play="play:dmx19-s14", evo=lambda e, d: list(range(len(d["options"]))),
         choose=choose, stop=lambda e: {"T001", "T002"} <= set(_defns(e, "hand", 1)))
    # 下のカード2枚ぶん、相手の2体が手札に戻る
    assert set(_defns(e, "hand", 1)) >= {"T001", "T002"}
    assert [c for c in e.zlist("bz", 0) if e.s.cards[c].owner == 1] == []


def test_ortros_each_turn_player_destroys(rules):
    e = build(rules, {"p0": {"bz": ["dmr04-015", "T001"]},
                      "p1": {"bz": ["T002", "T004"]}, "filler": "T002"})
    _run(e, stop=lambda e: "T001" in _defns(e, "graveyard", 0)
         and len(e.zlist("graveyard", 1)) == 1)
    # 自分のターンのはじめに T001（多色でない自軍）を破壊。オルトロス自身は多色で対象外
    assert "T001" in _defns(e, "graveyard", 0)
    assert "dmr04-015" in _defns(e, "bz", 0)
    # 相手のターンのはじめに、相手が自分の多色でない1体を選んで破壊する
    assert len(e.zlist("graveyard", 1)) == 1
    assert len([c for c in e.zlist("bz", 0) if e.s.cards[c].owner == 1]) == 1


def test_iggy_omega_and_attack_modal(rules):
    e = build(rules, {"p0": {"hand": ["dmr08-001"], "bz": ["dm24ex2-081"],
                             "graveyard": ["dm23ex2-090"],
                             "mana": ["dm24bd2-016", "dm24ex3-tf39"] + ["T001"] * 12},
                      "p1": {"bz": ["T001"]}, "filler": "T002"})
    top = e.zlist("hand", 0)[0]
    srcs = {e.zlist("bz", 0)[0], e.zlist("graveyard", 0)[0],
            next(c for c in e.zlist("mana", 0) if e.s.cards[c].defn == "dm24bd2-016")}
    victim = next(c for c in e.zlist("bz", 0)
                  if e.s.cards[c].owner == 1 and e.s.cards[c].defn == "T001")

    def evo(e, d):
        return [i for i, o in enumerate(d["options"]) if o["cid"] in srcs]

    _run(e, play="play:dmr08-001", evo=evo, attack=(3, "dmr08-001"),
         stop=lambda e: e.s.cards[victim].zone == "mana")
    assert set(e.s.cards[top].under) == srcs
    assert e.s.cards[victim].zone == "mana" and e.s.cards[victim].owner == 1


def test_tatebue_shieldize_and_untap(rules):
    e = build(rules, {"p0": {"hand": ["dmr08-007"], "bz": ["T001", "T002"],
                             "mana": ["T004"] + ["T001"] * 4},
                      "p1": {}, "filler": "T002"})
    top = e.zlist("hand", 0)[0]
    shields0 = len(e.zlist("shield", 0))
    _run(e, play="play:dmr08-007", evo=lambda e, d: [0, 1], attack=(3, "dmr08-007"),
         stop=lambda e: e.s.turn >= 4)
    assert len(e.zlist("shield", 0)) == shields0 + 1      # 下のカードが新しいシールドに
    assert len(e.s.cards[top].under) == 1
    assert e.s.cards[top].tapped is False                # ターンの終わりにアンタップした


def test_orchestra_cover_and_meteor(rules):
    e = build(rules, {"p0": {"hand": ["dmrp21-tr3"],
                             "bz": ["T004", "T063", "T008", "T064", "T001"],
                             "mana": ["T004", "T063", "T008", "T556", "T001"],
                             "deck": ["T002", "dm24ex1-088", "dm10-068", "T004", "T063"]},
                      "p1": {}, "filler": "T002"})
    picked = []

    def evo(e, d):
        have = {e.chars(c)["civs"][0] for c in picked}
        if {"light", "water", "darkness", "fire", "nature"} <= have:
            return []
        for i, o in enumerate(d["options"]):
            if e.chars(o["cid"])["civs"][0] not in have:
                picked.append(o["cid"])
                return [i]
        return []

    def choose(e, d):
        if d["max"] > 1:
            return list(range(len(d["options"])))
        return [0] if d["options"] else []

    _run(e, play="play:dmrp21-tr3", evo=evo, choose=choose, attack=(3, "dmrp21-tr3"),
         stop=lambda e: e.s.turn >= 4)
    tops = [e.s.cards[c].defn for c in e.zlist("bz", 0) if e.s.cards[c].top_of < 0]
    assert "dm10-068" in tops                             # 多色クリーチャーを出した
    assert "dm24ex1-088" in _defns(e, "graveyard", 0)     # 多色呪文を唱えた
    deck = _defns(e, "deck", 0)
    assert deck[-1] == "T002"                             # 残りは山札の一番下


def test_guyr_attack_wipes_smaller(rules):
    e = build(rules, {"p0": {"bz": ["dmx15-v02"]},
                      "p1": {"bz": ["T001", "T063"]}, "filler": "T002"})
    _run(e, attack=(1, "dmx15-v02"), stop=lambda e: e.s.turn >= 2)
    assert set(_defns(e, "graveyard", 1)) == {"T001", "T063"}


def test_storm_summon_and_meteor_extra_turn(rules):
    e = build(rules, {"p0": {"hand": ["dmex17-012"], "bz": ["dm01-s08", "dm10-006", "dm14-b01"],
                             "mana": ["T063", "T064", "T065"] + ["T001"] * 11},
                      "p1": {}, "filler": "T002"})
    charge_players = {}

    def choose(e, d):
        return list(range(len(d["options"])))

    orig_advance = e.advance
    seen = {"turns": []}

    def stop(e):
        return e.s.turn >= 5

    st = {"played": False}
    for _ in range(4000):
        if e.s.turn >= 5 or e.s.result is not None:
            break
        d = e.advance()
        if d is None:
            break
        if d["kind"] == "charge":
            charge_players[e.s.turn] = d["player"]
        kind, keys = d["kind"], [o["key"] for o in d["options"]]
        if kind == "main" and not st["played"] and "play:dmex17-012" in keys:
            st["played"] = True
            e.answer([keys.index("play:dmex17-012")])
        elif kind == "choose_evo_source":
            e.answer(list(range(len(d["options"]))))
        elif kind == "pay_mana":
            e.answer([0])
        elif kind == "yes_no":
            e.answer([0])
        elif kind == "choose_cards":
            e.answer(choose(e, d))
        elif kind == "attack" and d["player"] == 0 and e.s.turn == 3:
            hit = [i for i, k in enumerate(keys) if k == "attack:dmex17-012:player"]
            e.answer([hit[0]] if hit else [keys.index("pass")])
        elif kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif kind == "declare_attack":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    # メテオバーン: 下の3枚（7+9+6=22 >= 20）を墓地に置いたので追加ターン
    assert charge_players.get(3) == 0 and charge_players.get(4) == 0
    top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "dmex17-012")
    assert e.s.cards[top].under == []
