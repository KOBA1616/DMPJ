"""語彙パイロット第48弾の検証。

mod `cost_may` の `must: true`（強制・ターン1回の軽減）:
「各ターン、自分の〜１体目/１枚目のコストを少なくする」のような強制形は、
任意形（第9弾）と違い確認を出さずに適用し、once の消費だけを共有する。
converted に素の整数で書かれて parse できなかった3枚（キユリ2種・ザパンプ）の
受け皿として追加した。
"""
from conftest import answer, setup


def drive_turn(e, plays):
    """メインで plays 本の play を選び切り、攻撃ステップに着くまで進める。
    途中で reduce の確認が一度も出ないことも確かめる。"""
    done = 0
    for _ in range(40):
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        assert "reduce" not in keys, "must の軽減で確認が出てはいけない"
        if d["kind"] == "attack":
            return done
        if d["kind"] == "main" and done < plays and any(k.startswith("play:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:"))])
            done += 1
        elif d["kind"] == "pay_mana":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("攻撃ステップにたどり着かなかった")


def test_cost_may_must_applies_once_without_asking(rules):
    e = setup(rules, {"bz": ["T136"], "hand": ["T001", "T001"],
                      "mana": ["T001", "T001", "T001"]}, {})
    answer(e, "charge", "pass")
    done = drive_turn(e, 2)
    assert done == 2
    assert len([c for c in e.bz_tops(0) if e.s.cards[c].defn == "T001"]) == 2
    # 1体目は強制軽減で1マナ、2体目は once 消費済みで通常コスト2マナ = 合計3マナ
    tapped = len([c for c in e.s.zones["mana"][0] if e.s.cards[c].tapped])
    assert tapped == 3, tapped


def test_cost_may_must_floor(rules):
    # コスト1のクリーチャーは min: 1 により0にはならない（通常どおり1マナ払う）
    e = setup(rules, {"bz": ["T136"], "hand": ["T009"],
                      "mana": ["T009", "T009"]}, {})
    answer(e, "charge", "pass")
    done = drive_turn(e, 1)
    assert done == 1
    tapped = len([c for c in e.s.zones["mana"][0] if e.s.cards[c].tapped])
    assert tapped == 1, tapped
