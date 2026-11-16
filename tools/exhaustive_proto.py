"""全探索モードの試作（ノード制限なし・小規模局面専用）。

通常の TurnSearch の打ち切りを外して、小さい固定局面で
「勝ちがあるか／無いか」を最後まで調べ切るための実験スクリプト。
エンジン本体は変えず、このプロセス内だけで候補生成を差し替える。

打ち切りを外す対象:
  - budget: 10**12（実質無制限。使い切った後の貪欲ロールアウトには入らない）
  - combo_cap: 10**9（複数選択の組み合わせ上限を外す）
  - candidates() の pay_mana 上位2通り制限と、choose_evo_source の2順列制限
  - stock_offsets: 0..127（ループのストック周回数を上限と上限-1 だけでなく全部試す）

維持するもの（結果を変えない圧縮と、有限化の仕組み）:
  - 同じ意味キー・同じカード署名の選択肢の統合（candidates の sig 重複除去）
  - 既展開局面の再展開なし（TurnSearch.seen）
  - ループ証明書による周回の圧縮（fast_forward）。周回数だけを全て試す

使い方:
  python tools/exhaustive_proto.py            # 既定の小ケース一式
結果は「勝ち（手順あり）／勝ちなし（探索完了）」で出すが、seen の抽象キーや
証明書化できないループについては本体 TurnSearch の仕様に依存する点に注意。

試作の実測（2026-11-16, Python エンジン, このVM）:
  - A 勝ちケース（シャコガイル場・山札8）: 通常 7ノード / 全探索 7ノード、両方 KILL
  - B 払い無し（山札8）: 通常 39ノード / 全探索 66ノードで NO-KILL を最後まで確認（0.3秒）
  - C saga_setup（ドラゲリオン無し）: 全探索 21ノードで NO-KILL
  - D saga_setup + ドラゲリオン: 通常は 27ノード・0.4秒で KILL するのに、
    候補全列挙版（V1）は数分回しても終わらなかった。
    爆発点はノード予算ではなく「複数選択の組み合わせ列挙」そのもの:
    墓地15枚からの選択や進化元選択で組み合わせが桁違いに増え、
    ハズレの枝を最後まで掘る全探索では、勝ち筋が早く見つかっても
    先に試した枝の全展開が重い。進化元の全順列は階乗になるため最初から組の列挙に絞った。
  → 本実装では「全列挙する決定の種類」を絞るか、勝ち筋に近い順の枝を
    完全に掘り切る前に打ち切れる反復深化との併用が要る、というのが試作の結論。
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim import load_rules  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
import dmsim.search.turn as turn  # noqa: E402
import dmsim.search.game as game  # noqa: E402
from dmsim.search.turn import TurnSearch  # noqa: E402

SAGA = "dm22ex2-021"        # 絶望神サガ
SHAKO = "dmrp03-s03"        # 水上第九院 シャコガイル
DRAG = "dm22ex1-007"        # 超神星DOOM・ドラゲリオン
IWASHIN = "dmrp03-036"      # 一なる部隊 イワシン
MANA = ["dm01-080", "dm01-080", "dm01-027"]


def _enumerate(eng, d, order, limit=10 ** 9):
    """order（選択肢の並び）に従って組み合わせを列挙する共通部。

    sig による同値統合は残す。これは「良さそうな順」ではなく、同じ意味の
    選択肢を1つにまとめる等価性の処理なので、順序とは別扱い。
    組み合わせの生成は元の候補生成と同じく「多く選ぶ組」から先に出す
    （列挙の構造であって、良し悪しの順位ではないという整理）。
    limit に達したら生成を止める（全生成してから切ると、生成自体が爆発する。
    v1 の全探索がケースDで終わらなかった主因はこれ）。
    """
    if d["max"] == 1 and d["min"] == 1:
        out, seen = [], set()
        cs = getattr(eng, "card_sig", None)
        for i in order:
            o = d["options"][i]
            sig = (o["key"],) + (turn._card_sig(eng, cs, o["cid"]) if "cid" in o and o.get("name") == "?" else ())
            if sig in seen:
                continue
            seen.add(sig)
            out.append([i])
        return out  # pay_mana の上位2通り制限を外す
    keys = [o["key"] for o in d["options"]]
    out, seen = [], set()
    # 進化元は「組」で列挙し、順列は先頭順の1通りだけにする。
    # 全順列は階乗で爆発する（試作初版で実測: 墓地15枚の局面で2分以上終わらない）。
    # 順序が結果に効くケースの完全化は、本実装時の課題として残す。
    for n in range(d["max"], d["min"] - 1, -1):
        for combo in itertools.combinations(order, n):
            sig = tuple(sorted(keys[i] for i in combo))
            if sig in seen:
                continue
            seen.add(sig)
            out.append(list(combo))
            if len(out) >= limit:
                return out
    return out


def _classify(d) -> str:
    """決定の種類。爆発の危険度が種類でまったく違うので、上限は種類別に持つ。"""
    if d["min"] == 1 and d["max"] == 1:
        return "single"          # 1つ選ぶ決定（pay_mana・出す・攻撃・はい/いいえ等）。選択肢の数しか増えない
    if d["kind"] == "choose_evo_source":
        return "evo"             # 進化元の組。組み合わせで増える
    return "multi"               # 複数選択（choose_cards 等）。組み合わせ爆発の主犯


# 段ごとの種類別上限。single は全段で無制限（安い決定を絞る意味がない）。
# 段を分けるのは multi / evo だけ。stock_offsets は決定ではなくループ処理の軸として別に段を持つ。
KIND_CAPS = {
    1: {"multi": 6, "evo": 6},
    2: {"multi": 64, "evo": 64},
    3: {"multi": 10 ** 9, "evo": 10 ** 9},
}


def _value_after(eng, choice, w, player) -> float:
    """選択肢を実際に選んだ後の局面の評価値（leaf_eval.evaluate）。順序付け専用。"""
    from dmsim.search.leaf_eval import evaluate
    try:
        e2 = eng.clone()
        e2.answer(list(choice))
        for _ in range(400):
            if e2.advance() is not None:
                break
        return evaluate(e2, player, w)
    except Exception:
        return float("-inf")


def _ordered_combos(eng, d, w, order_name, limit):
    """順序方式に従って組み合わせを並べ、上限 limit まで返す。

    rank / canonical は生成しながら limit で止める（全生成は爆発するため）。
    value は、組み合わせ総数が少なければ各組を選んだ後の局面評価で並べ替え、
    多ければ正準順序の先頭 limit 個にフォールバックする。
    """
    n = len(d["options"])
    if order_name == "value":
        if _classify(d) == "single":
            base = _enumerate(eng, d, list(range(n)))
            scored = [(_value_after(eng, c, w, d["player"]), c) for c in base]
            scored.sort(key=lambda t: -t[0])
            return [c for _, c in scored][:limit]
        combos = _enumerate(eng, d, list(range(n)), limit=301)
        if len(combos) <= 300:
            scored = [(_value_after(eng, c, w, d["player"]), c) for c in combos]
            scored.sort(key=lambda t: -t[0])
            return [c for _, c in scored][:limit]
        return combos[:limit]
    order = turn._rank(eng, d, w) if order_name == "rank" else list(range(n))
    return _enumerate(eng, d, order, limit=limit)


def make_candidates(order_name: str, stage: int):
    """段×順序方式の候補生成関数を作る。上限は決定の種類ごとに適用する。"""
    kind_caps = KIND_CAPS[stage]

    def cands(eng, d, w, cap=10 ** 9):
        eff = kind_caps.get(_classify(d), 10 ** 9)   # single は表に無い = 無制限
        return _ordered_combos(eng, d, w, order_name, eff)

    return cands


def stage_candidates(order_name: str, stage: int):
    """(候補生成関数, ログ用ラベル) を返す。"""
    return make_candidates(order_name, stage), order_name


class ExhaustiveTurnSearch(TurnSearch):
    def __init__(self, me, budget=10 ** 12, weights=None, **kw):
        kw["combo_cap"] = 10 ** 9
        super().__init__(me, budget, weights, **kw)
        self.stock_offsets = tuple(range(0, 128))


def spec(deck_left, **p0):
    base = {"hand": [SAGA, "T001", "T001", "T001", "T001", "T001"], "mana": MANA,
            "graveyard": [SAGA, "T001", "T001", "T001"]}
    return {"p0": {**base, **p0}, "p1": {}, "deck_size": 40, "deck_left": [deck_left, 40], "seed": 1}


class JsonlLog:
    """全探索の証拠ログ（explog と同じ流儀: 1行目ヘッダ＋版、以降は1イベント1行）。

    読み方:
      - case_start だけあって case_result が無いケース = 中断・未完了 → 判定は unknown。
        全探索は「終わらなかったこと」自体が結果なので、開始時点で先に書いて flush する。
      - verdict は kill / no-kill / lost / error の区別を残す。no-kill は
        「この scope（配置・1ターン）では勝ちなしが最後まで確認できた」という意味で、
        scope の外（複数ターン・別配置）には主張を広げない。scope は case_start に記録する。
    """

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._f = path.open("w", encoding="utf-8")
        from dmsim.eval.explog import engine_version
        self.write({"kind": "header", "tool": "exhaustive_proto", "schema": "exhaustive-proto-1",
                    "engine_version": engine_version("."),
                    "settings": {"budget": "unlimited", "combo_cap": "unlimited",
                                 "pay_mana_cap": "removed", "stock_offsets": "all",
                                 "equivalence_kept": ["sig-dedup", "seen-tkey", "loop-certificate"]}})

    def write(self, obj: dict):
        self._f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self._f.flush()

    def close(self):
        self._f.close()


def _scope_of(spec_dict: dict) -> dict:
    p0 = spec_dict.get("p0", {})
    return {"hand": p0.get("hand", []), "mana": p0.get("mana", []), "graveyard": p0.get("graveyard", []),
            "bz": p0.get("bz", []), "deck_size": spec_dict.get("deck_size"), "deck_left": spec_dict.get("deck_left"),
            "seed": spec_dict.get("seed", 1), "turns": 1}


def run_case(rules, name, spec_dict, log: JsonlLog | None = None, mode: str = "exhaustive"):
    if log is not None:
        log.write({"kind": "case_start", "case": name, "mode": mode, "scope": _scope_of(spec_dict)})
    eng = sc.build(rules, spec_dict)
    t0 = time.perf_counter()
    try:
        res, final = game.play_game(rules, None, None, 1, max_turn=1, start=eng, lock_rounds=0)
    except Exception as e:  # 探索自体の例外も「結果」として残す（unknown 扱い）
        if log is not None:
            log.write({"kind": "case_result", "case": name, "mode": mode, "verdict": "error",
                       "error": f"{type(e).__name__}: {e}", "wall_seconds": round(time.perf_counter() - t0, 3)})
        print(f"[{name}] ERROR {e}", flush=True)
        return None
    dt = time.perf_counter() - t0
    verdict = "kill" if res.kind else ("lost" if res.lost else "no-kill")
    record_path = None
    if res.kind:  # 勝ち手順は再生可能な記録として別ファイルに残す（ログ本体には混ぜない）
        from dmsim.engine.play import deck_lists, make_record
        rec_dir = Path("logs/exhaustive_records")
        rec_dir.mkdir(parents=True, exist_ok=True)
        record_path = str(rec_dir / (re.sub(r"[^0-9A-Za-z]+", "_", name) + ".json"))
        Path(record_path).write_text(json.dumps(
            make_record(final, deck_lists(final), 1, scenario=spec_dict), ensure_ascii=False), encoding="utf-8")
    if log is not None:
        log.write({"kind": "case_result", "case": name, "mode": mode, "verdict": verdict,
                   "kill_kind": res.kind, "kill_turn": res.kill_turn, "origin": res.origin,
                   "nodes": res.nodes, "decisions": res.decisions,
                   "loops_chosen": res.loops, "loops_tried": len(res.loop_candidates or []),
                   "error": res.error, "wall_seconds": round(dt, 3), "record": record_path})
    print(f"[{name}] {verdict.upper()} nodes={res.nodes} wall={dt:.1f}s", flush=True)  # stdout は要約だけ
    return res


def _make_stage_search(stock_offsets):
    class _StageSearch(TurnSearch):
        def __init__(self, me, budget=10 ** 12, weights=None, **kw):
            kw["combo_cap"] = 10 ** 9   # 上限は候補生成側（種類別）で適用するので、こちらは実質無制限
            super().__init__(me, budget, weights, **kw)
            self.stock_offsets = stock_offsets
    return _StageSearch


# 段階的拡大: 上限の小さい段から順に回す。勝ち手順が見つかればその時点で証明になる
# （手順は構成的な証拠）。「勝ちなし」の証明になるのは最終段（全上限解除）が
# 最後まで終わった場合だけ。途中の段で終わらなければ unknown のまま次段へ進む。
# v1（一段で全部外す）はケースDで組み合わせ列挙が爆発して終わらなかったための改修。
# 上限は決定の種類別（KIND_CAPS）: single は全段無制限、multi / evo だけが段で広がる。
STAGES = [
    {"stage": 1, "stock_offsets": (0, 1)},
    {"stage": 2, "stock_offsets": (0, 1)},
    {"stage": 3, "stock_offsets": tuple(range(0, 128))},
]


def run_case_staged(rules, name, spec_dict, log: JsonlLog | None = None, order: str = "value"):
    if log is not None:
        log.write({"kind": "case_start", "case": name, "mode": "exhaustive-staged", "scope": _scope_of(spec_dict)})
    orig_candidates = turn.candidates
    total_nodes, verdict, final_res, final_eng = 0, "unknown", None, None
    t0 = time.perf_counter()
    try:
        for st in STAGES:
            fn, label = stage_candidates(order, st["stage"])
            turn.candidates = fn
            game.TurnSearch = _make_stage_search(st["stock_offsets"])
            eng = sc.build(rules, spec_dict)
            ts = time.perf_counter()
            try:
                res, final = game.play_game(rules, None, None, 1, max_turn=1, start=eng,
                                            lock_rounds=0, budget=10 ** 12)
            except Exception as e:
                if log is not None:
                    log.write({"kind": "stage_result", "case": name, "stage": st["stage"], "candidates": label,
                               "kind_caps": KIND_CAPS[st["stage"]],
                               "stock_offsets": list(st["stock_offsets"])[:4], "verdict": "error",
                               "error": f"{type(e).__name__}: {e}", "wall_seconds": round(time.perf_counter() - ts, 3)})
                verdict = "error"
                break
            total_nodes += res.nodes
            sverdict = "kill" if res.kind else ("lost" if res.lost else "no-kill")
            if log is not None:
                log.write({"kind": "stage_result", "case": name, "stage": st["stage"], "candidates": label,
                           "kind_caps": KIND_CAPS[st["stage"]],
                           "stock_offsets": list(st["stock_offsets"])[:4], "verdict": sverdict,
                           "nodes": res.nodes, "wall_seconds": round(time.perf_counter() - ts, 3)})
            print(f"[{name}] stage{st['stage']} {sverdict.upper()} nodes={res.nodes} "
                  f"wall={time.perf_counter() - ts:.1f}s", flush=True)
            if res.kind or res.lost:
                verdict, final_res, final_eng = sverdict, res, final
                break
            if st["stage"] == STAGES[-1]["stage"]:
                verdict, final_res, final_eng = "no-kill", res, final
    finally:
        turn.candidates = orig_candidates
    record_path = None
    if verdict == "kill" and final_res is not None and final_eng is not None:
        from dmsim.engine.play import deck_lists, make_record
        rec_dir = Path("logs/exhaustive_records")
        rec_dir.mkdir(parents=True, exist_ok=True)
        record_path = str(rec_dir / (re.sub(r"[^0-9A-Za-z]+", "_", name) + ".json"))
        Path(record_path).write_text(json.dumps(
            make_record(final_eng, deck_lists(final_eng), 1, scenario=spec_dict), ensure_ascii=False), encoding="utf-8")
    if log is not None:
        log.write({"kind": "case_result", "case": name, "mode": "exhaustive-staged", "verdict": verdict,
                   "kill_kind": final_res.kind if final_res else None,
                   "kill_turn": final_res.kill_turn if final_res else None,
                   "origin": final_res.origin if final_res else None,
                   "nodes": total_nodes, "decisions": final_res.decisions if final_res else None,
                   "loops_chosen": final_res.loops if final_res else [],
                   "loops_tried": len(final_res.loop_candidates or []) if final_res else 0,
                   "error": final_res.error if final_res else None,
                   "wall_seconds": round(time.perf_counter() - t0, 3), "record": record_path})
    print(f"[{name}] => {verdict.upper()} total_nodes={total_nodes} wall={time.perf_counter() - t0:.1f}s", flush=True)
    return final_res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="A,B,C,D", help="実行するケース（A,B,C,D から選択）")
    ap.add_argument("--order", default="value", choices=["rank", "canonical", "value"],
                    help="選択肢の順序方式（rank=_rank ヒューリスティクス / canonical=提示順 / value=評価関数V）")
    ap.add_argument("--out", default="logs/exhaustive_proto.jsonl")
    a = ap.parse_args()
    want = {c.strip() for c in a.cases.split(",") if c.strip()}

    rules = load_rules()
    print("rules loaded", flush=True)
    log = JsonlLog(Path(a.out))

    # --- 対照: 通常探索（予算200・上限あり） ---
    print("--- baseline (budget=200, caps on) ---", flush=True)
    if "A" in want:
        run_case(rules, "base A win-case deck8 shako-bz", spec(8, bz=[SHAKO]), log, mode="baseline")
    if "B" in want:
        run_case(rules, "base B no-payoff deck8", spec(8), log, mode="baseline")

    # --- 全探索（段階的拡大） ---
    print("--- exhaustive staged (stage1 caps -> stage3 all off) ---", flush=True)
    if "A" in want:
        run_case_staged(rules, "exh A win-case deck8 shako-bz", spec(8, bz=[SHAKO]), log, order=a.order)
    if "B" in want:
        run_case_staged(rules, "exh B no-payoff deck8", spec(8), log, order=a.order)

    # tests/saga_setup.yaml: ドラゲリオンだけを抜いた配置（足すと勝ち、無ければ勝てないはず）
    import yaml
    if "C" in want:
        setup = yaml.safe_load(Path("tests/saga_setup.yaml").read_text(encoding="utf-8"))
        run_case_staged(rules, "exh C saga_setup (no DRAG)", setup, log, order=a.order)
    if "D" in want:
        setup2 = yaml.safe_load(Path("tests/saga_setup.yaml").read_text(encoding="utf-8"))
        _hand = list(setup2["p0"]["hand"])
        _hand[_hand.index("T001")] = DRAG          # 先頭の T001 をドラゲリオンに差し替える
        setup2["p0"]["hand"] = _hand
        run_case_staged(rules, "exh D saga_setup + DRAG in hand", setup2, log, order=a.order)
    log.close()
    print(f"log written: {a.out}", flush=True)


if __name__ == "__main__":
    main()
