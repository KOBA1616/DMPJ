"""部品探索の端から端まで（S5、2026-11-15）: 部品集め → 自己診断（陽性対照）→ 試し打ち → 物差し → 記録・登録簿の候補。

PR #453/#461 でワーカーが手で回していた流れを1コマンドにする（tools/hunt.py、日次ルーティンからも呼ぶ）。
- 途中再開: 段ごとに out_dir/<段>.json を書き、あれば読み直して次の段から続ける（--fresh で最初から）。
- 再現: 設定（乱数シード・予算・ターン数）と版（git の HEAD）を out_dir/run.json に残し、段ごとのログを out_dir/log.txt に追記する。
- 自己診断: 試し打ちの前に、登録簿の陽性対照（サガ単体、アカシック3＋訪れる魔の時刻＋ナウ・オア・ネバー＋ウォカンナ）を同じ試し打ちにかけ、
  落ちたらその先へ進まず止めて理由を記録する（試し打ちの直し方は自動では決められないため、人に知らせる）。
- 記録: 測った組の値を out_dir/results.json と data/registry/hunt_latest.yaml に書く（足切りしない、値で並べる）。
- 登録簿: 段2の率が register_min 以上の組は、入口局面 data/loops/entry/auto/<id>.json を作り、split=discovered の候補として
  verify.register に通す（登録簿へ書けるのは S4 の検証だけ。通らなければ rejected に記録される）。
カード名で特別扱いはしない。陽性対照は登録簿の中核（loop_entry.core_ids）から読む。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import triples as X

REPO = Path(__file__).resolve().parents[2]


@dataclass
class Config:
    stages: tuple = ("collect2", "collect3", "check", "trial", "measure", "record")
    cheap: bool = False                # 軸がコスト4以下の三角（collect_cheap、時間がかかる）も集める
    max_cost: int = 4
    max_turn_cheap: int = 4
    trial_budget: int = 200
    trial_seeds: int = 2
    trial_turns: int = 2
    measure_seeds: int = 4
    measure_budget: int = 1500
    measure_turns: int = 2             # 入口から何ターン（ruler_control.run_one の max_turn）
    opp_level: int = 1                 # 物差しの相手（search.opponent.resistance。1 = 盾にトリガー）
    top: int = 0                       # 物差しにかける上限（0 = 試し打ちを通った全部）
    register_min: float = 0.75         # 段2の率がこれ以上なら登録簿の候補に通す
    register: bool = True
    workers: int | None = None         # None は DMSIM_WORKERS
    controls: tuple = ("saga", "akashic")


def _git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:   # noqa: BLE001
        return ""


def _bdict(b: X.Base) -> dict:
    return {**asdict(b), "gains": {f"{o}:{z}": v for (o, z), v in b.gains.items()}}


def _base(d: dict) -> X.Base:
    return X.Base(cards=d["cards"], names=d["names"], gains={tuple(k.split(":")): v for k, v in d["gains"].items()},
                  has_win=d["has_win"], unknown=d["unknown"], turn=d["turn"], score=d.get("score", 0.0),
                  layout=d.get("layout", {}), grave=d.get("grave", []))


class Run:
    def __init__(self, rules, out_dir, cfg: Config, log=print):
        self.rules, self.out, self.cfg, self._log = rules, Path(out_dir), cfg, log
        self.out.mkdir(parents=True, exist_ok=True)
        self.by = X.by_card_of(rules)
        from .basebuild import _raw_cards
        self.raw = _raw_cards(rules)

    def log(self, m: str):
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {m}"
        self._log(line)
        with (self.out / "log.txt").open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _path(self, stage):
        return self.out / f"{stage}.json"

    def done(self, stage):
        return self._path(stage).exists()

    def load(self, stage):
        return json.loads(self._path(stage).read_text(encoding="utf-8"))

    def save(self, stage, obj):
        tmp = self._path(stage).with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self._path(stage))

    # ---- 段 ----
    def collect2(self):
        bases, drop = X.collect(self.rules, self.by, max_turn=99, log=self.log)
        return {"bases": [_bdict(b) for b in bases], "drop": dict(drop)}

    def collect3(self):
        bases, drop = X.collect3(self.rules, self.by, log=self.log)
        wins = X.win_cards(self.rules, self.raw)
        prev = [_base(d) for d in self.load("collect2")["bases"]] if self.done("collect2") else []
        zero = [b for b in bases + prev if "zero" in X.static_flags(b)]
        ext = [e for b in zero for e in X.zero_extend(self.rules, self.by, b, wins)]
        out = bases + ext
        if self.cfg.cheap:
            cb, cdrop = X.collect_cheap(self.rules, self.by, max_cost=self.cfg.max_cost, max_turn=self.cfg.max_turn_cheap, log=self.log)
            out += cb
            drop.update({f"cheap:{k}": v for k, v in cdrop.items()})
        return {"bases": [_bdict(b) for b in out], "drop": dict(drop), "zero_extended": len(ext)}

    def _pool(self) -> list[X.Base]:
        seen, out = set(), []
        for st in ("collect2", "collect3"):
            if not self.done(st):
                continue
            for d in self.load(st)["bases"]:
                b = _base(d)
                k = tuple(sorted(b.cards))
                if k in seen or "copy_chain" in X.static_flags(b):   # 山札から別のコピーを出し続けるだけの連鎖は後回し（印）
                    continue
                seen.add(k)
                out.append(b)
        return out

    def control_bases(self) -> list[tuple[str, X.Base]]:
        """陽性対照: 登録簿の入口の中核（ループ部品＋勝ち手段）を静的判定で部品にする。"""
        from ..eval import loop_entry as le
        from . import loop_screen as F
        out = []
        for name in self.cfg.controls:
            # 入口の中核のうちループ部品（part: loop、各 any の最初の組）と、最初の勝ち手段の組（入口と同じ最小の形）
            groups = le.load(name).source.get("core") or []
            ids = []
            for g in groups:
                if g.get("part", "loop") == "loop":
                    ids += list(g["any"][0])
            wg = [g for g in groups if g.get("part") == "win"]
            if wg:
                ids += list(wg[0]["any"][0])
            ids = list(dict.fromkeys(c for c in ids if c in self.rules.cards))
            # 中核すべて（ループ部品＋勝ち手段）を部品にする。置き方は閉路から読む（閉じなければ既定の置き方）
            r, cyc = F.judge_set(ids, self.by, self.rules)
            lay, grave = X.layout_of(cyc[0], ids, self.rules) if cyc else ({}, [])
            best = X.Base(cards=ids, names=[self.rules.cards[x].name for x in ids], gains=X._gains(cyc[0]) if cyc else {},
                          has_win=r is None, unknown=0, turn=None, layout=lay, grave=grave)
            out.append((name, best))
        return out

    def check(self):
        rows = []
        for name, b in self.control_bases():
            if b is None:
                rows.append({"control": name, "ok": False, "why": "中核から静的に閉じる部品が作れない"})
                continue
            r = X.trial(self.rules, b, T=4, seeds=range(1, self.cfg.trial_seeds + 1), budget=max(self.cfg.trial_budget, 1500),
                        raw=self.raw, turns=self.cfg.trial_turns)
            rows.append({"control": name, "cards": b.cards, "ok": r["ok"], "laps": r["laps"], "layout": r["layout"], "why": r["reason"]})
        return {"controls": rows, "ok": all(x["ok"] for x in rows)}

    def trial(self):
        from ..eval.parallel import map_ordered
        pool = self._pool()
        cfg = self.cfg
        self.log(f"試し打ち {len(pool)} 組（予算 {cfg.trial_budget}・{cfg.trial_seeds} シード・{cfg.trial_turns} ターン）")

        def one(b):
            r = X.trial(self.rules, b, T=4, seeds=range(1, cfg.trial_seeds + 1), budget=cfg.trial_budget, raw=self.raw, turns=cfg.trial_turns)
            return {"base": _bdict(b), "ok": r["ok"], "laps": r["laps"], "layout": r["layout"], "reason": r["reason"]}
        # 長い実行が途中で止まっても続きから回せるよう、500 組ごとに途中結果を書く。
        part = self.out / "trial.part.json"
        rows = json.loads(part.read_text(encoding="utf-8"))["rows"] if part.exists() else []
        if rows:
            self.log(f"試し打ち: 途中結果 {len(rows)} 組から再開")
        step = 500
        for k in range(len(rows), len(pool), step):
            rows += map_ordered(one, pool[k:k + step], cfg.workers)
            part.write_text(json.dumps({"rows": rows}, ensure_ascii=False), encoding="utf-8")
            self.log(f"試し打ち {len(rows)}/{len(pool)} 通過 {sum(r['ok'] for r in rows)}")
        from collections import Counter
        return {"rows": rows, "passed": sum(r["ok"] for r in rows), "reasons": dict(Counter(r["reason"] for r in rows if r["reason"]))}

    def spec_of(self, b: X.Base, layout: str) -> "object":
        """入口局面の LoopSpec（ruler_control.run_one が読む形）。部品だけを置き、勝ち手段は part: win（入口の条件に入れない）。"""
        from ..base.loopspec import LoopSpec, Pred
        lo = next(x for x in X.layouts(self.rules, b, self.raw) if x["name"] == layout)
        deck = X.deck_of(self.rules, lo["parts"], self.raw)
        sp = X.entry_spec(self.rules, deck, lo["parts"], 4, 0, lo["layout"], b.grave)
        wins = X.win_cards(self.rules, self.raw)
        minimal = []
        for z in ("bz", "hand", "graveyard"):
            for i in sorted(set(sp["p0"][z]) & set(lo["parts"])):
                minimal.append(Pred(0, {"name": i}, sp["p0"][z].count(i), ">=", z))
        core = [{"any": [{i: 1}], "role": "部品", "part": "win" if i in wins else "loop"} for i in b.cards]
        return LoopSpec(name="+".join(b.names)[:120], kind="deterministic", minimal=minimal,
                        source={"board": {"p0": {z: v for z, v in sp["p0"].items() if z != "deck"}, "p1": sp["p1"], "opp_deck": sp["deck_left"][1], "opp_deck_total": 40}, "deck_list": deck, "core": core,
                                "budget": self.cfg.measure_budget, "note": "部品探索（hunt_pipeline）が作った入口。自分の4ターン目相当（マナ4）"})

    def measure(self):
        from ..eval.parallel import map_ordered
        from ..eval.ruler_control import run_one
        from ..eval import speed_bound as S
        cfg = self.cfg
        rows = [r for r in self.load("trial")["rows"] if r["ok"]]
        if cfg.top:
            rows = rows[:cfg.top]
        self.log(f"物差し {len(rows)} 組（相手の段階 {cfg.opp_level}・{cfg.measure_seeds} シード・予算 {cfg.measure_budget}）")

        def one(r):
            b = _base(r["base"])
            ls = self.spec_of(b, r["layout"])
            gs = [run_one(self.rules, ls, s, max_turn=cfg.measure_turns, budget=cfg.measure_budget, opp_level=cfg.opp_level)
                  for s in range(1, cfg.measure_seeds + 1)]
            wt = [g["win_turn"] for g in gs if g["stage2"] and g["win_turn"] is not None]
            return {"cards": b.cards, "names": b.names, "layout": r["layout"], "trial_laps": r["laps"],
                    "stage1": sum(g["stage1"] for g in gs), "stage2": sum(g["stage2"] for g in gs), "games": len(gs),
                    "best_turn": min(wt) if wt else None, "vias": sorted({str(g["via"]) for g in gs if g["via"]}),
                    "errors": sum(1 for g in gs if g["error"]), "entry_bound": S.static_bound(self.rules, b.cards)["turn"],
                    "spec": json.loads(ls.to_json())}
        out = map_ordered(one, rows, cfg.workers)
        out.sort(key=lambda x: (-x["stage2"], -x["stage1"], x["entry_bound"] or 99, x["best_turn"] or 99))
        return {"rows": out}

    def record(self):
        import yaml
        rows = self.load("measure")["rows"]
        summ = [{k: r[k] for k in ("cards", "names", "stage1", "stage2", "games", "best_turn", "vias", "entry_bound", "layout")}
                for r in rows if r["stage1"]]
        (REPO / "data" / "registry" / "hunt_latest.yaml").write_text(
            "# 部品探索（dmsim/discovery/hunt_pipeline.py）の最新の測定値。足切りしない（登録の対象は register_min 以上の段2だけ）。\n"
            + yaml.safe_dump({"run": json.loads((self.out / "run.json").read_text(encoding="utf-8")), "rows": summ},
                             allow_unicode=True, sort_keys=False), encoding="utf-8")
        regs = []
        if self.cfg.register:
            regs = self.register([r for r in rows if r["games"] and r["stage2"] / r["games"] >= self.cfg.register_min])
        return {"recorded": len(summ), "registered": regs}

    def register(self, rows) -> list[dict]:
        from ..base import registry
        from ..base.loopspec import LoopSpec
        from ..eval.verify import register
        out = []
        known = {tuple(sorted(c["id"] for c in e.get("core", []))) for e in registry.load(registry.PATH).get("entries", [])} \
            if hasattr(registry, "load") else set()
        for r in rows:
            key = tuple(sorted(r["cards"]))
            if key in known:
                out.append({"cards": r["cards"], "skipped": "登録済みと同じ中核"})
                continue
            h = hashlib.blake2b("+".join(key).encode(), digest_size=5).hexdigest()
            cid = f"auto_{h}"
            ep = REPO / "data" / "loops" / "entry" / "auto" / f"{cid}.json"
            ep.parent.mkdir(parents=True, exist_ok=True)
            ep.write_text(LoopSpec.from_json(json.dumps(r["spec"])).to_json(), encoding="utf-8")
            win = "opp_deck_out" if any(v in ("loop",) for v in r["vias"]) else "effect"
            cand = registry.Candidate(
                id=cid, name="＋".join(r["names"])[:200], split="discovered", types=["loop"],
                core=[{"id": c, "name": self.rules.cards[c].name, "role": "部品", "part": p["part"]}
                      for c, p in zip(r["cards"], r["spec"]["source"]["core"])],
                win=win, entry=str(ep.relative_to(REPO)), seeds=list(range(1, 9)), max_turn=self.cfg.measure_turns,
                budget=self.cfg.measure_budget, note=f"部品探索が自動で載せた候補（段2 {r['stage2']}/{r['games']}、相手の段階 {self.cfg.opp_level}）")
            try:
                ev, row = register(self.rules, cand, purpose="tuning")
                out.append({"id": cid, "cards": r["cards"], "passed": ev.passed})
            except Exception as ex:   # noqa: BLE001
                out.append({"id": cid, "cards": r["cards"], "error": f"{type(ex).__name__}: {ex}"[:200]})
            self.log(f"登録簿: {cid} {out[-1]}")
        return out


def run(rules, out_dir, cfg: Config | None = None, *, fresh: bool = False, log=print) -> dict:
    cfg = cfg or Config()
    R = Run(rules, out_dir, cfg, log)
    if fresh:
        for p in R.out.glob("*.json"):
            p.unlink()
    meta = {"config": asdict(cfg), "git": _git_head(), "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    if not (R.out / "run.json").exists():
        (R.out / "run.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    for st in cfg.stages:
        if R.done(st):
            R.log(f"{st}: 済み（再開）")
            continue
        t0 = time.time()
        R.log(f"{st}: 開始")
        res = getattr(R, st)()
        R.save(st, res)
        R.log(f"{st}: 終了 {time.time()-t0:.0f}s " + json.dumps({k: v for k, v in res.items() if not isinstance(v, list)}, ensure_ascii=False)[:300])
        if st == "check" and not res["ok"]:
            R.log("自己診断: 陽性対照が試し打ちで落ちた。先へ進まず止める（試し打ちか部品集めの退行）")
            return {"stopped": "check", "check": res}
    return {"ok": True, "out": str(R.out)}
