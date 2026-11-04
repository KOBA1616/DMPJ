"""語彙パイロット第55弾: filter の fushigi 所持判定。

第54弾の vividraw フィルタと同じ型で、カード定義（本体かいずれかの面）が
フシギバースを持つかを filter {fushigi: true/false} で判定できるようにした。
「墓地に置いた中から、フシギバースを持つクリーチャー1体につき〜」の数え上げや
対象指定に使う。
"""
from conftest import setup


def _settle(e, done, drive=None, max_steps=300):
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


def test_fushigi_filter(rules):
    """T152: filter {fushigi: true} はフシギバース所持者（T095）だけを選ぶ。"""
    e = setup(rules, {"bz": ["T095", "T001"], "hand": ["T152"], "mana": ["T001", "T001"]}, {})
    state = {}

    def drive(e, d, keys):
        if d["kind"] == "charge" and not state.get("tapped"):
            for c in e.zlist("bz", 0):
                e.s.cards[c].tapped = True
            state["tapped"] = True
            e.answer([keys.index("pass")])
            return True
        if d["kind"] == "main" and "play:T152" in keys:
            e.answer([keys.index("play:T152")])
            return True
        return False

    def done():
        t095 = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T095")
        t001 = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T001")
        return not e.s.cards[t095].tapped and e.s.cards[t001].tapped

    assert _settle(e, done, drive)
