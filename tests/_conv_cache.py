"""テスト用: 変換データ（converted）の読み込みを1プロセス1回にする（ファイルの更新時刻・大きさが変われば読み直す）。
返すのは毎回その札の深いコピーなので、テストが書き換えても他のテストに漏れない。"""
import copy
from pathlib import Path

from dmsim.cards import cardstore

_cache: dict = {}


def _sig(path: Path):
    path = Path(path)
    files = sorted(path.glob("*.yaml")) if path.is_dir() else [path]
    return tuple((str(f), f.stat().st_mtime_ns, f.stat().st_size) for f in files if f.exists())


def find(path, cid):
    """path の変換データから id が cid の札（深いコピー）。無ければ None。"""
    key = str(path)
    sig = _sig(path)
    ent = _cache.get(key)
    if ent is None or ent[0] != sig:
        ent = _cache[key] = (sig, {c["id"]: c for c in cardstore.read(path)} if sig else {})
    c = ent[1].get(cid)
    return copy.deepcopy(c) if c is not None else None
