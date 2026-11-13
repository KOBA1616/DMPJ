"""物差しの陽性対照（校正）（S4、docs/combo-ruler-design.md §6 タスク8・§12）。

既知のループ型コンボ（入口局面 data/loops/entry/）を ruler.judge で測ると段2に高い割合で届き、
中核の札だけを差し替えたランダムな組は届かないことを確かめる。旧い陽性対照（validity.judge、combo_screen --control の点）とは別の判定。

入口局面のばらつき（vary）: 入口 M に要る札（LoopSpec.minimal を満たす最小の札）と場・墓地・マナはそのまま。
手札の残り（M に要らない札）と盾は、山札の残りと混ぜてシードで配り直す。山札の並びもシードで変わる。相手の山札の枚数もシードで ±OPP_SPREAD 変える。

ランダムな対照組（make_randoms）: ループの部品（入口 M が名前で要求する札。loop_parts）を1種類選び、その全コピー（デッキと局面の両方）を
カードプールの別の札1種類に置き換える。置き換え先は同じ種別（クリーチャー／呪文）・コスト差 1 以内・文明を1つ以上共有・進化でない・既知コンボの中核でない札。
マナ・盾に置かれただけの中核（コダマ・フィオナ等、入口へ届くための札）は入口局面では働かないので差し替えない（差し替えても結果が変わらず対照にならない。実測で確認）。
1種類だけ差し替えるのは、全部差し替えると自明に 0 になり物差しの区別の力を確かめられないため（1部品欠けた組でもループ勝ちを数えるなら、物差しが緩い）。

合否（judge_control）: 既知コンボごとの段2到達率 >= KNOWN_MIN、ランダム組の段2到達率の中央値 <= RANDOM_MAX。
自己点検（張り付き検知に相当）: 既知・ランダムの全行が同じ値／ランダム組の最大値が既知コンボの最小値以上（区別がない）／
入口局面のばらつきが効いていない（既知コンボの開始局面がシード間ですべて同じ）／対局の失敗が混ざる、を理由付きで不合格にする。
"""
from __future__ import annotations

import hashlib
import json
import random
import statistics
from collections import Counter
from dataclasses import replace
from pathlib import Path

import yaml

from ..base.store import REPO
from . import loop_entry as le
from .ruler import judge

KNOWN = ("saga", "akashic")          # ループ型の陽性対照（騎士+DMC はリソース型、ドリル+ジョバンニは検証専用）
HOLDOUT = ()                         # 参考値として別欄に出すもの（入口局面ができたら足す。調整には使わない）
KNOWN_MIN = 0.8
RANDOM_MAX = 0.05
OPP_SPREAD = 3
STAMP = REPO / "data" / "eval" / "ruler_control_stamp.json"
COMBOS = Path("data/known_combos/combos.yaml")


def core_ids(path: Path = COMBOS) -> set[str]:
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    out = set()
    for c in d.get("combos", []):
        for p in c.get("parts", []):
            if p.get("role") == "core" and p.get("id"):
                out.add(p["id"])
    return out


def _pinned_hand(rules, ls, hand: list[str]) -> list[str]:
    """手札のうち入口 M が要求する札（述語ごとに必要枚数まで、先頭から）。"""
    left = list(hand)
    keep = []
    for p in ls.minimal:
        if p.owner != 0 or (p.zone or "") != "hand":
            continue
        k = 0
        for i in list(left):
            if k >= p.n:
                break
            d = rules.cards[i]
            m = p.match
            if "name" in m and m["name"] not in (i, d.id):
                continue
            if "types" in m and not set(m["types"]) & set(d.types):
                continue
            if "civs" in m and not set(m["civs"]) & set(d.civs):
                continue
            left.remove(i)
            keep.append(i)
            k += 1
    return keep


