"""コンボ発見 v3・第2層: 前提閉集合による候補生成（サイクル＋前提閉集合の本実装）。

手書きの構造署名（structsig）は「知っている形の家族」しか拾えず、サイクル
プローブ（tools/combo_hunt3_cycleprobe.py）の結論は「調整すれば可能」だった。
本モジュールはその本実装で、候補の単位を有向サイクル単独から **前提閉集合**
（組の全束の前提が組の中で満たされる集合）へ広げる:

- 核: 束の相互作用グラフ（A の効果が B の前提を満たす時に A→B）の有向サイクル。
  辺は zone_graph.feeds の「狙って満たせる」（スコア2）だけを使う（確実な辺）。
  遅延誘発の移動はターン内に連鎖しないため feeds の判定から外す（プローブと同じ）。
- 付け足し: 核に前提を満たされる束を持つカードを、役割つきで足す。
  役割は 核 (core) / 出力変換 (output_conversion: 核の移動イベントを受けて、
  その移動で送られた先から自分を取り戻す。XENARCH 型) / 積み荷 (cargo:
  前提を満たされるだけで戻り辺を持たない。ウォカンナ型) / 逆流 (feedback:
  核へ戻る辺を持つ＝実質的に大きなサイクルの一部) / イネーブラ (enabler:
  static の無料化・コスト軽減が核の札に届く)。
- 束は正準モジュール dmsim.engine.bundle_canon から取る（第1層の語彙統合）。
  種の同一性は正準 ID（cards.identity.canon_id。同名再録は alias）。

静的ファネル（第3層）は funnel_stage が担う:
- F3 確実性: '?' を含む移動が無い（辺の確実性・ターン内完結は構築時点で担保）。
- F1 収支: 参加カードの bz 同一性（出ていく数 <= 入る数。自己帰属を含む
  プローブ v2 の会計）＋ 集約デルタに獲得がある（自ゾーンの増または相手の減）
  ＋ 盾・マナの集約が減らない ＋ 手札の集約減は「一括戻し（many の手札戻し）が
  ある場合のみ許す。根拠: twinpact の回転（アカシック対照）では、count=any の
  一括戻しと ref 連鎖のため、移動を1回ずつ数える静的集約が実デルタ
  （自ゾーン収支ゼロ）とずれる。プローブでも回転対の収支は静的検証不能だった。
  engine_verdict（集約デルタ）は特徴として記録するが合否には使わない。
- F2 マナ持続: 実効マナ（イネーブラ適用後）が 0、または集約でマナが増える。

候補ごとに特徴ベクトル（種数・増分型・核の長さ・自己言及・ハブ次数・役割等）を
記録する（第4層の還流・将来の予測器の受け皿）。

使い方の本体は tools/combo_hunt3_cycles.py。
"""
from __future__ import annotations

import copy
import json
import re
import time
from collections import Counter, defaultdict

import numpy as np

from dmsim.cards.identity import canon_id
from dmsim.discovery import loop_cond as C
from dmsim.engine import bundle_canon as BC
from dmsim.engine import zone_graph as Z

# ---------------------------------------------------------------- 定数

#: グラフの対象にする前提種（ターン内に移動・詠唱・ドローの連鎖で満たせるもの）
NODE_KINDS = ("move", "cast", "draw")
#: 獲得とみなす自ゾーン（hunt2.GAIN_ZONES と同じ）
GAIN_ZONES = ("hand", "graveyard", "mana", "mana_untapped")
FLOW_ZONES = ("hand", "graveyard", "mana", "bz")

_T_CARD = re.compile(r"^T\d+$")


def is_test_card(cid: str) -> bool:
    """試験用カード（T001 等のプロト札）。候補から除外する。"""
    return bool(_T_CARD.match(cid or ""))


# ---------------------------------------------------------------- 束の要約

def _subj_json(s):
    return json.dumps(s, ensure_ascii=False, sort_keys=True) if isinstance(s, dict) else s


def _owner_key(o):
    return o if isinstance(o, str) else json.dumps(o, ensure_ascii=False, sort_keys=True)


def bundle_meta(b) -> dict:
    """束の JSON 化できる要約（グラフのノード属性）。
    card は正準 ID に直す（再録の別印刷が別種として分裂しないように）。"""
    p = b.prem
    return {"card": canon_id(b.card), "raw": b.card, "name": b.name,
            "origin": b.origin, "cost": b.cost or 0,
            "once": bool(getattr(b, "once", False)), "rearm": bool(b.rearm),
            "gate": C.gate(b),
            "prem": ({"kind": p.kind, "frm": p.frm, "to": p.to,
                      "subject": _subj_json(p.subject), "player": p.player,
                      "zone": p.zone, "draw_gated": bool(getattr(p, "draw_gated", False))} if p else None),
            "moves": [{"src": m.src, "dst": m.dst, "ref_self": bool(m.ref_self),
                       "draw": bool(m.draw), "owner": _owner_key(m.owner),
                       "flt": m.flt or {}, "delayed": bool(m.delayed),
                       "many": bool(m.many), "conditional": bool(m.conditional),
                       "ref": m.ref, "alias": m.alias} for m in b.moves]}


