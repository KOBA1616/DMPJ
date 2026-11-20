"""語彙パイロット第308弾: evolve_from_deck_onto_self（ドリフト）。

対象は dmc64-024 ゴウケンオー～剣々轟々～ / dmc64-025
ケンゴウグレンオー～天地鳴動～ の2件（いずれも gaps =
[soul_shift, evolve_from_deck_onto_self]、partial は空）。
soul_shift は第305弾でドリフト確認済み。本弾の対象条項
「自分の山札を見る。その中から名前に《X》とあるクリーチャーを
1体選び、このクリーチャーの上に置いてもよい。その後、山札を
シャッフルする」も新規語彙なしで書ける:

- 山札から上に置く = move {stack_evo: true, evo_source:
  {ref: self}}（第173弾 deck_evolution の形。同製品 DMC64 の
  登録済み dmc64-036 / dmc64-042 が全山札検索形の先例で、
  choose {zone: deck, look: true, filter: {name_has: X},
  count: 1} as p → move {ref: p, count: all} → shuffle）
- 攻撃するかわりにタップ = {kind: activate, cost: {tap: self}}
- 相手のブロッカーすべて破壊 = destroy {filter:
  {keyword: blocker}, count: all}、パワー2000以下すべて破壊 =
  destroy {filter: {power_le: 2000}, count: all}
- 進化元は evolve_from {name_has: ...}（dmc64-036 の先例）
- ソウルシフトは soul_shift {floor: 1}（024 は裸のキーワード
  ＝標準定義「1より少なくならない」。025 はリマインダ明記で
  floor: 1。第274弾・ラウンド309の先例どおり）

確立形は tests/test_vocab_pilot308_cards.py の FORM_024 /
FORM_025 が正本。プロト T948 = 024形、T949 = 025形。
"""
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card
from tests._conv_cache import proto_card

TABLES = load_tables()


def _by_defn(e, zone, defn, player=0):
    return [c for c in e.zlist(zone, player)
            if e.s.cards[c].defn == defn
            and (zone != "bz" or e.s.cards[c].controller == player)]


def _tapped_mana(e, player=0):
    return [c for c in e.zlist("mana", player) if e.s.cards[c].tapped]


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