def vary(rules, ls, seed: int):
    """入口局面の LoopSpec をシードで変えた写しを返す（中核と M の札は動かさない）。seed=0 は元のまま。"""
    if seed == 0:
        return ls
    rng = random.Random(seed * 7919 + 17)
    b = json.loads(json.dumps(ls.source["board"]))
    p0 = b["p0"]
    hand = p0.get("hand", [])
    keep = _pinned_hand(rules, ls, hand)
    free_hand = list((Counter(hand) - Counter(keep)).elements())
    shields = p0.get("shield", [])
    placed = Counter()
    for ids in p0.values():
        placed.update(ids)
    rest = list((Counter(_deck(ls)) - placed).elements())
    pool = free_hand + shields + rest
    rng.shuffle(pool)
    nh, ns = len(free_hand), len(shields)
    p0["hand"] = keep + pool[:nh]
    p0["shield"] = pool[nh:nh + ns]
    opp = b["opp_deck"] + rng.randint(-OPP_SPREAD, OPP_SPREAD)
    b["opp_deck"] = max(1, opp)
    return replace(ls, source=dict(ls.source, board=b))


def start_key(eng) -> str:
    """開始局面の指紋（自分の各ゾーンの札と山札の並び、相手の山札枚数）。ばらつきの確認用。"""
    s = eng.s
    parts = []
    for z in sorted(s.zones):
        parts.append(z + ":" + ",".join(s.cards[c].defn for c in s.zones[z][0]))
    parts.append("opp_deck:%d" % len(s.zones["deck"][1]))
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]


def candidates(rules, card_id: str, banned: set[str]) -> list[str]:
    d = rules.cards[card_id]
    out = []
    for i, c in rules.cards.items():
        if i in banned or i == card_id or i.startswith("T"):
            continue
        if bool(c.is_creature) != bool(d.is_creature) or bool(c.is_spell) != bool(d.is_spell):
            continue
        if c.evolve_from or abs((c.cost or 0) - (d.cost or 0)) > 1:
            continue
        if not set(c.civs) & set(d.civs):
            continue
        out.append(i)
    return sorted(out)


def swap(ls, deck: list[str], old: str, new: str):
    b = json.loads(json.dumps(ls.source["board"]))
    for z, ids in b["p0"].items():
        b["p0"][z] = [new if i == old else i for i in ids]
    d2 = [new if i == old else i for i in deck]
    mini = [replace(p, match={**p.match, "name": new}) if p.match.get("name") == old else p for p in ls.minimal]
    ls2 = replace(ls, source=dict(ls.source, board=b, deck_list=d2), minimal=mini)
    return ls2, d2


def loop_parts(ls) -> list[str]:
    """ループの部品 = 入口 M が名前で要求する札。マナ・盾・墓地に置かれただけの中核（入口へ届くための札）は差し替えない。"""
    return sorted({p.match["name"] for p in ls.minimal if p.owner == 0 and "name" in p.match})


def make_randoms(rules, name: str, per_core: int, seed: int = 0) -> list[dict]:
    """中核1種類を差し替えたランダム組。{"combo", "old", "new", "spec", "deck"}。"""
    ls = le.load(name)
    deck = le.deck_of(ls)
    cores = core_ids()
    on_board = loop_parts(ls) or sorted({i for ids in ls.source["board"]["p0"].values() for i in ids if i in cores})
    rng = random.Random(f"{name}:{seed}")
    out = []
    for old in on_board:
        cand = candidates(rules, old, cores)
        for new in rng.sample(cand, min(per_core, len(cand))):
            ls2, d2 = swap(ls, deck, old, new)
            out.append({"combo": name, "old": old, "new": new, "spec": ls2, "deck": d2})
    return out


def _deck(ls) -> list[str]:
    return ls.source.get("deck_list") or le.deck_of(ls)


def run_one(rules, ls, seed: int, max_turn: int = 2, budget: int | None = None) -> dict:
    from dmsim.engine import scenario
    from dmsim.search.game import play_game
    from .lockcheck import lock_probe
    deck = _deck(ls)
    v = vary(rules, ls, seed)
    spec = _entry_spec(v, deck, seed)
    e = scenario.build(rules, spec, first_player=0)
    key = start_key(e)
    bud = budget if budget is not None else ls.source.get("budget", 200)
    res, eng = play_game(rules, deck, [], seed, first_player=0, max_turn=max_turn, budget=bud, start=e, lock_judge=lock_probe)
    vd = judge(res, eng)
    return {"seed": seed, "start": key, "stage1": vd.stage1.ok, "stage2": vd.stage2.ok, "via": vd.stage2.via,
            "win_turn": vd.stage2.win_turn, "error": res.error, "reason": vd.reason}


