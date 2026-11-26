"""静的なループ判定の「条件」を読む部分（tools/fast_loop_screen.py が使う、2026-11-14）。

束化そのものは正準モジュール dmsim.engine.bundle_canon に寄せた（抽出層の
語彙統合、2026-11-26）。本モジュールは発見側固有の付加情報だけを持つ:
- 移動の条件 Move.conds: その移動を囲む if の cond の並び（bundle_canon が
  束への注釈として付ける。may・modal の選択はいつでも選べるので条件にしない）
- gate: 前提のうち移動だけでは満たせない限定の判定（発見側のポリシー）
- 特殊勝利 win_paths: 勝つ効果（op: win）と、そこに至る条件（能力の if・
  置換の if・囲む if）と前提（誘発・置換の when）
- 条件の評価 cond_state(cond, ctx): "yes"（組の中で満たせる）/ "no"
  （満たせない）/ "unknown"（読めない）。ctx はループ1周の収支など。

_walk / _many は後方互換のため残す（束化には使わない）。
"""
from __future__ import annotations

from dmsim.engine import bundle_canon as BC
from dmsim.engine import zone_graph as Z

CHILD = ("then", "else", "body")


def _walk(ops, conds=(), delayed=False):
    for op in ops or []:
        if not isinstance(op, dict):
            continue
        o = op.get("op")
        if o in ("move", "draw", "play_free", "swap"):
            yield op, conds, delayed
        if o == "if":
            c = conds + (op.get("cond"),)
            yield from _walk(op.get("then"), c, delayed)
            yield from _walk(op.get("else"), conds + ({"not": op.get("cond")},), delayed)
            continue
        if o == "modal":
            for m in op.get("modes") or []:
                yield from _walk(m, conds, delayed)
            continue
        for k in CHILD:
            if isinstance(op.get(k), list):
                yield from _walk(op[k], conds, delayed)
        if o == "delayed_trigger":
            yield from _walk(op.get("effect", []), conds, True)


def _many(sel):
    c = sel.get("count", 1)
    return c in ("any", "all") or (isinstance(c, int) and c > 1)


def moves(ops, zone="bz", after=None, card=None) -> list[Z.Move]:
    """zone: 能力が働くゾーン。after: 誘発の後に自分がいるゾーン（ref: self_moved）。card: 自分の札の定義（呪文の面を唱える時）。

    正準モジュール bundle_canon.moves_of への委譲（2026-11-26 統合）。
    従来の本モジュール独自の解釈との差は bundle_canon の docstring 参照:
    ref の束縛解決、特殊セレクタ、play_free の宛先推定、移動を生む op の
    拡充（put_under / play_self / break 等）がエンジン解釈に一致した。
    """
    return BC.moves_of(ops, zone, after=after, card=card)


def bundles(rules) -> list[Z.Bundle]:
    """全カードの束（正準 bundle_canon.bundles への委譲）。

    従来との差: trigger/declare に加えて replace / activate / silent /
    static の束が増え、前提イベントの範囲が defs.EVENTS 全体に広がった。
    ループ判定側の受け止めは gate() が担う（下記）。
    """
    return BC.bundles(rules)


def gate(b) -> str | None:
    """誘発の前提のうち、カードの移動だけでは満たせない限定。via（特定の方法で出た時: D・D・D 等）・unpaid（コストを払わずに出た時）は
    閉路の移動がその方法かを読めないので受け渡しに数えない。once_per_turn は1ターンに1回なので回らない。

    統合（2026-11-26）で増えた束の受け止めもここが担う（発見側のポリシー）:
    - replace の束は「起きたイベントを置き換える」もので、サイクルの一員や
      付け足しにはならない → "replace"
    - move / cast / draw と TICKS 以外の前提イベント（tap・break・
      attack_end 等）は、ゾーン移動の連鎖では満たせない → "event"
      （束自体は正準側に残り、前提閉集合などの消費側は直接読める）
    """
    if getattr(b, "origin", "") == "replace":
        return "replace"
    w = getattr(b, "when", {}) or {}
    if w.get("via") or w.get("unpaid"):
        return "via"
    if getattr(b, "once", False):
        return "once"
    prem = getattr(b, "prem", None)
    if prem is not None and prem.kind not in ("move", "cast", "draw") \
            and prem.kind not in Z.TICKS:
        return "event"
    return None


# ---- 条件の評価 ----

