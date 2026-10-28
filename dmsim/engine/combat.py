"""攻撃ステップ（505〜510）、バトル（701.13）、ブレイクとS・トリガー（509.5, 113.6）、使用宣言（506.3b〜）。

攻撃できるか・ブロックできるか・何枚ブレイクするかは、キーワード名ではなく特性の許可・禁止（permissions.yaml）と
breaks で判定する。キーワードは keywords.yaml でそれらを与える常在型能力として定義する。
"""
from __future__ import annotations

from ..types import AttackTask, BreakTask, DeclareTask, SlayerTask
from .registry import task


class CombatMixin:
    def _can_attack(self, cid) -> bool:
        c = self.s.cards[cid]
        if c.tapped or "creature" not in self.chars(cid)["types"]:
            return False
        return c.entered_turn != self.s.turn or self.permits(cid, "attack_summoning_sick")   # 506.1a

    def _attack_options(self, a):
        out = []
        for cid in self.bz_tops(a):
            if not self._can_attack(cid):
                continue
            dfn = self.s.cards[cid].defn
            if self.permits(cid, "attack_player"):
                out.append({"key": f"attack:{dfn}:player", "cid": cid, "target": "player"})
            allow = [e for e in self.chars(cid)["allow"] if isinstance(e, dict) and e["action"] == "attack_creature"]
            for tc in self.bz_tops(1 - a):
                # 505.2 既定ではタップ状態のクリーチャーだけ。「タップされていないクリーチャーを攻撃できる」(マッハファイター等)は allow で広げる
                if (self.s.cards[tc].tapped or any(e.get("other", {}).get("tapped") is False and self.filter_match(tc, e["other"]) for e in allow)) \
                        and self.permits(cid, "attack_creature", tc) and self.permits(tc, "be_attacked", cid):
                    out.append({"key": f"attack:{dfn}:{self.s.cards[tc].defn}", "cid": cid,
                                "target": self.s.ref(tc)})
        return out

    def _activate_options(self, a, attack_opts):
        """起動型能力（602）のうち「攻撃する代わりにタップして使う」もの。攻撃ができるときだけ使える（602.3a）。
        cost.tap が self ならこのクリーチャー、フィルタなら条件に合う自分のクリーチャー1体をタップする。"""
        can = {o["cid"] for o in attack_opts}
        out = []
        for cid in self.bz_tops(a):
            for i, ab in self.abilities(cid, "activate"):
                env = {"you": a, "self": self.s.ref(cid), "vars": {}}
                if "if" in ab and not self.eval_cond(ab["if"], env):
                    continue
                dfn = self.s.cards[cid].defn
                who = [cid] if ab["cost"]["tap"] == "self" else \
                    [x for x in self.bz_tops(a) if self.filter_match(x, ab["cost"]["tap"])]
                for x in who:
                    if x in can:
                        key = f"activate:{dfn}:{i}" + ("" if x == cid else f":{self.s.cards[x].defn}")
                        out.append({"key": key, "cid": cid, "ab": i, "tap": x})
        return out

    def _battle_substitute(self, t, att, tgt):
        """バトル相手の置換（「かわりにこのクリーチャーにバトルさせてもよい」）。ターン・プレイヤー側から順に選ぶ（609.8）。
        置換効果 when: {event: battle, subject: <置き換えられる側>}、instead: [{op: battle_substitute}] を持つ
        バトルゾーンのクリーチャーが、その側の代わりにバトルする。1回のバトルで同じ側は1度だけ。
        戻り値: (att, tgt, Decision|None)。"""
        s = self.s
        sides = t.setdefault("subbed", [])
        for k, (p, q) in enumerate(((att, tgt), (tgt, att))):
            if k in sides or not s.alive(p) or not s.alive(q):
                continue
            ctrl = s.cards[p[0]].controller
            rec = {"ev": "battle", "subject": p, "opponent": q, "controller": ctrl}
            opts = []
            for src in self.bz_tops(ctrl):
                if src == p[0] or src == q[0]:
                    continue
                for i, ab in self.abilities(src, "replace"):
                    if ab["when"]["event"] == "battle" and self._pattern_match(ab["when"], rec, src, None):
                        opts.append({"key": f"battle_sub:{s.cards[src].defn}:{i}", "cid": src})
            if not opts:
                continue
            a, d = self.ask(t, ctrl, "choose_replacement", opts + [{"key": "decline"}])
            if d:
                return att, tgt, d
            sides.append(k)
            if a[0] < len(opts):
                new = s.ref(opts[a[0]]["cid"])
                if k == 0:
                    att = new
                else:
                    tgt = new
                t["attacker"], t["target"] = att, tgt
                break
        return att, tgt, None

    def _battle_bonus(self, ref, attacking: bool = False) -> int:
        """バトル中だけのパワー修整（mod battle_power。ハンティング: 自分のハンター1体につき+1000）。only: attacking は攻撃側のときだけ。
        「攻撃中」「ブロック中」のパワー修整は mod power_when（バトルをしていない間も含む）。"""
        cid = ref[0]
        env = {"you": self.s.cards[cid].controller, "self": ref}
        total = 0
        for _, ab in self.abilities(cid, "static"):
            bp = ab.get("mod", {}).get("battle_power")
            if bp and bp.get("only") == "attacking" and not attacking:
                continue
            if bp and ab.get("affects") == "self" and ab.get("zone", "bz") == self.s.cards[cid].zone:
                total += bp["amount"] * (self.eval_expr({"count": bp["count"]}, env) if "count" in bp else 1)
        return total

    def _battle(self, x, y):
        """バトル（701.13）。結果で誘発した効果はその場で解決してからバトルを終える。"""
        px = self.chars(x[0])["power"] + self._battle_bonus(x, attacking=True)      # x は攻撃側
        py = self.chars(y[0])["power"] + self._battle_bonus(y)
        losers = ([x] if px <= py else []) + ([y] if py <= px else [])
        winners = [r for r in (x, y) if r not in losers]
        slay = [[r, y if r == x else x] for r in losers if self.permits(r[0], "slayer")]
        evs = [{"ev": "move", "subject": r, "to": "graveyard", "reason": "destroy"} for r in losers]
        evs += [{"ev": "battle_win", "subject": r, "controller": self.s.cards[r[0]].controller} for r in winners]
        out = self._window(self.ev_task(evs))
        if slay:   # 701.13d バトルの後に誘発する「スレイヤー」
            out += self._window({"t": "slayer", "pairs": slay})
        return out

    def _declarable(self, player, rec) -> list[dict]:
        """使用宣言できる能力（603.2e/f）。手札（または ab.zone）にあり、when が rec に合い、if を満たすもの。"""
        s = self.s
        out = []
        for z in ("hand", "mana", "graveyard"):
            for cid in self.zlist(z, player):
                d = self.cdef(cid)
                faces = [(None, d)] if not d.faces else list(enumerate(d.faces))
                for fi, f in faces:
                    for i, ab in enumerate(f.abilities):
                        if ab["kind"] != "declare" or ab.get("zone", "hand") != z:
                            continue
                        env = {"you": player, "self": s.ref(cid), "event": rec, "vars": {}}
                        if not self._match_when(ab["when"], rec, env):
                            continue
                        if "if" in ab and not self.eval_cond(ab["if"], env):
                            continue
                        o = {"key": f"declare:{d.id}:{i}", "cid": cid, "ab": i}
                        if fi is not None:
                            o["face"] = fi
                        if o["key"] not in [x["key"] for x in out]:
                            out.append(o)
        return out


