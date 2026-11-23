"""攻撃ステップ（505〜510）、バトル（701.13）、ブレイクとS・トリガー（509.5, 113.6）、使用宣言（506.3b〜）。

攻撃できるか・ブロックできるか・何枚ブレイクするかは、キーワード名ではなく特性の許可・禁止（permissions.yaml）と
breaks で判定する。キーワードは keywords.yaml でそれらを与える常在型能力として定義する。
"""
from __future__ import annotations

from ..base.types import AttackTask, BreakTask, DeclareTask, SlayerTask
from .registry import task


class CombatMixin:
    def _breaker(self, env) -> dict:
        """効果でブレイクする時の、ブレイクしたクリーチャー（効果の発生源がバトルゾーンのクリーチャーなら）。"""
        me = env.get("self")
        if me and self.s.alive(me) and self.s.cards[me[0]].zone == "bz" and "creature" in self.chars_ro(me[0])["types"]:
            return {"breaker": me}
        return {}

    def _can_attack(self, cid) -> bool:
        c = self.s.cards[cid]
        if c.tapped or "creature" not in self.chars_ro(cid)["types"]:
            return False
        return c.entered_turn != self.s.turn or self.permits(cid, "attack_summoning_sick")   # 506.1a

    def _attack_options(self, a):
        lim = self._action_limit(a, "attack")   # 攻撃回数の制限（第254弾）
        if lim is not None and self.s.turn_counters.get(f"atk_decl:{a}", 0) >= lim:
            return []
        out = []
        for cid in self.bz_tops(a):
            dfn = self.s.cards[cid].defn
            if not self._can_attack(cid):
                # アビスラッシュで出たターンだけ、召喚酔いでもプレイヤーへの攻撃はできる（クリーチャーは不可）
                if (self.s.turn_counters.get(f"rush:{cid}") == self.s.turn or self.chars_ro(cid).get("player_rush")) and not self.s.cards[cid].tapped \
                        and "creature" in self.chars_ro(cid)["types"] and self.permits(cid, "attack_player"):
                    out.append({"key": f"attack:{dfn}:player", "cid": cid, "target": "player"})
                continue
            player_opt = {"key": f"attack:{dfn}:player", "cid": cid, "target": "player"} \
                if self.permits(cid, "attack_player") else None
            allow = [e for e in self.chars_ro(cid)["allow"] if isinstance(e, dict) and e["action"] == "attack_creature"]
            creature_opts = []
            for tc in self.bz_tops(1 - a):
                # 505.2 既定ではタップ状態のクリーチャーだけ。「タップされていないクリーチャーを攻撃できる」(マッハファイター等)は allow で広げる
                if (self.s.cards[tc].tapped or any(e.get("other", {}).get("tapped") is False and self.filter_match(tc, e["other"]) and self._only_ok(e, tc) for e in allow)) \
                        and self.permits(cid, "attack_creature", tc) and self.permits(tc, "be_attacked", cid):
                    creature_opts.append({"key": f"attack:{dfn}:{self.s.cards[tc].defn}", "cid": cid,
                                          "target": self.s.ref(tc)})
            # 「可能ならこのクリーチャーを攻撃する」（第51弾）: 合法な攻撃先になる誘引持ちがいれば、攻撃先はそれらに限る
            # 「はじめて攻撃するなら」（第160弾）は、そのクリーチャーがこのターンまだ攻撃していなければ（履歴カウンタ hist:attack_by が 0）制限する
            _attacked = self.s.turn_counters.get(f"hist:attack_by:{cid}", 0)
            def _taunt(o):
                _tch = self.chars_ro(o["target"][0])
                return _tch["must_be_attacked"] or (_tch.get("must_be_attacked_first") and _attacked == 0)
            taunts = [o for o in creature_opts if _taunt(o)]
            # 「可能ならクリーチャーを攻撃する」（第171弾）: 攻撃できるクリーチャーがいればプレイヤーは攻撃できない。
            # first_only は第160弾と同じく攻撃側クリーチャー単位の初回攻撃だけ。特定の誘引（taunts）があればそちらが優先する
            _ch = self.chars_ro(cid)
            _mac = _ch["must_attack_creature"] or (_ch.get("must_attack_creature_first") and _attacked == 0)
            if taunts:
                out += taunts
            elif _mac and creature_opts:
                out += creature_opts
            else:
                if player_opt:
                    out.append(player_opt)
                out += creature_opts
        return out

    def _activate_options(self, a, attack_opts):
        """起動型能力（602）のうち攻撃ステップで使うもの。攻撃ができるときだけ使える（602.3a）。
        cost.tap が self ならこのクリーチャー、フィルタなら条件に合う自分のクリーチャー1体をタップする。
        cost.under（第53弾）はタップせず、下のカードを墓地に置いて使う（メテオバーン「攻撃できる時」形）。
        使った後も攻撃できるため、攻撃を強制されているクリーチャーでも使える。"""
        can = {o["cid"] for o in attack_opts}
        out = []
        for cid in self.bz_tops(a):
            for i, ab in self.abilities(cid, "activate"):
                env = {"you": a, "self": self.s.ref(cid), "vars": {}}
                if "if" in ab and not self.eval_cond(ab["if"], env):
                    continue
                dfn = self.s.cards[cid].defn
                cost = ab["cost"]
                if "under" in cost and len(self.s.cards[cid].under) < cost["under"]:
                    continue   # 下のカードが足りなければコストを払えない
                if "tap" not in cost:   # under のみ: タップしないので選択肢はクリーチャー自身に付く
                    # untap コスト（第171弾のリダイレクト）は攻撃ステップの起動では使わない
                    # （ブロック時の redirect 決定で使う）。tap も under も無い形はここでは出さない
                    if "under" not in cost:
                        continue
                    # 原文が「自分のクリーチャーが攻撃できる時」の形は any_attacker: true（保持者自身でなくてもよい）
                    if cid in can or (ab.get("any_attacker") and can):
                        out.append({"key": f"activate:{dfn}:{i}", "cid": cid, "ab": i,
                                    "under_cost": cost["under"]})
                    continue
                if isinstance(cost["tap"], dict) and "ref" in cost["tap"]:   # {ref: crossed}（第170弾）: このギアをクロスしているクリーチャーをタップする（dm15-014 型）
                    g = self.s.cards[cid].crossed
                    who = [g[0]] if g and self.s.alive(g) and g[0] in self.bz_tops(a) else []
                else:
                    who = [cid] if cost["tap"] == "self" else \
                        [x for x in self.bz_tops(a) if self.filter_match(x, cost["tap"])]
                for x in who:
                    if x in can:
                        key = f"activate:{dfn}:{i}" + ("" if x == cid else f":{self.s.cards[x].defn}")
                        o = {"key": key, "cid": cid, "ab": i, "tap": x}
                        n = cost.get("tap_mana")
                        if n:   # 複合コスト: タップされていないマナが足りる時だけ使える
                            if sum(1 for m in self.zlist("mana", a) if not self.s.cards[m].tapped) < n:
                                continue
                            o["tap_mana"] = n
                        if "under" in cost:
                            o["under_cost"] = cost["under"]
                        out.append(o)
        return out

    def _redirect_options(self, t):
        """攻撃先の変更（第171弾）: 防御側の起動型能力のうち、アンタップをコストに攻撃先を
        変更するもの（activate + cost.untap + redirect）。選択肢は（能力を持つクリーチャー、
        コストでアンタップするクリーチャー、新しい攻撃先）の組。新しい攻撃先は、コストの
        クリーチャー（redirect が true か include_cost が真の時）と自分のタップしている
        クリーチャー。能力の if（「自分のクリーチャーの数が相手より多ければ」等）も見る。
        攻撃の使用宣言の後・ブロックの前に諮る（h_attack ph 2）。"""
        d = 1 - self.s.active
        out = []
        for cid in self.bz_tops(d):
            for i, ab in self.abilities(cid, "activate"):
                if "redirect" not in ab or "untap" not in ab.get("cost", {}):
                    continue
                env = {"you": d, "self": self.s.ref(cid), "vars": {}}
                if "if" in ab and not self.eval_cond(ab["if"], env):
                    continue
                cost = ab["cost"]
                if cost["untap"] == "self":
                    payers = [cid] if self.s.cards[cid].tapped else []
                else:
                    payers = [x for x in self.bz_tops(d)
                              if self.s.cards[x].tapped and self.filter_match(x, cost["untap"])]
                include_cost = ab["redirect"] is True or ab["redirect"].get("include_cost", True)
                for p in payers:
                    targets = [p] if include_cost else []
                    targets += [x for x in self.bz_tops(d)
                                if x != p and self.s.cards[x].tapped]
                    for tgt in targets:
                        out.append({"key": f"redirect:{self.s.cards[cid].defn}:{i}:{self.s.cards[p].defn}:{self.s.cards[tgt].defn}",
                                    "cid": cid, "ab": i, "payer": p, "target": self.s.ref(tgt)})
        return out

    def _battle_substitute(self, t, att, tgt):
        """バトル相手の置換（「かわりにこのクリーチャーにバトルさせてもよい」）。ターン・プレイヤー側から順に選ぶ（609.8）。
        置換効果 when: {event: battle, subject: <置き換えられる側>}、instead: [{op: battle_substitute}] を持つ
        バトルゾーンのクリーチャーが、その側の代わりにバトルする。1回のバトルで同じ側は1度だけ。
        instead の battle_substitute に tap: true があれば、代わりにバトルするクリーチャーをタップする
        （スーパーガードマン。第186弾。タップ済みのクリーチャーは選択肢に出ない。タップにイベントは出さない）。
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
                        tap = any(o.get("op") == "battle_substitute" and o.get("tap") is True
                                  for o in ab.get("instead", []))
                        if tap and s.cards[src].tapped:
                            continue   # タップしてバトルさせる置換は、タップ済みでは使えない
                        opts.append({"key": f"battle_sub:{s.cards[src].defn}:{i}", "cid": src, "tap": tap})
            if not opts:
                continue
            a, d = self.ask(t, ctrl, "choose_replacement", opts + [{"key": "decline"}])
            if d:
                return att, tgt, d
            sides.append(k)
            if a[0] < len(opts):
                o = opts[a[0]]
                new = s.ref(o["cid"])
                if o["tap"]:
                    s.cards[o["cid"]].tapped = True
                if k == 0:
                    att = new
                else:
                    tgt = new
                t["attacker"], t["target"] = att, tgt
                break
        return att, tgt, None

    def _battle_bonus(self, ref, attacking: bool = False, opponent=None) -> int:
        """バトル中だけのパワー修整（mod battle_power。ハンティング: 自分のハンター1体につき+1000）。only: attacking は攻撃側のときだけ。
        opponent_filter（第122弾）: バトルの相手がフィルタに合う時だけ。「攻撃中」「ブロック中」のパワー修整は mod power_when（バトルをしていない間も含む）。
        条件つき常在型の if（第167弾）: chars の集約と同じく _static_cond で見る。見ないと「相手のターン、バトル中+4000」（dmr09-031）等が常に効いてしまう。"""
        cid = ref[0]
        env = {"you": self.s.cards[cid].controller, "self": ref}
        total = 0
        # 得た常在型（第244弾）: affects 無し／self／{ref: self} は持ち主自身の能力として扱う
        statics = [(ab, False) for _, ab in self.abilities(cid, "static")] + \
                  [(gab, True) for gab in self._gained_statics(cid)]
        for ab, gained in statics:
            bp = ab.get("mod", {}).get("battle_power")
            if bp and "if" in ab and not self._static_cond(ab["if"], env):
                continue
            if bp and bp.get("only") == "attacking" and not attacking:
                continue
            if bp and "opponent_filter" in bp and (opponent is None or not self.filter_match(opponent[0], bp["opponent_filter"])):
                continue
            ga = ab.get("affects")
            is_self = (ga is None or ga == "self" or ga == {"ref": "self"}) if gained else ga == "self"
            if bp and is_self and ab.get("zone", "bz") == self.s.cards[cid].zone:
                total += bp["amount"] * (self.count_of(bp["count"], env) if "count" in bp else 1)
        # 他のカードからの付与（第342弾）: chars の集約と同じく、バトルゾーンと
        # シールドゾーンの発生源から affects が合う常在型の battle_power を集める。
        # これまで _battle_bonus は本人の常在型しか見ておらず、affects 辞書形の
        # 付与（例: dm21-031 の「自分のティラノ・ドレイクはバトル中+4000」）は
        # 一切効いていなかった。{ref: self} 形も _subject_match で本人だけに合う。
        cards = self.s.cards
        grant_srcs = [(src, ab) for src in self.s.zones["bz"][0]
                      if cards[src].top_of < 0 and self._affects_others(src)
                      for _, ab in self.abilities(src, "static")
                      if ab.get("zone", "bz") == "bz"]
        grant_srcs += [(src, ab) for p in (0, 1) for src in self.s.zones["shield"][p]
                       if self._affects_others(src)
                       for _, ab in self.abilities(src, "static")
                       if ab.get("zone") == "shield"]
        for src, ab in grant_srcs:
            bp = (ab.get("mod") or {}).get("battle_power")
            if not bp:
                continue
            aff = ab.get("affects", {})
            if not isinstance(aff, dict) or aff == "self":
                continue
            if (aff.get("zone", "bz") if isinstance(aff, dict) else "bz") != cards[cid].zone:
                continue
            env_src = {"you": cards[src].controller, "self": self.s.ref(src)}
            if "if" in ab and not self._static_cond(ab["if"], env_src):
                continue
            if not self._subject_match(aff, cid, env_src, None, base=True):
                continue
            if bp.get("only") == "attacking" and not attacking:
                continue
            if "opponent_filter" in bp and (opponent is None or not self.filter_match(opponent[0], bp["opponent_filter"])):
                continue
            total += bp["amount"] * (self.count_of(bp["count"], env_src) if "count" in bp else 1)
        return total

    def _battle_indestructible(self, ref, opponent) -> bool:
        """バトルで破壊されないか。無条件（第59弾）と、相手フィルタつき（第122弾）の両方を見る。"""
        ch = self.chars(ref[0])
        if ch["battle_indestructible"] or ch.get("indestructible"):
            return True
        return any(self.filter_match(opponent[0], f) for f in ch.get("battle_indestructible_filters", []))

    def _battle(self, x, y):
        """バトル（701.13）。結果で誘発した効果はその場で解決してからバトルを終える。"""
        px = self.chars_ro(x[0])["power"] + self._battle_bonus(x, attacking=True, opponent=y)      # x は攻撃側
        py = self.chars_ro(y[0])["power"] + self._battle_bonus(y, opponent=x)
        # 第61弾: すべてのバトルに勝つクリーチャーはパワーに関わらず勝つ
        x_wins = self.chars_ro(x[0])["win_all_battles"]
        y_wins = self.chars_ro(y[0])["win_all_battles"]
        if x_wins and y_wins:
            losers_by_power = []   # 両方勝つ場合は相打ちなし
        elif x_wins:
            losers_by_power = [y]
        elif y_wins:
            losers_by_power = [x]
        else:
            losers_by_power = ([x] if px <= py else []) + ([y] if py <= px else [])
        # 第59弾: バトル中破壊されないクリーチャーは破壊されない（勝敗判定はパワーどおり）
        losers = [r for r in losers_by_power if not self._battle_indestructible(r, y if r == x else x)]
        winners = [r for r in (x, y) if r not in losers_by_power]
        slay = [[r, y if r == x else x] for r in losers if self.permits(r[0], "slayer")]
        # 「バトルに負けた時」: パワーで負けた側（破壊されない場合も負けは負け。相打ちは両方）。相手は event.opponent。
        # 破壊の移動より前に置き、負けて破壊されるクリーチャー自身の能力も誘発する（場にいる間に起きた出来事として拾う）
        lose_evs = [{"ev": "battle_lose", "subject": r, "opponent": y if r == x else x, "controller": self.s.cards[r[0]].controller} for r in losers_by_power]
        evs = [{"ev": "move", "subject": r, "to": "graveyard", "reason": "destroy", "battle": True} for r in losers]
        evs += [{"ev": "battle_win", "subject": r, "opponent": y if r == x else x, "controller": self.s.cards[r[0]].controller} for r in winners]
        # 負けの誘発は破壊の前（場にいる間）に拾い、解決は同じ窓の終わり＝破壊の後（603.3: 誘発は次に解決できる時まで待機）
        out = self._window(*([self.ev_task(lose_evs)] if lose_evs else []), self.ev_task(evs))
        if slay:   # 701.13d バトルの後に誘発する「スレイヤー」
            out += self._window({"t": "slayer", "pairs": slay})
        # 「バトルの後」（バンドB U7）: 両参加者を subject とする合成レコードを末尾に出す。
        # 既に場を離れた参加者の誘発は発生源が場に無いため拾われない（対象文面の範囲では足りるという設計の範囲）
        out.append(self.ev_task([
            {"ev": "battle_end", "subject": x, "opponent": y, "controller": self.s.cards[x[0]].controller},
            {"ev": "battle_end", "subject": y, "opponent": x, "controller": self.s.cards[y[0]].controller}]))
        return out

    def _declarable(self, player, rec) -> list[dict]:
        """使用宣言できる能力（603.2e/f）。手札（または ab.zone）にあり、when が rec に合い、if を満たすもの。
        第183弾: S級侵略のため bz も走査する。bz は共有ゾーンなので controller で絞り、
        下のカード（top_of >= 0）は宣言できない。攻撃中のクリーチャー自身は自分の上に重ねられない
        （「自分以外のクリーチャーが攻撃する時」）ので、イベントの subject は除外する。"""
        s = self.s
        out = []
        subj = rec.get("subject")
        subj_cid = subj[0] if isinstance(subj, (list, tuple)) else None
        for z in ("hand", "mana", "graveyard", "bz"):
            for cid in self.zlist(z, player):
                if z == "bz":
                    if s.cards[cid].controller != player:
                        continue
                    if s.cards[cid].top_of >= 0:
                        continue
                    if subj_cid is not None and cid == subj_cid:
                        continue
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
                        if ab.get("group") and s.turn_counters.get(f"declgrp:{ab['group']}:{player}") == s.turn_counters.get("current_attack"):
                            continue   # この攻撃ではもう同じグループの宣言を使った（第262弾）
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
    seen_groups = set()   # 第262弾: 同じ group の宣言は1回の宣言窓でも1つまで（残りは宣言しなかったことにする）
    kept = []
    for i in ans:
        o = opts[i]
        grp = eng.cdef(o["cid"]).face(o.get("face")).abilities[o["ab"]].get("group")
        if grp:
            if grp in seen_groups:
                continue
            seen_groups.add(grp)
        kept.append(i)
    ans = kept
    eng._pop(t)
    win = s.windows[-1] if s.windows else 0
    for i in ans:
        o = opts[i]
        fd = eng.cdef(o["cid"]).face(o.get("face"))
        if fd.abilities[o["ab"]].get("group"):
            s.turn_counters[f"declgrp:{fd.abilities[o['ab']]['group']}:{t['player']}"] = s.turn_counters.get("current_attack")   # 第262弾: この攻撃では同じグループを再宣言できない
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
    if t.get("cancelled"):                                    # 攻撃の中止（第251弾）: バトルもブレイクもしない
        if not t.get("end_fired") and not s.result:
            t["end_fired"] = True
            broke = s.turn_counters.get(f"broke_in:{att[0]}") == t.get("ano")
            eng._push(eng.ev_task({"ev": "attack_end", "subject": att, "target": t["target"],
                                   "controller": a, "broke": broke, "blocked": bool(t.get("blocked"))}))
            return None
        eng._pop(t)
        eng._expire("during_attack")
        return None
    if ph == 0:                                               # 506 攻撃クリーチャー指定
        t["phase"] = 1
        s.turn_counters[f"atk_decl:{a}"] = s.turn_counters.get(f"atk_decl:{a}", 0) + 1   # 攻撃回数の制限用（第254弾）
        s.turn_counters["attack_no"] = s.turn_counters.get("attack_no", 0) + 1
        t["ano"] = s.turn_counters["attack_no"]
        s.turn_counters["current_attack"] = t["ano"]
        rec = {"ev": "attack", "subject": att, "target": t["target"], "controller": a}
        eng._push(eng.ev_task(rec), _decl(eng, a, "attack", rec))
        # 第190弾: 攻撃宣言のタップは tap イベントを出す（「タップした時」誘発用）。
        # _apply_one の tap 処理が tapped=True にする。既にタップ済みなら記録は出ない
        if not s.cards[att[0]].tapped:
            eng._push(eng.ev_task({"ev": "tap", "subject": att}))
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
        if not t.get("redirect_done"):   # 攻撃先の変更（第171弾）: ブロックの前に、防御側の起動型能力で攻撃先を変えられる。断ればブロックへ進む
            opts = eng._redirect_options(t)
            if opts:
                ans, d = eng.ask(t, 1 - a, "redirect", opts + [{"key": "decline"}])
                if d:
                    return d
                if ans[0] < len(opts):
                    o = opts[ans[0]]
                    s.cards[o["payer"]].tapped = False   # コスト: アンタップする（タップのコストと同じくイベントは出さない）
                    t["target"] = o["target"]
                    return None   # もう一度諮る（別のクリーチャーの変更も使える）
            t["redirect_done"] = True
        blockers = [c for c in eng.bz_tops(1 - a)
                    if not s.cards[c].tapped and eng.permits(c, "block", att[0])
                    and "creature" in eng.chars_ro(c)["types"]   # 507.1: ブロックできるのはクリーチャーだけ（第179弾: 条件を満たさないACEタマシード等を除外）
                    and eng.permits(att[0], "be_blocked", c) and [c, s.cards[c].gen] != t["target"]]
        guards = [] if t["target"] == "player" else [          # 507.1a ガードマン: 攻撃されている自分の他のクリーチャーがいる時だけ
            c for c in eng.bz_tops(1 - a) if not s.cards[c].tapped and [c, s.cards[c].gen] != t["target"]
            and eng.permits(c, "guardman", att[0])]
        blim = eng._action_limit(1 - a, "block")   # ブロック回数の制限（第254弾）
        if blim is not None and s.turn_counters.get(f"blk_decl:{1 - a}", 0) >= blim:
            blockers, guards = [], []
        forced = [c for c in blockers if "block" in eng.chars_ro(c)["require"]]   # 507.1b ブロックを強制されたクリーチャーは必ず選ぶ
        opts = [eng._card_option(c) for c in blockers] + \
               [eng._card_option(c, key=f"guard:{s.cards[c].defn}") for c in guards] + ([] if forced else [{"key": "no_block"}])
        ans, d = eng.ask(t, 1 - a, "block", opts)
        if d:
            return d
        t["phase"] = 3
        o = opts[ans[0]]
        if o["key"] != "no_block":
            # 第190弾: ブロック宣言のタップも tap イベントを出す（「タップした時」誘発用）。
            # ガードマン（ブロックにならない）でもタップは起きる。後から積むほど先に実行される
            # ため、tap イベントは block イベントより後に積んで先に実行させる
            to_tap = [c for c in list(forced) + [o["cid"]] if not s.cards[c].tapped]
            t["target"] = s.ref(o["cid"])
            if o["key"].startswith("guard:"):      # 507.2b ガードマンで変更された場合、ブロッククリーチャーにはならない
                for c in to_tap:
                    eng._push(eng.ev_task({"ev": "tap", "subject": s.ref(c)}))
                return None
            t["blocked"] = True
            s.turn_counters[f"blk_decl:{1 - a}"] = s.turn_counters.get(f"blk_decl:{1 - a}", 0) + 1   # ブロック回数の制限用（第254弾）
            rec = {"ev": "block", "subject": t["target"], "attacker": att, "controller": 1 - a}
            eng._push(eng.ev_task(rec), _decl(eng, a, "block", rec), _decl(eng, 1 - a, "block", rec))
            for c in to_tap:
                eng._push(eng.ev_task({"ev": "tap", "subject": s.ref(c)}))
        return None
    if ph == 3:                                               # 508 バトル
        t["phase"] = 4
        if t["target"] != "player":
            att, tgt, d = eng._battle_substitute(t, att, t["target"])
            if d:
                t["phase"] = 3
                return d
            eng._push(*eng._window(eng.ev_task({"ev": "battle_start", "subject": att, "opponent": tgt, "controller": a})),
                      {"t": "battle_run", "att": att, "tgt": tgt})
        return None
    if ph == 4:                                               # 509 ダイレクトアタック
        if t["target"] == "player" and not t.get("blocked") and not t.get("through_fired"):
            # ブロックされなかった時（第229弾バイオ・K）: ブレイクの前に発火する
            # （W・ブレイカーの付与などがこの攻撃のブレイクに間に合うタイミング）
            t["through_fired"] = True
            eng._push(eng.ev_task({"ev": "attack_unblocked", "subject": att, "target": "player",
                                   "controller": a}))
            return None
        if t["target"] == "player" and eng.zlist("shield", 1 - a):
            # 509.2c 複数のブレイカー能力を持つなら、どの能力を使うかを選ぶ（どれも使わずに1つだけは選べない）
            counts = sorted(set(eng.chars_ro(att[0])["break_opts"])) or [1]
            if "g_breaker" in eng.chars_ro(att[0])["keywords"]:
                counts = counts + ["all"]   # G・ブレイカー（第252弾）: すべてブレイクする能力も選択肢に加える
            if "infinite_breaker" in eng.chars_ro(att[0])["keywords"]:
                # ∞ブレイカー（第272弾）: 好きな数ブレイクする。0〜残シールド数のすべてを選択肢にする
                counts = list(range(0, len(eng.zlist("shield", 1 - a)) + 1))
            opts = [{"key": f"breaks:{n}"} for n in counts]
            ans, d = eng.ask(t, a, "choose_breaker", opts)
            if d:
                return d
            n = counts[ans[0]]
            if n == "all":
                t["g_break"] = True
                n = len(eng.zlist("shield", 1 - a))
        t["phase"] = 5
        if t["target"] == "player":
            shields = eng.zlist("shield", 1 - a)
            if shields:
                if n > 0:   # ヌル・ブレイカー（0ブレイク）ではブレイク自体が起こらない（第129弾）
                    if t.get("g_break"):
                        # G・ブレイカー: その攻撃の後、自分のシールドもすべてブレイクする。
                        # 先に積んだタスクが後に実行されるので、自分のブレイクを先に積む
                        eng._push({"t": "break", "victim": a, "by": a, "count": 1 << 30, "phase": 0, "in_effect": False, "breaker": att})
                    eng._push({"t": "break", "victim": 1 - a, "by": a, "count": n, "phase": 0, "in_effect": False, "breaker": att})
            else:
                eng._push(*eng.game_lose(1 - a, "direct_attack"))   # 509.1 / 703.4a（敗北の置換を諮ってから確定する）
        return None
    if not t.get("end_fired") and not s.result:               # 510 攻撃の終わり（キリフダッシュ等の誘発点）
        t["end_fired"] = True
        broke = s.turn_counters.get(f"broke_in:{att[0]}") == t.get("ano")
        eng._push(eng.ev_task({"ev": "attack_end", "subject": att, "target": t["target"],
                               "controller": a, "broke": broke, "blocked": bool(t.get("blocked"))}))
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
    if t["phase"] == 1:
        if t.get("fire_break", True) and not t.get("brk_done"):
            r = eng._break_consult(t)   # ブレイクの置換の諮問（第146弾。chosen 確定後・宣言の前。擬似ブレイクは対象外）
            if r is not True:
                return r
        opts = []
        for c in [x for ch in t["chosen"] for x in [ch] + list(s.cards[ch].under)]:   # シールドの束は、重なったカードのどれも宣言できる（113.2）
            d = eng.cdef(c)
            for fi in ([None] if not d.faces else range(len(d.faces))):
                ok = eng._permits_face(c, "s_trigger", fi)
                card = s.cards[c]
                if t.get("strigger") == "off" or card.strigger_off:
                    ok = False   # S・トリガーの印（使用不可）: この移動で手札に加わるカード／印つきのカードは宣言できない（バンドC2 U68）
                elif t.get("strigger") == "on" or card.strigger_on:
                    fd = d.face(fi)
                    ok = ok or fd.is_creature() or "spell" in fd.types   # S・トリガーの印（付与）: 実行可能な種別の面なら宣言できる
                if ok:
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
        t["declared"] = declared
        t["phase"] = 2
        return None
    declared = t["declared"]
    sback = []
    # S・バック: S・トリガーの宣言と同じ機会に、手札のカードの S・バックを宣言する（112.3b）
    used = {c for c, _ in declared}
    pool = [x for ch in t["chosen"] for x in [ch] + list(s.cards[ch].under) if x not in used]
    sopts = []
    for h in eng.zlist("hand", victim):
        hd = eng.cdef(h)
        if hd.s_back and eng.permits(h, "summon" if hd.is_creature() else "cast"):
            # 対象指定: 文明名（文字列）はその文明のカード、filter（辞書）はその条件に合うカード（第52弾）
            sopts += [{"key": f"sback:{s.cards[h].defn}:{s.cards[x].defn}", "cid": h, "shield": x}
                      for x in pool if (hd.s_back in eng.cdef(x).civs if isinstance(hd.s_back, str)
                                        else eng.filter_match(x, hd.s_back))]
    if sopts:
        ans, d = eng.ask(t, victim, "declare_sback", sopts, 0, len(sopts))
        if d:
            return d
        su, sh = set(), set()
        for i in ans:       # 1枚のカードの S・バックは1回、捨てるカードも1枚につき1回
            if sopts[i]["cid"] not in su and sopts[i]["shield"] not in sh:
                su.add(sopts[i]["cid"])
                sh.add(sopts[i]["shield"])
                sback.append((sopts[i]["cid"], sopts[i]["shield"]))
    eng._pop(t)
    chosen = [c for c in t["chosen"] if s.cards[c].zone == "shield"]   # 宣言の間に別のゾーンへ移っていたら加えない
    seq = []
    if t.get("fire_break", True) and t.get("breaker") and s.alive(t["breaker"]) and chosen:
        # 「各ブレイクの前に」（第239弾）: ブレイクするクリーチャー自身の誘発を、シールド1枚につき
        # 1回ずつ、ブレイクの移動より先に起こす。置換でブレイク自体が無くなった場合は phase 1 で戻っている
        seq.append(eng.ev_task([{"ev": "break_before", "subject": t["breaker"], "player": victim,
                                 "controller": t["by"], "shield": s.ref(c)} for c in chosen]))   # shield: 割られるシールドそのもの（第248弾: ブレイク差し替え系が event.shield で参照する）
    seq.append(eng.ev_task([{"ev": "move", "subject": s.ref(c), "to": "hand", "reason": t.get("reason", "break"),
                         **({"strigger": t["strigger"]} if t.get("strigger") else {})}
                         for c in chosen]))
    if sback:       # 手札に加わったカードを捨てる → そうした場合だけ、コストを支払わずに実行する
        seq.append({"t": "sback", "pairs": [[h, x] for h, x in sback], "player": victim})
    seq.append({"t": "enqueue_st", "cids": declared, "player": victim, "strigger": True})
    if t.get("fire_break", True) and chosen:   # 実際にブレイクされるシールドが無いならブレイク自体が起こらなかった（QA 33466。第146弾）
        ev = {"ev": "break", "player": victim, "count": len(chosen)}
        if t.get("breaker") and s.alive(t["breaker"]):      # ブレイクしたクリーチャー（「他のクリーチャーがシールドをブレイクした」）
            ev["subject"] = t["breaker"]
            s.turn_counters[f"broke_in:{t['breaker'][0]}"] = s.turn_counters.get("current_attack", 0)
            # 第185弾: その攻撃中にそのクリーチャーがブレイクした枚数（ブレイク・ボーナスの読み先。攻撃番号で区切る）
            k = f"broke_count:{t['breaker'][0]}:atk{s.turn_counters.get('current_attack', 0)}"
            s.turn_counters[k] = s.turn_counters.get(k, 0) + len(chosen)
        seq.append(eng.ev_task(ev))
    if t["in_effect"]:   # S・トリガーの解決中のブレイクは、新しい S・トリガーをその場で解決する（101.4g）
        seq = eng._window(*seq, only_st=True)
    eng._push(*seq)
    return None
