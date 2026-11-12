"""結果・ログ・台帳の書き込み口（S0、ロードマップ P1）。評価・発見・改善の書き込みはここを通す。

最小の3点だけを持つ:
1. 保存先の根を1か所で決める: root()。環境変数 DMPJ_STORE_ROOT が無ければ <リポジトリ>/logs。
   既存の呼び出し元は今まで通り明示のパスを渡す（相対パスは従来どおり作業ディレクトリ基準）。
   新しいコードは path_in("explog", ...) のように根からの場所で指定する。
2. 途中で壊れない書き込み: write_text は同じディレクトリの一時ファイルへ書いてから os.replace で差し替える。
   append_line は1行を1回の write で追記する（途中で止まっても前の行は壊れない）。
3. tuning / holdout の区別: 記録に split を持たせられる（append_json に split を渡すと "split" 欄が付く）。
   purpose="tuning"（調整用の経路）へ split="holdout" のデータを書こうとすると HoldoutWriteError。

他の層を import しない。
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Literal

Split = Literal["tuning", "holdout"]
Purpose = Literal["tuning", "eval", "log"]
SPLITS = ("tuning", "holdout")
PURPOSES = ("tuning", "eval", "log")

REPO = Path(__file__).resolve().parents[2]


class HoldoutWriteError(ValueError):
    """検証専用(holdout)のデータを調整用の経路へ書こうとした。"""


def root() -> Path:
    """保存先の根。DMPJ_STORE_ROOT があればそれ、無ければ <リポジトリ>/logs。"""
    env = os.environ.get("DMPJ_STORE_ROOT")
    return Path(env) if env else REPO / "logs"


def path_in(*parts: str) -> Path:
    """根からの場所。"""
    return root().joinpath(*parts)


def check(purpose: Purpose | None, split: Split | None) -> None:
    if split is not None and split not in SPLITS:
        raise ValueError(f"split は {SPLITS} のどれか: {split!r}")
    if purpose is not None and purpose not in PURPOSES:
        raise ValueError(f"purpose は {PURPOSES} のどれか: {purpose!r}")
    if purpose == "tuning" and split == "holdout":
        raise HoldoutWriteError("検証専用(holdout)のデータは調整用の経路へ書けない")


def write_text(path, text: str, *, purpose: Purpose | None = None, split: Split | None = None,
               encoding: str = "utf-8") -> Path:
    """ファイル全体を書き換える（一時ファイル → os.replace で差し替え。途中で止まっても元のファイルは残る）。"""
    check(purpose, split)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{p.name}.", suffix=".tmp", dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
    return p


def append_line(path, line: str, *, purpose: Purpose | None = None, split: Split | None = None,
                encoding: str = "utf-8") -> Path:
    """1行を追記する（改行は付け足す。1回の write で書く）。"""
    check(purpose, split)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding=encoding) as f:
        f.write(line.rstrip("\n") + "\n")
    return p


def append_json(path, record: dict, *, purpose: Purpose | None = None, split: Split | None = None) -> Path:
    """JSON 1行の記録を追記する。split を渡すと記録に "split" 欄を付ける（記録自身の split と食い違えば拒否）。"""
    own = record.get("split")
    if split is not None and own is not None and own != split:
        raise ValueError(f"記録の split={own!r} と指定 split={split!r} が食い違う")
    split = split if split is not None else own
    rec = record if split is None or own is not None else {**record, "split": split}
    return append_line(path, json.dumps(rec, ensure_ascii=False), purpose=purpose, split=split)
