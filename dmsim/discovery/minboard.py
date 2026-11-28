"""最小のループ盤面を縮約で自動的に求める（2026-11-28）。

回る盤面（scenario の spec）と起点の攻撃から、合成手（search/compose.find_loop）が回帰を見つける限りカードを外し、
ループが成立する最小の盤面 M を出力として得る。縮約そのものは eval/shrink.shrink（1-極小）を使う。

墓地は「必要な部品＋任意の n 枚」の枚数条件で表す。残った墓地の札を filler に入れ替えても成立するなら、
その札は名前が要らず枚数だけが要る（任意枠）。入れ替えると落ちる札が必要な部品。
入口はループの最小パーツだけ（フィニッシュは段2。ユーザー定義 2026-11-14）。

  mb = minimal_board(rules, spec, "attack:<ID>:player", name="x")
  mb.spec        # 縮約後の spec（任意枠の墓地は filler が入っている）
  mb.loopspec    # 最小盤面 M を述語で持つ LoopSpec
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field

from ..base.loopspec import LoopSpec, Pred
from ..engine import scenario as sc
from ..eval import shrink as S
from ..search import compose as C

LOOP_KINDS = ("finite", "infinite")


def board_spec(ls, seed: int = 1) -> dict:
    """入口局面（LoopSpec）から、縮約の対象になる盤面だけの spec を作る（山札・シールドは入れない。残りは filler で埋まる）。"""
    from ..eval import loop_entry as LE
    spec = LE.entry_spec(ls, seed)
    spec["p0"] = {z: list(spec["p0"].get(z) or []) for z in ("bz", "graveyard", "hand", "mana") if spec["p0"].get(z)}
    spec.pop("deck_exact", None)
    spec.pop("deck_left", None)
    return spec


def loop_on_board(rules, origin_key: str, *, me: int = 0, laps_max: int = 1, max_nodes: int = 800, tries: int = 2,
                  kinds: tuple[str, ...] = LOOP_KINDS):
    """spec → 起点の攻撃から合成手の回帰（ループ）が見つかるか、の判定関数（キャッシュ付き）。"""
    cache: dict[str, bool] = {}

    def test(spec: dict) -> bool:
        key = json.dumps(spec, sort_keys=True, ensure_ascii=False)
        if key not in cache:
            ok = False
            try:
                e = sc.build(rules, spec)
                while (d := e.advance()) is not None and d["kind"] != "attack":
                    if e.s.result or d["player"] != me:
                        break
                    ks = [o["key"] for o in d["options"]]
                    e.answer([ks.index("pass") if "pass" in ks else 0])
                if d is not None and d["kind"] == "attack" and origin_key in [o["key"] for o in d["options"]]:
                    ok = C.find_loop(e, origin_key, player=me, laps_max=laps_max, max_nodes=max_nodes,
                                     tries=tries)["kind"] in kinds
            except (KeyError, StopIteration, ValueError):
                ok = False    # 外した結果、盤面を作れない配置は「成立しない」
            cache[key] = ok
        return cache[key]

    test.cache = cache
    return test


def graveyard_condition(spec: dict, test, filler: str, pk: str = "p0") -> tuple[dict, Counter, int]:
    """墓地の札を1枚ずつ filler に入れ替えて成立するかを見る。成立する札は「任意枠」、しない札は「必要な部品」。
    戻り: (任意枠を filler にした spec, 必要な部品の名前→枚数, 任意枠の枚数)。"""
    cur = json.loads(json.dumps(spec))
    required: Counter = Counter()
    any_n = 0
    for i, name in enumerate(list((cur.get(pk) or {}).get("graveyard", []))):
        if name == filler:
            any_n += 1
            continue
        cand = S.replaced(cur, pk, "graveyard", i, filler)
        if test(cand):
            cur, any_n = cand, any_n + 1
        else:
            required[name] += 1
    return cur, required, any_n


@dataclass
class MinBoard:
    spec: dict                                   # 縮約後の盤面（任意枠は filler）
    loopspec: LoopSpec
    removed: list = field(default_factory=list)
    gy_required: Counter = field(default_factory=Counter)
    gy_any: int = 0
    tests: int = 0


def minimal_board(rules, spec: dict, origin_key: str, *, name: str = "loop", me: int = 0, test=None,
                  filler: str | None = None, order: tuple[str, ...] = S.ORDER, **kw) -> MinBoard:
    """spec から最小盤面を縮約して LoopSpec（最小盤面 M）にする。元の盤面でループが成立しなければ AssertionError。"""
    test = test or loop_on_board(rules, origin_key, me=me, **kw)
    filler = filler or spec.get("filler", "T001")
    sh = S.shrink(spec, test, order=order)
    pk = f"p{me}"
    gspec, req, any_n = graveyard_condition(sh.spec, test, filler, pk)
    preds: dict[tuple, int] = {}
    for p, z, _i, n in S.entries(gspec):
        if int(p[1]) != me or z == "graveyard":
            continue
        preds[(z, n)] = preds.get((z, n), 0) + 1
    minimal = [Pred(me, {"name": n}, c, ">=", zone=z) for (z, n), c in sorted(preds.items())]
    minimal += [Pred(me, {"name": n}, c, ">=", zone="graveyard") for n, c in sorted(req.items())]
    if any_n:   # 任意の n 枚: 墓地の札の総数が、必要な部品＋任意枠の枚数以上
        types = sorted({t for d in rules.cards.values() for t in d.types})
        minimal.append(Pred(me, {"types": types}, sum(req.values()) + any_n, ">=", zone="graveyard"))
    ls = LoopSpec(name=name, kind="deterministic", minimal=minimal, source={"origin": origin_key, "filler": filler})
    return MinBoard(gspec, ls, sh.removed, req, any_n, len(test.cache))
