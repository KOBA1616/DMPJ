"""コンボ発見 v3・サイクル列挙プローブ: 束の相互作用グラフから有向サイクルを
自動列挙する方式の実現可能性検証（本実装ではない）。

背景: 手書きの構造署名2種（structsig）で新規エンジン11件が見つかったが、全て
既知の骨格の一般化だった。署名を手で増やす方式は自動化も新骨格の発見も
期待しにくい。そこで署名を「入力」ではなく「発見されるサイクルの形」とし、
束同士の相互作用グラフ（A の効果が B の前提を満たす時に A→B の辺）から
有向サイクルを列挙してエンジン候補とする方式を検証する。

設計（プローブとしての割り切りを明示する）:
- 束は hunt 系が使う loop_cond.bundles（条件つき移動・once・when つき）。
  辺の判定は zone_graph.feeds を再利用するが、遅延誘発の移動（delayed）は
  ターン内に連鎖しないため、辺の判定からは除外する（非遅延の移動のみで feeds）。
- 列挙対象の前提種は move / cast / draw とする。attack / battle_win 前提は
  feeds の TICKS 規則（ヒューリスティクス）が最も弱く、アンタップを含む
  サイクルでしかターン内に回らないため、本プローブの主グラフからは外した
  （束の件数は記録する）。turn_start / turn_end / block / battle_start 前提は
  ターン内に繰り返せない（時計・相手依存）ため対象外。
- グラフは辺が数千万規模になるため、隣接を numpy 配列（offsets/targets/scores）
  で保持する（Python の list-of-list では OOM になった）。
- サイクル列挙: 長さ1・2は全辺で網羅。長さ3・4は「狙って満たせる」辺
  （feeds スコア2）の部分グラフで列挙し、探索上限に達したら打ち切りを明示する
  （blind な辺＝山札の上から偶然当たる受け渡しを含むサイクルは「運任せ」で、
  zone_graph でも格下に扱われる）。
- 刈り込み: (a) once_per_turn の束を含むサイクルを除外（グラフ構築時に束ごと除外）
  (b) 参加カードのゾーン収支の回帰（近似: flow_balance）
  (c) 資源の正味増（自ゾーンの hand/graveyard/mana/bz/shield のいずれかが増える、
      または相手ゾーンのいずれかが減る）
- 陽性対照は厳密サイクルだけでなく「前提閉集合」（組の全束の前提が組の中で
  満たされる集合）でも確認する。傍受（XENARCH 型）や積み荷（ウォカンナ型）は
  サイクルへ戻る辺を持たないため、厳密サイクルでは原理的に拾えないことの
  切り分けが目的。

使い方:
  PYTHONPATH=. python tools/combo_hunt3_cycleprobe.py build
  PYTHONPATH=. python tools/combo_hunt3_cycleprobe.py cycles [--time-cap 600]
  PYTHONPATH=. python tools/combo_hunt3_cycleprobe.py controls
  PYTHONPATH=. python tools/combo_hunt3_cycleprobe.py spotcheck [--n 10] [--timeout 240]
出力は ~/workspace/combo3/cycleprobe/ に置く（再開・再利用のため）。
"""
from __future__ import annotations

import argparse
import copy
import json
import pickle
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.discovery import loop_cond as C  # noqa: E402
from dmsim.engine import zone_graph as Z  # noqa: E402

OUT = Path.home() / "workspace" / "combo3" / "cycleprobe"
GRAPH = OUT / "graph.pkl"
CYCLES = OUT / "cycles.jsonl"

SAGA = "dm22ex2-021"
XENARCH = "dm22rp2x-004"

ENUM_KINDS = ("move", "cast", "draw")
FLOW_ZONES = ("hand", "graveyard", "mana", "bz")
GAIN_ZONES = ("hand", "graveyard", "mana", "bz", "shield")


# ---------------------------------------------------------------- 束の要約

def _subj_json(s):
    return json.dumps(s, ensure_ascii=False, sort_keys=True) if isinstance(s, dict) else s


