"""ループ／ロックの検出とストック（設計判断⑦）。

状態を「骨格」と「カウンタ」に分ける。
- 骨格: バトルゾーン（カード名・タップ・召喚酔い・重なり）、手札の中身、待機中の効果、継続的効果、
        ステップ、決定待ちの種類と選択肢。ここが同じなら「同じ局面に戻った」とみなす。
- カウンタ: zones.yaml で counter: true のゾーンの枚数（山札・墓地・マナ・シールドなど）と、未タップのマナ数。
同じ骨格に戻る行動列が見つかったら、カウンタの差分 Δ を取り、Δ×N 回で勝てるかを判定する（LoopCertificate）。
period="in_turn" は1ターン内のループ、"round" は自分＋相手のターンを1周とするロック。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .core import Engine
from .core import IllegalAnswer


def abstract(eng: Engine, period: str = "in_turn", hand_keys: set[str] | None = None) -> tuple[str, dict[str, int]]:
    """hand_keys を渡すと、手札はその名前のカードだけを骨格に入れ、残りは枚数（hand:p）だけのカウンタにする。
    ドローを含むループ・ロックでは、引いたカードで骨格が変わらないようにこれを使う。"""
    s = eng.s
    zones = eng.rules.zones

    def name(c):
        return s.cards[c].defn

    skel = {
        "active": s.active, "step": s.step,
        "turn": s.turn if period == "in_turn" else None,
        "bz": sorted([s.cards[c].controller, name(c), s.cards[c].tapped, s.cards[c].entered_turn == s.turn,
                      sorted(name(u) for u in s.cards[c].under)] for c in eng.bz_tops()),
        "pending": sorted([p["kind"], p["defn"], p["ab"], p["controller"], p["win"]] for p in s.pending),
        "cont": sorted([json.dumps(ce["mod"], sort_keys=True), ce["duration"],   # affected=None は filter で範囲を見る効果
                        sorted(name(r[0]) for r in ce["affected"] or [] if s.alive(r)),
                        json.dumps(ce.get("filter"), sort_keys=True)] for ce in s.continuous),
        "hold": sorted(name(c) for c in s.hold),
        "tasks": [[t["t"], t.get("phase"), t.get("pc"), t.get("i"), t.get("sub")] for t in s.tasks],
        "waiting": None if s.waiting is None else [s.waiting["kind"], s.waiting["player"]] + (
            [] if hand_keys is not None else [sorted(o["key"] for o in s.waiting["options"])]),
        "delayed": sorted(json.dumps([d["when"], d["effect"], d["duration"]], sort_keys=True) for d in s.delayed),
        "step_mods": sorted(json.dumps(m, sort_keys=True) for m in s.step_mods),
    }
    for p in (0, 1):   # シールドの束（113.2）の中身は骨格に入れる。単独のシールドは従来どおり枚数だけ（counter）。
        # 束の中身は非公開情報（裏向き）。これはエンジン内部の骨格で、観測（相手や AI に見せる情報）には含めない。
        # 同じカードが積み増されるだけの周回で骨格が変わらないよう、中身は種類の集合にして、枚数は counter（under:p）にする。
        skel[f"bundles:{p}"] = sorted([name(c), sorted({name(u) for u in s.cards[c].under})]
                                       for c in s.zones["shield"][p] if s.cards[c].under)
    counters: dict[str, int] = {}
    for z, zd in zones.items():
        if zd["shared"]:
            continue
        for p in (0, 1):
            if zd["counter"]:
                counters[f"{z}:{p}"] = len(s.zones[z][p])
            elif z == "hand" and hand_keys is not None:
                names = [name(c) for c in s.zones[z][p]]
                skel[f"{z}:{p}"] = sorted(n for n in names if n in hand_keys)
                counters[f"{z}:{p}"] = sum(1 for n in names if n not in hand_keys)
            else:
                skel[f"{z}:{p}"] = sorted(name(c) for c in s.zones[z][p])
    for p in (0, 1):
        counters[f"under:{p}"] = sum(len(s.cards[c].under) for c in s.zones["shield"][p])
        counters[f"mana_untapped:{p}"] = sum(1 for c in s.zones["mana"][p] if not s.cards[c].tapped)
    h = hashlib.blake2b(json.dumps(skel, sort_keys=True, ensure_ascii=False).encode(), digest_size=16).hexdigest()
    return h, counters


@dataclass
class LoopCertificate:
    start_skeleton: str
    actions: list[list[str]]          # 1周分の選択（意味キー）。answer_by_keys で再生できる
    deciders: list[int]
    delta: dict[str, int]
    limit: float                      # 繰り返せる回数の上限（inf もありうる）
    period: str
    win_by: str | None = None
    needed: int | None = None         # 勝利に必要な周回数
    verified: int = 0                 # 実際に再生して確認できた周回数
    notes: list[str] = field(default_factory=list)
    hand_keys: set[str] | None = None
    wild: bool = False                # actions に抽象キー（WILD_HAND）を含む。再生は replay_keys で解決する


# 「引いて捨てる」型のループ（引く札が毎周違う）用の抽象キー。手札の札を選ぶ決定のうち、
# 骨格に入らない札（hand_keys 外 = 検出開始時の手札に無い名前の札）を選んだものをこのキーに置き換える。
# 再生では hand_keys 外の札のうち、いちばん最近手札に入った札を選ぶ（入口時点の手札の札は選ばない）。
WILD_HAND = "hand:*"


def wild_keys(keys: list[str], hand_keys: set[str]) -> list[str]:
    out = []
    for k in keys:
        parts = k.split(":")
        out.append(WILD_HAND if len(parts) >= 3 and parts[0] == "hand" and parts[1] not in hand_keys else k)
    return out


def replay_keys(eng: Engine, keys: list[str], hand_keys: set[str] | None = None):
    """answer_by_keys と同じだが、WILD_HAND を hand_keys 外の手札の札（最近手札に入った順）で解決する。"""
    if WILD_HAND not in keys:
        return eng.answer_by_keys(keys)
    d = eng.s.waiting
    if d is None:
        raise IllegalAnswer("no decision pending")
    opts = d["options"]
    hk = hand_keys or set()
    order = {c: i for i, c in enumerate(eng.s.zones["hand"][d["player"]])}
    choice, used = [], set()
    for k in sorted(keys, key=lambda k: k == WILD_HAND):     # 具体的なキーを先に取る
        if k == WILD_HAND:
            cand = [i for i, o in enumerate(opts) if i not in used and o["key"].startswith("hand:")
                    and o["key"].split(":")[1] not in hk]
            cand.sort(key=lambda i: -order.get(opts[i].get("cid"), -1))
        else:
            cand = [i for i, o in enumerate(opts) if i not in used and o["key"] == k]
        if not cand:
            raise IllegalAnswer(f"key {k} not available in {[o['key'] for o in opts]}")
        choice.append(cand[0])
        used.add(cand[0])
    eng.answer(sorted(choice))


def analyze(delta: dict[str, int], counters: dict[str, int], me: int) -> tuple[float, str | None, int | None]:
    opp = 1 - me
    limit = float("inf")
    for k, d in delta.items():
        if d < 0 and (k.endswith(f":{me}")):
            # 自分の資源を消費する成分。山札は 0 枚で敗北なので残り1枚までしか使えない
            reserve = 1 if k.startswith("deck:") else 0
            limit = min(limit, (counters[k] - reserve) // -d)
    win_by, needed = None, None
    d_deck = delta.get(f"deck:{opp}", 0)
    if d_deck < 0:
        needed = -(-counters[f"deck:{opp}"] // -d_deck)   # 相手の山札が 0 枚になった瞬間に勝ち（104.2b）
        if needed <= limit:
            win_by = "opp_deck_out"
    d_sh = delta.get(f"shield:{opp}", 0)
    if win_by is None and d_sh < 0:
        n = -(-counters[f"shield:{opp}"] // -d_sh)
        if n <= limit:
            win_by, needed = "shield_zero", n   # この後ダイレクトアタックが通れば勝ち
    return limit, win_by, needed


def is_engine(delta: dict[str, int], me: int) -> bool:
    """相手には効かないが、自分の手札かアンタップのマナが周回ごとに増える（山札以外の自分の資源は減らない）ループ。
    ドローを含むループ（引いて、使って、戻す）がここに入る。ストックして次の手を探す土台にする。"""
    mine = {k: v for k, v in delta.items() if k.endswith(f":{me}") and not k.startswith("deck:")}
    return (any(v > 0 for k, v in mine.items() if k.startswith(("hand:", "mana_untapped:")))
            and all(v >= 0 for v in mine.values()))


def is_burn(delta: dict[str, int], me: int) -> bool:
    """相手に何も起きず、自分の山札だけが周回ごとに減る（自分の他の資源は減らない）ループ。
    絶望神サガのように「山札を1枚ずつ削る」だけでは勝てないが、山札が少ない時に勝つ効果
    （シャコガイルの置換勝利など）の前段になる。stock してから続きを探索する。"""
    return (delta.get(f"deck:{me}", 0) < 0 and not is_engine(delta, me)      # 手札やマナが増えるものは資源ループ
            and all(k.endswith(f":{me}") and (v >= 0 or k == f"deck:{me}") for k, v in delta.items()))


def draw_keys(eng: Engine, me: int) -> set[str]:
    """ドローを含むループの検出で骨格に入れる手札のカード名。いま手札にあるカードだけを区別し、
    ループ中に引いた別のカードは名前を見ず枚数だけ数える（引いたカードで骨格が毎回変わるのを避ける）。"""
    return {eng.s.cards[c].defn for c in eng.s.zones["hand"][me]}


class LoopDetector:
    """1人回し中に呼び出し、同じ骨格への回帰を見つける。"""

    def __init__(self, me: int = 0, period: str = "in_turn", hand_keys: set[str] | None = None,
                 engine_loops: bool = False, report_all: bool = False, burn_loops: bool = False,
                 wild: bool = False):
        self.me = me
        self.wild = wild and hand_keys is not None   # 手札の選択を抽象キーで記録する（hand_keys を渡す検出器だけ）
        self.report_all = report_all
        self.burn_loops = burn_loops
        self.period = period
        self.hand_keys = hand_keys
        self.engine_loops = engine_loops
        self.seen: dict[str, tuple[dict[str, int], int]] = {}

    def fork(self) -> "LoopDetector":
        d = LoopDetector(self.me, self.period, self.hand_keys, self.engine_loops, self.report_all, self.burn_loops, self.wild)
        d.seen = dict(self.seen)
        return d

    def observe(self, eng: Engine) -> LoopCertificate | None:
        h, ctr = abstract(eng, self.period, self.hand_keys)
        now = len(eng.log)
        if h in self.seen:
            old, at = self.seen[h]
            delta = {k: ctr[k] - old[k] for k in ctr if ctr[k] != old[k]}
            if delta and now > at:
                limit, win_by, needed = analyze(delta, ctr, self.me)
                if (any(v < 0 for k, v in delta.items() if k.endswith(f":{1 - self.me}")) or win_by
                        or (self.engine_loops and is_engine(delta, self.me)) or self.report_all
                        or (self.burn_loops and is_burn(delta, self.me))):
                    acts = eng.log[at:now]
                    keys = [a["keys"] for a in acts]
                    wild = False
                    if self.wild:
                        keys = [wild_keys(k, self.hand_keys) for k in keys]
                        wild = any(WILD_HAND in k for k in keys)
                    return LoopCertificate(h, keys, [a["p"] for a in acts], delta,
                                           limit, self.period, win_by, needed, hand_keys=self.hand_keys, wild=wild)
        self.seen[h] = (ctr, now)
        return None


import os as _os

# 再生の同一視（2026-11-13、設計書 §20）。同じ札を同じ結果になる形で使う手を同じ手とみなす:
# 払って出す手 ↔ 同じ札を無償で出す手、支払い（mana:…）は今の支払いの候補の先頭で代える、払わずに済んだ周の支払いは飛ばす。
# 同一視した周は必ず骨格と差分を確かめ直し、ずれたら捨てる。DMSIM_REPLAY_EQUIV=0 で切る
REPLAY_EQUIV = _os.environ.get("DMSIM_REPLAY_EQUIV", "1") != "0"


def _equiv_keys(d: dict, keys: list[str]) -> list[str] | None:
    opts = {o["key"] for o in d["options"]}
    out = []
    for k in keys:
        if k in opts:
            out.append(k)
        elif k.startswith("play:") and not k.endswith(":free") and k + ":free" in opts:
            out.append(k + ":free")
        elif k.startswith("mana:") and d["kind"] == "pay_mana" and d["options"]:
            out.append(d["options"][0]["key"])
        else:
            return None
    return out


def _delta_ok(delta: dict, cert: LoopCertificate, subst: bool) -> bool:
    """差分が証明書どおりか。同一視した周は、自分の未タップのマナが証明書より多く残るだけの違いを許す（払わずに済んだ分）。"""
    if delta == cert.delta:
        return True
    if not subst:
        return False
    keys = set(delta) | set(cert.delta)
    for k in keys:
        a, b = delta.get(k, 0), cert.delta.get(k, 0)
        if a == b:
            continue
        if k.startswith("mana_untapped:") and a > b:
            continue
        return False
    return True


def _replay_lap(e: Engine, cert: LoopCertificate) -> tuple[str | None, bool]:
    """1周を再生する。(None か "ended", 同一視したか) を返す。同じ選択ができなければ IllegalAnswer。"""
    subst = False
    i = 0
    while i < len(cert.actions):
        keys = cert.actions[i]
        d = e.advance()
        if d is None:
            return "ended", subst
        if REPLAY_EQUIV and keys and d["kind"] != "pay_mana" and all(k.startswith("mana:") for k in keys):
            subst = True                       # 無償に代えたので支払いの決定が来ない
            i += 1
            continue
        try:
            replay_keys(e, keys, cert.hand_keys)
        except IllegalAnswer:
            alt = _equiv_keys(d, keys) if REPLAY_EQUIV and WILD_HAND not in keys else None
            if alt is None:
                raise
            e.answer_by_keys(alt)
            subst = True
        i += 1
    return None, subst


def verify(eng: Engine, cert: LoopCertificate, times: int = 2) -> LoopCertificate:
    """証明書の行動列を実際に再生し、同じ骨格に戻って同じ差分が出ることを確かめる。"""
    e = eng.clone()
    for _ in range(times):
        h0, c0 = abstract(e, cert.period, cert.hand_keys)
        try:
            end, subst = _replay_lap(e, cert)
        except IllegalAnswer as ex:
            cert.notes.append(f"diverged: {ex}")     # 引いたカードが違うなど、同じ選択ができなかった
            return cert
        if end:
            cert.notes.append("game ended during replay")
            return cert
        e.advance()
        h1, c1 = abstract(e, cert.period, cert.hand_keys)
        delta = {k: c1[k] - c0[k] for k in c1 if c1[k] != c0[k]}
        if h1 != cert.start_skeleton or not _delta_ok(delta, cert, subst):
            cert.notes.append(f"diverged: delta={delta}")
            return cert
        cert.verified += 1
    return cert


def fast_forward(eng: Engine, cert: LoopCertificate, n: int):
    """競技ルール4.3 の「回数を宣言して省略」に相当。ここでは決定的に n 周を実際に再生する。
    抽象キーを含む証明書（wild）は、周ごとに骨格と差分が証明書どおりかを確かめ、ずれたら IllegalAnswer を出す
    （引いた札しだいで続かなくなる手順を、早送りの途中で見逃さないため）。"""
    for _ in range(n):
        h0, c0 = abstract(eng, cert.period, cert.hand_keys)
        end, subst = _replay_lap(eng, cert)
        if end:
            return
        if cert.wild or subst:
            eng.advance()
            h1, c1 = abstract(eng, cert.period, cert.hand_keys)
            if h1 != cert.start_skeleton or not _delta_ok({k: c1[k] - c0[k] for k in c1 if c1[k] != c0[k]}, cert, subst):
                raise IllegalAnswer("fast_forward diverged from certificate")
    eng.advance()
