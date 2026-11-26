"""語彙パイロット第380弾: up_to_cost_reduction 残り1件（ドリフト）。

対象は pure 1件すべて: dm23rp4x-tf03
西南の超人 / 断断打つべしナウ（ツインパクト）。

up_to_cost_reduction 自体は第347弾でドリフト確立済み
（「最大N少なく」は固定の mod {cost: -N} として扱い、
下限0はエンジン既定のため省略する作法）。第347弾は
dm23rp4x-tf03 を「partial が完全に空で登録の基礎がない」
として対象外にしたが、現在の partial は両面とも
組立て済み（クリーチャー面のセイバー置換＋呪文面の
choose→tap→modify、proto T147・dm20-038 と同型という
注記つき）で、前提が消えている。残る未解決は
クリーチャー面の召喚コスト軽減条項だけで、これは
登録済み dmbd02-014 西南の超人（同一カードの単体版）と
同文であり、第347弾の確立形がそのまま使える。本弾は
ツインパクトとしての組立て（両面）を実挙動で検証する。

確立形:
- クリーチャー面 abilities = [static {affects:
  {zone: hand, owner: you, filter: {races: [ジャイアント]}},
  mod: {cost: -2}}（第347弾・dmbd02-014 登録形と同一）,
  セイバー置換（partial の組立て済み・dmbd02-014 登録形と
  完全同一）] の2件（公式テキストの条項順）。
- 呪文面 spell = partial の組立て済み形
  [choose {zone: bz, owner: you, filter: {types: [creature]},
  count: 1} as t, tap {ref: t},
  modify {select: {ref: t}, mod: {must_be_attacked: true},
  duration: until_next_own_turn_start}]、keywords [s_trigger]。
- top の text は面テキストを「 ／ 」で連結したもの
  （dm23bd6-003 等のツインパクト登録形の作法。rejects 行の
  top text はクリーチャー面分しか無いため、ラウンド415では
  この連結形で補完すること）。

proto: T1134（dm23rp4x-tf03 型ツインパクト全体）。
判別役は既存 proto を流用: T356（ジャイアント・コスト7）/
T341（ジャイアント・コスト3）/ T005（非ジャイアント・
スピードアタッカー）/ T001（自然の素・呪文面の選択先）/
T710（単体破壊呪文・セイバー判別用）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接包む（第319弾以降の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

COST_STATIC = {
    "kind": "static",
    "affects": {"zone": "hand", "owner": "you",
                "filter": {"races": ["ジャイアント"]}},
    "mod": {"cost": -2},
}
SABER = {
    "kind": "replace", "optional": True,
    "when": {"event": "move", "to": "graveyard", "reason": "destroy",
             "subject": {"owner": "you",
                         "filter": {"races": ["ジャイアント"]},
                         "other": True}},
    "instead": [{"op": "destroy", "select": {"ref": "self", "count": 1}}],
}
FACE0_TEXT = ("自分のジャイアント・クリーチャーの召喚コストを最大２"
              "少なくしてもよい。ただし、コストは０以下にはならない。"
              "セイバー：ジャイアント（自分のジャイアントが破壊される時、"
              "このクリーチャーをかわりに破壊してもよい）")
FACE0 = {
    "name": "西南の超人",
    "types": ["creature"], "civs": ["nature"], "cost": 4, "power": 3000,
    "races": ["ジャイアント", "サムライ"],
    "text": FACE0_TEXT,
    "abilities": [COST_STATIC, SABER],
}
SPELL_OPS = [
    {"op": "choose",
     "select": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}, "count": 1},
     "as": "t"},
    {"op": "tap", "select": {"ref": "t"}},
    {"op": "modify", "select": {"ref": "t"},
     "mod": {"must_be_attacked": True},
     "duration": "until_next_own_turn_start"},
]
FACE1_TEXT = ("S・トリガー / 自分のクリーチャーを１体、タップする。"
              "次の自分のターンのはじめまで、相手のクリーチャーが"
              "攻撃する時、可能ならそのクリーチャーを攻撃する。")
FACE1 = {
    "name": "断断打つべしナウ",
    "types": ["spell"], "civs": ["nature"], "cost": 1,
    "keywords": ["s_trigger"],
    "text": FACE1_TEXT,
    "spell": SPELL_OPS,
}
SPELL_TOP_TEXT = ("S・トリガー 自分のクリーチャーを１体、タップする。"
                  "次の自分のターンのはじめまで、相手のクリーチャーが"
                  "攻撃する時、可能ならそのクリーチャーを攻撃する。")
TOP_TEXT = FACE0_TEXT + " ／ " + SPELL_TOP_TEXT


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1134")
    assert c["name"] == "西南の超人 / 断断打つべしナウ"
    assert c["faces"] == [FACE0, FACE1]
    assert c["mana"] == 1
    assert c["text"] == TOP_TEXT
    parse_card(c, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _drive_to_main(e, player=0, limit=300):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] == "main" and d.get("player") == player:
            return d, _keys(d)
        if "pass" in _keys(d):
            e.answer([_keys(d).index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("main never came")


def test_giant_discount(rules):
    # ジャイアント T356（コスト7）が 5 で召喚できる
    e = _build(rules, {"bz": ["T1134"], "hand": ["T356"],
                       "mana": ["T001"] * 5}, {})
    d, keys = _drive_to_main(e)
    assert "play:T356" in keys
    # マナ4では届かない
    e = _build(rules, {"bz": ["T1134"], "hand": ["T356"],
                       "mana": ["T001"] * 4}, {})
    d, keys = _drive_to_main(e)
    assert "play:T356" not in keys


def test_non_giant_not_discounted(rules):
    # ジャイアントでない T005（火・コスト3）は軽減を受けない
    # （漏れれば 1 になってマナ2で出てしまう）
    e = _build(rules, {"bz": ["T1134"], "hand": ["T005"],
                       "mana": ["T005", "T001"]}, {})
    d, keys = _drive_to_main(e)
    assert "play:T005" not in keys


def test_pay_cost_values(rules):
    # T341（ジャイアント・コスト3）の pay_cost が発生源ありで 1、
    # なしで 3。T356（コスト7）は発生源ありで 5
    e = _build(rules, {"bz": ["T1134"], "hand": ["T341", "T356"]}, {})
    for defn, want in (("T341", 1), ("T356", 5)):
        cid = next(c for c in e.zlist("hand", 0)
                   if e.s.cards[c].defn == defn)
        assert e.chars_ro(cid)["pay_cost"] == want
    e = _build(rules, {"hand": ["T341"]}, {})
    cid = next(c for c in e.zlist("hand", 0)
               if e.s.cards[c].defn == "T341")
    assert e.chars_ro(cid)["pay_cost"] == 3


def _saber_game(rules, accept):
    """p1 の T710 が p0 の T356 を破壊する場面を作り、
    セイバー置換の判断で accept / decline を選んで結果を返す。"""
    e = _build(rules, {"bz": ["T1134", "T356"]},
               {"hand": ["T710"], "mana": ["T005"]})
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        k = _keys(d)
        if d["kind"] == "main" and d.get("player") == 1 \
                and "play:T710" in k:
            e.answer([k.index("play:T710")])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "choose_cards" \
                and any(x.startswith("bz:T356") for x in k):
            e.answer([k.index(next(x for x in k
                                   if x.startswith("bz:T356")))])
        elif d["kind"] == "choose_replacement":
            assert d.get("player") == 0
            assert any(x.startswith("replace:T1134") for x in k), k
            e.answer([k.index(next(x for x in k
                                   if x.startswith("replace:T1134")))]
                     if accept else [k.index("decline")])
            # 置換（または元の破壊）が解決しきるまで進める
            for _ in range(60):
                d2 = e.advance()
                if d2 is None:
                    break
                if "pass" in _keys(d2):
                    e.answer([_keys(d2).index("pass")])
                else:
                    e.answer(list(range(d2["min"])))
            return e
        elif "pass" in k:
            e.answer([k.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("replacement decision never came")


def test_saber_accept(rules):
    # セイバーを使う: T356 は残り、かわりに T1134 が破壊される
    e = _saber_game(rules, accept=True)
    assert "T356" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert "T1134" in [e.s.cards[c].defn
                       for c in e.zlist("graveyard", 0)]


def test_saber_decline(rules):
    # セイバーを使わない: T356 が破壊され、T1134 は残る
    e = _saber_game(rules, accept=False)
    assert "T1134" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert "T356" in [e.s.cards[c].defn
                      for c in e.zlist("graveyard", 0)]


def _p1_attack_options(rules, cast):
    """p0 が呪文面を唱えた（または唱えなかった）後、
    p1 の T005 の攻撃選択肢と T001 のタップ状態を返す。"""
    p0 = {"bz": ["T001"], "mana": ["T001"]}
    if cast:
        p0["hand"] = ["T1134"]
    e = _build(rules, p0, {"bz": ["T005"]})
    done = False
    for _ in range(400):
        d = e.advance()
        assert d is not None, "game ended"
        k = _keys(d)
        if cast and not done and d["kind"] == "main" \
                and d.get("player") == 0 and "play:T1134:1" in k:
            done = True
            e.answer([k.index("play:T1134:1")])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif cast and done and any(x.startswith("bz:T001") for x in k) \
                and d.get("player") == 0:
            e.answer([k.index(next(x for x in k
                                   if x.startswith("bz:T001")))])
        elif d["kind"] == "attack" and d.get("player") == 1:
            cid = next(c for c in e.bz_tops(0)
                       if e.s.cards[c].defn == "T001")
            return [x for x in k if x.startswith("attack:T005:")], \
                e.s.cards[cid].tapped
        elif "pass" in k:
            e.answer([k.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("p1 attack decision never came")


def test_spell_face_taunt(rules):
    # 唱えた場合: 選んだ T001 がタップし、相手は可能なら
    # そのクリーチャーを攻撃しなければならない
    opts, tapped = _p1_attack_options(rules, cast=True)
    assert tapped
    assert "attack:T005:T001" in opts, opts
    assert "attack:T005:player" not in opts, opts
    # 唱えない場合: 誘引は無くプレイヤーを攻撃できる
    opts, tapped = _p1_attack_options(rules, cast=False)
    assert not tapped
    assert "attack:T005:player" in opts, opts
