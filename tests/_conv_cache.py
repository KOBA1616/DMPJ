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


def _entry(path):
    key = str(path)
    sig = _sig(path)
    ent = _cache.get(key)
    if ent is None or ent[0] != sig:
        cards = cardstore.read(path) if sig else []
        ent = _cache[key] = (sig, {c["id"]: c for c in cards}, cards)
    return ent


def find(path, cid):
    """path の変換データから id が cid の札（深いコピー）。無ければ None。"""
    c = _entry(path)[1].get(cid)
    return copy.deepcopy(c) if c is not None else None


def all_cards(path):
    """path の変換データ全件（深いコピーのリスト）。パースは1プロセス1回。"""
    return copy.deepcopy(_entry(path)[2])


PROTO = Path(__file__).parent.parent / "data" / "cards" / "proto.yaml"


def proto_card(cid):
    """proto.yaml から id が cid の札（深いコピー）。読み込みは1プロセス1回。

    各 pilot テストが自前の _proto_card で proto.yaml を毎回 safe_load し直す
    のを避けるための共有入口。"""
    return find(str(PROTO), cid)


def full_rules():
    """converted.yaml 込みの Rules。conftest と他モジュールの setdefault が収集後に
    DMSIM_SKIP_CONVERTED=1 を戻すため、import 時の pop だけでは全体実行で効かない。読む間だけ外して戻す。"""
    import os
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        return load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old
