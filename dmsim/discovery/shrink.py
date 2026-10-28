"""最小初期盤面の縮約（介入による特定）。

回るとわかっている盤面（シナリオ spec）から、カードを1枚ずつ外し、ループが再生検証できる限り縮める。
さらに残ったカード1枚ごとに、(1) 別のゾーンに置いても成立するか（手札か墓地でよい、など）、
(2) 同じ種別の別カードに入れ替えても成立するか（名前固有か、クリーチャー一般でよいか）を確かめる。
統計ではなくエンジン上の再生で確かめるので、結果は決定的に再現できる。

  python -m dmsim.discovery.shrink --setup tests/saga_loop_first_setup.yaml
"""
from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

from .. import loop_first as lf
from .. import scenario as sc
from .loopspec import LoopSpec, Pred

ZONES = ("hand", "graveyard", "mana", "bz")
Test = "Callable[[dict], bool]"


def entries(spec: dict) -> list[tuple[str, str, int, str]]:
    """(プレイヤー鍵 'p0'/'p1', ゾーン, 位置, カードID) の一覧。"""
    out = []
    for pk in ("p0", "p1"):
        for z, ids in (spec.get(pk) or {}).items():
            out += [(pk, z, i, n) for i, n in enumerate(ids)]
    return out


def without(spec: dict, pk: str, zone: str, i: int) -> dict:
    s = copy.deepcopy(spec)
    del s[pk][zone][i]
    if not s[pk][zone]:
        del s[pk][zone]
    return s


def replaced(spec: dict, pk: str, zone: str, i: int, name: str) -> dict:
    s = copy.deepcopy(spec)
    s[pk][zone][i] = name
    return s


def moved(spec: dict, pk: str, zone: str, i: int, to: str) -> dict:
    s = copy.deepcopy(spec)
    name = s[pk][zone].pop(i)
    if not s[pk][zone]:
        del s[pk][zone]
    s[pk].setdefault(to, []).append(name)
    return s


def loop_test(rules, me: int = 0, budget: int = 1500, delta: dict | None = None, discover=lf.discover_loops):
    """spec から局面を作り、1ターンの探索で、再生検証できるループ（delta が指定なら一致するもの）が見つかるか。"""
    cache: dict[str, bool] = {}

    def test(spec: dict) -> bool:
        key = json.dumps(spec, sort_keys=True, ensure_ascii=False)
        if key not in cache:
            try:
                found = discover(sc.build(rules, spec), me, budget)
            except (KeyError, StopIteration):
                found = []     # 外した結果、盤面を作れない配置は「成立しない」
            cache[key] = any(f.verified and (delta is None or f.cert.delta == delta) for f in found)
        return cache[key]

    test.cache = cache
    return test


@dataclass
class Shrunk:
    spec: dict
    removed: list[tuple[str, str, str]] = field(default_factory=list)   # (プレイヤー鍵, ゾーン, カードID)
    tests: int = 0


ORDER = ("hand", "bz", "mana", "shield", "graveyard")


def shrink(spec: dict, test, protect: tuple[str, ...] = (), order: tuple[str, ...] = ORDER) -> Shrunk:
    """1つ外してもループが成立する限り外し続ける。どの1枚を外しても成立しなくなった（1-極小）盤面を返す。
    protect のゾーン（'hand' など。例: 手札の filler）は外さない。

    1-極小は外す順で変わる。order の先頭のゾーンから外す（既定は手札から）。墓地を先に外すと、
    手札の別のカードが代わりに墓地へ送って条件を作る盤面が残り、入口に不要なカードが紛れ込む。"""
    assert test(spec), "元の盤面でループが成立しない"
    cur = copy.deepcopy(spec)
    removed = []
    changed = True
    while changed:
        changed = False
        rank = {z: k for k, z in enumerate(order)}
        for pk, z, i, n in sorted(reversed(entries(cur)), key=lambda e: rank.get(e[1], len(rank))):   # 同じゾーンは後ろから外す
            if z in protect:
                continue
            cand = without(cur, pk, z, i)
            if test(cand):
                cur, changed = cand, True
                removed.append((pk, z, n))
    return Shrunk(cur, removed, len(test.cache))