def _filtered(b):
    """遅延移動を除いた束（feeds 判定用）。遅延が無ければそのまま返す。"""
    if any(m.delayed for m in b.moves):
        c = copy.copy(b)
        c.moves = [m for m in b.moves if not m.delayed]
        return c
    return b


# ---------------------------------------------------------------- グラフ

class CanonGraph:
    """正準束の相互作用グラフ（確実な辺のみを CSR で保持）。

    meta: 全束の要約（bundle_canon の並び）。
    nodes: グラフのノードになる束の添字（meta の添字）。
    offsets/targets: nodes 上の CSR（targets は nodes 内の位置ではなく meta 添字）。
    statics: origin=static の束の添字。
    enablers: 無料化・コスト軽減の static の索引。
    """

    def __init__(self, meta, nodes, offsets, targets, statics, enablers, stats,
                 rep=None):
        self.meta = meta
        self.nodes = nodes
        self.node_set = set(nodes)
        self.offsets = offsets          # len = len(meta)+1（ノード外は空行）
        self.targets = targets
        self.statics = statics
        self.enablers = enablers
        self.stats = stats
        # 正準 ID → 収録されている代表印刷 ID（正準印刷自体が未収録の種がある。
        # rules.cards の実参照と判定にはこちらを使う）
        self.rep = rep or {}

    def row(self, i: int):
        return self.targets[self.offsets[i]:self.offsets[i + 1]]

    def has_edge(self, i: int, j: int) -> bool:
        t = self.row(i)
        k = np.searchsorted(t, j)
        return k < len(t) and t[k] == j

    def out_degree(self, i: int) -> int:
        return int(self.offsets[i + 1] - self.offsets[i])


def _enabler_of(b, meta_i: int) -> dict | None:
    """static 束が無料化・コスト軽減のイネーブラなら、その記述を返す。"""
    st = (getattr(b, "ann", {}) or {}).get("static") or {}
    mod = st.get("mod") or {}
    allow = mod.get("allow") or []
    flat = [a if isinstance(a, str) else (a.get("action") if isinstance(a, dict) else None)
            for a in allow]
    affects = st.get("affects")
    if "cast_free" in flat:
        return {"bundle": meta_i, "card": canon_id(b.card), "kind": "free",
                "amount": None, "cost_min": 0, "affects": affects}
    if isinstance(mod.get("cost"), int) and mod["cost"] < 0:
        return {"bundle": meta_i, "card": canon_id(b.card), "kind": "reduce",
                "amount": -mod["cost"],
                "cost_min": mod.get("cost_min") if isinstance(mod.get("cost_min"), int) else 0,
                "affects": affects}
    return None


def _affects_covers(affects, target_cd) -> bool:
    """static の affects が対象カードに届くか（エンジンの affects 解釈の近似）。
    "self" は自分の札だけ、文字列のその他は届かないものとして扱う。
    dict は owner が you（または無指定）で filter が対象に適合する時。"""
    if affects == "self":
        return False            # 自分専用は呼び出し側（同一カード）で扱う
    if not isinstance(affects, dict):
        return False
    if affects.get("owner") not in (None, "you"):
        return False
    flt = affects.get("filter") or {}
    return Z._match(flt, target_cd)


def enabler_applies(en: dict, enabler_card: str, target_cd) -> bool:
    """イネーブラ en が対象カード target_cd に届くか（種は正準 ID で比べる）。"""
    if enabler_card == canon_id(target_cd.id):
        return True             # 自分専用の static は自分の札に届く
    return _affects_covers(en["affects"], target_cd)


