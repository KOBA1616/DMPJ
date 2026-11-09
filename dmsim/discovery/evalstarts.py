"""LoopSpec から評価用の開始局面を作る（計画書 §3.3 の 1・2・3）。エンジンとカードデータには触れない。

LoopSpec の source に残した「盤面 board ＋ 勝ちの手順 steps」を再生し、手順の途中のターン頭
（自分のターン開始・最初の決定がマナチャージ）で局面を書き出す。勝ちまであと何手かが「難しさの段階」。
書き出した局面は dmsim.scenario.build の spec としてそのまま読め、評価ハーネスの start_spec に使える。

- split: 既定は "tuning"（調整用）のみ。検証専用（"validation"）には自動では入れない（探索が見つけた局面で
  同じ探索を測ると自己採点になるため。検証専用は人の提供のみ）。
- unverified: 局面に変換未確認（承認前）のカードが含まれるなら、そのID一覧を付ける。主指標には使わない。
- 山札・盾・マナ・墓地・手札・場はカードIDの並びで写す。タップ状態・盾の束・カウンタなど、ターン頭で
  ゾーンの並びに現れない状態は写せない（lossy に印を付けて残す）。
"""
from __future__ import annotations

import hashlib
import json

from .. import scenario
from ..engine.core import IllegalAnswer
from .loopspec import LoopSpec
from ..engine_view import active_of, defn_of, result_of, turn_of, zone_of

VERSION = 1


def _steps(ls: LoopSpec) -> list[tuple[str, tuple[str, ...], tuple[int, ...]]]:
    return [(k, tuple(keys), tuple(idx)) for k, keys, idx in ls.source["steps"]]


def _answer(e, kind, keys, idx) -> bool:
    d = e.advance()
    if d is None or result_of(e) is not None or d["kind"] != kind:
        return False
    ks = [o["key"] for o in d["options"]]
    pick, used = [], set()
    for j, key in zip(idx, keys):
        cand = j if j < len(ks) and ks[j] == key and j not in used else next((i for i, k2 in enumerate(ks) if k2 == key and i not in used), None)
        if cand is None:
            return False
        pick.append(cand)
        used.add(cand)
    try:
        e.answer(pick)
    except IllegalAnswer:
        return False
    return True


def export_spec(rules, e, base: dict) -> dict:
    """エンジンの今の局面を scenario spec に写す（ゾーンの並びのみ）。base は元の spec（filler・seed・deck_size など）。"""
    spec = {k: v for k, v in base.items() if k not in ("p0", "p1", "deck_left")}
    for p in (0, 1):
        spec[f"p{p}"] = {z: [defn_of(e, c) for c in zone_of(e, z, p)] for z in rules.zones if zone_of(e, z, p) and z not in ("gr",)}
    spec["deck_exact"] = [True, True]
    spec["deck_size"] = 0
    return spec


def boundaries(rules, ls: LoopSpec, prepare=None) -> list[dict]:
    """手順を再生し、自分のターン頭ごとに {step, remaining, turn, spec} を返す。remaining は勝ちまでの残り決定数。"""
    steps = _steps(ls)
    board = ls.source["board"]
    e = scenario.build(rules, board)
    if prepare:
        prepare(e)
    out = []
    for i, (kind, keys, idx) in enumerate(steps):
        d = e.advance()
        if d is None or result_of(e) is not None:
            break
        if d["kind"] == "charge" and active_of(e) == 0 and (not out or turn_of(e) != out[-1]["turn"]):
            out.append({"step": i, "remaining": len(steps) - i, "turn": turn_of(e), "spec": export_spec(rules, e, board)})
        if not _answer(e, kind, keys, idx):
            break
    return out


def approved_ids(rules_approved) -> set[str]:
    return set(rules_approved.cards.keys())


def unverified_cards(spec: dict, approved: set[str]) -> list[str]:
    ids = {n for p in ("p0", "p1") for zl in (spec.get(p) or {}).values() for n in zl}
    return sorted(n for n in ids if n not in approved)


def make_starts(rules, ls: LoopSpec, approved: set[str], levels: list[int] | None = None, prepare=None, split: str = "tuning") -> list[dict]:
    """levels: 勝ちまでの残り決定数の目安（それ以上で最も近いターン頭を選ぶ）。省略時は全てのターン頭。
    1つの局面 = {id, loop, level, remaining, turn, split, unverified, lossy, spec}。"""
    if split != "tuning":
        raise ValueError("検証専用への自動追加はしない（人の提供のみ）")
    bs = boundaries(rules, ls, prepare)
    if levels is not None:
        chosen = []
        for n in levels:
            ok = [b for b in bs if b["remaining"] >= n]
            if ok:
                b = min(ok, key=lambda b: b["remaining"])
                if b not in chosen:
                    chosen.append(b)
        bs = chosen
    out = []
    for b in bs:
        body = json.dumps(b["spec"], sort_keys=True, ensure_ascii=False)
        uv = unverified_cards(b["spec"], approved)
        out.append({"id": f"{ls.name}@{b['remaining']}-{hashlib.sha1(body.encode()).hexdigest()[:8]}", "loop": ls.name, "version": VERSION,
                    "level": b["remaining"], "remaining": b["remaining"], "turn": b["turn"], "split": split,
                    "unverified": uv, "use_for_primary": not uv, "lossy": True, "spec": b["spec"]})
    return out