def _count_ok(spec, op, n, ctx):
    """count {zone, owner, filter} op n を、ループの収支と組の中の札で満たせるか。"""
    if not isinstance(spec, dict) or not isinstance(n, int):
        return "unknown"
    owner = spec.get("owner", "you")
    zone = spec.get("zone")
    if not isinstance(zone, str):
        return "unknown"
    flt = spec.get("filter") or {}
    net = ctx["opp_net" if owner == "opp" else "net"]
    inflow = ctx["inflow_opp" if owner == "opp" else "inflow"]
    if "name" in flt:   # 名前で数える条件: 組の中のその札が、ループでそのゾーンへ増えていく時だけ
        name = flt["name"]
        grows = any(z == zone and nm == name for z, nm in ctx["named_in"])
        if op in (">=", ">"):
            return "yes" if grows else "no"
        return "unknown"
    d = net.get(zone, 0)
    if op in (">=", ">"):
        if n <= 1 and zone in inflow:
            return "yes"
        return "yes" if d > 0 or (zone in inflow and n <= ctx.get("seed_cap", 3)) else "no"
    if op in ("<=", "<", "=="):
        if n == 0 and zone in ("deck",) and d < 0:
            return "yes"
        return "yes" if d < 0 else ("unknown" if d == 0 else "no")
    return "unknown"


def cond_state(c, ctx) -> str:
    if c is None:
        return "yes"
    if not isinstance(c, dict):
        return "unknown"
    if "all" in c:
        s = [cond_state(x, ctx) for x in c["all"]]
        return "no" if "no" in s else "unknown" if "unknown" in s else "yes"
    if "any" in c:
        s = [cond_state(x, ctx) for x in c["any"]]
        return "yes" if "yes" in s else "unknown" if "unknown" in s else "no"
    if "not" in c:
        s = cond_state(c["not"], ctx)
        return "unknown" if s == "unknown" else "yes"    # 否定は満たせる向きに倒す（その時点の盤面しだい）
    if "exists" in c:
        return "yes"
    if "is_turn" in c:
        return "yes" if c["is_turn"] in ("you", True) else "no"
    if "cmp" in c:
        a, op, b = c["cmp"]
        if isinstance(a, dict) and "count" in a:
            return _count_ok(a["count"], op, b, ctx)
        return "unknown"
    return "unknown"


def conds_state(conds, ctx) -> str:
    s = [cond_state(c, ctx) for c in conds]
    return "no" if "no" in s else "unknown" if "unknown" in s else "yes"


def _all_ops_with_conds(ops, conds=()):
    for op in ops or []:
        if not isinstance(op, dict):
            continue
        yield op, conds
        if op.get("op") == "if":
            yield from _all_ops_with_conds(op.get("then"), conds + (op.get("cond"),))
            yield from _all_ops_with_conds(op.get("else"), conds + ({"not": op.get("cond")},))
            continue
        for k in ("body", "then", "else", "effect", "instead"):
            if isinstance(op.get(k), list):
                yield from _all_ops_with_conds(op[k], conds)
        for m in op.get("modes") or []:
            yield from _all_ops_with_conds(m, conds)


def win_paths(d) -> list[dict]:
    """自分の特殊勝利: [{conds, when}]。when は誘発・置換の前提（{event, ...}）。"""
    out = []
    for f in (getattr(d, "faces", None) or [d]):
        for ab in f.abilities or []:
            top = tuple(x for x in (ab.get("if"),) if x is not None)
            for key in ("effect", "instead"):
                for op, conds in _all_ops_with_conds(ab.get(key) or []):
                    if op.get("op") == "win" and op.get("player", "you") == "you":
                        out.append({"conds": top + conds, "when": ab.get("when") or {}, "kind": ab.get("kind")})
        for op, conds in _all_ops_with_conds(getattr(f, "spell", None) or []):
            if op.get("op") == "win" and op.get("player", "you") == "you":
                out.append({"conds": conds, "when": {"event": "cast"}, "kind": "spell"})
    return out


def win_state(paths, ctx) -> str:
    """特殊勝利の札が、ループの蓄積で勝利条件に近づくか。yes / no / unknown。"""
    best = "no"
    for p in paths:
        w = p["when"] or {}
        ev = w.get("event")
        if ev == "draw" and not ctx["draws"]:
            continue                     # 引いた時の置換: ループが引かないなら起きない
        s = conds_state(p["conds"], ctx)
        if not p["conds"] and ev not in ("draw", "cast"):
            s = "unknown"                # 条件のない勝ち（出た時に勝つ等）は、ループで近づくとは言えない
        if s == "yes":
            return "yes"
        if s == "unknown":
            best = "unknown"
    return best