@task("slayer", SlayerTask)
def h_slayer(eng, t):
    eng._pop(t)
    evs = [{"ev": "move", "subject": o, "to": "graveyard", "reason": "destroy"}
           for _, o in t["pairs"] if eng.s.alive(o)]
    if evs:
        eng._push(eng.ev_task(evs))
    return None


@task("declare", DeclareTask)
def h_declare(eng, t):
    """宣言した能力だけを誘発させて待機させる（603.2f）。"""
    s = eng.s
    opts = eng._declarable(t["player"], t["ctx"])
    if not opts:
        eng._pop(t)
        return None
    ans, d = eng.ask(t, t["player"], f"declare_{t['window']}", opts, 0, len(opts))
    if d:
        return d
    eng._pop(t)
    win = s.windows[-1] if s.windows else 0
    for i in ans:
        o = opts[i]
        s.seq += 1
        p = {"pid": s.seq, "kind": "normal", "win": win, "controller": t["player"], "src": s.ref(o["cid"]),
             "defn": s.cards[o["cid"]].defn, "ab": o["ab"],
             "env": {"you": t["player"], "self": s.ref(o["cid"]), "event": t["ctx"], "vars": {}}}
        if "face" in o:
            p["face"] = o["face"]
        s.pending.append(p)
    return None


