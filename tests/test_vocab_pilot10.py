"""語彙パイロット第10弾（2026-10-31）の検証。

スペース・チャージ（rejects: space_charge）は新規実装なしで表せる:
自分のマナゾーンに置かれたカード（＝イベントの subject）の文明ごとに、
optional な誘発を分けて書く。チャージでも効果でマナに置いた時でも発火する。
"""
from conftest import answer, setup


def test_space_charge_light_shieldify(rules):
    e = setup(rules, {"bz": ["T045"], "hand": ["T004", "T003"]}, {"hand": ["T001"]})
    sh0 = len(e.s.zones["shield"][0])
    answer(e, "charge", "charge:T004")          # 光のカードをチャージ
    # optional な誘発の確認（使う／使わない）が出て、使うとシールドが増える
    d = None
    for _ in range(10):
        d = e.advance()
        if d is None or len(e.s.zones["shield"][0]) == sh0 + 1:
            break
        keys = [o["key"] for o in d["options"]]
        if "yes" in keys:
            e.answer([keys.index("yes")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert len(e.s.zones["shield"][0]) == sh0 + 1


def test_space_charge_decline(rules):
    """「使ってもよい」なので、効果側の may で断れる（誘発自体は任意にできない）。"""
    e = setup(rules, {"bz": ["T045"], "hand": ["T004", "T003"]}, {"hand": ["T001"]})
    sh0 = len(e.s.zones["shield"][0])
    answer(e, "charge", "charge:T004")
    for _ in range(10):
        d = e.advance()
        if d is None or d["kind"] in ("main", "attack"):
            break
        keys = [o["key"] for o in d["options"]]
        if "no" in keys:
            e.answer([keys.index("no")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert len(e.s.zones["shield"][0]) == sh0


def test_space_charge_no_matching_civ_no_trigger(rules):
    e = setup(rules, {"bz": ["T045"], "hand": ["T003"]}, {"hand": ["T001"]})
    sh0 = len(e.s.zones["shield"][0])
    answer(e, "charge", "charge:T003")          # 水のカード: 対応する行が無いので誘発しない
    d = e.advance()
    assert d is not None and d["kind"] in ("main", "attack")   # 誘発の確認（yes/no）は挟まらない
    assert len(e.s.zones["shield"][0]) == sh0
