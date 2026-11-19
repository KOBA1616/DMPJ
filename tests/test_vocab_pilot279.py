"""語彙パイロット第279弾: alt_cost_mana_civilization_condition
（マナゾーンの各文明を条件とする代替コスト）。

rejects の alt_cost_mana_civilization_condition 純粋4件はいずれも同形:
- dm25ex3-054 ～破壊と殺戮の連鎖～（光・水・闇）
- dm25ex3-057 大集合！アカネ&アサギ&コハク（光・水・自然）
- dm25ex3-062 哀蛇の虚 シンロッチ（闇・火・自然）
- dm25ex3-060 トレース＝トレーシー（水・闇・火）
「自分のマナゾーンに（3文明）の各文明があれば、このクリーチャーを
[cc02]支払って召喚してもよい」＋ NEO進化。partial は他の条項まで
完成しており、不足は代替コストの条件だけ。

本弾は新語彙を足さないイディオム確立弾（第247/255/276弾と同型）:
- 条件は既存の alt_cost.if（第〜弾で導入済み。converted に13件の先例）に
  cond の all ＋ exists {zone: mana, owner: you, filter: {civs: [文明]}}
  の3連を載せる。eval_cond は all/any と exists（candidates）を実装済みで、
  多色マナ1枚はその各文明について exists を満たす（公式ルールどおり
  多色カードは各文明を持つ）。
- [cc02]（無色2コスト）の支払い文明は civs: [] が正表現。bazurenda
  [cc02] の登録先例（dm23bd6-015 等）がすべて civs: [] で、civs に
  "zero" を入れると _mana_choices の need が「ゼロ文明のマナでしか
  払えない」意味になる（実測: civs [zero] の dm24bd2-016 は自然マナ
  2枚では play 選択肢自体が出ず、無色マナでのみ出る）。partial の
  alt_cost.civs: [zero, zero] は変換側の誤記で、ラウンド314は
  civs: [] に直して提出すること。
- エンジン変更なし・スキーマ再生成なし（cond の all/exists と
  alt_cost.if はスキーマ登録済み）。新規 GameState フィールドなし。

既知の制限（本弾の対象外）: NEO進化と代替コストの併用選択肢
（:neo:alt）は生成されない。free_if と NEO の併用（dm25rp2-068 等の
登録済みカード）でも同じで、エンジン全体の既存性質。:neo は通常
コスト、:alt は通常召喚（重ねない）として働く。

プロト:
- T792 試験用三文明NEO獣（光/水/闇・コスト3・NEO進化・本弾の代替コスト形）
"""
import pytest
from tests.conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card

TABLES = load_tables()
CIVS3 = ["light", "water", "darkness"]


def _cond(civs):
    return {"all": [{"exists": {"zone": "mana", "owner": "you",
                                 "filter": {"civs": [c]}}} for c in civs]}


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _tapped_mana(e, p=0):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def _main_keys(e):
    """charge を pass して最初の main 決定の選択肢キーを返す。"""
    d = e.advance()
    for _ in range(12):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main":
            return keys
        e.answer([keys.index("pass")] if "pass" in keys else [0])
        d = e.advance()
    raise AssertionError("main not reached")


