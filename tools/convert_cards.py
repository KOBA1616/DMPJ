"""公式テキスト（fetch_cards.py の jsonl）を効果DSLのカード定義に変換する（Claude API を使う）。

    export ANTHROPIC_API_KEY=...
    pip install anthropic
    python tools/convert_cards.py data/cards/raw/official_YYYYMMDD.jsonl --out data/cards/converted.yaml
    python tools/convert_cards.py data/cards/raw/by_product --workers 4 --order short --limit 200   # 大量変換
    python tools/convert_cards.py data/cards/raw --retry-rejects     # 語彙を足したあと、落ちたカードだけやり直す
    python tools/convert_cards.py raw.jsonl --only dm01-001 --dry-run     # プロンプトだけ表示

- 出力は defs.parse_card で検査する。通らなければエラー文を返して1回だけ直させ、それでも駄目なら
  --rejects のファイルに原文とエラーを書いて人に回す。
- 出力カードは source.review: pending。開発者モード（python -m dmsim.devserver）で動かして確かめ、
  approved / rejected を付ける。
- システムプロンプト（スキーマ・語彙・既存カードの例）は全カードで同じなのでキャッシュする。
- 既に data/cards/*.yaml にあるIDは飛ばす（途中で止めても続きから再開できる）。1枚ごとに保存する。
- 結果は --report（既定 data/cards/raw/convert_report.json）に件数・トークン・失敗理由の種類別集計を残す。
  API の一時的な失敗（レート制限など）は rejects に入れず、再実行で拾う。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dmsim import schema  # noqa: E402
from dmsim.defs import DATA, DefError, load_tables, parse_card  # noqa: E402

MODEL = "claude-opus-5-5"

INSTRUCTIONS = """\
あなたはデュエル・マスターズのカードテキストを、シミュレーター dmsim のカード定義（YAML）に変換する。

