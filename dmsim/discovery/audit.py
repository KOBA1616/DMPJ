"""変換の監査（U-7）: カードの原文から予測した資源増減と、エンジンで測った値を突き合わせる。

原文（text）から、「このクリーチャーが出た時」の無条件の効果のうち、ドロー枚数と手札を捨てる枚数を読み取って予測する。
エンジンでそのカードを手札から出して、山札・墓地の増減を測る。ずれたら、変換データの不具合（誘発の二重登録など）の疑い。
条件つき（てもよい・場合・なら・ごとに・かわりに）の文は予測しない（不明として除く）。
"""
from __future__ import annotations

import re
import unicodedata

CIP = re.compile(r"このクリーチャーが(?:バトルゾーンに)?出た時[、,]?(.*)")
SKIP_WORDS = ("てもよい", "場合", "なら", "ごとに", "かわりに", "相手の", "選び", "選ぶ", "ターン", "まで")


def predict_cip(text: str) -> dict | None:
    """原文から cip のドロー枚数・捨てる枚数を予測する。読み取れない／条件つきなら None。"""
    t = unicodedata.normalize("NFKC", text or "")
    draws = discards = 0
    seen = False
    for line in t.splitlines():
        m = CIP.search(line)
        if not m:
            continue
        body = m.group(1)
        if any(w in body for w in SKIP_WORDS):
            return None
        d = re.findall(r"カードを(\d+)枚引く", body)
        x = re.findall(r"手札を(\d+)枚捨てる", body)
        rest = re.sub(r"カードを\d+枚引く|自分の手札を\d+枚捨てる|手札を\d+枚捨てる|[、。,\s]|その後|そして", "", body)
        if rest:                                   # 読み取れない効果が混ざる
            return None
        draws += sum(int(v) for v in d)
        discards += sum(int(v) for v in x)
        seen = True
    return {"draws": draws, "discards": discards} if seen else None


def measure_cip(rules, cid: str, mana=("T001", "T003", "T004", "T005", "T008") * 2, hand_extra: int = 6) -> dict | None:
    """cid を手札から出し、山札・墓地の増減を測る。出せなければ None。"""
    from .. import scenario
    spec = {"p0": {"hand": [cid] + ["T001"] * hand_extra, "mana": list(mana)}, "p1": {"bz": ["T001"]}, "seed": 1, "deck_size": 30}
    e = scenario.build(rules, spec)
    s = e.s
    hand0, gy0 = len(s.zones["hand"][0]), len(s.zones["graveyard"][0])
    played = False
    for _ in range(60):
        d = e.advance()
        if d is None or (played and d["kind"] in ("main", "charge", "attack")):   # 出した後に次の行動の選択に戻ったら、出た時の効果は終わっている
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and not played:
            k = next((k for k in keys if k.startswith(f"play:{cid}")), None)
            if k is None:
                return None
            e.answer([keys.index(k)])
            played = True
        elif d["kind"] == "charge" and not played:
            e.answer([keys.index("pass")] if "pass" in keys else [0])
        elif d["kind"] in ("yes_no", "may"):
            e.answer([keys.index("yes")] if "yes" in keys else [0])
        else:
            e.answer(list(range(d["min"])))
    if not played:
        return None
    discards = len(s.zones["graveyard"][0]) - gy0
    # 引いた枚数 = 手札の増減（出した1枚を除く）+ 捨てた枚数。EXライフなど山札の上を盾にするカードに惑わされない
    return {"draws": len(s.zones["hand"][0]) - (hand0 - 1) + discards, "discards": discards}


def audit_card(rules, cid: str) -> dict | None:
    cd = rules.cards[cid]
    f = cd.face(None) if hasattr(cd, "face") else cd
    if "creature" not in f.types or getattr(f, "evolve_from", None) or getattr(cd, "evolve_from", None):
        return None
    pred = predict_cip(cd.text)
    if pred is None:
        return None
    got = measure_cip(rules, cid)
    if got is None:
        return {"id": cid, "predicted": pred, "measured": None, "ok": None}
    return {"id": cid, "predicted": pred, "measured": got, "ok": pred == got}


def audit_all(rules, cards: list[str] | None = None, limit: int | None = None) -> dict:
    cards = cards or [c for c in rules.cards if not c.startswith("T")]
    rows = []
    for c in cards:
        try:
            r = audit_card(rules, c)
        except Exception as ex:
            r = {"id": c, "error": f"{type(ex).__name__}: {str(ex)[:60]}"}
        if r:
            rows.append(r)
            if limit and len(rows) >= limit:
                break
    return {"checked": len(rows), "mismatches": [r for r in rows if r.get("ok") is False],
            "unmeasured": [r for r in rows if r.get("ok") is None and "error" not in r], "errors": [r for r in rows if "error" in r], "rows": rows}
