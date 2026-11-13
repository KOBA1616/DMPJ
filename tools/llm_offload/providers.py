"""無料モデル（OpenCode）の呼び出し部。課金事故防止の検査（許可リスト・費用の兆候・課金系エラー）はここに集約する。

convert_cards.py など全ツールがこれを使う。課金が発生しうる経路はここに作らない。
"""
from __future__ import annotations

import json
import sys
import re
from pathlib import Path


class BadResponse(ValueError):
    """応答に本文がないなど、モデルの出力が使えない。"""


class CallTimeout(RuntimeError):
    """1回の呼び出しが上限秒内に終わらなかった。"""


class Fatal(Exception):
    """続行すると課金や無駄打ちになるエラー。実行全体を止める。"""


# --- OpenCode（無料モデル専用） -------------------------------------------------------------
# 課金事故防止: この許可リストにあるモデルIDだけを、この固定URLにだけ送る。リスト外は実行前に拒否する。
# 新しい無料モデルを使うときは、公式 https://opencode.ai/docs/zen/ で $0 と確認してここに足す。
OPENCODE_URL = "https://opencode.ai/inference/openai/v1/chat/completions"
OPENCODE_FREE_MODELS = frozenset({
    "glm-5.3-flash-free", "deepseek-v4.1-flash-free", "nemotron-3-ultra-free", "mimo-v2.6-flash-free",
    "beam-free", "flint-40b-free", "nemotron-3.5-lightning-free", "nemotron-3.5-super-vl-free",
    # 公式 zen の料金表で Free(入出力$0)を確認（2026-10-26）。longcat-2.5-preview-free は表から消え `opencode models` にもないので外した
})
OPENCODE_DEFAULT = "glm-5.3-flash-free"
OPENCODE_FALLBACK_ORDER = ("deepseek-v4.1-flash-free", "glm-5.3-flash-free", "nemotron-3-ultra-free",
                           "mimo-v2.6-flash-free", "nemotron-3.5-super-vl-free", "flint-40b-free", "beam-free",
                           "nemotron-3.5-lightning-free")
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


OPENROUTER_URL = "https://openrouter.ai/api/v1"
OPENROUTER_PREFER = ("deepseek", "qwen", "glm", "gpt-oss", "llama", "gemma", "mistral")   # 変換向きの順（無料モデルの中での好み）


class Chain:
    """別サービスを順に試す（先のものが全部だめなら次へ。Fatal=課金の兆候はそのまま上げる）。"""

    def __init__(self, *llms):
        self.llms = [x for x in llms if x is not None]

    def complete(self, sysp, messages, effort, usage):
        last = None
        for x in self.llms:
            try:
                return x.complete(sysp, messages, effort, usage)
            except Fatal:
                raise
            except Exception as e:      # noqa: BLE001
                last = e
                print(f"  ⏱ {x.name} も使えない（{type(e).__name__}）", file=sys.stderr, flush=True)
        raise last or RuntimeError("切り替え先がない")


class FreeLimit(RuntimeError):
    """OpenCode の無料枠の上限（FreeUsageLimitError）。アカウント・ワークスペース・ネットワーク単位なので、別の OpenCode モデルに替えても直らない。"""


FREE_LIMIT_RE = re.compile(r"(?i)FreeUsageLimitError|Free usage limit reached|free (?:usage|message)s? limit")