def build_graph(rules, only_cards: set[str] | None = None) -> CanonGraph:
    """正準束からグラフを構築する。only_cards はテスト用の絞り込み
    （そのカード種の束だけをノードにする。feeds の判定は rules 全体を使う）。"""
    t0 = time.time()
    bs = BC.bundles(rules)
    meta = [bundle_meta(b) for b in bs]
    rep: dict[str, str] = {}
    for m in meta:
        rep.setdefault(m["card"], m["raw"])
    filt = [_filtered(b) for b in bs]

    nodes, statics, enablers = [], [], []
    excluded = Counter()
    for i, b in enumerate(bs):
        if b.origin == "static":
            statics.append(i)
            en = _enabler_of(b, i)
            if en is not None and not is_test_card(meta[i]["card"]):
                enablers.append(en)
            continue
        m = meta[i]
        if only_cards is not None and m["card"] not in only_cards:
            excluded["only_cards"] += 1
            continue
        if is_test_card(m["card"]):
            excluded["test_card"] += 1
            continue
        if m["prem"] is None:
            excluded["no_premise"] += 1
            continue
        if m["gate"] is not None:
            excluded[f"gate:{m['gate']}"] += 1
            continue
        if m["prem"]["kind"] not in NODE_KINDS:
            excluded[f"kind:{m['prem']['kind']}"] += 1
            continue
        nodes.append(i)
    node_set = set(nodes)

    # feeds の候補絞り（プローブと同じ: 前提の行き先で索引する）
    by_dst: dict[str, list[int]] = defaultdict(list)
    drawers, spells = [], []
    for i in nodes:
        for z in {mv["dst"] for mv in meta[i]["moves"] if isinstance(mv["dst"], str)}:
            by_dst[z].append(i)
        if any(mv["draw"] for mv in meta[i]["moves"]):
            drawers.append(i)
        if bs[i].origin == "spell":
            spells.append(i)

    rows: dict[int, list[int]] = {}
    n_pairs = 0
    for j in nodes:
        p = bs[j].prem
        if p.kind == "move":
            cand = by_dst.get(p.to, []) if p.to is not None else []
        elif p.kind == "cast":
            cand = spells
        else:  # draw
            cand = drawers
        for i in cand:
            if i not in node_set:
                continue
            n_pairs += 1
            if Z.feeds(filt[i], bs[j], rules) == 2:
                rows.setdefault(i, []).append(j)
    offsets = np.zeros(len(bs) + 1, dtype=np.int64)
    parts = []
    for i in range(len(bs)):
        if i in rows:
            t = np.array(sorted(rows[i]), dtype=np.int32)
            parts.append(t)
            offsets[i + 1] = offsets[i] + len(t)
        else:
            offsets[i + 1] = offsets[i]
    targets = np.concatenate(parts) if parts else np.zeros(0, dtype=np.int32)
    # イネーブラの適用範囲（届く種の集合）を全種に対して事前に計算する
    for en in enablers:
        applies = {en["card"]}
        if isinstance(en["affects"], dict):
            for sp, raw in rep.items():
                if _affects_covers(en["affects"], rules.cards[raw]):
                    applies.add(sp)
        en["applies"] = applies
    stats = {"bundles": len(bs), "nodes": len(nodes), "statics": len(statics),
             "enablers": len(enablers), "edges_sure": int(offsets[-1]),
             "pairs_evaluated": n_pairs, "excluded": dict(excluded),
             "seconds": round(time.time() - t0, 1)}
    return CanonGraph(meta, nodes, offsets, targets, statics, enablers, stats,
                      rep=rep)


# ---------------------------------------------------------------- 収支

def set_deltas(meta, idxs) -> tuple[dict, dict]:
    """束集合の自/相手ゾーン収支（非遅延の移動を1回ずつ数える近似）。"""
    own, opp = Counter(), Counter()
    for i in idxs:
        for m in meta[i]["moves"]:
            if m["delayed"] or not isinstance(m["src"], str) or not isinstance(m["dst"], str):
                continue
            d = own if m["owner"] != "opp" else opp
            d[m["src"]] -= 1
            d[m["dst"]] += 1
    return ({k: v for k, v in own.items() if v}, {k: v for k, v in opp.items() if v})


def bundle_delta(meta, i: int) -> tuple[dict, dict]:
    return set_deltas(meta, [i])


def has_gain(own: dict, opp: dict) -> bool:
    return any(own.get(z, 0) > 0 for z in GAIN_ZONES) or any(v < 0 for v in opp.values())


def bz_identity(rules, meta, idxs) -> bool:
    """参加カードの bz 同一性: カード C ごとに、C を bz から出しうる移動の数 <=
    C を bz へ入れうる移動の数（プローブ v2 の会計。帰属は ref_self（本人）と、
    フィルタが C に適合する owner=you の移動（持ち主自身を含む全参加カード））。"""
    cards = {meta[i]["card"] for i in idxs}
    raw_of = {meta[i]["card"]: meta[i]["raw"] for i in idxs}
    flows: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for i in idxs:
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
                        if Z._match(m["flt"], rules.cards[raw_of[c]]):
                            flows[c][slot] += 1
    return all(inn >= out for out, inn in flows.values())


def hunt3_delta(own: dict, opp: dict) -> dict:
    """集約デルタを hunt3 の増分ベクトル形式（"zone:player"）に直す。"""
    d = {f"{z}:0": v for z, v in own.items()}
    d.update({f"{z}:1": v for z, v in opp.items()})
    return d


# ---------------------------------------------------------------- 核（サイクル）

def _core_record(g: CanonGraph, path: list[int]) -> dict:
    meta = g.meta
    own, opp = set_deltas(meta, path)
    return {"bundles": list(path), "cards": sorted({meta[i]["card"] for i in path}),
            "delta": own, "opp_delta": opp,
            "mana": sum(meta[i]["cost"] for i in path if meta[i]["origin"] in ("spell", "summon")),
            "max_out_degree": max((g.out_degree(i) for i in path), default=0)}


def _delta_sig(own: dict, opp: dict) -> str:
    return json.dumps({"d": own, "o": opp}, sort_keys=True, ensure_ascii=False)


