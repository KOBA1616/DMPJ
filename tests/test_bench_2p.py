"""bench_2p の煙テスト: サガミラー2局が最後まで回り、指標が返ること。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.bench_2p import load_deck, run_bench  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402


def test_bench_2p_saga_mirror_smoke(monkeypatch):
    # サガデッキには converted.yaml のみの札が含まれるため、conftest の
    # DMSIM_SKIP_CONVERTED=1 をこのテストだけ外して全カードで読み込む。
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)
    rules = load_rules()
    deck = load_deck("data/decks/saga.yaml")
    assert len(deck) == 40
    r = run_bench(rules, deck, deck, games=2, seed=7, engine="python")
    assert r["games_done"] == 2
    assert r["decisions"] > 0
    assert r["games_per_sec"] > 0
    assert r["wins"][0] + r["wins"][1] == 2
