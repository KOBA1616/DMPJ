"""エンジン疑似API（プロセス内ライブラリ）の参照実装。Python 版エンジンをこの形で包む。

目的: 探索・チューナー・自動診断・カード検証・対戦記録・差分検証が、同じ小さな操作の集合からエンジンを使えるようにする。
Rust 版（rust/dmcore）も同じ操作を満たす（notes/engine-api-v0.md）。ネットワークのサーバーではない。

2層の作り:
  - 熱い経路（探索の内側）: ハンドルを持ち回る関数呼び出し。fork / apply(番号) / digest / decision は JSON 化しない。
  - 冷たい経路（ログ・差分・ツール・将来の外部連携）: 入出力は JSON で表せる辞書。to_message / from_message で往復できる。

操作: open / decision / apply / fork / checkpoint / rollback / observe / digest / expand / trace / run / diff_states / lockstep
"""
from __future__ import annotations

from typing import Callable

from . import scenario as sc
from .engine import Engine
from .play import passive_policy, random_policy  # noqa: F401  (方策 id の解決用)

API_VERSION = "0.1"


class Session:
    """1局面を持つ操作の窓口。fork() で独立した枝を作る（clone）。"""

    def __init__(self, eng: Engine, rules, spec: dict):
        self.eng, self.rules, self.spec = eng, rules, spec
        self._ckpt: list[Engine] = []
        self._events: list[dict] = []

    # ---- 開く（局面の注入を含む） ----
    @classmethod
    def open(cls, rules, spec: dict, **kw) -> "Session":
        """spec: {"kind":"new_game","decks":[[..],[..]],"seed":n,"first_player":p} /
                 {"kind":"scenario","scenario":{...}}（配置を指定して始める。dmsim.scenario の spec）"""
        k = spec.get("kind", "new_game")
        if k == "scenario":
            eng = sc.build(rules, spec["scenario"], **kw)
        elif k == "new_game":
            eng = Engine.new_game(rules, spec["decks"], spec.get("seed", 1), spec.get("first_player", 0), **kw)
        else:
            raise ValueError(f"unknown spec kind: {k}")
        return cls(eng, rules, spec)

    # ---- 観測 ----
    def decision(self) -> dict | None:
        """次の決定（なければ None = 終局）。{id, player, kind, options[{key,...}], min, max, prompt}。
        id は「ここまでの選択の数」で、同じ局面なら必ず同じ値（差分検証の位置合わせに使う）。"""
        d = self.eng.advance()
        if d is None:
            return None
        return {**d, "id": len(self.eng.log)}

    def result(self) -> dict | None:
        return self.eng.s.result

    def digest(self) -> str:
        return self.eng.s.digest()

    def observe(self, view: str = "full") -> dict:
        """状態の JSON 表現。view="full" は全体、"player:N" は N から見えない札（相手の手札・両者の山札・裏向きシールド）を伏せる。"""
        import json
        from dataclasses import asdict
        st = json.loads(self.eng.s.to_json()) if view == "full" else asdict(self.eng.s)
        if view == "full":
            return st
        viewer = int(view.split(":")[1])
        for c in st["cards"]:
            hidden = c["zone"] in ("deck", "shield") or (c["zone"] == "hand" and c["owner"] != viewer)
            if hidden and not c.get("face_up"):
                c["defn"] = None
        return st

    def read(self, what: str, *a):
        """読み取り専用の問い合わせ（状態を変えない）: zone(z,p) / bz_tops(p) / chars(cid) / card(cid)。"""
        e = self.eng
        if what == "zone":
            return list(e.zlist(a[0], a[1]))
        if what == "bz_tops":
            return list(e.bz_tops(*a))
        if what == "chars":
            return e.chars(a[0])
        if what == "card":
            c = e.s.cards[a[0]]
            return {"cid": c.cid, "defn": c.defn, "zone": c.zone, "owner": c.owner, "controller": c.controller,
                    "tapped": c.tapped, "gen": c.gen}
        raise ValueError(what)

    # ---- 操作 ----
    def apply(self, answer: list[int] | dict, digest: bool = False) -> dict:
        """答えを適用して次の決定まで進める。answer は番号のリスト、または {"keys": [...]}（key で選ぶ）。
        戻り値（JSON 化できる）: {applied:{p,kind,choice,keys}, decision|None, result[, digest]}。
        digest は重い（状態全体のハッシュ）ので、要るときだけ digest=True（熱い経路では付けない）。"""
        d = self.eng.s.waiting or self.eng.advance()
        if d is None:
            raise RuntimeError("no decision pending")
        if isinstance(answer, dict):
            keys = [o["key"] for o in d["options"]]
            answer = [keys.index(k) for k in answer["keys"]]
        self.eng.answer(answer)
        applied = dict(self.eng.log[-1])
        nxt = self.decision()
        out = {"applied": applied, "decision": nxt, "result": self.eng.s.result}
        if digest:
            out["digest"] = self.digest()
        if self.eng.s.trace is not None:
            out["trace"] = self.eng.s.trace[:]
            self.eng.s.trace.clear()
        return out

    def fork(self) -> "Session":
        """独立した枝（clone）。親には影響しない。"""
        return Session(self.eng.clone(), self.rules, self.spec)

    def checkpoint(self) -> int:
        self._ckpt.append(self.eng.clone())
        return len(self._ckpt) - 1

    def rollback(self, cid: int) -> None:
        """checkpoint の時点に戻す（それ以降の checkpoint は捨てる）。"""
        self.eng = self._ckpt[cid].clone()
        del self._ckpt[cid + 1:]

    def expand(self, answers: list[list[int]] | None = None) -> list[dict]:
        """探索向けの一括展開: 現在の決定の各答え（省略時は単一選択の全選択肢）ごとに fork して適用し、
        [{answer, decision, result, session}]（digest は ch.session.digest() で） を返す。呼び出し回数を減らすための API。"""
        d = self.decision()
        if d is None:
            return []
        if answers is None:
            answers = [[i] for i in range(len(d["options"]))] if d["min"] <= 1 <= d["max"] else []
        out = []
        for a in answers:
            ch = self.fork()
            r = ch.apply(a)
            out.append({"answer": a, "decision": r["decision"], "result": r["result"], "session": ch})
        return out

    def trace(self, on: bool = True) -> None:
        """誘発の因果の記録（state.trace）の入り切り。apply の戻り値に trace が付く。"""
        self.eng.s.trace = [] if on else None

    # ---- 記録 ----
    def log(self) -> list[dict]:
        return [dict(e) for e in self.eng.log]