def bundle_meta(b) -> dict:
    p = b.prem
    return {"card": b.card, "name": b.name, "origin": b.origin, "cost": b.cost,
            "once": bool(getattr(b, "once", False)), "rearm": bool(b.rearm),
            "prem": ({"kind": p.kind, "frm": p.frm, "to": p.to, "subject": _subj_json(p.subject),
                      "player": p.player, "zone": p.zone} if p else None),
            "when": getattr(b, "when", {}) or {},
            "moves": [{"src": m.src, "dst": m.dst, "ref_self": bool(m.ref_self),
                       "draw": bool(m.draw), "owner": m.owner, "flt": m.flt or {},
                       "delayed": bool(m.delayed), "many": bool(m.many)} for m in b.moves]}


def _filtered(b):
    """遅延移動を除いた束（feeds 判定用）。遅延が無ければそのまま返す。"""
    if any(m.delayed for m in b.moves):
        c = copy.copy(b)
        c.moves = [m for m in b.moves if not m.delayed]
        return c
    return b


# ---------------------------------------------------------------- グラフ

class Graph:
    """隣接を numpy 配列で持つ有向グラフ（offsets/targets/scores）。"""

    def __init__(self, meta, keep, offsets, targets, scores, stats):
        self.meta = meta
        self.keep = keep
        self.offsets = offsets      # len = len(meta)+1、keep 外の束は空行
        self.targets = targets
        self.scores = scores
        self.stats = stats

    def row(self, i):
        lo, hi = self.offsets[i], self.offsets[i + 1]
        return self.targets[lo:hi], self.scores[lo:hi]

    def has_edge(self, i, j) -> bool:
        t, _ = self.row(i)
        k = np.searchsorted(t, j)
        return k < len(t) and t[k] == j

    def edge_score(self, i, j) -> int:
        t, s = self.row(i)
        k = np.searchsorted(t, j)
        return int(s[k]) if k < len(t) and t[k] == j else 0


