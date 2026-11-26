"""モデル提案（tools/combo_hunt3_propose.py）の部品テスト。

重い実物（load_rules・属性行列の構築）は使わず、近傍の除外規則と
既知エンジン照合だけをスタブで確認する。
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import combo_hunt3_propose as P  # noqa: E402


class _StubRules:
    def __init__(self, names):
        self.cards = {cid: SimpleNamespace(name=n) for cid, n in names.items()}


def _unit(rows):
    m = np.array(rows, dtype=np.float32)
    n = np.linalg.norm(m, axis=1)
    n[n == 0] = 1.0
    return m / n[:, None]


def test_neighbors_excludes_known_core_and_same_name():
    # ids: seed, known-core (dm16-007 ヘブンズ・ゲート), seed の同名再録, 通常候補
    ids = ["seed", "dm16-007", "reprint", "cand"]
    rules = _StubRules({"seed": "種カード", "dm16-007": "ヘブンズ・ゲート",
                         "reprint": "種カード", "cand": "候補カード"})
    vocab = SimpleNamespace(ids=ids, index={d: i + 1 for i, d in enumerate(ids)})
    unit = _unit([[0, 0], [1, 0], [1, 0.01], [1, 0.02], [1, 0.05]])  # 先頭は PAD 行
    out = P.neighbors(rules, vocab, unit, "seed", 10, exclude_names={"ヘブンズ・ゲート"})
    assert [o["card"] for o in out] == ["cand"]


def test_exclude_ids_cover_known_core_18():
    # v3 発見ランの KNOWN_CORE 17種＋XENARCH＋ホーリーエンド正規 ID が除外集合に入る
    from tools.combo_hunt3_run import KNOWN_CORE
    assert set(KNOWN_CORE) <= P.EXCLUDE_IDS
    assert P.XENARCH in P.EXCLUDE_IDS
    assert P.HOLYEND_CANONICAL in P.EXCLUDE_IDS
    assert len(P.EXCLUDE_IDS) >= 19


def test_is_known_engine():
    assert P._is_known_engine({P.SAGA: 2}, {"deck:0": -1, "graveyard:0": 1})
    assert P._is_known_engine({P.SAGA: 2, P.XENARCH: 2}, {"deck:0": -1, "hand:0": 1})
    assert P._is_known_engine(dict(P.AKASHIC_CORE), {"deck:1": -1, "graveyard:1": 1})
    # 増分が違えば別エンジン（サガ＋XENARCH の手札型をサガ単独と混同しない）
    assert not P._is_known_engine({P.SAGA: 2}, {"deck:0": -1, "hand:0": 1})
    assert not P._is_known_engine({P.SAGA: 2, "dmr21-s03": 2},
                                  {"deck:0": -1, "graveyard:0": 1})
    assert not P._is_known_engine({P.SAGA: 2}, None)
