"""公式テキスト（fetch_cards.py の jsonl）を効果DSLのカード定義に変換する（Claude API を使う）。

    export ANTHROPIC_API_KEY=...
    pip install anthropic
    python tools/convert_cards.py data/cards/raw/official_YYYYMMDD.jsonl --out data/cards/converted.yaml
    python tools/convert_cards.py raw.jsonl --only dm01-001 --dry-run     # プロンプトだけ表示

- 出力は defs.parse_card で検査する。通らなければエラー文を返して1回だけ直させ、それでも駄目なら
  --rejects のファイルに原文とエラーを書いて人に回す。
- 出力カードは source.review: pending。開発者モード（python -m dmsim.devserver）で動かして確かめ、
  approved / rejected を付ける。
- システムプロンプト（スキーマ・語彙・既存カードの例）は全カードで同じなのでキャッシュする。
- 既に --out にあるIDは飛ばす（途中で止めても続きから再開できる）。
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


def convert(client, row: dict, tables, sysp: str, effort: str) -> dict:
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
        print(f"  {row['id']}: in={u.input_tokens} cache_read={u.cache_read_input_tokens} "
              f"cache_write={u.cache_creation_input_tokens} out={u.output_tokens}", file=sys.stderr)
        try:
            return validate(extract(text), row, tables)
        except (DefError, yaml.YAMLError, KeyError, TypeError) as e:
            err = e
            messages += [{"role": "assistant", "content": msg.content},
                         {"role": "user", "content": f"検査でエラーになった。直した定義だけを出力して。\n{e}"}]
    raise DefError(f"2回とも検査を通らなかった: {err}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw", help="fetch_cards.py の出力（jsonl）")
    ap.add_argument("--out", default=str(DATA / "cards" / "converted.yaml"))
    ap.add_argument("--rejects", default=str(DATA / "cards" / "raw" / "rejects.jsonl"))
    ap.add_argument("--only", nargs="*", help="このIDだけ変換する")
    ap.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--dry-run", action="store_true", help="API を呼ばずにプロンプトを表示する")
    a = ap.parse_args(argv)
    rows = [json.loads(s) for s in Path(a.raw).read_text(encoding="utf-8").splitlines() if s.strip()]
    if a.only:
        rows = [r for r in rows if r["id"] in a.only]
    out = Path(a.out)
    done_doc = yaml.safe_load(out.read_text(encoding="utf-8")) if out.exists() else None
    cards = (done_doc or {}).get("cards") or []
    existing = {c["id"] for c in cards}
    for f in (DATA / "cards").glob("*.yaml"):
        if f.resolve() != out.resolve():
            existing |= {c["id"] for c in (yaml.safe_load(f.read_text(encoding="utf-8")).get("cards") or [])}
    rows = [r for r in rows if r["id"] not in existing]
    sysp = system_prompt()
    if a.dry_run:
        print(sysp)
        for r in rows:
            print("\n---\n" + user_prompt(r))
        return
    import anthropic    # 変換するときだけ必要
    client = anthropic.Anthropic()
    tables = load_tables()
    for r in rows:
        try:
            cards.append(convert(client, r, tables, sysp, a.effort))
        except DefError as e:
            print(f"{r['id']}: {e}", file=sys.stderr)
            with open(a.rejects, "a", encoding="utf-8") as f:
                f.write(json.dumps({**r, "error": str(e)}, ensure_ascii=False) + "\n")
            continue
        out.write_text("# convert_cards.py の出力（review: pending）。確認後に real.yaml へ移す。\n"
                       + yaml.safe_dump({"cards": cards}, allow_unicode=True, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