def enumerate_cores(g: CanonGraph, *, deg_cap: int = 400, visit_cap: int = 40_000_000,
                    start_visit_cap: int = 20_000, time_cap: float = 1200.0,
                    ) -> tuple[list[dict], dict]:
    """厳密サイクル（核）を列挙する。長さ1・2は全 sure 辺で網羅し、長さ3・4は
    出次数キャップつき DFS（ハブ刈り）。種は4まで・束は4まで。
    戻り値は (核のリスト, 統計)。核は (カード種集合, デルタ署名) で重複を除き、
    見本は「束が少ない → マナが安い → ハブ次数が小さい」順で残す。"""
    t0 = time.time()
    best: dict[tuple, dict] = {}

    def offer(path):
        rec = _core_record(g, path)
        key = (tuple(rec["cards"]), _delta_sig(rec["delta"], rec["opp_delta"]))
        rank = (len(path), rec["mana"], rec["max_out_degree"])
        cur = best.get(key)
        if cur is None or rank < cur[0]:
            best[key] = (rank, rec)

    nodes = g.nodes
    # 長さ1（自己ループ）
    n_l1 = 0
    for i in nodes:
        if g.has_edge(i, i):
            offer([i])
            n_l1 += 1
    # 長さ2
    n_l2 = 0
    for i in nodes:
        for j in g.row(i):
            j = int(j)
            if j > i and g.has_edge(j, i):
                offer([i, j])
                n_l2 += 1
    # 長さ3・4（キャップつき DFS。正規形: 起点が最小、中間は起点より大。
    # 訪問上限は開始点ごと＋全体の二重にする: 序盤のハブ開始点が全体の
    # 予算を使い切って後続が列挙できない事態を避ける）
    truncated = False
    visits = [0]
    n_l34 = 0
    start_visits = [0]

    def dfs(start, path, path_cards):
        nonlocal truncated, n_l34
        if truncated:
            return
        visits[0] += 1
        start_visits[0] += 1
        if visits[0] > visit_cap or time.time() - t0 > time_cap:
            truncated = True
            return
        if start_visits[0] > start_visit_cap:
            return
        last = path[-1]
        row = g.row(last)
        if len(path) >= 3:
            k = np.searchsorted(row, start)
            if k < len(row) and row[k] == start:
                offer(list(path))
                n_l34 += 1
        if len(path) >= 4:
            return
        for j in row:
            j = int(j)
            if j <= start or j in path:
                continue
            if g.out_degree(j) > deg_cap:
                continue
            nc = path_cards | {g.meta[j]["card"]}
            if len(nc) > 4:
                continue
            dfs(start, path + [j], nc)
            if truncated:
                return

    for s in sorted(nodes, key=lambda i: g.out_degree(i)):
        if g.out_degree(s) > deg_cap:
            continue
        start_visits[0] = 0
        dfs(s, [s], {g.meta[s]["card"]})
        if truncated:
            break
    # 退化した核を除く: 全束がドロー前提の核は、ドロー効果が自分の前提を
    # 満たすだけの自己言及で、カード移動の回帰ではない（feeds の draw 前提は
    # 引く主体を区別しないため大量に生まれる。第1波の判定で全件不一致だった）
    def all_draw(rec) -> bool:
        return all((g.meta[i]["prem"] or {}).get("kind") == "draw"
                   for i in rec["bundles"])
    n_degenerate = sum(1 for _, rec in best.values() if all_draw(rec))
    cores = [rec for _, rec in best.values() if not all_draw(rec)]
    cores.sort(key=lambda r: (len(r["cards"]), len(r["bundles"]), r["mana"],
                              r["max_out_degree"]))
    stats = {"self_loops": n_l1, "pairs": n_l2, "l34_offers": n_l34,
             "distinct_cores": len(cores), "degenerate_draw_cores": n_degenerate,
             "l34_truncated": truncated,
             "l34_visits": visits[0], "seconds": round(time.time() - t0, 1)}
    return cores, stats


# ---------------------------------------------------------------- 前提閉集合

def _is_output_conversion(meta, rules, core_moves: list[dict], b: int) -> bool:
    """出力変換の形: 核の移動イベントに反応して自分を取り戻し、核の増分の
    行き先を変える束。配線は2通りある。
    (a) 傍受型（XENARCH）: 主体が self でない前提（自分の札一般の移動を見張る）
        で、前提ゾーンに待機し、自分自身をそこから戻す。
    (b) 自己到着型（胡椒）: 自分が前提ゾーンに着いた時に発動し、戻し移動の
        フィルタが自分自身に適合する（ref_self でなくてもよい）。
    召喚束・呪文束（唱える行為そのもの）はどちらの形でもない。"""
    m = meta[b]
    p = m["prem"]
    if not p or p["kind"] != "move" or p["to"] is None:
        return False
    if m["origin"] in ("summon", "spell"):
        return False
    if not any(mv["dst"] == p["to"] and (p["frm"] is None or mv["src"] == p["frm"])
               for mv in core_moves):
        return False
    if p["subject"] != "self":
        return any(mv["ref_self"] and mv["src"] == p["zone"] for mv in m["moves"])
    cd = rules.cards[m["raw"]]
    return any(mv["src"] == p["zone"]
               and (mv["ref_self"] or Z._match(mv["flt"], cd))
               for mv in m["moves"])


