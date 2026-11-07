"""版つき経験ログ（JSONL）。エンジン版を凍結し、版が違うログは再生を拒否する。

1行目 = ヘッダ(engine_version, vocab_version, experiment_id)。以降 1ステップ/行。Parquet へ無損失変換できるよう平坦なキーに保つ。"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

STEP_KEYS = ("state", "legal", "chosen", "policy_id", "opp_id", "seed", "turn", "result")


def engine_version(repo: str | Path = ".") -> str:
    """git のタグ（無ければ短縮ハッシュ）。取れなければ 'unknown'。"""
    try:
        return subprocess.check_output(["git", "-C", str(repo), "describe", "--tags", "--always", "--dirty"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def experiment_id(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


class VersionMismatch(Exception):
    pass


class LogWriter:
    def __init__(self, path, config: dict, engine_ver: str | None = None, vocab_ver: str = "unknown"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.header = {"kind": "header", "engine_version": engine_ver or engine_version(),
                       "vocab_version": vocab_ver, "experiment_id": experiment_id(config), "config": config}
        self._f = self.path.open("w", encoding="utf-8")
        self._f.write(json.dumps(self.header, ensure_ascii=False) + "\n")

    def step(self, **kw) -> None:
        missing = [k for k in STEP_KEYS if k not in kw]
        if missing:
            raise ValueError(f"ステップに必須キーが無い: {missing}")
        self._f.write(json.dumps({"kind": "step", **kw}, ensure_ascii=False) + "\n")

    def close(self) -> None:
        self._f.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def read_log(path, require_engine_version: str | None = None):
    """(header, steps) を返す。require_engine_version を渡して不一致なら VersionMismatch。"""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    header = json.loads(lines[0])
    if header.get("kind") != "header":
        raise ValueError("ヘッダが無い")
    if require_engine_version is not None and header["engine_version"] != require_engine_version:
        raise VersionMismatch(f"ログの版 {header['engine_version']} != 現在 {require_engine_version}。新しい版で作り直す")
    return header, [json.loads(x) for x in lines[1:] if x]


def summarize_log(path) -> dict:
    """リポジトリに置く要約（本体はローカル保存）。"""
    h, steps = read_log(path)
    return {"experiment_id": h["experiment_id"], "engine_version": h["engine_version"],
            "vocab_version": h["vocab_version"], "steps": len(steps),
            "seeds": sorted({s["seed"] for s in steps}),
            "replay": "同じ engine_version を checkout し config の seed と決定列から再生成"}