規則:
- 出力は ```yaml で囲んだ1枚分のカード定義（`cards:` の下の1要素と同じ形。先頭の `- ` は付けない）だけ。
- 語彙は下の JSON Schema・キーワード・マクロ・許可/禁止できる行為の一覧にあるものだけを使う。無い語を作らない。
- キーワード能力（ブロッカー、S・トリガー、W・ブレイカー など）は keywords に書き、説明文の括弧書きは無視する。
- 「〜できない」は static の mod.deny、「〜できる」は mod.allow。「〜してもよい」は op: may。
- 進化は types に evolution を含め evolve_from に進化元の条件を書く。ツインパクトは faces に2面を書く。
- 革命チェンジ・ニンジャ・ストライク等の宣言は kind: declare（既存カードの例に倣う）。
- text には原文から括弧書きの注釈を除いたものを「 / 」区切りで書く。
- 表せない・近似した点は source.notes に日本語で具体的に書く。表せない能力を黙って落とさない。
- 語彙が足りず表せない効果は source.unsupported に [{need: <足せばよい op・語彙の案（英語の識別子）>, text: <該当する原文>}] で書く。
  無い op を effect に書いて検査を落とすより、近似して notes に書き、足りない語彙を unsupported に残す。
- source は {official: <id>, review: pending} とし、必要なら notes を足す。
- 原文の表現が古い（例: 「墓地に置く」）場合も原文どおりに変換し、気づいた点は notes に書く。
"""


def _rules_text(name: str) -> str:
    return (DATA / "rules" / name).read_text(encoding="utf-8")


def system_prompt() -> str:
    """全カード共通の部分（キャッシュされる）。内容が変わらない限り同じ文字列になるようにする。"""
    parts = [INSTRUCTIONS,
             "## JSON Schema\n" + json.dumps(schema.build(), ensure_ascii=False, sort_keys=True),
             *[f"## data/rules/{n}\n{_rules_text(n)}" for n in
               ("zones.yaml", "keywords.yaml", "op_macros.yaml", "permissions.yaml", "turn.yaml")],
             "## 変換済みカードの例（data/cards/real.yaml）\n" + (DATA / "cards" / "real.yaml").read_text(encoding="utf-8")]
    return "\n\n".join(parts)


def user_prompt(row: dict) -> str:
    return "次のカードを変換してください。\n\n" + json.dumps(row, ensure_ascii=False, indent=1)


def extract(text: str) -> dict:
    m = re.search(r"```ya?ml\s*\n(.*?)```", text, re.S)
    raw = yaml.safe_load(m.group(1) if m else text)
    if isinstance(raw, list) and len(raw) == 1:
        raw = raw[0]
    if isinstance(raw, dict) and "cards" in raw:
        raw = raw["cards"][0]
    if not isinstance(raw, dict):
        raise DefError("出力が1枚分のカード定義（mapping）になっていない")
    return raw


def validate(raw: dict, row: dict, tables) -> dict:
    if raw.get("id") != row["id"]:
        raise DefError(f"id が {row['id']} になっていない: {raw.get('id')}")
    parse_card(raw, tables)
    src = raw.setdefault("source", {})
    src["official"] = row["id"]
    src["review"] = "pending"      # LLM の出力は必ず人の確認待ちにする
    return raw


def convert(client, row: dict, tables, sysp: str, effort: str, usage: dict | None = None) -> dict:
    messages = [{"role": "user", "content": user_prompt(row)}]
    err = None
    for attempt in range(2):
        with client.messages.stream(
            model=MODEL, max_tokens=16000,
            system=[{"type": "text", "text": sysp, "cache_control": {"type": "ephemeral"}}],
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
            messages=messages,
        ) as stream:
            msg = stream.get_final_message()
        if msg.stop_reason == "refusal":
            raise DefError("モデルが変換を断った")
        text = "".join(b.text for b in msg.content if b.type == "text")
        u = msg.usage
        if usage is not None:
            usage["input"] += u.input_tokens
            usage["cache_read"] += u.cache_read_input_tokens or 0
            usage["cache_write"] += u.cache_creation_input_tokens or 0
            usage["output"] += u.output_tokens
        print(f"  {row['id']}: in={u.input_tokens} cache_read={u.cache_read_input_tokens} "
              f"cache_write={u.cache_creation_input_tokens} out={u.output_tokens}", file=sys.stderr)
        try:
            return validate(extract(text), row, tables)
        except (DefError, yaml.YAMLError, KeyError, TypeError) as e:
            err = e
            messages += [{"role": "assistant", "content": msg.content},
                         {"role": "user", "content": f"検査でエラーになった。直した定義だけを出力して。\n{e}"}]
    raise DefError(f"2回とも検査を通らなかった: {err}")


def load_rows(inputs: list[str]) -> list[dict]:
    """jsonl のパス・ディレクトリ・glob から原文の行を読む（同じIDは後のものを採る）。rejects は入力に含めない。"""
    files: list[Path] = []
    for spec in inputs:
        p = Path(spec)
        if p.is_dir():
            files += sorted(p.rglob("*.jsonl"))
        elif p.exists():
            files.append(p)
        else:
            files += sorted(Path(".").glob(spec))
    rows: dict[str, dict] = {}
    for f in files:
        if f.name.startswith("rejects"):
            continue
        for s in f.read_text(encoding="utf-8").splitlines():
            if s.strip():
                r = json.loads(s)
                r.pop("error", None)
                rows[r["id"]] = r
    return list(rows.values())


def known_ids(out: Path) -> set[str]:
    ids: set[str] = set()
    for f in (DATA / "cards").glob("*.yaml"):
        ids |= {c["id"] for c in (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("cards") or []}
    return ids


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()] if path.exists() else []


def write_jsonl(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def triage(rejects: list[dict]) -> dict:
    """検査を通らなかった理由を種類ごとに数える（足すべき語彙の見当をつける）。"""
    from report_gaps import categorize
    by_kind: dict[str, dict] = {}
    for r in rejects:
        for part in filter(None, (p.strip() for p in r.get("error", "").split("\n"))):
            kind, term = categorize(part)
            by_kind.setdefault(f"{kind}:{term}", {"n": 0, "ids": []})
            g = by_kind[f"{kind}:{term}"]
            if r["id"] not in g["ids"]:
                g["n"] += 1
                g["ids"].append(r["id"])
    return dict(sorted(by_kind.items(), key=lambda kv: -kv[1]["n"]))


def run(rows: list[dict], client, tables, sysp: str, effort: str, out: Path, rejects_path: Path,
        workers: int = 1, report_path: Path | None = None) -> dict:
    """rows を変換して out に追記する。1枚ごとに保存するので途中で止まっても続きから再開できる。
    検査を通らなかったカードは rejects に（成功したIDは rejects から消す）、APIの一時的な失敗は数えるだけで記録しない。"""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    lock = threading.Lock()
    doc = (yaml.safe_load(out.read_text(encoding="utf-8")) if out.exists() else None) or {}
    cards = doc.get("cards") or []
    rejects = {r["id"]: r for r in read_jsonl(rejects_path)}
    usage = {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0}
    stats = {"ok": 0, "rejected": 0, "api_error": 0}
    api_errors: list[dict] = []

    def save():
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("# convert_cards.py の出力（review: pending）。確認後に real.yaml へ移す。\n"
                       + yaml.safe_dump({"cards": cards}, allow_unicode=True, sort_keys=False), encoding="utf-8")
        write_jsonl(rejects_path, list(rejects.values()))

    def one(r):
        try:
            card = convert(client, r, tables, sysp, effort, usage)
        except DefError as e:
            with lock:
                stats["rejected"] += 1
                rejects[r["id"]] = {**r, "error": str(e)}
                print(f"✗ {r['id']} {r.get('name', '')}: {e}", file=sys.stderr)
                save()
            return
        except Exception as e:      # noqa: BLE001  API の一時的な失敗。カードの問題ではないので rejects には入れない
            with lock:
                stats["api_error"] += 1
                api_errors.append({"id": r["id"], "error": f"{type(e).__name__}: {e}"[:300]})
                print(f"! {r['id']} API失敗: {type(e).__name__}", file=sys.stderr)
            return
        with lock:
            stats["ok"] += 1
            cards.append(card)
            rejects.pop(r["id"], None)
            save()

    if workers > 1:
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(one, rows))
    else:
        for r in rows:
            one(r)
    report = {"requested": len(rows), **stats, "usage": usage, "triage": triage(list(rejects.values())),
              "api_errors": api_errors}
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw", nargs="+", help="原文の jsonl（複数・ディレクトリ・glob 可。data/cards/raw/by_product など）")
    ap.add_argument("--out", default=str(DATA / "cards" / "converted.yaml"))
    ap.add_argument("--rejects", default=str(DATA / "cards" / "raw" / "rejects.jsonl"))
    ap.add_argument("--report", default=str(DATA / "cards" / "raw" / "convert_report.json"),
                    help="実行結果（件数・トークン・失敗の種類別集計）の出力先")
    ap.add_argument("--only", nargs="*", help="このIDだけ変換する")
    ap.add_argument("--retry-rejects", action="store_true", help="前回検査を通らなかったカードだけをもう一度変換する")
    ap.add_argument("--limit", type=int, help="この枚数まで変換する（試運転・予算の上限用）")
    ap.add_argument("--order", choices=["file", "short"], default="file", help="short: 原文の短い順（簡単なものから）")
    ap.add_argument("--workers", type=int, default=1, help="並列数（API のレート制限に合わせる）")
    ap.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--dry-run", action="store_true", help="API を呼ばずにプロンプトと対象枚数を表示する")
    a = ap.parse_args(argv)
    rows = load_rows(a.raw)
    out, rejects_path = Path(a.out), Path(a.rejects)
    if a.only:
        rows = [r for r in rows if r["id"] in a.only]
    if a.retry_rejects:
        failed = {r["id"] for r in read_jsonl(rejects_path)}
        rows = [r for r in rows if r["id"] in failed]
    else:
        done = known_ids(out) | ({c["id"] for c in (yaml.safe_load(out.read_text(encoding="utf-8")) or {}).get("cards") or []}
                                 if out.exists() else set())
        rows = [r for r in rows if r["id"] not in done]
    if a.order == "short":
        rows.sort(key=lambda r: len(r.get("text", "")))
    if a.limit:
        rows = rows[:a.limit]
    sysp = system_prompt()
    if a.dry_run:
        print(sysp)
        for r in rows:
            print("\n---\n" + user_prompt(r))
        print(f"\n対象 {len(rows)} 枚（システムプロンプト {len(sysp)} 文字）", file=sys.stderr)
        return
    import anthropic    # 変換するときだけ必要
    report = run(rows, anthropic.Anthropic(), load_tables(), sysp, a.effort, out, rejects_path,
                 a.workers, Path(a.report))
    print(f"変換 {report['ok']}/{report['requested']} 件、検査を通らず {report['rejected']} 件（{a.rejects}）、"
          f"API失敗 {report['api_error']} 件（再実行で続きから）。不足語彙の集計: python tools/report_gaps.py", file=sys.stderr)


if __name__ == "__main__":
    main()