def _fed_additions(g: CanonGraph, member: set[int], member_cards: set[str],
                   ) -> dict[str, list[int]]:
    """メンバーの束に前提を満たされる（sure 辺）束を、カード別に集める。
    戻り値の束は「デルタに寄与する」か「メンバーへ逆流する」ものだけ
    （純粋な乗客束は見本に入れない）。自カードの追加束は種集合を変えない
    ため対象外。"""
    fed: set[int] = set()
    for a in member:
        fed.update(int(j) for j in g.row(a))
    fed -= member
    by_card: dict[str, list[int]] = defaultdict(list)
    for b in fed:
        card = g.meta[b]["card"]
        if card in member_cards:
            continue
        own, opp = bundle_delta(g.meta, b)
        active = bool(own or opp)
        feedback = any(g.has_edge(b, a) for a in member)
        if active or feedback:
            by_card[card].append(b)
    return by_card


def _feeds_structural(g: CanonGraph, b: int, a: int) -> bool:
    """b→a の sure 辺が「対象を狙える移動」で支えられているか。
    山札→手札の移動（ドロー系）は正準層の feeds では sure 扱いだが、
    特定の札を手札に戻す配線ではないので、構造的な逆流とはみなさない。"""
    if not g.has_edge(b, a):
        return False
    pa = g.meta[a]["prem"]
    if pa is None or pa["kind"] != "move":
        return True
    return any(m["dst"] == pa["to"] and (pa["frm"] is None or m["src"] == pa["frm"])
               and not (m["src"] == "deck" and m["dst"] == "hand")
               for m in g.meta[b]["moves"] if not m["delayed"])


def _roles(g: CanonGraph, rules, member: set[int], core: set[int],
           additions: list[int], core_moves: list[dict]) -> dict[int, str]:
    roles: dict[int, str] = {}
    for b in additions:
        if any(_feeds_structural(g, b, a) for a in member):
            roles[b] = "feedback"
        elif _is_output_conversion(g.meta, rules, core_moves, b):
            roles[b] = "output_conversion"
        else:
            roles[b] = "cargo"
    for b in core:
        roles[b] = "core"
    return roles


def _enablers_for(g: CanonGraph, cards: set[str]) -> list[dict]:
    """札の集合に届くイネーブラ（static）を種別に返す（applies は構築時に計算）。"""
    out: dict[str, dict] = {}
    for en in g.enablers:
        if en["card"] in cards or cards & en.get("applies", {en["card"]}):
            out.setdefault(en["card"], en)
    return list(out.values())


def _effect_enters_bz(g: CanonGraph, rules, idxs, i: int) -> bool:
    """束 i の札が、組の他の束の効果（bz への移動）で場に出るか。
    効果で出る召喚はマナを払わない（例: ウォカンナはホーリーエンドの
    効果で場に出る。サガは自身の誘発で墓地から戻る）。"""
    cd = rules.cards[g.meta[i]["raw"]]
    for j in idxs:
        if j == i:
            continue
        for m in g.meta[j]["moves"]:
            if m["dst"] != "bz" or m["delayed"] or m["owner"] == "opp":
                continue
            if m["ref_self"] and g.meta[j]["card"] == g.meta[i]["card"]:
                return True
            if not m["ref_self"] and Z._match(m["flt"], cd):
                return True
    return False


def effective_mana(g: CanonGraph, rules, idxs, enabler_bundles: list[int]) -> int:
    """組の実効マナ（1周分）。組の中のイネーブラを適用する:
    cast_free が届く札は 0、コスト軽減は届く範囲で最大の軽減を適用（下限つき）。
    召喚は、組の効果で場に出る場合は 0（コストを払うのは自分で唱える時だけ）。"""
    ens = [e for e in g.enablers if e["bundle"] in set(enabler_bundles)]
    total = 0
    for i in idxs:
        m = g.meta[i]
        if m["origin"] not in ("spell", "summon"):
            continue
        cost = m["cost"]
        if cost <= 0:
            continue
        if m["origin"] == "summon" and _effect_enters_bz(g, rules, idxs, i):
            continue
        cd = rules.cards[m["raw"]]
        best = cost
        for e in ens:
            if not enabler_applies(e, e["card"], cd):
                continue
            if e["kind"] == "free":
                best = 0
            else:
                best = min(best, max(cost - e["amount"], e["cost_min"]))
        total += best
    return total


