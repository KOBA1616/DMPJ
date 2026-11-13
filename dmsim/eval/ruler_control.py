"""物差しの陽性対照（校正）（S4、docs/combo-ruler-design.md §6 タスク8・§12）。

既知のループ型コンボ（入口局面 data/loops/entry/）を ruler.judge で測ると段2に高い割合で届き、
中核の札だけを差し替えたランダムな組は届かないことを確かめる。旧い陽性対照（validity.judge、combo_screen --control の点）とは別の判定。

入口局面のばらつき（vary）: 入口 M に要る札（LoopSpec.minimal を満たす最小の札）と場・墓地・マナはそのまま。
手札の残り（M に要らない札）と盾は、山札の残りと混ぜてシードで配り直す。山札の並びもシードで変わる。相手の山札の枚数もシードで ±OPP_SPREAD 変える。

ランダムな対照組（make_randoms）: 中核の組（loop_entry.core_groups。「どれか1組でよい」代わりを含む、§14）を1つ選び、
その組に出てくる札（代わりの札も含む）の全コピー（デッキと局面の両方）を、札ごとにカードプールの別の札1種類に置き換える。置き換え先は同じ種別（クリーチャー／呪文）・コスト差 1 以内・文明を1つ以上共有・進化でない・既知コンボの中核でない札。
マナ・盾に置かれただけの中核（コダマ・フィオナ等、入口へ届くための札）は入口局面では働かないので差し替えない（差し替えても結果が変わらず対照にならない。実測で確認）。
1種類だけ差し替えるのは、全部差し替えると自明に 0 になり物差しの区別の力を確かめられないため（1部品欠けた組でもループ勝ちを数えるなら、物差しが緩い）。

合否（judge_control）: 既知コンボごとの段2到達率 >= KNOWN_MIN、ランダム組の段2到達率の中央値 <= RANDOM_MAX。
段2 >= EXPLAIN_MIN のランダム組は要説明（EXPLAIN に a〜d の説明を記録するまで保留。a/b は対照から外す、c/d は不合格）。
取り除き試験（removal_cases / judge_removal）: 中核の札1種類を全部抜いて段2が落ちない札を見つけ、定義と食い違えば理由を付けて知らせる。
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

KNOWN = ("saga", "akashic", "akashic_hd2")   # ループ型の陽性対照（騎士+DMC はリソース型、ドリル+ジョバンニは検証専用）。akashic_hd2 は既知の別版（§13）
HOLDOUT = ()                         # 参考値として別欄に出すもの（入口局面ができたら足す。調整には使わない）
KNOWN_MIN = 0.8
RANDOM_MAX = 0.05
OPP_SPREAD = 3
EXPLAIN_MIN = 0.25                   # ランダム組の段2がこれ以上なら「要説明」（説明が記録されるまで合格の印を保留）
REMOVAL_KEEP = 0.25                  # 取り除き試験: 抜いても段2がこれ以上なら「落ちない」
LABELS = {"a": "本物の別ループ", "b": "中核でない札だった", "c": "物差しの不具合", "d": "データやエンジンの誤り"}
STAMP = REPO / "data" / "eval" / "ruler_control_stamp.json"
EXPLAIN = Path("data/eval/ruler_control_explain.yaml")
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
    for i in ls.source.get("pin_hand", []):   # 取り除き試験で置いた代わりの札（vary で動かさない）
        if i in left:
            left.remove(i)
            keep.append(i)
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
    names = {rules.cards[b].name for b in banned if b in rules.cards} | {d.name}   # 再録（同名で別ID）も中核と同じ札として除く
    out = []
    for i, c in rules.cards.items():
        if i in banned or i == card_id or i.startswith("T") or c.name in names:
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
    """ループの部品 = 中核の組に出てくる札（代わりの札も含む。loop_entry.core_groups）。"""
    return le.core_ids(ls)


def swap_many(ls, deck: list[str], pairs: list[tuple[str, str]]):
    for old, new in pairs:
        ls, deck = swap(ls, deck, old, new)
    return ls, deck


def make_randoms(rules, name: str, per_core: int, seed: int = 0) -> list[dict]:
    """中核の組1つを、代わりの札も含めて組ごと差し替えたランダム組。{"combo", "group", "old", "new", "pairs", "spec", "deck"}。
    old / new は差し替えた札を「+」でつないだ文字列（代わりのない組なら1札）。"""
    ls = le.load(name)
    deck = le.deck_of(ls)
    cores = core_ids() | set(le.core_ids(ls))
    rng = random.Random(f"{name}:{seed}")
    out = []
    groups = sorted(le.core_groups(ls), key=lambda g: sorted({i for o in g["any"] for i in o})[0])
    for g in groups:
        olds = sorted({i for o in g["any"] for i in o})
        cands = {o: candidates(rules, o, cores) for o in olds}
        n = min([per_core] + [len(c) for c in cands.values()])
        picks = {o: rng.sample(cands[o], n) for o in olds}
        for k in range(n):
            pairs = [(o, picks[o][k]) for o in olds]
            ls2, d2 = swap_many(ls, deck, pairs)
            out.append({"combo": name, "group": g["role"], "old": "+".join(o for o, _ in pairs),
                        "new": "+".join(nw for _, nw in pairs), "pairs": pairs, "spec": ls2, "deck": d2})
    return out


def removal_cases(rules, name: str, seed: int = 0) -> list[dict]:
    """取り除き試験の組: 中核の札1種類の全コピーを、中核でない札1種類に置き換える（代わりの札は残す）。
    expected_drop は定義上「どの代わりを選んでも要る」札（抜くと段2が落ちるはず）。"""
    ls = le.load(name)
    deck = le.deck_of(ls)
    cores = core_ids() | set(le.core_ids(ls))
    req = set(le.required_ids(ls))
    rng = random.Random(f"removal:{name}:{seed}")
    out = []
    for old in le.core_ids(ls):
        cand = candidates(rules, old, cores)
        if not cand:
            continue
        new = rng.choice(cand)
        ls2, d2 = swap(ls, deck, old, new)
        if old not in req:
            ls2, d2 = _place_alternative(rules, ls, ls2, d2, old, new)
        out.append({"combo": name, "old": old, "new": new, "expected_drop": old in req, "spec": ls2, "deck": d2})
    return out


def _place_alternative(rules, ls, ls2, d2: list[str], old: str, new: str):
    """代わりのある札を抜いたとき、入口局面のその札の位置に、old を含まない代わりの組を置く。
    入口局面は「中核が揃った」局面なので、代わりがあるという定義を確かめるには代わりの組も揃えて置く必要がある
    （置かないと、山札から2ターン以内に引けるかどうかを測ってしまう。§17）。足りない分は手札の中核でない札と入れ替える。"""
    alt = next((o for g in le.core_groups(ls) if any(old in o for o in g["any"])
                for o in g["any"] if old not in o), None)
    if not alt:
        return ls2, d2
    b = json.loads(json.dumps(ls2.source["board"]))
    p0 = b["p0"]
    placed = Counter(i for z in ("hand", "bz") for i in p0.get(z, []))   # 盾・山札にあるだけでは使えない
    need = [i for i, k in alt.items() for _ in range(max(0, k - placed[i]))]
    deck = list(d2)
    cores = set(le.core_ids(ls))
    pins = []
    for i in need:
        if i not in deck:
            return ls2, d2                 # デッキに代わりの札が無い（置けない）
        z = next((z for z, ids in p0.items() if new in ids), None)
        if z is not None:
            p0[z][p0[z].index(new)] = i    # 抜いた札の位置へ
        else:
            hand = p0.setdefault("hand", [])
            j = next((j for j in range(len(hand) - 1, -1, -1) if hand[j] not in cores and hand[j] != new), None)
            if j is None:
                return ls2, d2
            hand[j] = i
        pins.append(i)
    ls3 = replace(ls2, source=dict(ls2.source, board=b, pin_hand=[i for i in pins if i in p0.get("hand", [])]))
    return ls3, deck


def judge_removal(cases: list[dict], keep: float = REMOVAL_KEEP) -> list[dict]:
    """取り除き試験の判定。cases は removal_cases に rows を足したもの。定義と食い違う札に理由を付ける（定義は書き換えない）。"""
    out = []
    for c in cases:
        r = rate(c["rows"])
        dropped = r < keep
        why = None
        if c["expected_drop"] and not dropped:
            why = f"定義では代わりのない中核だが、抜いても段2 {r:.2f}（中核でないか、定義にない代わりがある）"
        elif not c["expected_drop"] and dropped:
            why = f"定義では代わりがあるが、抜くと段2 {r:.2f} に落ちる（代わりの組が入口から届いていない）"
        out.append({"combo": c["combo"], "old": c["old"], "new": c["new"], "rate": r, "expected_drop": c["expected_drop"],
                    "dropped": dropped, "mismatch": why})
    return out


def load_explanations(path: Path = EXPLAIN) -> list[dict]:
    try:
        d = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return []
    return d.get("explanations", [])


def explanation_for(row: dict, expl: list[dict]) -> dict | None:
    """要説明の組（combo, old, new）に当たる説明。説明の old は差し替えた札の集合、new は省略（どの札へでも）か集合。"""
    old = set(row["old"].split("+"))
    new = set(row["new"].split("+"))
    for e in expl:
        if e.get("combo") != row["combo"] or set(e.get("old", [])) != old:
            continue
        if e.get("new") and set(e["new"]) != new:
            continue
        if e.get("label") not in LABELS:
            continue
        return e
    return None


def _deck(ls) -> list[str]:
    return ls.source.get("deck_list") or le.deck_of(ls)


def run_one(rules, ls, seed: int, max_turn: int = 2, budget: int | None = None, macros: bool = False) -> dict:
    from dmsim.engine import scenario
    from dmsim.search.game import play_game
    from .lockcheck import lock_probe
    deck = _deck(ls)
    v = vary(rules, ls, seed)
    spec = _entry_spec(v, deck, seed)
    e = scenario.build(rules, spec, first_player=0)
    key = start_key(e)
    bud = le.measure_budget(ls, budget)
    # 物差しは探索の力で測る: 登録簿の手（search.macro）は使わない（使うと登録簿が自分自身を検証する）
    from dmsim.search import macro
    was = macro._ENABLED
    macro.enable(macros)
    try:
        res, eng = play_game(rules, deck, [], seed, first_player=0, max_turn=max_turn, budget=bud, start=e, lock_judge=lock_probe)
    finally:
        macro._ENABLED = was
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
                  random_max: float = RANDOM_MAX, explanations: list[dict] | None = None,
                  explain_min: float = EXPLAIN_MIN) -> tuple[bool, str, dict]:
    """known: コンボ名→各シードの行。randoms: {"combo","old","new","rows"}。合否・理由・集計を返す。
    段2 >= explain_min のランダム組は「要説明」。説明（explanations、既定は EXPLAIN のファイル）が a/b なら対照から外して記録、
    c/d なら不合格、説明がなければ合格の印を保留（passed=False、reason は「保留」で始まる）。"""
    expl = load_explanations() if explanations is None else explanations
    allr = [{"combo": r["combo"], "old": r["old"], "new": r["new"], "rate": rate(r["rows"])} for r in randoms]
    summ = {"known": {k: rate(v) for k, v in known.items()}, "random": [], "explained": [], "pending": [], "bad": []}
    for x in allr:
        if x["rate"] < explain_min:
            summ["random"].append(x)
            continue
        e = explanation_for(x, expl)
        if e is None:
            summ["pending"].append(x)
            summ["random"].append(x)
        elif e["label"] in ("a", "b"):
            summ["explained"].append({**x, "label": e["label"], "note": e.get("note", "")})
        else:
            summ["bad"].append({**x, "label": e["label"], "note": e.get("note", "")})
            summ["random"].append(x)
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
    if summ["bad"]:
        return False, "要説明の組が物差しの不具合・データの誤りと判定済み: " + ", ".join(
            f"{x['combo']} {x['old']}→{x['new']}（{x['label']} {LABELS[x['label']]}）" for x in summ["bad"]), summ
    if summ["pending"]:
        return False, f"保留: 段2 {explain_min} 以上のランダム組 {len(summ['pending'])} 組に説明がない（{EXPLAIN} に記録する）: " + ", ".join(
            f"{x['combo']} {x['old']}→{x['new']} {x['rate']:.2f}" for x in summ["pending"]), summ
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