# ---- 方策と実行 ----

def resolve_policy(pid: str) -> Callable:
    """方策 id: "first"（最初の選択肢）/ "passive" / "random:<seed>" / "greedy"。"""
    if pid == "first":
        return lambda eng, d: list(range(d["min"])) if d["min"] > 0 else [0] if d["max"] >= 1 else []
    if pid == "passive":
        return passive_policy
    if pid.startswith("random:"):
        import random
        return random_policy(random.Random(int(pid.split(":")[1])))
    if pid == "greedy":
        from .verify import greedy_policy
        return greedy_policy
    raise ValueError(pid)


def run(sess: Session, policy: str | Callable = "first", max_decisions: int = 100000) -> dict | None:
    pol = resolve_policy(policy) if isinstance(policy, str) else policy
    for _ in range(max_decisions):
        d = sess.decision()
        if d is None:
            return sess.result()
        sess.apply(pol(sess.eng, d))
    raise RuntimeError("decision limit")


# ---- 差分検証 ----

def diff_states(a: dict, b: dict, path: str = "") -> list[dict]:
    """2つの状態（JSON の辞書）の差を、JSON ポインタつきで返す: [{path, a, b}]。"""
    if type(a) is not type(b):
        return [{"path": path or "/", "a": a, "b": b}]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append({"path": f"{path}/{k}", "a": a.get(k), "b": b.get(k)})
            else:
                out += diff_states(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [{"path": path, "a": a, "b": b}]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff_states(x, y, f"{path}/{i}")
        return out
    return [] if a == b else [{"path": path, "a": a, "b": b}]


def lockstep(a: Session, b: Session, policy: str | Callable = "random:1", max_decisions: int = 100000) -> dict:
    """2つの実装（Python 版と Rust 版など）を、同じ方策で 1 決定ずつ並走させて比べる。
    毎決定で ①決定の kind・player・選択肢（key と順序と中身）②適用後の digest を比べ、最初のずれを返す。
    方策は a の決定から選び、同じ答えを b に適用する。戻り値: {ok, steps, divergence|None}"""
    pol = resolve_policy(policy) if isinstance(policy, str) else policy
    da, db = a.decision(), b.decision()
    for step in range(max_decisions):
        if da != db:
            return {"ok": False, "steps": step, "divergence": {"at": "decision", "a": da, "b": db}}
        if da is None:
            return {"ok": a.digest() == b.digest() and a.result() == b.result(), "steps": step, "divergence": None}
        ans = pol(a.eng, da)
        ra, rb = a.apply(ans, digest=True), b.apply(ans, digest=True)
        if ra["digest"] != rb["digest"]:
            return {"ok": False, "steps": step + 1, "divergence": {
                "at": "digest", "answer": ans, "diff": diff_states(a.observe(), b.observe())[:20]}}
        da, db = ra["decision"], rb["decision"]
    raise RuntimeError("decision limit")
