"""相手のターン中の自分の選択（S3）。札の名前に頼らない最小限の防御。

既定は有効（DMSIM_DEFEND=0 で無効）。2026-11-14 の比較で 2a 相手の負けが減り、2b は変わらないため。無効のときは、自分の決定も相手役の方策が答える従来どおり。
有効なら、自分の決定（相手のターン中）を次の方針で答える:
- block: 攻撃先がプレイヤーで、盾が0（通せば負け）か、この攻撃と残りの相手のアンタップの体のブレイク数の合計が盾の枚数を
  上回る（このターンに止めを刺されうる）ならブロックする（勝てる体があればそれ、無ければ最も安い体）。
  それ以外はバトルに勝てるブロッカーがいる時だけブロックする。攻撃先が自分のクリーチャーでも、勝てる時だけブロックする。
- declare_strigger / declare_sback: 使えるものは全部使う。
- その他（効果の対象などの選択）: 自分の手番と同じ貪欲な並べ方（search.turn.candidates）の先頭。
"""
from __future__ import annotations

import os

from ..engine import Engine

_ENABLED = os.environ.get("DMSIM_DEFEND", "1") == "1"


def enabled() -> bool:
    return _ENABLED


def set_enabled(on: bool) -> None:
    global _ENABLED
    _ENABLED = bool(on)


def _power(eng: Engine, c: int) -> int:
    try:
        return int(eng.chars_ro(c)["power"] or 0)
    except Exception:
        return 0


def _breaks(eng: Engine, c: int) -> int:
    try:
        ch = eng.chars_ro(c)
        return max([ch.get("breaks", 1) or 1] + list(ch.get("break_opts") or ())) + (ch.get("breaks_add") or 0)
    except Exception:
        return 1


def choose_block(eng: Engine, d: dict) -> list[int]:
    opts = d["options"]
    keys = [o["key"] for o in opts]
    nob = keys.index("no_block") if "no_block" in keys else None
    t = eng.s.tasks[-1] if eng.s.tasks else {}
    att = t.get("attacker")
    if t.get("t") != "attack" or not att:
        return [nob if nob is not None else 0]
    me = d["player"]
    ap = _power(eng, att[0])
    blk = [(i, o["cid"]) for i, o in enumerate(opts) if "cid" in o and not o["key"].startswith("guard:")]
    if not blk:
        return [nob if nob is not None else 0]
    wins = sorted([(i, c) for i, c in blk if _power(eng, c) > ap], key=lambda x: _power(eng, x[1]))
    if t.get("target") == "player":
        shields = len(eng.zlist("shield", me))
        others = [c for c in eng.bz_tops(1 - me) if c != att[0] and not eng.s.cards[c].tapped
                  and "creature" in eng.chars_ro(c)["types"]]
        incoming = _breaks(eng, att[0]) + sum(_breaks(eng, c) for c in others)
        if shields == 0 or incoming > shields:
            if wins:
                return [wins[0][0]]
            cheap = min(blk, key=lambda x: (eng.chars_ro(x[1])["cost"] or 0, _power(eng, x[1])))
            return [cheap[0]]
    if wins:
        return [wins[0][0]]
    return [nob if nob is not None else 0]


def defend(eng: Engine, d: dict, weights=None) -> list[int]:
    k = d["kind"]
    if k == "block":
        return choose_block(eng, d)
    if k in ("declare_strigger", "declare_sback"):
        return list(range(len(d["options"])))
    from .turn import candidates
    from .leaf_eval import Weights
    return candidates(eng, d, weights or Weights(), cap=1)[0]


def wrap(opp_pol, me: int, weights=None):
    """有効なら、相手のターン中の自分の決定を defend で答える方策を返す。無効なら opp_pol をそのまま返す。"""
    if not _ENABLED:
        return opp_pol

    def pol(eng: Engine, d: dict) -> list[int]:
        if d["player"] == me and eng.s.active != me:
            return defend(eng, d, weights)
        return opp_pol(eng, d)
    return pol