@dataclass
class Robust:
    spec: dict                         # どの filler でも成立する最小の盤面
    per_filler: dict[str, dict]        # filler ごとの縮約結果
    holds_for_all: bool


def robust_shrink(spec: dict, test, fillers: list[str]) -> Robust:
    """山札の残りを埋める filler の違いに左右されない最小盤面を求める。

    山札の中身はループの「自由な部分」だが、filler が最小盤面の条件を偶然満たすことがある
    （例: filler がクリーチャーなら、引いて捨てるだけで「墓地のクリーチャー」が増える）。
    filler ごとに縮約し、その結果のうち、すべての filler で成立する最小のものを採る。
    どれもすべての filler では成立しなければ holds_for_all を偽にして、最小のものを返す。"""
    per = {}
    for f in fillers:
        s = {**spec, "filler": f}
        if test(s):
            per[f] = shrink(s, test).spec
    if not per:
        raise AssertionError("どの filler でも元の盤面でループが成立しない")
    ok = [c for c in per.values() if all(test({**c, "filler": f}) for f in fillers)]
    pool = ok or list(per.values())
    best = min(pool, key=lambda c: (len(entries(c)), json.dumps(c, sort_keys=True, ensure_ascii=False)))
    return Robust({k: v for k, v in best.items()}, per, bool(ok))


def win_test(rules, me: int = 0, budget: int = 1500, seek_budget: int = 1500, delta: dict | None = None):
    """spec から、ループを使って（delta が指定なら一致するループで）勝ち筋が見つかるか。出口の判定。"""
    cache: dict[str, bool] = {}

    def test(spec: dict) -> bool:
        key = json.dumps(spec, sort_keys=True, ensure_ascii=False)
        if key not in cache:
            try:
                found = [f for f in lf.discover_loops(sc.build(rules, spec), me, budget)
                         if f.verified and (delta is None or f.cert.delta == delta)]
                cache[key] = any(lf.seek_wins(f, me, seek_budget).wins for f in found)
            except (KeyError, StopIteration):
                cache[key] = False
        return cache[key]

    test.cache = cache
    return test


@dataclass
class EntranceExit:
    entrance: dict                     # ループが回る最小の盤面（M）
    exit: dict                         # M を保ったまま勝てる最小の盤面
    extra: list[tuple[str, str, str]]  # 出口に追加で要るカード (プレイヤー鍵, ゾーン, カードID)
    wins: bool


def split_entrance_exit(spec: dict, enter, win, fillers: list[str] | None = None,
                        order: tuple[str, ...] = ORDER) -> EntranceExit:
    """入口（ループ成立）と出口（勝利）を別々に縮約し、出口に追加で要るカードを求める。
    入口は enter（ループが検出できるか）だけで縮約する。出口は入口のカードを外さずに、win（勝てるか）で縮約する。"""
    m = (robust_shrink(spec, enter, fillers).spec if fillers else shrink(spec, enter, order=order).spec)
    have = [(pk, z, n) for pk, z, _, n in entries(m)]
    if not win(spec):
        return EntranceExit(m, spec, [], False)
    cur = copy.deepcopy(spec)
    rank = {z: k for k, z in enumerate(order)}
    keep = list(have)
    protected = set()
    for pk, z, i, n in sorted(reversed(entries(cur)), key=lambda e: rank.get(e[1], len(rank))):
        if (pk, z, n) in keep:
            keep.remove((pk, z, n))
            protected.add((pk, z, n))
    changed = True
    while changed:
        changed = False
        budget = list(have)
        for pk, z, i, n in sorted(reversed(entries(cur)), key=lambda e: rank.get(e[1], len(rank))):
            if (pk, z, n) in budget:
                budget.remove((pk, z, n))
                continue
            cand = without(cur, pk, z, i)
            if win(cand):
                cur, changed = cand, True
                break
    left = list(have)
    extra = []
    for pk, z, i, n in entries(cur):
        if (pk, z, n) in left:
            left.remove((pk, z, n))
        else:
            extra.append((pk, z, n))
    return EntranceExit(m, cur, extra, True)


