"""イベント・パイプライン（置換→同時適用→状況起因処理→誘発）と待機・解決窓。"""
from __future__ import annotations

from ..types import CaptureTask, CloseWinTask, EnqueueStTask, EventTask, OpenWinTask, ResolvePendingTask
from .registry import task


class EventMixin:
    def ev_task(self, evs, env: dict | None = None) -> dict:
        """同時に起こるイベントの束（400.7, 609.9）。"""
        if isinstance(evs, dict):
            evs = [evs]
        if env and env.get("capture"):   # 置換効果の中で起こすイベントは、元の束に加えて同時に適用する（609.9）
            return {"t": "capture", "evs": [dict(e, replaced=True) for e in evs]}
        if env and env.get("no_replace"):
            evs = [dict(e, replaced=True) for e in evs]   # 置換後のイベントはそれ以上置換しない（101.5）
        return {"t": "event", "evs": evs, "i": 0, "rp": 0, "skip": [], "instead": [], "captured": [], "applying": False}

    def _replacement(self, t, ev, p):
        """プレイヤー p の置換効果の選択。同じプレイヤーの複数は本人が選ぶ（609.8）。
        戻り値: None（置換なし）/ Decision / 置換後に実行する effect タスク。"""
        rec = self._record_for(ev)
        if rec is None:
            return None
        cands = []
        for src in self.bz_tops(p):
            for i, ab in self.abilities(src, "replace"):
                if self._pattern_match(ab["when"], rec, src, None):
                    if "if" in ab:   # 置換効果にも条件を書ける（《水上第九院 シャコガイル》の最後の1枚判定）
                        env = {"you": self.s.cards[src].controller, "self": self.s.ref(src),
                               "event": rec, "vars": {}}
                        if not self.eval_cond(ab["if"], env):
                            continue
                    cands.append((src, i, ab))
        cands_ab = [((s_, i), ab) for s_, i, ab in cands]
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
                       "vars": {}, "no_replace": True, "capture": True}
                ab = next(a for j, a in cands_ab if j == (src, i))
                return self._child(ab["instead"], env)
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
        if evs and not any(ev.get("sba") for ev in evs):
            self.s.sba_held.clear()   # 状況起因処理以外で状態が動いたら、止められていた破壊をもう一度試す
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
            if ev["to"] == "bz" and c.zone != "hold" and not self.permits(cid, "enter_bz"):
                return []   # 出せない（実行は h_play で先に確認している。効果で出す場合はここで止める）
            from_zone = ev.get("from") if c.zone == "hold" else c.zone
            lki = {"defn": c.defn, "face": c.face, "controller": c.controller, "zone": from_zone,
                   "tapped": c.tapped, "chars": self.chars(cid), "ref": list(ev["subject"])}   # 過去の状態を見る（603.5c）
            unders = list(c.under)
            if ev.get("card_only") and unders:   # カードとして離れる: 下のカードを再構築（801.4, 703.4h）
                self._rebuild(cid)
                unders = []
            self._raw_move(cid, ev["to"], ev.get("position", "top"), ev.get("controller"))
            if ev.get("tapped"):   # 「タップして置く」: 置かれた時点でタップ状態（別のタップ イベントにしない）
                c.tapped = True
            for u in unders:   # クリーチャーとして離れたら下のカードも同じゾーンへ（109.2b, 316.3）
                if s.cards[u].zone == "bz":
                    self._raw_move(u, ev["to"])
            new = s.ref(cid)
            stack_on = ev.get("stack_on")
            if ev["to"] == "bz" and stack_on and s.alive(stack_on):
                base = stack_on[0]
                if s.cards[base].zone != "bz":      # 超無限墓地進化など: 進化元も自分のゾーンから移す
                    self._raw_move(base, "bz")
                self._stack(cid, base)
                for x in ev.get("stack_more", []):   # 進化元の残り（801.1b。超無限墓地進化やバトルゾーンの複数の進化元）
                    if not s.alive(x):
                        continue
                    if s.cards[x[0]].zone == "graveyard":
                        self._raw_move(x[0], "bz")
                    if s.cards[x[0]].zone == "bz":
                        self._stack(cid, x[0], more=True)
            out = [{"ev": "move", "subject": new, "lki": lki, "from": from_zone, "to": ev["to"],
                    "reason": ev["reason"], "controller": c.controller}]
            if ev.get("via"):
                out[0]["via"] = ev["via"]
            if ev["to"] == "bz" and "ex_life" in self.chars(cid)["keywords"]:
                out += self._exlife_shield(cid)
            if ev["reason"] == "summon":
                out.append({"ev": "summon", "subject": new, "controller": c.controller, "player": c.controller,
                            "unpaid": bool(ev.get("unpaid"))})
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

    def _exlife_shield(self, cid: int) -> list[dict]:
        """EXライフ: このクリーチャーを出す時、自分の山札の上から1枚目をシールド化し、このクリーチャーに紐付ける。
        （総合ルール Ver.1.53 には定義がなく、公式カード・裁定に基づく。出た時の能力より先に済ませる）"""
        s = self.s
        p = s.cards[cid].controller
        deck = s.zones["deck"][p]
        if not deck:
            return []
        top = deck[0]
        self._raw_move(top, "shield", "top")
        s.cards[top].exlife_of = s.ref(cid)
        return [{"ev": "move", "subject": s.ref(top), "lki": None, "from": "deck", "to": "shield",
                 "reason": "put", "controller": p}]

    def _stack(self, top: int, base: int, more: bool = False):
        """進化: base（とその下）を top の下に重ねる（801.1, 801.2）。同一のクリーチャーとして扱い、
        タップ状態と受けていた効果を引き継ぐ。進化クリーチャーは召喚酔いしない（801.3）。
        more は2枚目以降の進化元（801.1b）。タップ状態は1枚でもタップなら進化後もタップ（801.2b）。"""
        s = self.s
        t, b = s.cards[top], s.cards[base]
        old = s.ref(base)
        for p in (0, 1):   # 進化元の EXライフシールドは進化後のクリーチャーに引き継がれる（2026-04-10 裁定）
            for sh in s.zones["shield"][p]:
                if s.cards[sh].exlife_of is not None and list(s.cards[sh].exlife_of) == old:
                    s.cards[sh].exlife_of = s.ref(top)
        t.under = (t.under if more else []) + [base] + b.under
        for u in t.under:
            s.cards[u].top_of = top
        b.under = []
        t.tapped = (t.tapped or b.tapped) if more else b.tapped
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
        # 801.4c: 新たに出るわけではないので、そのカード自身の出たターンをそのまま使う
        # （ターンのはじめから下にあったなら酔わず、このターンに出た進化元なら酔う）
        old, new = s.ref(top), s.ref(nt.cid)
        for ce in s.continuous:
            if ce["affected"] is not None and old in ce["affected"]:
                ce["affected"].append(new)

    def _sba(self):
        """状況起因処理（703.3: 条件を満たすものすべてを単一のイベントとして同時に処理）。
        イベントの後のほか、イベントを通さずに状態が変わった時（継続的効果の生成・終了など）にも呼ぶ（111.2d）。"""
        self._push(*self._sba_tasks())

    def _sba_tasks(self) -> list[dict]:
        s = self.s
        if s.result is not None:
            return []
        # 703.4b 山札0枚で敗北。104.2b: 効果の途中で一瞬でも0枚になっていれば0枚とみなす
        out = sorted(set(s.deck_emptied) | {p for p in (0, 1) if not s.zones["deck"][p]})
        if out:
            # 両者が同時に0枚ならターン・プレイヤーの敗北とする（プロジェクトの裁定。条文に明記なし）
            loser = s.active if len(out) == 2 else out[0]
            s.result = {"winner": 1 - loser, "reason": "deck_out", "turn": s.turn}
            return []
        dead = [s.ref(c) for c in self.bz_tops()
                if "creature" in self.chars(c)["types"] and self.chars(c)["power"] <= 0]   # 703.4c
        # 「墓地に置かれるかわりにとどまる」置換で破壊できなかったものは、状態が動くまで同じ処理を繰り返さない
        # （繰り返すと無限ループになる）。パワーが0より大きくなれば対象から外れる
        s.sba_held = [r for r in s.sba_held if r in dead]
        dead = [r for r in dead if r not in s.sba_held]
        if dead:
            s.sba_held += [r for r in dead if r not in s.sba_held]
            return [self.ev_task([{"ev": "move", "subject": r, "to": "graveyard", "reason": "destroy", "sba": True}
                                  for r in dead])]
        return []

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
        for k in ("from", "to", "reason", "via"):
            if k in when and rec.get(k) != when[k]:
                return False
        if "unpaid" in when and bool(rec.get("unpaid")) != when["unpaid"]:   # マナをタップせずに（コストを支払わずに）
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
        zt = self.rules.zone_trigger_defs
        if zt:   # 墓地などで機能する誘発型能力（《黒神龍グールジェネレイド》など）
            for z in sorted({z for v in zt.values() for z in v}):
                sources += [(c, None) for p in (0, 1) for c in self.zlist(z, p) if s.cards[c].defn in zt]
        lki = rec.get("lki")
        if lki and lki["zone"] == "bz" and rec.get("to") != "bz":
            sources.append((rec["subject"][0], lki))
        win = s.windows[-1] if s.windows else 0
        for src, lsrc in sources:
            if lsrc:
                face = lsrc["face"]
                abs_ = list(enumerate(self.rules.cards[lsrc["defn"]].face(None if face < 0 else face).abilities))
                abs_ = [(i, ab) for i, ab in abs_ if ab["kind"] == "trigger" and ab.get("zone", "bz") == "bz"]
                defn = lsrc["defn"]
            else:
                face = s.cards[src].face
                abs_ = [(i, ab) for i, ab in self.abilities(src, "trigger")
                        if ab.get("zone", "bz") == s.cards[src].zone]
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
                if i < 0:          # 継続的効果で得た能力は、能力そのものを持たせる
                    p["inline"] = ab
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
        if "inline" in p:
            return p["inline"]
        return self.rules.cards[p["defn"]].face(p.get("face")).abilities[p["ab"]]