def build_graph(kinds) -> Graph:
    t0 = time.time()
    rules = load_rules()
    print(f"rules loaded {time.time()-t0:.0f}s", flush=True)
    bs = C.bundles(rules)
    meta = [bundle_meta(b) for b in bs]
    print(f"bundles: {len(bs)}", flush=True)

    prem_kinds = Counter(m["prem"]["kind"] if m["prem"] else None for m in meta)
    dropped = Counter()
    for cd in rules.cards.values():
        for f in (cd.faces or [cd]):
            for ab in f.abilities:
                if ab.get("kind") in ("trigger", "declare") and Z._premise(ab) is None:
                    dropped[(ab.get("when") or {}).get("event")] += 1
    print("premise kinds:", dict(prem_kinds.most_common()), flush=True)
    print("dropped premise events:", dict(dropped.most_common()), flush=True)

    # (a) once 束と、列挙対象外の前提種の束はグラフから外す（件数は記録）
    keep, n_once, n_kind = [], 0, 0
    for i, m in enumerate(meta):
        if m["once"]:
            n_once += 1
        elif m["prem"] is None or m["prem"]["kind"] not in kinds:
            n_kind += 1
        else:
            keep.append(i)
    keep_set = set(keep)
    print(f"graph nodes: {len(keep)} (excluded: once={n_once}, premise-kind={n_kind})", flush=True)

    by_dst: dict[str, list[int]] = defaultdict(list)
    drawers, spells, filt = [], [], {}
    for i in keep:
        fb = _filtered(bs[i])
        filt[i] = fb
        for z in {m.dst for m in fb.moves if isinstance(m.dst, str)}:
            by_dst[z].append(i)
        if any(m.draw for m in fb.moves):
            drawers.append(i)
        if bs[i].origin == "spell":
            spells.append(i)

    # 辺を (source ごと) 集め、最後に CSR へ固める
    rows: dict[int, tuple[list[int], list[int]]] = {}
    edge_by_kind = Counter()
    t1 = time.time()
    for n, j in enumerate(keep):
        p = bs[j].prem
        if p.kind == "move":
            cand = by_dst.get(p.to, [])
        elif p.kind == "cast":
            cand = spells
        else:  # draw
            cand = drawers
        for i in cand:
            if i not in keep_set:
                continue
            v = Z.feeds(bs[i] if i == j else filt[i], bs[j], rules)
            if v:
                tlist, slist = rows.setdefault(i, ([], []))
                tlist.append(j)
                slist.append(v)
                edge_by_kind[p.kind] += 1
        if n % 2000 == 0:
            print(f"  targets {n}/{len(keep)} edges={sum(edge_by_kind.values())} "
                  f"{time.time()-t1:.0f}s", flush=True)
    offsets = np.zeros(len(bs) + 1, dtype=np.int64)
    t_parts, s_parts = [], []
    for i in range(len(bs)):
        if i in rows:
            tlist, slist = rows[i]
            order = np.argsort(tlist)
            t_parts.append(np.array([tlist[k] for k in order], dtype=np.int32))
            s_parts.append(np.array([slist[k] for k in order], dtype=np.uint8))
            offsets[i + 1] = offsets[i] + len(tlist)
        else:
            offsets[i + 1] = offsets[i]
    targets = np.concatenate(t_parts) if t_parts else np.zeros(0, dtype=np.int32)
    scores = np.concatenate(s_parts) if s_parts else np.zeros(0, dtype=np.uint8)
    n_edges = int(offsets[-1])
    print(f"edges: {n_edges} by target premise kind: {dict(edge_by_kind.most_common())}", flush=True)
    print(f"build total {time.time()-t0:.0f}s", flush=True)
    stats = {"bundles": len(bs), "nodes": len(keep), "edges": n_edges,
             "excluded_once": n_once, "excluded_premise_kind": n_kind,
             "premise_kinds": dict(prem_kinds), "dropped_events": dict(dropped),
             "edge_by_kind": dict(edge_by_kind), "kinds": list(kinds),
             "seconds": round(time.time() - t0, 1)}
    return Graph(meta, keep, offsets, targets, scores, stats)


# ---------------------------------------------------------------- 収支と増分（近似）

def cycle_deltas(meta, path):
    """サイクルの自/相手ゾーン収支（移動を1回ずつ数える近似。many や枚数は見ない）。"""
    own, opp = Counter(), Counter()
    for i in path:
        for m in meta[i]["moves"]:
            if m["delayed"] or not isinstance(m["src"], str) or not isinstance(m["dst"], str):
                continue
            d = own if m["owner"] != "opp" else opp
            d[m["src"]] -= 1
            d[m["dst"]] += 1
    return ({k: v for k, v in own.items() if v}, {k: v for k, v in opp.items() if v})


def flow_balance(rules, meta, path, own_delta=None) -> bool:
    """参加カードのゾーン収支が回帰するかの近似判定（v2）。

    v1 の教訓（陽性対照サガの自己ループを誤って落とした）:
    非 ref_self の移動は、フィルタが適合すれば束の持ち主自身のカードも動かしうる
    （サガの蘇生はサガ自身に適合する。structsig の自己適合と同じ意味論）。
    v1 は「他のカードにだけ」帰属させたため、単独カードのサイクルで流れが消えた。

    v2 の条件:
    - bz の同一性: カード C ごとに、C を bz から出しうる移動の数 <= C を bz へ
      入れうる移動の数。帰属は ref_self（本人）と、フィルタが C に適合する
      owner=you の移動（持ち主自身を含む全参加カード）。
    - 代替可能なゾーンの持続性: hand / mana / shield の自ゾーン収支（delta）が
      いずれも負でないこと（周回ごとに減る資源はエンジンとして持続しない。
      hunt3.engine_verdict の致命条件と同じ方向）。graveyard は増分そのものに
      なりうるため課さない。山札は燃料として減少を許す。
    - 移動元/先が "?" の移動（alias の解決漏れ）を含むサイクルは、収支を
      静的に検証できないため False とし、呼び出し側で別枠に数える。
    """
    if own_delta is None:
        own_delta, _ = cycle_deltas(meta, path)
    for m_all in (meta[i]["moves"] for i in path):
        for m in m_all:
            if m["src"] == "?" or m["dst"] == "?":
                return False
    for z in ("hand", "mana", "shield"):
        if own_delta.get(z, 0) < 0:
            return False
    cards = {meta[i]["card"] for i in path}
    flows: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for i in path:
        b = meta[i]
        for m in b["moves"]:
            if m["delayed"] or m["owner"] == "opp" or m["draw"]:
                continue
            for z, slot in ((m["src"], 0), (m["dst"], 1)):
                if z != "bz":
                    continue
                if m["ref_self"]:
                    flows[b["card"]][slot] += 1
                elif isinstance(m["src"], str):
                    for c in cards:
                        if Z._match(m["flt"], rules.cards[c]):
                            flows[c][slot] += 1
    return all(inn >= out for out, inn in flows.values())


