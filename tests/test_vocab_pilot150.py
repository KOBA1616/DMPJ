"""語彙パイロット第150弾: become_evolution_base_trigger（進化元になる時）。

- 進化の重ね適用時（_apply_one の stack_on 分岐）、h_play が立てた進化印がある時だけ、
  進化元を subject・出たクリーチャーを top とする合成レコード evolve_base を出す。
  誘発収集ではその subject を発生源に加える（重ねられた側は bz_tops から外れているため）。
  効果側は {ref: event.top} で上に乗ったクリーチャーを指す。
- 前提修正: when の stacked 照合を有効化した（第28弾で「照合可能」とされたが _match_when に
  分岐が無く、重ねずに出た時にも「進化して出た時」が誘発していた）。あわせて収集レコード
  （_apply_one の out）に stacked を伝播させた。converted の stacked 使用は52箇所で、
  変わるのは重ねずに出られるカード（NEO等）が通常召喚で誘発しなくなる方向のみ。
- 無月の門（summon_on）と侵略は進化ではないので発火しない（summon_on の ev には進化印が
  無く、侵略はイベントを経ず _stack を直接呼ぶ）。
- proto は第149弾が T188 まで使ったため T189〜T191（設計ノートの T188〜T190 から +1）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


X_CARDS = """
cards:
  - id: X190
    name: 魔導具・進化元試験獣
    civs: [darkness]
    cost: 2
    power: 1000
    types: [creature]
    races: [魔導具]
    text: このクリーチャーが進化元になる時、カードを１枚引く。（無月の門で重ねられた時は進化ではないので引かない）
    abilities:
      - kind: trigger
        when: {event: evolve_base, subject: self}
        effect:
          - {op: draw, count: 1}
  - id: X191
    name: 進化元試験ドラゴン
    civs: [nature]
    cost: 2
    power: 2000
    types: [creature]
    races: [テスト・ドラゴン]
    text: このクリーチャーが進化元になる時、カードを１枚引く。（侵略で重ねられた時は進化ではないので引かない）
    abilities:
      - kind: trigger
        when: {event: evolve_base, subject: self}
        effect:
          - {op: draw, count: 1}
"""


@pytest.fixture(scope="session")
def xr(tmp_path_factory):
    p = tmp_path_factory.mktemp("pilot150x") / "x_cards.yaml"
    p.write_text(X_CARDS, encoding="utf-8")
    return load_rules(card_yaml_files() + [p])


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _settle(e, done, drive=None, max_steps=200):
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if drive and drive(e, d, keys):
            continue
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    return done()


def _play_drive(want_key, evo_pick=None):
    def drive(e, d, keys):
        if d["kind"] == "choose_evo_source":
            if evo_pick is None:
                e.answer([0])
            else:
                e.answer([next(i for i, k in enumerate(keys) if k.startswith(evo_pick))])
            return True
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if k == want_key]
            if hit:
                e.answer([hit[0]])
                return True
        return False
    return drive


def _allows_creature(e, cid):
    """chars の allow に attack_creature 許可（dict 形）があるか。文字列形の許可は対象外。"""
    return any(isinstance(a, dict) and a.get("action") == "attack_creature" for a in e.chars(cid)["allow"])


def test_proto_parse(rr):
    """T189〜T191 が parse でき、evolve_base の when が検証を通る。"""
    for cid in ("T189", "T190", "T191"):
        parse_card(_proto_card(cid), TABLES)
    t189 = next(c for c in rr.cards.values() if c.id == "T189")
    trig = [a for a in t189.face(None).abilities if a["kind"] == "trigger"]
    assert trig and trig[0]["when"]["event"] == "evolve_base"
    t190 = next(c for c in rr.cards.values() if c.id == "T190")
    evs = [a["when"]["event"] for a in t190.face(None).abilities]
    assert evs == ["move", "evolve_base"]


def test_shinkapower_grants_to_top(rules):
    """(1) タマシードに進化を重ねるとシンカパワーが発火し、付与（マッハファイター相当の
    attack_creature 許可）が一番上のクリーチャー（event.top）に付く。"""
    e = setup(rules, {"bz": ["T189"], "hand": ["T191"], "mana": ["T001"] * 5}, {})
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T191" for c in e.bz_tops(0)),
                   _play_drive("play:T191"))
    top = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T191")
    under = e.s.cards[top].under
    assert len(under) == 1 and e.s.cards[under[0]].defn == "T189"   # タマシードが下にいる
    assert _allows_creature(e, top)                                  # 付与がトップ（event.top）に付いた
    assert not _allows_creature(e, under[0])                         # 進化元自身には付いていない


def test_neo_plain_summon_no_draw(rules):
    """(2) NEO を通常召喚しただけでは、stacked 側も evolve_base 側も発火しない
    （stacked 照合の有効化の判別テスト。有効化前は stacked 側が誤って発火した）。"""
    e = setup(rules, {"hand": ["T190"], "mana": ["T001", "T001"]}, {})
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T190" for c in e.bz_tops(0)),
                   _play_drive("play:T190"))
    assert _settle(e, lambda: True, None, 30)   # 誘発が残っていないことを進めて確認
    assert len(e.zlist("hand", 0)) == 0         # ドローしていない（T190 が手札を離れただけ）


def test_neo_stacked_draw(rules):
    """(2') NEO を重ねて出すと stacked 側（進化して出た時）が発火してドローする。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T190"], "mana": ["T001", "T001"]}, {})
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T190" for c in e.bz_tops(0)),
                   _play_drive("play:T190:neo", evo_pick="bz:T001"))
    top = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T190")
    assert e.s.cards[top].under and e.s.cards[e.s.cards[top].under[0]].defn == "T001"
    assert _settle(e, lambda: len(e.zlist("hand", 0)) == 1, None, 60)   # 1ドロー