class OpenRouterLLM:
    """別サービスへの切り替え先。OpenRouter の無料モデルだけを、毎回公式の一覧(/models・認証不要)で確かめて使う。
    ':free' で終わり、かつ入力・出力の単価がどちらも 0 のものに限る。応答に費用が載っていたら停止する。
    キーは環境変数 OPENROUTER_API_KEY（無ければ使わない）。"""
    name = "openrouter"

    def __init__(self, min_interval: float = 3.0, key: str | None = None):
        import os
        import threading
        self.key = key or os.environ.get("OPENROUTER_API_KEY", "")
        if not self.key:
            raise Fatal("環境変数 OPENROUTER_API_KEY が未設定")
        self.min_interval = min_interval
        self.model = None
        self.base = OPENROUTER_URL
        self.free_suffix = ":free"       # 応答のモデル名がこれで終わらなければ無料でないとみなして停止
        self._free: list[str] | None = None
        self._last, self._lock = 0.0, threading.Lock()

    def _request(self, path: str, payload: dict | None = None, auth: bool = True) -> dict:
        import time
        import urllib.error
        import urllib.request
        with self._lock:
            time.sleep(max(0.0, self._last + self.min_interval - time.monotonic()))
            self._last = time.monotonic()
        headers = {"Content-Type": "application/json", "User-Agent": "dmpj-convert/1.0"}
        if auth:
            headers["Authorization"] = f"Bearer {self.key}"
        req = urllib.request.Request(self.base + path, json.dumps(payload).encode() if payload else None, headers)
        try:
            with urllib.request.urlopen(req, timeout=OPENCODE_TIMEOUT) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300].replace(self.key, "***")
            if e.code == 402 or re.search(r"(?i)billing|credit|balance|payment|insufficient", body):
                raise Fatal(f"課金・残高に関するエラーなので停止する: HTTP {e.code} {body}") from None
            # キー自体の問題は止める。「このモデルは agentic harness 限定」等、特定モデルだけの 403 は止めずに次のモデルへ
            if e.code == 401 or (e.code == 403 and re.search(r"(?i)api[ _-]?key|credential|unauthori[sz]ed|invalid.*(key|token)|permission denied|billing|suspended|banned", body)):
                raise Fatal(f"認証/権限エラー: HTTP {e.code} {body}") from None
            raise RuntimeError(f"HTTP {e.code} {body[:160]}") from None
        except OSError as e:
            if "timed out" in str(e):
                raise CallTimeout(f"openrouter が{OPENCODE_TIMEOUT:g}秒以内に終わらなかった") from None
            raise

    def free_models(self) -> list[str]:
        """公式の一覧から、入出力とも $0 の ':free' モデルを、好みの順→文脈長の順で返す。"""
        if self._free is None:
            data = self._request("/models", auth=False).get("data") or []
            ok = [m for m in data if str(m.get("id", "")).endswith(":free")
                  and float((m.get("pricing") or {}).get("prompt", 1)) == 0 and float((m.get("pricing") or {}).get("completion", 1)) == 0]
            def rank(m):
                i = next((k for k, w in enumerate(OPENROUTER_PREFER) if w in m["id"]), len(OPENROUTER_PREFER))
                return (i, -(m.get("context_length") or 0))
            self._free = [m["id"] for m in sorted(ok, key=rank)]
        return self._free

    def complete(self, sysp: str, messages: list[dict], effort: str, usage: dict | None, max_models: int = 3) -> str:
        tried, last = [], None
        for m in self.free_models()[:max_models]:
            try:
                resp = self._request("/chat/completions", {"model": m, "max_tokens": 16000, "temperature": 0.2,
                                                           "messages": [{"role": "system", "content": sysp}, *messages]})
            except Fatal:
                raise
            except Exception as e:      # noqa: BLE001  次の無料モデルへ
                tried.append(m)
                last = e
                continue
            if not str(resp.get("model", m)).endswith(self.free_suffix) or (resp.get("usage") or {}).get("cost", 0) > 0:
                raise Fatal(f"応答のモデルが無料でない、または費用が載っている: {resp.get('model')}。停止する")
            try:
                text = resp["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError, TypeError):
                tried.append(m)
                last = BadResponse("応答に本文がない")
                continue
            self.model = m
            u = resp.get("usage") or {}
            if usage is not None:
                usage["input"] += u.get("prompt_tokens", 0)
                usage["output"] += u.get("completion_tokens", 0)
            return text
        raise RuntimeError(f"OpenRouter の無料モデル {tried or '（なし）'} がすべて失敗（最後: {last}）")


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
# 公式料金ページで無料枠(Free of charge)と出ている Flash 系（2026-10-26）。Pro 系・画像・Argon は無料枠にないので入れない
GEMINI_FREE_MODELS = ("gemini-3.8-flash", "gemini-3.6-flash", "gemini-3-flash-preview", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite")


class GeminiLLM(OpenRouterLLM):
    """Google AI Studio の Gemini API（OpenAI 互換）。キー GEMINI_API_KEY があるときだけ使う。
    無料枠のモデルだけを固定で使う。注意: キーのプロジェクトに請求先を設定すると有料になりうる（応答から費用は検知できない）。
    請求先のないプロジェクトで作ったキーだけを使うこと。"""
    name = "gemini"

    def __init__(self, min_interval: float = 3.0, key: str | None = None):
        import os
        super().__init__(min_interval, key=key or os.environ.get("GEMINI_API_KEY", "") or "-")
        if self.key == "-":
            raise Fatal("環境変数 GEMINI_API_KEY が未設定")
        self.base = GEMINI_URL
        self.free_suffix = ""

    def free_models(self) -> list[str]:
        return list(GEMINI_FREE_MODELS)


BAD_COOLDOWN = 24 * 3600     # 使えなかった OpenCode モデルを飛ばす秒数（24時間）
EXTERNAL_COOLDOWN = 900   # OpenCode 全滅のあと、この秒数は別サービスを先に使う
LLM7_URL = "https://api.llm7.io/v1"
# 公式 /v1/models で usage_based_only: false（匿名・無料で使える側）と出ているモデル（2026-10-26）。他は従量課金のモデルなので使わない
LLM7_FREE_MODELS = ("gpt-oss:20b", "nemotron-3-nano:30b", "mistral-Nemo-Instruct-2407", "minimax-m2.7")


class LLM7LLM(OpenRouterLLM):
    """最後の切り替え先。LLM7（登録・キー不要の匿名ゲートウェイ。匿名は毎分30回まで、IP が記録される）。
    キーは公式の匿名キー 'unused' で、課金される口座がないので、固定の許可リストの無料モデルだけを使う。"""
    name = "llm7"

    def __init__(self, min_interval: float = 3.0):
        super().__init__(min_interval, key="unused")
        self.base = LLM7_URL
        self.free_suffix = ""

    def free_models(self) -> list[str]:
        return list(LLM7_FREE_MODELS)


def _run_tree(cmd: list[str], timeout: float, cwd: str):
    """subprocess.run の代わり。時間切れでは子孫プロセスごと止める。

    Windows の opencode.cmd は node を子に持ち、run(timeout=) は親だけ kill して、子がパイプを握ったまま
    communicate() で永久に待つ（2026-10-26 無応答で20分の上限が効かなかった）。ここではプロセスツリーを kill する。
    """
    import os
    import signal
    import subprocess
    kw = {"start_new_session": True} if os.name != "nt" else {}
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                            errors="replace", cwd=cwd, **kw)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, timeout=30)
            else:
                os.killpg(proc.pid, signal.SIGKILL)
        except Exception:   # noqa: BLE001  止められなくても待ち続けない
            proc.kill()
        try:
            proc.communicate(timeout=10)
        except Exception:   # noqa: BLE001
            pass
        raise CallTimeout(f"opencode が{timeout:g}秒以内に終わらなかった（TimeoutExpired）") from None
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


