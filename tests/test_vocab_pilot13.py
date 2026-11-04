"""語彙パイロット第13弾（2026-10-31）の検証。

1. summon_time_alternative_cost の「タップして軽減」: opt_reduce の do に tap を追加した。
   「減らす」を選ぶと燃料のクリーチャーをタップしてから、減額したコストを支払う。
2. revolution_condition（革命N）は新規語彙不要: 条件は「自分のシールドがNつ以下」という
   cmp で、常在型の if に置けばパワー修整とブレイカー付与が切り替わる。
3. race_addition（種族追加）: mod add_races を chars の種族計算に足した。
"""
from conftest import setup


def test_opt_reduce_tap_fuel(rules):
    e = setup(rules, {"hand": ["T048"], "bz": ["T001"], "mana": ["T001"] * 3}, {})
    fuel = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T001")
    # 燃料候補が1体だけ・支払い組み合わせが1通りなので、燃料選択と支払いは自動で決まる。
    # 場に出た時点で止める（進め続けると次のターンのアンタップで印が消える）
    for _ in range(10):
        if any(e.s.cards[c].defn == "T048" for c in e.bz_tops(0)):
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main":
            e.answer([keys.index("play:T048")])
        elif d["kind"] == "choose_cards" and "reduce" in keys:
            e.answer([keys.index("reduce")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert any(e.s.cards[c].defn == "T048" for c in e.bz_tops(0))     # 召喚できた（3マナで足りた）
    assert e.s.cards[fuel].tapped is True                             # 燃料はタップされた
    paid = [c for c in e.zlist("mana", 0) if e.s.cards[c].tapped]
    assert len(paid) == 3                                             # 5-2=3 だけ支払った


def test_revolution_condition_switches(rules):
    own = {"bz": ["T049"], "shield": ["T001", "T001", "T001"]}
    e = setup(rules, own, {})
    cid = e.bz_tops(0)[0]
    assert e.chars(cid)["power"] == 3000 and e.chars(cid)["breaks"] == 1   # シールド3つ: 革命オフ
    own2 = {"bz": ["T049"], "shield": ["T001", "T001"]}
    e2 = setup(rules, own2, {})
    cid2 = e2.bz_tops(0)[0]
    assert e2.chars(cid2)["power"] == 12000 and e2.chars(cid2)["breaks"] == 4   # シールド2つ: 革命オン


def test_add_races(rules):
    e = setup(rules, {"bz": ["T050", "T008"]}, {})
    dark = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T008")
    assert "サバイバー" in e.chars(dark)["races"]         # 闇のクリーチャーに種族が追加される
    src = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T050")
    assert "サバイバー" in e.chars(src)["races"]          # 発生源自身（闇）も対象
