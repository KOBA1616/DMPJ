"""実カードの一括検証ハーネス。

各カードを「試す」シナリオ（scenario.try_card）で局面を作り、簡易方策で自動的に数百手回す。
- エンジンの例外・形状検査（DMSIM_CHECK/ check=True）・決定上限の超過を「動かない証拠」として検出する
- approve / reject の判断材料にする（自動で review を書き換えない。devserver から一覧で見る）
"""
from __future__ import annotations

import traceback

from . import scenario as sc
from .engine import Engine


def greedy_policy(eng: Engine, d: dict) -> list[int]:
    """検証用方策。P0 はチャージ・プレイ・攻撃・yes を積極的に選び（動けるものは動かす）、
    P1 とその他の選択は最小限（何もしない系を優先）。"""
    keys = [o["key"] for o in d["options"]]
    if d["player"] == 0:
        if d["kind"] in ("main", "charge", "attack"):
            i = next((j for j, o in enumerate(d["options"]) if o["key"] != "pass"), None)
            if i is not None:
                return [i]
        for k in ("yes",):          # 使える効果は使う
            if k in keys:
                return [keys.index(k)]
    for k in ("pass", "no_block", "no", "decline"):
        if k in keys:
            return [keys.index(k)]
    return list(range(d["min"]))


def verify_card(rules, card_id: str, steps: int = 400) -> dict:
    """card_id の「試す」シナリオを自動回しして結果を返す。

    {"id", "name", "status": "ok" | "error", "detail"}。detail は exception の要約や到達手数。
    シナリオや初期化が失敗した場合も error にする（そこが検出すべき点だから）。
    """
    name = rules.cards[card_id].name if card_id in rules.cards else card_id
    info = {"id": card_id, "name": name, "status": "ok", "detail": ""}
    try:
        spec = sc.try_card(rules, card_id)
        eng = sc.build(rules, spec, check=True)
        d = None
        for i in range(steps):
            d = eng.advance()
            if d is None:
                break
            eng.answer(greedy_policy(eng, d))
        else:
            info["status"] = "error"
            info["detail"] = f"決定上限 {steps} 手を超えた（ループの疑い）。turn={eng.s.turn} step={eng.s.step}"
            return info
        n = eng.log[-1]["n"] if eng.log and "n" in eng.log[-1] else len(eng.log)
        info["detail"] = f"{len(eng.log)}手・turn {eng.s.turn} まで正常に回った（result={eng.s.result}）"
    except Exception:
        info["status"] = "error"
        info["detail"] = traceback.format_exc(limit=2).strip().replace("\n", " | ")
    return info


def verify_all(rules, card_ids=None, steps: int = 400) -> list[dict]:
    """複数カードを一括検証して結果リストを返す。指定なければ real.yaml 由来の全カード。"""
    if card_ids is None:
        card_ids = sorted(cid for cid, d in rules.cards.items() if d.source)
    return [verify_card(rules, cid, steps=steps) for cid in card_ids]