def zone_alternatives(spec: dict, test, zones=ZONES) -> dict[tuple[str, str, int], list[str]]:
    """残ったカード1枚ごとに、別のゾーンへ動かしても成立するゾーン（自分のゾーンを含む）。"""
    out = {}
    for pk, z, i, n in entries(spec):
        ok = [z]
        for to in zones:
            if to != z and test(moved(spec, pk, z, i, to)):
                ok.append(to)
        out[(pk, z, i)] = ok
    return out


def class_substitutes(spec: dict, test, pool: list[str]) -> dict[tuple[str, str, int], list[str]]:
    """残ったカード1枚ごとに、pool の中で入れ替えても成立するカード。"""
    out = {}
    for pk, z, i, n in entries(spec):
        out[(pk, z, i)] = [c for c in pool if c != n and test(replaced(spec, pk, z, i, c))]
    return out


def to_loopspec(rules, name: str, shrunk: Shrunk, delta: dict, alts: dict | None = None,
                subs: dict | None = None, source: dict | None = None, me: int = 0) -> LoopSpec:
    """縮約した盤面を述語（最小盤面 M）にする。同じ条件の述語は個数にまとめる。
    subs が全て同じ種別で、pool の全員が入れ替え可能なカードは、名前でなく種別で書く。"""
    preds: dict[tuple, int] = {}
    for pk, z, i, n in entries(shrunk.spec):
        owner = int(pk[1])
        zs = tuple(sorted((alts or {}).get((pk, z, i), [z])))
        d = rules.cards[n]
        generic = bool(subs and subs.get((pk, z, i)) and
                       all(rules.cards[c].types == d.types for c in subs[(pk, z, i)]) and
                       len(subs[(pk, z, i)]) >= 2)
        match = json.dumps({"types": sorted(d.types)} if generic else {"name": n}, sort_keys=True)
        preds[(owner, match, zs)] = preds.get((owner, match, zs), 0) + 1
    minimal = [Pred(owner, json.loads(match), cnt, ">=", zone=zs[0] if len(zs) == 1 else None,
                    zones=() if len(zs) == 1 else zs)
               for (owner, match, zs), cnt in sorted(preds.items())]
    return LoopSpec(name=name, kind="deterministic", minimal=minimal, delta=delta, source=source or {})


def main(argv=None):
    import yaml

    from .. import load_rules
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", required=True)
    ap.add_argument("--budget", type=int, default=1500)
    ap.add_argument("--pool", default="", help="入れ替え候補のカードID（カンマ区切り）")
    ap.add_argument("--zones", action="store_true", help="ゾーンの代替も調べる")
    a = ap.parse_args(argv)
    rules = load_rules()
    spec = yaml.safe_load(Path(a.setup).read_text(encoding="utf-8"))
    found = lf.discover_loops(sc.build(rules, spec), 0, a.budget)
    delta = next(f.cert.delta for f in found if f.verified)
    test = loop_test(rules, 0, a.budget, delta)
    sh = shrink(spec, test, protect=())
    print("残った盤面:", json.dumps({k: v for k, v in sh.spec.items() if k in ("p0", "p1")}, ensure_ascii=False))
    print("外したカード:", [(pk, z, rules.cards[n].name) for pk, z, n in sh.removed], "実行回数:", sh.tests)
    alts = zone_alternatives(sh.spec, test) if a.zones else None
    subs = class_substitutes(sh.spec, test, a.pool.split(",")) if a.pool else None
    ls = to_loopspec(rules, "loop", sh, delta, alts, subs)
    print(ls.to_json())


if __name__ == "__main__":
    main()
