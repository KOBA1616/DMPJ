"""無料モデル（OpenCode）の呼び出し部。課金事故防止の検査（許可リスト・費用の兆候・課金系エラー）はここに集約する。

convert_cards.py など全ツールがこれを使う。課金が発生しうる経路はここに作らない。
"""
from __future__ import annotations

import json
import re
from pathlib import Path


class BadResponse(ValueError):
    """応答に本文がないなど、モデルの出力が使えない。"""


class Fatal(Exception):
    """続行すると課金や無駄打ちになるエラー。実行全体を止める。"""


# --- OpenCode（無料モデル専用） -------------------------------------------------------------
# 課金事故防止: この許可リストにあるモデルIDだけを、この固定URLにだけ送る。リスト外は実行前に拒否する。
# 新しい無料モデルを使うときは、公式 https://opencode.ai/docs/zen/ で $0 と確認してここに足す。
OPENCODE_URL = "https://opencode.ai/inference/openai/v1/chat/completions"
OPENCODE_FREE_MODELS = frozenset({
    "glm-5.3-flash-free", "deepseek-v4.1-flash-free", "longcat-2.5-preview-free",
})
OPENCODE_DEFAULT = "glm-5.3-flash-free"
OPENCODE_TIMEOUT = 150   # 1回の呼び出しの上限秒。無応答時に1枚10分も待たない(2026-10-25: 600秒x3回で30分空回り)


def check_free_model(model: str):
    if model not in OPENCODE_FREE_MODELS or not model.endswith("-free"):
        raise Fatal(f"{model!r} は無料モデルの許可リストにない（許可: {sorted(OPENCODE_FREE_MODELS)}）。課金を避けるため実行しない")


class OpenCodeLLM:
    name = "opencode"

    def __init__(self, model: str = OPENCODE_DEFAULT, min_interval: float = 3.0, key: str | None = None):
        import os
        import threading
        check_free_model(model)
        self.key = key or os.environ.get("OPENCODE_API_KEY", "")
        if not self.key:
            raise Fatal("環境変数 OPENCODE_API_KEY が未設定")
        self.model, self.min_interval = model, min_interval
        self._last, self._lock = 0.0, threading.Lock()

    def _wait(self):
        import time
        with self._lock:
            time.sleep(max(0.0, self._last + self.min_interval - time.monotonic()))
            self._last = time.monotonic()

    def _post(self, payload: dict) -> dict:
        import time
        import urllib.error
        import urllib.request
        data = json.dumps(payload).encode()
        for attempt in range(4):
            self._wait()
            req = urllib.request.Request(OPENCODE_URL, data, {
                "Authorization": f"Bearer {self.key}", "Content-Type": "application/json",
                "User-Agent": "dmpj-convert/1.0"})   # 既定の Python-urllib はCloudflareに403(1010)で弾かれる
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")[:300].replace(self.key, "***")
                if e.code == 402 or re.search(r"(?i)billing|credit|balance|payment|insufficient|FreeTierError", body):
                    raise Fatal(f"課金・無料枠に関するエラーなので停止する: HTTP {e.code} {body}") from None
                if e.code in (401, 403):
                    raise Fatal(f"認証/権限エラー: HTTP {e.code} {body}") from None
                if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                    time.sleep(10 * 2 ** attempt)
                    continue
                raise RuntimeError(f"HTTP {e.code}") from None
        raise RuntimeError("リトライ上限")

    def complete(self, sysp: str, messages: list[dict], effort: str, usage: dict | None) -> str:
        resp = self._post({"model": self.model, "max_tokens": 16000, "temperature": 0.2,
                           "messages": [{"role": "system", "content": sysp}, *messages]})
        # 課金の兆候: 応答に 0 でない費用が載っていたら止める
        for k in ("cost", "total_cost"):
            if (resp.get(k) or (resp.get("usage") or {}).get(k) or 0) > 0:
                raise Fatal(f"応答に費用({k})が含まれている。無料でなくなった可能性があるので停止する")
        if resp.get("model") and not str(resp["model"]).removeprefix("opencode/").endswith("-free"):
            raise Fatal(f"応答のモデルが無料モデルでない: {resp['model']}")
        u = resp.get("usage") or {}
        if usage is not None:
            usage["input"] += u.get("prompt_tokens", 0)
            usage["output"] += u.get("completion_tokens", 0)
        try:
            return resp["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise BadResponse("応答に本文がない") from None


class OpenCodeCLI:
    """OpenCode CLI（opencode run）経由。無料枠は「OpenCode の中からのみ」使えるため、API 直叩きが拒否されるときの経路。
    キー不要。モデルは同じ許可リストで検査する。"""
    name = "opencode-cli"

    def __init__(self, model: str = OPENCODE_DEFAULT, min_interval: float = 3.0):
        import threading
        check_free_model(model)
        self.model, self.min_interval = model, min_interval
        self._last, self._lock = 0.0, threading.Lock()

    def complete(self, sysp: str, messages: list[dict], effort: str, usage: dict | None) -> str:
        import shutil
        import subprocess
        import tempfile
        import time
        prompt = sysp + "\n\n" + "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in messages)
        with self._lock:
            time.sleep(max(0.0, self._last + self.min_interval - time.monotonic()))
            self._last = time.monotonic()
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "prompt.md"
            f.write_text(prompt, encoding="utf-8")
            # Windows の npm 版は拡張子なしの sh スクリプトと opencode.cmd が並ぶ。拡張子なしは起動できない(WinError 193)ので .cmd/.exe を先に探す
            exe = next(filter(None, (shutil.which(n) for n in ("opencode.cmd", "opencode.exe", "opencode"))), None)
            if not exe:
                raise FileNotFoundError("opencode コマンドが PATH にない（npm i -g opencode-ai）")
            try:
                r = subprocess.run([exe, "run", "-m", f"opencode/{self.model}", "--format", "json",
                                    "添付ファイルの指示に従い、最後の [user] への答えだけを出力して。", "-f", str(f)],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   timeout=OPENCODE_TIMEOUT, cwd=d)
            except subprocess.TimeoutExpired:
                raise RuntimeError(f"opencode が{OPENCODE_TIMEOUT}秒以内に終わらなかった（TimeoutExpired）")
        if re.search(r"(?i)FreeTierError|billing|credit balance|insufficient|payment", r.stdout + r.stderr):
            raise Fatal(f"課金・無料枠に関するエラーなので停止する: {(r.stdout + r.stderr)[:300]}")
        texts, err = [], None
        for line in r.stdout.splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") == "error":
                err = json.dumps(ev.get("error"), ensure_ascii=False)[:300]
            elif ev.get("type") == "text":
                texts.append((ev.get("part") or {}).get("text", ""))
        if err and not texts:
            raise RuntimeError(f"opencode error: {err}")
        if usage is not None:
            usage["input"] += len(prompt) // 3
            usage["output"] += sum(map(len, texts)) // 3
        if not texts:
            kinds = sorted({json.loads(l).get("type", "?") for l in r.stdout.splitlines() if l.startswith("{") and l.endswith("}")} or {"出力なし"})
            raise RuntimeError(f"opencode が本文を返さなかった（イベント: {','.join(kinds)}）")
        return "".join(texts)
