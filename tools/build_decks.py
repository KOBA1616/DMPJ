"""既知コンボ（tuning）の部品で40枚デッキ案を作る。 python tools/build_decks.py [--out data/decks]
core 部品=コスト軽いものは4枚・重いものは2枚、support は3〜4枚、残りは汎用札（同文明の単色・低コスト・進化/呪文でない普通のクリーチャー）。
デッキの組み立ては探索から切り離す（full-auto-discovery-framework）。検証専用(holdout)の部品は使わない。
エンジンに未登録の部品はスキップして warnings に残す。決定的（乱数なし）。"""
import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from dmsim.defs import load_rules  # noqa: E402
import known_combos  # noqa: E402


def copies(cd, role, cap=4):
    if role == "support":
        return 3
    return min(cap, 4 if cd.cost <= 5 else 2)


def filler_pool(rules, civs, banned_names):
    out, names = [], set()
    for i in sorted(rules.cards):
        cd = rules.cards[i]
        if not i.startswith("dm") or cd.name in banned_names or cd.name in names:
            continue
        if cd.types != ["creature"] or cd.cost > 5 or len(cd.civs) != 1 or cd.civs[0] not in civs:
            continue
        names.add(cd.name)
        out.append(i)
    return out


def build(rules, parts_lists, size=40, cap=4):
    """parts_lists: [(id, role)] を順に。同名4枚まで。足りない分は汎用札。"""
    deck, warn, cnt = [], [], {}
    civs = set()
    for pid, role in parts_lists:
        cd = rules.cards.get(pid)
        if cd is None:
            warn.append(f"{pid} は未登録")
            continue
        civs |= set(cd.civs)
        n = min(copies(cd, role, cap), 4 - cnt.get(cd.name, 0), size - len(deck))
        deck += [pid] * n
        cnt[cd.name] = cnt.get(cd.name, 0) + n
    return deck, civs, warn


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data" / "decks"))
    a = ap.parse_args(argv)
    rules = load_rules()
    combos = {c["id"]: c for c in known_combos.load()}
    banned = {p["name"] for c in combos.values() if c["split"] == "holdout" for p in c["parts"]}
    plans = {c: [c] for c in combos if combos[c]["split"] == "tuning"}
    plans["mix_tenmon_saga"] = ["tenmon", "saga"]
    Path(a.out).mkdir(parents=True, exist_ok=True)
    for name, cids in plans.items():
        parts, seen = [], set()
        for c in cids:
            for p in combos[c]["parts"]:
                if p["id"] not in seen:
                    seen.add(p["id"])
                    parts.append((p["id"], p["role"]))
        deck, civs, warn = build(rules, parts, cap=2 if len(cids) > 1 else 4)
        # 部品を2組以上混ぜるときは枠が足りないので、core を優先して先頭から詰める（build が打ち切る）
        cnt = {}
        for i in deck:
            cnt[rules.cards[i].name] = cnt.get(rules.cards[i].name, 0) + 1
        pool = filler_pool(rules, civs, banned)
        k = 0
        while len(deck) < 40 and pool:
            i = pool[(k * 7) % len(pool)]
            k += 1
            nm = rules.cards[i].name
            if cnt.get(nm, 0) >= 4 or k > 400:
                continue
            deck.append(i)
            cnt[nm] = cnt.get(nm, 0) + 1
        assert len(deck) == 40, (name, len(deck))
        doc = {"name": name, "combos": cids, "warnings": warn, "deck": deck}
        (Path(a.out) / f"{name}.yaml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(name, len(deck), "distinct", len(set(deck)), warn)


if __name__ == "__main__":
    main()