def build_closed_sets(g: CanonGraph, rules, core: dict, *,
                      add_cap: int = 300,
                      must_include: set[str] | None = None) -> list[dict]:
    """核1つから前提閉集合の候補を作る。形は
    核のみ / 核＋イネーブラ / 核＋付け足し1種 / 核＋イネーブラ＋付け足し1種
    （カード種は合計4まで）。各候補は見本の束（役割つき）を持つ。
    付け足しは階層＋増分署名で選別する（本関数内のコメント参照）。
    must_include に挙げた種は選別の対象外（対照＝既知エンジンの回帰保証用。
    一般候補の生成には影響しない）。"""
    meta = g.meta
    core_bundles = list(core["bundles"])
    core_set = set(core_bundles)
    core_cards = set(core["cards"])
    core_moves = [m for i in core_bundles for m in meta[i]["moves"] if not m["delayed"]]
    additions = _fed_additions(g, core_set, core_cards) if len(core_cards) < 4 else {}
    if len(additions) > add_cap:
        # 付け足しの優先順位: 0=逆流・出力変換（構造的に効く形）、
        # 1=核に無い増分を持つ／核の減少を補う（ゼブルエ・ルード型の積み荷）、
        # 2=その他。コスト順だけだと本命の積み荷が高コストで埋もれる。
        def add_tier(item) -> int:
            _, blist = item
            if any(any(_feeds_structural(g, b, a) for a in core_set)
                   or _is_output_conversion(meta, rules, core_moves, b)
                   for b in blist):
                return 0
            own, opp = set_deltas(meta, blist)
            # 補完の判定は verdict の獲得ゾーンより広く取る（場・盾の増分も、
            # 核に無い増分なら積み荷として意味がある。ゼブルエの盾、エビデンス
            # の場経由ドローが該当する）
            comp = any(own.get(z, 0) > 0 and core["delta"].get(z, 0) <= 0
                       for z in GAIN_ZONES + ("bz", "shield"))
            comp = comp or any(v < 0 and core["opp_delta"].get(z, 0) >= 0
                               for z, v in opp.items())
            return 1 if comp else 2
        # 同じ増分署名の付け足しは代表だけ残す（コスト順の選別だと、盾増分や
        # ドローのような珍しい署名を持つ高コストの本命が埋もれる）。
        def sig_of(blist) -> str:
            own, opp = set_deltas(meta, blist)
            return _delta_sig(own, opp)
        ranked = sorted(additions.items(),
                        key=lambda it: (add_tier(it),
                                        min(meta[b]["cost"] for b in it[1]),
                                        it[0]))
        per_sig_cap = {0: 12, 1: 8, 2: 1}
        total_cap = {0: 600, 1: 800, 2: 100}
        sig_seen: Counter = Counter()
        total_seen: Counter = Counter()
        kept_add: dict[str, list[int]] = {}
        for card, blist in ranked:
            if must_include and card in must_include:
                kept_add[card] = blist
                continue
            t = add_tier((card, blist))
            key = (t, sig_of(blist))
            if sig_seen[key] >= per_sig_cap[t] or total_seen[t] >= total_cap[t]:
                continue
            sig_seen[key] += 1
            total_seen[t] += 1
            kept_add[card] = blist
        additions = kept_add

    def make(add_card: str | None, add_bundles: list[int],
             ens: list[dict]) -> dict:
        member = core_set | set(add_bundles)
        roles = _roles(g, rules, member, core_set, add_bundles, core_moves)
        bundles = [{"i": i, "role": roles[i]} for i in sorted(member)]
        for en in ens:
            bundles.append({"i": en["bundle"], "role": "enabler"})
        cards = sorted(core_cards | ({add_card} if add_card else set())
                       | {en["card"] for en in ens})
        return {"cards": cards, "core_cards": core["cards"], "bundles": bundles,
                "core_bundles": core_bundles,
                "enabler": [{"card": en["card"], "kind": en["kind"]} for en in ens]}

    out = []
    base_sets: list[tuple[str | None, list[int]]] = [(None, [])]
    base_sets += list(additions.items())
    for add_card, add_bundles in base_sets:
        species = core_cards | ({add_card} if add_card else set())
        member = core_set | set(add_bundles)
        # 組の種に含まれるイネーブラは物理的に存在するので常時つける
        intrinsic = [e for e in _enablers_for(g, species) if e["card"] in species]
        out.append(make(add_card, add_bundles, intrinsic))
        # 外部のイネーブラは最大2種まで足す: 「適用後の近似マナが最小」のものと、
        # 無料化（free）の最良のもの。近似スコア（節約量）で選ぶと大幅軽減が
        # 無料化を押しのけてアカシック型が漏れるため、結果マナで選ぶ。
        # 正確な実効マナはファネルが計算する（ここは近似でよい）。
        if len(species) < 4:
            payable = [(meta[i]["card"], meta[i]["cost"]) for i in member
                       if meta[i]["origin"] in ("spell", "summon")
                       and meta[i]["cost"] > 0]
            if payable:
                base_mana = sum(c for _, c in payable)
                scored = []
                for en in _enablers_for(g, species):
                    if en["card"] in species:
                        continue
                    applies = en.get("applies", {en["card"]})
                    result = 0
                    for card, cost in payable:
                        if card not in applies:
                            result += cost
                        elif en["kind"] == "free":
                            pass
                        else:
                            result += max(cost - en["amount"], en["cost_min"])
                    if result < base_mana:
                        scored.append((result, en))
                picks: list[dict] = []
                if scored:
                    scored.sort(key=lambda t: t[0])
                    picks.append(scored[0][1])
                    frees = [e for _, e in scored if e["kind"] == "free"]
                    if frees and frees[0] is not picks[0]:
                        picks.append(frees[0])
                for en in picks:
                    out.append(make(add_card, add_bundles, intrinsic + [en]))
    return out


