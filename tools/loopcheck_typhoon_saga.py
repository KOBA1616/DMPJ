"""「タイフーンで引いて捨てて整えた次のターンに、サガループで勝てるか」の検証（3ターン目スタート時の配置）。
実行: PYTHONPATH=. python tools/loopcheck_typhoon_saga.py
結果（2026-10-25）: マナ3枚のうち闇を出せる札が2枚あり、手札にサガ・ドラゲリオン（＋シャコガイルが墓地にあるか、イワシンとシャコガイルが両方手札にある。シャコガイルだけ手札でイワシンが墓地だと届かない）、
墓地にサガがあれば1ターンで置換勝利まで届く。闇が1枚だと届かない。"""
from dmsim import scenario as sc
from dmsim.defs import load_rules
from dmsim.solitaire import play_game

r = load_rules()
SAGA, SHAKO, DRAG, IWA = "dm22ex2-021", "dmrp03-s03", "dm22ex1-007", "dmrp03-036"
ET = "dm26ex2-071"      # ツインパクト エマージェンシー・タイフーン
DARK2 = ["dm01-027", "dm01-027", "dm01-080"]     # 闇マナ2枚＋他1枚

CASES = [
    ("墓地サガ,イワ,シャコ,ET／手札サガ,ドラゲ／闇2", [SAGA, IWA, SHAKO, ET], [SAGA, DRAG, "T001"], DARK2),
    ("墓地サガ,シャコ,ET／手札サガ,ドラゲ,イワ／闇2", [SAGA, SHAKO, ET], [SAGA, DRAG, IWA], DARK2),
    ("墓地サガ,ET／手札サガ,ドラゲ,イワ,シャコ／闇2", [SAGA, ET], [SAGA, DRAG, IWA, SHAKO], DARK2),
    ("墓地サガ,イワ,ET／手札サガ,ドラゲ,シャコ／闇2", [SAGA, IWA, ET], [SAGA, DRAG, SHAKO], DARK2),
    ("墓地サガ,イワ,シャコ／手札サガ,ドラゲ／闇1", [SAGA, IWA, SHAKO], [SAGA, DRAG], ["dm01-027", "dm01-080", "dm01-080"]),
]

if __name__ == "__main__":
    for name, gy, hand, mana in CASES:
        spec = {"p0": {"hand": hand, "mana": mana, "graveyard": gy}, "p1": {}, "deck_size": 40,
                "deck_left": [33, 40], "seed": 1}
        res, e = play_game(r, None, None, 1, max_turn=1, start=sc.build(r, spec), lock_rounds=0, budget=8000)
        print(f"{name} -> {res.kind} T{res.kill_turn} loops={[(l['kind'], l['stocked']) for l in res.loops][:1]}")
