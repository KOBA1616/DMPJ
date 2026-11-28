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
