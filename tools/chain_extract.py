"""検証済み手順の記録から、段階目標の鎖（実行フェーズ）を抽出する試作。

docs/phase-chain-plan.md §4 の段1。入力は make_record 形式のキル記録
（再生で digest が一致するものだけを使う）。各記録を再生しながら
自分のターン開始局面のスナップショットを取り、勝ち軌跡に共通する
通過点を段にする:

- 序盤の段: 全記録でターン開始時に同じゾーンに居た部品
- 中盤の段: 共通ガード（山札の残り>=2、生成側の定数）＋墓地枚数の最小値
- 終盤の段: キルターンの開始時に全記録で揃っていた部品＋墓地枚数の最小値

使い方:
  python tools/chain_extract.py --records 'logs/exhaustive_records/crossturn_*_frontier.json' \
      --out tools/saga_extracted_stages.yaml
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

from dmsim import load_rules  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402

ZONES = ("hand", "bz", "graveyard", "mana", "shield", "deck")
GUARD_DECK_MIN = 2          # 共通ガード（生成側の定数。軌跡からは学習しない）


def snapshot(eng, parts):
    """ターン開始局面の特徴: 部品の所在（ゾーン×部品の枚数）とゾーン総数。"""
    feats = {}
    for z in ZONES:
        ids = [eng.s.cards[c].defn for c in eng.s.zones[z][0]]
        feats[f"{z}:*"] = len(ids)
        for p in parts:
            n = ids.count(p)
            if n:
                feats[f"{z}:{p}"] = n
    return feats


def snapshots_of_record(rules, rec, parts):
    """記録を再生しながら自分のターン開始局面のスナップショットを集める。
    戻り値: [snapshot, ...]（古い順）。digest が一致しない記録は例外。"""
    if rec.get("scenario") is not None:
        eng = sc.build(rules, rec["scenario"])
    else:
        eng = Engine.new_game(rules, rec["decks"], rec["seed"], rec.get("first_player", 0))
    snaps = [snapshot(eng, parts)]
    prev_p = None
    for entry in rec["log"]:
        d = eng.advance()
        if d is None or d["kind"] != entry["kind"] or d["player"] != entry["p"]:
            raise RuntimeError("replay diverged")
        if entry["p"] == 0 and prev_p == 1:
            snaps.append(snapshot(eng, parts))
        eng.answer(entry["choice"])
        prev_p = entry["p"]
    eng.advance()
    if eng.s.digest() != rec["digest"]:
        raise ValueError("digest mismatch")
    if eng.s.result is None or eng.s.result.get("winner") != 0:
        raise ValueError("not a verified win record")
    return snaps


def merge_into(target: dict, feats: dict, keys) -> dict:
    out = {z: dict(v) for z, v in target.items()}
    for k in keys:
        z, i = k.split(":", 1)
        out.setdefault(z, {})[i] = max(out.get(z, {}).get(i, 0), feats[k])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", required=True, help="記録ファイルの glob")
    ap.add_argument("--out", required=True)
    ap.add_argument("--exclude", default="T001,dm01-080,dm01-027",
                    help="部品とみなさないカードID（試験用フィラー）")
    a = ap.parse_args()

    files = sorted(glob.glob(a.records))
    if not files:
        print("no records matched", file=sys.stderr)
        return 1
    exclude = {s.strip() for s in a.exclude.split(",") if s.strip()}
    recs = [json.loads(Path(f).read_text(encoding="utf-8")) for f in files]
    parts = sorted({c for r in recs for deck in (r.get("decks") or [[], []]) for c in deck} - exclude)
    # シナリオ由来の記録は decks が空のことがある。その場合はシナリオの全ゾーンから拾う
    if not parts:
        for r in recs:
            s = r.get("scenario") or {}
            for z in ("hand", "mana", "graveyard", "bz", "shield"):
                parts.extend(s.get(z) or [])
            parts.extend((s.get("deck") or []))
        parts = sorted(set(parts) - exclude)
    print(f"records={len(recs)} parts={parts}", flush=True)

    rules = load_rules()
    print("rules loaded", flush=True)
    all_snaps = []
    for f, r in zip(files, recs):
        try:
            snaps = snapshots_of_record(rules, r, parts)
        except Exception as e:
            print(f"  skip {Path(f).name}: {e}", flush=True)
            continue
        all_snaps.append(snaps)
        print(f"  {Path(f).name}: snapshots={len(snaps)}", flush=True)
    if len(all_snaps) < 2:
        print("not enough usable records", file=sys.stderr)
        return 1

    firsts = [s[0] for s in all_snaps]          # 最初のターン開始（残りターン最大）
    lasts = [s[-1] for s in all_snaps]          # キルターンの開始
    grave_min_first = min(s["graveyard:*"] for s in firsts)
    grave_min_last = min(s["graveyard:*"] for s in lasts)

    def common_present(snaps, zone):
        out = []
        for p in parts:
            k = f"{zone}:{p}"
            if all(s.get(k, 0) >= 1 for s in snaps):
                out.append(k)
        return out

    stages = []
    cur: dict = {}
    early = common_present(firsts, "graveyard")
    if early:
        cur = merge_into(cur, {k: 1 for k in early}, early)
        stages.append({"name": "extract:grave-parts", "target": cur})
    mid = merge_into(cur, {}, [])
    mid.setdefault("deck", {})["*"] = GUARD_DECK_MIN
    if grave_min_first > 0:
        mid.setdefault("graveyard", {})["*"] = grave_min_first
    if mid != cur:
        cur = mid
        stages.append({"name": "extract:build", "target": cur})
    late = [k for k in common_present(lasts, "hand") + common_present(lasts, "graveyard")
            if cur.get(k.split(":", 1)[0], {}).get(k.split(":", 1)[1], 0) < 1]
    fin = merge_into(cur, {k: 1 for k in late}, late)
    if grave_min_last > grave_min_first:
        fin.setdefault("graveyard", {})["*"] = grave_min_last
    if fin != cur:
        cur = fin
        stages.append({"name": "extract:execute-ready", "target": cur})

    evidence = {"records": len(all_snaps), "files": [Path(f).name for f in files],
                "parts": parts, "grave_min_first_turn": grave_min_first,
                "grave_min_kill_turn": grave_min_last, "guard_deck_min": GUARD_DECK_MIN}
    out = Path(a.out)
    out.write_text("# tools/chain_extract.py による抽出（docs/phase-chain-plan.md §4）。"
                   "手で直さず、記録を増やして作り直す。\n"
                   + yaml.safe_dump({"stages": stages, "goal": {}, "evidence": evidence},
                                    allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"wrote {out}: {len(stages)} stages")
    for s in stages:
        print(f"  {s['name']}: {s['target']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
