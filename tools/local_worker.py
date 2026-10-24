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

    def commit_push(self, d: Path, branch: str, msg: str, add: bool = True):
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
                raise RuntimeError(f"{branch} への push が衝突した。次回やり直す")
        raise RuntimeError(f"{branch} への push に失敗")


class Lock:
    def __init__(self, path: Path):
        self.path = path

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and time.time() - self.path.stat().st_mtime > LOCK_STALE:
            self.path.unlink()
        try:
            os.close(os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError:
            raise SystemExit("別のワーカーが実行中（work/lock）。終了する") from None
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


def run_convert(job: dict, git: Git, jobs_model: str | None) -> dict:
    """cards-data の作業ツリーに現在の tools/dmsim/data/rules を重ねて auto_convert を実行し、結果を push する。"""
    d = data_tree(git)
    model = job.get("model") or jobs_model or lo.OPENCODE_DEFAULT
    lo.make_llm("opencode-cli", model)       # 許可リスト検査（違反は Fatal）
    env = {k: v for k, v in os.environ.items() if k != "OPENCODE_API_KEY"}
    r = subprocess.run([sys.executable, "tools/auto_convert.py", "--model", model, "--limit", str(job.get("limit", 20)),
                        "--interval", str(job.get("interval", 3)), "--workers", str(job.get("workers", 1))],
                       cwd=d, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    git.sh("reset", "-q", cwd=d)
    git.sh("add", "-f", "data/cards/converted.yaml", "data/cards/raw/rejects.jsonl", "data/cards/raw/convert_report.json",
           "data/cards/raw/convert_status.json", cwd=d, check=False)
    git.commit_push(d, DATA_BRANCH, f"cards-data: convert (local worker) {now()}", add=False)
    if r.returncode:
        return {"status": "error", "error": lo.scrub((r.stderr or "")[-400:])}
    return {"status": "ok", "text": lo.scrub((r.stdout or "")[-1500:])}


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


def process(git: Git, llm_factory=None, max_jobs: int = 20, daily_limit: int = lo.DAILY_LIMIT) -> list[str]:
    jd = git.worktree("jobs", JOBS_BRANCH, create=True)
    pending, done = jd / "jobs" / "pending", jd / "jobs" / "done"
    done.mkdir(parents=True, exist_ok=True)
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
    with Lock(Path(a.work) / "lock"):
        while True:
            try:
                print(now(), process(git, daily_limit=a.daily_limit) or "ジョブなし", flush=True)
            except RuntimeError as ex:
                print(now(), "失敗（次回やり直す）:", lo.scrub(str(ex)), file=sys.stderr, flush=True)
            if not a.loop:
                return 0
            time.sleep(a.loop)


if __name__ == "__main__":
    sys.exit(main())
