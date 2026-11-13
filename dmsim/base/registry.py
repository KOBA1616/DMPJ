"""検証済みコンボの登録簿（S0、ロードマップ P2「登録簿」、設計 docs/registry-design.md）。

- 入力: 候補 Candidate（中核の札・入口局面か手順・勝ち方・型・区分・測り方の設定）と、S4 の検証結果 Evidence。
- 出力: query（大局観 S3・発見 S5 が読む照会）。holdout は for_tuning=True の照会に出さない。
- 書き込み: record だけ。Evidence が候補と同じ指紋で、S4 の検証役（ISSUER）が出したものだけ受け付ける。
  通ったものは entries、落ちたものは rejected に「どの検証で落ちたか」と一緒に残す（再挑戦の材料）。
  record を呼んでよいのは dmsim/eval/verify.py だけ（tests/test_registry.py が確かめる）。
- 新規性: novelty は登録済みと中核の札の集合を比べるだけの最小版（同じ／含む／含まれる／重なる）。仕組み（1周の差分）の比較はしない。

他の層を import しない。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from . import store

TYPES = ("loop", "resource", "attack", "lock")        # 設計書 §11 の類型（重複可）
SPLITS = ("tuning", "holdout", "discovered")         # discovered = システムが見つけた新規（調整に使ってよいかは tuning と同じ扱い）
WINS = ("opp_deck_out", "effect", "lock", "beat")
ISSUER = "dmsim.eval.verify"
PATH = store.REPO / "data" / "registry" / "combos.yaml"


class RegistryError(ValueError):
    pass


@dataclass
class Candidate:
    id: str
    name: str
    split: str
    types: list[str]
    core: list[dict]                          # [{id, name, role}]。role は自由記述（エンジン・回収・勝ち手段 など）
    win: str                                  # WINS のどれか
    entry: str | None = None                  # 入口局面（data/loops/entry/*.json）。無ければ procedure だけ
    procedure: list[str] = field(default_factory=list)
    lock_mode: str = "passive"                # ロック型: passive（lock_probe）/ active（自分が毎ターン動く）
    seeds: list[int] = field(default_factory=lambda: list(range(1, 9)))
    max_turn: int = 2
    budget: int | None = None                 # None は入口局面の既定
    note: str = ""

    def __post_init__(self):
        if self.split not in SPLITS:
            raise RegistryError(f"split は {SPLITS}: {self.split!r}")
        bad = [t for t in self.types if t not in TYPES]
        if not self.types or bad:
            raise RegistryError(f"types は {TYPES} から1つ以上: {self.types!r}")
        if self.win not in WINS:
            raise RegistryError(f"win は {WINS}: {self.win!r}")
        if self.lock_mode not in ("passive", "active"):
            raise RegistryError(f"lock_mode: {self.lock_mode!r}")

    def core_ids(self) -> set[str]:
        return {c["id"] for c in self.core if c.get("id")}

    def to_dict(self) -> dict:
        return asdict(self)

    def digest(self) -> str:
        return hashlib.sha1(json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]

    @classmethod
    def from_dict(cls, d: dict) -> "Candidate":
        keys = cls.__dataclass_fields__
        return cls(**{k: v for k, v in d.items() if k in keys})


@dataclass
class Evidence:
    candidate_digest: str
    passed: bool
    checks: list[dict]                        # [{name, ok, detail}]。順に行い、最初に落ちた所で止める
    measured: dict = field(default_factory=dict)   # 段1・段2の到達率、勝ち方の内訳、シードごとの行
    version: dict = field(default_factory=dict)    # {fingerprint, commit, measured_at}
    issuer: str = ""

    def failed_at(self) -> str | None:
        return next((c["name"] for c in self.checks if not c["ok"]), None)


def load(path: Path = PATH) -> dict:
    p = Path(path)
    if not p.exists():
        return {"entries": [], "rejected": []}
    d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {"entries": d.get("entries") or [], "rejected": d.get("rejected") or []}


def record(cand: Candidate, ev: Evidence, *, path: Path = PATH, purpose: str = "eval") -> dict:
    """検証結果を登録簿に書く唯一の入口。通れば entries、落ちれば rejected（同じ id は置き換え）。"""
    store.check(purpose, "holdout" if cand.split == "holdout" else "tuning")
    if ev.issuer != ISSUER:
        raise RegistryError(f"S4 の検証（{ISSUER}）を通っていない結果は書けない: issuer={ev.issuer!r}")
    if ev.candidate_digest != cand.digest():
        raise RegistryError("検証結果が別の候補（指紋が違う）のもの")
    if ev.passed and ev.failed_at():
        raise RegistryError("passed なのに落ちた検証がある")
    row = {**cand.to_dict(), "digest": ev.candidate_digest, "checks": ev.checks, "measured": ev.measured, "version": ev.version}
    reg = load(path)
    for k in ("entries", "rejected"):
        reg[k] = [r for r in reg[k] if r["id"] != cand.id]
    if ev.passed:
        reg["entries"].append(row)
    else:
        reg["rejected"].append({**row, "failed_at": ev.failed_at()})
    for k in ("entries", "rejected"):
        reg[k].sort(key=lambda r: r["id"])
    head = "# 検証済みコンボの登録簿（dmsim/base/registry.py）。手で書き換えない: tools/registry.py が dmsim/eval/verify.py を通して書く。\n"
    store.write_text(path, head + yaml.safe_dump(reg, allow_unicode=True, sort_keys=False, width=200), purpose=purpose,
                     split="holdout" if cand.split == "holdout" else None)
    return row


def query(*, types: str | list[str] | None = None, split: str | None = None, for_tuning: bool = False,
          core_id: str | None = None, win: str | None = None, path: Path = PATH) -> list[dict]:
    """登録済み（検証を通った）コンボの照会。for_tuning=True は holdout を除く（調整に使う経路はこれを使う）。"""
    want = {types} if isinstance(types, str) else set(types or ())
    out = []
    for r in load(path)["entries"]:
        if for_tuning and r["split"] == "holdout":
            continue
        if split and r["split"] != split:
            continue
        if want and not want & set(r["types"]):
            continue
        if core_id and core_id not in {c.get("id") for c in r["core"]}:
            continue
        if win and r["win"] != win:
            continue
        out.append(r)
    return out


def novelty(cand: Candidate, *, path: Path = PATH, include_holdout: bool = True) -> list[dict]:
    """最小版の新規性: 登録済み（と落ちた候補）と中核の札の集合を比べる。空なら重なりなし。
    relation: same（同じ中核）/ superset（候補が登録済みを含む）/ subset（候補が登録済みに含まれる＝部品が少ない別版の可能性）/ overlap。
    仕組み（1周の差分・勝ち方）が同じかは見ない（設計 docs/registry-design.md §5 の次段）。"""
    mine = cand.core_ids()
    reg = load(path)
    out = []
    for status, rows in (("entry", reg["entries"]), ("rejected", reg["rejected"])):
        for r in rows:
            if r["id"] == cand.id or (not include_holdout and r["split"] == "holdout"):
                continue
            theirs = {c["id"] for c in r["core"] if c.get("id")}
            common = mine & theirs
            if not common:
                continue
            rel = "same" if mine == theirs else "superset" if mine > theirs else "subset" if mine < theirs else "overlap"
            out.append({"id": r["id"], "status": status, "relation": rel, "common": sorted(common),
                        "same_win": r["win"] == cand.win})
    return out
