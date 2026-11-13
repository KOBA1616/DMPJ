"""語彙パイロット第196弾: eternal_kappa（エターナル・Κ）のイディオム確認。

「このクリーチャーが離れる時、かわりに自分のマナゾーンにある裏向きの
カードをN枚、表向きにしてもよい」は、既存の置換 machinery で表せる
（新規エンジン語彙なし）:

- kind: replace、when は {event: move, from: bz, subject: self}
  （行き先を書かない = どこへ離れる時でも）
- optional: true で「してもよい」（断れば元の移動が進む）
- if で裏向きマナの枚数を数える（{count: {zone: mana, filter: {face_down: true}}}。
  第23弾の水晶武装と同じ数え方）
- instead は op flip_up（既存）
- 「各ターンに一度」版は once_per_turn: true（既存フラグ）
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T484", "T485", "T486")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _face_down_mana(e, player=0):
    return sum(1 for c in e.zlist("mana", player) if e.s.cards[c].face_down)


def _in_bz(e, defn, player=0):
    return any(e.s.cards[c].defn == defn and e.s.cards[c].controller == player
               for c in e.zlist("bz", player))


def _in_gy(e, defn, player=0):
    return any(e.s.cards[c].defn == defn for c in e.zlist("graveyard", player))


def _run(e, plan, limit=200):
    """plan: [(kind, key or callable), ...] を順に消費する簡易ドライブ。
    choose_cards は plan の対象が無ければ先頭から min 枚。
    戻り値: choose_replacement 決定のキー一覧（現れたものすべて）。"""
    plan = list(plan)
    replacements = []
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "choose_replacement":
            replacements.append(list(keys))
        hit = next((i for i, (k, key) in enumerate(plan)
                    if k == d["kind"] and (key in keys or key == "*")), None)
        if hit is not None:
            k, key = plan.pop(hit)
            if key == "*":
                e.answer(list(range(min(3, len(keys)))))
            else:
                e.answer([keys.index(key)])
            continue
        if d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return replacements


def _setup_kappa(rules, proto="T484", flips=1, p1_spells=1):
    e = setup(rules,
              {"hand": ["T485"] * flips, "mana": ["T030"] * 6, "bz": [proto]},
              {"hand": ["T056"] * p1_spells, "mana": ["T082"] * (3 * p1_spells),
               "bz": ["T001"]},
              filler="T002")
    plan = []
    for _ in range(flips):
        plan += [("main", "play:T485"), ("choose_cards", "*")]
    return e, plan


def test_kappa_replace_saves_creature(rules):
    """裏向き3枚を表向きにして、離れるかわりに残る。"""
    e, plan = _setup_kappa(rules)
    plan += [("main", "play:T056"), ("choose_cards", "bz:T484:0"),
             ("choose_replacement", "replace:T484:0")]
    reps = _run(e, plan)
    assert _face_down_mana(e) == 0          # 3枚とも表向きになった
    assert any("decline" in r for r in reps)  # 「してもよい」なので断る選択肢もある
    assert _in_bz(e, "T484")
    assert not _in_gy(e, "T484")


def test_kappa_decline_lets_it_leave(rules):
    """断れば通常どおり破壊される（判別）。"""
    e, plan = _setup_kappa(rules)
    plan += [("main", "play:T056"), ("choose_cards", "bz:T484:0"),
             ("choose_replacement", "decline")]
    _run(e, plan)
    assert _in_gy(e, "T484")
    assert _face_down_mana(e) == 3          # 裏向きはそのまま


def test_kappa_not_enough_face_down(rules):
    """裏向きが2枚しかなければ置換自体が現れない（if の門番）。"""
    e = setup(rules,
              {"hand": ["T485"], "mana": ["T030"] * 6, "bz": ["T484"]},
              {"hand": ["T056"], "mana": ["T082"] * 3, "bz": ["T001"]},
              filler="T002")
    # T485 は3枚まで選べるが、ここでは2枚だけ裏向きにする
    plan = [("main", "play:T485")]
    reps = []
    flipped = False
    for _ in range(200):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "choose_replacement":
            reps.append(list(keys))
        if plan and d["kind"] == "main" and "play:T485" in keys:
            e.answer([keys.index("play:T485")])
            plan.pop(0)
            continue
        if d["kind"] == "choose_cards" and not flipped and d.get("player") == 0:
            e.answer([0, 1])   # 2枚だけ
            flipped = True
            continue
        if d["kind"] == "main" and d.get("player") == 1 and "play:T056" in keys:
            e.answer([keys.index("play:T056")])
            continue
        if d["kind"] == "choose_cards" and d.get("player") == 1 and "bz:T484:0" in keys:
            e.answer([keys.index("bz:T484:0")])
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert reps == []                        # 置換の諮問は一度も出ない
    assert _in_gy(e, "T484")
    assert _face_down_mana(e) == 2


def test_kappa_once_per_turn(rules):
    """T486（各ターンに一度・2枚版）: 同じターンに2回目は使えない。"""
    e, plan = _setup_kappa(rules, proto="T486", flips=2, p1_spells=2)
    plan += [("main", "play:T056"), ("choose_cards", "bz:T486:0"),
             ("choose_replacement", "replace:T486:0"),
             ("main", "play:T056"), ("choose_cards", "bz:T486:0")]
    reps = _run(e, plan)
    assert len(reps) == 1                    # 諮問は1回だけ
    assert _in_gy(e, "T486")                 # 2回目の破壊は通る
    assert _face_down_mana(e) == 4           # 6 - 2（1回分だけ表向きに）