def _entry_spec(ls, deck: list[str], seed: int) -> dict:
    b = ls.source["board"]
    left = Counter(deck)
    for ids in b["p0"].values():
        for i in ids:
            left[i] -= 1
            if left[i] < 0:
                raise ValueError(f"{ls.name}: {i} がデッキの枚数を超える")
    p0 = dict(b["p0"], deck=sorted(left.elements()))
    return {"p0": p0, "p1": b["p1"], "deck_size": b["opp_deck_total"], "deck_exact": [True, False],
            "deck_left": [None, b["opp_deck"]], "seed": seed}


def rate(rows: list[dict]) -> float:
    return sum(r["stage2"] for r in rows) / len(rows) if rows else 0.0


def judge_control(known: dict[str, list[dict]], randoms: list[dict], known_min: float = KNOWN_MIN,
                  random_max: float = RANDOM_MAX) -> tuple[bool, str, dict]:
    """known: コンボ名→各シードの行。randoms: {"combo","old","new","rows"}。合否・理由・集計を返す。"""
    summ = {"known": {k: rate(v) for k, v in known.items()},
            "random": [{"combo": r["combo"], "old": r["old"], "new": r["new"], "rate": rate(r["rows"])} for r in randoms]}
    rr = [x["rate"] for x in summ["random"]]
    summ["random_median"] = statistics.median(rr) if rr else None
    summ["random_max"] = max(rr) if rr else None
    if not known:
        return False, "既知コンボの対照結果がない", summ
    if not rr:
        return False, "ランダム組の対照結果がない", summ
    errs = sum(1 for v in known.values() for r in v if r.get("error")) + sum(1 for r in randoms for x in r["rows"] if x.get("error"))
    summ["errors"] = errs
    kv = list(summ["known"].values())
    if len(set(kv + rr)) == 1:
        return False, f"測定が張り付いている: 既知もランダム組も全部 {kv[0]:.2f}（物差しか入口局面を疑う）", summ
    flat = [k for k, v in known.items() if len(v) > 1 and len({r["start"] for r in v}) == 1]
    if flat:
        return False, f"入口局面のばらつきが効いていない: {flat} の開始局面がシード間で全部同じ", summ
    if summ["random_max"] >= min(kv):
        top = max(summ["random"], key=lambda x: x["rate"])
        why = f"既知とランダム組の区別がない: ランダム組の最大 {summ['random_max']:.2f}（{top['combo']} の {top['old']}→{top['new']}）が既知の最小 {min(kv):.2f} 以上"
        if summ["random_median"] > random_max:
            return False, why, summ
        summ["warn"] = why
    bad = [k for k, v in summ["known"].items() if v < known_min]
    if bad:
        return False, f"既知コンボが基準 {known_min} に届かない: " + ", ".join(f"{k} {summ['known'][k]:.2f}" for k in bad), summ
    if summ["random_median"] > random_max:
        return False, f"ランダム組の中央値 {summ['random_median']:.2f} が基準 {random_max} を超える（物差しが緩い）", summ
    if errs:
        return False, f"対局の失敗が {errs} 局ある", summ
    return True, "ok", summ


def write_stamp(passed: bool, reason: str, summ: dict, path: Path = STAMP, root: Path = REPO) -> dict:
    from .validity import fingerprint
    st = {"passed": passed, "reason": reason, "fingerprint": fingerprint(root), "summary": summ}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    return st


def status(path: Path = STAMP, root: Path = REPO) -> tuple[bool, str]:
    """物差しの陽性対照の印。測定器（dmsim/*.py）かカードデータが変わると失効する（validity.status と同じ扱い）。"""
    from .validity import fingerprint
    try:
        st = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return False, "物差しの陽性対照の印がない（tools/ruler_control.py を先に回す）"
    if st.get("fingerprint") != fingerprint(root):
        return False, "測定器かカードデータが変わり、印が古い（対照をやり直す）"
    if not st.get("passed"):
        return False, st.get("reason", "物差しの陽性対照に不合格")
    return True, "ok"