def has_gain(own, opp) -> bool:
    return any(own.get(z, 0) > 0 for z in GAIN_ZONES) or any(v < 0 for v in opp.values())


def period_of(meta, path) -> str:
    """ターン内に繰り返せるか。time 系前提と when の via/unpaid ゲートを見る。
    主グラフの前提種は move/cast/draw のみなので、通常は in_turn になる。"""
    gated = set()
    for i in path:
        k = meta[i]["prem"]["kind"] if meta[i]["prem"] else None
        if k in Z.TICKS:
            gated.add(k)
        w = meta[i]["when"]
        if w.get("via") or w.get("unpaid"):
            gated.add("via/unpaid")
    return "in_turn" if not gated else "gated:" + ",".join(sorted(gated))


# ---------------------------------------------------------------- サイクル列挙

class CycleCounter:
    def __init__(self, g: Graph, rules, store_caps: dict):
        self.g = g
        self.meta = g.meta
        self.rules = rules
        self.counts = Counter()
        self.stored = []
        self.store_caps = store_caps          # stage -> 保存上限（記録順の偏りに注意）
        self.n_stored = Counter()

    def record(self, path, scores, stage: str):
        meta = self.meta
        own, opp = cycle_deltas(meta, path)
        cards = sorted({meta[i]["card"] for i in path})
        sure = all(s == 2 for s in scores)
        per = period_of(meta, path)
        key = (stage, len(path), len(cards), sure, per == "in_turn")
        self.counts[key] += 1
        if "?" in own or "?" in opp:
            self.counts[("qmark",) + key[1:]] += 1
        bal = flow_balance(self.rules, meta, path, own)
        if bal:
            self.counts[("balanced_" + stage,) + key[1:]] += 1
        gain = has_gain(own, opp)
        if gain:
            self.counts[("gain_" + stage,) + key[1:]] += 1
        if bal and gain:
            self.counts[("pruned_" + stage,) + key[1:]] += 1
            if self.n_stored[stage] < self.store_caps.get(stage, 0):
                self.n_stored[stage] += 1
                self.stored.append({"bundles": list(path), "cards": cards,
                                    "names": {c: self.rules.cards[c].name for c in cards},
                                    "delta": own, "opp_delta": opp, "sure": sure,
                                    "period": per,
                                    "mana": sum(meta[i]["cost"] for i in path
                                                if meta[i]["origin"] in ("spell", "summon"))})


def enumerate_l12(g: Graph, cc: CycleCounter):
    """長さ1（自己ループ）と長さ2のサイクルを全辺で網羅する。"""
    for n, i in enumerate(g.keep):
        if n % 3000 == 0:
            print(f"  L12 nodes {n}/{len(g.keep)} raw={sum(v for k, v in cc.counts.items() if k[0] == 'L12')}",
                  flush=True)
        t, s = g.row(i)
        if len(t) == 0:
            continue
        k = np.searchsorted(t, i)
        if k < len(t) and t[k] == i:
            cc.record([i], [int(s[k])], "L12")
        for a in range(len(t)):
            j = int(t[a])
            if j <= i:
                continue
            if g.has_edge(j, i):
                cc.record([i, j], [int(s[a]), g.edge_score(j, i)], "L12")