def test_neo_becomes_base_draw(rules):
    """(3) NEO の上に進化を重ねると、その NEO の進化元側（evolve_base）が発火してドローする。"""
    e = setup(rules, {"bz": ["T190"], "hand": ["T191"], "mana": ["T001"] * 5}, {})
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T191" for c in e.bz_tops(0)),
                   _play_drive("play:T191"))
    top = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T191")
    assert e.s.cards[e.s.cards[top].under[0]].defn == "T190"
    assert _settle(e, lambda: len(e.zlist("hand", 0)) == 1, None, 60)   # 進化元側の1ドロー


def test_evolution_v_each_base_fires(rules):
    """(5) 進化V（複数進化元）では元ごとに発火する: 光の元（能力なし）と T190（自然）が
    元になり、ドローは T190 の分だけ1回。"""
    e = setup(rules, {"bz": ["T004", "T190"], "hand": ["T089"],
                      "mana": ["T004"] * 5 + ["T001"]}, {})
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T089" for c in e.bz_tops(0)),
                   _play_drive("play:T089"))
    top = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T089")
    assert len(e.s.cards[top].under) == 2
    assert _settle(e, lambda: len(e.zlist("hand", 0)) == 1, None, 60)   # T190 の evolve_base で1ドローだけ


def test_mugon_does_not_fire(xr):
    """(4) 無月の門で重ねても「進化元になる時」は発火しない（進化ではないため）。"""
    e = setup(xr, {"bz": ["X190", "T127"], "graveyard": ["T127", "T127"],
                   "hand": ["T126", "T127"], "mana": ["T127", "T127"]}, {})
    x190 = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "X190")

    def drive(e, d, keys):
        if d["kind"] == "summon_on":
            opts = d["options"]
            hit = [i for i, o in enumerate(opts) if o.get("cid") == x190]
            rest = [i for i in range(len(opts)) if i not in hit]
            e.answer((hit + rest)[:d["min"]])
            return True
        if d["kind"] == "may":
            e.answer([keys.index("yes") if "yes" in keys else 0])
            return True
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if k == "play:T127"]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T126" for c in e.bz_tops(0)), drive)
    gate = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T126")
    assert x190 in e.s.cards[gate].under          # X190 は実際に門の進化元（下）になっている
    assert _settle(e, lambda: True, drive, 30)
    assert len(e.zlist("hand", 0)) == 0           # evolve_base が発火していれば1枚引いている


def test_invasion_does_not_fire(xr):
    """(6) 侵略で重ねても「進化元になる時」は発火しない（イベントを経ない重ね処理のため）。
    手札は侵略獣自身の出た時ドロー（1枚）だけ増える。"""
    e = setup(xr, {"bz": ["X191"], "hand": ["T065"]}, {"shield": ["T001", "T001"]})
    atk = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "X191")
    e.s.cards[atk].entered_turn = -1

    def drive(e, d, keys):
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if "T065" in k and not k.startswith("charge:")]
            if hit:
                e.answer([hit[0]])
                return True
            if d["kind"] == "yes_no" and "yes" in keys:
                e.answer([keys.index("yes")])
                return True
            if d["kind"] == "attack":
                e.answer([0])
                return True
        return False

    done = lambda: any(e.s.cards[c].defn == "T065" for c in e.bz_tops(0)) and len(e.zlist("shield", 1)) == 1
    assert _settle(e, done, drive, 120)
    top = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T065")
    assert e.s.cards[top].under and e.s.cards[e.s.cards[top].under[0]].defn == "X191"   # 攻撃クリーチャーが下に
    assert _settle(e, lambda: True, drive, 30)
    assert len(e.zlist("hand", 0)) == 1           # T065 自身の出た時ドローだけ（evolve_base が発火すれば2枚）
