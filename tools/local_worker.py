"""手元のPCで OpenCode の無料モデルを動かすワーカー。GitHub 上のジョブを取りに行き、結果を戻す（ポート開放・キー不要）。

    python tools/local_worker.py run --once          # 1回だけ処理（cron / タスクスケジューラから呼ぶ）
    python tools/local_worker.py run --loop 300      # 5分ごとに処理し続ける（手動で常駐させる場合）
    python tools/local_worker.py enqueue ask --task review-diff --file my.diff
    python tools/local_worker.py enqueue convert --limit 100
    python tools/local_worker.py status

ジョブは専用ブランチ llm-jobs の jobs/pending/<id>.yaml。結果は jobs/done/<id>.yaml（status: ok / escalate / error、text）。
  type: ask      {task, instruction?, input | input_file?}   → llm_offload.ask（秘密の伏せ字・切り詰め・日次上限・キャッシュ）
  type: convert  {limit?, workers?, interval?, model?}        → tools/auto_convert.py を cards-data ブランチの作業ツリーで実行して push
  どのジョブも pr: <番号> を付けると結果を PR コメントに投稿する（PC に gh が要る。docs/offload.md）。
  type: routine  {name: gaps | tests | review | status, summarize?, base?}  → 決まった定型作業だけ（任意コマンドは実行しない）
無料モデルの許可リスト検査・課金検知は llm_offload/providers.py がそのまま効く。課金の兆候は Fatal で全体を止める。
詳しい手順は docs/offload.md。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import llm_offload as lo  # noqa: E402

JOBS_BRANCH, DATA_BRANCH = "llm-jobs", "cards-data"
EMPTY_TREE_ARGS = ["git", "mktree"]
LOCK_STALE = 3 * 3600


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Git:
    def __init__(self, root: Path, work: Path):
        self.root, self.work = root, work
        work.mkdir(parents=True, exist_ok=True)

    def sh(self, *args, cwd: Path | None = None, check: bool = True, inp: str | None = None) -> str:
        r = subprocess.run(["git", *args], cwd=cwd or self.root, capture_output=True, text=True, input=inp,
                           encoding="utf-8", errors="replace")
        if check and r.returncode:
            raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()[:300]}")
        return r.stdout.strip()

    def remote_has(self, branch: str) -> bool:
        return bool(self.sh("ls-remote", "--heads", "origin", branch))

    def worktree(self, name: str, branch: str, create: bool = False) -> Path:
        """origin/<branch> を作業ツリー(work/<name>)に最新化して返す。create=True で無ければ空のブランチを作る。"""
        if not self.remote_has(branch):
            if not create:
                raise RuntimeError(f"origin に {branch} ブランチが無い")
            empty = self.sh("mktree", inp="")
            c = self.sh("commit-tree", empty, "-m", f"init {branch}")
            self.sh("push", "origin", f"{c}:refs/heads/{branch}")
        self.sh("fetch", "-q", "origin", branch)
        d = self.work / name
        if not d.exists():
            self.sh("worktree", "add", "-f", "--detach", str(d), f"origin/{branch}")
        self.sh("reset", "-q", "--hard", f"origin/{branch}", cwd=d)
        return d

    def merge_convert_results(self, d: Path, branch: str, msg: str):
        """変換結果ファイルが origin 側とも変わって rebase が衝突したときの合流。converted.yaml と rejects.jsonl を ID ごとの和集合にして、
        origin の最新の上に1コミット作り直す（作業ツリーの tools/ 等の上書きはそのまま残す）。成功扱い（変換済み）が優先。"""
        import yaml as _y
        conv, rej = d / "data/cards/converted.yaml", d / "data/cards/raw/rejects.jsonl"

        def theirs(path: str) -> str:
            return self.sh("show", f"origin/{branch}:{path}", cwd=d, check=False)

        cards = {}
        for text in (theirs("data/cards/converted.yaml"), conv.read_text(encoding="utf-8") if conv.exists() else ""):
            for c in (_y.safe_load(text) or {}).get("cards") or []:      # あとから読む（自分の結果）が優先
                cards[c["id"]] = c
        rejects = {}
        for text in (theirs("data/cards/raw/rejects.jsonl"), rej.read_text(encoding="utf-8") if rej.exists() else ""):
            for line in text.splitlines():
                if line.strip():
                    r = json.loads(line)
                    rejects[r["id"]] = r
        for i in cards:
            rejects.pop(i, None)
        conv.write_text("# convert_cards.py の出力（review: pending）。確認後に real.yaml へ移す。\n"
                        + _y.safe_dump({"cards": list(cards.values())}, allow_unicode=True, sort_keys=False), encoding="utf-8")
        rej.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rejects.values()), encoding="utf-8")
        self.sh("reset", "-q", "--mixed", f"origin/{branch}", cwd=d)
        for f in ("data/cards/converted.yaml", "data/cards/raw/rejects.jsonl", "data/cards/raw/convert_report.json",
                  "data/cards/raw/convert_status.json"):
            if (d / f).exists():      # 無いパスを混ぜると git add 全体が失敗するので、あるものだけ足す
                self.sh("add", "-f", f, cwd=d, check=False)
        self.sh("commit", "-qm", msg + "（衝突を合流）", cwd=d, check=False)

    def commit_push(self, d: Path, branch: str, msg: str, add: bool = True, on_conflict=None):
        if add:
            self.sh("add", "-A", "jobs", cwd=d, check=False)
        if not self.sh("diff", "--cached", "--name-only", cwd=d):
            return
        self.sh("commit", "-qm", msg, cwd=d)
        for i in range(3):
            if subprocess.run(["git", "push", "-q", "origin", f"HEAD:{branch}"], cwd=d, capture_output=True).returncode == 0:
                return
            self.sh("fetch", "-q", "origin", branch)
            if subprocess.run(["git", "rebase", f"origin/{branch}"], cwd=d, capture_output=True).returncode:
                self.sh("rebase", "--abort", cwd=d, check=False)
                if on_conflict is None:
                    raise RuntimeError(f"{branch} への push が衝突した。次回やり直す")
                on_conflict()      # 結果ファイルの合流など。そのあと push をやり直す
        raise RuntimeError(f"{branch} への push に失敗")


def keep_awake(on: bool):
    """Windows で、ワーカーが動いている間はスリープに入らないようにする（画面は消えてよい）。他の OS では何もしない。
    注意: ふたを閉じた時の動作や、タスクスケジューラの『スリープ解除』は別の設定（docs/offload.md）。"""
    if os.name != "nt":
        return
    try:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED if on else ES_CONTINUOUS)
    except Exception:   # noqa: BLE001  設定できなくても本処理は続ける
        pass


class Tee:
    """画面とログファイルの両方へ書く（スケジューラ起動のウィンドウに経過を出しつつ log.txt にも残す）。"""

    def __init__(self, stream, f):
        self.stream, self.f = stream, f

    def write(self, text):
        for t in (self.stream, self.f):
            try:
                t.write(text)
                t.flush()
            except Exception:   # noqa: BLE001  画面が閉じられてもログは続ける
                pass
        return len(text)

    def flush(self):
        pass


def pid_alive(pid: int) -> bool:
    """そのPIDのプロセスが生きているか。Windows の os.kill(pid, 0) は対象を終了させてしまうので使わない。"""
    if pid <= 0:
        return False
    if os.name == "nt":
        r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, timeout=20)
        return str(pid) in r.stdout.split()
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Lock:
    """<--work>/lock（既定 ~/.dmpj-worker/lock）。中に持ち主のPIDを書く。持ち主が死んでいれば自動で引き継ぐ（強制終了で残ったロック対策）。"""

    def __init__(self, path: Path):
        self.path = path

    def _stale(self) -> bool:
        if time.time() - self.path.stat().st_mtime > LOCK_STALE:
            return True
        try:
            pid = int(self.path.read_text().strip())
        except (ValueError, OSError):
            return False      # PIDなし（旧版が作ったロック）は時間切れまで待つ
        return not pid_alive(pid)

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self._stale():
            print("古いロックを回収した（持ち主のプロセスがいない）", flush=True)
            self.path.unlink(missing_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise SystemExit(f"別のワーカーが実行中（{self.path}）。終了する") from None
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return self

    def __exit__(self, *a):
        self.path.unlink(missing_ok=True)


def run_ask(job: dict, llm, cache: Path, daily_limit: int, base: Path) -> dict:
    text = job.get("input")
    if text is None and job.get("input_file"):
        text = (base / job["input_file"]).read_text(encoding="utf-8", errors="replace")
    if text is None:
        return {"status": "error", "error": "input / input_file がない"}
    try:
        r = lo.ask(job.get("task", "ask"), text, instruction=job.get("instruction"), llm=llm, cache=cache,
                   daily_limit=daily_limit)
    except lo.Escalate as e:
        return {"status": "escalate", "error": str(e)}     # Claude が代わりに処理してよい合図
    return {"status": "ok", "text": r.text, "model": r.model, "cached": r.cached}


class ModelOutage(RuntimeError):
    """モデルが使えず進まなかった。ジョブは error にせず pending のまま残し、次回やり直す。"""


def run_convert(job: dict, git: Git, jobs_model: str | None) -> dict:
    """cards-data の作業ツリーに現在の tools/dmsim/data/rules を重ねて auto_convert を実行し、結果を push する。"""
    d = data_tree(git)
    model = job.get("model") or jobs_model or lo.OPENCODE_DEFAULT
    lo.make_llm("opencode-cli", model)       # 許可リスト検査（違反は Fatal）
    env = {k: v for k, v in os.environ.items() if k != "OPENCODE_API_KEY"}
    # chunk 枚ごとに auto_convert を呼び、そのたびに cards-data へ push する（途中で止めても済んだ分は残る）。
    # 次回起動時の worktree は origin に reset されるので、push していない分は消える。だから chunk 枚ごとに push する。
    # chunk は job の `chunk:` で変えられる（既定10。止まったときに失うのは最大 chunk 枚）。
    chunk, total = max(1, int(job.get("chunk", 10))), int(job.get("limit", 20))
    tail: list[str] = []
    code, done_n = 0, 0
    for _ in range(max(1, -(-total // chunk))):
        cmd = [sys.executable, "-u", "tools/auto_convert.py", "--model", model, "--limit", str(chunk), "--batch", str(min(chunk, 5)),
               "--interval", str(job.get("interval", 3)), "--workers", str(job.get("workers", 1))]
        # 出力を1行ずつ画面とログへ流す（ウィンドウで途中経過が見える）。最後の出力は結果に残す
        proc = subprocess.Popen(cmd, cwd=d, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", bufsize=1)
        for line in proc.stdout:
            line = lo.scrub(line.rstrip("\n"))
            print(now(), line, flush=True)
            tail = (tail + [line])[-40:]
        proc.wait()
        git.sh("reset", "-q", cwd=d)
        git.sh("add", "-f", "data/cards/converted.yaml", "data/cards/raw/rejects.jsonl", "data/cards/raw/convert_report.json",
               "data/cards/raw/convert_status.json", cwd=d, check=False)
        msg = f"cards-data: convert (local worker) {now()}"
        git.commit_push(d, DATA_BRANCH, msg, add=False, on_conflict=lambda: git.merge_convert_results(d, DATA_BRANCH, msg))
        print(now(), "保存して push した", flush=True)
        code = proc.returncode
        try:
            lr = (json.loads((d / "data/cards/raw/convert_status.json").read_text(encoding="utf-8")).get("last_run") or {}).get("new") or {}
        except (OSError, ValueError):
            lr = {}
        progressed = 0 if code else lr.get("ok", 0) + lr.get("rejected", 0)      # 異常終了のときは前回の status が残っているので数えない
        done_n += progressed
        outage = code == 3 or (code == 0 and not progressed and lr.get("api_error", 0) > 0)    # 3=開始前ヘルスチェック失敗
        if outage:
            raise ModelOutage(f"モデルが使えず進まなかった（ここまで {done_n} 枚）。ジョブは pending のまま次回やり直す")
        if code or not progressed:      # 停止・API失敗だけで進まない時はここで終える（空回りしない）
            break
    r = subprocess.CompletedProcess([], code, "\n".join(tail), "\n".join(tail))
    if r.returncode:
        return {"status": "error", "error": lo.scrub((r.stderr or "")[-400:])}
    return {"status": "ok", "text": lo.scrub(f"処理 {done_n} 枚（{chunk}枚ごとに保存）\n" + (r.stdout or "")[-1400:])}


def data_tree(git: Git) -> Path:
    """cards-data の作業ツリーに、現在の tools/dmsim/語彙/カード定義を重ねて返す。"""
    d = git.worktree("cards-data", DATA_BRANCH)
    for sub in ("tools", "dmsim", "data/rules"):
        shutil.copytree(ROOT / sub, d / sub, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", ".cache"))
    for f in ("data/cards/proto.yaml", "data/cards/real.yaml", "data/cards/real_vocab.yaml", "data/cards/real_zone.yaml"):
        if (ROOT / f).exists():
            shutil.copy(ROOT / f, d / f)
    for f in (ROOT / "data/cards/raw").glob("official_*.jsonl"):
        shutil.copy(f, d / "data/cards/raw" / f.name)
    return d


def run_routine(job: dict, git: Git, llm, cache: Path, daily_limit: int) -> dict:
    """決まった定型作業だけ。ジョブから渡された文字列をコマンドとして実行することはない。"""
    name = job.get("name")
    if name == "gaps":
        d = data_tree(git)
        out = subprocess.run([sys.executable, "tools/report_gaps.py"], cwd=d, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout or ""
        job = {**job, "summarize": None}     # report_gaps の出力は集計済み。無料モデルで再要約すると途中で切れて不正確になるので、上位だけをそのまま返す
    elif name == "tests":
        r = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = lo.digest_pytest((r.stdout or "") + (r.stderr or ""))
    elif name == "status":
        r = subprocess.run([sys.executable, "tools/gen_status.py", "--check"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = ((r.stdout or "") + (r.stderr or "")) or "STATUS.md は最新"
    elif name == "review":
        base = str(job.get("base", "origin/main"))
        if not re.fullmatch(r"[\w./-]+", base) or base.startswith("-"):
            return {"status": "error", "error": "base が不正"}
        if job.get("pr") and gh_exe():       # PR 付きなら、その PR の差分をレビューする（PC の main は origin/main と同じで差分が空になるため）
            out = subprocess.run([gh_exe(), "pr", "diff", str(int(job["pr"]))], cwd=ROOT, env=gh_env(), capture_output=True,
                                 text=True, encoding="utf-8", errors="replace").stdout or ""
        else:
            out = subprocess.run(["git", "diff", base], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                                 errors="replace").stdout or ""
        if not out.strip():
            return {"status": "ok", "text": "差分なし（レビュー対象が空）。PR 付きで投入するか、base を指定する"}
        job = {**job, "summarize": "review-diff"}
    else:
        return {"status": "error", "error": f"未知の routine {name!r}（gaps / tests / review / status）"}
    out = lo.scrub(out)
    if job.get("summarize"):
        task = job["summarize"] if job["summarize"] in lo.TASKS else "summarize"
        try:
            r2 = lo.ask(task, out, llm=llm, cache=cache, daily_limit=daily_limit, max_chars=12000)
        except lo.Escalate as e:
            return {"status": "escalate", "error": str(e), "text": lo.clip(out, 3000)}
        return {"status": "ok", "text": r2.text, "model": r2.model}
    return {"status": "ok", "text": lo.clip(out, 6000)}


SELF_FILES = ("tools/local_worker.py", "tools/run_worker.bat", "tools/llm_offload/")


def self_update(root: Path = ROOT, log=print) -> str:
    """実行前に main を fast-forward だけで更新する（PC での git pull の自動化）。
    作業ツリーが汚れている・main 以外のブランチ・ff 不可・ネットワーク不通のときは何もせず理由を返す。例外は呼び出し側に出さない。
    ワーカー自身が更新された場合は、呼び出し側（main）が新版で起動し直す（旧版のまま長いジョブを走らせないため）。"""
    def git(*a):
        r = subprocess.run(["git", *a], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    try:
        rc, branch, _ = git("rev-parse", "--abbrev-ref", "HEAD")
        if rc or branch != "main":
            return f"更新しない: ブランチが main でない({branch or '不明'})"
        rc, dirty, _ = git("status", "--porcelain", "--untracked-files=no")
        if rc or dirty:
            return "更新しない: 作業ツリーに未コミットの変更がある"
        rc, _, err = git("fetch", "-q", "origin", "main")
        if rc:
            return f"更新しない: fetch に失敗({lo.scrub(err)[:100]})"
        rc, old, _ = git("rev-parse", "HEAD")
        rc2, new, _ = git("rev-parse", "origin/main")
        if rc or rc2 or old == new:
            return "最新"
        rc, _, err = git("merge", "--ff-only", "-q", "origin/main")
        if rc:
            return f"更新しない: fast-forward できない({lo.scrub(err)[:100]})"
        _, changed, _ = git("diff", "--name-only", old, new)
        self_changed = [f for f in changed.splitlines() if f.startswith(SELF_FILES)]
        return f"更新した {old[:7]}→{new[:7]}" + ("（ワーカー自身が変わった）" if self_changed else "")
    except Exception as e:   # noqa: BLE001  更新の失敗でワーカー本体を止めない
        return f"更新しない: {type(e).__name__}"


def summary_line(res: dict) -> str:
    """結果の1行要約。Claude が全文を読まずに済むようにする。"""
    first = next((ln.strip(" -*#") for ln in (res.get("text") or "").splitlines() if ln.strip()), "")
    head = f"[{res['status']}]" + (f" {res['error']}" if res.get("error") else "")
    return lo.scrub(f"{head} {first}".strip())[:160]


def gh_exe() -> str | None:
    return next(filter(None, (shutil.which(n) for n in ("gh.exe", "gh"))), None)


def gh_env() -> dict:
    """環境変数の GITHUB_TOKEN / GH_TOKEN は無効なことがあり、gh のキーリング認証より優先されて 401 になる。外して呼ぶ。"""
    return {k: v for k, v in os.environ.items() if k not in ("GITHUB_TOKEN", "GH_TOKEN", "GH_ENTERPRISE_TOKEN")}


def post_pr_comment(pr, jid: str, res: dict) -> str:
    """結果を PR コメントに投稿する（PC の gh 認証を使う）。購読中のセッションにイベントとして届く。失敗してもジョブは失敗にしない。"""
    exe = gh_exe()
    if not exe:
        return "skipped: gh が無い（winget install GitHub.cli → gh auth login）"
    try:
        num = int(pr)
    except (TypeError, ValueError):
        return "skipped: pr が数値でない"
    body = f"**ローカルワーカー結果** `{jid}` — {res['status']}\n\n{lo.clip(res.get('text') or res.get('error') or '', 6000)}\n"
    try:
        r = subprocess.run([exe, "pr", "comment", str(num), "--body-file", "-"], input=lo.scrub(body), cwd=ROOT, env=gh_env(),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    except Exception as e:   # noqa: BLE001
        return f"failed: {type(e).__name__}"
    return "posted" if r.returncode == 0 else f"failed: {lo.scrub((r.stderr or '')[:150])}"


def model_alive(timeout: float = 90) -> str | None:
    """無料モデル（匿名枠）が応答するかを短い質問で確かめる。使えれば None、だめなら理由を返す。"""
    from llm_offload import providers
    old = providers.OPENCODE_TIMEOUT
    providers.OPENCODE_TIMEOUT = timeout
    try:
        llm = lo.make_llm("opencode-cli", lo.OPENCODE_DEFAULT)
        if llm.recently_ok():
            return None          # 直近に応答が返っている（5枚ごとの再起動でも試し直さない）
        llm.alternates = []      # 開始前の確認は1モデル＋別サービスだけ（5分ごとの起動に収める）
        llm.complete("", [{"role": "user", "content": "OKとだけ答えて"}], "low", None)
        return None
    except lo.Fatal:
        raise
    except Exception as e:      # noqa: BLE001  応答なし・CLIなし等はすべて「今は使えない」
        return f"{type(e).__name__}: {str(e)[:150]}"
    finally:
        providers.OPENCODE_TIMEOUT = old


def process(git: Git, llm_factory=None, max_jobs: int = 20, daily_limit: int = lo.DAILY_LIMIT, health=None) -> list[str]:
    jd = git.worktree("jobs", JOBS_BRANCH, create=True)
    pending, done = jd / "jobs" / "pending", jd / "jobs" / "done"
    done.mkdir(parents=True, exist_ok=True)
    if health and any(pending.glob("*.yaml")):
        why = health()      # ジョブがある時だけ確かめる。だめなら cards-data にも触れず、ジョブは pending のまま次回へ
        if why:
            return [f"モデルが使えないので今回は処理しない（ジョブは pending のまま）: {why}"]
    llm_factory = llm_factory or (lambda model: lo.make_llm("opencode-cli", model))
    handled = []
    for p in sorted(pending.glob("*.yaml"))[:max_jobs]:
        job = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        jid = p.stem
        try:
            if job.get("type") == "convert":
                res = run_convert(job, git, None)
            elif job.get("type") == "routine":
                res = run_routine(job, git, llm_factory(job.get("model")), git.work / "cache", daily_limit)
            elif job.get("type") == "ask":
                res = run_ask(job, llm_factory(job.get("model")), git.work / "cache", daily_limit, jd)
            else:
                res = {"status": "error", "error": f"未知の type {job.get('type')!r}"}
        except ModelOutage as e:    # ジョブは消さず、残りも今回は見送る
            handled.append(f"{jid}:pending（{e}）")
            break
        except lo.Fatal as e:      # 課金の兆候・許可外モデル。以降のジョブは実行しない
            res = {"status": "error", "error": lo.scrub(f"STOP: {e}")}
            (done / f"{jid}.yaml").write_text(yaml.safe_dump({"id": jid, "finished": now(), **res}, allow_unicode=True), encoding="utf-8")
            p.unlink()
            git.commit_push(jd, JOBS_BRANCH, f"jobs: {jid} stopped")
            raise SystemExit(f"停止: {res['error']}") from None
        except Exception as e:     # noqa: BLE001  1件の失敗でワーカー全体を落とさない。error を残して done に移す（毎回の再実行で無料枠を使わない）
            res = {"status": "error", "error": lo.scrub(f"{type(e).__name__}: {e}")[:400]}
        if job.get("pr"):
            res["pr_comment"] = post_pr_comment(job["pr"], jid, res)
        (done / f"{jid}.yaml").write_text(yaml.safe_dump({"id": jid, "summary": summary_line(res), "finished": now(), **res},
                                                         allow_unicode=True, sort_keys=False), encoding="utf-8")
        p.unlink()
        handled.append(f"{jid}:{res['status']}")
        git.commit_push(jd, JOBS_BRANCH, f"jobs: {jid} {res['status']}")
    return handled


def enqueue(git: Git, job: dict) -> str:
    jd = git.worktree("jobs", JOBS_BRANCH, create=True)
    jid = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    (jd / "jobs" / "pending").mkdir(parents=True, exist_ok=True)
    (jd / "jobs" / "pending" / f"{jid}.yaml").write_text(yaml.safe_dump(job, allow_unicode=True, sort_keys=False), encoding="utf-8")
    git.commit_push(jd, JOBS_BRANCH, f"jobs: enqueue {jid}")
    return jid


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", default=str(Path.home() / ".dmpj-worker"), help="作業ディレクトリ（作業ツリー・キャッシュ・ロック）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--once", action="store_true")
    r.add_argument("--loop", type=int, metavar="SEC")
    r.add_argument("--no-update", action="store_true", help="実行前の main 更新(git fetch + merge --ff-only)をしない")
    r.add_argument("--log", help="出力を追記するログファイル（画面にも出す）。省略時は画面のみ")
    r.add_argument("--daily-limit", type=int, default=lo.DAILY_LIMIT)
    e = sub.add_parser("enqueue")
    e.add_argument("type", choices=["ask", "convert", "routine"])
    e.add_argument("--task", default="summarize")
    e.add_argument("--instruction")
    e.add_argument("--file", help="ask の入力ファイル（中身をジョブに埋め込む）")
    e.add_argument("--model")
    e.add_argument("--name", help="routine の名前（gaps / tests / review / status）")
    e.add_argument("--summarize", action="store_true", help="routine の結果を無料モデルで要約する")
    e.add_argument("--pr", type=int, help="結果をこの PR にコメント投稿する（PC に gh が要る）。Claude は PR 購読で自動に受け取る")
    e.add_argument("--limit", type=int, default=100)
    e.add_argument("--workers", type=int, default=1)
    sub.add_parser("status")
    a = ap.parse_args(argv)
    # デスクトップアプリのDBと食い違うことがあるので、OpenCode CLI は専用の保存先で動かす（Windowsで動作確認済み）
    os.environ.setdefault("PYTHONUTF8", "1")      # 子プロセス(Python)の出力もUTF-8にそろえる(Windows既定はcp932)
    os.environ.setdefault("XDG_DATA_HOME", str(Path(a.work) / "xdg"))
    os.environ.setdefault("XDG_CONFIG_HOME", str(Path(a.work) / "xdg-config"))
    os.environ.setdefault("DMPJ_MODEL_STATE", str(Path(a.work) / "model_state.json"))      # 使えたモデル・使えなかったモデルを実行をまたいで覚える
    git = Git(ROOT, Path(a.work))
    if a.cmd == "enqueue":
        job = {"type": a.type}
        if a.model:
            job["model"] = a.model
        if a.type == "ask":
            job.update(task=a.task, input=lo.scrub(Path(a.file).read_text(encoding="utf-8") if a.file else sys.stdin.read()))
            if a.instruction:
                job["instruction"] = a.instruction
        elif a.type == "routine":
            job.update(name=a.name, summarize=a.summarize)
        else:
            job.update(limit=a.limit, workers=a.workers)
        if a.pr:
            job["pr"] = a.pr
        print(enqueue(git, job))
        return 0
    if a.cmd == "status":
        jd = git.worktree("jobs", JOBS_BRANCH, create=True)
        for k in ("pending", "done"):
            fs = sorted((jd / "jobs" / k).glob("*.yaml")) if (jd / "jobs" / k).exists() else []
            print(f"{k}: {len(fs)}", *[f.stem for f in fs[-5:]])
        return 0
    if a.log:
        Path(a.log).parent.mkdir(parents=True, exist_ok=True)
        lf = open(a.log, "a", encoding="utf-8", errors="replace")
        sys.stdout, sys.stderr = Tee(sys.stdout, lf), Tee(sys.stderr, lf)
    print(now(), "ワーカー開始", flush=True)
    restart = False
    keep_awake(True)
    import atexit
    atexit.register(keep_awake, False)
    with Lock(Path(a.work) / "lock"):
        while True:
            if not a.no_update:
                msg = self_update()
                print(now(), "self-update:", msg, flush=True)
                if "ワーカー自身が変わった" in msg and not os.environ.get("DMPJ_WORKER_RESTARTED"):
                    restart = True      # ロックを放してから新版で起動し直す（with を抜けた後）
                    break
            try:
                print(now(), process(git, daily_limit=a.daily_limit, health=model_alive) or "ジョブなし", flush=True)
            except RuntimeError as ex:
                print(now(), "失敗（次回やり直す）:", lo.scrub(str(ex)), file=sys.stderr, flush=True)
            if not a.loop:
                return 0
            time.sleep(a.loop)
    if restart:
        print(now(), "ワーカーが更新されたので新版で起動し直す", flush=True)
        return subprocess.call([sys.executable, *sys.argv], env={**os.environ, "DMPJ_WORKER_RESTARTED": "1"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
