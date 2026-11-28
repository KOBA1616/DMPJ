"""候補→最小盤面→証明書→submit→登録 の共通の入口。部品Aを例に、札の決め打ち無しで流れることを見る。"""
from dmsim.cards.defs import load_rules
from dmsim.discovery import pipeline as P

CORE = [{"id": i} for i in ("dm25sd1-001", "dm20-013", "dm26ex1-018", "dm25sd1-003", "dm26ex2-pr004", "dm25rp4-066")]
CAND = dict(id="t_pipe", name="部品A", core=CORE, bz=["dm25sd1-001", "dm20-013", "dm26ex1-018", "dm25sd1-003"],
            graveyard=["dm26ex2-pr004", "dm25rp4-066"])


def test_pipeline_auto_origin(tmp_path, monkeypatch):
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("dmsim.cards.decks.REPO", tmp_path)   # 相対パスのデッキは tmp_path 側から読む
    rules = load_rules(only_approved=False)
    rep = P.run_candidate(rules, CAND, root=tmp_path, path=tmp_path / "reg", seeds=range(1, 3),
                          find=dict(laps_max=2, max_nodes=800, tries=2))
    print({k: v for k, v in rep.items() if k not in ("evidence", "row")})
    assert rep["stage"] == "registered" and rep["origin"]
    assert rep["minimal"] is not None
