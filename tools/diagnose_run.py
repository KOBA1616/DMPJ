"""1本で「回す→集計→失敗局の分類」をする診断コマンド（Claude が結果ファイルを手で数えなくて済むように）。

  python tools/diagnose_run.py saga --games 40 --jobs 4 --out diag_saga.md

- シードごとに tools/route_macro_run.py を別プロセスで回す（--timeout 秒を超えたら外して数える）。
- 集計: 入口・入口4T以内・段2・3〜4Tキル・殴り勝ち。
- 分類: 入口に届いて段2なしの局について、中核の札（デッキで4枚以上の札のうち経路データに出る札）を
  「マナに置いた」「一度も出していない」で数え、いちばん多い原因を先頭に出す。
- 出力は Markdown 1ファイル（数十行）。--json で行データも残す。判断（原因の見立て・直し方）はしない。
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_seed(entry, deck, route, seed, opp, timeout, tmp):
    out = Path(tmp) / f"s{seed}.json"
    if out.exists():      # --parts で前回までに終わったシードは回し直さない（途中で切れても続きから）
        d = json.loads(out.read_text())
        rows = d.get("rows", [])
        if rows:
            rows[0]["_deck_list"] = d.get("deck_list", [])
            return seed, rows[0], None
    cmd = [sys.executable, str(ROOT / "tools/route_macro_run.py"), entry, "--keep", "--games", "1",
           "--start", str(seed), "--opp-level", str(opp), "--out", str(out)]
    if deck:
        cmd += ["--deck", deck]
    if route:
        cmd += ["--route", route]
    env = dict(os.environ, PYTHONPATH=str(ROOT) + os.pathsep + str(ROOT / "tools"), DMSIM_WHY="1")
    try:
        subprocess.run(cmd, cwd=ROOT, env=env, timeout=timeout, capture_output=True)
    except subprocess.TimeoutExpired:
        return seed, None, "timeout"
    if not out.exists():
        return seed, None, "error"
    d = json.loads(out.read_text())
    rows = d.get("rows", [])
    if rows:
        rows[0]["_deck_list"] = d.get("deck_list", [])
    return seed, (rows[0] if rows else None), (None if rows else "error")


class _Keep:
    def __init__(self, d):
        self.d = d

    def __enter__(self):
        return self.d

    def __exit__(self, *a):
        return False


def card_counts(keys, prefix):
    c = collections.Counter()
    for k, v in keys.items():
        if k.startswith(prefix):
            c[k[len(prefix):].split(":")[0]] += v
    return c


WHY = {"a_not_reached": "届いていない（手札にも墓地にも来ない）", "b_cannot_pay": "届いたが払えない（出す手が合法手に無い: マナ・文明・進化元）",
       "c_not_chosen": "払えたのに選ばない（探索）"}


def classify(rows, core, names=None):
    """入口あり・段2なしの局で、最後まで場に出なかった中核の札を理由（a/b/c）ごとに数える。1局は複数に入りうる。"""
    names = names or {}
    causes = collections.defaultdict(list)
    for r in rows:
        if r.get("entry_turn") is None or r.get("stage2"):
            continue
        w = r.get("why") or {}
        hit = False
        for cid in core:
            if cid in w:
                x = w[cid]
                causes[f"{names.get(cid, cid)}: {WHY[x['why']]}"].append(r["seed"]); hit = True
        if not hit:
            causes["中核は全部場に出た（勝ち切れない理由は別）" if w else "理由の記録なし（DMSIM_WHY 無しで回した結果）"].append(r["seed"])
    return sorted(causes.items(), key=lambda x: -len(x[1]))


def core_cards(deck_list, route):
    cnt = collections.Counter(deck_list)
    txt = ""
    if route:
        p = ROOT / "data/loops/route" / f"{route}.yaml"
        txt = p.read_text(encoding="utf-8") if p.exists() else ""
    names = [c for c, n in cnt.items() if n >= 4]
    return [c for c in names if not txt or c in txt] or names


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("entry")
    ap.add_argument("--deck")
    ap.add_argument("--route", default=None)
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--opp-level", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--out", default="diag.md")
    ap.add_argument("--json", help="行データ（小分けの結果）を書く。--merge で合算できる")
    ap.add_argument("--parts", help="1局ごとの結果を置くフォルダ。指定すると残り、再実行で続きから回る（小分け）")
    ap.add_argument("--merge", nargs="+", help="対局は回さず、小分けで出た --json を合算して表だけ作る")
    a = ap.parse_args(argv)
    route = a.route or (f"{a.entry}_v3" if a.entry == "saga" else None)
    seeds = range(a.start, a.start + a.games)
    rows, dropped = [], {}
    if a.merge:
        for f in a.merge:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
            rows += d["rows"]
            dropped.update({int(k): v for k, v in d["dropped"].items()})
        seeds = []
    if a.parts:
        Path(a.parts).mkdir(parents=True, exist_ok=True)
    with (tempfile.TemporaryDirectory() if not a.parts else _Keep(a.parts)) as tmp, cf.ThreadPoolExecutor(a.jobs) as ex:
        for seed, row, err in ex.map(lambda s: run_seed(a.entry, a.deck, route, s, a.opp_level, a.timeout, tmp), seeds):
            if row is None:
                dropped[seed] = err
            else:
                rows.append(row)
    rows.sort(key=lambda r: r["seed"])
    deck_list = []
    if rows:
        # route_macro_run の出力にあるデッキ一覧を使う（--deck 省略時の既定デッキにも合う）
        deck_list = rows[0].get("_deck_list", [])
    if not deck_list and a.deck:
        import yaml
        deck_list = yaml.safe_load(open(ROOT / a.deck, encoding="utf-8")).get("deck", [])
    core = core_cards(deck_list, route) if deck_list else []
    e = [r["entry_turn"] for r in rows if r.get("entry_turn") is not None]
    s2 = [(r["seed"], r.get("win_turn")) for r in rows if r.get("stage2")]
    k34 = sum(1 for r in rows if r.get("kill") and r.get("win_turn") and r["win_turn"] <= 4)
    L = [f"# 診断 {a.entry}（デッキ {a.deck or '既定'}、相手 段階{a.opp_level}）", "",
         f"- 局数 {len(rows)}（外した {len(dropped)}: {dict(sorted(dropped.items()))}）",
         f"- 入口 {len(e)}（4T以内 {sum(x <= 4 for x in e)}、ターン別 {dict(sorted(collections.Counter(e).items()))}）",
         f"- 段2 {len(s2)} {s2}",
         f"- 3〜4Tキル {k34}、殴り勝ち {sum(1 for r in rows if r.get('beat'))}", "",
         "## 入口に届いて段2なしの局の分類（多い順、1局が複数に入りうる）", ""]
    try:
        from dmsim import load_rules
        R = load_rules()
        names = {c: R.cards[c].name for c in core if c in R.cards}
    except Exception:  # noqa: BLE001  名前が引けなくても表は出す
        names = {}
    for c, ss in classify(rows, core, names):
        L.append(f"- {len(ss)}局: {c} — seed {ss}")
    L += ["", f"中核の札: {core}"]
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    if a.json:
        slim = [{**{k: v for k, v in r.items() if k != "my_keys"},
                 "why": r.get("why"), "my_keys": {k: v for k, v in (r.get("my_keys") or {}).items() if k.startswith(("charge|", "main|play:"))}} for r in rows]
        Path(a.json).write_text(json.dumps({"rows": slim, "dropped": dropped}, ensure_ascii=False), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
