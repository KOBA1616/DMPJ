"""複数ターン（3〜4ターンキル）の全探索方式による発見ランナー（試作）。

条件の固定: デッキ・シード（=山札の並びとドロー）・相手（無抵抗）を固定し、
「判断の全探索」を行う。ドローの全順序まで含めた全探索ではないので、
判定の主張は scope（デッキ／シード／ターン数）の中だけに及ぶ。

方式は exhaustive_proto の段階的拡大をそのまま使う:
  段1: 通常の候補列挙＋combo_cap=6 / 段2: 候補全列挙＋combo_cap=64 /
  段3: 全上限解除。勝ち手順が見つかれば構成的な証明になる。
  「勝ちなし」は段3が最後まで終わった場合だけ証明になる（複数ターンでは
  段3が終わらないことが多く、その場合は unknown として記録する）。

ログは exhaustive_proto と同じ流儀（ヘッダ＋case_start/stage_result/case_result、
勝ち手順は再生可能な記録ファイルへ分離）。ただし scope はデッキ対戦用
（deck/seed/max_turn）で、exhaustive_log.schema.json の case_start とは
キー構成が異なる（スキーマ拡張は宿題）。

使い方:
  python tools/exhaustive_multiturn.py --deck data/decks/saga.yaml --seeds 1,2,3,4 --stages 1,2
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dmsim import load_rules  # noqa: E402
from dmsim.eval.measure import load_deck  # noqa: E402
import dmsim.search.turn as turn  # noqa: E402
import dmsim.search.game as game  # noqa: E402
from exhaustive_proto import STAGES, _make_stage_search, cfg_suffix, stage_candidates  # noqa: E402

OPP_DECK = ["dm01-080"] * 40   # 無抵抗の相手（チャージのみ）


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", default="data/decks/saga.yaml")
    ap.add_argument("--seeds", default="1,2,3,4")
    ap.add_argument("--max-turn", type=int, default=4)
    ap.add_argument("--stages", default="1,2")
    ap.add_argument("--order", default="value", choices=["rank", "canonical", "value"])
    ap.add_argument("--budget", type=int, default=200_000, help="1ターンあたりの探索予算（段の上限とは別）")
    ap.add_argument("--out", default="logs/exhaustive_multiturn.jsonl")
    a = ap.parse_args()

    stage_ids = {int(s) for s in a.stages.split(",") if s.strip()}
    stages = [st for st in STAGES if st["stage"] in stage_ids]
    seeds = [int(s) for s in a.seeds.split(",") if s.strip()]

    rules = load_rules()
    print("rules loaded", flush=True)
    deck = load_deck(a.deck)
    deck_name = Path(a.deck).stem

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    f = out.open("w", encoding="utf-8")

    def w(obj):
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        f.flush()

    from dmsim.eval.explog import engine_version
    settings = {"mode": "staged-exhaustive multiturn", "budget_per_turn": a.budget,
                "opp": "passive (charge only)", "max_turn": a.max_turn,
                "order": a.order, "stages": a.stages}
    w({"kind": "header", "tool": "exhaustive_multiturn", "schema": "exhaustive-proto-1",
       "engine_version": engine_version("."), "settings": settings})
    # 記録ファイル名の設定サフィックス（設定が違う走行同士の上書き事故を防ぐ）
    cfg_hash = cfg_suffix(settings)

    orig_candidates = turn.candidates
    try:
        for seed in seeds:
            case = f"{deck_name} seed{seed} T{a.max_turn}"
            w({"kind": "case_start", "case": case, "mode": "exhaustive-staged-multiturn",
               "scope": {"deck": a.deck, "deck_size": len(deck), "seed": seed,
                         "max_turn": a.max_turn, "opp": "dm01-080x40 passive"}})
            verdict, best = "unknown", None
            t0 = time.perf_counter()
            for st in stages:
                fn, _label = stage_candidates(a.order, st["stage"])
                turn.candidates = fn
                game.TurnSearch = _make_stage_search(st["stock_offsets"])
                ts = time.perf_counter()
                try:
                    res, final = game.play_game(rules, deck, OPP_DECK, seed, max_turn=a.max_turn,
                                                budget=a.budget, lock_rounds=0)
                except Exception as e:
                    w({"kind": "stage_result", "case": case, "stage": st["stage"], "verdict": "error",
                       "error": f"{type(e).__name__}: {e}", "wall_seconds": round(time.perf_counter() - ts, 3)})
                    print(f"[{case}] stage{st['stage']} ERROR {e}", flush=True)
                    verdict = "error"
                    break
                sv = "kill" if res.kind else ("lost" if res.lost else "no-kill")
                w({"kind": "stage_result", "case": case, "stage": st["stage"], "verdict": sv,
                   "kill_kind": res.kind, "kill_turn": res.kill_turn, "origin": res.origin,
                   "nodes": res.nodes, "decisions": res.decisions, "loops_chosen": len(res.loops or []),
                   "error": res.error, "wall_seconds": round(time.perf_counter() - ts, 3)})
                print(f"[{case}] stage{st['stage']} {sv.upper()} kill_turn={res.kill_turn} "
                      f"kind={res.kind} nodes={res.nodes} wall={time.perf_counter() - ts:.1f}s", flush=True)
                if res.kind:
                    verdict = "kill_3_4" if res.kill_turn in (3, 4) else f"kill_turn{res.kill_turn}"
                    best = (res, final)
                    break
                if res.lost:
                    verdict = "lost"
                    break
                if st["stage"] == STAGES[-1]["stage"]:
                    verdict = "no-kill"   # 最終段まで終わって勝ちなし = scope 内の証明
            record_path = None
            if best is not None:
                from dmsim.engine.play import deck_lists, make_record
                rec_dir = Path("logs/exhaustive_records")
                rec_dir.mkdir(parents=True, exist_ok=True)
                record_path = str(rec_dir / (re.sub(r"[^0-9A-Za-z]+", "_", case)
                                             + f"-{cfg_hash}.json"))
                Path(record_path).write_text(json.dumps(
                    make_record(best[1], deck_lists(best[1]), seed,
                                note=f"{verdict} deck={a.deck}"), ensure_ascii=False), encoding="utf-8")
            w({"kind": "case_result", "case": case, "mode": "exhaustive-staged-multiturn",
               "verdict": verdict,
               "kill_kind": best[0].kind if best else None, "kill_turn": best[0].kill_turn if best else None,
               "origin": best[0].origin if best else None,
               "wall_seconds": round(time.perf_counter() - t0, 3), "record": record_path})
            print(f"[{case}] => {verdict} wall={time.perf_counter() - t0:.1f}s", flush=True)
    finally:
        turn.candidates = orig_candidates
        f.close()
    print(f"log written: {a.out}", flush=True)


if __name__ == "__main__":
    main()
