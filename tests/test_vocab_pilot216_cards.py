"""第216弾の登録カード（ラウンド252）の確認。

- 6枚が converted.yaml の登録形で parse できる（dm23ex3-or2 は差し戻し）
- dm23rp4x-08a: CIP で墓地枚数以下のコストの他クリーチャーを全てタップして持ち主のマナへ／
  終極宣言で墓地のアビスを出す
- dm26rp1-tr003: CIP で相手2体をタップし、次の相手ターン開始時にアンタップさせない
- dm23rp4x-01b: 終極宣言のモードを4回選ぶ（シールド化＋墓地回収／破壊＋ドロー）
- dm26sd1-q001: 終極宣言で手札枚数ドロー＋マナ枚数ぶんマナ加速
- dm23rp4x-06a: CIP でパワー10000以下を破壊して2枚引く／終極宣言でマジック -4 と唱えた時ドロー
- dm26sd1-g003: 終極宣言で自シールドを全部ブレイクし、敗北しなくなる（対照: 宣言なしでは敗北）
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
IDS = ("dm23rp4x-08a", "dm26rp1-tr003", "dm23rp4x-01b",
       "dm26sd1-q001", "dm23rp4x-06a", "dm26sd1-g003")


@pytest.fixture(scope="module")
def converted():
    return {c["id"]: c for c in _conv_cache.all_cards(str(CONVERTED))}


@pytest.fixture(scope="module")
def rules():
    return _conv_cache.full_rules()


def test_build_forms_parse(converted):
    for cid in IDS:
        assert cid in converted, cid
        parse_card(converted[cid], TABLES)


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _run(e, plays=None, yes=(), modes=(), stop=None, on_decision=None, limit=2500):
    """plays: {player: [key,...]}、yes/modes は出現順のキュー。
    stop() が真で次の main/charge 決定が来たら、pass して戻る。"""
    plays = {p: list(v) for p, v in (plays or {}).items()}
    yes = list(yes)
    modes = list(modes)
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        if on_decision:
            on_decision(d, keys)
        if stop and stop() and d["kind"] in ("main", "charge"):
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
            return
        p = d.get("player")
        if d["kind"] == "yes_no":
            ans = yes.pop(0) if yes else True
            e.answer([0] if ans else [1])
        elif d["kind"] == "choose_mode":
            idx = modes.pop(0) if modes else 0
            e.answer([idx])
        elif d["kind"] in ("main", "attack"):
            todo = plays.get(p) or []
            hit = next((k for k in todo if k in keys), None)
            if hit is not None:
                todo.remove(hit)
                e.answer([keys.index(hit)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif d.get("min") == 0 and d.get("max", 0) >= 1:
            e.answer([0])   # 「N体まで」等の任意選択は1つ取る
        else:
            e.answer(list(range(d["min"])))


def test_08a_cip_mass_mana_put(rules):
    e = build(rules, {"p0": {"hand": ["dm23rp4x-08a"],
                             "mana": ["T050"] * 3 + ["T002"] * 4,
                             "bz": ["T002"], "graveyard": ["T002"] * 3},
                      "p1": {"bz": ["T551", "T534"]},
                      "filler": "T002", "seed": 1, "deck_size": 20})
    done = lambda: "dm23rp4x-08a" in _defns(e, "bz", 0) and "T551" in _defns(e, "mana", 1)
    _run(e, plays={0: ["play:dm23rp4x-08a"]}, yes=[True], stop=done)
    assert done()
    # 相手の T551（コスト1）は相手のマナへ、自分の T002（コスト2）も自分のマナへ。
    # T551 自身のタップは持ち主のターン開始で解けてしまうため観測できないが、
    # 同じ move で置かれた自分の T002 は「支払いの7枚＋タップして置かれた1枚」で
    # 全8枚タップしていることから確認する（タップせず置かれれば1枚だけ起きている）。
    assert len(e.zlist("mana", 0)) == 8          # 支払いの7枚＋CIPで置いた1枚
    assert all(e.s.cards[c].tapped for c in e.zlist("mana", 0))
    assert "T534" in _defns(e, "bz", 1)          # コスト5は墓地3枚の上限を超えるので残る


def test_08a_declaration_summons_from_graveyard(rules):
    e = build(rules, {"p0": {"bz": ["dm23rp4x-08a"], "graveyard": ["dm23rp4x-08a"]},
                      "p1": {}, "filler": "T002", "seed": 1, "deck_size": 20})
    _run(e, yes=[True, True],
         stop=lambda: _defns(e, "bz", 0).count("dm23rp4x-08a") >= 2)
    assert _defns(e, "bz", 0).count("dm23rp4x-08a") == 2
    assert e.eval_cond({"marked": {"name": "final_declaration", "scope": "game"}},
                       {"you": 0, "self": None, "vars": {}})


def test_tr003_cip_tap_and_freeze(rules):
    e = build(rules, {"p0": {"hand": ["dm26rp1-tr003"], "mana": ["T030"] * 10},
                      "p1": {"bz": ["T002", "T060"]},
                      "filler": "T002", "seed": 1, "deck_size": 20})
    snaps = {}

    def hook(d, keys):
        if d["kind"] == "charge" and d.get("player") == 1 and e.s.turn not in snaps:
            snaps[e.s.turn] = {e.s.cards[c].defn: e.s.cards[c].tapped
                               for c in e.zlist("bz", 1)
                               if e.s.cards[c].controller == 1}
    _run(e, plays={0: ["play:dm26rp1-tr003"]}, on_decision=hook,
         stop=lambda: 4 in snaps)
    assert snaps[2] == {"T002": True, "T060": True}     # CIP でタップ
    assert snaps[4] == {"T002": False, "T060": False}   # 凍結は次の相手ターン開始時の1回だけ


def test_01b_declaration_modal(rules):
    e = build(rules, {"p0": {"bz": ["dm23rp4x-01b"], "graveyard": ["T002"]},
                      "p1": {"bz": ["T002"]},
                      "filler": "T002", "seed": 1, "deck_size": 20})
    seen = {}

    def hook(d, keys):
        if d["kind"] == "yes_no" and "hand0" not in seen:
            seen["hand0"] = len(e.zlist("hand", 0))
    _run(e, yes=[True], modes=[1, 0, 1, 0], on_decision=hook,
         stop=lambda: len(e.zlist("shield", 0)) >= 7
         and len(e.zlist("hand", 0)) >= seen.get("hand0", 0) + 4)
    assert "T002" in _defns(e, "graveyard", 1)              # モードAで破壊
    assert len(e.zlist("shield", 0)) == 7                   # モードB×2でシールド化
    # 手札: ターンドロー1＋モードAのドロー2＋モードBの墓地回収1
    assert len(e.zlist("hand", 0)) == seen["hand0"] + 4


def test_q001_declaration_draw_and_mana(rules):
    e = build(rules, {"p0": {"bz": ["dm26sd1-q001"], "hand": ["T002", "T002"],
                             "mana": ["T002"] * 3},
                      "p1": {}, "filler": "T002", "seed": 1, "deck_size": 20})
    seen = {}

    def hook(d, keys):
        if d["kind"] == "yes_no" and "hand0" not in seen:
            seen["hand0"] = len(e.zlist("hand", 0))
    _run(e, yes=[True], on_decision=hook,
         stop=lambda: len(e.zlist("mana", 0)) >= 6 and len(e.zlist("hand", 0)) >= 5)
    assert seen["hand0"] == 2
    assert len(e.zlist("hand", 0)) == 2 + 2 + 1   # 宣言ドロー（手札2枚ぶん）＋ターンドロー
    assert len(e.zlist("mana", 0)) == 6           # マナ3枚ぶん加速


def test_06a_cip_destroy_and_draw(rules):
    e = build(rules, {"p0": {"hand": ["dm23rp4x-06a"],
                             "mana": ["T030"] * 4 + ["T060"] * 3},
                      "p1": {"bz": ["T201", "T397"]},
                      "filler": "T002", "seed": 1, "deck_size": 20})
    seen = {}

    def hook(d, keys):
        if d["kind"] == "main" and "play:dm23rp4x-06a" in keys and "h" not in seen:
            seen["h"] = len(e.zlist("hand", 0))
    _run(e, plays={0: ["play:dm23rp4x-06a"]}, on_decision=hook,
         stop=lambda: "T201" in _defns(e, "graveyard", 1))
    assert "T201" in _defns(e, "graveyard", 1)    # パワー9000は破壊
    assert "T397" in _defns(e, "bz", 1)           # パワー12000は対象外
    assert len(e.zlist("hand", 0)) == seen["h"] + 1   # 06a が離れて -1、ドロー +2


@pytest.mark.xfail(reason="pilot274 と同じ 112.2b（有色のコスト0でも文明数ぶんタップ）対 第292弾（実効0=支払いなし）の競合。koba の判断待ち", strict=False)
def test_06a_declaration_discount_and_cast_draw(rules):
    e = build(rules, {"p0": {"bz": ["dm23rp4x-06a"], "hand": ["dm23rp1-036"],
                             "mana": ["T030"] * 4},
                      "p1": {}, "filler": "T002", "seed": 1, "deck_size": 20})
    cid = next(c for c in e.zlist("hand", 0) if e.s.cards[c].defn == "dm23rp1-036")
    seen = {}

    def hook(d, keys):
        if d["kind"] == "yes_no" and "before" not in seen:
            # 宣言の may が出た時点（解決前）ではまだコスト2
            seen["before"] = min(len(c) for c in e._mana_choices(cid, 0))
        if d["kind"] == "main" and d.get("player") == 0 and "combos" not in seen:
            seen["combos"] = e._mana_choices(cid, 0)
            seen["pay_cost"] = e.chars(cid)["pay_cost"]
            seen["h"] = len(e.zlist("hand", 0))
        if d["kind"] == "yes_no" and seen.get("combos") is not None:
            seen["cast_may"] = True
    _run(e, plays={0: ["play:dm23rp1-036"]}, yes=[True, True], on_decision=hook,
         stop=lambda: seen.get("cast_may") and "dm23rp1-036" in _defns(e, "graveyard", 0))
    assert seen["before"] == 2                                 # 宣言前はコスト2
    # 宣言の modify で pay_cost は 0（-4、下限0）。支払いの組は、コスト0でも
    # 文明ぶんのマナをタップさせるエンジンの既存規則により1枚が残る。
    assert seen["pay_cost"] == 0
    assert min(len(c) for c in seen["combos"]) == 1
    assert seen.get("cast_may")                                # 唱えた時ドローの may が出た
    assert len(e.zlist("hand", 0)) == seen["h"]                # 呪文 -1＋ドロー +1


def test_g003_declaration_break_and_no_lose(rules):
    e = build(rules, {"p0": {"bz": ["dm26sd1-g003"]},
                      "p1": {"bz": ["T542"]},
                      "filler": "T002", "seed": 1, "deck_size": 20})
    _run(e, plays={1: ["attack:T542:player"]}, yes=[True],
         stop=lambda: e.s.turn >= 3)
    assert len(e.zlist("shield", 0)) == 0       # 宣言で全ブレイク（手札へ）
    assert e.s.result is None                   # シールド0で攻撃されても敗北しない

    # 対照: 宣言がなければ、シールド0への攻撃で敗北する
    e = build(rules, {"p0": {"shield": []},
                      "p1": {"bz": ["T542"]},
                      "filler": "T002", "seed": 1, "deck_size": 20})
    _run(e, plays={1: ["attack:T542:player"]},
         stop=lambda: e.s.result is not None or e.s.turn >= 3)
    assert e.s.result is not None and e.s.result["winner"] == 1
