"""取得済みカードを OpenCode の無料モデルで定期的に変換する（.github/workflows/auto-convert.yml から呼ぶ）。

    python tools/auto_convert.py --limit 20 --interval 6 --model glm-5.3-flash-free

1. 原文（data/cards/raw）のうち未変換のカードを --limit 枚まで変換する（既定はカードID順＝弾ごと。--order short で短い順）。
2. 語彙（スキーマ・data/rules）が前回から変わっていたら、検査落ち(rejects)を --limit 枚まで再試行する。
   変わっていなければ再試行しない（無料枠を無駄に使わないため）。
3. 進捗を data/cards/raw/convert_status.json に書く（gen_status.py が docs/STATUS.md に出す）。
無料モデルの許可リスト検査と課金検知は convert_cards.py のものがそのまま効く。違反したら Fatal で止まる。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import convert_cards as cc  # noqa: E402
from llm_offload import providers  # noqa: E402
from dmsim import schema  # noqa: E402
from dmsim.defs import DATA, load_tables  # noqa: E402

RAW = DATA / "cards" / "raw"
STATUS = RAW / "convert_status.json"


def vocab_hash() -> str:
    h = hashlib.sha256(json.dumps(schema.build(), sort_keys=True, ensure_ascii=False).encode())
    for n in ("zones.yaml", "keywords.yaml", "op_macros.yaml", "permissions.yaml", "turn.yaml"):
        h.update(cc._rules_text(n).encode())
    return h.hexdigest()[:16]


def reasons(rejects: list[dict]) -> dict:
    out: dict[str, int] = {}
    for r in rejects:
        k = r.get("reason") or cc.classify(r.get("error", ""))["reason"]
        out[k] = out.get(k, 0) + 1
    return out


def vocab_gaps(rejects: list[dict]) -> dict:
    """語彙不足(vocab_gap)で落ちたカードから、不足している語彙を {種類:語: カード数} で返す（多い順）。"""
    n: dict[str, int] = {}
    for r in rejects:
        for g in (r.get("gaps") if "gaps" in r else cc.classify(r.get("error", ""))["gaps"]):
            n[g] = n.get(g, 0) + 1
    return dict(sorted(n.items(), key=lambda kv: -kv[1])[:30])


def opencode_usage() -> str:
    """手元の OpenCode の利用量（`opencode stats`：トークン・費用・モデル別）。無料枠の残量や使用割合は CLI/API に公式の手段がないので出せない。"""
    import shutil
    exe = next(filter(None, (shutil.which(n) for n in ("opencode.cmd", "opencode.exe", "opencode"))), None)
    if not exe:
        return "opencode コマンドなし（利用量は取得できない）"
    try:
        r = providers._run_tree([exe, "stats", "--days", "1", "--models", "5"], 30, None)
    except Exception as e:      # noqa: BLE001  報告用なので失敗しても本処理は止めない
        return f"opencode stats を取得できなかった: {type(e).__name__}"
    return (r.stdout or r.stderr).strip()[:1500] or "opencode stats の出力なし"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", default="opencode-cli", choices=["opencode", "opencode-cli"])
    ap.add_argument("--model", default=cc.OPENCODE_DEFAULT)
    ap.add_argument("--interval", type=float, default=6.0)
    ap.add_argument("--workers", type=int, default=1, help="並列数（無料枠は共有枠らしいので増やしすぎない）")
    ap.add_argument("--limit", type=int, default=20, help="1回の実行で扱う最大枚数（--batch ごとに区切って処理する）")
    ap.add_argument("--batch", type=int, default=5, help="1単位の枚数。単位の中がすべてAPI失敗ならその単位を飛ばして次へ")
    ap.add_argument("--max-bad-batches", type=int, default=2, help="API失敗だけの単位がこの回数続いたら打ち切る")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--order", choices=["id", "short"], default="id",
                    help="変換の順番。id: カードID順（弾ごとにまとまる）、short: 原文の短い順（簡単なものから）")
    ap.add_argument("--timeout", type=float, default=300, help="1枚の呼び出しの上限秒。超えた1枚は次の成功で reason: timeout に確定、連続2回なら打ち切り")
    ap.add_argument("--health-timeout", type=float, default=90, help="開始前にモデルへ短い質問をして応答を確認する上限秒（0で省略）。返らなければ何も処理せず終了")
    ap.add_argument("--examples", type=int, default=8, help="プロンプトに入れる変換例の数（原文が近い順）。0で全部（約55,000字→約25,000字に減る）")
    ap.add_argument("--fallbacks", type=int, default=2, help="タイムアウト時に切り替える別の無料モデルの数（0で切り替えなし）")
    a = ap.parse_args(argv)
    providers.OPENCODE_TIMEOUT = a.health_timeout or a.timeout
    out, rej = DATA / "cards" / "converted.yaml", RAW / "rejects.jsonl"
    prev = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    vh = vocab_hash()
    tables = load_tables()
    sysp = (lambda row: cc.system_prompt(row=row, n_examples=a.examples)) if a.examples else cc.system_prompt()
    llm = cc.make_llm(a.provider, a.model, a.interval)
    if hasattr(llm, "alternates"):
        llm.alternates = llm.alternates[:max(0, a.fallbacks)]
    if a.health_timeout and not (hasattr(llm, "recently_ok") and llm.recently_ok()):      # 直前に応答が返っていれば省く
        try:
            llm.complete("", [{"role": "user", "content": "OKとだけ答えて"}], "low", None)
        except cc.Fatal:
            raise
        except Exception as e:      # noqa: BLE001  停止中のモデルに1枚ずつ待たされないよう、最初の1回で見切る
            print(f"ヘルスチェック失敗（モデルが応答しない）: {type(e).__name__}: {str(e)[:200]}。今回は何も処理しない", file=sys.stderr)
            sys.exit(3)
    providers.OPENCODE_TIMEOUT = a.timeout
    ran = {"new": None, "retry": None}
    batches: list[dict] = []
    try:
        rows = cc.load_rows([str(RAW)])
        done = cc.known_ids(out) | ({c["id"] for c in (yaml.safe_load(out.read_text(encoding="utf-8")) or {}).get("cards") or []}
                                    if out.exists() else set())
        failed = {r["id"] for r in cc.read_jsonl(rej)}
        key = (lambda r: r["id"]) if a.order == "id" else (lambda r: len(r.get("text", "")))
        todo = sorted((r for r in rows if r["id"] not in done and r["id"] not in failed), key=key)[:a.limit]
        bad = 0
        for i in range(0, len(todo), a.batch):
            chunk = todo[i:i + a.batch]
            rep = cc.run(chunk, llm, tables, sysp, a.effort, out, rej, workers=a.workers, report_path=RAW / "convert_report.json")
            ran["new"] = {k: (ran["new"] or {}).get(k, 0) + rep[k] for k in ("requested", "ok", "rejected", "api_error")}
            skipped = rep["ok"] == 0 and rep["api_error"] > 0       # 検査落ちは rejects に入り次回から対象外。API失敗は飛ばして次の単位へ
            batches.append({"ids": [r["id"] for r in chunk], "ok": rep["ok"], "rejected": rep["rejected"],
                            "api_error": rep["api_error"], "skipped": skipped})
            bad = bad + 1 if skipped else 0
            if bad >= a.max_bad_batches:
                print(f"API失敗の単位が{bad}回続いたので打ち切る", file=sys.stderr)
                break
        if vh != prev.get("vocab_hash") and failed:
            timed_out = {r["id"] for r in cc.read_jsonl(rej) if r.get("reason") == "timeout"}   # 語彙が変わっても直らないので再試行しない
            retry = [r for r in rows if r["id"] in failed and r["id"] not in timed_out][:a.limit]
            ran["retry"] = cc.run(retry, llm, tables, sysp, a.effort, out, rej, workers=a.workers)
        retried_all = vh == prev.get("vocab_hash") or len(failed) <= a.limit
    except cc.Fatal as e:
        print(f"停止: {e}", file=sys.stderr)
        STATUS.parent.mkdir(parents=True, exist_ok=True)
        STATUS.write_text(json.dumps({**prev, "stopped": str(e)[:300],
                                      "at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                                     ensure_ascii=False, indent=1), encoding="utf-8")
        sys.exit(1)
    converted = len({c["id"] for c in (yaml.safe_load(out.read_text(encoding="utf-8")) or {}).get("cards") or []}) if out.exists() else 0
    rejects = cc.read_jsonl(rej)
    status = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": a.model,
              "raw_total": len(rows), "converted": converted, "rejected": len(rejects),
              "pending": max(0, len(rows) - converted - len(rejects)),
              # 語彙が変わった直後で再試行しきれなかった時は、次回も再試行するよう古いハッシュを残す
              "vocab_hash": vh if retried_all else prev.get("vocab_hash"),
              "vocab_gaps": vocab_gaps(rejects), "reject_reasons": reasons(rejects), "batches": batches,
              "last_run": {k: (v and {x: v[x] for x in ("requested", "ok", "rejected", "api_error")}) for k, v in ran.items()}}
    if isinstance(llm, providers.OpenCodeCLI):
        status["opencode_usage"] = "（直近1日・手元の集計。無料枠の残量・使用割合は公式に取得手段なし。Zen コンソールで確認）\n" + opencode_usage()
        status["model_in_use"] = llm.model
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