@task("event", EventTask)
def h_event(eng, t):
    """置換効果の決定（609.9a）: まずターン・プレイヤーが束の全イベントについて自分の置換効果を決め、
    次に非ターン・プレイヤーが、まだ置換されていないイベントについて決める。決め終えたら同時に適用する。"""
    order = (eng.s.active, 1 - eng.s.active)
    while t["rp"] < 2:
        while t["i"] < len(t["evs"]):
            ev = t["evs"][t["i"]]
            if not ev.get("replaced") and t["i"] not in t["skip"]:
                r = eng._replacement(t, ev, order[t["rp"]])
                if r is not None and "options" in r:
                    return r
                if r is not None:
                    t["skip"].append(t["i"])
                    t["instead"].append(r)
            t["i"] += 1
        t["i"] = 0
        t["rp"] += 1
    if t["instead"] and not t["applying"]:   # 置換後のイベントを集めてから、束と同時に適用する（609.9）
        t["applying"] = True
        eng._push(*t["instead"])
        return None
    eng._pop(t)
    eng.apply_batch([e for k, e in enumerate(t["evs"]) if k not in t["skip"]] + t["captured"])
    return None


@task("capture", CaptureTask)
def h_capture(eng, t):
    """置換効果が起こすイベントを、適用待ちの束（直近の event タスク）に加える。"""
    eng._pop(t)
    host = next(x for x in reversed(eng.s.tasks) if x["t"] == "event" and x["applying"])
    host["captured"] += t["evs"]
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
            eng._push(eng.play_task(p["src"][0], player, True, p.get("face"), st=True))
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
