"""デッキ側の自動改善。 python tools/deck_fix.py --targets data/autofix/targets.yaml --seeds 30 [--only saga] [--stage-from logs/autofix.jsonl]
cards 段階（部品が揃わない）のデッキへ、部品追加・準備札追加の候補を作り、同一シード比較で有意に良いものだけ data/deckplans/auto/ に保存する。
holdout コンボは対象外。未変換カードを含む候補は自動採用しない。結果は --out（既定 logs/deckfix.jsonl）に追記。"""
import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.defs import load_rules  # noqa: E402
from dmsim.deckplan.auto import auto_improve  # noqa: E402
from dmsim.solitaire import load_deck  # noqa: E402


def cards_stage_decks(path: str) -> set[str]:
    """autofix の履歴から、直近の診断が cards 段階（deck_hint 付き）のデッキ名の目印を返す。履歴にコンボ名があれば使う。"""
    out = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("stage") == "cards" and e.get("deck_hint"):
            out.add(e.get("combo", "*"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default="data/autofix/targets.yaml")
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--stage-from", help="autofix の履歴。cards 段階の記録があるときだけ回す（コンボ名なしの記録は全対象）")
    ap.add_argument("--setup", help="仕込み済み開始局面のYAML（全対象に適用）。無ければ targets の setup を使う")
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--out", default="logs/deckfix.jsonl")
    a = ap.parse_args(argv)
    combos = {c["id"]: c for c in yaml.safe_load(Path("data/known_combos/combos.yaml").read_text(encoding="utf-8"))["combos"]}
    ts = yaml.safe_load(Path(a.targets).read_text(encoding="utf-8"))["targets"]
    gate = cards_stage_decks(a.stage_from) if a.stage_from else None
    if gate is not None and not gate:
        print("cards 段階の記録なし。何もしない"); return 0
    rules = load_rules()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    for t in ts:
        c = combos.get(t["combo"])
        if c is None or c.get("split") == "holdout" or (a.only and t["combo"] not in a.only):
            continue
        if gate and "*" not in gate and t["combo"] not in gate:
            continue
        deck = load_deck(t["deck"])
        opp = load_deck(t["opp_deck"]) if t.get("opp_deck") else ["T001"] * 40
        setup_path = a.setup or t.get("setup")        # 仕込み済み開始局面（4ターン以内キル率を現実的に比べるため。無ければ冷たい開幕）
        setup = yaml.safe_load(Path(setup_path).read_text(encoding="utf-8")) if setup_path else None
        r = auto_improve(rules, deck, opp, c, list(range(1, a.seeds + 1)), a.out, rounds=a.rounds, turn=a.turns, setup=setup)
        print(t["combo"], r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
