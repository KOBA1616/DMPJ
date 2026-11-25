"""コンボ発見 v3・モデル提案（属性近傍置換）: 既知エンジンの一般化を属性表現から求める。

方針（2026-11-25 ユーザー提示）: コンボ発見は ID の静的列挙ではなく、ID を排した
属性表現のモデルから求める。Phase 26-4 の属性ベクトル（dmsim/ai/attributes.py、
全カード 294 次元、語彙データから決定的生成）の近傍で既知コアのカードを置換し、
「既知コンボの一般化」候補を作って v3 判定（judge_engine3 / judge_conversion3）で検証する。

種（既知エンジン）と置換パターン:
  A サガ置換:      サガの近傍カード単独×2（サガの役割を担える別カードがあるか）
  B XENARCH 置換:  サガ×2 ＋ XENARCH の近傍×2（出力リソースを変える相方の一般化）
  C サガ相方探索:  サガ×2 ＋ サガの近傍×2（優先度は A・B の次）
  D アカシック置換: 最小コア4種のうち1種をその近傍に置換（枚数は元のまま）

提案からの除外: 既知コアのカード自身、および v3 発見ランで除外した既知コア集合
（tools/combo_hunt3_run.KNOWN_CORE の17種＋XENARCH = 18種）。加えて、種カードと
同名のカード（別セットの同名再録）は「同じカード」として除く。同名判定は既知コア
18種の名前にも適用する（dmrp12-s01 は rules.cards のエイリアスで、正規 ID は
dm25sp1-003 のため、ID だけでは再録を拾えない）。

使い方:
  PYTHONPATH=. python tools/combo_hunt3_propose.py --list-only
      近傍と候補の一覧だけを出す（判定しない）。
  PYTHONPATH=. python tools/combo_hunt3_propose.py --out proposals_attr.jsonl
      全候補を v3 判定する。結果は1候補1行で追記し、記録済みは飛ばす（再開可能）。
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np  # noqa: E402

from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.ai.attributes import build_attribute_matrix  # noqa: E402
from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.discovery import hunt3  # noqa: E402
from tools.combo_hunt3_run import KNOWN_CORE  # noqa: E402

SAGA = "dm22ex2-021"
XENARCH = "dm22rp2x-004"
AKASHIC_CORE = {"dm23ex2-009": 1, "dm23bd7-035": 2, "dm24ex1-038": 1, "dmrp12-s01": 1}
# dmrp12-s01 はエイリアス（rules.cards のキーには無い）。属性空間での正規 ID:
HOLYEND_CANONICAL = "dm25sp1-003"
SEED_CANONICAL = {SAGA: SAGA, XENARCH: XENARCH,
                  "dm23ex2-009": "dm23ex2-009", "dm23bd7-035": "dm23bd7-035",
                  "dm24ex1-038": "dm24ex1-038", "dmrp12-s01": HOLYEND_CANONICAL}

EXCLUDE_IDS = set(KNOWN_CORE) | {XENARCH, HOLYEND_CANONICAL}

# パターン別の近傍取得数
N_SAGA_SUB = 25
N_XENARCH_SUB = 40
N_SAGA_PARTNER = 25
N_AKASHIC_SUB = 10


def _exclude_names(rules) -> set[str]:
    names = set()
    for cid in EXCLUDE_IDS:
        cd = rules.cards.get(cid)
        if cd is not None and cd.name:
            names.add(cd.name)
    return names


def neighbors(rules, vocab, unit, seed_id: str, n: int, exclude_names: set[str]) -> list[dict]:
    """種カードの属性近傍（コサイン類似上位 n 件）。既知コア・同名カード・種自身を除く。"""
    i = vocab.index[seed_id]
    sims = unit @ unit[i]
    order = np.argsort(-sims)
    seed_name = rules.cards[seed_id].name
    out = []
    for j in order:
        if j == 0:
            continue
        cid = vocab.ids[j - 1]
        if cid == seed_id or cid in EXCLUDE_IDS:
            continue
        nm = rules.cards[cid].name
        if nm == seed_name or nm in exclude_names:
            continue
        out.append({"card": cid, "name": nm, "sim": round(float(sims[j]), 4)})
        if len(out) >= n:
            break
    return out


def build_candidates(rules, vocab, unit) -> tuple[list[dict], dict]:
    """置換パターンで候補を作る。候補は {cards, pattern, seed_card, replaced, with, sim}。

    同一のカード集合が複数パターンで生成された場合は最初のパターンを残し、
    also_patterns に併記する。
    """
    exclude_names = _exclude_names(rules)
    neigh: dict[str, list[dict]] = {}

    def get_neigh(seed: str, n: int) -> list[dict]:
        key = f"{seed}:{n}"
        if key not in neigh:
            neigh[key] = neighbors(rules, vocab, unit, SEED_CANONICAL[seed], n, exclude_names)
        return neigh[key]

    raw: list[dict] = []

    def add(cards: dict, pattern: str, seed: str, replaced: str, nb: dict):
        raw.append({"cards": dict(cards), "pattern": pattern, "seed_card": seed,
                    "replaced": replaced, "with": nb["card"], "sim": nb["sim"]})

    for nb in get_neigh(SAGA, N_SAGA_SUB):
        add({nb["card"]: 2}, "A_saga_sub", SAGA, SAGA, nb)
    for nb in get_neigh(XENARCH, N_XENARCH_SUB):
        add({SAGA: 2, nb["card"]: 2}, "B_xenarch_sub", XENARCH, XENARCH, nb)
    for nb in get_neigh(SAGA, N_SAGA_PARTNER):
        add({SAGA: 2, nb["card"]: 2}, "C_saga_partner", SAGA, SAGA, nb)
    for slot in AKASHIC_CORE:
        for nb in get_neigh(slot, N_AKASHIC_SUB):
            cards = dict(AKASHIC_CORE)
            cnt = cards.pop(slot)
            cards[nb["card"]] = cards.get(nb["card"], 0) + cnt
            add(cards, "D_akashic_sub", slot, slot, nb)

    seen: dict[str, dict] = {}
    for c in raw:
        key = json.dumps(c["cards"], sort_keys=True)
        if key in seen:
            seen[key].setdefault("also_patterns", []).append(c["pattern"])
        else:
            seen[key] = c
    neigh_dump = {seed: get_neigh(seed, 30) for seed in
                  [SAGA, XENARCH, *AKASHIC_CORE]}
    return list(seen.values()), neigh_dump


def _engine_summary(v: dict, rules) -> dict:
    core = v.get("core")
    return {"pass": v["pass"], "kinds": v["kinds"], "delta": v["delta"],
            "grown": v["grown"], "within_turn": v["within_turn"],
            "own_turns": v["own_turns"], "core": core,
            "core_names": ({cid: rules.cards[cid].name for cid in core} if core else None),
            "necessity": {k: x["necessary"] for k, x in (v.get("necessity") or {}).items()}}


# 既知エンジン（最小コアと増分の組）。これと一致する合格は「既知の再検出」で、
# 変換は v3 対照で確立済みのため再判定しない（新規性がある場合のみ変換を見る）。
KNOWN_ENGINES = [
    ({SAGA: 2}, {"deck:0": -1, "graveyard:0": 1}),
    ({SAGA: 2, XENARCH: 2}, {"deck:0": -1, "hand:0": 1}),
    (dict(AKASHIC_CORE), {"deck:1": -1, "graveyard:1": 1}),
]


def _is_known_engine(core: dict, delta: dict | None) -> bool:
    return any(core == kc and delta == kd for kc, kd in KNOWN_ENGINES)


def judge_candidate(rules, by_card, catalog3, cand: dict, budget: int, conv_limit: int) -> dict:
    t0 = time.time()
    rec = dict(cand)
    rec["names"] = {cid: rules.cards[cid].name for cid in cand["cards"]}
    try:
        v = hunt3.judge_engine3(rules, cand["cards"], by_card, budget=budget, seeds=(1,))
        rec["engine"] = _engine_summary(v, rules)
        rec["engine_rows"] = v["rows"]
        if v["pass"] and _is_known_engine(v.get("core") or cand["cards"], v["delta"]):
            rec["conversion"] = "skipped_known_engine"
        elif v["pass"]:
            core = v.get("core") or cand["cards"]
            convs = []
            for pc in hunt3.pair_conversions3(v["delta"], v["kinds"], catalog3, limit=conv_limit):
                cv = hunt3.judge_conversion3(rules, core, [pc["card"]], by_card,
                                             engine_budget=budget, conv_budget=budget,
                                             seeds=(1,), delta=v["delta"])
                convs.append({"card": pc["card"], "name": pc["name"], "zones": pc["zones"],
                              "pass": cv["pass"], "rows": cv["rows"]})
            rec["conversion"] = convs
    except Exception as e:  # 1候補の失敗で全体を止めない
        rec["error"] = f"{type(e).__name__}: {e}"
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="結果 JSONL（追記・再開可能）")
    ap.add_argument("--neighbors-out", default=None, help="近傍の一覧 JSON の出力先")
    ap.add_argument("--list-only", action="store_true")
    ap.add_argument("--budget", type=int, default=1000)
    ap.add_argument("--conv-limit", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--patterns", default=None, help="対象パターンのカンマ区切り（並行実行用）")
    a = ap.parse_args(argv)

    rules = load_rules()
    vocab = Vocab(rules)
    mat, feat_names = build_attribute_matrix(rules, vocab)
    assert mat.shape[1] == 294, mat.shape
    norms = np.linalg.norm(mat, axis=1)
    norms[norms == 0] = 1.0
    unit = mat / norms[:, None]

    cands, neigh_dump = build_candidates(rules, vocab, unit)
    if a.patterns:
        pats = set(a.patterns.split(","))
        cands = [c for c in cands if c["pattern"] in pats]
    if a.neighbors_out:
        Path(a.neighbors_out).write_text(
            json.dumps({"features": len(feat_names), "neighbors": neigh_dump},
                       ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print("候補内訳:", dict(Counter(c["pattern"] for c in cands)), "合計", len(cands), flush=True)
    for seed, nbs in neigh_dump.items():
        print(f"近傍 {rules.cards[SEED_CANONICAL[seed]].name}: "
              + ", ".join(f"{n['name']}({n['sim']})" for n in nbs[:5]), flush=True)
    if a.list_only:
        for c in cands:
            print(json.dumps(c, ensure_ascii=False), flush=True)
        return 0

    by_card = hunt3.bundles_by_card(rules)
    catalog3 = hunt3.conversion_catalog3(rules, by_card)
    done = set()
    if a.out and Path(a.out).exists():
        for line in Path(a.out).read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.dumps(json.loads(line)["cards"], sort_keys=True))
    n_pass = 0
    for i, cand in enumerate(cands):
        if a.limit and i >= a.limit:
            break
        key = json.dumps(cand["cards"], sort_keys=True)
        if key in done:
            continue
        rec = judge_candidate(rules, by_card, catalog3, cand, a.budget, a.conv_limit)
        eng = rec.get("engine") or {}
        if eng.get("pass"):
            n_pass += 1
        print(f"[{i+1}/{len(cands)}] {cand['pattern']} {' + '.join(rec['names'].values())}: "
              f"{'合格' if eng.get('pass') else '不合格'}"
              + (f" core={eng.get('core')} delta={eng.get('delta')}" if eng.get("pass") else "")
              + (f" ERROR={rec['error']}" if rec.get("error") else "")
              + f" ({rec['seconds']}s)", flush=True)
        if a.out:
            with Path(a.out).open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"完了: エンジン合格 {n_pass} 件", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