def premise_closed(g: CanonGraph, idxs) -> bool:
    """見本の束集合が前提閉か（static を除く全束に、集合内からの sure 辺がある）。"""
    s = set(idxs)
    for b in s:
        if g.meta[b]["prem"] is None:
            continue
        if not any(g.has_edge(a, b) for a in s):
            return False
    return True


# ---------------------------------------------------------------- ファネル（第3層）

def funnel_evaluate(g: CanonGraph, rules, cand: dict) -> dict:
    """候補に静的ファネルを適用し、到達した段階と特徴ベクトルを返す。
    stage: "F3"（確実性で落ちた）/ "F1"（収支で落ちた）/ "F2"（マナで落ちた）/
    "pass"（全通過）。"""
    from dmsim.discovery.hunt3 import engine_type
    from dmsim.discovery.hunt2 import engine_verdict
    meta = g.meta
    idxs = [b["i"] for b in cand["bundles"]]
    move_idxs = [i for i in idxs if meta[i]["origin"] != "static"]
    own, opp = set_deltas(meta, move_idxs)
    hd = hunt3_delta(own, opp)
    kind, verdict_ok = engine_verdict(hd)
    feats: dict = {
        "n_species": len(cand["cards"]), "n_bundles": len(idxs),
        "core_len": len(cand["core_bundles"]),
        "roles": dict(Counter(b["role"] for b in cand["bundles"])),
        "has_self_ref": any(m["ref_self"] for i in move_idxs for m in meta[i]["moves"]),
        "max_out_degree": max((g.out_degree(i) for i in move_idxs), default=0),
        "delta": own, "opp_delta": opp, "engine_kind": kind,
        "engine_type": engine_type(hd, [kind] if kind else []),
        "verdict_ok": bool(verdict_ok),
        "mana_cost": sum(meta[i]["cost"] for i in move_idxs
                         if meta[i]["origin"] in ("spell", "summon")),
        "closed": premise_closed(g, move_idxs),
    }
    # F3: '?' を含む移動が無いこと（辺の確実性・ターン内は構築時点で担保）
    if any(m["src"] == "?" or m["dst"] == "?" for i in move_idxs for m in meta[i]["moves"]):
        return {"stage": "F3", "reason": "qmark_move", "features": feats}
    # F1: 収支
    if not feats["closed"]:
        return {"stage": "F1", "reason": "not_premise_closed", "features": feats}
    if not bz_identity(rules, meta, move_idxs):
        return {"stage": "F1", "reason": "bz_identity", "features": feats}
    if not has_gain(own, opp):
        return {"stage": "F1", "reason": "no_gain", "features": feats}
    if own.get("shield", 0) < 0 or own.get("mana", 0) + own.get("mana_untapped", 0) < 0:
        return {"stage": "F1", "reason": "shield_or_mana_drain", "features": feats}
    bulk_return = any(m["dst"] == "hand" and m["many"] and m["owner"] != "opp"
                      for i in move_idxs for m in meta[i]["moves"])
    feats["hand_bulk_return"] = bulk_return
    if own.get("hand", 0) < 0 and not bulk_return:
        return {"stage": "F1", "reason": "hand_drain", "features": feats}
    # F2: マナ持続
    en_bundles = [b["i"] for b in cand["bundles"] if b["role"] == "enabler"]
    eff = effective_mana(g, rules, move_idxs, en_bundles)
    feats["effective_mana"] = eff
    mana_net = own.get("mana", 0) + own.get("mana_untapped", 0)
    if eff > 0 and mana_net <= 0:
        return {"stage": "F2", "reason": "mana_not_sustained", "features": feats}
    return {"stage": "pass", "reason": None, "features": feats}


def candidate_rank(feats: dict) -> tuple:
    """候補の順位（小さいほど有望）: 集約デルタが合格形 → 実効マナが小さい →
    種が少ない → 核が短い → ハブ次数が小さい。"""
    return (0 if feats.get("verdict_ok") else 1, feats.get("effective_mana", 0),
            feats["n_species"], feats["core_len"], feats["max_out_degree"])


# ---------------------------------------------------------------- 陽性対照

SAGA = "dm22ex2-021"
XENARCH = "dm22rp2x-004"
AKASHIC = "dm23ex2-009"
ORZEKIA = "dm23bd7-035"
WOKANNA = "dm24ex1-038"
HOLYEND = "dmrp12-s01"          # alias（正準は dm25sp1-003）

