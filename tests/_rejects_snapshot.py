"""再変換ラウンド前の rejects.jsonl を git 履歴から取り出す（テスト用）。

第166–173弾の生成テストは、定期の変換ラウンドで rejects から消えた行（partial）を
入力に使う。以前は作業者の PC にあるバックアップを読んでいたため他の環境で失敗した。
main に残るコミット acd8dec（PR #379 の親）の rejects を使う。
"""
import functools
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
SNAPSHOT_COMMIT = "acd8dec"


@functools.lru_cache(maxsize=None)
def snapshot_path(commit: str = SNAPSHOT_COMMIT) -> Path:
    data = subprocess.run(
        ["git", "show", f"{commit}:data/cards/raw/rejects.jsonl"],
        cwd=ROOT, check=True, capture_output=True).stdout
    f = tempfile.NamedTemporaryFile(prefix=f"rejects-{commit}-", suffix=".jsonl", delete=False)
    f.write(data)
    f.close()
    return Path(f.name)
