"""語彙パイロット第305弾: soul_shift（ギャップ名ドリフト）。

rejects の純粋2件（dm26rp2-001 極まる九極 Q.9 / dmex18-005 ケンゲキオージャ
～究極火焔～）はギャップ名 soul_shift で残っているが、機構そのものは
第218弾の面フィールド soul_shift {floor}（ソウルシフト∞）＋第274弾の
クラシック単体進化への適用（ギャップ名は soulshift）で実装済み。
本弾は新規語彙なしで、対象2件の形が既存語彙で表せることを固定する:

- 両件とも floor は「０以下にならない」→ {floor: 0}。
- dm26rp2-001 形（T932）: 文明フィルタ進化＋離脱誘発。離脱誘発の
  「その下にコスト９のクリーチャーがあれば」は第294弾の
  event.was_under を exists ゲートで読み、「上から９枚を見て
  光のコスト９を出してもよい。残りをシャッフルして下に置く」は
  dmex18-s11 の登録先例（choose look → may play_free → move）で
  order: shuffle に替えた形。
- dmex18-005 形（T935）: 名前フィルタ進化＋勝利誘発。「相手の呪文
  またはバトルゾーンにある相手のクリーチャーの能力によって離れる時」
  は第290弾で固定した cause {by: opp, kind: [spell, ability]} の形。

コスト０まで軽減された有色カードの支払い（112.2b）は第274弾と
第292弾で解釈が競合し未解決のため、本弾ではタップ枚数を断言しない
（場に出ることと進化元の束だけを見る）。
"""
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card
from dmsim.engine.scenario import build
from tests._conv_cache import proto_card

TABLES = load_tables()

LEAVE_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "subject": "self"},
    "if": {"exists": {"ref": "event.was_under",
                      "filter": {"types": ["creature"],
                                 "cost_le": 9, "cost_ge": 9}}},
    "effect": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "from_top": 9,
                    "look": True, "count": "all"},
         "reveal": True, "as": "pile"},
        {"op": "may", "body": [
            {"op": "play_free",
             "select": {"ref": "pile",
                        "filter": {"types": ["creature"], "civs": ["light"],
                                   "cost_le": 9, "cost_ge": 9},
                        "count": 1}}]},
        {"op": "move",
         "select": {"ref": "pile", "count": "all"},
         "to": "deck", "position": "bottom", "order": "shuffle",
         "reason": "put"},
    ],
}

WIN_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "subject": "self",
             "cause": {"by": "opp", "kind": ["spell", "ability"]}},
    "effect": [{"op": "win"}],
}


