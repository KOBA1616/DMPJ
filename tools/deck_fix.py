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
from dmsim.deckplan.auto import add_candidates, two_stage, unused_names  # noqa: E402
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
    ap.add_argument("--workers", type=int, default=1, help="並列プロセス数（seeds を分けて fork で回す）")
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--usage-seeds", type=int, default=8, help="使われにくい札を探す試行数（0で無効）")
    ap.add_argument("--cands", type=int, default=4, help="種類ごとの候補数")
    ap.add_argument("--coarse-budget", type=int, default=40, help="①粗比較の base_budget（通常は 200）")
    ap.add_argument("--coarse-seeds", type=int, default=None, help="①粗比較に使う局数（省略時は --seeds と同じ。時間上限に収めたいとき減らす）")
    ap.add_argument("--top-k", type=int, default=2, help="②通常予算で再比較する上位件数")
    ap.add_argument("--time-budget", type=int, default=0, help="全体の時間予算（秒）。指定すると対象ごとに候補数と粗比較の局数を自動配分し、締め切りで打ち切る（--cands/--coarse-seeds は上限）")
    ap.add_argument("--history", default="data/autofix/deckfix_times.yaml", help="--time-budget 用の所要時間の履歴（前回途中のデッキを優先する）")
    ap.add_argument("--out", default="logs/deckfix.jsonl")
    a = ap.parse_args(argv)
    combos = {c["id"]: c for c in yaml.safe_load(Path("data/known_combos/combos.yaml").read_text(encoding="utf-8"))["combos"]}
    ts = yaml.safe_load(Path(a.targets).read_text(encoding="utf-8"))["targets"]
    gate = cards_stage_decks(a.stage_from) if a.stage_from else None
    if gate is not None and not gate:
        print("cards 段階の記録なし。何もしない"); return 0
    rules = load_rules()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    import time
    from dmsim.deckplan import budget as B
    hist = B.load_history(a.history) if a.time_budget else {}
    ok = lambda t: (c := combos.get(t["combo"])) is not None and c.get("split") != "holdout" and not (a.only and t["combo"] not in a.only) \
        and not (gate and "*" not in gate and t["combo"] not in gate)
    ts = [t for t in ts if ok(t)]
    if a.time_budget:
        names = B.order_targets([t["combo"] for t in ts], hist)
        ts = sorted(ts, key=lambda t: names.index(t["combo"]))      # 前回途中・未実行のデッキが先
    start = time.time()
    for i, t in enumerate(ts):
        c = combos[t["combo"]]
        cands, cs, deadline, cb = a.cands, a.coarse_seeds, None, a.coarse_budget
        deck = load_deck(t["deck"])
        opp = load_deck(t["opp_deck"]) if t.get("opp_deck") else ["T001"] * 40
        setup_path = a.setup or t.get("setup")        # 仕込み済み開始局面（4ターン以内キル率を現実的に比べるため。無ければ冷たい開幕）
        setup = yaml.safe_load(Path(setup_path).read_text(encoding="utf-8")) if setup_path else None
        if a.time_budget:
            slot = (a.time_budget - (time.time() - start)) / (len(ts) - i)
            if slot < B.MIN_SLOT_SEC:
                print(t["combo"], "時間予算の残りが少ないので次回へ"); continue
            pu = B.probe_unit(rules, deck, opp, setup, a.workers, a.coarse_budget)      # 1シードの実測で重いデッキを自動検出
            cands, cs, cb = B.allocate(hist.get(t["combo"]), slot, a.cands, a.coarse_seeds or a.seeds, probe=pu, max_budget=a.coarse_budget)
            print(t["combo"], f"枠{slot:.0f}秒 実測{pu:.1f}秒/候補/局 → 候補{cands}/種類 粗比較{cs}局 予算{cb}")
            deadline = time.time() + slot * B.SAFETY
        un = unused_names(rules, deck, opp, list(range(1, a.usage_seeds + 1))) if a.usage_seeds else []   # 抜く候補（usage 監査）
        r = two_stage(rules, deck, opp, c, list(range(1, a.seeds + 1)), a.out, turn=a.turns, setup=setup, workers=a.workers,
                      unused=un, adds=add_candidates(c), n=cands, coarse_budget=cb, top_k=a.top_k, coarse_seeds=cs, deadline=deadline)
        print(t["combo"], r)
        if a.time_budget:
            B.update(hist, t["combo"], r, cands, cs or a.seeds, time.time(), cb)
            B.save_history(a.history, hist)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
