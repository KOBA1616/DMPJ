"""物差しの本体（S4、docs/combo-ruler-design.md §6 タスク5）: 1局の結果から段1（ループ成立）と段2（勝利への変換）を判定する。

入力は play_game の (GameResult, Engine)。測定そのもの（局面を作って回す）はしない。judge は記録を読むだけで、既存の測定の挙動を変えない。

段1 ループ成立（§7-1: 有限回も数える。回数は相手の残り資源と無関係に記録）:
- 採った手順のループ（GameResult.loops。候補 loop_candidates は見ない）が1件以上あり、検証済み（verified）であること。
  certificate は探索中に verify で再生確認済み、pattern は実際に N 周指した記録。
- 無限か有限か: certificate は limit=="inf" なら無限、pattern は有限（laps 周）。N は certificate なら stocked、pattern なら laps。
  pattern の limit_est（減る資源が尽きるまでの見積もり）は確かめていないので別欄。
- 1周の差分（delta）と、ストック（1周以上回して蓄積したか）を返す。

段2 勝利への変換（§7-4: 勝った瞬間の勝ち方がループの蓄積由来かまで見る）:
- エンジンが自分の勝ちと判定したか（GameResult.kind が None でない。ロックは play_game が打ち切るので kind=="lock"）。
- 勝ち方の分類 via:
  loop   … 相手の山札切れ（loop_deck_out、または勝ちのターンに相手の山札を減らすループがある deck_out）、
             または勝利効果・状況起因（effect / state）で、勝ちのターンに勝ちより前に終わったループがある。
  lock   … ロック（山札切れ勝ちの経路として記録。lock_mode で受け身／能動を区別、相手マナが0になったかは別欄）。
  beat   … ダイレクトアタックでの勝ち（ループの後に殴って勝った局もここ。ループ勝ちに数えない）。
  other  … 上のどれでもない勝ち（ループなしの効果勝ちなど）。
- 自分が先に山札切れで負けた局（GameResult.lost=="deck_out"）は段2不成立。
- ループ勝ち（loop と lock）と殴り勝ち（beat）は別欄。キル率には両方を数える（kill=True）。勝ったターン win_turn は速さの材料。
- 勝ちの直前（最後のループの後）に攻撃した回数 attacks_after_loop を参考に返す（pattern のみ。certificate はログ位置が無いので None）。
  シャコガイル（攻撃時のドローで山札最後の札を引いて勝つ）のように、攻撃が勝利効果の引き金でも勝ち方は効果なので loop に数える。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

LOOP_WIN = ("loop", "lock")


@dataclass
class Stage1:
    ok: bool
    n_loops: int = 0
    verified: bool = False
    infinite: bool = False
    n: int = 0                        # 回した周回数（最大のループ）。certificate は stocked、pattern は laps
    limit_est: int | None = None      # pattern の見積もり上限（確かめていない）
    delta: dict = field(default_factory=dict)
    stocked: bool = False             # 1周以上回して蓄積したか
    sources: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class Stage2:
    ok: bool                          # ループ（またはロック）による勝ち
    engine_win: bool = False
    win_kind: str | None = None       # GameResult.kind
    win_turn: int | None = None       # 自分の何ターン目に勝ったか
    via: str | None = None            # loop / lock / beat / other
    loop_win: bool = False
    beat_win: bool = False
    kill: bool = False                # キル率に数える勝ち（loop・lock・beat・other すべて）
    self_deck_out: bool = False
    attacks_after_loop: int | None = None
    lock: dict | None = None          # {"mode": passive|active, "opp_mana": n, "opp_mana_zero": bool, ...}
    cross_turn: bool = False          # 前のターンまでのループの蓄積で、勝ち手段の効果により勝った（§24。同じターンの勝ちは False）
    loop_turn: int | None = None      # cross_turn のとき、蓄積したループの自分のターン（最後のもの）
    loop_beat: bool = False           # 段1が成立したうえでの殴り勝ち（ループで出した体による殴り勝ち、段2とは別の欄。§24）
    unverified_cross: bool = False    # ターンまたぎの勝ちだが蓄積への依存を確かめられない（段2にしない別欄）
    reason: str = ""


@dataclass
class Verdict:
    stage1: Stage1
    stage2: Stage2
    reason: str
    opp: str = "none"     # 測った時の相手の抵抗の段階（GameResult.opp の写し）

    def to_dict(self) -> dict:
        return asdict(self)


def _n(lp: dict) -> int:
    return int(lp.get("laps", lp.get("stocked", 0)) or 0)


def _infinite(lp: dict) -> bool:
    if lp.get("source") == "pattern":
        return False
    return str(lp.get("limit")) == "inf"


def consume_only(lp: dict, me: int = 0) -> bool:
    """有限のパターンループのうち、1周の差分が自分のマナの減り（untapped_mana / mana）だけで、何も増えず相手も減らないもの。
    マナを払って同じ札を使い直すだけの繰り返しで、払える分で止まる（例: 墓地から手札に戻る呪文を毎周マナを払って唱え直す）。ループに数えない。
    山札が減るだけのもの（掘り進める）はループのままにする。"""
    if lp.get("source") != "pattern" or _infinite(lp):
        return False
    d = lp.get("delta") or {}
    return bool(d) and all(v < 0 and str(k).endswith(f":{me}") and str(k).split(":")[0] in ("untapped_mana", "mana")
                           for k, v in d.items())


def stage1(res, me: int = 0) -> Stage1:
    consumed = [lp for lp in res.loops if lp.get("verified", True) and consume_only(lp, me)]
    loops = [lp for lp in res.loops if lp.get("verified", True) and not consume_only(lp, me)]
    if not res.loops:
        why = "採った手順にループが無い"
        if getattr(res, "loop_candidates", None):
            why += f"（探索の候補には {len(res.loop_candidates)} 件あったが選ばれていない）"
        return Stage1(ok=False, reason=why)
    if not loops:
        if consumed:
            return Stage1(ok=False, n_loops=len(res.loops), reason="自分の資源を払うだけの有限の繰り返ししかない（ループに数えない）")
        return Stage1(ok=False, n_loops=len(res.loops), reason="ループの記録はあるが検証されていない")
    best = max(loops, key=_n)
    inf = any(_infinite(lp) for lp in loops)
    n = _n(best)
    s = Stage1(ok=True, n_loops=len(loops), verified=True, infinite=inf, n=n,
               limit_est=best.get("limit_est"), delta=dict(best.get("delta") or {}), stocked=n >= 1,
               sources=sorted({lp.get("source", "certificate") for lp in loops}))
    s.reason = f"ループ成立（{'無限' if inf else f'有限 {n} 周'}、{'/'.join(s.sources)}）"
    return s


def _attacks(log, a: int, b: int) -> int:
    return sum(1 for x in log[a:b] if x.get("kind") == "attack" and any(k.startswith("attack:") and not k.endswith(":none") for k in x.get("keys", ())))


_ZONE_WORDS = ("graveyard", "deck", "bz", "hand", "mana", "shield")


def _zones_read(rules, cid: str) -> set[str]:
    """勝ち手段の札の効果データが触れるゾーン（能力・呪文・進化の指定を文字列で見る）。"""
    import json as _json
    d = rules.cards[cid]
    blob = _json.dumps([d.abilities, d.spell, d.evolve_zone if d.grave_evo or d.evolve_from else None,
                        getattr(d, "cost_reduce_per_evo", 0) and "graveyard"], ensure_ascii=False, default=str)
    out = {z for z in _ZONE_WORDS if f'"{z}"' in blob or f"'{z}'" in blob}
    if d.grave_evo:
        out.add("graveyard")
    if "最後の１枚" in (d.text or "") or "最後の1枚" in (d.text or ""):
        out.add("deck")
    return out


def _cross_turn(res, eng, me: int, win_ids) -> tuple[bool, bool, int | None]:
    """(段2に数える, 依存を確かめられない別欄, ループのターン)。条件（§24）: (a) 勝ったターンより前に自分のループがある、
    (b) 勝ち手段（part: win）の札が勝った時点で場にあるか、勝ったターンに使われた（勝ち手段の効果による勝ち）、
    (c) 前のループの差分が、勝ち手段の効果が読むゾーン（墓地・山札・場など）を自分の側で動かしている（蓄積への依存）。"""
    if not win_ids or eng is None or res.kind not in ("effect", "state", "deck_out", "loop_deck_out"):
        return False, False, None
    prev = [lp for lp in res.loops if lp.get("verified", True) and not consume_only(lp, me)
            and lp.get("own_turn") is not None and lp["own_turn"] < res.kill_turn]
    if not prev:
        return False, False, None
    s = eng.s
    on_bz = {s.cards[c].defn for c in s.zones["bz"][me]} | {eng.rules.cards[s.cards[c].defn].id for c in s.zones["bz"][me]}
    used = set()
    for x in eng.log:
        if x.get("p") == me and x.get("turn", res.kill_turn) == res.kill_turn:
            for k in x.get("keys", ()):
                used |= {w for w in win_ids if w in k}
    by = [w for w in win_ids if w in on_bz or w in used]
    lt = max(lp["own_turn"] for lp in prev)
    if not by:
        return False, False, None
    zones = set().union(*(_zones_read(eng.rules, w) for w in by))
    moved = set()
    for lp in prev:
        for k, v in (lp.get("delta") or {}).items():
            z, _, who = str(k).partition(":")
            if v and who == str(me) and z in zones:
                moved.add(z)
    if moved:
        return True, False, lt
    return False, True, lt


def stage2(res, eng, me: int = 0, lock_mode: str = "passive", win_ids=None) -> Stage2:
    s = Stage2(ok=False, self_deck_out=res.lost == "deck_out")
    if res.error:
        s.reason = f"対局が失敗した（{res.error}）"
        return s
    if res.kind is None:
        s.reason = "自分が負けた（%s）" % res.lost if res.lost else "上限のターンまでに勝てなかった"
        if s.self_deck_out:
            s.reason = "自分が先に山札切れで負けた"
        return s
    s.engine_win, s.win_kind, s.win_turn, s.kill = True, res.kind, res.kill_turn, True
    win_loops = [lp for lp in res.loops if lp.get("own_turn") == res.kill_turn]
    win_pos = len(eng.log) if eng is not None else None
    if win_pos is not None:
        ends = [lp["log_end"] for lp in win_loops if lp.get("log_end") is not None]
        if ends and all(lp.get("source") == "pattern" for lp in win_loops):
            s.attacks_after_loop = _attacks(eng.log, max(ends), win_pos)
    if res.kind == "lock":
        opp_mana = len(eng.s.zones["mana"][1 - me]) if eng is not None else None
        s.via, s.loop_win = "lock", True
        s.lock = dict(res.lock or {}, mode=lock_mode, opp_mana=opp_mana, opp_mana_zero=opp_mana == 0)
        s.reason = f"ロック成立（{'能動' if lock_mode == 'active' else '受け身'}、相手マナ {opp_mana}）。山札切れ勝ちの経路として数える"
    elif res.kind == "direct_attack":
        s.via, s.beat_win = "beat", True
        s.loop_beat = bool([lp for lp in res.loops if lp.get("verified", True) and not consume_only(lp, me)])
        s.reason = "ループの後に殴り勝ち（ループ勝ちに数えない。別欄 loop_beat）" if s.loop_beat else (
            "ループの後に殴り勝ち（ループ勝ちに数えない）" if res.loops else "殴り勝ち（ループなし）")
    elif res.kind == "loop_deck_out" or (res.kind == "deck_out" and any((lp.get("delta") or {}).get(f"deck:{1 - me}", 0) < 0 or lp.get("win_by") == "opp_deck_out" for lp in win_loops)):
        s.via, s.loop_win = "loop", True
        s.reason = "ループで相手の山札を削り切って勝ち"
    elif res.kind in ("effect", "state") and win_loops and all(lp.get("log_end") is None or win_pos is None or lp["log_end"] <= win_pos for lp in win_loops):
        s.via, s.loop_win = "loop", True
        s.reason = "ループで蓄積した後に勝利効果で勝ち"
        if s.attacks_after_loop:
            s.reason += f"（ループ後に攻撃 {s.attacks_after_loop} 回、攻撃は勝利効果の引き金）"
    else:
        ok, unv, lt = _cross_turn(res, eng, me, win_ids)
        if ok:
            s.via, s.loop_win, s.cross_turn, s.loop_turn = "loop", True, True, lt
            s.reason = f"{lt} ターン目のループの蓄積で、{res.kill_turn} ターン目に勝ち手段の効果で勝ち（ターンまたぎ）"
        else:
            s.via = "other"
            s.unverified_cross = unv
            s.reason = f"勝ちのターンにループが無い勝ち（{res.kind}）" + (
                "。前のターンのループはあるが、勝ち手段がそれに依存するかを確かめられない（別欄）" if unv else "")
    s.ok = s.loop_win and not s.self_deck_out
    return s


def judge(res, eng, *, me: int = 0, lock_mode: str = "passive", win_ids=None) -> Verdict:
    """1局の (GameResult, Engine) を段1・段2で判定する。lock_mode は play_game に渡したロック判定役が受け身（lock_probe）か能動（prefer_policy・探索）か。"""
    a = stage1(res, me)
    b = stage2(res, eng, me, lock_mode, win_ids)
    if b.via == "lock" and not a.ok:
        a.reason += "（ロックは段1に数えず段2の経路として記録）"
    return Verdict(a, b, f"段1: {a.reason} / 段2: {b.reason}", getattr(res, "opp", "none"))
