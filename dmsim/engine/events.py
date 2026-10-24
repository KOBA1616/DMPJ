"""イベント・パイプライン（置換→同時適用→状況起因処理→誘発）と待機・解決窓。"""
from __future__ import annotations

from ..types import CloseWinTask, EnqueueStTask, EventTask, OpenWinTask, ResolvePendingTask
from .registry import task


class EventMixin:
    def ev_task(self, evs, env: dict | None = None) -> dict:
        """同時に起こるイベントの束（400.7, 609.9）。"""
        if isinstance(evs, dict):
            evs = [evs]
        if env and env.get("no_replace"):
            evs = [dict(e, replaced=True) for e in evs]   # 置換後のイベントはそれ以上置換しない（101.5）
        return {"t": "event", "evs": evs, "i": 0, "rp": 0, "skip": [], "instead": []}

    def _replacement(self, t, ev):
        """置換効果の選択。ターン・プレイヤーの効果を優先し、同じプレイヤーの複数は本人が選ぶ（609.8）。
        戻り値: None（置換なし）/ Decision / 置換後に実行する effect タスク。"""
        rec = self._record_for(ev)
        if rec is None:
            return None
        order = (self.s.active, 1 - self.s.active)
        while t["rp"] < 2:
            p = order[t["rp"]]
            cands = []
            for src in self.bz_tops(p):
                for i, ab in self.abilities(src, "replace"):
                    if self._pattern_match(ab["when"], rec, src, None):
                        cands.append((src, i, ab))
            if cands:
                opts = [{"key": f"replace:{self.s.cards[s_].defn}:{i}", "cid": s_, "ab": i} for s_, i, _ in cands]
                if all(ab.get("optional") for _, _, ab in cands):
                    opts.append({"key": "decline"})
                a, d = self.ask(t, p, "choose_replacement", opts)
                if d:
                    return d
                o = opts[a[0]]
                if o["key"] != "decline":
                    src, i = o["cid"], o["ab"]
                    env = {"you": self.s.cards[src].controller, "self": self.s.ref(src), "event": rec,
                           "vars": {}, "no_replace": True}
                    return self._child(self.fdef(src).abilities[i]["instead"], env)
            t["rp"] += 1
        return None

    def _record_for(self, ev):
        """適用前のイベントを、誘発・置換の照合用レコードにする。"""
        s = self.s
        if ev["ev"] == "move":
            if not s.alive(ev["subject"]):
                return None
            c = s.cards[ev["subject"][0]]
            return {"ev": "move", "subject": ev["subject"], "from": ev.get("from") if c.zone == "hold" else c.zone,
                    "to": ev["to"], "reason": ev["reason"], "controller": c.controller}
        if ev["ev"] == "draw":
            return {"ev": "draw", "player": ev["player"]}
        return None

    def apply_batch(self, evs: list[dict]):
        records = []
        for ev in evs:
            records += self._apply_one(ev)
        self._sba()
        for r in records:
            self._collect_triggers(r)

    def _apply_one(self, ev: dict) -> list[dict]:
        s = self.s
        kind = ev["ev"]
        if kind == "move":
            if not s.alive(ev["subject"]):
                return []   # 想定外のゾーンへ移っていたら、それ以上処理しない（400.8）
            cid = ev["subject"][0]
            c = s.cards[cid]
            from_zone = ev.get("from") if c.zone == "hold" else c.zone
            lki = {"defn": c.defn, "face": c.face, "controller": c.controller, "zone": from_zone,
                   "tapped": c.tapped, "chars": self.chars(cid), "ref": list(ev["subject"])}   # 過去の状態を見る（603.5c）
            unders = list(c.under)
            if ev.get("card_only") and unders:   # カードとして離れる: 下のカードを再構築（801.4, 703.4h）
                self._rebuild(cid)
                unders = []
            self._raw_move(cid, ev["to"], ev.get("position", "top"), ev.get("controller"))
            for u in unders:   # クリーチャーとして離れたら下のカードも同じゾーンへ（109.2b, 316.3）
                if s.cards[u].zone == "bz":
                    self._raw_move(u, ev["to"])
            new = s.ref(cid)
            stack_on = ev.get("stack_on")
            if ev["to"] == "bz" and stack_on and s.alive(stack_on):
                self._stack(cid, stack_on[0])
            out = [{"ev": "move", "subject": new, "lki": lki, "from": from_zone, "to": ev["to"],
                    "reason": ev["reason"], "controller": c.controller}]
            if ev["reason"] == "summon":
                out.append({"ev": "summon", "subject": new, "controller": c.controller})
            return out
        if kind == "draw":
            p = ev["player"]
            deck = s.zones["deck"][p]
            if not deck:
                return []   # 山札が無ければ何もしない。「引いた時」も誘発しない（114.6a）
            cid = deck[0]
            self._raw_move(cid, "hand")
            return [{"ev": "draw", "player": p, "subject": s.ref(cid)},
                    {"ev": "move", "subject": s.ref(cid), "lki": None, "from": "deck", "to": "hand",
                     "reason": "draw", "controller": p}]
        if kind in ("tap", "untap"):
            if not s.alive(ev["subject"]):
                return []
            c = s.cards[ev["subject"][0]]
            if c.tapped == (kind == "tap"):
                return []   # 「になる」誘発は状態が変わった時だけ（603.2c）
            c.tapped = kind == "tap"
            return [{"ev": kind, "subject": ev["subject"], "controller": c.controller}]
        if kind in ("attack", "block", "cast", "turn_start", "turn_end", "break", "battle_win"):
            return [dict(ev)]
        raise ValueError(kind)

    def _stack(self, top: int, base: int):
        """進化: base（とその下）を top の下に重ねる（801.1, 801.2）。同一のクリーチャーとして扱い、
        タップ状態と受けていた効果を引き継ぐ。進化クリーチャーは召喚酔いしない（801.3）。"""
        s = self.s
        t, b = s.cards[top], s.cards[base]
        old = s.ref(base)
        t.under = [base] + b.under
        for u in t.under:
            s.cards[u].top_of = top
        b.under = []
        t.tapped = b.tapped
        t.entered_turn = -1
        new = s.ref(top)
        for ce in s.continuous:
            if ce["affected"] is not None and old in ce["affected"]:
                ce["affected"].append(new)
        for t_ in s.tasks:   # 攻撃中のクリーチャーが進化しても攻撃は続く（801.2a）
            if t_["t"] == "attack" and t_["attacker"] == old:
                t_["attacker"] = new

    def _rebuild(self, top: int):
        """再構築（801.4）。下のカードのうち、一番上の単独で存在できるカード（クリーチャー）を残す。"""
        s = self.s
        c = s.cards[top]
        under = list(c.under)
        c.under = []
        while under and "creature" not in self.cdef(under[0]).types:
            self._raw_move(under.pop(0), "graveyard")
        if not under:
            return
        nt = s.cards[under[0]]
        nt.top_of = -1
        nt.under = under[1:]
        for u in nt.under:
            s.cards[u].top_of = nt.cid
        nt.tapped = c.tapped                                   # 801.4d
        nt.entered_turn = -1 if c.entered_turn != s.turn else c.entered_turn   # 801.4c（簡略）
        old, new = s.ref(top), s.ref(nt.cid)
        for ce in s.continuous:
            if ce["affected"] is not None and old in ce["affected"]:
                ce["affected"].append(new)

    def _sba(self):
        """状況起因処理（703.3: 条件を満たすものすべてを単一のイベントとして同時に処理）。"""
        s = self.s
        if s.result is not None:
            return
        out = [p for p in (0, 1) if not s.zones["deck"][p]]   # 703.4b 山札0枚で敗北（104.2b: 効果の途中でも）
        if out:
            s.result = {"winner": None if len(out) == 2 else 1 - out[0], "reason": "deck_out", "turn": s.turn}
            return
        dead = [s.ref(c) for c in self.bz_tops()
                if "creature" in self.chars(c)["types"] and self.chars(c)["power"] <= 0]   # 703.4c
        if dead:
            self._push(self.ev_task([{"ev": "move", "subject": r, "to": "graveyard", "reason": "destroy"}
                                     for r in dead]))

    def _subject_match(self, pat, cid, env, lki, base=False) -> bool:
        if pat == "self":
            return env.get("self") is not None and cid == env["self"][0]
        if not isinstance(pat, dict):
            return False
        if "refs" in pat:   # 遅延誘発型能力が「その〜」で指すカード
            return [cid, self.s.cards[cid].gen] in pat["refs"] or (lki is not None and lki["ref"] in pat["refs"])
        ctrl = lki["controller"] if lki else self.s.cards[cid].controller
        if "owner" in pat and pat["owner"] != "any" and ctrl != self._rel(pat["owner"], env):
            return False
        if pat.get("other") and env.get("self") and cid == env["self"][0]:
            return False
        return self.filter_match(cid, pat.get("filter", {}), lki, base)

    def _pattern_match(self, when, rec, src, lki_src) -> bool:
        env = {"you": lki_src["controller"] if lki_src else self.s.cards[src].controller,
               "self": lki_src["ref"] if lki_src else self.s.ref(src)}
        return self._match_when(when, rec, env)

    def _match_when(self, when, rec, env) -> bool:
        if when["event"] != rec["ev"]:
            return False
        for k in ("from", "to", "reason"):
            if k in when and rec.get(k) != when[k]:
                return False
        if "player" in when and rec.get("player") != self._rel(when["player"], env):
            return False
        if "subject" in when:
            if "subject" not in rec:
                return False
            subj = rec["subject"][0]
            if when["subject"] == "self":
                return env.get("self") is not None and subj == env["self"][0]
            lki = rec.get("lki") if rec.get("from") == "bz" else None
            return self._subject_match(when["subject"], subj, env, lki)
        return True

    def _collect_triggers(self, rec):
        """誘発チェック。離れた時の誘発で過去の状態を見るのは、その能力を持つカード自身だけ（603.5d）。"""
        s = self.s
        sources = [(c, None) for c in self.bz_tops()]
        lki = rec.get("lki")
        if lki and lki["zone"] == "bz" and rec.get("to") != "bz":
            sources.append((rec["subject"][0], lki))
        win = s.windows[-1] if s.windows else 0
        for src, lsrc in sources:
            if lsrc:
                face = lsrc["face"]
                abs_ = list(enumerate(self.rules.cards[lsrc["defn"]].face(None if face < 0 else face).abilities))
                abs_ = [(i, ab) for i, ab in abs_ if ab["kind"] == "trigger"]
                defn = lsrc["defn"]
            else:
                face = s.cards[src].face
                abs_ = self.abilities(src, "trigger")
                defn = s.cards[src].defn
            for i, ab in abs_:
                if not self._pattern_match(ab["when"], rec, src, lsrc):
                    continue
                ctrl = lsrc["controller"] if lsrc else s.cards[src].controller
                sref = lsrc["ref"] if lsrc else s.ref(src)
                s.seq += 1
                # 待機中の効果は発生源から独立する（110.5a）。発生源の情報は env に持つ
                p = {"pid": s.seq, "kind": "normal", "win": win, "controller": ctrl, "src": sref,
                     "defn": defn, "ab": i, "env": {"you": ctrl, "self": sref, "event": rec, "vars": {}}}
                if face >= 0:
                    p["face"] = face
                s.pending.append(p)
        for dl in list(s.delayed):   # 遅延誘発型能力（603.6）
            if self._match_when(dl["when"], rec, dl["env"]):
                s.seq += 1
                env = dict(dl["env"], event=rec, vars=dict(dl["env"].get("vars", {})))
                s.pending.append({"pid": s.seq, "kind": "delayed", "win": win, "controller": dl["controller"],
                                  "src": None, "defn": "", "ab": -1, "env": env, "effect": dl["effect"],
                                  "delayed": dl["id"]})
                if dl["once"]:
                    s.delayed.remove(dl)

    def _window(self, *inner, only_st=False):
        """inner を実行し、その間に誘発した効果をその場で解決するタスク列。"""
        self.s.seq += 1
        w = self.s.seq
        return [{"t": "open_win", "win": w}, *inner,
                {"t": "resolve_pending", "win": w, "only_st": only_st},
                {"t": "close_win"}]

    def pending_ability(self, p) -> dict:
        if p["kind"] == "delayed":
            return {"effect": p["effect"]}
        return self.rules.cards[p["defn"]].face(p.get("face")).abilities[p["ab"]]


