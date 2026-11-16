"""カード定義の読み書きを1か所に集める。パスが「ファイル」なら従来どおり1ファイル、「ディレクトリ」なら弾ごとの分割ファイル。

    read(path)                  -> カード辞書のリスト（ディレクトリなら全弾を ID 順に）
    write(path, cards, header)  -> 書き込む。ディレクトリは弾（IDの接頭辞）ごとに分け、内容が変わった弾だけ書き、空になった弾は消す

書き手（convert_cards / agent_convert）はこれだけを呼ぶ。保存形式を変えるときは、出力先のパスを変えるだけで済む。
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml

from .defs import DATA


def shard_of(card_id: str) -> str:
    return card_id.split("-")[0]


def _dump(cards: list[dict], header: str) -> str:
    return header + yaml.safe_dump({"cards": cards}, allow_unicode=True, sort_keys=False)


_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def _load(text: str):
    return yaml.load(text, Loader=_LOADER)


def read(path: Path) -> list[dict]:
    path = Path(path)
    if path.is_dir():
        cards = []
        for f in sorted(path.glob("*.yaml")):
            cards += (_load(f.read_text(encoding="utf-8")) or {}).get("cards") or []
        return sorted(cards, key=lambda c: c["id"])
    if path.exists():
        return (_load(path.read_text(encoding="utf-8")) or {}).get("cards") or []
    return []


def is_sharded(path: Path) -> bool:
    return Path(path).is_dir() or Path(path).suffix == ""


def write(path: Path, cards: list[dict], header: str = ""):
    path = Path(path)
    if not is_sharded(path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_dump(cards, header), encoding="utf-8")
        return
    path.mkdir(parents=True, exist_ok=True)
    groups = defaultdict(list)
    for c in cards:
        groups[shard_of(c["id"])].append(c)
    for k, cs in groups.items():
        f, text = path / f"{k}.yaml", _dump(sorted(cs, key=lambda c: c["id"]), header)
        if not f.exists() or f.read_text(encoding="utf-8") != text:
            f.write_text(text, encoding="utf-8")
    for f in path.glob("*.yaml"):
        if f.stem not in groups:
            f.unlink()


def converted_path(root: Path | None = None) -> Path:
    """変換結果の置き場。弾別ディレクトリ data/cards/converted/ があればそれ、無ければ従来の converted.yaml。
    移行は tools/migrate_converted.py（ディレクトリを作って元ファイルを消す）だけで切り替わる。"""
    cards = (root or DATA) / "cards"
    return cards / "converted" if (cards / "converted").is_dir() else cards / "converted.yaml"
