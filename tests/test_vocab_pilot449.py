"""語彙パイロット第449弾: 「攻撃またはブロックした時、
自分のタマシードがなければ、その攻撃の終わりに
このクリーチャーを破壊する」（end_of_attack_effect）。

センサス（rejects 1,882件を取り直し）: pure 1,734件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）か評価済み却下・残置群。
範囲内・未評価で最小の end_of_attack_effect
（純粋1件）を選定した: dm25ex2-094 鬼星の絆
ウコン丸＆サコン丸。

結論はドリフト（追加語彙なし）。確立形は第319弾
形B（攻撃誘発 {event: attack, subject: self} →
delayed_trigger {when: {event: attack_end, subject:
self}, duration: during_attack} ／ブロック誘発
{event: block, subject: self} → delayed_trigger
{when: {event: attack_end, target: self},
duration: during_attack} で自壊）に、「自分の
タマシードがなければ」の if:
{not: {exists: {zone: bz, owner: you, filter:
{types: [tamaseed]}}}} を両誘発に付けたもの。
if の形は登録済み dmrp21-072 の同文条項と同一。
エンジンは誘発の if を誘発時と解決時の両方で見る
（603.4）。遅延誘発が作られた後の攻撃終了時の
破壊は無条件で、公式の「〜時、〜ならば、その攻撃
の終わりに〜する」（条件は遅延誘発の生成にかかる）
とも一致する。

第3条項「自分のデモニオ・クリーチャーの召喚コスト
を１少なくする。ただし、コストは０以下にはならない」
は登録済み dm24bd2-016 ヤッタレマンと同文で、形は
static {affects: {owner: you, zone: hand, filter:
{types: [creature], race_has: デモニオ}},
mod: {cost: -1}}。ただしヤッタレマンの登録形が付けて
いる cost_min: 1 は本弾では付けない: 公式テキストの
下限は0で、エンジン既定の pay_cost 床は0（core.py
の cost_min 既定0で max を取る）ため、下限0は
cost_min 省略が確立形（第346弾の記録、dm23ex3-t13
の同形軽減も cost_min 無し）。cost_min: 1 は「1より
少なくならない」条項の形（dm21-011 等）。コスト1の
デモニオの pay_cost が0になることを判別テストで
固定する。

プロト T1240（dm25ex2-094 型）/ T1241（コスト1の
デモニオ＝下限0の判別役）。判別役: T189（タマシード）
/ T004（相手ブロッカー・パワー3000）/ T001（攻撃役・
パワー2000・非デモニオ）/ T826（デモニオ・コスト5）。
"""
import copy

import pytest

from dmsim.cards.defs import DefError, load_tables, parse_card
from tests.conftest import setup

TABLES = load_tables()

NAME = "鬼星の絆 ウコン丸＆サコン丸"
TEXT = ("ブロッカー（このクリーチャーをタップして、相手クリーチャーの攻撃先をこのクリーチャーに変更してもよい）\n"
        "このクリーチャーが攻撃またはブロックした時、自分のタマシードがなければ、その攻撃の終わりにこのクリーチャーを破壊する。\n"
        "自分のデモニオ・クリーチャーの召喚コストを１少なくする。だだし、コストは０以下にはならない。")

NO_TAMASEED = {"not": {"exists": {"zone": "bz", "owner": "you",
                                  "filter": {"types": ["tamaseed"]}}}}
DESTROY_SELF = {"op": "destroy", "select": {"ref": "self"}}
TRIGGER_ATTACK = {"kind": "trigger",
                  "when": {"event": "attack", "subject": "self"},
                  "if": copy.deepcopy(NO_TAMASEED),
                  "effect": [{"op": "delayed_trigger",
                              "when": {"event": "attack_end",
                                       "subject": "self"},
                              "duration": "during_attack",
                              "effect": [DESTROY_SELF]}]}
TRIGGER_BLOCK = {"kind": "trigger",
                 "when": {"event": "block", "subject": "self"},
                 "if": copy.deepcopy(NO_TAMASEED),
                 "effect": [{"op": "delayed_trigger",
                             "when": {"event": "attack_end",
                                      "target": "self"},
                             "duration": "during_attack",
                             "effect": [DESTROY_SELF]}]}
