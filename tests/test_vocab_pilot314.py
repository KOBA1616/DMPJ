"""語彙パイロット第314弾: stack_from_deck_search（ドリフト）。

対象は dmex18-045 ワンケングレンオー ～弧月躍動～ の1件
（gaps は空で、partial の source.unsupported にだけ
stack_from_deck_search が残る監査行。第313弾の監査で
ドリフト候補として記録された）。

未解決条項は起動能力1節のみで、第308弾の確立形と完全一致
する（新規語彙・エンジン変更なし）:

- 「このクリーチャーで攻撃するかわりに、タップして次の
  能力を使ってもよい」= {kind: activate, cost: {tap: self}}
- 「自分の山札を見る。その中から、名前に《ケンゴウ
  グレンオー》とあるクリーチャーを1体、このクリーチャーの
  上に置いてもよい。その後、山札をシャッフルする」=
  may [choose {zone: deck, owner: you, look: true,
  filter: {name_has: ケンゴウグレンオー, types: [creature]},
  count: 1} as p → move {select: {ref: p, count: all},
  to: bz, reason: put, stack_evo: true, evo_source:
  {ref: self}}] ＋ shuffle（第173弾 deck_evolution の
  全山札検索形。第308弾 T948 / T949 で実挙動固定済み）

探索名は《ケンゴウグレンオー》であって進化元の
《ケングレンオー》ではない（名前の連鎖: 本カードの名
《ワンケングレンオー》が上に乗る側の evolve_from
{name_has: ワンケングレンオー} と一致する。第308弾の
024 / 025 と同じ連鎖構造）。partial の他の節（NEO進化
evolve_from any_of、出た時マナ置き誘発）は完成済み。

確立形は tests/test_vocab_pilot314_cards.py の FORM が
正本。プロト T965 = dmex18-045 形（探索対象には既存の
T949 試験用ケンゴウグレンオー・鳴動を再利用する）。
"""
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card
from tests._conv_cache import proto_card

TABLES = load_tables()

ACTIVATE = {"kind": "activate",
            "cost": {"tap": "self"},
            "effect": [
                {"op": "may",
                 "body": [
                     {"op": "choose",
                      "select": {"zone": "deck", "owner": "you",
                                 "look": True,
                                 "filter": {"name_has": "ケンゴウグレンオー",
                                            "types": ["creature"]},
                                 "count": 1},
                      "as": "p"},
                     {"op": "move",
                      "select": {"ref": "p", "count": "all"},
                      "to": "bz", "reason": "put",
                      "stack_evo": True,
                      "evo_source": {"ref": "self"}}]},
                {"op": "shuffle"}]}


def _by_defn(e, zone, defn, player=0):
    return [c for c in e.zlist(zone, player)
            if e.s.cards[c].defn == defn
            and (zone != "bz" or e.s.cards[c].controller == player)]


def _run(e, handler, limit=900, done=None):
    for _ in range(limit):
        if e.s.result is not None or (done and done()):
            return
        d = e.advance()
        if d is None:
            return
        r = handler(e, d)
        if r is not None:
            e.answer(r)
            continue
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["min"] == 0:
            e.answer([])
        else:
            e.answer(list(range(d["min"])))


