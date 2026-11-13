"""ターン構造（500〜512）、カードの実行（601）、マナ支払い（112.2a）。

ターンはステップの列（data/rules/turn.yaml）で、各ステップの処理は @step で登録する。
ターンが始まる時に state.step_mods（効果による「飛ばす」「もう一度行う」）を反映した列を作る。
"""
from __future__ import annotations

import itertools

from ..base.types import ActivateTask, CrossTask, HyperTask, PlayTask, TurnTask
from .registry import STEPS, read_only, step, task


class TurnMixin:
    def turn_task(self) -> dict:
        return {"t": "turn", "steps": self._build_steps(self.s.active), "i": 0, "sub": 0, "cp": True}

    def _build_steps(self, p: int) -> list[str]:
        """このターンのステップ列。使った step_mod は turns を 1 減らし、0 になったら消す。"""
        out = []
        for name in self.rules.steps:
            mods = [m for m in self.s.step_mods if m["player"] == p and m["step"] == name]
            if any(m["mode"] == "skip" for m in mods):
                pass
            else:
                out.append(name)
                out += [name for m in mods if m["mode"] == "extra"]
            for m in mods:
                m["turns"] -= 1
        self.s.step_mods = [m for m in self.s.step_mods if m["turns"] > 0]
        return out

    def _step_done(self, t):
        t["i"] += 1
        t["sub"] = 0

    def _expire(self, duration: str):
        """期限の切れた継続的効果を消す。修整が切れてパワー0以下になったら、その場で破壊する（703.4c）。
        状況起因処理のタスクを積むので、呼んだ側はこの後に自分のタスクを積まないこと。"""
        n = len(self.s.continuous)
        self.s.continuous = [c for c in self.s.continuous if c["duration"] != duration]
        self.s.delayed = [d for d in self.s.delayed if d["duration"] != duration]
        if len(self.s.continuous) != n:
            self._sba()

    def _distinct_hand_options(self, p, verb):
        """同じカード名の手札は区別しない（対称な選択肢の正規化）。"""
        seen, out = set(), []
        for cid in self.zlist("hand", p):
            dfn = self.s.cards[cid].defn
            if dfn not in seen:
                seen.add(dfn)
                out.append({"key": f"{verb}:{dfn}", "cid": cid, "name": self.cdef(cid).name})
        return out

    def _play_options(self, p) -> list[dict]:
        """メインステップで実行できるカード。ツインパクトは面ごとに別の選択肢（810.3）。"""
        out = []
        for o in self._distinct_hand_options(p, "play"):
            cid = o["cid"]
            d = self.cdef(cid)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                if not self._can_play_face(cid, p, fi):
                    continue
                key = o["key"] if fi is None else f"{o['key']}:{fi}"
                opt = {"key": key, "cid": cid, "name": f.name}
                if fi is not None:
                    opt["face"] = fi
                out.append(opt)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                # G・ゼロ: コストを支払わずに召喚／唱える。従来はクリーチャーだけだったが、
                # 呪文も free_if で登録されている（dm23rp1-t10 等15枚）のに選択肢が出ず、
                # 無料で唱えられなかったため、呪文も同じ条件で :free を出す（第167弾）。
                # 下の cast_free 許可の分岐が重複を弾くので、キーは同じ :free でよい。
                if f.free_if and self.eval_cond(f.free_if, {"you": p, "self": self.s.ref(cid), "vars": {}}) \
                        and ((f.is_creature() and self.permits(cid, "summon"))
                             or ("spell" in f.types and self.permits(cid, "cast"))):
                    opt = {"key": f"{o['key']}:free" if fi is None else f"{o['key']}:{fi}:free", "cid": cid,
                           "name": f.name, "free": True}   # G・ゼロ: コストを支払わずに召喚／唱える
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                if "spell" in f.types and self.permits(cid, "cast") and self.permits(cid, "cast_free"):
                    fk = f"{o['key']}:free" if fi is None else f"{o['key']}:{fi}:free"
                    if all(x["key"] != fk for x in out):   # 無償詠唱（アカシック3など）: コストを支払わずに唱える選択肢
                        opt = {"key": fk, "cid": cid, "name": f.name, "free": True}
                        if fi is not None:
                            opt["face"] = fi
                        out.append(opt)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                if f.neo and f.evolve_from and self._evo_sources(cid, p, fi):   # NEO進化: 重ねて出す選択肢
                    opt = {"key": f"{o['key']}:neo" if fi is None else f"{o['key']}:{fi}:neo", "cid": cid,
                           "name": f.name, "neo": True}
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                if f.grave_evo and f.evolve_from and self._evo_sources(cid, p, fi):   # 墓地進化: 自分の墓地のクリーチャーの上に重ねて出す選択肢
                    opt = {"key": f"{o['key']}:gevo" if fi is None else f"{o['key']}:{fi}:gevo", "cid": cid,
                           "name": f.name, "grave_evo": True}
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                ac = f.alt_cost   # 代替コスト: 別額を払う / 行動で払う（if があれば条件成立時のみ提示）
                if ac:
                    if "if" in ac and not self.eval_cond(ac["if"], {"you": p, "self": self.s.ref(cid), "vars": {}}):
                        continue
                    ok = bool(self._mana_choices(cid, p, fi, cost=ac["cost"], limit=1, civs=ac.get("civs"))) if "cost" in ac else \
                        all(sum(1 for c in self.zlist(st["zone"], p)
                                if c != cid and self.filter_match(c, st.get("filter", {}))
                                and (not st.get("tap") or not self.s.cards[c].tapped)) >= st["count"]
                            for st in ac["do"])
                    if ok:
                        opt = {"key": f"{o['key']}:alt" if fi is None else f"{o['key']}:{fi}:alt",
                               "cid": cid, "name": f.name, "alt": True}
                        if fi is not None:
                            opt["face"] = fi
                        out.append(opt)
                vd = f.vividraw   # ビビッドロー: 表向きにしたカードは代替コストで実行できる
                if vd and self.s.cards[cid].vivid and self._mana_choices(cid, p, fi, cost=vd["cost"], limit=1, civs=vd["civs"]):
                    opt = {"key": f"{o['key']}:vivid" if fi is None else f"{o['key']}:{fi}:vivid",
                           "cid": cid, "name": f.name, "vivid": True}
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
                gs = f.galaxy_shield   # ギャラクシールド: 代替コストで表向きにシールド化する選択肢
                if gs and self._mana_choices(cid, p, fi, cost=gs["cost"], limit=1, civs=gs["civs"]):
                    opt = {"key": f"{o['key']}:gshield" if fi is None else f"{o['key']}:{fi}:gshield", "cid": cid,
                           "name": f.name, "gshield": True}
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                mc = f.mugen_climb   # ムゲンクライム: 自分のクリーチャーをタップし代替コストを払って手札/墓地から実行
                if mc and self._climb_ready(cid, p, fi, mc):
                    opt = {"key": f"{o['key']}:climb" if fi is None else f"{o['key']}:{fi}:climb", "cid": cid,
                           "name": f.name, "climb": True}
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
        seen_mc = set()   # ムゲンクライム: 墓地からも実行できる
        for cid in self.zlist("graveyard", p):
            dn = self.s.cards[cid].defn
            if dn in seen_mc:
                continue
            d = self.cdef(cid)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                mc = f.mugen_climb
                if mc and self._climb_ready(cid, p, fi, mc):
                    seen_mc.add(dn)
                    opt = {"key": f"play:{dn}:climb" if fi is None else f"play:{dn}:{fi}:climb",
                           "cid": cid, "name": f.name, "climb": True}
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
        seen = set()   # アビスラッシュ等: 墓地から召喚できるカードも選択肢に出す
        for cid in self.zlist("graveyard", p):
            dn = self.s.cards[cid].defn
            if dn in seen:
                continue
            grant = self._grave_summon_grant(cid)
            if grant is None:
                continue
            seen.add(dn)
            d = self.cdef(cid)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                if self._can_play_face(cid, p, fi):
                    opt = {"key": f"play:{dn}:rush" if fi is None else f"play:{dn}:{fi}:rush",
                           "cid": cid, "name": f.name, "rush": True}
                    if grant.get("once_src") is not None:
                        opt["once_src"] = grant["once_src"]
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
        seen_f = set()   # フシギバース: 墓地から、自分のクリーチャー1体をマナに置いて差額で召喚
        for cid in self.zlist("graveyard", p):
            dn = self.s.cards[cid].defn
            if dn in seen_f:
                continue
            d = self.cdef(cid)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                fg = f.fushigi
                if not fg:
                    continue
                bases = [c for c in self.bz_tops(p) if not self.s.cards[c].tapped]
                if not bases:
                    continue
                cheapest = max(fg.get("min", 1), fg["cost"] - max(self.chars_ro(b)["cost"] for b in bases))
                if self._mana_choices(cid, p, fi, cost=cheapest, limit=1, civs=fg["civs"]):
                    seen_f.add(dn)
                    opt = {"key": f"play:{dn}:fushigi" if fi is None else f"play:{dn}:{fi}:fushigi",
                           "cid": cid, "name": f.name, "fushigi": True}
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
        seen_r = set()   # リサイクル（第172弾）: 墓地から代替コストで唱える。civs 省略時はカード自身の文明
        for cid in self.zlist("graveyard", p):
            dn = self.s.cards[cid].defn
            if dn in seen_r:
                continue
            d = self.cdef(cid)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                rc = f.recycle
                if not rc or "spell" not in f.types or not self.permits(cid, "cast"):
                    continue
                if self._mana_choices(cid, p, fi, cost=rc["cost"], limit=1, civs=rc.get("civs")):
                    seen_r.add(dn)
                    opt = {"key": f"play:{dn}:recycle" if fi is None else f"play:{dn}:{fi}:recycle",
                           "cid": cid, "name": f.name, "recycle": True}
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
        seen_m = set()   # マナゾーンから召喚できるカードも選択肢に出す（通常コスト）
        for cid in self.zlist("mana", p):
            dn = self.s.cards[cid].defn
            if dn in seen_m or not self.permits(cid, "summon_from_mana"):
                continue
            grant = self._mana_summon_grant(cid)
            if grant is None:   # 回数制限つき許可しかなく、使い切っている
                continue
            seen_m.add(dn)
            d = self.cdef(cid)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                if self._can_play_face(cid, p, fi):
                    opt = {"key": f"play:{dn}:msum" if fi is None else f"play:{dn}:{fi}:msum",
                           "cid": cid, "name": f.name, "rush": True}
                    if grant.get("once_src") is not None:
                        opt["once_src"] = grant["once_src"]
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
        seen_b = set()   # マナ爆誕（第191弾）: カード自身の能力で、自分のマナゾーンから固定コストで召喚できる
        for cid in self.zlist("mana", p):
            dn = self.s.cards[cid].defn
            if dn in seen_b or not self.permits(cid, "summon"):
                continue
            d = self.cdef(cid)
            for fi, f in ([(None, d)] if not d.faces else list(enumerate(d.faces))):
                mb = f.mana_bakutan
                if mb is None or "creature" not in f.types or "evolution" in f.types:
                    continue
                # コスト0はマナをタップしないので文明の要求も無い。それ以外はカード自身の文明を含む支払い
                if self._mana_choices(cid, p, fi, cost=mb, limit=1, civs=f.civs if mb > 0 else []):
                    seen_b.add(dn)
                    opt = {"key": f"play:{dn}:bakutan" if fi is None else f"play:{dn}:{fi}:bakutan",
                           "cid": cid, "name": f.name, "rush": True, "bakutan": True}
                    if fi is not None:
                        opt["face"] = fi
                    out.append(opt)
        return out

    def _grave_summon_grant(self, cid) -> dict | None:
        """墓地から召喚する許可の状態。無制限なら {}、回数制限つき（ターン1回・未使用）なら {"once_src": 発生源}、
        許可が無い／使い切っていれば None。"""
        limited = None
        for e in self.chars_ro(cid)["allow"]:
            if isinstance(e, str):
                if e == "summon_from_graveyard":
                    return {}
            elif e.get("action") == "summon_from_graveyard":
                if not e.get("once"):
                    return {}
                if not self.s.turn_counters.get(f"summon_once:{e.get('src')}"):
                    limited = e.get("src")
        return {"once_src": limited} if limited is not None else None

    def _mana_summon_grant(self, cid) -> dict | None:
        """マナゾーンから召喚する許可の状態（第50弾。第37弾の墓地版と同じ方式）。
        無制限なら {}、回数制限つき（ターン1回・未使用）なら {"once_src": 発生源}、
        許可が無い／使い切っていれば None。"""
        limited = None
        for e in self.chars_ro(cid)["allow"]:
            if isinstance(e, str):
                if e == "summon_from_mana":
                    return {}
            elif e.get("action") == "summon_from_mana":
                if not e.get("once"):
                    return {}
                if not self.s.turn_counters.get(f"summon_once:{e.get('src')}"):
                    limited = e.get("src")
        return {"once_src": limited} if limited is not None else None

    def _climb_ready(self, cid, p, fi, mc) -> bool:
        """ムゲンクライムの前提: 代替コストが払えて、タップできる自分のクリーチャーが足りる。"""
        f = self.cdef(cid).face(fi)
        action = "summon" if f.is_creature() else "generate" if f.is_permanent() or f.is_castle() else "cast"
        if not self.permits(cid, action):
            return False
        pool = [c for c in self.bz_tops(p) if not self.s.cards[c].tapped
                and "creature" in self.chars_ro(c)["types"]]
        return len(pool) >= mc["tap"] and bool(self._mana_choices(cid, p, fi, cost=mc["cost"], limit=1, civs=mc["civs"]))

    def _cross_options(self, p) -> list[dict]:
        """メインステップに、バトルゾーンのクロスギアのマナコストをもう一度支払って自分のクリーチャーにクロスする（303.3b, 504.2）。
        すでにクロスしているクリーチャー自身にはクロスしなおせない（303.4a）。"""
        out = []
        for g in self.bz_tops(p):
            if "cross_gear" not in self.chars_ro(g)["types"]:
                continue
            cur = self.s.cards[g].crossed
            payable = bool(self._mana_choices(g, p, limit=1))
            for c in self.bz_tops(p):
                if "creature" in self.chars_ro(c)["types"] and not (cur and cur == self.s.ref(c)):
                    if payable:
                        out.append({"key": f"cross:{self.s.cards[g].defn}:{self.s.cards[c].defn}", "cid": g, "target": self.s.ref(c)})
                    # コストを支払わずにクロスできる許可（第195弾）: ギア側・クリーチャー側
                    # どちらの allow でもよい（other は相手側カードに当てる）
                    if self.permits(g, "cross_free", c) or self.permits(c, "cross_free", g):
                        out.append({"key": f"cross:{self.s.cards[g].defn}:{self.s.cards[c].defn}:free", "cid": g, "target": self.s.ref(c), "free": True})
        return out

    def _reveal_options(self, p: int) -> list[dict]:
        """ビビッドロー: このターンにドローして、まだ攻撃していないなら表向きにできる。"""
        s = self.s
        if s.turn_counters.get("attacked"):
            return []
        out = []
        for c in self.zlist("hand", p):
            card = s.cards[c]
            if card.vivid or card.drawn_turn != s.turn:
                continue
            if self.cdef(c).vividraw or any(f.vividraw for f in self.cdef(c).faces):
                out.append({"key": f"reveal:{card.defn}", "cid": c, "reveal": True})
        return out

    def _hyper_options(self, p: int) -> list[dict]:
        """ハイパー化: ハイパーモードでない自分のクリーチャーで、タップできる他の自分のクリーチャーがいるもの。"""
        s = self.s
        out = []
        allies = [c for c in self.bz_tops(p) if not s.cards[c].tapped]
        for c in self.bz_tops(p):
            if self.is_hyper(c) or not self.fdef(c).hyper:
                continue
            if any(a != c for a in allies):
                out.append({"key": f"hyper:{s.cards[c].defn}", "cid": c, "hyper_act": True})
        return out

    def _can_play_face(self, cid, p, face) -> bool:
        d = self.cdef(cid).face(face)
        action = "summon" if d.is_creature() else "generate" if d.is_permanent() or d.is_castle() else "cast"
        if not self.permits(cid, action) or (d.is_creature() and not self.permits(cid, "enter_bz")):
            return False
        if "evolution" in d.types and not d.s_max:   # S-MAX進化は進化元を必要としない（通常召喚として扱う）
            if d.deck_evolution:   # デッキ進化（第173弾）: 山札が空でなければ、めくりの結果にかかわらず召喚を試みられる
                if not self.zlist("deck", p):
                    return False
                n = 1
                cost = max(1, d.cost - n * d.cost_reduce_per_evo) if d.cost_reduce_per_evo else None   # 「コストは0以下にはならない」= 最低1
                return bool(self._mana_choices(cid, p, face, cost=self._opt_reduced(cid, face, d, self._sac_reduced(d, self._tap_reduced(d, p, cost, None), self._sac_pool(d, p))), limit=1))
            if isinstance(d.evolve_from, list):   # 進化V: フィルタごとに進化元が要る
                if not self._evo_v_ready(cid, p, face):
                    return False
                srcs = self._evo_sources(cid, p, face)
            else:
                srcs = self._evo_sources(cid, p, face)
                if len(srcs) < d.evolve_count:
                    return False
            n = len(srcs) if d.evolve_any else d.evolve_count           # 最も安い組合せで払えるか（112.2b）
            cost = max(1, d.cost - n * d.cost_reduce_per_evo) if d.cost_reduce_per_evo else None   # 「コストは0以下にはならない」= 最低1
            return bool(self._mana_choices(cid, p, face, cost=self._opt_reduced(cid, face, d, self._sac_reduced(d, self._tap_reduced(d, p, cost, None), self._sac_pool(d, p))), limit=1))
        return bool(self._mana_choices(cid, p, face, cost=self._opt_reduced(cid, face, d, self._sac_reduced(d, self._tap_reduced(d, p, None, None), self._sac_pool(d, p))), limit=1))

    def _opt_reduced(self, cid, face, d, cost):
        """任意の軽減（opt_reduce / cost_may）をすべて使った場合の最安コスト（実行可能かの判定用）。"""
        base = d.cost if cost is None else cost
        o = self.chars_ro(cid, face)["opt_reduce"]
        if o:
            n = 1
            if o.get("do") and o.get("per"):   # 支払い時の行動1件につき軽減: 選べる最大数で見積もる
                env = {"you": self.s.cards[cid].controller, "self": self.s.ref(cid)}
                do = o["do"]
                if "selects" in do:   # 第189弾: 複数の選択肢の合計で見積もる
                    n = sum(min(e.get("max", 99), len([c for c in self.candidates(e["select"], env) if c != cid]))
                            for e in do["selects"])
                else:
                    n = min(do.get("max", 99), len([c for c in self.candidates(do["select"], env) if c != cid]))
            base = max(o.get("floor", 0), base - o["amount"] * n)
        cm = self._cost_may_avail(cid, face)
        if cm:
            base = max(max(e.get("min", 0) for e in cm), base - sum(e["amount"] for e in cm))
        return base if (o or cm) else cost

    def _opt_amount(self, o, fuel) -> int:
        """実際に得る軽減量: per なら支払い時の行動の件数 × amount。"""
        return o["amount"] * (len(fuel) if o.get("per") else 1)

    @read_only
    def _cost_may_avail(self, cid, face=None) -> list[dict]:
        """今使える任意のコスト軽減（mod cost_may）。once のものは発生源ごとにターン中1回まで。"""
        out = []
        for e in self.chars_ro(cid, face)["cost_may"]:
            if e.get("once") and self.s.turn_counters.get(f"cost_may:{e['src']}"):
                continue
            out.append(e)
        return out

    def _sac_pool(self, d, p) -> list[int]:
        """ササゲール: ディスペクターを召喚する時、破壊してコストを減らせる自分のクリーチャー。"""
        if not any("ディスペクター" in r for r in d.races):
            return []
        return [c for c in self.bz_tops(p) if self.chars_ro(c)["sac_reduce"] > 0]

    def _sac_reduced(self, d, cost, sacs):
        if not sacs:
            return cost
        return max(0, (d.cost if cost is None else cost) - sum(self.chars_ro(c)["sac_reduce"] for c in sacs))

    def _tap_pool(self, p) -> list[int]:
        return [c for c in self.bz_tops(p) if "creature" in self.chars_ro(c)["types"] and not self.s.cards[c].tapped]

    def _tap_reduced(self, d, p, cost, tapped):
        """ハイパーエナジー: タップしたクリーチャー1体につきコストを減らす（床は0）。tapped=None は最大限タップした場合。"""
        if not d.tap_reduce:
            return cost
        n = len({self.chars_ro(c)["cost"] for c in self._tap_pool(p)}) if tapped is None else len(tapped)
        return max(0, (d.cost if cost is None else cost) - n * d.tap_reduce)

    @read_only
    def _evo_sources(self, cid, p, face=None) -> list[int]:
        """適正な進化元（801.1a）。evolve_zone（既定は自分のバトルゾーン）のクリーチャーで
        evolve_from を満たすもの（超無限墓地進化は自分の墓地から選ぶ）。"""
        f = self.cdef(cid).face(face)
        if isinstance(f.evolve_from, list):   # 進化V: どのフィルタか1つでも満たせば候補（選択は h_play がフィルタごとに進める）
            pool = self._evo_pool(cid, p, face)
            return [c for c in pool if any(self.filter_match(c, {k: v for k, v in ef.items() if k != "zone"})
                                            for ef in f.evolve_from)]
        ef = {k: v for k, v in (f.evolve_from or {}).items() if k != "zone"} or {}
        pool = self._evo_pool(cid, p, face)
        return [c for c in pool if self.filter_match(c, ef)]

    def _evo_pool(self, cid, p, face=None) -> list[int]:
        f = self.cdef(cid).face(face)
        z = f.evolve_zone
        pool = self.bz_tops(p) if z == "bz" else self.zlist(z, p)
        return [c for c in pool if ("creature" in self.chars_ro(c)["types"] or self.permits(c, "evolve_base"))]

    def _evo_v_ready(self, cid, p, face=None) -> bool:
        """進化V: フィルタごとに別々の進化元が確保できるか（貪欲に照合）。"""
        f = self.cdef(cid).face(face)
        pool = self._evo_pool(cid, p, face)
        used = set()
        for ef in f.evolve_from:
            ef = {k: v for k, v in ef.items() if k != "zone"}
            hit = next((c for c in pool if c not in used and self.filter_match(c, ef)), None)
            if hit is None:
                return False
            used.add(hit)
        return True

    @read_only
    def _mana_choices(self, cid, p, face=None, cost: int | None = None, limit: int = 32, civs=None) -> list[list[int]]:
        """支払いに使うマナの組（112.2a）。文明は1文明につき別々の1枚で満たし、マナの数値の合計がコストに一致。
        cost: 実行時に確定したコスト（進化元数の軽減など）。指定なければカード定義のコスト。
        civs: 必要な文明の上書き（代替コスト用）。"""
        d = self.cdef(cid).face(face)
        eff = d.cost if cost is None else cost
        ch = self.chars(cid, face)
        eff = max(0, eff + ch["pay_cost"] - d.cost)           # 継続的効果によるコストの増減（mod cost）
        if eff == 0 and not (civs if civs is not None else d.civs):
            return [[]]
        cs = ch.get("crystal_soul", 0)   # 水晶ソウル（第154弾）: このカードの支払いでは裏向きマナの数字が cs になる（置換。文明は得ない）
        untapped = [c for c in self.zlist("mana", p) if c != cid and not self.s.cards[c].tapped]   # 実行するカード自身は支払いに使えない（第191弾: マナゾーンから出す時、自分をタップして払えてしまっていた）
        if len(untapped) < len(d.civs) or sum(cs if (cs and self.s.cards[c].face_down) else self.cdef(c).mana for c in untapped) < eff:
            return []
        groups: dict = {}
        for c in untapped:   # 裏向きマナは無色として別グループに分ける（水晶武装）。文明は特性（chars）で見る: 「マナゾーンにあるカードをすべての文明として扱う」等が効く（第123弾）
            civkey = () if self.s.cards[c].face_down else tuple(sorted(self.chars_ro(c)["civs"]))
            groups.setdefault((self.s.cards[c].defn, self.s.cards[c].face_down, civkey), []).append(c)
        names = sorted(groups)
        need = list(civs) if civs is not None else list(d.civs)
        mana = [cs if (cs and n[1]) else self.rules.cards[n[0]].mana for n in names]   # n[1] はグループの face_down: 裏向きグループだけ水晶ソウル値に差し替える
        out: list[list[int]] = []

        def civ_ok(cnt):
            civsets = [set(n[2]) for n, k in zip(names, cnt) for _ in range(k)]
            return any(all(need[j] in civsets[perm[j]] for j in range(len(need)))
                       for perm in itertools.permutations(range(len(civsets)), len(need)))

        def dfs(i, cnt, total, zeros):
            if len(out) >= limit:
                return
            if i == len(names):
                if total == eff and civ_ok(cnt):
                    out.append([c for n, k in zip(names, cnt) for c in groups[n][:k]])
                return
            cap = len(groups[names[i]])
            for k in range(min(cap, (eff - total) // mana[i] if mana[i] else len(need) - zeros), -1, -1):
                dfs(i + 1, cnt + [k], total + k * mana[i], zeros + (0 if mana[i] else k))

        def floor_dfs(i, cnt, left):
            """112.2b: コストが文明の数を下回ったら文明の支払いを優先する（マナの数値の合計は問わない）。"""
            if len(out) >= limit:
                return
            if i == len(names):
                if left == 0 and civ_ok(cnt):
                    out.append([c for n, k in zip(names, cnt) for c in groups[n][:k]])
                return
            for k in range(min(len(groups[names[i]]), left), -1, -1):
                floor_dfs(i + 1, cnt + [k], left - k)

        if eff < len(need):
            floor_dfs(0, [], len(need))
        else:
            dfs(0, [], 0, 0)
        return out

    def play_task(self, cid, p, free, face=None, st=False) -> dict:
        t = {"t": "play", "cid": cid, "player": p, "free": free, "phase": "start", "gen": self.s.cards[cid].gen}
        if face is not None:
            t["face"] = face
        if st:
            t["st"] = True
        return t


@task("turn", TurnTask)
def h_turn(eng, t):
    s = eng.s
    if s.skip_rest:          # 「ターンの残りをとばす」: 残りのステップを行わずに次のターンへ（ターン終了時の誘発もなし）
        s.skip_rest = False
        t["i"] = len(t["steps"])
        eng._expire("end_of_turn")
        return None          # 状況起因処理と待機中の効果を、このターンのうちに済ませる
    if t["i"] < len(t["steps"]):
        name = t["steps"][t["i"]]
        s.step = name
        return STEPS[name](eng, t)
    # 512 次のターンへ
    for c in list(s.hold):                              # 512.1 保留状態のカードは墓地へ（誘発なし）
        eng._raw_move(c, "graveyard")
    s.active = s.extra_turns.pop(0) if s.extra_turns else 1 - s.active   # 500.5
    s.turn += 1
    if s.turn > eng.turn_limit:
        s.result = {"winner": None, "reason": "turn_limit", "turn": s.turn}
    t.update(steps=eng._build_steps(s.active), i=0, sub=0)
    return None


@step("start")
def st_start(eng, t):                                   # 501
    s = eng.s
    for c in eng.zlist("bz", s.active):                 # ハイパーモードは次の自分のターンのはじめまで（文字通り。bz は共有ゾーンなので、そのターンのプレイヤーがコントロールするカードだけを戻す。相手ターンに解放されても自分のターンのはじめに戻る）
        if s.cards[c].controller == s.active:
            s.cards[c].hyper = False
    a = s.active
    s.steps_this_turn = 0
    s.prev_counters = dict(s.turn_counters)   # 前のターンの履歴を退避する（{prev_shield_added} の読み先。バンドB U18）
    s.turn_counters = {}
    n = len(s.continuous)
    s.continuous = [c for c in s.continuous if c["duration"] != f"until_turn_start:{a}"]
    s.delayed = [d for d in s.delayed if d["duration"] != f"until_turn_start:{a}"]
    cands = [c for c in eng.bz_tops(a) if s.cards[c].tapped and eng.permits(c, "untap_at_start") and eng.abilities(c, "silent")]
    skill = []
    if cands:                          # 501.1a サイレントスキル: アンタップしないことを選び、かわりに能力を使ってもよい
        ans, d = eng.ask(t, a, "choose_cards", [eng._card_option(c) for c in cands], 0, len(cands))
        if d:
            return d
        skill = [cands[i] for i in ans]
    frozen = [c for c in eng.bz_tops(a) + eng.zlist("mana", a) if s.cards[c].no_untap_next]
    for c in frozen:                       # フリーズ等: 印を消費してこの回のアンタップをしない
        s.cards[c].no_untap_next = False
    untap = [{"ev": "untap", "subject": s.ref(c)}
             for c in eng.bz_tops(a) + eng.zlist("mana", a)
             if s.cards[c].tapped and eng.permits(c, "untap_at_start") and c not in skill and c not in frozen]
    eng._step_done(t)
    # ターン起因処理（同時にアンタップ, 702.3a）→ サイレントスキルの解決（他のカードのアンタップの後, 501.1a）→「ターンのはじめに」の誘発（501.2）
    effects = [eng._child(ab["effect"], {"you": a, "self": s.ref(c), "vars": {}}) for c in skill for _, ab in eng.abilities(c, "silent")]
    eng._push(*([eng.ev_task(untap)] if untap else []), *effects, eng.ev_task({"ev": "turn_start", "player": a}))
    if len(s.continuous) != n:
        eng._sba()           # 期限切れでパワー0以下になったものを先に破壊（703.1）


@step("draw")
def st_draw(eng, t):                                    # 502
    s = eng.s
    eng._step_done(t)
    if not (s.turn == 1 and s.active == s.first_player):   # 500.6
        eng._push(eng.ev_task({"ev": "draw", "player": s.active}))


@step("charge")
def st_charge(eng, t):                                  # 503
    s = eng.s
    a = s.active
    opts = eng._distinct_hand_options(a, "charge") + [{"key": "pass"}]
    ans, d = eng.ask(t, a, "charge", opts)
    if d:
        return d
    eng._step_done(t)
    o = opts[ans[0]]
    if o["key"] != "pass":
        eng._push(eng.ev_task({"ev": "move", "subject": s.ref(o["cid"]), "to": "mana", "reason": "charge"}))


@step("main")
def st_main(eng, t):                                    # 504
    a = eng.s.active
    with eng.chars_scope():   # 選択肢の列挙は読み取りだけなので、同じ状態での chars() の重複計算を省く
        opts = eng._play_options(a) + eng._cross_options(a) + eng._hyper_options(a) + eng._reveal_options(a) + [{"key": "pass"}]
    ans, d = eng.ask(t, a, "main", opts)
    if d:
        return d
    o = opts[ans[0]]
    if o["key"] == "pass":
        eng._step_done(t)
    elif o.get("reveal"):   # ビビッドロー: 表向きにする（ステップは終わらない）
        eng.s.cards[o["cid"]].vivid = True
    elif o.get("hyper_act"):
        eng._push({"t": "hyper", "cid": o["cid"], "player": a})
    elif o["key"].startswith("cross:"):
        eng._push({"t": "cross", "gear": eng.s.ref(o["cid"]), "target": o["target"], "player": a,
                   **({"free": True} if o.get("free") else {})})
    else:
        task = eng.play_task(o["cid"], a, o.get("free", False), o.get("face"))
        if o.get("rush"):
            task["rush"] = True
        if o.get("once_src") is not None:
            task["once_src"] = o["once_src"]
        if o.get("gshield"):
            fd = eng.cdef(o["cid"]).face(o.get("face"))
            task["to_shield"] = True
            task["cost_override"] = fd.galaxy_shield["cost"]
            task["cost_civs"] = fd.galaxy_shield["civs"]
        if o.get("climb"):
            fd = eng.cdef(o["cid"]).face(o.get("face"))
            task["climb"] = True
            task["cost_override"] = fd.mugen_climb["cost"]
            task["cost_civs"] = fd.mugen_climb["civs"]
        if o.get("alt"):
            fd = eng.cdef(o["cid"]).face(o.get("face"))
            task["alt"] = True
            if fd.alt_cost and "cost" in fd.alt_cost:
                task["cost_override"] = fd.alt_cost["cost"]
                task["cost_civs"] = fd.alt_cost.get("civs", fd.civs)
        if o.get("recycle"):   # リサイクル（第172弾）: 墓地から代替コストで唱える（alt_cost と同じ支払い規約）
            fd = eng.cdef(o["cid"]).face(o.get("face"))
            task["recycle"] = True
            task["cost_override"] = fd.recycle["cost"]
            task["cost_civs"] = fd.recycle.get("civs", fd.civs)
        if o.get("bakutan"):   # マナ爆誕（第191弾）: マナゾーンから固定コストで召喚する（支払い規約は recycle と同じ）
            fd = eng.cdef(o["cid"]).face(o.get("face"))
            task["bakutan"] = True
            task["cost_override"] = fd.mana_bakutan
            task["cost_civs"] = fd.civs if fd.mana_bakutan > 0 else []
        if o.get("vivid"):
            fd = eng.cdef(o["cid"]).face(o.get("face"))
            task["vivid"] = True   # 第54弾: 唱えた/召喚した経路をイベントと解決 env へ伝える
            task["cost_override"] = fd.vividraw["cost"]
            task["cost_civs"] = fd.vividraw["civs"]
        if o.get("fushigi"):
            task["fushigi"] = True
        if o.get("neo") or o.get("grave_evo"):
            task["evo_mode"] = True
        eng._push(task)


@task("hyper", HyperTask)
def h_hyper(eng, t):
    """ハイパーモードの解放: 自分の他のクリーチャーを1体タップし、このクリーチャーをハイパーモードにする。"""
    s = eng.s
    cid, p = t["cid"], t["player"]
    c = s.cards[cid]
    if c.zone != "bz" or eng.is_hyper(cid):
        eng._pop(t)
        return None
    cands = [x for x in eng.bz_tops(p) if x != cid and not s.cards[x].tapped]
    if not cands:
        eng._pop(t)
        return None
    ans, d = eng.ask(t, p, "choose_cards", [eng._card_option(x) for x in cands], 1, 1)
    if d:
        return d
    target = cands[ans[0]]
    c.hyper = True
    eng._pop(t)
    eng._push(eng.ev_task([{"ev": "tap", "subject": s.ref(target)}]))
    return None


@task("activate", ActivateTask)
def h_activate(eng, t):
    """起動型能力の複合コスト（DM24系）: 自分のマナゾーンのタップされていないカードを tap_mana 枚タップし、効果を解決する。
    クリーチャー自身のタップは st_attack 側で支払い済み。"""
    s = eng.s
    cid, p = t["cid"], t["player"]
    if s.cards[cid].zone != "bz":
        eng._pop(t)
        return None
    ab = dict(eng.abilities(cid, "activate"))[t["ab"]]
    n = ab["cost"].get("tap_mana", 0)
    untapped = [m for m in eng.zlist("mana", p) if not s.cards[m].tapped]
    if len(untapped) < n:
        eng._pop(t)
        return None
    ans, d = eng.ask(t, p, "choose_cards", [eng._card_option(m) for m in untapped], n, n)
    if d:
        return d
    for i in ans:
        s.cards[untapped[i]].tapped = True
    eng._pop(t)
    eng._push(eng._child(ab["effect"], {"you": p, "self": s.ref(cid), "vars": {}}))
    return None


@step("attack")
def st_attack(eng, t):                                  # 505
    s = eng.s
    a = s.active
    atk = eng._attack_options(a)
    forced = {o["cid"] for o in atk if "attack" in eng.chars_ro(o["cid"])["require"]}   # 506.1b 攻撃を強制されたクリーチャーは攻撃させなくてはいけない
    act = [o for o in eng._activate_options(a, atk) if o.get("tap") not in forced]       # タップ能力で攻撃を免れることはできない（タップしない under 形は免れないので可）
    opts = atk + act + ([] if forced else [{"key": "pass"}])
    ans, d = eng.ask(t, a, "attack", opts)
    if d:
        return d
    o = opts[ans[0]]
    if o["key"] == "pass":
        eng._step_done(t)
    elif o["key"].startswith("activate:"):                  # 602 起動型能力: コストを払い、効果は待機状態になる
        if o.get("tap") is not None:
            s.cards[o["tap"]].tapped = True
        if o.get("tap_mana"):   # 複合コスト（マナもタップする）は activate タスクで残りを払ってから効果へ
            eng._push({"t": "activate", "cid": o["cid"], "player": a, "ab": o["ab"]})
        else:
            ab = dict(eng.abilities(o["cid"], "activate"))[o["ab"]]
            ops = list(ab["effect"])
            if o.get("under_cost"):   # コスト: 下のカードを墓地に置く（効果より先に処理する。第53弾）
                ops = [{"op": "move", "select": {"under_of": "self", "count": o["under_cost"]},
                        "to": "graveyard", "reason": "put"}] + ops
            eng._push(eng._child(ops, {"you": a, "self": s.ref(o["cid"]), "vars": {}}))
    else:
        s.turn_counters["attacked"] = True   # ビビッドロー: 「攻撃の前に」の判定
        eng._push({"t": "attack", "attacker": s.ref(o["cid"]), "target": o["target"], "phase": 0, "cp": True})


@step("end")
def st_end(eng, t):                                     # 511
    if t["sub"] == 0:
        t["sub"] = 1
        eng._push(eng.ev_task({"ev": "turn_end", "player": eng.s.active}))
        return None
    eng._expire("end_of_turn")                          # 511.2
    eng._step_done(t)


@task("cross", CrossTask)
def h_cross(eng, t):
    """クロスする（303.3, 701.17）。マナコストをもう一度支払い、クロスギアをクリーチャーに付ける。"""
    s = eng.s
    g, tg, p = t["gear"], t["target"], t["player"]
    if not (s.alive(g) and s.alive(tg)) or s.cards[g[0]].zone != "bz" or s.cards[tg[0]].zone != "bz":
        eng._pop(t)
        return None
    if t.get("free"):   # cross_free 許可によるクロス（第195弾）: 支払いは無い
        s.cards[g[0]].crossed = list(tg)
        eng._pop(t)
        return None
    choices = eng._mana_choices(g[0], p)
    if not choices:
        eng._pop(t)
        return None
    opts = [{"key": "mana:" + ",".join(sorted(s.cards[c].defn for c in ch)), "cids": ch} for ch in choices]
    ans, dd = eng.ask(t, p, "pay_mana", opts)
    if dd:
        return dd
    for c in opts[ans[0]]["cids"]:
        s.cards[c].tapped = True
    s.cards[g[0]].crossed = list(tg)
    eng._pop(t)
    return None


@task("play", PlayTask)
def h_play(eng, t):
    """カードの実行（601）。free=True はコストを支払わずに実行（S・トリガー等）。それでも召喚・詠唱したことになる（112.3g）。
    ツインパクトは face で実行する面を選ぶ（810.3）。進化は進化元を選んでその上に重ねる（801）。"""
    s = eng.s
    cid, p = t["cid"], t["player"]
    face = t.get("face")
    if s.cards[cid].gen != t["gen"] or s.cards[cid].zone in ("bz", "hold"):
        eng._pop(t)
        return None
    d = eng.cdef(cid).face(face)
    action = "summon" if d.is_creature() else "generate" if d.is_permanent() or d.is_castle() else "cast"
    with eng.chars_scope():   # 読み取りだけの判定
        denied = not eng.permits(cid, action) or (d.is_creature() and not eng.permits(cid, "enter_bz"))
    if denied:
        eng._pop(t)
        return None
    # スーパー・S・トリガー: シールドが1つもない時に使ったら追加能力を得る（印は移動後に付ける）
    sst_bonus = bool(t.get("st") and "super_s_trigger" in eng.chars_ro(cid, face)["keywords"]
                     and not eng.zlist("shield", p))
    # S・トリガー・プラス: 相手のターンで、そのターンに自分のシールドが2つ以上ブレイクされていれば追加能力を得る
    stp_bonus = bool(t.get("st") and "s_trigger_plus" in eng.chars_ro(cid, face)["keywords"]
                     and s.active != p and s.turn_counters.get(f"broken:{p}", 0) >= 2)
    if t.get("fushigi") and not t.get("fushigi_done"):   # フシギバース: 自分のクリーチャー1体をタップしてマナに置き、差額を払う
        fg = d.fushigi
        cands = [c for c in eng.bz_tops(p) if not s.cards[c].tapped]
        if not cands:
            eng._pop(t)
            return None
        ans, dd = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in cands], 1, 1)
        if dd:
            return dd
        base = cands[ans[0]]
        override = max(fg.get("min", 1), fg["cost"] - eng.chars_ro(base)["cost"])
        if not eng._mana_choices(cid, p, face, cost=override, limit=1, civs=fg["civs"]):
            eng._pop(t)   # 差額が払えない組み合わせでは始められない
            return None
        t["cost_override"] = override
        t["cost_civs"] = fg["civs"]
        t["fushigi_done"] = True
        eng._push(eng.ev_task([{"ev": "move", "subject": s.ref(base), "to": "mana", "reason": "charge",
                                "tapped": True}]))
        return None
    ac = d.alt_cost
    if t.get("alt") and ac and "do" in ac and not t.get("alt_done"):   # 代替コスト（行動形式）: 段階ごとに選んで支払う
        step_i = t.get("alt_step", 0)
        if step_i < len(ac["do"]):
            st = ac["do"][step_i]
            cands = [c for c in eng.zlist(st["zone"], p) if c != cid and eng.filter_match(c, st.get("filter", {}))]
            if len(cands) < st["count"]:
                eng._pop(t)
                return None
            ans, dd = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in cands], st["count"], st["count"])
            if dd:
                return dd
            if st.get("tap"):
                # タップで支払う（第57弾）
                evs = [{"ev": "tap", "subject": s.ref(cands[i])} for i in ans]
            else:
                evs = [{"ev": "move", "subject": s.ref(cands[i]), "to": st["to"], "reason": st.get("reason", "pay")}
                       for i in ans]
            t["alt_step"] = step_i + 1
            if evs:
                eng._push(eng.ev_task(evs))
            return None
        t["alt_done"] = True
        t["free"] = True        # コストは行動で払い切った
        t["as_paid"] = True
    if ("evolution" in d.types or t.get("evo_mode")) and "evo" not in t and not eng.cdef(cid).face(face).s_max:
        face_def = eng.cdef(cid).face(face)
        if face_def.deck_evolution:   # デッキ進化（第173弾）: 山札の上からめくって重ねる。支払いの前に行う
            de = face_def.deck_evolution
            if de.get("shuffle_first"):
                eng._shuffle(p)
            revealed = list(eng.zlist("deck", p)[: de.get("count", 1)])
            if de.get("blind"):   # OMGデッキ進化: 裏向きのまま、種類を問わず一番上に重ねる
                if not revealed:
                    eng._pop(t)
                    return None
                t["evo"] = [s.ref(revealed[0])]
            else:
                for c in revealed:
                    eng.note_public("reveal", c)
                efs = face_def.evolve_from if isinstance(face_def.evolve_from, list) else [face_def.evolve_from or {}]
                cands = [c for c in revealed
                         if any(eng.filter_match(c, {k: v for k, v in ef.items() if k != "zone"}) for ef in efs)]
                if not cands:   # クリーチャーがなければ手札に戻る（この時点では未払い。カードは手札に残る）
                    eng._pop(t)   # 先に pop してから残りの移動を積む（_push 後に _pop すると assert が壊れる）
                    if revealed and de.get("rest_to"):
                        eng._push(eng.ev_task([{"ev": "move", "subject": s.ref(c), "to": de["rest_to"],
                                                "reason": "put"} for c in revealed]))
                    return None
                if len(cands) == 1:   # 1候補だけなら選択は出ない
                    t["evo"] = [s.ref(cands[0])]
                else:
                    ans, dd = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in cands], 1, 1)
                    if dd:
                        return dd
                    t["evo"] = [s.ref(cands[ans[0]])]
                rest = [c for c in revealed if c != t["evo"][0][0]]
                if rest and de.get("rest_to"):   # Mデッキ進化: 選ばなかった分は墓地へ（支払いの前に済ませる）
                    eng._push(eng.ev_task([{"ev": "move", "subject": s.ref(c), "to": de["rest_to"],
                                            "reason": "put"} for c in rest]))
                    return None
        elif isinstance(face_def.evolve_from, list):   # 進化V: フィルタごとに1体ずつ選ぶ
            chosen = t.setdefault("evo_v", [])
            if len(chosen) < len(face_def.evolve_from):
                ef = {k: v for k, v in face_def.evolve_from[len(chosen)].items() if k != "zone"}
                used = {r[0] for r in chosen}
                cands = [c for c in eng._evo_pool(cid, p, face) if c not in used and eng.filter_match(c, ef)]
                if not cands:
                    eng._pop(t)
                    return None
                ans, dd = eng.ask(t, p, "choose_evo_source", [eng._card_option(c) for c in cands], 1, 1)
                if dd:
                    return dd
                chosen.append(s.ref(cands[ans[0]]))
                if len(chosen) == len(face_def.evolve_from):
                    t["evo"] = list(chosen)
                return None
        else:   # 通常の進化: バトルゾーン（evolve_zone）の進化元を選ぶ
            srcs = eng._evo_sources(cid, p, face)
            if len(srcs) < d.evolve_count:
                eng._pop(t)
                return None
            opts = [eng._card_option(c) for c in srcs]
            mn, mx = (1, len(srcs)) if d.evolve_any else (d.evolve_count, d.evolve_count)
            ans, dd = eng.ask(t, p, "choose_evo_source", opts, mn, mx)
            if dd:
                return dd
            t["evo"] = [s.ref(srcs[i]) for i in ans]
    if d.tap_reduce and not t["free"] and not t.get("tap_done"):     # ハイパーエナジー: コストが異なるクリーチャーを好きな数タップ
        chosen = t.setdefault("tap", [])
        used = {eng.chars_ro(c)["cost"] for c in chosen}
        cands = [c for c in eng._tap_pool(p) if c not in chosen and eng.chars_ro(c)["cost"] not in used]
        if cands:
            ans, dd = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in cands], 0, 1)
            if dd:
                return dd
            if ans:
                chosen.append(cands[ans[0]])
                return None
        t["tap_done"] = True
    if not t["free"] and not t.get("sac_done"):                      # ササゲール: 破壊するクリーチャーを任意に選ぶ
        chosen = t.setdefault("sac", [])
        cands = [c for c in eng._sac_pool(d, p) if c not in chosen]
        if cands:
            ans, dd = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in cands], 0, 1)
            if dd:
                return dd
            if ans:
                chosen.append(cands[ans[0]])
                return None
        t["sac_done"] = True
    if t.get("climb") and not t.get("climb_done"):   # ムゲンクライム: 自分のクリーチャーを指定数タップする
        mc = d.mugen_climb
        pool = [c for c in eng.bz_tops(p) if not s.cards[c].tapped and "creature" in eng.chars_ro(c)["types"]]
        if len(pool) < mc["tap"]:
            eng._pop(t)
            return None
        ans, dd = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in pool], mc["tap"], mc["tap"])
        if dd:
            return dd
        for i in ans:
            s.cards[pool[i]].tapped = True
        t["climb_done"] = True
    ch0 = eng.chars(cid, face)
    flag = f"last_play_creature:{p}"
    cyc = "cyclone" in ch0["keywords"] and bool(s.turn_counters.get(flag))   # サイクロン: 唱える直前に召喚していたか（直前の実行が召喚）
    s.turn_counters[flag] = int(d.is_creature())
    if ch0["opt_reduce"] and not t["free"] and not t.get("reduce_done"):    # B・A・D / J・O・E: 減らして実行するか選ぶ
        ans, dd = eng.ask(t, p, "choose_cards", [{"key": "reduce"}, {"key": "normal"}], 1, 1)
        if dd:
            return dd
        t["reduced"] = ans[0] == 0
        t["reduce_done"] = True
    if t.get("reduced") and ch0["opt_reduce"].get("do") and not t.get("fuel_done"):
        # 支払い時の行動（手札を見せる・捨てる、シールドを手札に加える、墓地の呪文を山札に戻す等）を先に行う
        # 第189弾: selects なら複数の選択肢（手札・クリーチャー・タマシード・シールドを最大1つずつ等）を
        # 順に選ぶ。ask は再入ごとに先頭の1回だけ保存された回答を消費するため、項目ごとの進捗を
        # t["fuel_idx"] / t["fuel"] / t["fuel_asked"] に刻んで再入時にそこから再開する。
        spec = ch0["opt_reduce"]["do"]
        env = {"you": p, "self": s.ref(cid)}
        entries = spec["selects"] if "selects" in spec else [spec]
        idx = t.get("fuel_idx", 0)
        fuel = list(t.get("fuel", []))
        asked = t.get("fuel_asked", False)
        failed = False
        while idx < len(entries):
            entry = entries[idx]
            cands = [c for c in eng.candidates(entry["select"], env) if c != cid and c not in fuel]   # 実行中のカード自身は対象にしない
            mx = min(entry.get("max", len(cands)), len(cands))
            if mx <= 0:
                if entry.get("min", 0) > 0:
                    failed = True          # 必須の燃料が選べないなら軽減も得られない
                idx += 1
                continue
            ans, dd = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in cands],
                              min(entry.get("min", 0), mx), mx)
            if dd:
                t["fuel_idx"] = idx
                t["fuel"] = fuel
                t["fuel_asked"] = True
                return dd
            asked = True
            fuel.extend(cands[i] for i in ans)
            idx += 1
        t["fuel_idx"] = idx
        t["fuel"] = fuel
        t["fuel_asked"] = asked
        if failed or (len(entries) == 1 and not asked):
            t["reduced"] = False          # 行動できないなら軽減も得られない
            t["fuel_done"] = True
        else:
            t["fuel_done"] = True
            if spec.get("tap"):   # 燃料としてタップする（コストの支払い。ゾーンは動かない）
                for c in t["fuel"]:
                    s.cards[c].tapped = True
            if spec.get("move_to") and (fuel or asked):
                reason = {"graveyard": "discard", "hand": "return", "deck": "put"}.get(spec["move_to"], "put")
                moves = [{"ev": "move", "subject": s.ref(c), "to": spec["move_to"], "reason": reason}
                         for c in t["fuel"]]
                if spec.get("strigger_off") and spec["move_to"] == "hand":   # 第189弾: 手札に加わる燃料の S・トリガーは使えない
                    for m in moves:
                        m["strigger"] = "off"
                seq = [eng.ev_task(moves)]
                if spec.get("shuffle"):
                    seq.append(eng._child([{"op": "shuffle"}], {"you": p, "self": s.ref(cid), "vars": {}}))
                eng._push(*seq)
                return None               # 行動の適用を終えてから支払いに進む
    if not t["free"] and not t.get("cost_may_done"):    # 任意のコスト軽減（cost_may）: 発生源ごとに使うか選ぶ
        avail = eng._cost_may_avail(cid, face)
        i = t.get("cost_may_i", 0)
        while i < len(avail):
            e = avail[i]
            if e.get("must"):   # 強制の軽減（「〜のコストを少なくする」）: 確認せずに適用する
                t["cost_may_total"] = t.get("cost_may_total", 0) + e["amount"]
                t["cost_may_min"] = max(t.get("cost_may_min", 0), e.get("min", 0))
                if e.get("once"):
                    s.turn_counters[f"cost_may:{e['src']}"] = 1
                i += 1
                continue
            ans, dd = eng.ask(t, p, "choose_cards", [{"key": "reduce"}, {"key": "normal"}], 1, 1)
            if dd:
                t["cost_may_i"] = i
                return dd
            if ans[0] == 0:
                t["cost_may_total"] = t.get("cost_may_total", 0) + e["amount"]
                t["cost_may_min"] = max(t.get("cost_may_min", 0), e.get("min", 0))
                if e.get("once"):
                    s.turn_counters[f"cost_may:{e['src']}"] = 1
            i += 1
        t["cost_may_done"] = True
    if not t["free"] and not t.get("paid_done"):
        n = len(t.get("evo", []))
        cost = max(1, d.cost - n * d.cost_reduce_per_evo) if d.cost_reduce_per_evo else None   # 「コストは0以下にはならない」= 最低1
        cost = eng._sac_reduced(d, eng._tap_reduced(d, p, cost, t.get("tap", [])), t.get("sac", []))
        if t.get("reduced"):
            o = ch0["opt_reduce"]
            cost = max(o.get("floor", 0), (d.cost if cost is None else cost) - eng._opt_amount(o, t.get("fuel", [])))
        if t.get("cost_may_total"):
            cost = max(t.get("cost_may_min", 0), (d.cost if cost is None else cost) - t["cost_may_total"])
        if t.get("cost_override") is not None:   # 代替コスト（キリフダッシュ等）は他の軽減より優先して総額を置き換える
            cost = t["cost_override"]
        choices = eng._mana_choices(cid, p, face, cost=cost, civs=t.get("cost_civs"))
        if not choices:
            eng._pop(t)
            return None
        opts = [{"key": "mana:" + ",".join(sorted(s.cards[c].defn for c in ch)), "cids": ch} for ch in choices]
        ans, dd = eng.ask(t, p, "pay_mana", opts)
        if dd:
            return dd
        for c in opts[ans[0]]["cids"] + t.get("tap", []):
            s.cards[c].tapped = True
        # フォートE（第168弾）: 召喚コストとしてタップしたマナを記録する。
        # t["tap"] はハイパーエナジーでタップしたバトルゾーンのクリーチャー（マナではない）なので含めない
        t["summon_paid"] = list(opts[ans[0]]["cids"])
        t["paid_done"] = True   # 後段（バズレンダ等）の決定で再入しても二重に支払わない
    if d.bazurenda and not t["free"]:   # バズレンダ: 追加でこのコストを好きな回数支払ってもよい
        while not t.get("bz_done"):
            cnt = t.get("bz_count", 0)
            if t.get("bz_yn_for") != cnt:
                ans, dd = eng.ask(t, p, "yes_no", [{"key": "yes"}, {"key": "no"}], prompt="バズレンダ: 追加で支払う")
                if dd:
                    return dd
                t["bz_yn_for"] = cnt
                t["bz_pay"] = ans[0] == 0
            if not t["bz_pay"]:
                t["bz_done"] = True
                break
            if t.get("bz_paid_for") != cnt:
                choices = eng._mana_choices(cid, p, face, cost=d.bazurenda["cost"],
                                            civs=d.bazurenda.get("civs") or None)
                if not choices:
                    t["bz_done"] = True
                    break
                opts = [{"key": "mana:" + ",".join(sorted(s.cards[c].defn for c in ch)), "cids": ch} for ch in choices]
                ans, dd = eng.ask(t, p, "pay_mana", opts)
                if dd:
                    return dd
                for c in opts[ans[0]]["cids"]:
                    s.cards[c].tapped = True
                t.setdefault("summon_paid", []).extend(opts[ans[0]]["cids"])   # バズレンダの追加支払いも召喚のためのタップ
                t["bz_paid_for"] = cnt
            t["bz_count"] = cnt + 1
    if d.o_drive and not t["free"] and not t.get("od_done"):   # O・ドライブ: 追加で指定文明のマナをタップしてもよい
        od = d.o_drive
        if "civs" in od:
            steps = [[(cv, n)] for cv, n in od["civs"].items()] if od.get("each") else [list(od["civs"].items())]
        else:
            steps = [[(od["civ"], od["count"])]]
        tapped_civs = t.setdefault("od_civs_done", [])
        idx = t.get("od_idx", 0)
        while idx < len(steps):
            step = steps[idx]   # [(文明, 枚数), ...]（まとめて形は全文明が1ステップ、文明別形は1文明ずつ）
            def _feasible(st, used):
                if not st:
                    return True
                (cv, n), rest = st[0], st[1:]
                pool = [c for c in eng.zlist("mana", p) if not s.cards[c].tapped and c not in used
                        and cv in eng.chars_ro(c)["civs"]]
                from itertools import combinations
                return any(_feasible(rest, used | set(comb)) for comb in combinations(pool, min(n, len(pool))) if len(pool) >= n)
            if t.get("od_yn") is None:
                if not _feasible(step, set()):
                    t["od_yn"] = False
                else:
                    ans, dd = eng.ask(t, p, "yes_no", [{"key": "yes"}, {"key": "no"}], prompt="O・ドライブ: 追加でタップする")
                    if dd:
                        t["od_idx"] = idx
                        return dd
                    t["od_yn"] = ans[0] == 0
            if t["od_yn"]:
                sub = t.get("od_sub", 0)
                while sub < len(step):
                    cv, n = step[sub]
                    pool = [c for c in eng.zlist("mana", p) if not s.cards[c].tapped
                            and cv in eng.chars_ro(c)["civs"]]
                    ans, dd = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in pool], n, n)
                    if dd:
                        t["od_idx"], t["od_sub"] = idx, sub
                        return dd
                    for i in ans:
                        s.cards[pool[i]].tapped = True
                    t.setdefault("summon_paid", []).extend(pool[i] for i in ans)   # O・ドライブの追加タップも召喚のためのタップ
                    tapped_civs.append(cv)
                    sub += 1
                t["od_sub"] = 0
            t["od_yn"] = None
            idx += 1
        t["odrive"] = bool(tapped_civs)
        t["odrive_civs"] = list(tapped_civs)
        t["od_done"] = True
    eng._pop(t)
    from_zone = s.cards[cid].zone
    eng._to_hold(cid)
    if sst_bonus:
        s.cards[cid].sst = True
    if stp_bonus:
        s.cards[cid].stp = True
    if t.get("odrive"):
        s.cards[cid].odrive = True
        s.cards[cid].odrive_civs = list(t.get("odrive_civs", []))
    # フォートE（第168弾）: 召喚時にタップしたマナを種族のスナップショットつきで刻む
    paid_snapshot = [{"ref": s.ref(c), "races": list(eng.chars_ro(c)["races"])}
                     for c in t.get("summon_paid", [])]
    if paid_snapshot:
        s.cards[cid].summon_tapped = [dict(e, ref=list(e["ref"])) for e in paid_snapshot]
    # 第189弾: 召喚時の支払い行動で選んだカードを刻む（出た時の誘発が ref: fuel で参照する）
    fuel_snapshot = [list(s.ref(c)) for c in t.get("fuel", [])]
    if fuel_snapshot:
        s.cards[cid].summon_fuel = [list(r) for r in fuel_snapshot]
    if d.bazurenda:
        s.cards[cid].bazurenda = t.get("bz_count", 0)
    if face is not None:
        s.cards[cid].face = face
    ref = s.ref(cid)
    if t.get("to_shield") or d.is_castle():   # ギャラクシールド / G城: 代替コストを払って、または通常の実行で表向きにシールド化する（召喚ではない）
        eng._push(eng.ev_task({"ev": "move", "subject": ref, "from": from_zone, "to": "shield", "reason": "put",
                               "controller": p, "face_up": True}))
        return None
    if d.is_creature():
        ev = {"ev": "move", "subject": ref, "from": from_zone, "to": "bz", "reason": "summon", "controller": p,
              "unpaid": bool(t["free"]) and not t.get("as_paid")}
        if sst_bonus:
            ev["sst"] = True
        if stp_bonus:
            ev["stp"] = True
        if t.get("odrive"):
            ev["odrive"] = True
            ev["odrive_civs"] = list(t.get("odrive_civs", []))
        if paid_snapshot:   # フォートE: 移動で印が消えるためイベントに載せて出し直す（odrive と同じ作法）
            ev["summon_tapped"] = [dict(e, ref=list(e["ref"])) for e in paid_snapshot]
        if fuel_snapshot:   # 第189弾: 同上
            ev["summon_fuel"] = [list(r) for r in fuel_snapshot]
        if t.get("alt"):
            ev["alt"] = True
        if t.get("vivid"):
            ev["vivid"] = True
        if t.get("via"):
            ev["via"] = t["via"]   # 出し方の印（第149弾。D・D・D で出した時は via: d_d_d）
        if d.bazurenda:
            ev["bazurenda"] = t.get("bz_count", 0)
        if t.get("evo"):
            ev["stack_on"] = t["evo"][0]
            ev["evolution"] = True   # 進化として重ねた印（第150弾: evolve_base レコードは進化の時だけ出す。無月の門の summon_on には付けない）
            if len(t["evo"]) > 1:
                ev["stack_more"] = t["evo"][1:]
        eng._push(eng.ev_task(ev))
    elif d.is_permanent():      # タマシード・フィールド・クロスギア: 実行（展開・ジェネレート）したらバトルゾーンに出る（315.2, 308.2, 303.2）
        ev = {"ev": "move", "subject": ref, "from": from_zone, "to": "bz", "reason": "put",
              "controller": p, "via": t.get("via") or "generate", "unpaid": bool(t["free"])}
        # 出し方の印（第149弾）: play_self の via があればそちらを優先し、無ければ従来どおり generate
        if sst_bonus:
            ev["sst"] = True
        if fuel_snapshot:   # 第189弾: 移動で消える召喚時燃料の記録を出し直す
            ev["summon_fuel"] = [list(r) for r in fuel_snapshot]
        if d.bazurenda:
            ev["bazurenda"] = t.get("bz_count", 0)
        eng._push(eng.ev_task(ev))
    else:   # 呪文: 唱えた → 書かれた順に解決 → 最終段階として墓地へ（605.2f）
        if t.get("recycle"):   # リサイクル（第172弾）: 唱えた後は墓地に置くかわりに山札の一番下へ
            t["resolve_to"] = "deck"
            t["resolve_position"] = "bottom"
        env = {"you": p, "self": ref, "vars": {}}
        if t.get("st"):
            env["in_st"] = True
        if t.get("alt"):
            env["alt_paid"] = True
        if t.get("vivid"):
            env["vivid_paid"] = True
        if t.get("recycle"):
            env["recycle_paid"] = True
        if t.get("via") == "d_d_d":
            env["ddd_paid"] = True   # D・D・D で唱えた（第149弾。「この呪文を『D・D・D』で唱えたなら」）
        spell_ops = list(d.spell) + (list(d.sst_spell) if s.cards[cid].sst else []) \
            + (list(d.stp_spell) if s.cards[cid].stp else []) \
            + (list(d.odrive_spell) if s.cards[cid].odrive else [])
        reps = 1 + (s.cards[cid].bazurenda if d.bazurenda else 0)   # バズレンダ呪文は能力を1+追加回数使う
        cev = {"ev": "cast", "player": p, "subject": ref, "unpaid": bool(t["free"])}
        if t.get("vivid"):
            cev["vivid"] = True
        if t.get("recycle"):
            cev["recycle"] = True
        if t.get("via"):
            cev["via"] = t["via"]   # 出し方の印（第149弾。when: {event: cast, via: d_d_d} の照合用）
        eng._push(eng.ev_task(cev),
                   *([eng._child(spell_ops, env)] * reps),
                   eng.ev_task({"ev": "move", "subject": ref, "from": from_zone, "to": t.get("resolve_to", "hand" if cyc else d.resolve_to),
                                 "reason": "resolve", "position": t.get("resolve_position", "top")}),
                   *([eng._child(d.after_resolve, env)] if d.after_resolve else []))
    if t.get("reduced") and ch0["opt_reduce"].get("then"):   # 減らして実行したら、そのターンの終わりに処理する。実行の解決より後に積む＝先に処理する
        then = ch0["opt_reduce"]["then"]
        end = [{"op": "move", "select": {"ref": "self_entered"}, "to": "graveyard", "reason": "destroy"}] if then == "destroy" else \
              [{"op": "move", "select": {"ref": "self_entered"}, "to": "deck", "reason": "put", "position": "bottom"},
               {"op": "draw", "count": 1}]
        eng._push(eng._child([{"op": "delayed_trigger", "when": {"event": "turn_end"}, "effect": end}],
                             {"you": p, "self": ref, "vars": {}}))
    if t.get("once_src") is not None and from_zone in ("graveyard", "mana"):   # 回数制限つき許可（ターン1回）を使った
        s.turn_counters[f"summon_once:{t['once_src']}"] = True
    if t.get("rush") and from_zone == "graveyard" and d.is_creature() and "abyss_rush" in d.keywords:   # アビスラッシュの付随処理（素の墓地召喚には付けない）
        s.turn_counters[f"rush:{cid}"] = s.turn      # このターン、召喚酔いでもプレイヤーを攻撃できる
        eng._push(eng._child([{"op": "delayed_trigger", "when": {"event": "turn_end"},
                               "effect": [{"op": "move", "select": {"ref": "self_entered"},
                                           "to": "deck", "reason": "put", "position": "bottom"}]}],
                             {"you": p, "self": ref, "vars": {}}))   # ターンの終わりに山札の下へ
    if t.get("sac"):       # ササゲール: 軽減したら破壊する（支払いの一部。実行の解決より先に行う）
        eng._push(eng.ev_task([{"ev": "move", "subject": s.ref(c), "to": "graveyard", "reason": "destroy"}
                               for c in t["sac"]]))
    return None
