"""第158弾 put_evolution_stacking: move の stack_evo と put_stacked タスクのテスト。

対象カードは dm26ex1-017（型2: コストの異なるクリーチャーを好きな数。進化は重ねる）と
dmrp03-007（型3: コストがすべて異なるクリーチャーをすべて出す側）。出し方の要点は
公式QA 31610（先に出たカードが後の進化元になれる）/ 31611（「出た時」は全員出終わる
まで待機。以後の出し方に途中で出たカードの能力が影響する）。
設計ノート: pilot157-put-evolution-stacking-design.md（ツリー内では第158弾）。
"""
import os

import pytest
import yaml

from dmsim import load_rules
from dmsim.defs import DefError, card_yaml_files, load_tables, parse_card
from conftest import setup


def _play(e, defn):
    """defn を手札から出す（クリーチャーは場に出るまで、呪文は解決して墓地に行くまで）。"""
    def done():
        cs = [c for c in e.s.cards if c.defn == defn and c.controller == 0]
        return any(c.zone == "bz" for c in cs) or (cs and cs[0].zone == "graveyard")
    for _ in range(300):
        if done():
            return
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_cards":
            return   # 出た時などの選択は呼び出し側のドライバに委ねる（未回答のまま残す）
        if d["kind"] in ("main", "attack") and f"play:{defn}" in keys:
            e.answer([keys.index(f"play:{defn}")])
        elif d["kind"] == "yes_no":
            e.answer([next(i for i, o in enumerate(d["options"]) if o["key"] == "yes")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))

X_CARDS = """
cards:
  - id: X223
    name: 進化元観測獣
    types: [creature]
    civs: [water]
    cost: 1
    power: 1000
    races: [テスト]
    text: このクリーチャーが進化元になる時、カードを１枚引く。
    abilities:
      - kind: trigger
        when: {event: evolve_base, subject: self}
        effect: [{op: draw, count: 1}]
  - id: X224
    name: 重ね出し観測進化獣
    types: [creature, evolution]
    civs: [water]
    cost: 3
    power: 3000
    races: [テスト]
    evolve_from: {civs: [water]}
    text: 進化-自分の水のクリーチャー1体の上に置く。このクリーチャーが進化して出た時、カードを１枚引く。
    abilities:
      - kind: trigger
        when: {event: move, to: bz, subject: self, stacked: true}
        effect: [{op: draw, count: 1}]
  - id: X226
    name: 墓地封じの番人
    types: [creature]
    civs: [darkness]
    cost: 2
    power: 2000
    races: [テスト]
    text: 自分の墓地にあるクリーチャーは、バトルゾーンに出ることができない。（途中入場の常在型が後続の出し方に効くことの観測用）
    abilities:
      - kind: static
        affects: {zone: graveyard, owner: you, filter: {types: [creature]}}
        mod: {deny: [enter_bz]}
  - id: X227
    name: 重ね出し試験呪文
    types: [spell]
    civs: [darkness]
    cost: 3
    races: [テスト]
    text: 自分の墓地からクリーチャーを好きな数出す。進化クリーチャーは進化元に重ねて出す。
    spell:
      - {op: move, select: {zone: graveyard, owner: you, filter: {types: [creature]}, count: any}, to: bz, reason: put, stack_evo: true}
"""


@pytest.fixture(scope="module")
def xr(tmp_path_factory):
    p = tmp_path_factory.mktemp("p158") / "x158.yaml"
    p.write_text(X_CARDS, encoding="utf-8")
    here = os.path.dirname(os.path.abspath(__file__))
    return load_rules(card_yaml_files() + [os.path.join(here, "rule_cards.yaml"), str(p)])


def _card(e, defn, p=0):
    # 山札・シールドのフィラー（T001）と同名のカードを拾わないよう、その2ゾーンのコピーは除外する
    return next(c for c in e.s.cards if c.defn == defn and c.controller == p and c.zone not in ("deck", "shield"))


