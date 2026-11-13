"""サガループの「引いて捨てる」を乱数で掘り進め、山札が少なくなったところから通常の探索（TurnSearch）に渡して、
勝ち筋を自力で見つけられるかの成功率を測る。台本（loopcheck_full_chain.py）と違い、捨てる札・蘇生先・出す札は乱数で選ぶ。
実行: PYTHONPATH=. python tools/discover_dig.py [試行数] [探索に渡す山札の残り枚数] [探索予算]"""
import random
import sys

from dmsim import scenario as sc
from dmsim.defs import load_rules
from dmsim.play_api import InfoLevel, PlayConfig, search_turn
from dmsim.engine_view import active_of, defn_of, result_of, turn_of, zone_of  # noqa: E402

SAGA, SHAKO, DRAG, IWA = "dm22ex2-021", "dmrp03-s03", "dm22ex1-007", "dmrp03-036"
IZA, KODAMA, ET = "dm22ex1-025", "dmex10-020", "dm26ex2-071"
ME = 0


def start(rules, rng, deck_left=18):
    spec = {"p0": {"hand": [SAGA, KODAMA, IZA, "T001"], "mana": ["dm01-080", "dm01-080", "dm01-027"],
                   "graveyard": [ET, SAGA], "deck": [DRAG, IWA, SHAKO]},
            "p1": {}, "deck_size": 40, "deck_left": [deck_left, 40], "seed": rng.randrange(1 << 30)}
    e = sc.build(rules, spec)
    deck = zone_of(e, "deck", 0)
    key = [c for c in deck if defn_of(e, c) in (DRAG, IWA, SHAKO)]
    rest = [c for c in deck if c not in key]
    order = rest[:]
    for c in key:
        order.insert(rng.randrange(len(order) + 1), c)
    deck[:] = order
    return e


def dig(eng, rng, stop_deck):
    """自分の決定を乱数で答えて、山札が stop_deck 枚以下になるか勝敗が決まるまで進める。"""
    for _ in range(4000):
        d = eng.advance()
        if d is None or result_of(eng):
            return
        if d["player"] != ME or active_of(eng) != ME:
            eng.answer([0] if d["min"] >= 1 else [])
            continue
        if len(zone_of(eng, "deck", ME)) <= stop_deck:
            return
        keys = [o["key"] for o in d["options"]]
        k = d["kind"]
        if k == "charge" or k == "attack":
            eng.answer([keys.index("pass")])
        elif k == "main":
            play = [i for i, x in enumerate(keys) if x.startswith("play:")]
            eng.answer([rng.choice(play)] if play else [keys.index("pass")])
        elif k == "yes_no":
            eng.answer([keys.index("yes")])
        elif d["max"] == 1 and d["min"] == 1:
            eng.answer([rng.randrange(len(keys))])
        else:
            n = rng.randint(d["min"], d["max"])
            eng.answer(sorted(rng.sample(range(len(keys)), n)))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    stop = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    budget = int(sys.argv[3]) if len(sys.argv) > 3 else 1500
    rules = load_rules()
    rng = random.Random(1)
    wins = reached = 0
    for i in range(n):
        eng = start(rules, rng)
        t0 = turn_of(eng)
        try:
            dig(eng, rng, stop)
        except Exception as ex:      # 乱数の答えが不正になった試行は捨てる
            continue
        if result_of(eng):
            wins += result_of(eng).get("winner") == ME and result_of(eng).get("turn") == t0
            continue
        if len(zone_of(eng, "deck", ME)) > stop:
            continue
        reached += 1
        out, _ = search_turn(eng, PlayConfig(me=ME, budget=budget), InfoLevel.CHEAT)
        r = result_of(out)
        if r and r.get("winner") == ME and r.get("turn") == t0:      # そのターンのうちの勝ちだけ数える
            wins += 1
    print(f"試行{n}: 探索に到達{reached}, 勝ち{wins}")


if __name__ == "__main__":
    main()
