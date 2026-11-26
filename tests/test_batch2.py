"""Phase 25: dmcore.run_batch2（局面開始・座席別方策・観測ダイジェスト）の検証。

- 局面開始: シナリオ局面から始めたバッチ結果が、Python 駆動で同じ局面・
  同じ方策で回した結果と勝敗・ターン・決定数が一致する。
- 座席別方策: first / random / model を座席ごとに混ぜて完走し、モデル座席の
  決定だけが軌跡に記録される。
- 観測ダイジェスト: obs から tools/loop_stages.py の入口条件の充足数が
  ステップごとに再現できる（到達判定がダイジェストだけで行える）。
- torch glue: TorchModel と同じ .p 互換インターフェースを持つオブジェクトが
  rust 収集（collect_games_rust）にそのまま渡せる。

現行の saga.yaml は Rust 未対応の札（dm23bd7-030）を含むため、新規対戦の
テストには saga_legacy.yaml を使う（test_batch.py 側の既存失敗と同じ事情）。
"""
import pytest

dmcore = pytest.importorskip("dmcore")

from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import collect_games_rust  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import rustcore, scenario  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.loop_stages import MINIMAL, condition_counts  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _full_cards():
    import os
    saved = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    yield
    if saved is not None:
        os.environ["DMSIM_SKIP_CONVERTED"] = saved


@pytest.fixture(scope="module")
def rules():
    return load_rules()


@pytest.fixture(scope="module")
def deck():
    return load_deck("data/decks/saga_legacy.yaml")


@pytest.fixture(scope="module")
def vocab(rules):
    return Vocab(rules)


SPEC = {"p0": {"hand": ["dm22ex2-021"], "mana": ["dmrp03-036"] * 3,
               "graveyard": ["dmrp03-036"] * 2},
        "p1": {}, "filler": "dmrp03-036", "seed": 7}


def _drive_first(eng, limit=5000):
    """Python エンジンを '最小数を先頭から' 方策で駆動し (結果, 決定数) を返す。"""
    decisions = 0
    while decisions < limit:
        d = eng.advance()
        if d is None:
            break
        eng.answer(list(range(d["min"])))
        decisions += 1
    return eng.s.result, decisions


def test_scenario_start_parity_first(rules):
    sj = rustcore.state_from_scenario(rules, SPEC)
    got = rustcore.run_batch2(rules, [sj], [["first", "first"]], seed=1)[0]
    assert "error" not in got, got
    res, decisions = _drive_first(scenario.build(rules, SPEC))
    assert res is not None
    assert got["winner"] == res["winner"]
    assert got["turn"] == res["turn"]
    assert got["decisions"] == decisions


def test_batch2_accepts_engine_and_state_objects(rules):
    eng = scenario.build(rules, SPEC)
    by_engine = rustcore.run_batch2(rules, [eng], [["first", "first"]], seed=1)[0]
    by_state = rustcore.run_batch2(rules, [eng.s], [["first", "first"]], seed=1)[0]
    assert "error" not in by_engine, by_engine
    assert by_engine == by_state


def test_batch2_first_matches_run_batch(rules, deck):
    states = [rustcore.new_game(rules, [deck, deck], 700 + g, g % 2)
              for g in range(2)]
    got = rustcore.run_batch2(rules, states, [["first", "first"]] * 2, seed=1)
    exp = rustcore.run_batch(rules, states, policy="first", seed=1)
    for g, e in zip(got, exp):
        assert {k: g[k] for k in ("winner", "turn", "decisions")} == e
        assert g["traj"] == []


def test_batch2_seat_policies(rules, deck, vocab):
    m1 = Model(len(vocab), seed=1)
    m2 = Model(len(vocab), seed=2)
    states = [rustcore.new_game(rules, [deck, deck], 800 + g, g % 2)
              for g in range(4)]
    seats = [[m1, "first"], ["first", m2], [m1, m2], ["random", "random"]]
    got = rustcore.run_batch2(rules, states, seats, vocab.ids, seed=3)
    for r in got:
        assert "error" not in r, r
        assert r["winner"] in (0, 1)
    # モデル同士の局では全決定が軌跡に残る
    assert len(got[2]["traj"]) == got[2]["decisions"]
    # 片側だけモデルの局では、その座席の決定だけが軌跡に残る
    assert got[0]["traj"] and all(t["player"] == 0 for t in got[0]["traj"])
    assert got[1]["traj"] and all(t["player"] == 1 for t in got[1]["traj"])
    assert len(got[0]["traj"]) < got[0]["decisions"]


def test_observe_digest_reproduces_entry_conditions(rules, vocab):
    sj = rustcore.state_from_scenario(rules, SPEC)
    got = rustcore.run_batch2(rules, [sj], [["first", "first"]], vocab.ids,
                              seed=1, observe=True)[0]
    assert "error" not in got, got
    obs = got["obs"]
    assert len(obs) == got["decisions"]
    assert all(len(step) == 2 and len(step[0]) == len(rules.zones)
               for step in obs)
    eng = scenario.build(rules, SPEC)
    for i in range(got["decisions"]):
        d = eng.advance()
        assert d is not None
        eng.answer(list(range(d["min"])))
        for p in (0, 1):
            from_digest = rustcore.condition_counts_from_digest(
                obs[i], rules, vocab.ids, p, MINIMAL)
            actual = condition_counts(eng, rules, p)
            assert from_digest == actual, f"step {i} player {p}"
            reached_d = all(c >= cond["n"] for c, cond
                            in zip(from_digest, MINIMAL))
            reached_a = all(c >= cond["n"] for c, cond
                            in zip(actual, MINIMAL))
            assert reached_d == reached_a


class _TorchLike:
    """TorchModel の .p 互換インターフェースだけを持つ代替オブジェクト。

    torch が無い環境でも、rust 収集への glue（重み dict の受け渡し）を
    検証するために使う。TorchModel.p も全く同じ形の dict を返す。
    """

    def __init__(self, model):
        self._model = model

    @property
    def p(self):
        return self._model.p


def test_torch_glue_ducktyped_model_collects(rules, deck, vocab):
    wrapped = _TorchLike(Model(len(vocab), seed=5))
    batch, winners = collect_games_rust(rules, vocab, wrapped, deck, deck,
                                        games=2, seed=11)
    assert len(winners) == 2
    assert all(w in (0, 1) for w in winners)
    assert batch and all(set(t) >= {"st", "op", "choice", "ret"} for t in batch)
    # run_batch2 の座席としても使える
    states = [rustcore.new_game(rules, [deck, deck], 810, 0)]
    got = rustcore.run_batch2(rules, states, [[wrapped, "first"]],
                              vocab.ids, seed=3)[0]
    assert "error" not in got, got
    assert got["traj"] and all(t["player"] == 0 for t in got["traj"])
