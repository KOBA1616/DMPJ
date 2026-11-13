import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DMSIM_CHECK"] = "1"   # タスク・選択肢の形を毎回検査する
os.environ["DMSIM_SKIP_CONVERTED"] = "1"   # 確認前の変換結果（converted.yaml、約1,600枚）はテストの対象にしない（全カードを回すテストが遅くなる）

from dmsim import load_rules  # noqa: E402
from dmsim.engine import scenario  # noqa: E402


@pytest.fixture(scope="session")
def rules():
    return load_rules()


def setup(rules, p0: dict, p1: dict | None = None, filler="T001", seed=1, deck_size=20, deck_left=None):
    """指定した配置から始まる局面を作る（dmsim.scenario.build の薄い包み）。"""
    return scenario.build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler, "seed": seed,
                                  "deck_size": deck_size, "deck_left": deck_left})


def find_option(d, key):
    keys = [o["key"] for o in d["options"]]
    assert key in keys, f"{key} not in {keys}"
    return keys.index(key)


def answer(e, kind, key):
    d = e.advance()
    assert d is not None and d["kind"] == kind, (d and d["kind"], kind, d and [o["key"] for o in d["options"]])
    e.answer([find_option(d, key)])
    return d


@pytest.fixture(autouse=True)
def _registry_macro_off(monkeypatch):
    """登録簿の手（search.macro）は既定有効だが、テストは探索そのものの挙動を見るので切っておく。
    手の効き目を見るテスト（test_search_macro.py）は ts.macros や macro.enable で明示的に入れる。"""
    from dmsim.search import macro
    monkeypatch.setenv("DMSIM_REGISTRY_MACRO", "0")
    was = macro._ENABLED
    macro._ENABLED = None
    yield
    macro._ENABLED = was
