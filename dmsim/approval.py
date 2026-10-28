"""承認台帳（data/cards/approvals/<弾>.json）。カード定義とは別に、承認の状態と根拠を持つ。

- def_hash: 承認時のカード定義のハッシュ（source.review 系を除く）。定義が変わると承認は無効。
- uses / vocab_ver: カードが使う語彙（op・キーワード）と、それらの定義のハッシュ。語彙の定義が変わると、使うカードだけ無効。
- by: rule（ルール変換＋動作検証）/ human（開発者モード）。
無効になった承認は status を pending に戻し、reason を残す（再検査して自動承認できる）。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .defs import DATA, core_ops, load_tables

LEDGER = DATA / "cards" / "approvals"        # 弾ごとの <弾>.json を置くディレクトリ（単一の .json ファイルも指定できる）
_SKIP_SRC = {"review", "review_note"}


def _h(obj) -> str:
    return hashlib.blake2b(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode(), digest_size=8).hexdigest()


def def_hash(raw: dict) -> str:
    d = dict(raw)
    d["source"] = {k: v for k, v in (raw.get("source") or {}).items() if k not in _SKIP_SRC}
    return _h(d)


def _walk(o, ops: set):
    if isinstance(o, dict):
        if isinstance(o.get("op"), str):
            ops.add(o["op"])
        for v in o.values():
            _walk(v, ops)
    elif isinstance(o, list):
        for v in o:
            _walk(v, ops)


def vocab_versions(tables=None) -> dict[str, str]:
    """語彙項目ごとの定義ハッシュ。'op:x' / 'kw:x' / 'core'（ゾーン・許可・ターン進行の表）。"""
    zones, keywords, macros, actions, steps = tables or load_tables()
    v = {"core": _h([zones, actions, steps])}
    for name, sig in core_ops().items():
        v[f"op:{name}"] = _h(sig)
    for name, m in macros.items():
        v[f"op:{name}"] = _h(m)
    for name, k in keywords.items():
        v[f"kw:{name}"] = _h(k)
    return v


def uses(raw: dict) -> list[str]:
    ops: set = set()
    _walk(raw, ops)
    kws: set = set(raw.get("keywords") or [])
    for f in raw.get("faces") or []:
        kws |= set(f.get("keywords") or [])
    return sorted({"core"} | {f"op:{o}" for o in ops} | {f"kw:{(k if isinstance(k, str) else k.get('name', k))}" for k in kws
                                                         if isinstance(k, (str, dict))})


def _dump(ledger: dict) -> str:
    return json.dumps(ledger, ensure_ascii=False, indent=0, sort_keys=True) + "\n"


def load(path: Path = LEDGER) -> dict:
    path = Path(path)
    if path.is_dir():
        out = {}
        for f in sorted(path.glob("*.json")):
            out.update(json.loads(f.read_text(encoding="utf-8")))
        return out
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save(ledger: dict, path: Path = LEDGER):
    """ディレクトリなら弾（IDの接頭辞）ごとに分け、内容が変わった弾だけ書く（並行ワーカーの衝突と差分を小さくする）。"""
    path = Path(path)
    if path.suffix == ".json":
        path.write_text(_dump(ledger), encoding="utf-8")
        return
    path.mkdir(parents=True, exist_ok=True)
    groups: dict[str, dict] = {}
    for cid, e in ledger.items():
        groups.setdefault(cid.split("-")[0], {})[cid] = e
    for k, g in groups.items():
        f, text = path / f"{k}.json", _dump(g)
        if not f.exists() or f.read_text(encoding="utf-8") != text:
            f.write_text(text, encoding="utf-8")
    for f in path.glob("*.json"):
        if f.stem not in groups:
            f.unlink()


def entry(raw: dict, status: str, by: str, versions: dict, **extra) -> dict:
    u = uses(raw)
    return {"status": status, "by": by, "def_hash": def_hash(raw), "uses": u,
            "vocab_ver": _h([versions.get(x) for x in u]), **extra}



def stale_reason(e: dict, raw: dict | None, versions: dict) -> str | None:
    """承認済みの項目が古いとき、その理由。有効なら None。"""
    if raw is None:
        return "カード定義が見つからない"
    if def_hash(raw) != e.get("def_hash"):
        return "定義が変わった"
    if _h([versions.get(x) for x in e.get("uses", [])]) != e.get("vocab_ver"):
        changed = [x for x in e.get("uses", []) if versions.get(x) is None]
        return "語彙が削除された: " + ",".join(changed) if changed else "語彙の定義が変わった"
    return None


def invalidate(ledger: dict, raws: dict[str, dict], versions: dict) -> list[str]:
    """承認済みで古くなった項目を pending に戻す。戻した ID を返す。"""
    out = []
    for cid, e in ledger.items():
        if e.get("status") == "approved":
            why = stale_reason(e, raws.get(cid), versions)
            if why:
                e.update(status="pending", stale=why)
                out.append(cid)
    return out


def is_usable(raw: dict, ledger: dict, versions: dict) -> bool:
    """承認済みとして使ってよいか。source の無い試験用カードは常に可。台帳で承認済み（古くない）か、ファイル上で review: approved。"""
    src = raw.get("source")
    if not src:
        return True
    e = ledger.get(raw["id"])
    if e and e.get("status") == "approved" and stale_reason(e, raw, versions) is None:
        return True
    return src.get("review") == "approved" and not (e and e.get("status") != "approved" and e.get("stale"))
