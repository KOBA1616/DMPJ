"""自立発見ランナーを回す。盤面を変異させて探索し、勝てた盤面を data/loops/auto/ に LoopSpec として保存する（LLM・課金なし）。

  python tools/auto_discover.py --config tools/auto_discover.yaml --seconds 600
config: pool（足してよいカードID）, seeds（種盤面 = scenario の spec のリスト）, filler, width, rate_seeds。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dmsim import load_rules  # noqa: E402
from dmsim.discovery.auto import AutoConfig, run, run_decks  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "tools" / "auto_discover.yaml"))
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--width", type=int)
    ap.add_argument("--rng-seed", type=int)
    ap.add_argument("--out", default=str(ROOT / "data" / "loops" / "auto"))
    a = ap.parse_args(argv)
    raw = yaml.safe_load(Path(a.config).read_text())
    cfg = AutoConfig(pool=raw["pool"], seeds=raw["seeds"], filler=raw.get("filler", "T013"), width=a.width or raw.get("width", 300),
                     rate_seeds=raw.get("rate_seeds", 50), seconds=a.seconds or raw.get("seconds", 300.0),
                     rng_seed=a.rng_seed or raw.get("rng_seed", 1), out_dir=Path(a.out),
                     eval_seeds=raw.get("eval_seeds", 8), max_turn=raw.get("max_turn", 8), opp_card=raw.get("opp_card", "T001"))
    stats = (run_decks if raw.get("mode", "deck") == "deck" else run)(load_rules(), cfg)
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