def enumerate_l34(g: Graph, cc: CycleCounter, max_len: int, time_cap: float,
                  visit_cap: int):
    """長さ3・4のサイクルを sure 辺（スコア2）の部分グラフで列挙する。
    正規形（最小添字が起点、中間ノードは起点より大）で重複を除く。
    上限に達したら truncated=True を返す（件数は下限）。"""
    t0 = time.time()
    visits = [0]
    truncated = [False]
    sure_adj: dict[int, list[int]] = {}
    for i in g.keep:
        t, s = g.row(i)
        sure_adj[i] = [int(t[k]) for k in range(len(t)) if s[k] == 2]

    def dfs(start, path):
        if truncated[0]:
            return
        visits[0] += 1
        if visits[0] > visit_cap or time.time() - t0 > time_cap:
            truncated[0] = True
            return
        last = path[-1]
        row = sure_adj.get(last, [])
        for j in row:
            if j == start:
                if len(path) >= 3:
                    cc.record(path, [2] * len(path), "L34")
                break
        if len(path) >= max_len:
            return
        in_path = set(path)
        path_cards = {g.meta[i]["card"] for i in path}
        for j in row:
            if j <= start or j in in_path:
                continue
            if len(path_cards | {g.meta[j]["card"]}) > 4:
                continue
            dfs(start, path + [j])
            if truncated[0]:
                return

    for s in sorted(sure_adj.keys()):
        dfs(s, [s])
        if truncated[0]:
            break
    return truncated[0], visits[0]


# ---------------------------------------------------------------- 陽性対照

def find_bundle(meta, card=None, name=None, origin=None, prem_kind=None, prem_to=None):
    out = []
    for i, m in enumerate(meta):
        if card and m["card"] != card:
            continue
        if name and m["name"] != name:
            continue
        if origin and m["origin"] != origin:
            continue
        if prem_kind and (not m["prem"] or m["prem"]["kind"] != prem_kind):
            continue
        if prem_to and (not m["prem"] or m["prem"]["to"] != prem_to):
            continue
        out.append(i)
    return out


def controls(g: Graph):
    """対照3件を、厳密サイクルと前提閉集合の両方で確認する（診断つき）。"""
    meta = g.meta

    def fed_by(i, within):
        return any(g.has_edge(a, i) for a in within)

    def closed(idxs):
        return bool(idxs) and all(fed_by(i, idxs) for i in idxs)

    res = {}
    saga_trig = find_bundle(meta, card=SAGA, origin="trigger", prem_kind="move", prem_to="bz")
    res["saga"] = {"bundles": saga_trig,
                   "self_loop_in_graph": [i for i in saga_trig if g.has_edge(i, i)]}
    xen = find_bundle(meta, card=XENARCH, origin="trigger", prem_kind="move", prem_to="graveyard")
    pair = saga_trig + xen
    res["saga_xenarch"] = {
        "bundles": pair,
        "strict_cycle": bool(saga_trig and xen and g.has_edge(saga_trig[0], xen[0])
                             and g.has_edge(xen[0], saga_trig[0])),
        "saga_feeds_xenarch": [bool(g.has_edge(s, x)) for s in saga_trig for x in xen],
        "xenarch_feeds_saga": [bool(g.has_edge(x, s)) for s in saga_trig for x in xen],
        "premise_closed_set": closed(pair)}
    orz = find_bundle(meta, name="魔刻の斬将オルゼキア／訪れる魔の時刻", origin="spell")
    holy = find_bundle(meta, name="天命龍装 ホーリーエンド／ナウ・オア・ネバー", origin="spell")
    wok = find_bundle(meta, card="dm24ex1-038", origin="trigger", prem_kind="move", prem_to="bz")
    aka = find_bundle(meta, card="dm23ex2-009")
    core2 = orz + holy
    core3 = core2 + wok
    res["akashic"] = {
        "akashic3_bundles": aka,
        "orzekia_spell": orz, "holyend_spell": holy, "wokanna_trigger": wok,
        "two_bundle_cycle": bool(orz and holy and g.has_edge(orz[0], holy[0])
                                 and g.has_edge(holy[0], orz[0])),
        "core2_premise_closed": closed(core2),
        "core3_premise_closed": closed(core3) if len(core3) == 3 else False,
        "wokanna_fed_by_cycle": bool(wok and core2 and fed_by(wok[0], core2)),
        "wokanna_feeds_back": bool(wok and core2 and any(
            g.has_edge(w, c) for w in wok for c in core2))}
    return res