@task("event", EventTask)
def h_event(eng, t):
    while t["i"] < len(t["evs"]):
        ev = t["evs"][t["i"]]
        if not ev.get("replaced"):
            r = eng._replacement(t, ev)
            if r is not None and "options" in r:
                return r
            if r is not None:
                t["skip"].append(t["i"])
                t["instead"].append(r)
        t["i"] += 1
        t["rp"] = 0
    eng._pop(t)
    eng._push(*t["instead"])
    eng.apply_batch([e for k, e in enumerate(t["evs"]) if k not in t["skip"]])
    return None


@task("open_win", OpenWinTask)
def h_open_win(eng, t):
    eng._pop(t)
    eng.s.windows.append(t["win"])
    return None


@task("close_win", CloseWinTask)
def h_close_win(eng, t):
    """窓を閉じる。解決しきれなかった（S・トリガー以外の）効果は外側の窓へ戻す。"""
    eng._pop(t)
    s = eng.s
    w = s.windows.pop()
    outer = s.windows[-1] if s.windows else 0
    for p in s.pending:
        if p["win"] == w:
            p["win"] = outer
    return None


@task("resolve_pending", ResolvePendingTask)
def h_resolve_pending(eng, t):
    """101.4 / 605.1: S・トリガー系（ターン→非ターン）→ ターン・プレイヤーが自分の効果を好きな順 → 非ターン。
    1つ解決するたびに選び直すので、非ターン側の処理中に誘発したターン側の効果が先になる（101.4c）。"""
    s = eng.s
    win = t["win"]
    here = [p for p in s.pending if p["win"] == win]
    st = [p for p in here if p["kind"] == "strigger"]
    if st:
        pool = [p for p in st if p["controller"] == s.active] or st
    elif t["only_st"]:
        pool = []
    else:
        pool = [p for p in here if p["controller"] == s.active] or here
    if not pool:
        eng._pop(t)
        return None
    player = pool[0]["controller"]
    opts = [{"key": f"pending:{p['kind']}:{p['defn']}:{p['ab']}", "pid": p["pid"]} for p in pool]
    a, d = eng.ask(t, player, "order_pending", opts)
    if d:
        return d
    pid = opts[a[0]]["pid"]
    p = next(x for x in s.pending if x["pid"] == pid)
    s.pending.remove(p)
    if p["kind"] == "strigger":
        if s.alive(p["src"]):
            eng._push(eng.play_task(p["src"][0], player, True, p.get("face")))
    else:
        ab = eng.pending_ability(p)
        env = p["env"]
        if "if" in ab and not eng.eval_cond(ab["if"], env):   # 条件は解決時に確認（603.4, 605.2a）
            return None
        eng._push(eng._child(ab["effect"], env))
    return None


@task("enqueue_st", EnqueueStTask)
def h_enqueue_st(eng, t):
    s = eng.s
    eng._pop(t)
    win = s.windows[-1] if s.windows else 0
    for c, face in t["cids"]:
        if s.cards[c].zone == "hand":
            s.seq += 1
            p = {"pid": s.seq, "kind": "strigger", "win": win, "controller": t["player"],
                 "src": s.ref(c), "defn": s.cards[c].defn, "ab": -1, "env": {}}
            if face is not None:
                p["face"] = face
            s.pending.append(p)
    return None