STATIC_COST = {"kind": "static",
               "affects": {"owner": "you", "zone": "hand",
                           "filter": {"types": ["creature"],
                                      "race_has": "デモニオ"}},
               "mod": {"cost": -1}}
FORM = {"id": "dm25ex2-094", "name": NAME,
        "types": ["creature"], "civs": ["darkness"],
        "cost": 3, "power": 4000,
        "races": ["デモニオ", "鬼レクスターズ"],
        "mana": 1, "text": TEXT, "keywords": ["blocker"],
        "abilities": [TRIGGER_ATTACK, TRIGGER_BLOCK, STATIC_COST]}

# parse 後は destroy マクロが move（to: graveyard, reason: destroy）
# に展開される。parse 比較は展開形で行う。
PARSED_DESTROY = {"op": "move", "select": {"ref": "self"},
                  "to": "graveyard", "reason": "destroy"}


def _parsed(ab):
    t = copy.deepcopy(ab)
    t["effect"][0]["effect"] = [PARSED_DESTROY]
    return t


EXPECTED = {"T1240": [_parsed(TRIGGER_ATTACK), _parsed(TRIGGER_BLOCK),
                      copy.deepcopy(STATIC_COST)]}


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive(e, attacker=None, blocker=None, stop_when=None, limit=1500):
    """汎用ドライバ（第319弾と同型）。attacker（defn）で
    プレイヤーを攻撃し、blocker（defn）のブロック肢が現れたら
    ブロックする。攻撃したターンの2つ先のターンまで進める。"""
    state = {"attacked": False, "attack_turn": None}
    for _ in range(limit):
        if stop_when is not None and stop_when(e):
            break
        if state["attacked"] and e.s.turn >= state["attack_turn"] + 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "attack":
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and not state["attacked"]:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            hit = [i for i, k in enumerate(keys)
                   if blocker and k.startswith(f"bz:{blocker}:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


def _pay_cost(e, defn, zone="hand", p=0):
    cid = next(c for c in e.zlist(zone, p)
               if e.s.cards[c].defn == defn)
    return e.chars_ro(cid)["pay_cost"]


# ---------- parse / validation ----------

def test_pilot449_proto_parse(rules):
    for cid, wants in EXPECTED.items():
        d = rules.cards[cid]
        for want in wants:
            assert want in d.abilities, cid


def test_pilot449_form_raw_parse():
    d = parse_card(copy.deepcopy(FORM), TABLES)
    assert d.name == NAME and d.power == 4000
    for ab in (_parsed(TRIGGER_ATTACK), _parsed(TRIGGER_BLOCK),
               STATIC_COST):
        assert ab in d.abilities


def test_pilot449_def_errors():
    bad_when = copy.deepcopy(TRIGGER_ATTACK)
    bad_when["when"] = {"event": "explode", "subject": "self"}
    bad_exists = copy.deepcopy(TRIGGER_ATTACK)
    bad_exists["if"] = {"not": {"exists": {"zone": "bz", "owner": "you",
                                           "filter": {"types": ["tamaseed"],
                                                      "bogus_key": 1}}}}
    bad_op = copy.deepcopy(TRIGGER_ATTACK)
    bad_op["effect"] = [{"op": "explode_card"}]
    for bad in (bad_when, bad_exists, bad_op):
        card = {"id": "TX449", "name": "x", "types": ["creature"],
                "civs": ["darkness"], "cost": 3, "power": 2000,
                "abilities": [bad]}
        with pytest.raises(DefError):
            parse_card(card, TABLES)


# ---------- 実挙動: 攻撃（タマシードなし → 自壊） ----------

def test_attack_no_tamaseed_destroyed_at_attack_end(rules):
    """T1240 が攻撃すると、タマシードが無ければ攻撃の後に
    破壊される。次のターンの最初の決定時点で既に墓地にいる。"""
    e = setup(rules, {"bz": ["T1240"]}, {})
    st = _drive(e, attacker="T1240")
    assert st["attacked"]
    assert "T1240" in _defns(e, "graveyard", 0)
    assert "T1240" not in _defns(e, "bz", 0)


def test_attack_with_tamaseed_survives(rules):
    """自分のタマシード（T189）が場にあれば、攻撃しても
    攻撃の後に破壊されない。"""
    e = setup(rules, {"bz": ["T1240", "T189"]}, {})
    st = _drive(e, attacker="T1240")
    assert st["attacked"]
    assert e.s.turn >= st["attack_turn"] + 2
    assert "T1240" in _defns(e, "bz", 0)
    assert "T1240" not in _defns(e, "graveyard", 0)


def test_attack_blocked_no_tamaseed_destroyed(rules):
    """T1240 が攻撃し、相手ブロッカー（T004・パワー3000）
    とのバトルに勝っても、タマシードが無ければ攻撃の後に
    破壊される。"""
    e = setup(rules, {"bz": ["T1240"]}, {"bz": ["T004"]})
    st = _drive(e, attacker="T1240", blocker="T004")
    assert st["attacked"]
    assert "T004" in _defns(e, "graveyard", 1)   # バトルで相手が落ちる
    assert "T1240" in _defns(e, "graveyard", 0)
    assert "T1240" not in _defns(e, "bz", 0)


# ---------- 実挙動: ブロック（タマシードなし → 自壊） ----------

def test_block_no_tamaseed_destroyed_at_attack_end(rules):
    """T1240 がブロックし、バトルに勝っても、タマシードが
    無ければその攻撃の後に破壊される。"""
    e = setup(rules, {"bz": ["T1240"]}, {"bz": ["T001"]})
    st = _drive(e, attacker="T001", blocker="T1240",
                stop_when=lambda e: "T1240" in _defns(e, "graveyard", 0))
    assert st["attacked"]
    assert "T001" in _defns(e, "graveyard", 1)   # 攻撃側はバトルで落ちる
    assert "T1240" in _defns(e, "graveyard", 0)   # 勝ったブロッカーも自壊
    assert "T1240" not in _defns(e, "bz", 0)


def test_block_with_tamaseed_survives(rules):
    """自分のタマシード（T189）が場にあれば、ブロックして
    バトルに勝っても破壊されない。"""
    e = setup(rules, {"bz": ["T1240", "T189"]}, {"bz": ["T001"]})
    st = _drive(e, attacker="T001", blocker="T1240")
    assert st["attacked"]
    assert "T001" in _defns(e, "graveyard", 1)   # 攻撃側はバトルで落ちる
    assert "T1240" in _defns(e, "bz", 0)
    assert "T1240" not in _defns(e, "graveyard", 0)


def test_no_attack_no_destroy(rules):
    """攻撃もブロックもしなければ、ターンが終わっても
    破壊されない。"""
    e = setup(rules, {"bz": ["T1240"]}, {})
    for _ in range(400):
        if e.s.turn >= 2:
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "T1240" in _defns(e, "bz", 0)
    assert "T1240" not in _defns(e, "graveyard", 0)


# ---------- 実挙動: デモニオの召喚コスト軽減（下限0） ----------

def test_cost_reduction_demonio(rules):
    """T1240 が場にいれば、手札のデモニオの召喚コストが
    1少なくなる。T826（コスト5→4）、T1241（コスト1→0）。
    非デモニオの T001（コスト2）は変わらない。"""
    e = setup(rules, {"bz": ["T1240"],
                      "hand": ["T826", "T1241", "T001"]}, {})
    assert _pay_cost(e, "T826") == 4
    assert _pay_cost(e, "T1241") == 0   # 下限0: cost_min 省略の確立形
    assert _pay_cost(e, "T001") == 2


def test_cost_reduction_without_source(rules):
    """T1240 が場に無ければ、手札のデモニオは元の
    コストのまま。"""
    e = setup(rules, {"hand": ["T826", "T1241", "T001"]}, {})
    assert _pay_cost(e, "T826") == 5
    assert _pay_cost(e, "T1241") == 1
    assert _pay_cost(e, "T001") == 2