def _drive_picks(e, order, stop_turn=None, max_steps=400):
    """choose_cards では order の順に1枚ずつ選び、尽きたら止める（[] を返す）。
    yes_no は yes、他は pass / 最小手。stop_turn に達し pending が空なら止める。"""
    picks = list(order)
    for _ in range(max_steps):
        if stop_turn is not None and e.s.turn >= stop_turn and not e.s.pending:
            return
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_cards":
            want = next((w for w in picks
                         if any(o.get("cid") and e.s.cards[o["cid"]].defn == w for o in d["options"])), None)
            if want is None:
                e.answer([])
                picks = []
                continue
            idx = next(i for i, o in enumerate(d["options"])
                       if o.get("cid") and e.s.cards[o["cid"]].defn == want)
            picks.remove(want)
            e.answer([idx])
        elif d["kind"] == "yes_no":
            e.answer([next(i for i, o in enumerate(d["options"]) if o["key"] == "yes")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


# ---- (1) 型2: もとから場にある進化元へ重なる。stacked / evolve_base が発火する ----

def test_stacks_onto_existing_base(xr):
    e = setup(xr, {"hand": ["T223"], "mana": ["T008"] * 8, "bz": ["X223"],
                   "graveyard": ["X224", "T001", "T019"]}, {})
    _play(e, "T223")
    h0 = len(e.zlist("hand", 0))
    _drive_picks(e, ["T001", "X224", "T019"], stop_turn=2)
    base, evo = _card(e, "X223"), _card(e, "X224")
    assert evo.zone == "bz" and evo.under == [base.cid] and base.top_of == evo.cid
    assert _card(e, "T001").zone == "bz" and _card(e, "T019").zone == "bz"
    # evolve_base（進化元側）と stacked（進化して出た時）の両方が発火して計2ドロー
    assert len(e.zlist("hand", 0)) == h0 + 2


# ---- (2) QA 31610: 先に出たカードが進化元になれる。逆順では進化元が無く出ない ----

def test_base_enters_first_then_evo_stacks(xr):
    e = setup(xr, {"hand": ["T223"], "mana": ["T008"] * 8,
                   "graveyard": ["X223", "X224", "T001"]}, {})
    _play(e, "T223")
    _drive_picks(e, ["X223", "X224", "T001"], stop_turn=2)
    base, evo = _card(e, "X223"), _card(e, "X224")
    assert evo.zone == "bz" and evo.under == [base.cid] and base.top_of == evo.cid


def test_evo_first_without_base_stays_in_graveyard(xr):
    e = setup(xr, {"hand": ["T223"], "mana": ["T008"] * 8,
                   "graveyard": ["X223", "X224", "T001"]}, {})
    _play(e, "T223")
    _drive_picks(e, ["X224", "X223", "T001"], stop_turn=2)
    # 進化元が場に無い順序で選ばれた進化クリーチャーは出ない（墓地に残る）。残りは通常どおり出る
    assert _card(e, "X224").zone == "graveyard"
    assert _card(e, "X223").zone == "bz" and _card(e, "T001").zone == "bz"


# ---- (3) 型3: コストがすべて異なる8体（進化含む）が全員出て、「出た時」は全員出終わるまで待機 ----

def test_type3_all_enter_and_etb_waits(xr):
    e = setup(xr, {"bz": ["T224"],
                   "graveyard": ["T009", "T001", "T077", "R105", "T019", "T021", "T020", "T052", "T005"]}, {})
    order = ["T009", "T001", "T077", "R105", "T019", "T021", "T020", "T052"]
    picks = list(order)
    r105_options = []
    for _ in range(500):
        if e.s.turn > 2:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_cards":
            if not picks:
                # 積み上げ選択が終わった後の choose_cards は R105 の「出た時」（全員出終わった後に解決）
                r105_options.append([o.get("cid") for o in d["options"]])
                t052 = _card(e, "T052")
                assert all(_card(e, dn).zone == "bz" for dn in order)   # この時点で全員出ている
                e.answer([next(i for i, o in enumerate(d["options"]) if o.get("cid") == t052.cid)])
                continue
            want = next((w for w in picks
                         if any(o.get("cid") and e.s.cards[o["cid"]].defn == w for o in d["options"])), None)
            if want is None:
                e.answer([])
                picks = []
                continue
            picks.remove(want)
            e.answer([next(i for i, o in enumerate(d["options"])
                           if o.get("cid") and e.s.cards[o["cid"]].defn == want)])
        elif d["kind"] == "yes_no":
            e.answer([next(i for i, o in enumerate(d["options"]) if o["key"] == "yes")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    t052 = _card(e, "T052")
    assert r105_options and t052.cid in r105_options[0]
    assert t052.zone == "hand"   # R105 の効果で戻された
    t009, t077 = _card(e, "T009"), _card(e, "T077")
    assert t077.zone == "bz" and t077.under == [t009.cid] and t009.top_of == t077.cid   # 先に出た T009 が進化元
    assert [c.defn for c in e.s.cards if c.zone == "graveyard" and c.controller == 0] == ["T005"]


# ---- (4) QA 31611 後段: 途中で出たカードの常在型が、それ以降の出し方に影響する ----

def test_mid_sequence_static_affects_later_entries(xr):
    e = setup(xr, {"hand": ["X227"], "mana": ["T008"] * 3, "graveyard": ["X226", "T001"]}, {})
    _play(e, "X227")
    _drive_picks(e, ["X226", "T001"], stop_turn=2)
    assert _card(e, "X226").zone == "bz"
    # X226 が場に出た後は、その deny（墓地のクリーチャーは出られない）が T001 の移動に効く
    assert _card(e, "T001").zone == "graveyard"


# ---- (5) 進化V: フィルタごとに進化元を選んで重ねる ----

def test_evolution_v_stacks_on_each_filter(xr):
    e = setup(xr, {"hand": ["X227"], "mana": ["T008"] * 3, "bz": ["T004", "T001"],
                   "graveyard": ["T089"]}, {})
    _play(e, "X227")
    _drive_picks(e, ["T089"], stop_turn=2)
    t089 = _card(e, "T089")
    assert t089.zone == "bz"
    assert set(t089.under) == {_card(e, "T004").cid, _card(e, "T001").cid}


# ---- (6) 検証: stack_evo の不正な組み合わせは DefError ----

TABLES = load_tables()

_HEAD = """
id: {id}
name: 検証用
types: [creature]
civs: [fire]
cost: 3
power: 3000
races: [テスト]
abilities:
  - kind: trigger
    when: {{event: move, to: bz, subject: self}}
    effect:
      - {move}
source: {{official: test, review: pending}}
"""


def _bad(move_yaml):
    with pytest.raises(DefError):
        parse_card(yaml.safe_load(_HEAD.format(id="XBAD", move=move_yaml)), TABLES)


def test_stack_evo_validation():
    sel = "{zone: graveyard, owner: you, count: any}"
    _bad(f"{{op: move, select: {sel}, to: bz, reason: put, stack_evo: false}}")          # 偽値は不可
    _bad(f"{{op: move, select: {sel}, to: shield, reason: put, stack_evo: true}}")       # 行き先は bz だけ
    _bad(f"{{op: move, select: {sel}, to: bz, reason: put, stack_evo: true, stack_on: {{ref: self}}}}")
