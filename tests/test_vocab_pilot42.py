"""語彙パイロット第42弾（フェーズ17-3）: 革命０トリガー（revolution_zero_trigger 単独18件）。

「クリーチャーが自分を攻撃する時、自分のシールドがひとつもなければ、手札から見せてもよい。
そうしたら、山札の上から1枚目を表向きにし、それが（文明）の進化ではないクリーチャーなら出し、
このクリーチャーをその上に置く」は、新しいエンジン機構ではなく既存の宣言型能力で表せる:
- kind: declare（手札から使用宣言する能力。攻撃宣言の窓で相手側に提示される）
- when: {event: attack, target: player} ＋ if: シールド0枚＆相手のターン
- 上1枚の条件判定は op: if の exists、重ねる処理は op: invade（侵略と同じ重ね処理）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dmsim.engine import scenario  # noqa: E402


def _game(rules, shields):
    return scenario.build(rules, {
        "p0": {"bz": ["T001"]},
        "p1": {"hand": ["T120"], "shield": shields, "deck": ["T005", "T005", "T005"]},
        "filler": "T001", "seed": 1, "deck_size": 20, "deck_exact": [False, True],
    })


def _drive_to_block(e, use_declare, first_attack_only=False):
    """P0 がプレイヤー攻撃を宣言。革命０の宣言が出たら use_declare に従い、ブロックは T120 で受ける。
    first_attack_only の時は、最初の攻撃が終わって相手のターンに入った時点で観察を打ち切る。"""
    seen_declare = False
    for _ in range(120):
        if any(e.s.cards[c].defn == "T001" for c in e.zlist("graveyard", 0)):
            break   # 攻撃クリーチャーがバトルで破壊された（＝ブロックが成立した）
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if first_attack_only and d["kind"] == "charge" and d["player"] == 1:
            break   # 最初の攻撃は終わった（シールドが割れた）ので観察終了
        if d["kind"] == "attack" and "attack:T001:player" in keys:
            e.answer([keys.index("attack:T001:player")])
            continue
        if any("declare:" in k for k in keys):
            seen_declare = True
            e.answer([j for j, k in enumerate(keys) if "declare:" in k] if use_declare else [])
            continue
        if d["kind"] == "block":
            hit = [j for j, k in enumerate(keys) if "T120" in k]
            e.answer(hit if hit else [keys.index("no_block")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
            continue
        e.answer(list(range(d["min"])))
    tops = [c for c in e.zlist("bz", 1) if e.s.cards[c].defn == "T120"]
    return seen_declare, (tops[0] if tops else None)


def test_revolution_zero_enters_stacked_and_blocks(rules):
    """シールド0で攻撃された時、宣言して上1枚（火の非進化）の上に重なって出て、ブロックできる。"""
    e = _game(rules, [])
    seen, top = _drive_to_block(e, use_declare=True)
    assert seen is True
    assert top is not None
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T005"]   # 山札の上が下に重なっている
    attacker = [c for c in e.zlist("graveyard", 0) if e.s.cards[c].defn == "T001"]
    assert attacker   # パワー9000のブロッカーが受けて、攻撃クリーチャーは破壊された


def test_revolution_zero_not_offered_with_shield_remaining(rules):
    """シールドが残っている時は宣言が提示されない。"""
    e = _game(rules, ["T001"])
    seen, top = _drive_to_block(e, use_declare=True, first_attack_only=True)
    assert seen is False
    assert top is None
    assert any(e.s.cards[c].defn == "T120" for c in e.zlist("hand", 1))
