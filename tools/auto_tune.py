"""ノブの自動チューニング（進化戦略）を実エンジンで回す。LLM・課金なし。
python tools/auto_tune.py --targets data/autofix/targets.yaml --seeds 20 --workers 4 --seconds 1500 --out logs/autotune.jsonl
採用は「調整用シードで有意＋別の再確認シードでも有意」の時だけ。採用した設定は --store（data/autofix/knobs.yaml）へ、
autofix の次回の開始点になる。holdout は除外。時間予算は --seconds（日次ルーティンの枠に合わせる）。"""
import argparse
from dataclasses import replace
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from auto_fix import _prep_ids  # noqa: E402
from dmsim.autofix import Knobs, Rule, harness_measure  # noqa: E402
from dmsim.autofix.batch import default_board, default_need  # noqa: E402
from dmsim.autofix import partdiscovery as PD  # noqa: E402
from dmsim.autofix import partsgenome as PG  # noqa: E402
from dmsim.autofix import valuelearn as VL  # noqa: E402
from dmsim.autofix.tune import evolve, tune  # noqa: E402
from dmsim.defs import load_rules  # noqa: E402
from dmsim.eval.progress import ProgressSpec  # noqa: E402
from dmsim.search.leaf_parts import load_specs  # noqa: E402
from dmsim.solitaire import load_deck  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default="data/autofix/targets.yaml")
    ap.add_argument("--seeds", type=int, default=20, help="調整用の局数（再確認用も同数、別シード）")
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--generations", type=int, default=3)
    ap.add_argument("--lam", type=int, default=3)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--seconds", type=int, default=1500, help="全対象の時間予算。超えたら次の対象へ進まない")
    ap.add_argument("--only", help="対象の combo id（カンマ区切り）")
    ap.add_argument("--store", default="data/autofix/knobs.yaml")
    ap.add_argument("--parts-store", default="data/autofix/parts.yaml", help="部品ごとの重み倍率（評価式の進化）の保存先")
    ap.add_argument("--parts-share", type=float, default=0.5, help="対象ごとの世代のうち部品の重みの進化に回す割合（0で無効）")
    ap.add_argument("--edits-store", default="data/autofix/parts_edits.yaml", help="部品の自動追加・削除の保存先")
    ap.add_argument("--discover-gens", type=int, default=2, help="部品の自動追加・削除に回す世代数（0で無効）")
    ap.add_argument("--learn-gens", type=int, default=2, help="経験ログからの価値の学習の採否に回す世代数（0で無効）")
    ap.add_argument("--value-data", default="data/autofix/value_data", help="自己対戦の経験ログ（追記）の置き場")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    combos = {c["id"]: c for c in yaml.safe_load(Path("data/known_combos/combos.yaml").read_text(encoding="utf-8"))["combos"]}
    ts = yaml.safe_load(Path(a.targets).read_text(encoding="utf-8"))["targets"]
    only = set(a.only.split(",")) if a.only else None
    rules, specs = load_rules(), load_specs()
    store = (yaml.safe_load(Path(a.store).read_text(encoding="utf-8")) or {}) if Path(a.store).exists() else {}
    pstore = (yaml.safe_load(Path(a.parts_store).read_text(encoding="utf-8")) or {}) if Path(a.parts_store).exists() else {}
    estore = (yaml.safe_load(Path(a.edits_store).read_text(encoding="utf-8")) or {}) if Path(a.edits_store).exists() else {}
    t0, rule = time.time(), Rule(turn=a.turns)
    for t in ts:
        c = combos.get(t["combo"])
        if c is None or c.get("split") == "holdout" or (only and t["combo"] not in only):
            continue
        if time.time() - t0 > a.seconds:
            print("時間切れ:", t["combo"], "以降は次回")
            break
        deck = load_deck(t["deck"])
        opp = load_deck(t["opp_deck"]) if t.get("opp_deck") else ["T001"] * 40
        spec = yaml.safe_load(Path(t["setup"]).read_text(encoding="utf-8")) if t.get("setup") else None
        ps = specs[t["combo"]]
        model0 = VL.load_model(t["combo"])
        ps = PD.apply_store(ps, estore.get(t["combo"]))                 # 採用済みの部品の追加・削除を反映
        ps_cur = PG.apply(ps, tuple(pstore.get(t["combo"]) or ()))     # 採用済みの重み倍率を反映してノブを探す
        prog = ProgressSpec(board=default_board(c), cards=default_need(c))
        prep = _prep_ids(c, rules, deck, opp, ps)

        def measure(k, seeds, _c=(rules, deck, opp, spec, prog, ps_cur, prep)):
            return harness_measure(_c[0], _c[1], _c[2], list(seeds), _c[3], _c[4], _c[5], max_turn=a.turns,
                                   workers=a.workers, prep_ids=_c[6], value_model=model0)(k)
        k0 = Knobs(**{**Knobs().__dict__, **store.get(t["combo"], {})})
        n = a.seeds
        k, hist = tune(measure, k0, range(1, n + 1), range(1000, 1000 + n), rule, a.generations, a.lam, ledger=a.out)
        acc = [h["verdict"] for h in hist].count("accept")
        print(t["combo"], "採用", acc, "回", k.__dict__ if k != k0 else "（変更なし）", f"{time.time() - t0:.0f}s")
        if k != k0:
            store[t["combo"]] = dict(k.__dict__)
            Path(a.store).write_text(yaml.safe_dump(store, allow_unicode=True), encoding="utf-8")
        if a.discover_gens > 0 and time.time() - t0 <= a.seconds:        # 部品の自動追加・削除: 勝った局と負けた局の最終局面の差から候補→進化で採否
            ps0 = PG.apply(ps, tuple(pstore.get(t["combo"]) or ()))
            m0 = harness_measure(rules, deck, opp, list(range(1, n + 1)), spec, prog, ps0, max_turn=a.turns, workers=a.workers, prep_ids=prep, value_model=model0)(k)
            cands = PD.discover(m0, ps, a.turns)
            if cands:
                def measure_e(g, seeds, _c=(rules, deck, opp, spec, prog, prep)):
                    return harness_measure(_c[0], _c[1], _c[2], list(seeds), _c[3], _c[4], PG.apply(PD.apply_edits(ps, cands, g), tuple(pstore.get(t["combo"]) or ())),
                                           max_turn=a.turns, workers=a.workers, prep_ids=_c[5], value_model=model0)(k)
                g, ehist = evolve(measure_e, frozenset(), lambda x, r: PD.mutate_genes(x, r, len(cands)), lambda x: {"parts_edit": PD.to_store(cands, x)},
                                  range(1, n + 1), range(1000, 1000 + n), rule, a.discover_gens, a.lam, seed=2, ledger=a.out)
                print(t["combo"], f"部品候補{len(cands)}件 採用", [h["verdict"] for h in ehist].count("accept"), "回", PD.to_store(cands, g) if g else "（変更なし）")
                if g:
                    new = PD.to_store(cands, g)
                    old = estore.get(t["combo"]) or {"add": [], "drop": []}
                    estore[t["combo"]] = {"add": old["add"] + [x for x in new["add"] if x not in old["add"]], "drop": old["drop"] + [x for x in new["drop"] if x not in old["drop"]]}
                    Path(a.edits_store).write_text(yaml.safe_dump(estore, allow_unicode=True), encoding="utf-8")
                    pstore.pop(t["combo"], None)                          # 部品表の長さが変わるので重み倍率は作り直す
                    if Path(a.parts_store).exists():
                        Path(a.parts_store).write_text(yaml.safe_dump(pstore, allow_unicode=True), encoding="utf-8")
                    ps = PD.apply_store(specs[t["combo"]], estore[t["combo"]])
        gp = round(a.generations * a.parts_share)
        if gp > 0 and ps.parts and time.time() - t0 <= a.seconds:        # 評価式の進化: 採用したノブのまま、部品ごとの重み倍率を動かす
            base_ps = ps
            g0 = tuple(pstore.get(t["combo"]) or PG.neutral(base_ps))
            if len(g0) != len(base_ps.parts):
                g0 = PG.neutral(base_ps)

            def measure_g(g, seeds, _c=(rules, deck, opp, spec, prog, prep)):
                return harness_measure(_c[0], _c[1], _c[2], list(seeds), _c[3], _c[4], PG.apply(base_ps, g), max_turn=a.turns,
                                       workers=a.workers, prep_ids=_c[5], value_model=model0)(k)
            g, ghist = evolve(measure_g, g0, PG.mutate, lambda x: {"parts_mult": list(x)}, range(1, n + 1), range(1000, 1000 + n),
                              rule, gp, a.lam, seed=1, ledger=a.out)
            print(t["combo"], "評価式の重み 採用", [h["verdict"] for h in ghist].count("accept"), "回", list(g) if g != g0 else "（変更なし）")
            if g != g0:
                pstore[t["combo"]] = list(g)
                Path(a.parts_store).write_text(yaml.safe_dump(pstore, allow_unicode=True), encoding="utf-8")

        if a.learn_gens > 0 and time.time() - t0 <= a.seconds:           # 経験ログからの価値の学習: 局面→キルの早さを回帰し、葉の評価への加点の倍率を進化＋再確認で採否
            ps_f = PG.apply(ps, tuple(pstore.get(t["combo"]) or ()))
            m0 = harness_measure(rules, deck, opp, list(range(1, n + 1)), spec, prog, ps_f, max_turn=a.turns, workers=a.workers, prep_ids=prep, value_model=model0)(k)
            names = VL.feature_names(ps_f)
            rows = VL.rows_from_curves(m0.get("curves", []), m0["kill"], ps_f, a.turns)
            allrows = VL.append_rows(f"{a.value_data}/{t['combo']}.jsonl", rows, names)
            model1 = VL.fit(allrows)
            if model1:
                def measure_l(g, seeds, _c=(rules, deck, opp, spec, prog, prep)):
                    tag, mult = g
                    return harness_measure(_c[0], _c[1], _c[2], list(seeds), _c[3], _c[4], ps_f, max_turn=a.turns, workers=a.workers, prep_ids=_c[5],
                                           value_model=(model1 if tag == "new" else model0))(replace(k, learned_mult=mult))
                g0 = ("old", k.learned_mult)
                g, lhist = evolve(measure_l, g0, lambda x, r: ("new", r.choice([m for m in VL.MULTS if m > 0])), lambda x: {"learned": list(x), "rows": model1["n"]},
                                  range(1, n + 1), range(1000, 1000 + n), rule, a.learn_gens, a.lam, seed=3, ledger=a.out)
                print(t["combo"], f"価値の学習(行{model1['n']}) 採用", [h["verdict"] for h in lhist].count("accept"), "回", list(g) if g != g0 else "（変更なし）")
                if g != g0:
                    VL.save_model(t["combo"], model1)
                    model0 = model1
                    k = replace(k, learned_mult=g[1])
                    store[t["combo"]] = dict(k.__dict__)
                    Path(a.store).write_text(yaml.safe_dump(store, allow_unicode=True), encoding="utf-8")


if __name__ == "__main__":
    main()
