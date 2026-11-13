"""変換済みカードの棚卸し（読み取りのみ）。
  python tools/measure_coverage.py [--json]
data/cards/{converted,real}.yaml の枚数を、文明・種類・確認状態・効果の種類・未対応申告で数える。
台帳（cards_total）に対する変換率も出す。"""
import argparse, json
from collections import Counter
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
C = ROOT / "data" / "cards"

def load(name):
    p = C / name
    return yaml.safe_load(p.read_text(encoding="utf-8")).get("cards", []) if p.exists() else []

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--json", action="store_true"); a = ap.parse_args()
    cards = {}
    for f in ("converted.yaml", "real.yaml", "real_vocab.yaml", "real_zone.yaml"):
        for c in load(f): cards[c["id"]] = c   # 後勝ち
    st = json.loads((C / "catalog" / "status.json").read_text())
    civ, typ, rev, kinds, kw = Counter(), Counter(), Counter(), Counter(), Counter()
    unsup = vanilla = with_eff = 0
    for c in cards.values():
        civ["/".join(c.get("civs", [])) if len(c.get("civs", [])) > 1 else (c.get("civs") or ["none"])[0]] += 1
        typ["/".join(c.get("types", []))] += 1
        s = c.get("source", {}) or {}
        rev[s.get("review", "none")] += 1
        if s.get("unsupported"): unsup += 1
        for k in c.get("keywords", []) or []: kw[k if isinstance(k, str) else str(k)] += 1
        ab = c.get("abilities") or []
        if ab: with_eff += 1
        for x in ab: kinds[x.get("kind", "?") if isinstance(x, dict) else "?"] += 1
        if not ab and not c.get("keywords"): vanilla += 1
    out = dict(converted_unique=len(cards), catalog_total=st["cards_total"],
               rate=round(len(cards) / st["cards_total"], 4), review=dict(rev), unsupported_cards=unsup,
               with_abilities=with_eff, vanilla_or_text_only=vanilla,
               civs=civ.most_common(), types=typ.most_common(8), ability_kinds=kinds.most_common(10),
               keywords_top=kw.most_common(12))
    print(json.dumps(out, ensure_ascii=False, indent=1) if a.json else "\n".join(f"{k}: {v}" for k, v in out.items()))

if __name__ == "__main__":
    main()
