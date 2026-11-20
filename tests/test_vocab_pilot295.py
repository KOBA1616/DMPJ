"""語彙パイロット第295弾: super_shield_plus（スーパー／ウルトラ・シールド・プラス）。

rejects の super_shield_plus 純粋3件（dmex06-010 / dmx19-s06 / dm28-s01。
dm28-s01 はラウンド328で第293弾のマナ進化Vが解けた後にこのギャップで
差し戻された行）。共通の不足は1点: 既存 op shield_plus（第31弾）が
「山札の上1枚を、選んだシールド1つの下に」固定で、
- 形A（dmex06-010 / dm28-s01）: 各シールドの下に1枚ずつ
- 形B（dmx19-s06、ウルトラシールド・プラス）: 1つのシールドの下に最大5枚まで
が表せない。

本弾の追加は op shield_plus の引数2つだけ（新規 op・面フィールド・
GameState フィールドなし＝ state.rs 変更なし。op 引数のためスキーマ再生成）:
- each: true — 自分の各シールドの下に1枚ずつ。1枚ずつ置く先のシールドを
  選びながら進め、山札がシールドより少なければ置ける分だけ置く。
- count: N — 選んだ1つのシールドの下に最大 N 枚まで。2枚目以降は1枚ずつ
  続けるかどうかを諮問する（「N枚まで」の枚数選択と等価。置くカードは
  裏向きのままなので途中で情報は増えない）。
複数回の諮問にまたがるため、進行（各形の済みシールド／対象と枚数）は
タスクの os に持つ（gachinko と同じ作法。op は回答のたびに頭から再実行
される）。差し込み処理そのものは既存の _shield_plus_tuck に共通化し、
素形（引数なし）の挙動は従来どおり。
"""
import copy
from pathlib import Path

import pytest
import yaml

from dmsim.cards.defs import DefError, load_tables, parse_card
from tests.conftest import setup

TABLES = load_tables()
PROTO = yaml.safe_load(open(Path(__file__).parent.parent / "data" / "cards"
                            / "proto.yaml", encoding="utf-8"))["cards"]

CIP = {"event": "move", "to": "bz", "subject": "self"}
EXPECTED = {
    "T890": {"kind": "trigger", "when": dict(CIP),
             "effect": [{"op": "may", "body": [{"op": "shield_plus", "each": True}]}]},
    "T891": {"kind": "trigger", "when": dict(CIP),
             "effect": [{"op": "may", "body": [{"op": "shield_plus", "count": 3}]}]},
    "T099": {"kind": "trigger", "when": dict(CIP),
             "effect": [{"op": "may", "body": [{"op": "shield_plus"}]}]},
}


def _proto(cid):
    return next(c for c in PROTO if c["id"] == cid)


def test_proto_forms_parse():
    for cid, want in EXPECTED.items():
        d = parse_card(copy.deepcopy(_proto(cid)), TABLES)
        assert want in d.abilities, cid


def _raw_with_effect(effect):
    return {"id": "TX295", "name": "検証用", "types": ["creature"],
            "civs": ["light"], "cost": 4, "power": 4000, "mana": 1,
            "abilities": [{"kind": "trigger", "when": dict(CIP),
                           "effect": effect}]}


def test_op_arg_validation():
    # 未知の引数は拒否
    with pytest.raises(DefError):
        parse_card(_raw_with_effect([{"op": "shield_plus", "all": True}]), TABLES)
    # each は bool のみ
    with pytest.raises(DefError):
        parse_card(_raw_with_effect([{"op": "shield_plus", "each": "yes"}]), TABLES)
    # count は int のみ
    with pytest.raises(DefError):
        parse_card(_raw_with_effect([{"op": "shield_plus", "count": "3"}]), TABLES)
    # 正しい形は通る
    parse_card(_raw_with_effect([{"op": "shield_plus", "each": True}]), TABLES)
    parse_card(_raw_with_effect([{"op": "shield_plus", "count": 5}]), TABLES)


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


def _play_drive(cid, yes_no):
    """手札から cid を出し、yes_no には yes_no(回数) の方針で答えるドライバ。"""
    state = {"yn": 0}

    def drive(e, d, keys):
        if d["kind"] == "yes_no":
            state["yn"] += 1
            ans = yes_no(state["yn"])
            e.answer([keys.index("yes" if ans else "no")])
            return True
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys)
                   if cid in k and not k.startswith("charge:")]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    return drive


def _under_counts(e, p=0):
    return {c: len(e.s.cards[c].under) for c in e.zlist("shield", p)}