def _play_handler(play_key, evo_base=None):
    st = {"played": False}

    def handler(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d["player"] == 0 and not st["played"]:
            if play_key in keys:
                st["played"] = True
                return [keys.index(play_key)]
        if d["kind"] == "choose_evo_source" and evo_base is not None:
            for i, o in enumerate(d["options"]):
                if o.get("cid") == evo_base:
                    return [i]
        if d["kind"] == "pay_mana":
            return [0]
        if d["kind"] == "yes_no":
            return [0]
        return None

    return handler


def _activate_handler(defn, stack_defn=None, accept=True):
    """activate:<defn>:* を一度だけ使い、may は accept で承諾/辞退、
    choose_cards では stack_defn を選ぶ。起動は attack 決定で
    提示される（攻撃するかわりのタップ能力のため）。
    handler.state["declined"] に辞退したかどうかが残る。"""
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
        if d["kind"] == "choose_cards" and stack_defn is not None:
            for i, o in enumerate(d["options"]):
                if o.get("defn") == stack_defn:
                    return [i]
        if d["kind"] == "pay_mana":
            return [0]
        return None

    handler.state = st
    return handler


# ---------------------------------------------------------------- parse

def test_parse_forms(rules):
    d948 = parse_card(proto_card("T948"), TABLES)
    assert d948.soul_shift == {"floor": 1}
    assert d948.evolve_from == [{"name_has": "ケンゴウグレンオー"}] or \
        d948.evolve_from == {"name_has": "ケンゴウグレンオー"}
    assert "triple_breaker" in d948.keywords
    d949 = parse_card(proto_card("T949"), TABLES)
    assert d949.soul_shift == {"floor": 1}
    assert "double_breaker" in d949.keywords
    acts = [a for a in d948.abilities if a.get("kind") == "activate"]
    assert len(acts) == 1 and acts[0]["cost"] == {"tap": "self"}


# ------------------------------------------------------- soul shift 本体

def test_soulshift_024_form(rules):
    # コスト17 − 進化元コスト5 = 12 を支払う（floor 1 は効かない範囲）
    e = setup(rules, {"hand": ["T948"], "bz": ["T950"],
                      "mana": ["T034"] * 12}, {})
    top = e.zlist("hand", 0)[0]
    base = e.zlist("bz", 0)[0]
    _run(e, _play_handler("play:T948", evo_base=base),
         done=lambda: e.s.cards[top].zone == "bz")
    assert e.s.cards[top].zone == "bz"
    assert e.s.cards[top].under == [base]
    assert len(_tapped_mana(e)) == 12


def test_soulshift_025_form(rules):
    # コスト10 − 進化元コスト5 = 5 を支払う
    e = setup(rules, {"hand": ["T949"], "bz": ["T951"],
                      "mana": ["T034"] * 5}, {})
    top = e.zlist("hand", 0)[0]
    base = e.zlist("bz", 0)[0]
    _run(e, _play_handler("play:T949", evo_base=base),
         done=lambda: e.s.cards[top].zone == "bz")
    assert e.s.cards[top].zone == "bz"
    assert e.s.cards[top].under == [base]
    assert len(_tapped_mana(e)) == 5


def test_evolve_name_mismatch_not_offered(rules):
    # T948 の進化元は名前に《ケンゴウグレンオー》を含むものだけ。
    # ワンケングレンオー獣（T951）では提示されない
    e = setup(rules, {"hand": ["T948"], "bz": ["T951"],
                      "mana": ["T034"] * 17}, {})
    seen = []

    def probe(e, d):
        if d["kind"] == "main" and d["player"] == 0:
            seen.extend(o["key"] for o in d["options"])
        return None

    _run(e, probe, limit=60)
    assert "play:T948" not in seen


# ------------------------------------------------------- 起動能力（024形）

def _setup_024(rules, deck):
    return setup(rules,
                 {"bz": ["T948"], "deck": deck, "mana": ["T034"] * 3},
                 {"bz": ["T954", "T955"]})


def test_activate_024_destroys_blockers_and_stacks(rules):
    e = _setup_024(rules, ["T952"] + ["T001"] * 9)
    host = _by_defn(e, "bz", "T948")[0]
    placed = _by_defn(e, "deck", "T952")[0]
    blocker = _by_defn(e, "bz", "T954", player=1)[0]
    small = _by_defn(e, "bz", "T955", player=1)[0]
    deck_n = len(e.zlist("deck", 0))
    _run(e, _activate_handler("T948", stack_defn="T952"),
         done=lambda: e.s.cards[placed].zone == "bz")
    # 相手のブロッカーは破壊され、ブロッカーでない小型は残る
    assert e.s.cards[blocker].zone == "graveyard"
    assert e.s.cards[small].zone == "bz"
    # 山札のケンゲキオージャがこのクリーチャーの上に重なった
    assert e.s.cards[placed].zone == "bz"
    assert e.s.cards[host].top_of == placed
    assert host in e.s.cards[placed].under
    assert len(e.zlist("deck", 0)) == deck_n - 1
    # 起動コストでタップしている
    assert e.s.cards[host].tapped


def test_activate_024_decline_stacks_nothing(rules):
    e = _setup_024(rules, ["T952"] + ["T001"] * 9)
    host = _by_defn(e, "bz", "T948")[0]
    placed = _by_defn(e, "deck", "T952")[0]
    blocker = _by_defn(e, "bz", "T954", player=1)[0]
    deck_n = len(e.zlist("deck", 0))
    handler = _activate_handler("T948", accept=False)
    after = {"n": 0}

    def done():
        # 辞退が記録された時点で効果の解決は終わっている
        # （シャッフルは決定なしで流れる）。1決定だけ余分に
        # 流して止める（次の自分のターンのドローを跨がない）
        if handler.state["declined"]:
            after["n"] += 1
            return after["n"] > 1
        return False

    _run(e, handler, limit=300, done=done)
    assert handler.state["declined"]
    # 破壊は行われるが、置く方は辞退したので重ならない
    assert e.s.cards[blocker].zone == "graveyard"
    assert e.s.cards[placed].zone == "deck"
    assert e.s.cards[host].top_of == -1  # 重なっていない
    assert len(e.zlist("deck", 0)) == deck_n


def test_activate_024_no_match_in_deck(rules):
    e = _setup_024(rules, ["T001"] * 10)
    host = _by_defn(e, "bz", "T948")[0]
    blocker = _by_defn(e, "bz", "T954", player=1)[0]
    _run(e, _activate_handler("T948"), limit=300)
    assert e.s.cards[blocker].zone == "graveyard"
    assert e.s.cards[host].top_of == -1  # 重なっていない
    assert e.s.cards[host].zone == "bz"


# ------------------------------------------------------- 起動能力（025形）

def test_activate_025_destroys_small_and_stacks(rules):
    e = setup(rules,
              {"bz": ["T949"], "deck": ["T953"] + ["T001"] * 9,
               "mana": ["T034"] * 3},
              {"bz": ["T955", "T954"]})
    host = _by_defn(e, "bz", "T949")[0]
    placed = _by_defn(e, "deck", "T953")[0]
    small = _by_defn(e, "bz", "T955", player=1)[0]
    blocker = _by_defn(e, "bz", "T954", player=1)[0]
    deck_n = len(e.zlist("deck", 0))
    _run(e, _activate_handler("T949", stack_defn="T953"),
         done=lambda: e.s.cards[placed].zone == "bz")
    # パワー2000以下は破壊され、パワー3000のブロッカーは残る
    assert e.s.cards[small].zone == "graveyard"
    assert e.s.cards[blocker].zone == "bz"
    # 山札のゴウケンオーがこのクリーチャーの上に重なった
    assert e.s.cards[placed].zone == "bz"
    assert e.s.cards[host].top_of == placed
    assert host in e.s.cards[placed].under
    assert len(e.zlist("deck", 0)) == deck_n - 1
