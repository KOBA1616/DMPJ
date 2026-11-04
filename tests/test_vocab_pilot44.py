"""語彙パイロット第44弾（フェーズ17-5）: キズナと[P]能力（kizuna 単独18件）。

実装したもの:
- 能力種別 partner（[P]能力）: 単独では機能せず、効果だけを持つ
- キーワード kizuna: 出た時に op: use_partner を解決する誘発型能力に展開される
- op: use_partner: 自分のクリーチャーの[P]を1つ選んで使い、効果の self は[P]の持ち主に移る
  （候補が1つだけなら判断は自動で確定する）
"""
from conftest import answer, setup


def _play_and_finish_cip(e, play_key):
    """play_key を出し、出た時の処理が終わる（攻撃ステップに入る）まで進める。
    use_partner の判断が出たら、その内容（オプションキー列）を返す。"""
    answer(e, "charge", "pass")
    d = e.advance()
    keys = [o["key"] for o in d["options"]]
    e.answer([keys.index(play_key)])
    seen_keys = None
    for _ in range(40):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "use_partner":
            seen_keys = keys
            e.answer([0])
            continue
        if d["kind"] == "order_pending":
            e.answer([0])
            continue
        if d["kind"] == "attack" or (d["kind"] == "charge" and d["player"] == 1):
            break   # 出た時の処理は終わった（攻撃ステップか、相手のターンに入った）
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return seen_keys


def test_kizuna_uses_partner_of_other_creature(rules):
    """キズナ持ちを出すと、場の別クリーチャーの[P]（1ドロー）が使われる。"""
    e = setup(rules, {"bz": ["T124"], "hand": ["T123"], "mana": ["T001"] * 3}, {})
    _play_and_finish_cip(e, "play:T123")
    assert len(e.zlist("hand", 0)) == 1   # T124 の[P]で1枚引いた（出す前は0枚）


def test_kizuna_can_use_its_own_partner(rules):
    """キズナと[P]を併せ持つクリーチャーは、自分の[P]も使える。"""
    e = setup(rules, {"hand": ["T125"], "mana": ["T005"] * 5}, {})
    _play_and_finish_cip(e, "play:T125")
    assert len(e.zlist("hand", 0)) == 2   # 自分の[P]で2枚引いた


def test_kizuna_choose_among_multiple_partners(rules):
    """[P]の候補が複数あれば選ぶ判断が出て、選んだ方の効果が解決する。"""
    e = setup(rules, {"bz": ["T124", "T125"], "hand": ["T123"], "mana": ["T001"] * 3}, {})
    answer(e, "charge", "pass")
    d = e.advance()
    keys = [o["key"] for o in d["options"]]
    e.answer([keys.index("play:T123")])
    chosen = False
    for _ in range(40):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "use_partner":
            assert len(keys) == 2
            hit = [i for i, k in enumerate(keys) if k.startswith("partner:T125:")]
            e.answer(hit)   # T125 の[P]（2ドロー）を選ぶ
            chosen = True
            continue
        if d["kind"] == "order_pending":
            e.answer([0])
            continue
        if d["kind"] == "attack" or (d["kind"] == "charge" and d["player"] == 1):
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert chosen is True
    assert len(e.zlist("hand", 0)) == 2


def test_kizuna_without_any_partner_does_nothing(rules):
    """[P]を持つクリーチャーがいなければ何も起こらない。"""
    e = setup(rules, {"hand": ["T123"], "mana": ["T001"] * 3}, {})
    _play_and_finish_cip(e, "play:T123")
    assert len(e.zlist("hand", 0)) == 0