# ---------------------------------------------------------------- spotcheck

def spotcheck(n: int, timeout: int) -> int:
    """精緻化ファネルを通った新規サイクルに judge_engine_once を通す。

    選定: A（厳密）= engine_verdict 合格 ∧ マナコスト0 ∧ '?' なし ∧ sure ∧ in_turn
    から最大6件、B（多枚組）= 同条件でカード種>=3 ∧ マナ持続（コスト0または
    サイクル自身がマナを生む）から最大4件。いずれも既知コアを含まず、
    カード組で重複させない。"""
    from dmsim.discovery.hunt3 import engine_verdict
    from tools.combo_hunt3_run import KNOWN_CORE
    known_ids = set(KNOWN_CORE) | {XENARCH}
    rules = load_rules()
    known_names = {rules.cards[c].name for c in known_ids if c in rules.cards}
    rows = [json.loads(l) for l in CYCLES.read_text(encoding="utf-8").splitlines() if l.strip()]

    def to_hunt3(r):
        d = {f"{z}:0": v for z, v in r["delta"].items()}
        d.update({f"{z}:1": v for z, v in r["opp_delta"].items()})
        return d

    def base_ok(r):
        return (engine_verdict(to_hunt3(r))[1] and r["sure"] and r["period"] == "in_turn"
                and "?" not in r["delta"] and "?" not in r["opp_delta"]
                and not (set(r["cards"]) & known_ids)
                and not (set(r["names"].values()) & known_names))

    pool_a = sorted((r for r in rows if base_ok(r) and r["mana"] == 0),
                    key=lambda r: (len(r["cards"]), len(r["bundles"])))
    pool_b = sorted((r for r in rows if base_ok(r) and len(r["cards"]) >= 3
                     and (r["mana"] == 0 or r["delta"].get("mana", 0)
                          + r["delta"].get("mana_untapped", 0) > 0)),
                    key=lambda r: (r["mana"], len(r["bundles"])))
    novel, seen_sets = [], set()
    for r in pool_a[:6] + pool_b[:4]:
        k = tuple(r["cards"])
        if k in seen_sets:
            continue
        seen_sets.add(k)
        novel.append(r)
    novel = novel[:n]
    out_path = OUT / "spotcheck.jsonl"
    done = set()
    if out_path.exists():
        for l in out_path.read_text(encoding="utf-8").splitlines():
            if l.strip():
                done.add(json.dumps(json.loads(l)["cards"], sort_keys=True))
    picked = 0
    for r in novel:
        if picked >= n:
            break
        cards = {c: 2 for c in r["cards"]}
        if json.dumps(cards, sort_keys=True) in done:
            continue
        job = {"mode": "once", "cards": cards, "budget": 1000, "seed": 1}
        t0 = time.time()
        try:
            p = subprocess.run([sys.executable, str(Path(__file__).resolve().parent
                                                     / "combo_hunt3_struct.py"),
                                "--one", json.dumps(job)],
                               capture_output=True, text=True, timeout=timeout,
                               cwd=str(Path(__file__).resolve().parent.parent))
            if p.returncode != 0:
                rec = {"cards": cards, "names": r["names"], "cycle": r,
                       "error": f"exit {p.returncode}: {p.stderr.strip()[-300:]}"}
            else:
                got = json.loads(p.stdout.strip().splitlines()[-1])
                rec = {"cards": cards, "names": r["names"], "cycle": r, "engine": got["engine"]}
        except subprocess.TimeoutExpired:
            rec = {"cards": cards, "names": r["names"], "cycle": r,
                   "error": f"timeout after {timeout}s"}
        rec["seconds"] = round(time.time() - t0, 1)
        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        eng = rec.get("engine") or {}
        print(f"{' + '.join(r['names'].values())}: pass={eng.get('pass')} "
              f"delta={eng.get('delta')} err={rec.get('error')} ({rec['seconds']}s)", flush=True)
        picked += 1
    return 0


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    pb = sub.add_parser("build")
    pb.add_argument("--kinds", default=",".join(ENUM_KINDS))
    pc = sub.add_parser("cycles")
    pc.add_argument("--max-len", type=int, default=4)
    pc.add_argument("--store-cap-l12", type=int, default=80_000)
    pc.add_argument("--store-cap-l34", type=int, default=150_000)
    pc.add_argument("--time-cap", type=float, default=900)
    pc.add_argument("--visit-cap", type=int, default=60_000_000)
    sub.add_parser("controls")
    sub.add_parser("gstats")
    ps = sub.add_parser("spotcheck")
    ps.add_argument("--n", type=int, default=10)
    ps.add_argument("--timeout", type=int, default=240)
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)

    if a.cmd == "build":
        g = build_graph(a.kinds.split(","))
        with GRAPH.open("wb") as f:
            pickle.dump(g, f)
        (OUT / "graph_stats.json").write_text(
            json.dumps(g.stats, ensure_ascii=False, indent=1), encoding="utf-8")
        print("saved", GRAPH, flush=True)
        return 0

    with GRAPH.open("rb") as f:
        g = pickle.load(f)

    if a.cmd == "gstats":
        deg = np.diff(g.offsets)
        sure = int((g.scores == 2).sum())
        print(json.dumps({
            "edges": int(g.offsets[-1]), "sure_edges": sure,
            "blind_edges": int(g.offsets[-1]) - sure,
            "out_degree_mean": round(float(deg.mean()), 1),
            "out_degree_median": int(np.median(deg)),
            "out_degree_p95": int(np.percentile(deg, 95)),
            "out_degree_max": int(deg.max()),
            "nodes_out0": int((deg == 0).sum())}, ensure_ascii=False, indent=1), flush=True)
        return 0

    if a.cmd == "controls":
        res = controls(g)
        (OUT / "controls.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(res, ensure_ascii=False, indent=1), flush=True)
        return 0

    if a.cmd == "cycles":
        rules = load_rules()
        cc = CycleCounter(g, rules, {"L12": a.store_cap_l12, "L34": a.store_cap_l34})
        t0 = time.time()
        enumerate_l12(g, cc)
        print(f"L12 done {time.time()-t0:.0f}s counts={sum(cc.counts.values())}", flush=True)
        truncated, visits = enumerate_l34(g, cc, a.max_len, a.time_cap, a.visit_cap)
        print(f"L34 done truncated={truncated} visits={visits} {time.time()-t0:.0f}s", flush=True)
        with CYCLES.open("w", encoding="utf-8") as f:
            for r in cc.stored:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        summary = {"truncated_l34": truncated, "visits_l34": visits,
                   "counts": {json.dumps(k, ensure_ascii=False): v
                              for k, v in sorted(cc.counts.items())},
                   "stored": len(cc.stored), "seconds": round(time.time() - t0, 1)}
        (OUT / "cycles_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=1), flush=True)
        return 0

    if a.cmd == "spotcheck":
        return spotcheck(a.n, a.timeout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
