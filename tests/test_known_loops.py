"""既知ループの再発見率の指標（dmsim/eval/known_loops.py）。"""
from dmsim.cards.defs import load_rules
from dmsim.eval import known_loops as K


def test_known_loops_measure(monkeypatch):
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)
    m = K.measure(load_rules(only_approved=False), names=("akashic", "jashin_abyss"), max_nodes=800, laps_max=1, tries=2)
    by = {r["name"]: r for r in m["rows"]}
    assert by["akashic"]["found"] and by["akashic"]["origin"].startswith("play:")   # 攻撃の無い盤面はメインの呪文を起点にする
    assert by["jashin_abyss"]["found"]
    assert (m["found"], m["total"]) == (2, 2)


def test_saga_found_as_inner_loop(monkeypatch):
    """サガは出た時の効果が1手の中で墓地⇔場を回る（周回に分かれない）ので、手の中の繰り返しで見つける。"""
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)
    m = K.measure(load_rules(only_approved=False), names=("saga",), max_nodes=1500, laps_max=3, tries=3)
    r = m["rows"][0]
    assert r["found"] and r["origin"].startswith("play:") and r["laps"] >= 3


def test_repeat_count():
    from dmsim.search import compose as C
    blk = [("choose_cards", ["hand:a:0"]), ("yes_no", ["yes"]), ("choose_cards", ["graveyard:b:0"])]
    assert C.repeat_count(blk * 3 + [("main", ["pass"])])[0] == 3
    assert C.repeat_count(blk)[0] == 1


def test_saga_inner_certificate_replays(monkeypatch):
    """inner ループの証明書（1手の選択列）を check_certificate で再生でき、壊した列は通らない。"""
    from dmsim.eval import loop_entry as LE
    from dmsim.search import compose as C
    from dmsim.search.origins import auto_origins
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)
    rules = load_rules(only_approved=False)
    eng = LE.build(rules, LE.load("saga"), 1)
    e0, o = auto_origins(eng)[0]
    r = C.find_loop(e0, o, max_nodes=1500, laps_max=3, tries=3)
    assert r.get("inner")
    ok = C.check_certificate(e0, o, r["moves"], inner=True)
    assert ok["ok"] and ok["laps"] >= 3
    bad = C.check_certificate(e0, o, [r["moves"][0][:4]], inner=True)
    assert not bad["ok"]
