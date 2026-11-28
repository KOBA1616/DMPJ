"""使い方: PYTHONPATH=. python tools/saga_variants.py [局数] [hunt の measure.json] [出力]
サガ変形（hunt の物差しでループが回った組）が元のサガより入口に早く・多く届くかを同一シードで比べる。
デッキは basebuild_saga（中核固定・基盤を貪欲選択）。変形は残り2枚（サガ以外）を4枚ずつ、基盤の最後の2種（各4枚）と入れ替える。
入口は登録簿のサガの入口（新しい定義）。相手は段階1、通常開幕、6ターンまで。"""
import json, sys, time, statistics, yaml
from dmsim.cards.defs import load_rules
from dmsim.eval import loop_entry as L
from dmsim.eval.api import measure_assembly
OUT = sys.argv[3] if len(sys.argv) > 3 else "runs/saga_variants.json"   # 途中結果（続きから回す）
rules = load_rules()
ls = L.load("saga")
from dmsim.cards.decks import load_deck
base = load_deck("data/decks/basebuild_saga.yaml")
drop = ["dm22ex1-cho47", "dm22ex1-cho14"]
rows = [r for r in json.load(open(sys.argv[2] if len(sys.argv) > 2 else "runs/hunt/latest/measure.json"))["rows"] if r["stage1"] > 0]
items = [("元のサガ（basebuild_saga）", [], base)]
for r in rows:
    extra = [c for c in r["cards"] if c != "dm22ex2-021"]
    deck = [c for c in base if c not in drop] + [c for c in extra for _ in range(4)]
    deck += [c for c in base if c in drop][: 40 - len(deck)]
    items.append(("+".join(r["names"]), extra, deck))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 12
import os
out = json.load(open(OUT))["rows"] if os.path.exists(OUT) else []
done_ = {o["name"] for o in out}
t0 = time.time()
for name, extra, deck in items:
    if name in done_:
        continue
    g = measure_assembly(rules, ls, deck, range(1, N + 1), max_turn=6, budget=200, opp_level=1, workers=4)
    et = [x["entry_turn"] for x in g if x["entry_turn"] is not None]
    out.append({"name": name, "extra": extra, "games": len(g), "entry_rate": round(len(et) / len(g), 3),
                "entry_le4": sum(t <= 4 for t in et), "entry_median": statistics.median(et) if et else None,
                "entry_best": min(et) if et else None, "stage2": sum(bool(x["stage2"]) for x in g),
                "errors": sum(1 for x in g if x["error"]), "entry_turns": [x["entry_turn"] for x in g]})
    o = out[-1]
    print(name[:50], o["entry_rate"], o["entry_le4"], o["entry_median"], o["stage2"], o["errors"], f"{time.time()-t0:.0f}s", flush=True)
    json.dump({"seeds": N, "opp_level": 1, "max_turn": 6, "deck": "basebuild_saga, 変形は cho47/cho14 と入れ替え", "rows": out},
              open(OUT, "w"), ensure_ascii=False, indent=1)
print("done", flush=True)
