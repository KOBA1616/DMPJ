"""日次実行の自己修復の土台。段階（診断・deck_fix・チューナー・対象ごとの診断）の例外を握って記録し、残りの段階は続ける。

- 例外は data/autofix/health.yaml に残る（連続失敗回数・最後のエラー・最後に成功した日）。成功すると連続失敗は 0 に戻る。
- 失敗があれば Issue 用の要約（render_issue）を作る。日次ルーティンは label autofix-failing の Issue を読み、
  原因を直して PR を出し（直ったら Issue を閉じる）、次回の実行で再測定する（docs/autofix-selfheal.md）。
- 同じ段階が連続 QUARANTINE_AFTER 回失敗したら、その段階は日次では飛ばす（時間の無駄を避ける）。直ったら health.yaml の該当段階を消せば再開する。"""
from __future__ import annotations

import time
import traceback
from datetime import date
from pathlib import Path

import yaml

QUARANTINE_AFTER = 3
TB_LINES = 14


def load(path) -> dict:
    p = Path(path)
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}


def save(path, h: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(h, allow_unicode=True, sort_keys=True), encoding="utf-8")


def quarantined(h: dict, name: str) -> bool:
    return h.get(name, {}).get("consecutive_failures", 0) >= QUARANTINE_AFTER


def run_phase(name: str, fn, path, today: str | None = None):
    """fn() を実行する。例外は握って health に記録し (False, None) を返す。成功なら (True, 戻り値)。
    隔離中の段階は実行せず (False, None) を返す（skipped として記録する）。"""
    h = load(path)
    today = today or date.today().isoformat()
    e = h.setdefault(name, {"consecutive_failures": 0})
    if quarantined(h, name):
        e["last_skipped"] = today
        save(path, h)
        print(f"[selfheal] {name}: 連続{e['consecutive_failures']}回失敗のため隔離中（飛ばす）。直したら {path} の該当段階を消す")
        return False, None
    t0 = time.time()
    try:
        out = fn()
    except Exception as ex:                                # noqa: BLE001  次の段階を続けるために全部握る（記録は残す）
        tb = traceback.format_exc().strip().splitlines()[-TB_LINES:]
        e.update(consecutive_failures=e.get("consecutive_failures", 0) + 1, last_error=f"{type(ex).__name__}: {ex}",
                 last_traceback="\n".join(tb), last_failed=today, seconds=round(time.time() - t0, 1))
        save(path, h)
        print(f"[selfheal] {name}: 失敗 {type(ex).__name__}: {ex}")
        return False, None
    e.update(consecutive_failures=0, last_ok=today, seconds=round(time.time() - t0, 1))
    e.pop("last_error", None)
    e.pop("last_traceback", None)
    save(path, h)
    return True, out


def failing(h: dict) -> dict:
    return {k: v for k, v in h.items() if v.get("consecutive_failures", 0) > 0}


def render_issue(h: dict) -> str | None:
    """失敗している段階の要約（Issue 本文）。失敗が無ければ None。"""
    f = failing(h)
    if not f:
        return None
    lines = ["日次の自動診断・改善で失敗した段階があります。原因を直す PR を出してください（直ったら閉じる）。", ""]
    for k, v in sorted(f.items()):
        q = "（隔離中: 日次では飛ばされる）" if quarantined(h, k) else ""
        lines += [f"## {k}{q}", f"- 連続失敗: {v['consecutive_failures']} 回 / 最後の失敗: {v.get('last_failed')} / 最後の成功: {v.get('last_ok')}",
                  f"- エラー: `{v.get('last_error')}`", "```", v.get("last_traceback", ""), "```", ""]
    return "\n".join(lines)
