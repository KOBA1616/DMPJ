"""語彙パイロット第39弾（フェーズ16追補）: 合計コスト選択の枚数上限（total_cost_selection の「N体まで」併記）。

第38弾の合計制限モード（1枚ずつ積み上げ）は count を見ておらず、「コストの合計がN以下になるように
クリーチャーを2体まで選ぶ」型（邪入梵など再変換ラウンド14の複数枚）が厳密に表せなかった。
select に count がある場合だけ、その枚数で積み上げを打ち切るようにした（count 無しの「好きな数」は従来どおり無制限）。
"""
from conftest import setup


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


def test_total_cost_selection_respects_count_cap(rules):
    """合計10以下・2体まで: 候補は2+3+3で全て予算内でも、2体選んだ時点で選択が終わり3体目は残る。"""
    e = setup(rules, {"hand": ["T115"], "mana": ["T005"] * 7},
              {"bz": ["T001", "T005", "T109"]})
    targets = list(e.zlist("bz", 1))   # zlist は実リスト参照なのでコピーする（破壊で縮む）
    assert len(targets) == 3
    st = {"played": False, "asks": 0}

    def drive(e, d, keys):
        if d["kind"] == "main" and d["player"] == 0 and not st["played"]:
            if "play:T115" in keys:
                st["played"] = True
                e.answer([keys.index("play:T115")])
                return True
        if d["kind"] == "pay_mana" and d["player"] == 0:
            e.answer([0])
            return True
        if d["kind"] == "choose_cards" and d["player"] == 0:
            st["asks"] += 1
            e.answer([0])   # 常に先頭の候補を選ぶ（上限が無ければ3体目まで選んでしまう）
            return True
        return False

    assert _settle(e, lambda: sum(1 for c in targets if e.s.cards[c].zone == "graveyard") == 2, drive)
    destroyed = [c for c in targets if e.s.cards[c].zone == "graveyard"]
    remaining = [c for c in targets if e.s.cards[c].zone == "bz"]
    assert len(destroyed) == 2 and len(remaining) == 1, (
        f"2体までで止まらず: destroyed={len(destroyed)} remaining={len(remaining)} asks={st['asks']}")
    assert st["asks"] == 2   # 3回目の選択肢提示自体が無いこと
