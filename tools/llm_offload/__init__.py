"""機械的な作業を無料モデルに回す共通ライブラリ（CLI は tools/offload.py）。

    from llm_offload import ask
    r = ask("summarize-log", text)        # 無料モデルで要約。駄目なら Escalate（= Claude で処理してよい合図）

- 無料モデルのみ。許可リスト検査・費用検知は providers.py（課金が発生しうる経路は作らない）。
- 入力は秘密情報を伏せ字にし、長ければ前後を残して切る。送るのは公開してよい内容だけ（リポジトリは非公開なので、
  非公開ソースを外部APIへ送ってよいかは koba の判断。既定では diff / ログ / 公式テキストのみを想定）。
- 1日の呼び出し数に上限（既定200）。同じ入力は .cache/llm_offload に保存して再利用する。
- 失敗（枠切れ・レート制限・応答なし）は Escalate にして呼び出し側へ返す。黙って課金経路へ切り替えない。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from .providers import (OPENCODE_DEFAULT, OPENCODE_FREE_MODELS, BadResponse, Chain, Fatal, GeminiLLM, LLM7LLM, OpenRouterLLM,  # noqa: F401
                        OpenCodeCLI, OpenCodeLLM)

ROOT = Path(__file__).resolve().parent.parent.parent
CACHE = ROOT / ".cache" / "llm_offload"
DAILY_LIMIT = 200
MAX_CHARS = 60000

TASKS = {
    "summarize-log": "次のログ（テスト・ビルド・実行出力）を日本語で要約して。失敗したテスト名と原因の見当、"
                     "最初に直すべき箇所を箇条書きで。ログに無いことは推測と明記する。",
    "review-diff": "次の git diff を一次レビューして。バグの疑い・抜け・命名や重複の問題を、"
                   "ファイル:行 つきで重要度の高い順に最大10件、日本語で。問題がなければ「指摘なし」だけ。",
    "summarize": "次の文章を日本語で、要点だけ箇条書き10行以内に要約して。",
    "docstring": "次のコードに対する簡潔な日本語の説明（何をするか・入出力・注意点）を、docstring に貼れる形で書いて。",
    "classify": "次の項目を、指示に書かれた分類に振り分けて、JSON のみで返して。",
}


class Escalate(Exception):
    """無料モデルでは済まなかった。Claude（または人）で処理してよい。"""


@dataclass
class Result:
    text: str
    cached: bool
    model: str


_SECRET = re.compile(r"(?i)(sk-[A-Za-z0-9_\-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
                     r"Bearer\s+[A-Za-z0-9._\-]{16,}|(?:api[_-]?key|token|secret|password)\s*[=:]\s*\S{8,})")


def scrub(text: str) -> str:
    """キーや環境変数の値らしきものを伏せる（外部APIに送る前・ログに出す前）。"""
    text = text or ""
    for name in ("OPENCODE_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN"):
        v = os.environ.get(name)
        if v and len(v) >= 8:
            text = text.replace(v, "***")
    return _SECRET.sub("***", text)


def clip(text: str, limit: int = MAX_CHARS) -> str:
    if len(text) <= limit:
        return text
    h = limit * 2 // 3
    t = limit - h
    return text[:h] + f"\n…（{len(text) - limit}文字省略）…\n" + text[-t:]


def _usage_path(cache: Path) -> Path:
    return cache / "usage.json"


def _spend(cache: Path, limit: int) -> int:
    """今日の呼び出し数を1増やす。上限なら Escalate。"""
    p, today = _usage_path(cache), datetime.date.today().isoformat()
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        d = {}
    n = d.get(today, 0)
    if n >= limit:
        raise Escalate(f"今日の呼び出し上限({limit})に達した")
    cache.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({today: n + 1}))
    return n + 1


def make_llm(provider: str = "opencode-cli", model: str | None = None, interval: float = 3.0):
    if provider == "opencode":
        return OpenCodeLLM(model or OPENCODE_DEFAULT, interval)
    if provider == "opencode-cli":
        llm = OpenCodeCLI(model or OPENCODE_DEFAULT, interval)
        # OpenCode 全滅時の切り替え先。Gemini・OpenRouter はキーがあるときだけ、LLM7 は匿名で（DMPJ_NO_LLM7=1 で無効）
        llm.external = Chain(GeminiLLM(interval) if os.environ.get("GEMINI_API_KEY") else None,
                             OpenRouterLLM(interval) if os.environ.get("OPENROUTER_API_KEY") else None,
                             None if os.environ.get("DMPJ_NO_LLM7") else LLM7LLM(interval))
        return llm
    raise Fatal(f"provider {provider!r} は無料経路ではない（opencode / opencode-cli のみ）")


def ask(task: str, text: str, *, instruction: str | None = None, provider: str = "opencode-cli",
        model: str | None = None, llm=None, cache: Path | None = None, daily_limit: int = DAILY_LIMIT,
        max_chars: int = MAX_CHARS, use_cache: bool = True) -> Result:
    """task（TASKS のキー）の指示で text を処理する。失敗は Escalate。Fatal（課金の兆候）は握りつぶさず上げる。"""
    if instruction is None and task not in TASKS:
        raise ValueError(f"未知のタスク {task!r}（{sorted(TASKS)}）")
    inst = instruction or TASKS[task]
    body = clip(scrub(text), max_chars)
    cache = cache or CACHE
    llm = llm or make_llm(provider, model)
    model_name = getattr(llm, "model", "?")
    key = hashlib.sha256(json.dumps([model_name, inst, body], ensure_ascii=False).encode()).hexdigest()[:24]
    f = cache / f"{key}.txt"
    if use_cache and f.exists():
        return Result(f.read_text(encoding="utf-8"), True, model_name)
    _spend(cache, daily_limit)
    try:
        out = llm.complete("あなたは開発作業の補助役。指示に従い、結果だけを簡潔に出力する。",
                           [{"role": "user", "content": f"{inst}\n\n---\n{body}"}], "low", None)
    except Fatal:
        raise
    except Exception as e:   # noqa: BLE001  枠切れ・レート制限・応答なしなど
        raise Escalate(f"{type(e).__name__}: {scrub(str(e))[:200]}") from None
    out = scrub(out).strip()
    if not out:
        raise Escalate("空の応答")
    cache.mkdir(parents=True, exist_ok=True)
    f.write_text(out, encoding="utf-8")
    return Result(out, False, model_name)


def digest_pytest(text: str, tail: int = 15, limit: int = 4000) -> str:
    """LLM を使わずに pytest 出力を縮める（失敗行・エラー行・要約行だけ）。"""
    keep = [ln for ln in text.splitlines()
            if re.match(r"(FAILED|ERROR)\b", ln) or re.match(r"E\s", ln) or re.search(r"\b\d+ (failed|passed|error)", ln)
            or re.match(r"_{3,} .* _{3,}$", ln)]
    lines = keep + ["--- 末尾 ---"] + text.splitlines()[-tail:]
    out = "\n".join(dict.fromkeys(lines))
    return out if len(out) <= limit else out[:limit] + "\n…（省略）"


def affected_tests(changed: list[str], tests_dir: Path | None = None) -> list[str] | None:
    """変更ファイルに関係するテストファイルを返す。見当がつかない・全体に効く変更なら None（= 全部回す）。"""
    tests_dir = tests_dir or ROOT / "tests"
    all_tests = sorted(tests_dir.glob("test_*.py"))
    core = {"dmsim/defs.py", "dmsim/state.py", "dmsim/engine/core.py", "dmsim/engine/events.py", "tests/conftest.py"}
    hit: set[str] = set()
    for c in changed:
        if c in core or c.startswith("data/rules/"):
            return None
        p = Path(c)
        if c.startswith("tests/") and p.name.startswith("test_"):
            hit.add(c)
        elif p.suffix == ".py":
            stem = p.stem
            for t in all_tests:
                if re.search(rf"\b{re.escape(stem)}\b", t.read_text(encoding="utf-8")):
                    hit.add(f"tests/{t.name}")
        elif p.suffix in (".yaml", ".yml") and c.startswith("data/"):
            return None
    return sorted(hit) or None
