"""put_evolution_stacking: 対象2件の手変換 parse。

変換の型は move の `stack_evo: true`（put_stacked タスクが1体ずつ順に出し、進化は
その都度選んだ進化元に重ねる）。手変換は rejects の partial から filter の
not_types: [evolution] を外し（進化も対象に戻す）、stack_evo を足したもの。
dmrp03-007 は count 式の中のフィルタからも not_types を外す（設計§4.2）。
登録（submit）は行わない。設計ノート: pilot157-put-evolution-stacking-design.md（ツリー内では第158弾）。
"""
import yaml
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

PUT_MOVE = {"op": "move",
            "select": {"zone": "graveyard", "owner": "you",
                       "filter": {"types": ["creature"], "cost_le": 5},
                       "count": "any", "distinct_costs": True},
            "to": "bz", "reason": "put", "stack_evo": True}

MILL = {"op": "move",
        "select": {"zone": "deck", "owner": "you", "from_top": 5, "count": {"upto": 5}},
        "to": "graveyard", "reason": "put"}


def _parse(text):
    return parse_card(yaml.safe_load(text), TABLES)


def test_dm26ex1_017():
    """超暴淵 ボウダン＝ロウ: 召喚時／攻撃時の墓地出しが stack_evo になる（型2）。"""
    c = _parse("""
id: dm26ex1-017
name: 超暴淵 ボウダン＝ロウ
types: [creature]
civs: [darkness]
cost: 10
power: 13000
races: [アビスロイヤル]
mana: 1
keywords: [hyper_energy, triple_breaker]
text: このクリーチャーが召喚によって出た時または相手プレイヤーを攻撃する時、自分の山札の上から５枚まで墓地に置く。その後、コスト５以下の、コストが異なるクリーチャーを好きな数、自分の墓地から出す。
abilities:
  - kind: trigger
    when: {event: move, to: bz, subject: self, reason: summon}
    effect:
      - {op: move, select: {zone: deck, owner: you, from_top: 5, count: {upto: 5}}, to: graveyard, reason: put}
      - {op: move, select: {zone: graveyard, owner: you, filter: {types: [creature], cost_le: 5}, count: any, distinct_costs: true}, to: bz, reason: put, stack_evo: true}
  - kind: trigger
    when: {event: attack, subject: self, target: player}
    effect:
      - {op: move, select: {zone: deck, owner: you, from_top: 5, count: {upto: 5}}, to: graveyard, reason: put}
      - {op: move, select: {zone: graveyard, owner: you, filter: {types: [creature], cost_le: 5}, count: any, distinct_costs: true}, to: bz, reason: put, stack_evo: true}
source: {official: dm26ex1-017, review: pending}
""")
    effects = [a["effect"] for a in c.abilities if a["kind"] == "trigger"]
    assert len(effects) == 2 and all(e == [MILL, PUT_MOVE] for e in effects)


def test_dmrp03_007():
    """ラトリエ・ロブション: ターン終了時の全出しが stack_evo になる（型3）。
    count 式のフィルタからも not_types: [evolution] を外す。"""
    c = _parse("""
id: dmrp03-007
name: ラトリエ・ロブション
types: [creature]
civs: [darkness]
cost: 8
power: 8000
races: [マフィ・ギャング]
mana: 1
keywords: [double_breaker]
text: W・ブレイカー自分のターンの終わりに、自分の山札の上から３枚を見てもよい。そうしたら、そのうちの１枚を手札に加え、残りを墓地に置く。自分のターンの終わりに、自分の墓地にコストが違うクリーチャーが８体以上あれば、それらをすべてバトルゾーンに出してもよい。
abilities:
  - kind: trigger
    when: {event: turn_end, player: you}
    effect:
      - op: may
        body:
          - {op: choose, select: {zone: deck, owner: you, from_top: 3, look: true, count: all}, as: a}
          - {op: move, select: {ref: a, count: 1}, to: hand, reason: draw}
          - {op: move, select: {ref: a, count: all}, to: graveyard, reason: put}
  - kind: trigger
    when: {event: turn_end, player: you}
    if: {cmp: [{distinct_cost_count: {zone: graveyard, owner: you, filter: {types: [creature]}}}, ">=", 8]}
    effect:
      - op: may
        body:
          - {op: move, select: {zone: graveyard, owner: you, filter: {types: [creature]}, count: {distinct_cost_count: {zone: graveyard, owner: you, filter: {types: [creature]}}}, distinct_costs: true}, to: bz, reason: put, stack_evo: true}
source: {official: dmrp03-007, review: pending}
""")
    moves = []

    def walk(ops):
        for o in ops:
            if o.get("op") == "move" and o.get("to") == "bz":
                moves.append(o)
            for k in ("body", "then", "else"):
                if k in o:
                    walk(o[k])

    for a in c.abilities:
        if a["kind"] == "trigger":
            walk(a["effect"])
    assert len(moves) == 1
    move = moves[0]
    assert move["stack_evo"] is True
    assert "not_types" not in move["select"]["filter"]
    assert "not_types" not in move["select"]["count"]["distinct_cost_count"]["filter"]
