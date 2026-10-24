"""絶望神サガループの検証（水上第九院 シャコガイル の置換勝利を含む）。

3つのシナリオ:
1. シャコガイルなしでループを続ける → 山札1枚のドローで敗北（デッキアウト。無限ループにならない）
2. シャコガイルが場にいる → 山札1枚のドローが「勝つ」に置換される（エクストラウィン）
3. 実戦ルート: サガループ → 超神星DOOM・ドラゲリオン（超無限墓地進化＋メテオバーン）で
   シャコガイルを踏み倒し、イワシンの誘発（メテオバーンの解決後に解決）で最後の1枚を引き置換勝利
"""
import pytest

from dmsim import scenario as sc
from dmsim.defs import load_rules

SAGA = "dm22ex2-021"       # 絶望神サガ
SHAKO = "dmrp03-s03"       # 水上第九院 シャコガイル
DRAG = "dm22ex1-007"       # 超神星DOOM・ドラゲリオン
IWASHIN = "dmrp03-036"     # 一なる部隊 イワシン
DM_BLOCK = "テスト用ダミー"


def saga_policy(eng, d, stop_deck: int = 0):
    """サガループ試験用の簡易方策。

    stop_deck > 0 なら、メイン中のサガの蘇生 may を、自分の山札がその枚数以下に
    なったら「no」で打ち切る（それ以降はドラゲリオン・ルートへ）。
    """
    keys = [o["key"] for o in d["options"]]
    if d["kind"] == "yes_no":
        yn = keys.index("yes")
        if eng.s.step == "main" and stop_deck and len(eng.s.zones["deck"][0]) <= stop_deck:
            yn = keys.index("no")
        return [yn]
    if d["kind"] == "charge":
        j = next((j for j, o in enumerate(d["options"])
                  if o.get("cid") and eng.s.cards[o["cid"]].defn in ("dm01-027", "dm01-080")), None)
        return [j] if j is not None else [keys.index("pass")]
    if d["kind"] == "main":
        j = next((j for j, o in enumerate(d["options"]) if o["key"] != "pass"
                  and eng.s.cards[o["cid"]].defn in (SAGA, DRAG)), None)
        return [j] if j is not None else [keys.index("pass")]
    if d["kind"] == "attack":
        j = next((j for j, o in enumerate(d["options"]) if o["key"] != "pass"), None)
        return [j] if j is not None else [keys.index("pass")]
    if d["kind"] == "choose_evo_source":
        # 超無限墓地進化: シャコガイル以外を全部進化元にする（メテオバーンで出す対象として残す）
        return [j for j, o in enumerate(d["options"])
                if eng.s.cards[o["cid"]].defn != SHAKO]
    if d["kind"] == "choose_cards":
        z = eng.s.cards[d["options"][0]["cid"]].zone
        if z == "bz":            # メテオバーンの「下の1枚」: イワシンを墓地へ
            j = next((j for j, o in enumerate(d["options"])
                      if eng.s.cards[o["cid"]].defn == IWASHIN), None)
            return [j] if j is not None else [0]
        if z == "graveyard":     # 「その後、進化ではないクリーチャーを1体」: シャコガイルを出す
            j = next((j for j, o in enumerate(d["options"])
                      if eng.s.cards[o["cid"]].defn == SHAKO), None)
            return [j] if j is not None else [0]
        # 手札を捨てる系: ダミーを捨てる
        j = next((j for j, o in enumerate(d["options"])
                  if eng.s.cards[o["cid"]].defn != SAGA and eng.s.cards[o["cid"]].defn != DRAG), None)
        return [j] if j is not None else [0]
    if d["kind"] == "order_pending":
        j = next((j for j, o in enumerate(d["options"]) if IWASHIN in o["key"]), None)
        return [j] if j is not None else [0]
    if d["kind"] == "block":
        return [keys.index("no_block")]
    return list(range(d["min"]))


def run(eng, cap=600, stop_deck: int = 0):
    for _ in range(cap):
        d = eng.advance()
        if d is None:
            return eng.s.result
        eng.answer(saga_policy(eng, d, stop_deck))
    raise AssertionError(f"too many decisions: turn={eng.s.turn} step={eng.s.step}")


def test_saga_loop_deck_out_without_shakogairu(rules):
    """シャコガイルが場にいなければ、山札が尽きて敗北する（ループが無限にならない）。"""
    spec = {"p0": {"hand": [SAGA, "T001", "T001", "T001", "T001", "T001"],
                   "mana": ["dm01-080", "dm01-080", "dm01-027"],
                   "graveyard": [SAGA, "T001", "T001", "T001"]},
            "p1": {}, "deck_size": 20, "deck_left": [6, 20], "seed": 1}
    eng = sc.build(rules, spec, check=True)
    r = run(eng)
    assert r["winner"] == 1 and r["reason"] == "deck_out"


def test_saga_loop_replacement_win(rules):
    """シャコガイルが場にいるとき、山札1枚のドローが「勝つ」に置換される。"""
    spec = {"p0": {"bz": [SHAKO],
                   "hand": [SAGA, "T001", "T001", "T001", "T001", "T001"],
                   "mana": ["dm01-080", "dm01-080", "dm01-027"],
                   "graveyard": [SAGA, "T001", "T001", "T001"]},
            "p1": {}, "deck_size": 20, "deck_left": [6, 20], "seed": 1}
    eng = sc.build(rules, spec, check=True)
    r = run(eng)
    assert r["winner"] == 0 and r["reason"] == "effect"


def test_saga_kill_dragellion_route(rules):
    """実戦ルート: サガループ → ドラゲリオン（超無限墓地進化・メテオバーン）→ シャコガイル
    踏み倒し → イワシンの誘発（メテオバーン解決後に解決）で最後の1枚を引いて置換勝利。"""
    spec = {"p0": {"hand": [SAGA, DRAG, "T001", "T001", "T001", "T001"],
                   "mana": ["dm01-080", "dm01-080", "dm01-027"],
                   "graveyard": [SAGA, IWASHIN, SHAKO] + ["T001"] * 12},
            "p1": {}, "deck_size": 20, "deck_left": [2, 20], "seed": 1}
    eng = sc.build(rules, spec, check=True)
    r = run(eng, cap=1200, stop_deck=1)
    assert r["winner"] == 0 and r["reason"] == "effect"
    # 山札が1枚減った状態（最後の1枚のドローが置換されたまま）で終わっていること
    assert len(eng.s.zones["deck"][0]) == 1