class OpenCodeCLI:
    """OpenCode CLI（opencode run）経由。無料枠は「OpenCode の中からのみ」使えるため、API 直叩きが拒否されるときの経路。
    キー不要。モデルは同じ許可リストで検査する。"""
    name = "opencode-cli"

    def __init__(self, model: str = OPENCODE_DEFAULT, min_interval: float = 3.0, fallbacks: int = 2):
        import threading
        check_free_model(model)
        self.model, self.min_interval = model, min_interval
        # タイムアウト時に切り替える先（許可リスト内＝公式で $0 確認済みのものだけ）。fallbacks=0 で切り替えなし
        self.alternates = [m for m in OPENCODE_FALLBACK_ORDER if m != model and m in OPENCODE_FREE_MODELS][:max(0, fallbacks)]
        self._last, self._lock = 0.0, threading.Lock()
        self._ext_until = 0.0
        self.ok_at = 0.0
        self.bad: dict[str, float] = {}      # 使えなかったモデル → この時刻まで飛ばす
        self.fallbacks = max(0, fallbacks)
        self.external = None      # 別サービスの切り替え先（OpenRouterLLM / LLM7LLM、または複数をまとめた Chain）。make_llm が付ける
        self._load_state()

    # --- 実行をまたいで覚える（5枚ごとに別プロセスで起動し直しても、毎回モデルを試し直さない）。環境変数 DMPJ_MODEL_STATE のファイル ---
    def _load_state(self):
        import os
        import time
        self._state_path = os.environ.get("DMPJ_MODEL_STATE")
        if not self._state_path:
            return
        try:
            st = json.loads(Path(self._state_path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        now = time.time()
        if st.get("model") in OPENCODE_FREE_MODELS and st["model"] != self.model:
            self.model = st["model"]
            self.alternates = [m for m in OPENCODE_FALLBACK_ORDER if m != self.model and m in OPENCODE_FREE_MODELS][:self.fallbacks]
        self.bad = {m: float(t) for m, t in (st.get("bad") or {}).items() if float(t) > now and m in OPENCODE_FREE_MODELS}
        self._ext_until = float(st.get("ext_until", 0)) if float(st.get("ext_until", 0)) > now else 0.0
        self.ok_at = float(st.get("ok_at", 0))

    def _save_state(self):
        if not self._state_path:
            return
        try:
            Path(self._state_path).parent.mkdir(parents=True, exist_ok=True)
            Path(self._state_path).write_text(json.dumps({"model": self.model, "ok_at": self.ok_at, "bad": self.bad,
                                                          "ext_until": self._ext_until}), encoding="utf-8")
        except OSError:
            pass      # 記録できなくても変換は続ける

    def recently_ok(self, window: float = 600) -> bool:
        """直近 window 秒以内に（OpenCode または別サービスで）応答が返っていれば True。開始前チェックを省く。"""
        import time
        return time.time() - self.ok_at < window

    def complete(self, sysp: str, messages: list[dict], effort: str, usage: dict | None) -> str:
        """今のモデルがだめなら別の無料モデルで同じ依頼を再試行する。成功したモデルを覚えて使い続け、だめだったモデルは一定時間飛ばす。
        全部だめなら別サービス、それもだめなら CallTimeout / RuntimeError（呼び出し側が保留・連続打ち切りに数える）。"""
        import time
        now = time.time()
        if self.external is not None and now < self._ext_until:      # 直前に OpenCode が全滅したばかり。しばらくは別サービスを直接使う
            text = self.external.complete(sysp, messages, effort, usage)
            self.ok_at = time.time()
            self._save_state()
            return text
        full = [self.model, *self.alternates]
        order = [m for m in full if self.bad.get(m, 0) <= now]
        if not order and self.external is None:
            order = full                    # 全部が冷却中でも、切り替え先がなければ試す
        tried = []
        last: Exception | None = None
        for m in order:
            try:
                text = self._complete_one(m, sysp, messages, usage)
            except Fatal:
                raise
            except FreeLimit as e:      # 上限は全モデル共通。OpenCode の他のモデルは試さず、別サービスがあればそちらへ
                last = e
                tried.append(m)
                print(f"  ⛔ {e}", file=sys.stderr, flush=True)
                break
            except Exception as e:      # noqa: BLE001  タイムアウトも「Model is unavailable」等の応答エラーも、別モデルで試す
                tried.append(m)
                last = e
                self.bad[m] = time.time() + BAD_COOLDOWN
                self._save_state()
                kind = "時間内に終わらない" if isinstance(e, CallTimeout) else f"使えない（{type(e).__name__}: {str(e)[:80]}）"
                print(f"  ⏱ {m} が{kind}。別の無料モデルへ切り替える（{BAD_COOLDOWN // 3600}時間は飛ばす）", file=sys.stderr, flush=True)
                continue
            if m != self.model:
                self.alternates = [x for x in full if x != m]
                self.model = m
            self.bad.pop(m, None)
            self.ok_at = time.time()
            self._save_state()
            return text
        if self.external is not None:      # OpenCode の無料モデルが全滅したら別サービス（Gemini・OpenRouter・LLM7）へ
            print("  ⏱ OpenCode の無料モデルが全滅。別サービスの無料枠へ切り替える", file=sys.stderr, flush=True)
            text = self.external.complete(sysp, messages, effort, usage)
            self._ext_until = time.time() + EXTERNAL_COOLDOWN       # 毎回 OpenCode の全モデルを待たずに済ませる
            self.ok_at = time.time()
            self._save_state()
            return text
        if isinstance(last, FreeLimit):
            raise last
        if isinstance(last, CallTimeout):
            raise CallTimeout(f"{'・'.join(tried)} がすべてタイムアウト（{last}）")
        raise RuntimeError(f"{'・'.join(tried)} がすべて失敗（最後: {last}）")

    def _complete_one(self, model: str, sysp: str, messages: list[dict], usage: dict | None) -> str:
        import shutil
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
            r = _run_tree([exe, "run", "-m", f"opencode/{model}", "--format", "json",
                           "添付ファイルの指示に従い、最後の [user] への答えだけを出力して。", "-f", str(f)],
                          OPENCODE_TIMEOUT, d)
        if FREE_LIMIT_RE.search(r.stdout + r.stderr):
            raise FreeLimit("OpenCode の無料枠の上限に達した（リセットまで待つ。時刻は OpenCode のコンソールで確認）")
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