def _activate_handler(defn, stack_defn=None, accept=True, seen=None):
    """activate:<defn>:* を一度だけ使い、may は accept で
    承諾/辞退、choose_cards では stack_defn を選ぶ。
    seen があれば choose_cards の提示 defn 列を記録する。"""
    st = {"used": False, "declined": False}

    def handler(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["player"] == 0 and not st["used"]:
            for i, k in enumerate(keys):
                if k.startswith(f"activate:{defn}:"):
                    st["used"] = True
                    return [i]
        if d["kind"] == "yes_no":
            if not accept:
                st["declined"] = True
            return [0] if accept else [len(d["options"]) - 1]
        if d["kind"] == "choose_cards":
            defns = [e.s.cards[o["cid"]].defn for o in d["options"]]
            if seen is not None:
                seen.append(defns)
            if stack_defn is not None:
                for i, dfn in enumerate(defns):
                    if dfn == stack_defn:
                        return [i]
        if d["kind"] == "pay_mana":
            return [0]
        return None

    handler.state = st
    return handler


# ---------------------------------------------------------------- parse

def test_parse_form(rules):
    d = parse_card(proto_card("T965"), TABLES)
    assert d.neo
    assert d.evolve_from == {
        "any_of": [{"civs": ["nature"]}, {"name_has": "ケングレンオー"}],
        "types": ["creature"]}
    assert [a.get("kind") for a in d.abilities] == ["trigger", "activate"]
    act = d.abilities[1]
    assert act["cost"] == {"tap": "self"}
    assert act["effect"] == ACTIVATE["effect"]


# ------------------------------------------------------- CIP（出た時）

def test_cip_top_card_to_mana(rules):
    # partial で完成済みの節: 出た時、山札の上から1枚目を
    # マナゾーンに置く。山札は全て T949 なので上1枚が
    # どちら端でも T949 がマナに加わる
    e = setup(rules, {"hand": ["T965"], "deck": ["T949"] * 5,
                      "mana": ["T001"] * 5}, {})
    top = e.zlist("hand", 0)[0]
    deck_n = len(e.zlist("deck", 0))

    def handler(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d["player"] == 0:
            if "play:T965" in keys:
                return [keys.index("play:T965")]
        if d["kind"] == "pay_mana":
            return [0]
        if d["kind"] == "yes_no":
            return [0]
        return None

    _run(e, handler,
         done=lambda: len(_by_defn(e, "mana", "T949")) == 1)
    assert e.s.cards[top].zone == "bz"
    assert len(_by_defn(e, "mana", "T949")) == 1
    assert len(e.zlist("mana", 0)) == 6     # 支払い5＋CIP 1
    assert len(e.zlist("deck", 0)) == deck_n - 1


# ------------------------------------------------------- 起動能力

def _setup_host(rules, deck):
    return setup(rules,
                 {"bz": ["T965"], "deck": deck, "mana": ["T034"] * 3},
                 {})


def test_activate_stacks_kengogurenoh_from_deck(rules):
    # 山札には名前が近いだけの T951（ワンケングレンオー獣。
    # 《ケングレンオー》は含むが《ケンゴウグレンオー》は
    # 含まない）も混ぜる。探索対象は T949 のみ。候補が
    # 1枚だけだと choose は自動決定され決定として現れない
    # ため、T949 を2枚入れて選択決定を実際に踏む
    e = _setup_host(rules, ["T949", "T949", "T951"] + ["T001"] * 7)
    host = _by_defn(e, "bz", "T965")[0]
    deck_n = len(e.zlist("deck", 0))
    seen = []
    _run(e, _activate_handler("T965", stack_defn="T949", seen=seen),
         done=lambda: len(_by_defn(e, "bz", "T949")) == 1)
    # choose の候補は T949 の2枚だけで、T951 は提示されない
    assert seen and all(s == ["T949", "T949"] for s in seen)
    # 山札のケンゴウグレンオーがこのクリーチャーの上に重なった
    placed = _by_defn(e, "bz", "T949")[0]
    assert e.s.cards[host].top_of == placed
    assert host in e.s.cards[placed].under
    assert len(_by_defn(e, "deck", "T949")) == 1   # もう1枚は山札に残る
    assert len(e.zlist("deck", 0)) == deck_n - 1
    # 起動コストでタップしている
    assert e.s.cards[host].tapped


def test_activate_decline_stacks_nothing(rules):
    e = _setup_host(rules, ["T949"] + ["T001"] * 9)
    host = _by_defn(e, "bz", "T965")[0]
    placed = _by_defn(e, "deck", "T949")[0]
    deck_n = len(e.zlist("deck", 0))
    handler = _activate_handler("T965", accept=False)
    after = {"n": 0}

    def done():
        # 辞退が記録された時点で効果の解決は終わっている
        # （シャッフルは決定なしで流れる）。1決定だけ余分に
        # 流して止める（第308弾の作法）
        if handler.state["declined"]:
            after["n"] += 1
            return after["n"] > 1
        return False

    _run(e, handler, limit=300, done=done)
    assert handler.state["declined"]
    assert e.s.cards[placed].zone == "deck"
    assert e.s.cards[host].top_of == -1     # 重なっていない
    assert len(e.zlist("deck", 0)) == deck_n
    assert e.s.cards[host].tapped          # コストは支払う


def test_activate_no_match_in_deck(rules):
    e = _setup_host(rules, ["T001"] * 10)
    host = _by_defn(e, "bz", "T965")[0]
    _run(e, _activate_handler("T965"), limit=300)
    assert e.s.cards[host].top_of == -1     # 重なっていない
    assert e.s.cards[host].zone == "bz"
