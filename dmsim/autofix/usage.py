"""プレイログから「撃てるのに撃たれない札」を人の指定なしで見つける（準備札の一般化）。

各自分のターンの頭に「撃てそうな札」（手札の呪文・クリーチャーでコストが マナ+1(チャージ分) 以下）の種類を数え、
そのターンの探索の結果で実際に出した/唱えた種類を数える。使用率 = played / avail。
- unused    : 撃てる機会が min_avail 回以上あるのに使用率が max_rate 未満
- fair_gap  : ずるい探索の使用率より公平探索が gap 以上低い（隠れ情報のせいで撃たない札）
検出した札は評価の加点候補（Knobs.prep_bonus の対象 ids）として自動ループに渡す。エンジンは編集しない。
"""
from __future__ import annotations

from collections import Counter

from ..engine import Engine
from ..solitaire import TurnSearch, charge_only_policy, own_turn
from ..engine_view import active_of, defn_of, tapped_of


def castable_defs(eng: Engine, me: int) -> set[str]:
    """手札の呪文・クリーチャーで、コストが untapped マナ+1（チャージ分）以下の種類。コスト軽減は見ない近似。"""
    mana = sum(1 for c in eng.zlist("mana", me) if not tapped_of(eng, c)) + 1
    out = set()
    for c in eng.zlist("hand", me):
        ch = eng.chars(c)
        if ({"spell", "creature"} & set(ch["types"])) and ch["cost"] <= mana:
            out.add(defn_of(eng, c))
    return out


def played_defs(log: list, me: int) -> set[str]:
    """ログの main 選択 'play:ID[:面]' から出した/唱えた種類。"""
    out = set()
    for e in log:
        if e["p"] == me and e.get("kind") == "main":
            for k in e["keys"]:
                if k.startswith("play:"):
                    out.add(k.split(":")[1])
    return out


def collect_usage(rules, deck, opp_deck, seeds, fair: bool = False, max_turn: int = 3, budget: int = 100,
                  n_det: int = 2, value_fn=None) -> dict:
    """{"avail": Counter, "played": Counter, "games": n}。fair=True は公平探索、False はずるい探索。"""
    from ..search.fair import FairTurnSearch
    avail: Counter = Counter()
    played: Counter = Counter()
    me = 0
    for seed in seeds:
        eng = Engine.new_game(rules, [deck, opp_deck], seed, 0)
        while (d := eng.advance()) is not None:
            if active_of(eng) != me or d["player"] != me:
                eng.answer(charge_only_policy(eng, d))
                continue
            ot = own_turn(eng, me)
            if ot > max_turn:
                break
            av, pre = castable_defs(eng, me), len(eng.log)
            if fair:
                eng = FairTurnSearch(me, budget, n_det, seed * 7919 + ot, value_fn=value_fn).run(eng)
            else:
                eng, _ = TurnSearch(me, budget, value_fn=value_fn).run(eng)
            pl = played_defs(eng.log[pre:], me)
            avail.update(av)
            played.update(pl & av)
    return {"avail": avail, "played": played, "games": len(list(seeds))}


def _rate(u: dict, i: str) -> float:
    return u["played"][i] / u["avail"][i] if u["avail"][i] else 0.0


def unused_cards(fair: dict, cheat: dict | None = None, min_avail: int = 5, max_rate: float = 0.4, gap: float = 0.3) -> list[dict]:
    """加点候補。[{id, avail, fair_rate, cheat_rate, reason}]（unused / fair_gap）。使用率の低い順。"""
    out = []
    for i, n in fair["avail"].items():
        if n < min_avail:
            continue
        fr = _rate(fair, i)
        cr = _rate(cheat, i) if cheat and cheat["avail"][i] >= min_avail else None
        if fr < max_rate:
            out.append({"id": i, "avail": n, "fair_rate": round(fr, 3), "cheat_rate": cr if cr is None else round(cr, 3), "reason": "unused"})
        elif cr is not None and cr - fr >= gap:
            out.append({"id": i, "avail": n, "fair_rate": round(fr, 3), "cheat_rate": round(cr, 3), "reason": "fair_gap"})
    return sorted(out, key=lambda x: x["fair_rate"])


def detect_prep_ids(fair: dict, cheat: dict | None = None, **kw) -> tuple[str, ...]:
    return tuple(x["id"] for x in unused_cards(fair, cheat, **kw))


def auto_prep_ids(rules, deck, opp_deck, parts_spec=None, seeds=range(1, 13), max_turn: int = 3, budget: int = 100) -> tuple[str, ...]:
    """人が prep_ids を指定していないコンボ用: ずるい探索のログから使われない札を検出して返す（約10秒）。"""
    from ..search.leaf_parts import make_value_fn
    u = collect_usage(rules, deck, opp_deck, list(seeds), False, max_turn, budget,
                      value_fn=make_value_fn(parts_spec) if parts_spec is not None else None)
    return detect_prep_ids(u)
