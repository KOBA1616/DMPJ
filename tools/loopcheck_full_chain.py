"""koba の一連の筋を台本で再現する（3ターン目スタート時の配置から）。
タイフーン（2ターン目）で墓地にタイフーンとサガ（イザナギは手札からサガループの捨てで墓地へ） → 3ターン目に水闇3マナでサガ → サガループの「引いて捨てる」で
ドラゲリオンを手札へ・イワシン／シャコガイルを墓地へ → 山札2枚でサガの効果でイザナギを墓地から出す →
イザナギの効果でコダマダンス・チャージャーを踏み倒し（闇マナ+1）→ ドラゲリオン → メテオバーン → 山札を引ききって勝つ。
実行: PYTHONPATH=. python tools/loopcheck_full_chain.py [ドラゲリオンの山札位置 ...]"""
import sys

from dmsim import scenario as sc
from dmsim.defs import load_rules
from dmsim.engine_view import card_zone_of, defn_of, result_of, zone_of  # noqa: E402

SAGA, SHAKO, DRAG, IWA = "dm22ex2-021", "dmrp03-s03", "dm22ex1-007", "dmrp03-036"
IZA, KODAMA, ET = "dm22ex1-025", "dmex10-020", "dm26ex2-071"


def policy(eng, d):
    keys = [o["key"] for o in d["options"]]
    deck = len(zone_of(eng, "deck", 0))
    dn = lambda o: defn_of(eng, o["cid"])
    if d["kind"] == "charge":
        return [keys.index("pass")]
    if d["kind"] == "yes_no":
        return [keys.index("yes")]
    if d["kind"] == "pay_mana":
        return [min(range(len(keys)), key=lambda j: keys[j].count("dm01-027"))]
    if d["kind"] == "block":
        return [keys.index("no_block")]
    if d["kind"] == "choose_evo_source":
        return [j for j, o in enumerate(d["options"]) if dn(o) != SHAKO]
    if d["kind"] == "order_pending":
        j = next((j for j, o in enumerate(d["options"]) if IWA in o["key"]), None)
        return [j if j is not None else 0]
    if d["kind"] == "attack":
        j = next((j for j, o in enumerate(d["options"]) if o["key"] != "pass"), None)
        return [j if j is not None else keys.index("pass")]
    if d["kind"] == "main":
        for want in (DRAG, KODAMA, SAGA):
            j = next((j for j, o in enumerate(d["options"]) if o["key"] == "play:" + want), None)
            if j is not None and (want != DRAG or deck <= 1) and want != KODAMA:
                return [j]
        return [keys.index("pass")]
    if d["kind"] == "choose_cards":
        z = card_zone_of(eng, d["options"][0]["cid"])
        pick = lambda *want: next((j for w in want for j, o in enumerate(d["options"]) if dn(o) == w), None)
        if z == "bz":                       # メテオバーンの下の1枚: イワシンを墓地へ
            j = pick(IWA)
            return [j if j is not None else 0]
        if z == "graveyard":
            if any(dn(o) == IZA for o in d["options"]):          # サガの蘇生: 山札2枚以下でイザナギ、それまでサガ
                j = pick(IZA) if deck <= 2 else pick(SAGA)
            else:                                                  # メテオバーン: シャコガイルを出す
                j = pick(SHAKO)
            return [j if j is not None else 0]
        if z == "deck":                                            # イザナギで山札上から5枚: コダマダンスを取る
            j = pick(KODAMA)
            return [j if j is not None else 0]
        # 手札を捨てる: イワシン・シャコガイル・ダミーを先に。ドラゲリオン・コダマ・サガ・イザナギは残す
        j = pick(IWA, SHAKO, IZA, "T001")
        if j is None:
            j = next((j for j, o in enumerate(d["options"]) if dn(o) not in (DRAG, KODAMA, SAGA)), 0)
        return [j]
    return list(range(d["min"]))


def trial(rules, pos, deck_left=18):
    spec = {"p0": {"hand": [SAGA, KODAMA, IZA, "T001"], "mana": ["dm01-080", "dm01-080", "dm01-027"],
                   "graveyard": [ET, SAGA], "deck": [DRAG, IWA, SHAKO]},
            "p1": {}, "deck_size": 40, "deck_left": [deck_left, 40], "seed": 1}
    e = sc.build(rules, spec)
    deck = zone_of(e, "deck", 0)
    cs = [c for c in deck if defn_of(e, c) in (DRAG, IWA, SHAKO)]
    for c in cs:
        deck.remove(c)
    for c, p in zip(cs, pos):
        deck.insert(p, c)
    for _ in range(3000):
        d = e.advance()
        if d is None or result_of(e):
            break
        e.answer(policy(e, d))
    return e


if __name__ == "__main__":
    rules = load_rules()
    for pos in ([tuple(int(x) for x in a.split(",")) for a in sys.argv[1:]] or [(0, 1, 2), (3, 5, 7), (6, 9, 12)]):
        e = trial(rules, pos)
        gy = [defn_of(e, c) for c in zone_of(e, "graveyard", 0)]
        print(pos, result_of(e), "deck", len(zone_of(e, "deck", 0)), "gy", len(gy), "bz", [defn_of(e, c) for c in zone_of(e, "bz", 0)])
