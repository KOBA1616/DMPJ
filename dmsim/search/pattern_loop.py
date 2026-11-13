"""採った手順の中から「同じ手順の繰り返しで、1周ごとに資源が一定量ずつ変わる有限ループ」を見つける（S3、P2 タスク4）。

ループ証明書（engine.loop の LoopDetector）は、局面の骨格が元に戻ることを条件にする。サガ型のように1周ごとに引く札が違い、
骨格が戻らないループは証明書が出ない。ここでは実際に指した記録（eng.log）を見て、次の条件をすべて満たす区間を有限ループとして記録する。

骨格の比較の緩め方（設計判断）:
- 1手は (決定の種類, 選んだ札の鍵) で比べる。手札・山札の札（鍵が hand: / deck: で始まるもの）は札の種類を問わない
  （1周ごとに引く札・捨てる札が違ってよい）。それ以外（墓地・場・マナの札、はい/いいえ、攻撃先など）は鍵が完全に一致すること。

誤検出（ただの連続プレイをループと数える）を防ぐ条件:
1. 3周以上、続けて同じ手順であること（MIN_LAPS）。
2. 1周に「錨」があること: 墓地・バトルゾーン・マナの同じ札（同じ鍵）を毎周選んでいる。手札から別々の札を出し続けるだけの
   連続プレイは、手札の鍵がすべて緩められるので錨が無く、数えない。
3. 1周ごとの各ゾーンの枚数（両者の手札・山札・墓地・場・マナ・盾・未タップのマナ）の変化が、すべての周で同じであること。
4. その変化が自分について 0 ではないこと（何も変わらない空回しは数えない）。
5. そのターンに採った手順で、ループ証明書のループを既に使っていれば調べない（同じループを二重に数えない）。
"""
from __future__ import annotations

from ..engine import Engine

MIN_LAPS = 3
MAX_LOG = 4000                  # 1ターンの記録がこれより長ければ調べない（計算量の上限）
LOOSE = ("hand:", "deck:")
ANCHOR = ("graveyard:", "bz:", "mana:")
ZONES = ("hand", "deck", "graveyard", "bz", "mana", "shield")


def _gen(entry: dict) -> tuple:
    return (entry["kind"], tuple(k.split(":", 1)[0] + ":*" if k.startswith(LOOSE) else k for k in entry["keys"]))


def counts(eng: Engine) -> dict[str, int]:
    s = eng.s
    out = {}
    for p in (0, 1):
        for z in ZONES:
            out[f"{z}:{p}"] = len(s.zones[z][p])
        out[f"untapped_mana:{p}"] = sum(1 for c in s.zones["mana"][p] if not s.cards[c].tapped)
    return out


def _diff(a: dict, b: dict) -> dict[str, int]:
    return {k: b[k] - a[k] for k in a if b[k] != a[k]}


def replay_counts(start: Engine, entries: list[dict]) -> list[dict]:
    """start（変更しない）から entries を順に答え、各手の直前と最後の枚数を返す（長さ len(entries)+1）。"""
    e = start.clone()
    out = []
    for ent in entries:
        e.advance()
        out.append(counts(e))
        e.answer(ent["choice"])
    e.advance()
    out.append(counts(e))
    return out


def find(start: Engine, entries: list[dict], me: int, base: int = 0) -> list[dict]:
    """start から entries（このターンに採った手順の記録）を再生し、有限ループを返す。base は entries[0] の eng.log 上の位置。"""
    L = len(entries)
    if L < 2 * MIN_LAPS or L > MAX_LOG:
        return []
    g = [_gen(x) for x in entries]
    snaps = None
    found, i = [], 0
    while i < L:
        best = None
        for n in range(1, (L - i) // MIN_LAPS + 1):
            laps = 1
            while i + (laps + 1) * n <= L and g[i + laps * n:i + (laps + 1) * n] == g[i:i + n]:
                laps += 1
            if laps < MIN_LAPS:
                continue
            lap = g[i:i + n]
            if not any(k.startswith(ANCHOR) for _, keys in lap for k in keys):
                continue
            if snaps is None:
                snaps = replay_counts(start, entries)
            deltas = [_diff(snaps[i + k * n], snaps[i + (k + 1) * n]) for k in range(laps)]
            # 差分が一定の周だけを数える（最後の周で勝ちが決まって途中で止まる場合など、末尾の不一致は切り詰める）
            ok = 1
            while ok < laps and deltas[ok] == deltas[0]:
                ok += 1
            if ok < MIN_LAPS or not any(k.endswith(f":{me}") for k in deltas[0]):
                continue
            if best is None or ok * n > best[1] * best[0]:
                best = (n, ok, deltas[0])
        if best is None:
            i += 1
            continue
        n, laps, delta = best
        end = i + n * laps
        now = snaps[end]
        extra = [now[k] // -d for k, d in delta.items() if d < 0 and k.endswith(f":{me}")]
        found.append({
            "source": "pattern", "verified": True, "evidence": "executed",
            "kind": "finite", "infinite": False,
            "laps": laps, "stocked": laps, "length": n, "delta": delta,
            "stock": {k: v * laps for k, v in delta.items()},
            "limit_est": laps + (min(extra) if extra else 0),     # 見積もり: 減る資源が尽きるまで（確かめていない）
            "win_by": None, "needed": None,
            "log_start": base + i, "log_end": base + end,
            "lap_actions": [list(x[1]) for x in g[i:i + n]],
            "anchor": sorted({k for _, keys in g[i:i + n] for k in keys if k.startswith(ANCHOR)}),
        })
        i = end
    return found
