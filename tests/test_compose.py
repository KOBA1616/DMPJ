"""合成手（dmsim/search/compose.py）と、復活したACEタマシードの攻撃の確認。"""

from dmsim.cards.defs import load_rules
from dmsim.eval import loop_entry as LE


def test_jabibiru_rush_applies_to_ace_tamaseed_revived_from_graveyard(monkeypatch):
    """墓地から出た ACE タマシード（クリーチャーでもある）にも、ジャビビルブラッドの出たターン攻撃が効く。
    保留（play_free）を経由しても、直前のゾーンは墓地として数える。"""
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)   # ジャシン帝などは変換データ側にある
    rules = load_rules(only_approved=False)
    e = LE.build(rules, LE.load("jashin_abyss"), 1)
    while True:
        d = e.advance()
        if d["kind"] == "attack":
            break
        ks = [o["key"] for o in d["options"]]
        e.answer([ks.index("pass") if "pass" in ks else 0])
    from dmsim.search import compose as C
    mv, _ = C.enumerate_moves(e, "attack:dm25sd1-001:player", max_nodes=1200)
    assert any(m.get("again") for m in mv)   # 復活したジャシン帝が、同じ攻撃をもう一度選べる局面がある


def test_find_loop_reports_finite_loop_for_jashin_board(monkeypatch):
    """ジャシン帝＋ジャビビルブラッド＋マグナムの盤面から、回帰（有限ループ）が1周以上見つかる。"""
    from dmsim.search import compose as C
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)
    rules = load_rules(only_approved=False)
    S = "dm25sd1-001"
    e = LE.build(rules, LE.load("jashin_abyss"), 1)
    while (d := e.advance())["kind"] != "attack":
        ks = [o["key"] for o in d["options"]]
        e.answer([ks.index("pass") if "pass" in ks else 0])
    r = C.find_loop(e, f"attack:{S}:player", laps_max=1, max_nodes=800, tries=2)
    assert r["kind"] in ("finite", "infinite") and r["laps"] >= 1


def test_minimal_board_shrinks_jashin_loop(monkeypatch):
    """ジャシン帝の盤面を縮約して、ループが成立する最小盤面を LoopSpec で得る。墓地は必要な部品＋任意 n 枚で表す。"""
    from dmsim.discovery import minboard as MB
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)
    rules = load_rules(only_approved=False)
    ls = LE.load("jashin_abyss")
    spec = MB.board_spec(ls, 1)
    mb = MB.minimal_board(rules, spec, "attack:dm25sd1-001:player", name="jashin_min", max_nodes=800)
    n0 = sum(len(v) for v in spec["p0"].values())
    n1 = sum(len(v) for v in mb.spec["p0"].values())
    assert n1 < n0
    assert mb.loopspec.minimal and mb.tests > 0
    assert {p.match.get("name") for p in mb.loopspec.minimal if p.zone == "bz"} >= {"dm25sd1-001"}   # 起点の攻撃役は場に残る


def _board(monkeypatch, bz, gy, ident):
    """盤面を指定して、自分の攻撃選択まで進めたエンジンを返す。"""
    from dmsim.discovery.submit import build_entry, REPO
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)
    rules = load_rules(only_approved=False)
    ids = list(dict.fromkeys(bz + gy))
    ep, dp = build_entry(rules, id=ident, name=ident, core=[{"id": i} for i in ids], bz=bz, graveyard=gy)
    try:
        ls = LE.load(f"auto/{ident}")
        e = LE.build(rules, ls, 1)
    finally:   # テスト用の入口とデッキは残さない
        (REPO / ep).unlink(missing_ok=True)
        (REPO / dp).unlink(missing_ok=True)
    while (d := e.advance())["kind"] != "attack":
        ks = [o["key"] for o in d["options"]]
        e.answer([ks.index("pass") if "pass" in ks else 0])
    return e


S, M, JB, G, OA, BG = "dm25sd1-001", "dm20-013", "dm26ex1-018", "dm26ex2-pr004", "dm25rp4-066", "dm01-090"


def test_attack_cancel_by_destroying_attacker_breaks_no_shield(monkeypatch):
    """攻撃中のクリーチャーが破壊されると攻撃は中止になり、シールドはブレイクされない（攻撃時効果だけが出る）。"""
    from dmsim.search import compose as C
    e = _board(monkeypatch, [S, M, JB, BG], [G, OA], "t_cancel")
    shields = len(e.zlist("shield", 1))
    mv, _ = C.enumerate_moves(e, f"attack:{S}:player", max_nodes=500)
    destroyed = [m for m in mv if len(m["eng"].zlist("graveyard", 0)) > len(e.zlist("graveyard", 0))]
    assert destroyed
    assert all(len(m["eng"].zlist("shield", 1)) == shields for m in mv)


def test_ore_nateha_discards_each_lap_and_opponent_redraws(monkeypatch):
    """オア:ナテハの出た時で相手が1枚捨て、破壊時に相手が1枚引く。周回で相手の手札は変わらず、墓地が1枚増える。"""
    from dmsim.search import compose as C
    e = _board(monkeypatch, [S, M, JB, BG], [G, OA], "t_ore")
    hand0, gy0 = len(e.zlist("hand", 1)), len(e.zlist("graveyard", 1))
    mv, _ = C.enumerate_moves(e, f"attack:{S}:player", max_nodes=1200)
    good = [m for m in mv if m.get("again") and C.superset(m["core"], C.core(e))]
    assert good
    assert any(len(m["eng"].zlist("hand", 1)) == hand0 and len(m["eng"].zlist("graveyard", 1)) == gy0 + 1 for m in good)