class _Driver:
    """汎用ドライバ（第278弾のものと同形）。"""

    def __init__(self, play=None, choose=None):
        self.play = play
        self.choose = choose
        self.seen = []

    def run(self, e, stop, limit=800):
        for _ in range(limit):
            d = e.advance()
            assert d is not None, "game ended"
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
            self.seen.append(kind)
            if kind == "choose_cards" and self.choose is not None:
                ans = self.choose(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "main" and self.play is not None:
                ans = self.play(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "declare_strigger":
                e.answer([])
            elif kind == "declare_sback":
                e.answer([])
            elif kind == "choose_breaker":
                e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
            elif kind == "choose_shields":
                e.answer(list(range(d.get("min", 0))))
            elif kind == "pay_mana":
                e.answer([0])
            elif kind == "yes_no":
                e.answer([keys.index("yes")])
            elif kind == "order_pending":
                e.answer([0])
            elif kind == "block":
                if "no_block" in keys:
                    e.answer([keys.index("no_block")])
                else:
                    e.answer(list(range(d.get("min", 0))))
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
            if stop(e):
                return
        raise AssertionError("limit reached")


def _play_once(key):
    seen = {}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and not seen.get("opt"):
            seen["opt"] = True
            return [keys.index(key)]
        return None

    return play


# ---------- parse / validation ----------

def test_pilot279_proto_parse():
    rules = load_rules()
    d = rules.cards["T792"]
    assert d.civs == CIVS3 and d.cost == 3 and d.neo
    assert d.alt_cost == {"cost": 2, "civs": [], "if": _cond(CIVS3)}


def test_alt_cost_form_validation():
    base = {"id": "X279", "name": "検証用", "types": ["creature"],
            "civs": CIVS3, "cost": 3, "power": 3000, "neo": True,
            "evolve_from": {"civs": CIVS3},
            "alt_cost": {"cost": 2, "civs": [], "if": _cond(CIVS3)}}
    d = parse_card(base, TABLES)   # 本弾の形は通る
    assert d.alt_cost["if"] == _cond(CIVS3)
    bad = dict(base)
    bad["alt_cost"] = {"cost": 2, "civs": [],
                       "if": {"all": [{"exists2": {"zone": "mana"}}]}}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)   # 未知の cond キーは弾く


# ---------- 選択肢の生成: 条件の成否 ----------

def test_alt_offered_when_all_civs_present():
    """マナに光・水・闇が各1枚あれば :alt が出る（通常召喚も可）。"""
    e = setup(load_rules(), {"hand": ["T792"],
                             "mana": ["T004", "T010", "T008"]},
              {"bz": ["T001"]})
    keys = _main_keys(e)
    assert "play:T792:alt" in keys
    assert "play:T792" in keys


def test_alt_not_offered_when_civ_missing():
    """闇が無ければ :alt は出ない（通常召喚も闇不足で不可）。"""
    e = setup(load_rules(), {"hand": ["T792"],
                             "mana": ["T004", "T010", "T001"]},
              {"bz": ["T001"]})
    keys = _main_keys(e)
    assert "play:T792:alt" not in keys
    assert "play:T792" not in keys


def test_alt_offered_with_multicolor_covering_two_civs():
    """多色マナ1枚（光/水）はその各文明について条件を満たす。"""
    e = setup(load_rules(), {"hand": ["T792"],
                             "mana": ["T030", "T008", "T001"]},
              {"bz": ["T001"]})
    assert "play:T792:alt" in _main_keys(e)


def test_alt_offered_with_single_tricolor_mana():
    """3文明を持つマナ1枚だけで3文明すべての条件が満たせる。
    通常召喚は文明ごとに別々のマナが要るため、この配置では不可。"""
    e = setup(load_rules(), {"hand": ["T792"], "mana": ["T792", "T001"]},
              {"bz": ["T001"]})
    keys = _main_keys(e)
    assert "play:T792:alt" in keys
    assert "play:T792" not in keys


def test_alt_ignores_opponent_mana():
    """相手のマナゾーンの文明は数えない（owner: you）。
    自分のマナに闇が無ければ、相手のマナに闇があっても :alt は出ない。
    （main 決定を提示させるため、支払える filler T001 を引ける配置にする。
    pass だけの main は build が読み飛ばす＝第309弾の罠。）"""
    e = setup(load_rules(), {"hand": ["T792"],
                             "mana": ["T004", "T010", "T001", "T001"]},
              {"bz": ["T001"], "mana": ["T008", "T008", "T008"]})
    keys = _main_keys(e)
    assert "play:T001" in keys          # main が提示されていることの確認
    assert "play:T792:alt" not in keys


# ---------- 実挙動: 支払い ----------

def test_alt_payment_costs_two_generic():
    """:alt で召喚するとタップするマナは2枚（どの文明でもよい）。"""
    e = setup(load_rules(), {"hand": ["T792"],
                             "mana": ["T004", "T010", "T008"]},
              {"bz": ["T001"]})
    drv = _Driver(play=_play_once("play:T792:alt"))
    drv.run(e, lambda ev: "T792" in _defns(ev, "bz", 0) and _quiet(ev))
    assert _tapped_mana(e) == 2


def test_normal_payment_costs_three():
    """通常召喚は3枚タップ（光・水・闇を各1枚含む）。"""
    e = setup(load_rules(), {"hand": ["T792"],
                             "mana": ["T004", "T010", "T008"]},
              {"bz": ["T001"]})
    drv = _Driver(play=_play_once("play:T792"))
    drv.run(e, lambda ev: "T792" in _defns(ev, "bz", 0) and _quiet(ev))
    assert _tapped_mana(e) == 3


def test_neo_play_stacks_at_normal_cost():
    """:neo は通常コストで進化元に重なる（:alt との併用選択肢は無い）。"""
    e = setup(load_rules(), {"bz": ["T004"], "hand": ["T792"],
                             "mana": ["T004", "T010", "T008"]},
              {"bz": ["T001"]})

    def choose(e, d):
        for i, o in enumerate(d["options"]):
            if o["key"].startswith("bz:T004"):
                return [i]
        return None

    drv = _Driver(play=_play_once("play:T792:neo"), choose=choose)
    drv.run(e, lambda ev: "T792" in _defns(ev, "bz", 0) and _quiet(ev))
    assert "T004" not in _defns(e, "bz", 0)   # T004 は下に重なった
    assert _tapped_mana(e) == 3