def _decl(eng, player, window, rec):
    return {"t": "declare", "player": player, "window": window, "ctx": rec}


@task("attack", AttackTask)
def h_attack(eng, t):
    """攻撃ステップのサブステップ（506〜510）。cp=True なので各段階の間に待機効果を解決する。
    使用宣言: 攻撃時はターン・プレイヤー → （待機の解決）→ 非ターン・プレイヤー（506.3b〜e）。
    ブロック時も同じ順（507.3）。"""
    s = eng.s
    att = t["attacker"]
    a = s.active
    ph = t["phase"]
    if s.skip_rest:                                           # ターンの残りをとばす
        eng._pop(t)
        eng._expire("during_attack")
        return None
    if ph == 0:                                               # 506 攻撃クリーチャー指定
        t["phase"] = 1
        s.cards[att[0]].tapped = True
        rec = {"ev": "attack", "subject": att, "target": t["target"], "controller": a}
        eng._push(eng.ev_task(rec), _decl(eng, a, "attack", rec))
        return None
    if ph == 1:                                               # 506.3d 非ターン・プレイヤーの使用宣言
        t["phase"] = 2
        if s.alive(att):
            rec = {"ev": "attack", "subject": att, "target": t["target"], "controller": a}
            eng._push(_decl(eng, 1 - a, "attack", rec))
        return None
    if ph < 5 and (not s.alive(att) or (t["target"] != "player" and not s.alive(t["target"]))):
        t["phase"] = 5                                        # 505.6a 攻撃から取り除かれたら攻撃終了へ
        return None
    if ph == 2:                                               # 507 ブロッククリーチャー指定
        blockers = [c for c in eng.bz_tops(1 - a)
                    if not s.cards[c].tapped and eng.permits(c, "block", att[0])
                    and eng.permits(att[0], "be_blocked", c) and [c, s.cards[c].gen] != t["target"]]
        guards = [] if t["target"] == "player" else [          # 507.1a ガードマン: 攻撃されている自分の他のクリーチャーがいる時だけ
            c for c in eng.bz_tops(1 - a) if not s.cards[c].tapped and [c, s.cards[c].gen] != t["target"]
            and eng.permits(c, "guardman", att[0])]
        forced = [c for c in blockers if "block" in eng.chars(c)["require"]]   # 507.1b ブロックを強制されたクリーチャーは必ず選ぶ
        opts = [eng._card_option(c) for c in blockers] + \
               [eng._card_option(c, key=f"guard:{s.cards[c].defn}") for c in guards] + ([] if forced else [{"key": "no_block"}])
        ans, d = eng.ask(t, 1 - a, "block", opts)
        if d:
            return d
        t["phase"] = 3
        o = opts[ans[0]]
        if o["key"] != "no_block":
            for c in forced:      # 強制された全員が能力を使用する（タップ）。最後に解決する1体が攻撃先になる（507.2）
                s.cards[c].tapped = True
            s.cards[o["cid"]].tapped = True
            t["target"] = s.ref(o["cid"])
            if o["key"].startswith("guard:"):      # 507.2b ガードマンで変更された場合、ブロッククリーチャーにはならない
                return None
            t["blocked"] = True
            rec = {"ev": "block", "subject": t["target"], "attacker": att, "controller": 1 - a}
            eng._push(eng.ev_task(rec), _decl(eng, a, "block", rec), _decl(eng, 1 - a, "block", rec))
        return None
    if ph == 3:                                               # 508 バトル
        t["phase"] = 4
        if t["target"] != "player":
            att, tgt, d = eng._battle_substitute(t, att, t["target"])
            if d:
                t["phase"] = 3
                return d
            eng._push(*eng._battle(att, tgt))
        return None
    if ph == 4:                                               # 509 ダイレクトアタック
        if t["target"] == "player" and eng.zlist("shield", 1 - a):
            # 509.2c 複数のブレイカー能力を持つなら、どの能力を使うかを選ぶ（どれも使わずに1つだけは選べない）
            counts = sorted(set(eng.chars(att[0])["break_opts"])) or [1]
            opts = [{"key": f"breaks:{n}"} for n in counts]
            ans, d = eng.ask(t, a, "choose_breaker", opts)
            if d:
                return d
            n = counts[ans[0]]
        t["phase"] = 5
        if t["target"] == "player":
            shields = eng.zlist("shield", 1 - a)
            if shields:
                eng._push({"t": "break", "victim": 1 - a, "by": a, "count": n, "phase": 0, "in_effect": False})
            else:
                s.result = {"winner": a, "reason": "direct_attack", "turn": s.turn}   # 509.1 / 703.4a
        return None
    eng._pop(t)
    eng._expire("during_attack")                             # 510.2
    return None


