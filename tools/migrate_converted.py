"""converted.yaml を弾別ディレクトリ data/cards/converted/ に移す（書き手は converted_path() で自動的に切り替わる）。

    python tools/migrate_converted.py --check    # 何もせず、移行後に同じカード集合になるかだけ確かめる
    python tools/migrate_converted.py            # 分割して converted.yaml を消す（ワーカーを止めてから。docs/migrate-sharded.md）

移行前後でカードの ID と内容が一致することを確かめてから元ファイルを消す。一致しなければ何も消さない。
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim import cardstore  # noqa: E402
from dmsim.defs import DATA  # noqa: E402

HEADER = "# convert_cards.py の出力（review: pending）。確認後に real.yaml へ移す。\n"


def migrate(src: Path, dst: Path, check_only: bool = False) -> int:
    cards = cardstore.read(src)
    ids = [c["id"] for c in cards]
    if len(ids) != len(set(ids)):
        raise SystemExit("重複IDがある。dedupe_cards.py で整理してから")
    tmp = Path(tempfile.mkdtemp())
    try:
        cardstore.write(tmp / "c", cards, HEADER)
        back = {c["id"]: c for c in cardstore.read(tmp / "c")}
        if back != {c["id"]: c for c in cards}:
            raise SystemExit("分割後の内容が元と一致しない。中止")
        if not check_only:
            if dst.exists():
                raise SystemExit(f"{dst} が既にある。中止")
            shutil.copytree(tmp / "c", dst)
            src.unlink()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return len(cards)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--src", type=Path, default=DATA / "cards" / "converted.yaml")
    ap.add_argument("--dst", type=Path, default=DATA / "cards" / "converted")
    a = ap.parse_args(argv)
    n = migrate(a.src, a.dst, a.check)
    print(f"{n}枚: {'検査のみ（問題なし）' if a.check else f'{a.dst} へ移した'}")


if __name__ == "__main__":
    main()
