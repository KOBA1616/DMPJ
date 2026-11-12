"""base.store: 書き込み口（保存先の根・途中で壊れない書き込み・holdout の調整経路への書き込み拒否）。"""
import json

import pytest

from dmsim.base import store
from dmsim.deckplan.evaluate import record


def test_root_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DMPJ_STORE_ROOT", str(tmp_path))
    assert store.path_in("explog", "a.jsonl") == tmp_path / "explog" / "a.jsonl"
    monkeypatch.delenv("DMPJ_STORE_ROOT")
    assert store.root() == store.REPO / "logs"


def test_write_text_atomic_keeps_old_on_failure(tmp_path, monkeypatch):
    p = store.write_text(tmp_path / "d" / "x.yaml", "old\n")
    assert p.read_text() == "old\n"

    def boom(*a, **k):
        raise OSError("disk")
    monkeypatch.setattr(store.os, "replace", boom)
    with pytest.raises(OSError):
        store.write_text(p, "new\n")
    assert p.read_text() == "old\n"
    assert [q.name for q in p.parent.iterdir()] == ["x.yaml"]   # 一時ファイルは残らない


def test_append_json_split(tmp_path):
    p = tmp_path / "l.jsonl"
    store.append_json(p, {"a": 1})
    store.append_json(p, {"a": 2}, split="tuning")
    rows = [json.loads(x) for x in p.read_text().splitlines()]
    assert rows == [{"a": 1}, {"a": 2, "split": "tuning"}]
    with pytest.raises(ValueError):
        store.append_json(p, {"split": "tuning"}, split="holdout")


def test_holdout_cannot_go_to_tuning(tmp_path):
    with pytest.raises(store.HoldoutWriteError):
        store.append_json(tmp_path / "t.jsonl", {"x": 1}, purpose="tuning", split="holdout")
    with pytest.raises(store.HoldoutWriteError):
        record(tmp_path / "ledger.jsonl", {"combo": "drill", "split": "holdout"})
    assert not (tmp_path / "ledger.jsonl").exists()
    store.append_json(tmp_path / "e.jsonl", {"x": 1}, purpose="eval", split="holdout")   # 評価用なら可


def test_ledger_record_format_unchanged(tmp_path):
    p = tmp_path / "ledger.jsonl"
    record(p, {"verdict": "accept", "名": "札"})
    r = json.loads(p.read_text())
    assert set(r) == {"t", "verdict", "名"} and "札" in p.read_text()
