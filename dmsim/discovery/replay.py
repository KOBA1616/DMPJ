"""見つけた勝ちの手順（決定ごとの選択）を再生して、盤面が成り立つかを確かめる検査。縮約（shrink）の test に使う。

手順は「各決定の (種類, 選んだ選択肢の意味キー)」の列。再生中に決定の種類や選んだ意味キーが食い違えば不成立とする
（カードを外して選択肢が変わった時に、別の選択を黙って選んでしまわないため）。
縮約の結果は、この手順が通る盤面の下限（1-極小）で、別の手順なら成り立つ盤面を含めた最小ではない。"""
from __future__ import annotations

import json

from .. import scenario
from ..engine.core import IllegalAnswer
from ..engine_view import result_of


def steps_of(engine) -> list[tuple[str, tuple[str, ...], tuple[int, ...]]]:
    """Engine のログから (決定の種類, 選んだキー, 選んだ添字) の列を作る。"""
    out = []
    for x in engine.log:
        out.append((x["kind"], tuple(x["keys"]), tuple(x["choice"])))   # ログの keys は選んだ選択肢の意味キー
    return out


def replay_test(rules, steps, prepare=None, me: int = 0, build=None):
    """spec -> 手順を再生して me が勝つか。prepare(engine) は局面を作った直後の細工（山札の並びの固定など）。"""
    cache: dict[str, bool] = {}

    def test(spec: dict) -> bool:
        k = json.dumps(spec, sort_keys=True, ensure_ascii=False)
        if k in cache:
            return cache[k]
        ok = False
        try:
            e = (build or scenario.build)(rules, spec)
            if prepare:
                prepare(e)
            for kind, keys, idx in steps:
                d = e.advance()
                if d is None or result_of(e) is not None:
                    break
                if d["kind"] != kind:
                    break
                ks = [o["key"] for o in d["options"]]
                pick, used = [], set()
                for j, key in zip(idx, keys):   # 元の添字が同じキーならそれを、無ければ同じキーの最初の選択肢を選ぶ（カードを外して添字がずれても同じ意味の選択をする）
                    cand = j if j < len(ks) and ks[j] == key and j not in used else next((i for i, k2 in enumerate(ks) if k2 == key and i not in used), None)
                    if cand is None:
                        break
                    pick.append(cand)
                    used.add(cand)
                if len(pick) != len(keys):
                    break
                idx = tuple(pick)
                e.answer(list(idx))
            else:
                e.advance()
            ok = result_of(e) is not None and result_of(e)["winner"] == me
        except (IllegalAnswer, KeyError, StopIteration, IndexError, ValueError):
            ok = False
        cache[k] = ok
        return ok

    test.cache = cache
    return test
