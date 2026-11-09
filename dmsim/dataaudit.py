"""カードデータの不変条件を機械検査する（モデル不使用）。

承認の煙テスト（verify）は「落ちずに回るか」しか見ないため、変換の取りこぼし（進化の型欠落、付与文の脱落など）が
通り抜けて探索結果を歪めた。ここでは原文と構造化データの食い違いを違反コードごとに集める。
既存の違反は data/audit/baseline.json に記録し、テストは「基準線に無い新しい違反」だけを失敗にする（ラチェット）。
基準線は減らす方向にだけ更新する: python tools/audit_cards.py --update-baseline
"""
from __future__ import annotations

import json
import re

_EVO = re.compile(r"(スター)?進化[：:\-－ー―]")
_BREAKS = {"double_breaker": 2, "triple_breaker": 3, "quad_breaker": 4}     # ブレイク数は breaks 修整で表す
_GRANT = re.compile(r"[「『]([^」』]{2,12})[」』]を(?:与える|得る)")


def _dump(*xs) -> str:
    return json.dumps(xs, ensure_ascii=False, default=str)


def audit_card(rules, cd) -> list[str]:
    """1枚の違反コードのリスト。"""
    out: list[str] = []
    types = set(cd.types)
    text = cd.text or ""
    if cd.faces:                    # ツインパクト等は面ごとの検査が要る。今は面の無い札だけを見る
        return out
    if ({"creature", "evolution"} & types) and cd.power is None:
        out.append("creature_no_power")
    if cd.cost is None and not ({"gr", "psychic"} & types):
        out.append("no_cost")
    has_effect = bool(cd.abilities or cd.spell or cd.keywords or cd.sst_spell)
    if text.strip() and not has_effect:
        out.append("text_but_no_effect")
    if _EVO.search(text) and "evolution" not in types and not (cd.neo or cd.grave_evo or cd.s_max):
        out.append("evo_text_no_type")
    if "evolution" in types and not (cd.evolve_from or cd.evolve_any or cd.neo or cd.grave_evo or cd.s_max):
        out.append("evo_no_source")
    # 行頭のキーワード語が keywords に無い（本文の「ブロッカーを得る」等の付与とは区別する）
    ja2id = {v.get("ja"): k for k, v in rules.keywords.items() if v.get("ja")}
    kws = set(cd.keywords)
    for line in re.split(r"[\n/]", text):
        w = line.strip().lstrip("■◆▶").strip()
        k = ja2id.get(w)
        if k and k not in kws:
            out.append(f"kw_line_missing:{k}")
    # 「「X」を与える／得る」があるのに、効果のどこにも X に対応するキーワード付与が無い
    body = _dump(cd.abilities, cd.spell, cd.sst_spell)
    for m in _GRANT.finditer(text):
        k = ja2id.get(m.group(1))
        if k and k not in body and not (k in _BREAKS and f'"breaks": {_BREAKS[k]}' in body):
            out.append(f"grant_dropped:{k}")
    return sorted(set(out))


def audit_rules(rules) -> dict[str, list[str]]:
    """違反コード → カードIDのリスト。"""
    res: dict[str, list[str]] = {}
    for cid, cd in rules.cards.items():
        for code in audit_card(rules, cd):
            res.setdefault(code, []).append(cid)
    from .defs import REPAIRED          # 読み込み時に直した不備も、元データが直るまで違反として数える
    for k, v in REPAIRED.items():
        res.setdefault(k, []).extend(v)
    return {k: sorted(set(v)) for k, v in sorted(res.items())}


def new_violations(found: dict[str, list[str]], baseline: dict[str, list[str]]) -> dict[str, list[str]]:
    out = {}
    for code, ids in found.items():
        extra = sorted(set(ids) - set(baseline.get(code, [])))
        if extra:
            out[code] = extra
    return out