#: 健全性ゲートの対照（カード種集合。正準 ID に直して比較する）。
#: core は v3 判定で確定した最小コアの種。ゲートは「最小コア種 ⊆ 候補 ⊆ 対照種」
#: を満たす候補があれば合格とする（ゼブルエのウォカンナのような乗客を含む
#: 対照でも、エンジンそのものを捉えた候補があればよい）。
CONTROL_SETS: list[dict] = [
    {"label": "saga", "cards": {SAGA}, "core": {SAGA}},
    {"label": "saga+xenarch", "cards": {SAGA, XENARCH}, "core": {SAGA, XENARCH}},
    {"label": "akashic", "cards": {AKASHIC, ORZEKIA, WOKANNA, HOLYEND},
     "core": {AKASHIC, ORZEKIA, WOKANNA, HOLYEND}},
] + [{"label": f"saga+struct:{cid}", "cards": {SAGA, cid}, "core": {SAGA, cid}}
     for cid in ("dmd05-009", "dmr11-029", "dmr13-091", "dmrp04s-077",
                 "dmrp19-046", "dmrp19-066", "dmrp20-068")] + [
    {"label": "akashic+rudo", "cards": {AKASHIC, ORZEKIA, HOLYEND, "dm26ex3-047"},
     "core": {AKASHIC, ORZEKIA, HOLYEND, "dm26ex3-047"}},
    {"label": "akashic+arche", "cards": {AKASHIC, ORZEKIA, HOLYEND, "dm26ex3-081"},
     "core": {AKASHIC, ORZEKIA, HOLYEND, "dm26ex3-081"}},
    {"label": "akashic+evidence",
     "cards": {AKASHIC, ORZEKIA, HOLYEND, "dmrp13-016"},
     "core": {AKASHIC, ORZEKIA, HOLYEND, "dmrp13-016"}},
    {"label": "akashic+zebrue", "cards": {AKASHIC, ORZEKIA, WOKANNA, "dmrp08-s01"},
     "core": {AKASHIC, ORZEKIA, "dmrp08-s01"}},
]


def control_species(ctrl: dict) -> tuple:
    return tuple(sorted(canon_id(c) for c in ctrl["cards"]))


def control_core_species(ctrl: dict) -> tuple:
    return tuple(sorted(canon_id(c) for c in ctrl.get("core", ctrl["cards"])))


def control_match(ctrl: dict, cand_species: tuple) -> bool:
    """候補の種集合が対照を捉えたか（最小コア種 ⊆ 候補 ⊆ 対照種）。"""
    core = set(control_core_species(ctrl))
    full = set(control_species(ctrl))
    s = set(cand_species)
    return core <= s <= full


def trace_control(g: CanonGraph, rules, ctrl: dict) -> dict:
    """対照1件を、グラフの中で直接たどって診断する（生成に漏れた場合の切り分け）:
    対照の札だけに絞った核の列挙 → イネーブラ付与 → 付け足し → ファネル。"""
    species = control_species(ctrl)
    cards = set(species)
    sub_nodes = [i for i in g.nodes if g.meta[i]["card"] in cards]
    # 対照内の核: 自己ループと相互辺のペア（長さ3以上は対照の範囲では不要）
    cores = []
    for i in sub_nodes:
        if g.has_edge(i, i):
            cores.append([i])
    for a in range(len(sub_nodes)):
        for b in range(a + 1, len(sub_nodes)):
            i, j = sub_nodes[a], sub_nodes[b]
            if g.has_edge(i, j) and g.has_edge(j, i):
                cores.append([i, j])
    acceptable = {species, control_core_species(ctrl)}
    diag: dict = {"label": ctrl["label"], "species": list(species),
                  "sub_nodes": len(sub_nodes), "cores_found": len(cores),
                  "witness": None}
    if not cores:
        diag["stage"] = "no_core"
        return diag
    # 全ての核・全ての一致候補を評価し、最も進んだ段階の見本を残す
    # （最初に一致した見本が悪い核由来でも、良い見本があれば対照は届いている）
    stage_order = {"pass": 3, "F2": 2, "F1": 1, "F3": 0}
    best = None
    for path in cores:
        core_rec = _core_record(g, path)
        for cand in build_closed_sets(g, rules, core_rec,
                                      must_include=set(species)):
            if tuple(cand["cards"]) not in acceptable:
                continue
            ev = funnel_evaluate(g, rules, cand)
            if best is None or stage_order[ev["stage"]] > stage_order[best[0]]:
                best = (ev["stage"], ev, cand)
            if ev["stage"] == "pass":
                break
        if best is not None and best[0] == "pass":
            break
    if best is None:
        diag["stage"] = "no_closed_set"
        # 切り分け: 核はあるが閉集合として対照の種集合に届かなかった
        diag["core_species"] = sorted(
            {tuple(_core_record(g, p)["cards"]) for p in cores})
        return diag
    _, ev, cand = best
    diag["witness"] = {"bundles": cand["bundles"], "stage": ev["stage"],
                       "reason": ev["reason"], "features": ev["features"]}
    diag["stage"] = ev["stage"]
    return diag