@task("break", BreakTask)
def h_break(eng, t):
    """ブレイク: 選ぶ → S・トリガー宣言 → 同時に手札へ → S・トリガーを解決（509.3〜509.5, 113.6）。
    効果でシールドを手札に加える時も、宣言→移動→S・トリガーの解決は同じ（113.6）。その場合は chosen を渡して
    phase 1 から始め、fire_break を偽にして「ブレイクした」イベントは起こさない。"""
    s = eng.s
    victim = t["victim"]
    shields = eng.zlist("shield", victim)
    if t["phase"] == 0:
        n = min(t["count"], len(shields))
        opts = [eng._card_option(c) for c in shields]
        ans, d = eng.ask(t, t["by"], "choose_shields", opts, n, n)
        if d:
            return d
        t["chosen"] = [shields[i] for i in ans]
        t["phase"] = 1
        return None
    opts = []
    for c in [x for ch in t["chosen"] for x in [ch] + list(s.cards[ch].under)]:   # シールドの束は、重なったカードのどれも宣言できる（113.2）
        d = eng.cdef(c)
        for fi in ([None] if not d.faces else range(len(d.faces))):
            if eng._permits_face(c, "s_trigger", fi):
                o = {"key": f"strigger:{s.cards[c].defn}" + ("" if fi is None else f":{fi}"), "cid": c}
                if fi is not None:
                    o["face"] = fi
                opts.append(o)
    declared = []
    if opts:
        ans, d = eng.ask(t, victim, "declare_strigger", opts, 0, len(opts))
        if d:
            return d
        seen = set()
        for i in ans:   # 1枚のカードで使えるのは1つの面だけ
            if opts[i]["cid"] not in seen:
                seen.add(opts[i]["cid"])
                declared.append([opts[i]["cid"], opts[i].get("face")])
    eng._pop(t)
    chosen = [c for c in t["chosen"] if s.cards[c].zone == "shield"]   # 宣言の間に別のゾーンへ移っていたら加えない
    seq = [eng.ev_task([{"ev": "move", "subject": s.ref(c), "to": "hand", "reason": t.get("reason", "break")}
                         for c in chosen]),
           {"t": "enqueue_st", "cids": declared, "player": victim}]
    if t.get("fire_break", True):
        seq.append(eng.ev_task({"ev": "break", "player": victim, "count": len(chosen)}))
    if t["in_effect"]:   # S・トリガーの解決中のブレイクは、新しい S・トリガーをその場で解決する（101.4g）
        seq = eng._window(*seq, only_st=True)
    eng._push(*seq)
    return None