def setup_exact(rules, p0, p1=None, filler="T002"):
    """山札の中身を spec の deck リストだけにする（deck_exact）。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": 1, "deck_size": 20,
                         "deck_exact": [True, True]})


def _by_defn(e, zone, defn, player=0):
    return [c for c in e.zlist(zone, player)
            if e.s.cards[c].defn == defn
            and (zone != "bz" or e.s.cards[c].controller == player)]


def _tapped_mana(e, player=0):
    return [c for c in e.zlist("mana", player) if e.s.cards[c].tapped]


def _deck_defns(e, player):
    return [e.s.cards[c].defn for c in e.s.zones["deck"][player]]


def _run(e, handler, limit=900, done=None):
    """汎用ドライバ。handler(e, d) が回答 index 列を返せばそれを使い、
    None なら既定（pass 優先、min=0 なら空、それ以外は先頭 min 件）。
    done() が真になったら即止める（ターン開始のアンタップ等を跨がない）。"""
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


def _play_handler(play_keys, evo_base=None, choose_cid=None, choose_defn=None):
    """play_keys: {player: key} を一度だけプレイする。evo_base は進化元 cid、
    choose_cid / choose_defn は choose_cards で選ぶ対象。"""
    st = {"played": set()}

    def handler(e, d):
        p = d["player"]
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and p in play_keys and p not in st["played"]:
            if play_keys[p] in keys:
                st["played"].add(p)
                return [keys.index(play_keys[p])]
        if d["kind"] == "choose_evo_source" and evo_base is not None:
            for i, o in enumerate(d["options"]):
                if o.get("cid") == evo_base:
                    return [i]
        if d["kind"] == "pay_mana":
            return [0]
        if d["kind"] == "yes_no":
            return [0]
        if d["kind"] == "choose_cards":
            for i, o in enumerate(d["options"]):
                if choose_cid is not None and o.get("cid") == choose_cid:
                    return [i]
                if choose_defn is not None and o.get("defn") == choose_defn:
                    return [i]
        return None

    return handler


# ---------------------------------------------------------------- parse

def test_parse_forms(rules):
    d932 = parse_card(proto_card("T932"), TABLES)
    assert d932.soul_shift == {"floor": 0}
    assert d932.evolve_from and not d932.evolve_any
    trigs = [a for a in d932.abilities if a.get("kind") == "trigger"]
    assert trigs == [LEAVE_TRIGGER]
    d935 = parse_card(proto_card("T935"), TABLES)
    assert d935.soul_shift == {"floor": 0}
    assert d935.evolve_from == {"name_has": "ゴウケン"}
    trigs = [a for a in d935.abilities if a.get("kind") == "trigger"]
    assert trigs == [WIN_TRIGGER]


# ------------------------------------------------------- soul shift 本体

def test_soulshift_civs_base_full_reduction(rules):
    # 光・コスト9 − 進化元コスト9 = 0（floor 0）。場に出て束になる。
    # 支払い枚数は 112.2b 競合のため断言しない。
    e = setup(rules, {"hand": ["T932"], "bz": ["T933"],
                      "mana": ["T001"] * 3}, {})
    top = e.zlist("hand", 0)[0]
    base = e.zlist("bz", 0)[0]
    _run(e, _play_handler({0: "play:T932"}, evo_base=base))
    assert e.s.cards[top].zone == "bz"
    assert e.s.cards[top].under == [base]


def test_soulshift_civs_base_partial_reduction(rules):
    # 光・コスト9 − 進化元コスト5 = 4 を支払う（文明コストは光1枚を含む）
    e = setup(rules, {"hand": ["T932"], "bz": ["T934"],
                      "mana": ["T933", "T934", "T001", "T001", "T001"]}, {})
    top = e.zlist("hand", 0)[0]
    base = e.zlist("bz", 0)[0]
    _run(e, _play_handler({0: "play:T932"}, evo_base=base),
         done=lambda: e.s.cards[top].zone == "bz")
    assert e.s.cards[top].zone == "bz"
    assert e.s.cards[top].under == [base]
    assert len(_tapped_mana(e)) == 4


def test_soulshift_name_base(rules):
    # 火・コスト12 − 名前フィルタの進化元コスト5 = 7 を支払う
    e = setup(rules, {"hand": ["T935"], "bz": ["T936"],
                      "mana": ["T936"] + ["T001"] * 7}, {})
    top = e.zlist("hand", 0)[0]
    base = e.zlist("bz", 0)[0]
    _run(e, _play_handler({0: "play:T935"}, evo_base=base),
         done=lambda: e.s.cards[top].zone == "bz")
    assert e.s.cards[top].zone == "bz"
    assert e.s.cards[top].under == [base]
    assert len(_tapped_mana(e)) == 7


def test_soulshift_name_mismatch_not_offered(rules):
    # 名前に《ゴウケン》を含まないクリーチャーは進化元にならず提示されない
    e = setup(rules, {"hand": ["T935"], "bz": ["T934"],
                      "mana": ["T001"] * 13}, {})
    seen = []

    def probe(e, d):
        if d["kind"] == "main" and d["player"] == 0:
            seen.extend(o["key"] for o in d["options"])
        return None

    _run(e, probe, limit=60)
    assert "play:T935" not in seen


# ------------------------------------------------------- 離脱誘発（T932）

def _leave_setup(rules, base_defn):
    # build は deck spec を逆順に置く（spec の末尾が山札の一番上）
    return setup_exact(
        rules,
        {"hand": ["T932"], "bz": [base_defn],
         "mana": ["T933", "T934", "T001", "T001", "T001"],
         "deck": ["T003"] * 14 + ["T933"]},
        {"hand": ["T056"], "mana": ["T008"] * 5,
         "deck": ["T001"] * 10})


def test_leave_trigger_plays_cost9_from_look(rules):
    e = _leave_setup(rules, "T933")
    base = e.zlist("bz", 0)[0]
    top = e.zlist("hand", 0)[0]
    deck933 = _by_defn(e, "deck", "T933")[0]   # 山札にある T933（ベースと別個体）
    deck_before = _deck_defns(e, 0)
    assert deck_before[0] == "T933" and len(deck_before) == 15
    _run(e, _play_handler({0: "play:T932", 1: "play:T056"},
                          evo_base=base, choose_cid=top,
                          choose_defn="T933"),
         done=lambda: e.s.cards[deck933].zone == "bz")
    # 本体と進化元は墓地へ
    assert e.s.cards[top].zone == "graveyard"
    assert e.s.cards[base].zone == "graveyard"
    # 見た9枚から光のコスト9（山札の T933）が出る
    assert e.s.cards[deck933].zone == "bz"
    # 残り8枚はシャッフルして下へ: 山札+手札の T003 は計14枚（1枚は
    # 次ターン開始時のドローで手札に移っている場合がある）
    assert all(d == "T003" for d in _deck_defns(e, 0))
    assert (len(_deck_defns(e, 0))
            + len(_by_defn(e, "hand", "T003"))) == 14


def test_leave_trigger_gate_blocks_without_cost9_under(rules):
    # 下がコスト5なら門が閉じ、見ることも出ることも起きない
    e = _leave_setup(rules, "T934")
    base = e.zlist("bz", 0)[0]
    top = e.zlist("hand", 0)[0]
    deck933 = _by_defn(e, "deck", "T933")[0]
    _run(e, _play_handler({0: "play:T932", 1: "play:T056"},
                          evo_base=base, choose_cid=top),
         done=lambda: e.s.turn >= 5)
    assert e.s.cards[top].zone == "graveyard"
    assert e.s.cards[base].zone == "graveyard"
    # 山札の T933 は場に出ていない（山札か、通常ドローで手札にいるだけ）
    assert e.s.cards[deck933].zone in ("deck", "hand")


# ------------------------------------------------------- 勝利誘発（T935）

def test_win_trigger_opponent_spell(rules):
    e = setup(rules, {"bz": ["T935"]},
              {"hand": ["T056"], "mana": ["T008"] * 5})
    tgt = e.zlist("bz", 0)[0]
    _run(e, _play_handler({1: "play:T056"}, choose_cid=tgt))
    assert e.s.result is not None
    assert e.s.result["winner"] == 0


def test_win_trigger_opponent_creature_ability(rules):
    e = setup(rules, {"bz": ["T935"]},
              {"hand": ["T937"], "mana": ["T008"] * 5})
    tgt = e.zlist("bz", 0)[0]
    _run(e, _play_handler({1: "play:T937"}, choose_cid=tgt))
    assert e.s.result is not None
    assert e.s.result["winner"] == 0


def test_win_trigger_own_spell_does_not_win(rules):
    # 自分の呪文で離れた時は cause の by が合わず勝利しない
    e = setup(rules, {"hand": ["T938"], "bz": ["T935"],
                      "mana": ["T008"] * 5}, {})
    tgt = _by_defn(e, "bz", "T935")[0]
    _run(e, _play_handler({0: "play:T938"}, choose_cid=tgt), limit=200,
         done=lambda: len(_by_defn(e, "graveyard", "T935")) == 1)
    assert len(_by_defn(e, "graveyard", "T935")) == 1
    assert e.s.result is None