def test_each_all_shields(rules):
    """形A: 5つのシールドすべてに1枚ずつ入り、束の数は増えず山札が5枚減る。"""
    e = setup(rules, {"hand": ["T890"], "mana": ["T004"] * 4}, {})
    n_shields = len(e.zlist("shield", 0))
    deck0 = len(e.zlist("deck", 0))
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T890"
                                  for c in e.zlist("bz", 0)),
                   _play_drive("T890", lambda n: True))
    assert _settle(e, lambda: sum(_under_counts(e).values()) == n_shields,
                   _play_drive("T890", lambda n: True))
    counts = _under_counts(e)
    assert sorted(counts.values()) == [1] * n_shields      # 各束に1枚ずつ
    assert len(e.zlist("shield", 0)) == n_shields          # 束は1つと数える
    assert len(e.zlist("deck", 0)) == deck0 - n_shields
    for top, n in counts.items():                          # top_of の整合
        for u in e.s.cards[top].under:
            assert e.s.cards[u].top_of == top


def test_each_short_deck(rules):
    """形A・山札不足: 山札2枚なら2つのシールドにだけ入り、解決は潰れない。"""
    e = setup(rules, {"hand": ["T890"], "mana": ["T004"] * 4}, {},
              deck_left=[2, None])
    assert len(e.zlist("deck", 0)) == 2
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T890"
                                  for c in e.zlist("bz", 0)),
                   _play_drive("T890", lambda n: True))
    assert _settle(e, lambda: sum(_under_counts(e).values()) == 2,
                   _play_drive("T890", lambda n: True))
    assert len(e.zlist("deck", 0)) == 0
    assert sorted(_under_counts(e).values()) == [0, 0, 0, 1, 1]


def test_each_decline(rules):
    """形A・辞退: may を断れば何も入らず山札も減らない。"""
    e = setup(rules, {"hand": ["T890"], "mana": ["T004"] * 4}, {})
    deck0 = len(e.zlist("deck", 0))
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T890"
                                  for c in e.zlist("bz", 0)),
                   _play_drive("T890", lambda n: False))
    # 誘発が処理し終わるまで進める（相手のターンに入れば解決済み）
    assert _settle(e, lambda: e.s.turn >= 2, _play_drive("T890", lambda n: False))
    assert sum(_under_counts(e).values()) == 0
    assert len(e.zlist("deck", 0)) >= deck0 - 1   # 減っても相手のドロー分まで


def test_count_full(rules):
    """形B: 選んだ1つのシールドの下に上限3枚まで入る。他の束には入らない。"""
    e = setup(rules, {"hand": ["T891"], "mana": ["T004"] * 4}, {})
    first = e.zlist("shield", 0)[0]
    deck0 = len(e.zlist("deck", 0))
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T891"
                                  for c in e.zlist("bz", 0)),
                   _play_drive("T891", lambda n: True))
    assert _settle(e, lambda: len(e.s.cards[first].under) == 3,
                   _play_drive("T891", lambda n: True))
    counts = _under_counts(e)
    assert counts[first] == 3
    assert sum(counts.values()) == 3
    assert len(e.zlist("deck", 0)) == deck0 - 3
    assert len(e.zlist("shield", 0)) == 5


def test_count_stop_early(rules):
    """形B・途中停止: 1枚入れた後に断れば、入るのは1枚だけ。"""
    e = setup(rules, {"hand": ["T891"], "mana": ["T004"] * 4}, {})
    first = e.zlist("shield", 0)[0]
    # yes_no 1回目 = 誘発の may（yes）、2回目 = もう1枚（no）
    drive = _play_drive("T891", lambda n: n == 1)
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T891"
                                  for c in e.zlist("bz", 0)), drive)
    assert _settle(e, lambda: len(e.s.cards[first].under) == 1, drive)
    assert _settle(e, lambda: e.s.turn >= 2, drive)   # 解決が終わるまで進める
    assert _under_counts(e)[first] == 1
    assert sum(_under_counts(e).values()) == 1


def test_count_short_deck(rules):
    """形B・山札不足: 山札2枚なら上限3でも2枚で止まり、余分な諮問は出ない。"""
    e = setup(rules, {"hand": ["T891"], "mana": ["T004"] * 4}, {},
              deck_left=[2, None])
    first = e.zlist("shield", 0)[0]
    drive = _play_drive("T891", lambda n: True)
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T891"
                                  for c in e.zlist("bz", 0)), drive)
    assert _settle(e, lambda: len(e.s.cards[first].under) == 2, drive)
    assert len(e.zlist("deck", 0)) == 0
    assert sum(_under_counts(e).values()) == 2
