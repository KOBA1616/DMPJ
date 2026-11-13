"""ループに入るまでの最小配置の探索。配置を変えながら、サガループ中の判断を乱数で掘り→探索に渡す方式
（tools/discover_dig.py と同じ）で、置換勝利に届く率を測る。
実行: PYTHONPATH=. python tools/minimal_setup.py [試行数] [探索に渡す山札の残り] [探索予算] [配置名の部分一致...]"""
import random
import sys

from dmsim.engine import scenario as sc
from dmsim.cards.defs import load_rules
from dmsim.play_api import InfoLevel, PlayConfig, search_turn
from dmsim.engine.view import defn_of, result_of, turn_of, zone_of  # noqa: E402

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from discover_dig import ME, dig  # noqa: E402

SAGA, SHAKO, DRAG, IWA = "dm22ex2-021", "dmrp03-s03", "dm22ex1-007", "dmrp03-036"
IZA, KODAMA, ET, BRUCE = "dm22ex1-025", "dmex10-020", "dm26ex2-071", "dmbd17-009"
M3 = ["dm01-080", "dm01-080", "dm01-027"]
M3D = ["dm01-027", "dm01-027", "dm01-080"]
F = "T001"

# 名前: (手札, 墓地, マナ, 山札に混ぜるカード)。山札のカードは乱数の位置に入る
SETUPS = {
    "A 手札サガ,コダマ,イザナギ／墓地タイフーン,サガ": ([SAGA, KODAMA, IZA, F], [ET, SAGA], M3, [DRAG, IWA, SHAKO]),
    "B1 手札サガのみ／墓地サガ,ダミー2（山札にコダマ・イザナギ）": ([SAGA], [SAGA, F, F], M3, [DRAG, IWA, SHAKO, KODAMA, IZA]),
    "B2 手札サガ,イザナギ／墓地サガ,ダミー2（山札にコダマ）": ([SAGA, IZA], [SAGA, F, F], M3, [DRAG, IWA, SHAKO, KODAMA]),
    "B3 手札サガ,コダマ,イザナギ／墓地サガ,ダミー2": ([SAGA, KODAMA, IZA], [SAGA, F, F], M3, [DRAG, IWA, SHAKO]),
    "C1 手札サガ,ブルース,イザナギ／墓地ダミー3（サガは1枚）": ([SAGA, BRUCE, IZA], [F, F, F], M3D, [DRAG, IWA, SHAKO, KODAMA]),
    "C2 手札サガ,ブルース,イザナギ,コダマ／墓地ダミー3": ([SAGA, BRUCE, IZA, KODAMA], [F, F, F], M3D, [DRAG, IWA, SHAKO]),
    "C3 手札サガ,ブルース／墓地イザナギ,ダミー2": ([SAGA, BRUCE], [IZA, F, F], M3D, [DRAG, IWA, SHAKO, KODAMA]),
    "D1 手札サガ,ブルース,イザナギ／墓地ダミー2": ([SAGA, BRUCE, IZA], [F, F], M3D, [DRAG, IWA, SHAKO, KODAMA]),
    "D2 手札サガ,ブルース,イザナギ／墓地ダミー1": ([SAGA, BRUCE, IZA], [F], M3D, [DRAG, IWA, SHAKO, KODAMA]),
    "D3 手札サガ,ブルース,イザナギ／墓地なし": ([SAGA, BRUCE, IZA], [], M3D, [DRAG, IWA, SHAKO, KODAMA]),
    "D4 手札サガ,ブルース,イザナギ／墓地ダミー3／マナ闇1枚": ([SAGA, BRUCE, IZA], [F, F, F], M3, [DRAG, IWA, SHAKO, KODAMA]),
    "D5 手札サガ,ブルース,イザナギ／墓地ダミー3／マナ4枚(闇2)": ([SAGA, BRUCE, IZA], [F, F, F], M3D + ["dm01-080"], [DRAG, IWA, SHAKO, KODAMA]),
}


def build(rules, rng, hand, gy, mana, deckcards, deck_left=20):
    spec = {"p0": {"hand": hand, "mana": mana, "graveyard": gy, "deck": list(deckcards)}, "p1": {},
            "deck_size": 40, "deck_left": [deck_left, 40], "seed": rng.randrange(1 << 30)}
    e = sc.build(rules, spec)
    deck = zone_of(e, "deck", 0)
    key = [c for c in deck if defn_of(e, c) in set(deckcards)]
    order = [c for c in deck if c not in key]
    for c in key:
        order.insert(rng.randrange(len(order) + 1), c)
    deck[:] = order
    return e


def _won(eng, t0):
    """そのターンのうちに自分が勝った（殴り勝ちなど後のターンの勝ちは数えない）"""
    r = result_of(eng)
    return bool(r and r.get("winner") == ME and r.get("turn") == t0)


def measure(rules, name, n, stop, budget, seed=1):
    hand, gy, mana, dc = SETUPS[name]
    rng = random.Random(seed)
    wins = reached = 0
    for _ in range(n):
        eng = build(rules, rng, hand, gy, mana, dc)
        t0 = turn_of(eng)
        try:
            dig(eng, rng, stop)
        except Exception:
            continue
        if result_of(eng):
            wins += _won(eng, t0)
            continue
        if len(zone_of(eng, "deck", ME)) > stop:
            continue
        reached += 1
        out, _ = search_turn(eng, PlayConfig(me=ME, budget=budget), InfoLevel.CHEAT)
        wins += _won(out, t0)
    return reached, wins


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    stop = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    budget = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
    pats = sys.argv[4:]
    rules = load_rules()
    for name in SETUPS:
        if pats and not any(p in name for p in pats):
            continue
        reached, wins = measure(rules, name, n, stop, budget)
        print(f"{name}: 試行{n} 到達{reached} 勝ち{wins}", flush=True)
