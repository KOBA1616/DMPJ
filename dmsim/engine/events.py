"""イベント・パイプライン（置換→同時適用→状況起因処理→誘発）と待機・解決窓。"""
from __future__ import annotations

from ..base.types import CaptureTask, CloseWinTask, BattleRunTask, DoubleAskTask, EnqueueStTask, EventTask, GLinkTask, LoseReplaceTask, OpenWinTask, ResolvePendingTask, SbackTask, SealReleaseTask, SmaxReduceTask
from .registry import task


class EventMixin:
    def ev_task(self, evs, env: dict | None = None) -> dict:
        """同時に起こるイベントの束（400.7, 609.9）。"""
        if isinstance(evs, dict):
            evs = [evs]
        if env and isinstance(env.get("you"), int):   # 効果の解決者が起こす移動には、起こしたプレイヤーを記録する（「相手の効果によって捨てられる時」等の照合用）
            evs = [dict(e, by=env["you"]) if e.get("ev") == "move" and "by" not in e else e for e in evs]
            if env.get("self"):   # 効果帰属レコード（基盤B1）: その移動を起こした効果の発生源（defn 名と、呪文か能力かの種別）を常時記録する
                src = env["self"][0]
                cause = self.s.cards[src].defn
                ckind = "spell" if "spell" in self.fdef(src).types else "ability"
                evs = [dict(e, cause=cause, cause_defn=cause, cause_kind=ckind)
                       if e.get("ev") == "move" and "cause_defn" not in e else e for e in evs]
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
        srcs = list(self.bz_tops(p))
        subj = ev.get("subject")
        if subj and self.s.alive(subj) and self.s.cards[subj[0]].controller == p and subj[0] not in srcs:
            srcs.append(subj[0])   # 動くカード自身の置換（シールドゾーンの G・城など）
        for x in self.s.zones["shield"][p]:
            if x not in srcs:
                srcs.append(x)
        for src in srcs:
            for i, ab in self.abilities(src, "replace"):
                if self.s.cards[src].zone != "bz" and ab.get("zone") != self.s.cards[src].zone:
                    continue   # バトルゾーン外の発生源は、そのゾーンを宣言した置換だけ
                if self._pattern_match(ab["when"], rec, src, None):
                    if "if" in ab:   # 置換効果にも条件を書ける（《水上第九院 シャコガイル》の最後の1枚判定）
                        env = {"you": self.s.cards[src].controller, "self": self.s.ref(src),
                               "event": rec, "vars": {}}
                        if not self.eval_cond(ab["if"], env):
                            continue
                    if ab.get("once_per_turn"):   # 「各ターンに一度」の置換（第196弾。誘発側は
                        # events の誘発収集で見るが、置換側はここで見る。印は選ばれた時に付ける）
                        r = self.s.ref(src)
                        if self.s.turn_counters.get(f"once:replace:{r[0]}:{r[1]}:{i}"):
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
                if ab.get("once_per_turn"):
                    r = self.s.ref(src)
                    self.s.turn_counters[f"once:replace:{r[0]}:{r[1]}:{i}"] = 1
                return self._child(ab["instead"], env)
        return None

    def _break_candidates(self, rec, p):
        """プレイヤー p がブレイク（rec）に対して使える置換効果（kind: replace, when.event == break）の候補。

        発生源の走査は _replacement と同じ規則: そのプレイヤーの bz_tops とシールドゾーンのカードで、
        バトルゾーン外の発生源は能力の zone 宣言が実ゾーンと一致するものだけ。シールドゾーンの
        発生源は表向きのものだけ（裏向きのシールドに能力はない）。"""
        s = self.s
        cands = []
        srcs = list(self.bz_tops(p))
        for x in s.zones["shield"][p]:
            if x not in srcs:
                srcs.append(x)
        top = rec["shield"][0]
        bundle = [s.ref(top)] + [s.ref(u) for u in s.cards[top].under]
        for src in srcs:
            c = s.cards[src]
            for i, ab in self.abilities(src, "replace"):
                if ab.get("when", {}).get("event") != "break":
                    continue
                if c.zone != "bz" and ab.get("zone") != c.zone:
                    continue   # バトルゾーン外の発生源は、そのゾーンを宣言した置換だけ
                if c.zone == "shield" and not c.face_up:
                    continue   # 裏向きのシールドに能力はない
                if self._pattern_match(ab["when"], rec, src, None):
                    if "if" in ab:
                        env = {"you": c.controller, "self": s.ref(src), "event": rec,
                               "vars": {"shield": bundle}}
                        if not self.eval_cond(ab["if"], env):
                            continue
                    cands.append((src, i, ab))
        return cands

    def _break_consult(self, t):
        """ブレイクの置換の諮問（第146弾。公式FAQどおり自己置換効果として扱う）。

        h_break の phase 0（chosen 確定後）から phase 1（S・トリガー宣言）の間に、シールド1つずつ
        置換を諮る。諮問順はターン・プレイヤー→非ターン・プレイヤー（609.9a）。1つのシールドに
        適用できる置換は1つだけ（適用済みのシールドは再諮問しない＝自己置換は連鎖しない。
        FAQ qa_old/36516 と整合）。
        戻り値: True（諮問が終わった）/ None（instead を push したので続きは再入時）/ Decision。
        置換されたシールドは「ブレイクされた」ことにならない（QA 33466）ため、諮問の終わりに
        chosen から取り消しの印（brk_cancelled）とゾーンを離れたものを除き、S・トリガー宣言・
        S・バック・最終 move のすべてから外す。この「ブレイクされたことにならない」扱いは
        「ブレイクする時、かわりに」型でも「手札に加えるかわりに」型でも同じとする
        【裁定待ち: 設計ノート pilot146 §5-1。裁定が逆になれば、取り消しの印の付け方
        （brk_cancelled への追加）と combat.py 側の break レコード抑制をここで切り替える】。
        continue: true の置換（割り込み型。ガイアール・ベイビー）は instead の後もブレイクが続く
        ので、取り消しの印を付けず chosen に残す【裁定待ち: 設計ノート pilot146 §5-2 の
        ミラクルスターの扱いは、この印の付け方（continue の有無）だけで両案に対応する】。"""
        s = self.s
        victim = t["victim"]
        if "brk_list" not in t:
            t["brk_list"] = list(t["chosen"])
            t["brk_i"] = 0
            t["brk_p"] = 0
            t["brk_cancelled"] = []
        if "brk_waiting" in t:   # instead の解決が終わって戻ってきた
            cid, cont = t.pop("brk_waiting")
            if not cont:
                t["brk_cancelled"].append(cid)
            t["brk_i"] += 1
            t["brk_p"] = 0
        order = (s.active, 1 - s.active)
        while t["brk_i"] < len(t["brk_list"]):
            cid = t["brk_list"][t["brk_i"]]
            if s.cards[cid].zone != "shield":   # 諮問の途中で別の効果で離れたシールドは諮らない
                t["brk_i"] += 1
                t["brk_p"] = 0
                continue
            rec = {"ev": "break", "player": victim, "shield": s.ref(cid), "controller": t["by"]}
            if t.get("breaker") and s.alive(t["breaker"]):
                rec["subject"] = t["breaker"]
            while t["brk_p"] < 2:
                p = order[t["brk_p"]]
                cands = self._break_candidates(rec, p)
                if not cands:
                    t["brk_p"] += 1
                    continue
                opts = [{"key": f"replace:{s.cards[s_].defn}:{i}", "cid": s_, "ab": i} for s_, i, _ in cands]
                if all(ab.get("optional") for _, _, ab in cands):
                    opts.append({"key": "decline"})
                a, d = self.ask(t, p, "choose_replacement", opts)
                if d:
                    return d
                o = opts[a[0]]
                if o["key"] == "decline":
                    t["brk_p"] += 1
                    continue
                src, i = o["cid"], o["ab"]
                ab = next(a_ for s_, i_, a_ in cands if (s_, i_) == (src, i))
                bundle = [s.ref(cid)] + [s.ref(u) for u in s.cards[cid].under]
                env = {"you": s.cards[src].controller, "self": s.ref(src), "event": rec,
                       "vars": {"shield": bundle}, "no_replace": True}
                t["brk_waiting"] = [cid, bool(ab.get("continue"))]
                self._push(self._child(ab["instead"], env))
                return None
            t["brk_i"] += 1
            t["brk_p"] = 0
        cancelled = set(t["brk_cancelled"])
        t["chosen"] = [c for c in t["chosen"] if c not in cancelled and s.cards[c].zone == "shield"]
        t["brk_done"] = True
        return True

    def _record_for(self, ev):
        """適用前のイベントを、誘発・置換の照合用レコードにする。"""
        s = self.s
        if ev["ev"] == "move":
            if not s.alive(ev["subject"]):
                return None
            c = s.cards[ev["subject"][0]]
            rec = {"ev": "move", "subject": ev["subject"], "from": ev.get("from") if c.zone == "hold" else c.zone,
                   "to": ev["to"], "reason": ev["reason"], "controller": c.controller,
                   "position": ev.get("position", "top")}   # 置かれた位置（「山札の一番下に置かれた時」の照合用。第290弾。収集レコード側と対）
            if ev.get("cause"):
                rec["cause"] = ev["cause"]
            if ev.get("cause_defn"):   # 効果帰属（基盤B1）: 発生源の defn 名と種別（呪文／能力）
                rec["cause_defn"] = ev["cause_defn"]
                rec["cause_kind"] = ev["cause_kind"]
            if "by" in ev:        # その移動を起こした効果の解決者（無ければ記録しない: 状況起因・コスト等は「相手の効果」扱いにしない）
                rec["by"] = ev["by"]
            if ev.get("stack_on"):   # 進化として重ねて出た（シンカパワーの照合用）
                rec["stacked"] = True
            if ev.get("battle"):   # バトルで負けて破壊された（第332弾。収集レコードと対）
                rec["battle"] = True
            if ev.get("no_trigger"):   # この移動で出たカード自身の出た時能力は誘発しない（第213弾）
                rec["no_trigger"] = True
            if ev.get("alt"):        # 代替コストで実行された（「そうしたら」の照合用）
                rec["alt"] = True
            if ev.get("vivid"):      # ビビッドローで実行された（第54弾。「ビビッドローを使って召喚した時」の照合用）
                rec["vivid"] = True
            if ev.get("unpaid"):     # コストを支払わずに出た（「コストを支払わずに召喚した時」等の照合用）
                rec["unpaid"] = True
            elif ev["to"] == "bz" and ev.get("reason") != "summon" and rec["from"] != "bz":
                rec["unpaid"] = True   # 第257弾: 効果で出されたカードはマナをタップせずに出ている（「マナゾーンのカードをタップせずに出た時」の照合用）
            if c.zone == "bz" and c.top_of >= 0 and c.seal_of < 0:
                # 下にあったカードが単独で動く: 宿主（上にいたカード）の移動直前の姿を載せる（from_under 照合用）
                h = s.cards[c.top_of]
                href = s.ref(c.top_of)
                rec["host"] = href
                rec["host_lki"] = {"defn": h.defn, "face": h.face, "controller": h.controller,
                                   "zone": "bz", "tapped": h.tapped, "chars": self.chars(c.top_of),
                                   "ref": href}
            if c.under and ((rec["from"] == "bz" and ev["to"] != "bz")
                            or (rec["from"] == "shield" and ev["to"] not in ("bz", "shield"))) \
                    and not (ev.get("card_only")
                             or self.fdef(ev["subject"][0], c.face if c.face >= 0 else None).star):
                # 一緒に離れる下のカードすべて（移動直前の姿。収集レコード側の was_under と対。第294弾）
                rec["was_under"] = [s.ref(u) for u in c.under]
            return rec
        if ev["ev"] == "draw":
            rec = {"ev": "draw", "player": ev["player"]}
            if ev.get("turn_draw"):
                rec["turn_draw"] = True   # ターンのはじめのドローそのもの（第219弾）
            return rec
        if ev["ev"] == "battle_start":
            # バトル開始の置換（第271弾）: 置換の照合用にイベントをそのまま返す
            # （_apply_one の単純イベントと同じ扱い）。これまで _record_for は
            # move/draw しか作らず、battle_start の replace は _replacement で
            # 常に None になって一度も諮問されなかった。converted には
            # battle_start の replace は無く（trigger のみ32件）、既存カードへの
            # 影響は無い。break は _break_candidates の別経路があるため含めない。
            return dict(ev)
        return None

    def apply_batch(self, evs: list[dict]):
        if evs and not any(ev.get("sba") for ev in evs):
            self.s.sba_held.clear()   # 状況起因処理以外で状態が動いたら、止められていた破壊をもう一度試す
        records = []
        for ev in evs:
            records += self._apply_one(ev)
        for r in records:   # S・トリガー・プラスの条件用: このターンにブレイクされたシールドの数
            if r.get("ev") == "break":
                k = f"broken:{r['player']}"
                self.s.turn_counters[k] = self.s.turn_counters.get(k, 0) + r.get("count", 0)
        self._record_history(records)
        self._sba()
        for r in records:
            self._collect_triggers(r)

    def _hist_bump(self, kind: str, player: int, n: int = 1) -> int:
        """履歴カウンタ（turn_counters の hist:<kind>:{player}）を加算し、新しい値を返す。"""
        k = f"hist:{kind}:{player}"
        v = self.s.turn_counters.get(k, 0) + n
        self.s.turn_counters[k] = v
        return v

    def _hist_bump_from(self, kind: str, frm: str | None, player: int, n: int = 1) -> None:
        """from 修飾つき履歴カウンタ（第214弾。式 {turn_count: {kind, from: <zone>}} の読み先。
        「山札からシールドゾーンに加えた」のように、移動元ゾーンで絞る条件のために
        通常カウンタと並べて hist:<kind>_from_<zone>:<player> にも集約する。"""
        if frm:
            self._hist_bump(f"{kind}_from_{frm}", player, n)

    def _used_snapshot(self, cid: int) -> dict:
        """「使った」履歴に残す印刷特性のスナップショット（カードはその後ゾーンを移るため値で持つ）。"""
        d = self.fdef(cid)
        return {"cost": d.cost, "types": list(d.types), "civs": list(d.civs)}

    def _record_history(self, records: list[dict]):
        """履歴カウンタ基盤（バンドC1 U19＋統一で追加した kind）の記録器。
        適用済みレコードを並び順に走査し、turn_counters の hist: キーへ集約する。あわせて
        対象レコードに rec["ord"] = {kind: その出来事のこのターン通し番号} を刻む
        （when の {ord: {kind, 比較}} 照合用。同時適用の束内の順序は records の並び順）。
        既存キー（entered／drew／broken／broke_in）は従来どおり別途維持され、ここでは触らない。
        攻撃の記録は combat の phase 0 が出す attack レコード（適用はここを一度だけ通る）から拾う。"""
        s = self.s
        tc = s.turn_counters
        for rec in records:
            ev = rec.get("ev")
            if ev == "move":
                lki = rec.get("lki")
                ctrl = lki["controller"] if lki else rec["controller"]   # 離れる側は移動前のコントローラで数える
                frm, to = rec.get("from"), rec.get("to")
                if to == "shield":
                    self._hist_bump("shield_put", rec["controller"])
                    self._hist_bump_from("shield_put", frm, rec["controller"])
                if frm == "shield" and to != "shield" and not rec.get("host"):
                    # 束の下のカードは host 付き（第169弾）。シールドの数は束で1つなので、
                    # 下のカードの分は数えない（トップのレコードで1回だけ数える）
                    self._hist_bump("shield_left", ctrl)
                if to == "mana":
                    n = self._hist_bump("mana_put", rec["controller"])
                    self._hist_bump_from("mana_put", frm, rec["controller"])
                    rec.setdefault("ord", {})["mana_put"] = n
                if to == "bz":
                    n = self._hist_bump("enter", rec["controller"])
                    self._hist_bump_from("enter", frm, rec["controller"])
                    rec.setdefault("ord", {})["enter"] = n
                    if rec.get("unpaid"):
                        self._hist_bump("enter_unpaid", rec["controller"])
                    if rec.get("via") == "generate":   # 実行したタマシード／フィールド／クロスギアは「使った」履歴
                        tc.setdefault(f"hist:used:{rec['controller']}", []).append(
                            self._used_snapshot(rec["subject"][0]))
                if frm == "bz" and to != "bz":
                    if not rec.get("host"):   # 下にあったカードは「特性を持たないカード」の移動であり、クリーチャーとして離れた／破壊された数には入れない（from_under 機構）
                        self._hist_bump("leave", ctrl)
                        if to == "graveyard" and rec.get("reason") == "destroy":
                            self._hist_bump("destroyed", ctrl)
                if to == "graveyard" and rec.get("reason") == "discard":
                    self._hist_bump("discard", ctrl)
                    self._hist_bump_from("discard", frm, ctrl)
            elif ev == "summon":
                n = self._hist_bump("summon", rec["controller"])
                rec.setdefault("ord", {})["summon"] = n
            elif ev == "cast":
                p = rec["player"]
                n = self._hist_bump("cast", p)
                rec.setdefault("ord", {})["cast"] = n
                if rec.get("subject") is not None:   # 唱えた呪文は「使った」履歴（印刷特性のスナップショット）
                    tc.setdefault(f"hist:used:{p}", []).append(self._used_snapshot(rec["subject"][0]))
            elif ev == "draw":
                n = self._hist_bump("draw", rec["player"])
                rec.setdefault("ord", {})["draw"] = n   # draw の ord は枚単位（レコードは1枚ずつ）
            elif ev == "break":
                cnt = rec.get("count", 1)
                self._hist_bump("broken", rec["player"], cnt)
                if rec.get("subject") is not None:   # ブレイクしたクリーチャー単位（broke_by_self の読み先）
                    k = f"hist:broke_by:{rec['subject'][0]}"
                    tc[k] = tc.get(k, 0) + cnt
            elif ev == "attack":
                a = rec["controller"]
                att = rec["subject"][0]
                n = self._hist_bump("attack", a)
                rec.setdefault("ord", {})["attack"] = n
                tc.setdefault(f"hist:attackers:{a}", []).append(att)   # other / filter つきの数え用
                k = f"hist:attack_by:{att}"
                tc[k] = tc.get(k, 0) + 1
                rec["ord"]["attack_by"] = tc[k]
                tgt = rec.get("target")   # 攻撃先は宣言時点で記録する（ブロック／ガードマンで変わっても遡らない。バンドA の設計既定）
                if isinstance(tgt, list):
                    k2 = f"hist:attack_on:{tgt[0]}"
                    tc[k2] = tc.get(k2, 0) + 1
            elif ev == "block":   # ブロックの宣言1回（＝ブロックしたクリーチャー1体）につき1
                self._hist_bump("block", rec["controller"])
            elif ev == "tap":
                self._hist_bump("tap", rec["controller"])
            elif ev == "untap":   # 状態が実際に変わったアンタップだけがレコードになる（ターン開始の一括アンタップも数える。バンドB U18 の設計既定）
                self._hist_bump("untap", rec["controller"])
                uc = rec["subject"][0]
                if s.alive(rec["subject"]) and s.cards[uc].zone == "bz" and "creature" in self.chars_ro(uc)["types"]:
                    self._hist_bump("untap_creature", rec["controller"])   # 「このターンアンタップしたクリーチャー」（マナのアンタップを除く）

    def _apply_one(self, ev: dict) -> list[dict]:
        s = self.s
        kind = ev["ev"]
        if kind == "move":
            if not s.alive(ev["subject"]):
                return []   # 想定外のゾーンへ移っていたら、それ以上処理しない（400.8）
            cid = ev["subject"][0]
            c = s.mut_card(cid)
            if ev["to"] == "bz" and c.zone != "hold" and not self.permits(cid, "enter_bz"):
                return []   # 出せない（実行は h_play で先に確認している。効果で出す場合はここで止める）
            from_zone = ev.get("from") if c.zone == "hold" else c.zone
            if from_zone == "bz" and ev["to"] == "graveyard" and ev.get("reason") == "destroy" \
                    and self.chars(cid).get("indestructible"):
                return []   # 「破壊されない」（第127弾）: 置換を経た最終的な破壊に対して判定し、破壊自体が起こらない
            if from_zone == "hand" and ev["to"] == "graveyard" and ev.get("reason") == "discard" \
                    and ev.get("by") is not None and ev["by"] != c.controller \
                    and self._hand_protected(c.controller, ev):
                return []   # 「相手の呪文やクリーチャーの能力によって、自分の手札は捨てられない」（第253弾）
            if from_zone == "bz" and ev["to"] != "bz":
                # 「バトルゾーンを離れない」（第49弾）: 置換を経た最終的な移動に対して判定し、該当すれば移動自体が起こらない
                for nl in self.chars_ro(cid)["no_leave"]:
                    if nl.get("except_destroy") and ev["reason"] == "destroy":
                        continue   # 「破壊される以外は離れない」型: 破壊だけは通す
                    if nl.get("except_battle") and ev.get("battle"):
                        continue   # 「バトルに負けた時以外は離れない」型: バトルの敗北による破壊だけは通す（combat が battle 印を付ける）
                    if nl.get("by_opp") and not (ev.get("by") is not None and ev["by"] != c.controller):
                        continue   # 「相手の効果では離れない」型: by の無い移動（状況起因・バトル）と自分の効果は通す
                    if nl.get("by_opp_spell") and not (ev.get("by") is not None and ev["by"] != c.controller
                                                       and ev.get("cause_kind") == "spell"):
                        continue   # 「相手の呪文の効果では離れない」型（第230弾）: 相手が解決した呪文による移動だけを止める
                    return []
            lki = {"defn": c.defn, "face": c.face, "controller": c.controller, "zone": from_zone,
                   "tapped": c.tapped, "chars": self.chars(cid), "ref": list(ev["subject"]),
                   "exlife_of": list(c.exlife_of) if c.exlife_of is not None else None}   # 過去の状態を見る（603.5c）
            was_face_up = c.face_up   # 移動前の表向き状態（手札に加わると face_up は消える。裁きの紋章の判定用。第169弾）
            sealed_from = None
            if c.seal_of >= 0:   # 封印そのものが動く: 対象から外し、記録に「どのカードの封印だったか」を残す
                host = s.mut_card(c.seal_of)
                if cid in host.seals:
                    host.seals.remove(cid)
                sealed_from = s.ref(c.seal_of)
                c.seal_of = -1
            host_ref = host_lki = None   # このカード自身が他のカードの下にあった場合の宿主（移動直前の姿。from_under 照合用）
            if from_zone == "bz" and c.top_of >= 0 and c.seal_of < 0:
                hc = s.cards[c.top_of]
                host_ref = s.ref(c.top_of)
                host_lki = {"defn": hc.defn, "face": hc.face, "controller": hc.controller, "zone": "bz",
                            "tapped": hc.tapped, "chars": self.chars(c.top_of), "ref": host_ref}
            my_seals = list(c.seals) if ev["to"] != "bz" else []   # 封印されたカードが離れる時、封印は墓地に置く
            if my_seals:
                c.seals = []
            unders = list(c.under)
            under_snap = None   # 離れる時に下にあったクリーチャー（leave_under_untap）: 再構築で場に残る最初のクリーチャー1体
            if unders and ev["to"] != "bz" and (ev.get("card_only") or self.fdef(cid, c.face if c.face >= 0 else None).star):
                # カードとして離れる（801.4）/ スター進化（離れる時は一番上のカードだけ）: 下のカードを再構築して残す
                uc = next((u for u in unders if "creature" in self.cdef(u).types), None)
                if uc is not None:
                    under_snap = s.ref(uc)
                self._rebuild(cid)
                unders = []
            stack_unders = []
            if unders and ev["to"] == "shield" and ev.get("shield_stack"):
                # シールドの上に重ねて置く（第148弾）: 自分の下のカードは別のシールドにせず、束の一部として連れて行く
                stack_unders, unders = unders, []
            under_lkis = []   # 一緒に離れる下のカードの移動直前の姿（from_under レコード用。移動前に取る）
            if (from_zone == "bz" and ev["to"] != "bz") or \
                    (from_zone == "shield" and ev["to"] not in ("bz", "shield")):
                # シールドの束も一緒に動く（第169弾）: 束の下のカードにも move レコードを出す。
                # バトルゾーンへ出る時とシールド内の置き直しは除く（前者は下のカードが場の一部に
                # なる別経路、後者はシールドの置かれた数に影響するため）。face_up も snapshot に
                # 載せ、裁きの紋章（シールドの上に表向きに置かれていたカード）の判定に使う
                for u in unders:
                    uc = s.cards[u]
                    under_lkis.append((u, {"defn": uc.defn, "face": uc.face, "controller": uc.controller,
                                           "zone": from_zone, "tapped": uc.tapped, "chars": self.chars(u),
                                           "ref": s.ref(u), "face_up": uc.face_up}))
            self._raw_move(cid, ev["to"], ev.get("position", "top"), ev.get("controller"))
            if ev.get("sst"):
                c.sst = True         # スーパー・S・トリガーの印は移動した先で付ける（移動で消えるため）
            if ev.get("stp"):
                c.stp = True
            if ev.get("odrive"):
                c.odrive = True
                c.odrive_civs = list(ev.get("odrive_civs", []))
            if ev.get("summon_tapped"):   # フォートE（第168弾）: 移動で消えた召喚時タップ記録を出し直す
                c.summon_tapped = [{"ref": list(e["ref"]), "races": list(e.get("races", []))}
                                   for e in ev["summon_tapped"]]
            if ev.get("summon_fuel"):   # 第189弾: 移動で消えた召喚時燃料の記録を出し直す
                c.summon_fuel = [list(r) for r in ev["summon_fuel"]]
            if ev.get("bazurenda"):
                c.bazurenda = ev["bazurenda"]
            if ev.get("tapped"):   # 「タップして置く」: 置かれた時点でタップ状態（別のタップ イベントにしない）
                c.tapped = True
            if ev.get("face_up") and ev["to"] == "shield":   # 「表向きでシールドゾーンに置く」（ギャラクシールド）
                c.face_up = True
                self.note_public("face_up", cid)
            if ev["to"] == "shield" and ev.get("shield_stack"):
                # シールドの束の上に重ねる（第148弾）: 束は [新しいトップ, その下のカード, 旧トップ, 旧トップの下] の順で
                # 1つのシールドとして合体する。対象の束が消えている・持ち主が違う場合は通常の新しいシールドとして置く。
                # 旧トップの face_up はそのまま残る（覆われても表向きのまま。数え・選択は bundle_of 経由）
                for u in stack_unders:
                    self._raw_move(u, "shield")
                    self.mut_zlist("shield", s.cards[u].owner).remove(u)   # 束の下のカードはシールドの数に数えない（113.2）
                new_under = list(stack_unders)
                tgt = ev["shield_stack"]
                if s.alive(tgt):
                    top = tgt[0]
                    while s.cards[top].top_of >= 0:   # 対象がその後別のカードの下に入っていたら、今のトップへたどる
                        top = s.cards[top].top_of
                    tc = s.cards[top]
                    if top != cid and tc.zone == "shield" and tc.owner == c.owner:
                        self.mut_zlist("shield", tc.owner).remove(top)
                        new_under += [top] + list(tc.under)
                        tc.under = []
                c.under = new_under
                for u in new_under:
                    s.mut_card(u).top_of = cid
            if ev.get("face_down") and ev["to"] == "mana":   # 「裏向きのままマナゾーンに置く」（第128弾）: 置かれた時点で裏向き（別のイベントにしない）
                c.face_down = True
            if ev["to"] == "bz" and "enters_tapped" in self.chars_ro(cid)["keywords"]:   # 「タップしてバトルゾーンに出る」
                c.tapped = True
            if ev["to"] == "mana" and any("opp_mana_tapped" in self.chars_ro(x)["keywords"] for x in self.bz_tops(1 - c.owner)):
                c.tapped = True   # 「相手はカードをマナゾーンに置く時、タップして置く」（置く時点でタップ。別のイベントにしない）
            for u in unders:   # クリーチャーとして離れたら下のカードも同じゾーンへ（109.2b, 316.3）
                if s.cards[u].zone == "bz" or s.cards[u].top_of == cid:   # シールドの束も同時に動く（113.2）
                    self._raw_move(u, ev["to"])
            if from_zone == "shield" and ev["to"] != "shield":
                # Zラッシュ（常在型）: シールドが離れた際、その時点でバトルゾーンにいる Zラッシュ持ち全員の
                # ハイパーモードを即座に解放する（S・トリガーの使用より前。後から出たクリーチャーには適用されない）
                for p in (0, 1):
                    for x in self.bz_tops(p):
                        if "z_rush" in self.fdef(x).keywords:
                            s.mut_card(x).hyper = True
            new = s.ref(cid)
            if ev["to"] == "bz" and (self.link_side(cid) is not None or self.link_spec(cid)):   # ゴッドが出たらリンク手順を行う
                self._push({"t": "g_link", "cid": cid, "player": c.controller, "step": "start"})
            if ev["to"] == "bz" and "field" in self.fdef(cid).types:
                # 一意性はプール分離（第151弾。公式裏取り済み）: D2フィールドは D2フィールド同士だけが
                # 数え合い（703.4l。両プレイヤー合わせて1つだけ。行き先は破壊＝701.6＋109.1＋公式 QA 47896）、
                # 通常フィールド同士は第25弾の挙動を温存する。通常フィールドと D2 は互いに影響しない。
                # 適用は出現イベントごとに1回だけ（このフックは move の適用時にだけ走る）: 置換で生き残った
                # D2 は、次の新しい D2 が出るまで残る（QA 47896）
                d2 = "d2_field" in self.fdef(cid).types
                others = [x for p in (0, 1) for x in self.bz_tops(p)
                          if x != cid and "field" in self.fdef(x).types
                          and ("d2_field" in self.fdef(x).types) == d2]
                if others:
                    self._push(self.ev_task([{"ev": "move", "subject": s.ref(x), "to": "graveyard",
                                              "reason": "destroy"} for x in others]))
            stack_on = ev.get("stack_on")
            evo_bases = []   # 進化元になったカード（第150弾: 進化印がある時だけ evolve_base レコードを出す）
            if ev["to"] == "bz" and stack_on and s.alive(stack_on):
                base = stack_on[0]
                if s.cards[base].zone != "bz":      # 超無限墓地進化など: 進化元も自分のゾーンから移す
                    self._raw_move(base, "bz")
                self._stack(cid, base)
                if ev.get("evolution"):
                    evo_bases.append(base)
                for x in ev.get("stack_more", []):   # 進化元の残り（801.1b。超無限墓地進化やバトルゾーンの複数の進化元）
                    if not s.alive(x):
                        continue
                    if s.cards[x[0]].zone != "bz":   # 墓地・マナ等から選んだ進化元も場へ移す（第218弾Ω）
                        self._raw_move(x[0], "bz")
                    self._stack(cid, x[0], more=True)
                    if ev.get("evolution"):
                        evo_bases.append(x[0])
            out = [{"ev": "move", "subject": new, "lki": lki, "from": from_zone, "to": ev["to"],
                    "reason": ev["reason"], "controller": c.controller}]
            if sealed_from is not None:
                out[0]["sealed_from"] = sealed_from
            for sc in my_seals:   # 離れたカードに付いていた封印は、それぞれ持ち主の墓地に置く
                so = s.cards[sc]
                so.seal_of = -1
                self._raw_move(sc, "graveyard")
                out.append({"ev": "move", "subject": s.ref(sc), "lki": None, "from": "bz", "to": "graveyard",
                            "reason": "seal", "controller": so.controller, "sealed_from": new})
            if ev.get("via"):
                out[0]["via"] = ev["via"]
            if ev.get("alt"):        # 代替コストで実行された（誘発の if: {alt_paid} の照合用）
                out[0]["alt"] = True
            if ev.get("vivid"):      # ビビッドローで実行された（when: {vivid: true} と誘発の if: {vivid_paid} の照合用）
                out[0]["vivid"] = True
            if ev.get("unpaid"):     # コストを支払わずに出た（when: {unpaid: true} の照合用。summon レコードには従来から載せていたが、move レコード側に無く move 誘発がすべて不発だった）
                out[0]["unpaid"] = True
            elif ev["to"] == "bz" and ev.get("reason") != "summon" and from_zone != "bz":
                out[0]["unpaid"] = True   # 第257弾: 効果で出されたカードはマナをタップせずに出ている
            if ev.get("position"):   # 置かれた位置（「山札の一番下に置かれた時」の照合用。第290弾。_record_for と対）
                out[0]["position"] = ev["position"]
            if ev.get("battle"):   # バトルで負けて破壊された（「バトル中に破壊された時」の照合用。第332弾。_record_for と対）
                out[0]["battle"] = True
            if ev.get("stack_on"):   # 進化として重ねて出た（「進化して出た時」の照合用。第150弾で収集レコードへの伝播を追加。シールドの束は shield_stack キーで別）
                out[0]["stacked"] = True
            if ev.get("no_trigger"):   # この移動で出たカード自身の出た時能力は誘発しない（第213弾）
                out[0]["no_trigger"] = True
            if ev.get("cause"):
                out[0]["cause"] = ev["cause"]
            if ev.get("cause_defn"):   # 効果帰属（基盤B1）: 収集レコードにも発生源の defn 名と種別を載せる
                out[0]["cause_defn"] = ev["cause_defn"]
                out[0]["cause_kind"] = ev["cause_kind"]
            if ev.get("by") is not None:   # その移動を起こした効果の解決者（バンドC1 U26: 収集レコードに無く、when の by 照合が move 誘発で使えなかった）
                out[0]["by"] = ev["by"]
            if ev.get("strigger") in ("off", "on") and ev["to"] == "hand":
                # S・トリガーの印（バンドC2 U68）: 手札に加わったカード（束の下のカードも含む）に印を付ける
                for u in [cid] + [u for u in unders if s.cards[u].zone == "hand"]:
                    if ev["strigger"] == "off":
                        s.mut_card(u).strigger_off = True
                    else:
                        s.mut_card(u).strigger_on = True
            if ev.get("face_up") or (from_zone == "shield" and was_face_up):
                # 表向きで置かれたか（ギャラクシールド）。シールドを表向きで離れた時もレコードに
                # 載せる（G城の「表向きで離れた時」誘発用。第176弾。when の face_up 照合はレコードを見る）
                out[0]["face_up"] = True
            if from_zone == "shield" and was_face_up and unders:
                # 裁きの紋章（第169弾）: シールドの上に表向きに置かれていたカード。束のトップで
                # 下にカードがある（＝何かの上に置かれている）場合だけ。単独の表向きシールド
                # （ギャラクシールド）は紋章ではない。覆われて下にいる紋章は下のカードのレコードで扱う
                out[0]["emblem"] = True
            if under_snap is not None:
                out[0]["under"] = under_snap   # 離れる時に下にあったクリーチャー（解決時に {ref: event.under} で指せる。leave_under_untap）
            if under_lkis:
                wu = [s.ref(u) for u, _ in under_lkis if s.cards[u].zone == ev["to"]]
                if wu:
                    out[0]["was_under"] = wu   # 一緒に離れた下のカードすべて（移動後の姿。「下にあったカード」を {ref: event.was_under} で指す。第294弾。_record_for と対）
            if ev["to"] == "bz" and "ex_life" in self.chars_ro(cid)["keywords"]:
                out += self._exlife_shield(cid)
            if ev["to"] == "bz" and "extra_ex_life" in self.chars_ro(cid)["keywords"]:
                # エクストラEXライフ（第237弾）: 紐付けるシールドは2枚。置換能力の側は
                # ex_life と同じ形で、その中から1枚を選んで墓地に置く
                out += self._exlife_shield(cid)
                out += self._exlife_shield(cid)
            if ev["reason"] == "summon":
                srec = {"ev": "summon", "subject": new, "controller": c.controller, "player": c.controller,
                        "unpaid": bool(ev.get("unpaid"))}
                if ev.get("via"):
                    srec["via"] = ev["via"]   # 出し方の印も summon レコードに載せる（第149弾）
                out.append(srec)
            for b in evo_bases:   # 「進化元になる時」（第150弾）: 進化元を subject、出たクリーチャーを top とする合成レコード
                out.append({"ev": "evolve_base", "subject": s.ref(b), "top": new, "controller": s.cards[b].controller})
            if ev["to"] == "bz" and "creature" in self.chars_ro(cid)["types"]:   # 「このターンに出たクリーチャー」の記録（式 entered が数える）
                s.turn_counters.setdefault(f"entered:{c.controller}", []).append(cid)
            if ev["to"] == "bz" and ev.get("seal"):
                # 封印を付けた状態で出す（メモッタ等）: 誘発の収集より前に付くので、出た時能力は無視される
                host = s.mut_card(new[0])
                deck = s.zones["deck"][host.controller]
                for _ in range(int(ev["seal"])):
                    if not deck:
                        break
                    top = deck[0]
                    self._raw_move(top, "bz")
                    sc = s.mut_card(top)
                    sc.top_of = new[0]
                    sc.seal_of = new[0]
                    host.seals.append(top)
            if ev["to"] == "bz" and any("コマンド" in r for r in self.fdef(cid).races):
                # コマンドが出た時、その持ち主はそのコマンドと同じ文明を持つ自身のカードから封印を1つ墓地に置く
                self._push({"t": "seal_release", "player": c.controller, "civs": list(self.fdef(cid).civs)})
            if host_ref is not None:
                out[0]["host"] = host_ref   # このカード自身が下にあって単独で動いた（from_under 照合用）
                out[0]["host_lki"] = host_lki
            for u, u_lki in under_lkis:
                # 一緒に離れた下のカードにも move レコードを出す（from_under 機構）。下のカードは
                # 「特性を持たないカード」として置かれる（総合ルールの進化の扱い）ため、レコードには
                # 宿主（上にいたカード）の移動直前の姿を host / host_lki として必ず載せ、通常の
                # クリーチャーの移動と区別できるようにする。実際に一緒に動いたものだけが対象
                # （再構築で場に残る分は unders から外れており、ここには来ない）
                if s.cards[u].zone != ev["to"]:
                    continue
                r = {"ev": "move", "subject": s.ref(u), "lki": u_lki, "from": from_zone, "to": ev["to"],
                     "reason": ev["reason"], "controller": u_lki["controller"],
                     "host": lki["ref"], "host_lki": lki}
                if from_zone == "shield" and u_lki.get("face_up"):
                    # 束の下にいた表向きのカードも裁きの紋章（第169弾）。下にいる時点で何かの
                    # 上に置かれているので、束の有無は問わない
                    r["emblem"] = True
                if ev.get("via"):
                    r["via"] = ev["via"]
                if ev.get("cause"):
                    r["cause"] = ev["cause"]
                if ev.get("cause_defn"):   # 効果帰属（基盤B1）: スタック全体を動かした効果の帰属を下のカードにも載せる
                    r["cause_defn"] = ev["cause_defn"]
                    r["cause_kind"] = ev["cause_kind"]
                if ev.get("by") is not None:
                    r["by"] = ev["by"]
                out.append(r)
            return out
        if kind == "draw":
            p = ev["player"]
            deck = s.zones["deck"][p]
            if not deck:
                return []   # 山札が無ければ何もしない。「引いた時」も誘発しない（114.6a）
            cid = deck[0]
            self._raw_move(cid, "hand")
            s.mut_card(cid).drawn_turn = s.turn   # ビビッドロー: このターンにドローした記録
            s.turn_counters[f"drew:{p}"] = s.turn_counters.get(f"drew:{p}", 0) + 1   # このターン引いた枚数（第142弾）
            drec = {"ev": "draw", "player": p, "subject": s.ref(cid)}
            if ev.get("turn_draw"):
                drec["turn_draw"] = True   # ターンのはじめのドローそのもの（第219弾）
            return [drec,
                    {"ev": "move", "subject": s.ref(cid), "lki": None, "from": "deck", "to": "hand",
                     "reason": "draw", "controller": p}]
        if kind in ("tap", "untap"):
            if not s.alive(ev["subject"]):
                return []
            c = s.mut_card(ev["subject"][0])
            if c.tapped == (kind == "tap"):
                return []   # 「になる」誘発は状態が変わった時だけ（603.2c）
            c.tapped = kind == "tap"
            if c.link:   # G・リンク: グループは1体なので、タップ状態は全員で共有する
                for m in self.link_members(ev["subject"][0]):
                    s.mut_card(m).tapped = c.tapped
            return [{"ev": kind, "subject": ev["subject"], "controller": c.controller}]
        if kind in ("attack", "block", "cast", "turn_start", "turn_end", "break", "battle_win", "battle_lose", "battle_start", "attack_end", "attack_unblocked", "break_before", "mugon_used", "link_established", "battle_end", "janken"):
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
        s.mut_card(top).exlife_of = s.ref(cid)
        return [{"ev": "move", "subject": s.ref(top), "lki": None, "from": "deck", "to": "shield",
                 "reason": "put", "controller": p}]

    def _stack(self, top: int, base: int, more: bool = False):
        """進化: base（とその下）を top の下に重ねる（801.1, 801.2）。同一のクリーチャーとして扱い、
        タップ状態と受けていた効果を引き継ぐ。進化クリーチャーは召喚酔いしない（801.3）。
        more は2枚目以降の進化元（801.1b）。タップ状態は1枚でもタップなら進化後もタップ（801.2b）。"""
        s = self.s
        t, b = s.mut_card(top), s.mut_card(base)
        old = s.ref(base)
        for p in (0, 1):   # 進化元の EXライフシールドは進化後のクリーチャーに引き継がれる（2026-04-10 裁定）
            for sh in s.zones["shield"][p]:
                if s.cards[sh].exlife_of is not None and list(s.cards[sh].exlife_of) == old:
                    s.mut_card(sh).exlife_of = s.ref(top)
        if "cross_gear" in self.cdef(top).types and "cross_gear" in self.cdef(base).types:
            # 第304弾: 進化クロスギア: クロス先は束のトップだけが持つ。進化元が
            # クロスしていたら、進化後のギアがそのままクロスした状態になる
            t.crossed = b.crossed
            b.crossed = None
        t.under = (t.under if more else []) + [base] + b.under
        if more:   # 第231弾: 直接の進化元を順に記録（star 離脱時のセグメント分離用）
            if base not in t.stack_bases:
                t.stack_bases.append(base)
        else:
            t.stack_bases = [base]
        for u in t.under:
            s.mut_card(u).top_of = top
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
        """再構築（801.4）。下のカードのうち、一番上の単独で存在できるカード
        （クリーチャー。第304弾以降はクロスギアも）を残す。"""
        s = self.s
        c = s.mut_card(top)
        under = list(c.under)
        c.under = []
        bases = [b for b in c.stack_bases if b in under]
        if len(bases) >= 2:   # 第231弾: 進化V 等の複数進化元は、進化元ごとに別々のクリーチャーとして残す
            segs: list[list[int]] = []
            cur = None
            for u in under:
                if u in bases:
                    cur = [u]
                    segs.append(cur)
                elif cur is None:
                    self._raw_move(u, "graveyard")   # どの進化元にも属さない下のカード
                else:
                    cur.append(u)
            old = s.ref(top)
            for seg in segs:
                while seg and "creature" not in self.cdef(seg[0]).types:
                    self._raw_move(seg.pop(0), "graveyard")
                if not seg:
                    continue
                nt = s.cards[seg[0]]
                nt.top_of = -1
                nt.under = seg[1:]
                for u in nt.under:
                    s.cards[u].top_of = nt.cid
                nt.tapped = c.tapped                                   # 801.4d
                new = s.ref(nt.cid)
                for ce in s.continuous:
                    if ce["affected"] is not None and old in ce["affected"]:
                        ce["affected"].append(new)
            c.stack_bases = []
            return
        while under and "creature" not in self.cdef(under[0]).types \
                and "cross_gear" not in self.cdef(under[0]).types:
            # 第304弾: クロスギアも単独で存在できる（進化クロスギアの束の再構築）
            self._raw_move(under.pop(0), "graveyard")
        if not under:
            return
        nt = s.mut_card(under[0])
        nt.top_of = -1
        nt.under = under[1:]
        for u in nt.under:
            s.mut_card(u).top_of = nt.cid
        nt.tapped = c.tapped                                   # 801.4d
        if "cross_gear" in self.cdef(nt.cid).types:
            nt.crossed = c.crossed   # 第304弾: トップだけ離れた時、下のギアがクロスしたまま場に残る
        # 801.4c: 新たに出るわけではないので、そのカード自身の出たターンをそのまま使う
        # （ターンのはじめから下にあったなら酔わず、このターンに出た進化元なら酔う）
        old, new = s.ref(top), s.ref(nt.cid)
        for ce in s.continuous:
            if ce["affected"] is not None and old in ce["affected"]:
                ce["affected"].append(new)

    def _lose_immune(self, loser: int, reason: str) -> bool:
        """第188弾: 敗北の防止。loser が reason による敗北を防がれているか。
        (1) op no_lose の継続的効果（once なら防いだ時に消費する）。(2) バトルゾーンの
        常在型能力 no_lose（if があれば評価する。deck_out_only は山札切れだけ）。
        「相手はゲームに勝てない」は「自分はゲームに負けない」と同じことなので、勝敗の
        両側はこの1つの判定で足りる。"""
        s = self.s
        consumed = []
        for ce in s.continuous:
            nl = ce.get("no_lose")
            if not nl or nl["player"] != loser:
                continue
            if nl["deck_out_only"] and reason != "deck_out":
                continue
            if nl["once"]:
                consumed.append(ce)
            else:
                return True
        if consumed:
            for ce in consumed:
                s.continuous.remove(ce)
            return True
        for c in self.bz_tops(loser):
            for _, ab in self.abilities(c, "static"):
                if "no_lose" not in ab:
                    continue
                nl = ab["no_lose"]
                if isinstance(nl, dict) and nl.get("deck_out_only") and reason != "deck_out":
                    continue
                if "if" in ab:
                    env = {"you": loser, "self": s.ref(c), "vars": {}}
                    if not self._static_cond(ab["if"], env):
                        continue
                return True
        return False

    def _lose_candidates(self, loser: int, reason: str | None = None) -> list[tuple[int, int, dict]]:
        """敗北を置換できる能力（when: {event: lose} の kind: replace）を持つ、敗北する側のカード。
        発生源はバトルゾーンのカードと、手札にあるカードのうち zone: hand を宣言した置換
        （第287弾。《一王二命三眼槍》の「手札にあるこのカードを〜山札の下に置いてもよい」。
        バトルゾーン外の発生源は、そのゾーンを宣言した置換だけという _replacement と同じ規則）。
        when.reason があれば敗北の reason（direct_attack / deck_out / state / effect）と照合する（第188弾）。"""
        s = self.s
        out = []
        rec = {"ev": "lose", "controller": loser, "reason": reason}
        srcs = [(c, False) for c in self.bz_tops(loser)]
        srcs += [(c, True) for c in s.zones["hand"][loser]]
        for c, need_zone in srcs:
            for i, ab in self.abilities(c, "replace"):
                if ab.get("when", {}).get("event") != "lose":
                    continue
                if need_zone and ab.get("zone") != "hand":
                    continue   # 手札の発生源は zone: hand を宣言した置換だけ
                wr = ab.get("when", {}).get("reason")
                if wr is not None and reason is not None and reason not in (wr if isinstance(wr, list) else [wr]):
                    continue
                env = {"you": loser, "self": s.ref(c), "event": rec, "vars": {}}
                if "if" in ab and not self.eval_cond(ab["if"], env):
                    continue
                out.append((c, i, ab))
        return out

    def game_lose(self, loser: int, reason: str) -> list[dict]:
        """敗北の確定口: 防止されていれば何もしない。置換できる能力があれば諮問タスクを返し、無ければその場で敗北を確定する。
        ダイレクトアタック・デッキ切れ・状況起因の勝敗・効果による敗北は、すべてここを通す。"""
        s = self.s
        if s.result is not None:
            return []
        if self._lose_immune(loser, reason):   # 第188弾: 敗北の防止（op no_lose / 常在型 no_lose）
            return []
        if not self._lose_candidates(loser, reason):
            s.result = {"winner": 1 - loser, "reason": reason, "turn": s.turn}
            return []
        return [{"t": "lose_replace", "loser": loser, "reason": reason, "phase": 0}]

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
            return self.game_lose(loser, "deck_out")
        for c in self.bz_tops():   # 常在の勝敗条件（kind: state）。バトルゾーンで機能している間、条件を満たしたら決まる
            for _, ab in self.abilities(c, "state"):
                env = {"you": s.cards[c].controller, "self": s.ref(c)}
                if self.eval_cond(ab["if"], env):
                    for o in ab["effect"]:
                        win = o["op"] == "win"
                        who = self._rel(o.get("player", "you"), env)
                        if win:
                            if self._lose_immune(1 - who, "state"):   # 第188弾: 負けない側がいればその常在勝利は働かない
                                break
                            s.result = {"winner": who, "reason": "state", "turn": s.turn}
                            return []
                        return self.game_lose(who, "state")
                    else:
                        return []
                    continue
        for p in (0, 1):   # S-MAX進化の2体制限: 自分のS-MAX進化クリーチャーが2体以上あれば、1体を残して残りを手札に戻す
            tops = [c for c in self.bz_tops(p) if self.fdef(c).s_max]
            if len(tops) >= 2:
                return [{"t": "smax_reduce", "player": p}]
        with self.chars_scope():   # 読み取りだけ: 同じ状態での chars() の重複計算を省く
            glob = self._sba_power_safe_global()
            dead = [s.ref(c) for c in self.bz_tops()
                    if not self._sba_power_safe(c, glob)
                    and "creature" in self.chars_ro(c)["types"] and self.chars_ro(c)["power"] <= 0]   # 703.4c
        # 「墓地に置かれるかわりにとどまる」置換で破壊できなかったものは、状態が動くまで同じ処理を繰り返さない
        # （繰り返すと無限ループになる）。パワーが0より大きくなれば対象から外れる
        s.sba_held = [r for r in s.sba_held if r in dead]
        dead = [r for r in dead if r not in s.sba_held]
        if dead:
            s.sba_held += [r for r in dead if r not in s.sba_held]
            return [self.ev_task([{"ev": "move", "subject": r, "to": "graveyard", "reason": "destroy", "sba": True}
                                  for r in dead])]
        castles = [s.ref(c) for c in self.bz_tops()   # 城（第178弾）: 要塞化したシールドがシールドゾーンを離れたら墓地へ
                   if s.cards[c].fortifies is not None
                   and not (s.alive(s.cards[c].fortifies)
                            and s.cards[s.cards[c].fortifies[0]].zone == "shield")]
        if castles:
            return [self.ev_task([{"ev": "move", "subject": r, "to": "graveyard", "reason": "put", "sba": True}
                                  for r in castles])]
        return []

    def _mod_nonneg(self, m: dict) -> bool:
        """この mod がパワーを下げないと確定できるか（定義だけで決まる。保守的: 迷えば False）。"""
        pw = m.get("power", 0)
        if isinstance(pw, dict):
            if not (isinstance(pw.get("amount"), (int, float)) and pw["amount"] >= 0):
                return False
        elif not isinstance(pw, (int, float)) or pw < 0:
            return False
        if "power_set" in m:   # 第272弾: パワー置換は下げることがある（－∞）
            return False
        if "power_when" in m:
            return False
        for kw in m.get("grant", []):
            ent = self.rules.keywords.get(kw)
            if ent is None:
                continue
            for ab in ent["abilities"]:
                if "mod" in ab and not self._mod_nonneg(ab["mod"]):
                    return False
        return True

    def _sba_power_safe_global(self) -> bool:
        """盤面のどの mod もパワーを下げないか（継続的効果・他に及ぶ常在型）。chars_scope の中で呼ぶ。"""
        for ce in self.s.continuous:
            if ce.get("add_from") or "double_power" in ce or not self._mod_nonneg(ce["mod"]):
                return False
        asrc = self._aff_sources()
        if asrc is None:
            return False
        return all(self._mod_nonneg(ab["mod"]) for lst in asrc for _, ab in lst if "mod" in ab)

    def _sba_power_safe(self, c: int, glob: bool) -> bool:
        """パワー0以下の状況起因処理で、特性の計算を省いてよいか（パワーが印刷パワー以上で正と確定する時だけ True）。
        パワーを変えうるのは mod（自分・他のカードの常在型、継続的効果、付与キーワード）とダイナモ・G・リンクだけ。
        DMSIM_CHECK=1 では計算した値と比べる。"""
        if not glob:
            return False
        card = self.s.cards[c]
        if card.link or self.fdef(c).power <= 0:
            return False
        if not all(self._mod_nonneg(ab["mod"]) for _, ab in self.abilities(c, "static") if "mod" in ab):
            return False
        if self.check:
            assert self.chars_ro(c)["power"] > 0, f"sba fast path: cid={c}"
        return True

    def _castle_fortifiers(self, shield_cid: int) -> list:
        """shield_cid を要塞化している城の参照の列（[cid, gen]）。城側の fortifies から逆引きする。
        cid だけで比べる（gen は見ない）: シールドが動いた直後の誘発照合では gen が進んでいるため。
        城がバトルゾーンを離れれば fortifies 自体が消えるので、古い参照が残ることはない。"""
        s = self.s
        return [s.ref(c) for c in self.bz_tops()
                if s.cards[c].fortifies is not None and s.cards[c].fortifies[0] == shield_cid]

    def _subject_match(self, pat, cid, env, lki, base=False) -> bool:
        if pat == "self":
            return env.get("self") is not None and cid == env["self"][0]
        if pat == "crossed":   # 「これをクロスしたクリーチャー」（303.3a）。離れた後の誘発は離れる前の姿（lki）で見る
            g = self.s.cards[env["self"][0]].crossed if env.get("self") else None
            return g is not None and list(g) == (list(lki["ref"]) if lki else self.s.ref(cid))
        if not isinstance(pat, dict):
            return False
        if "refs" in pat:   # 遅延誘発型能力が「その〜」で指すカード
            return [cid, self.s.cards[cid].gen] in pat["refs"] or (lki is not None and lki["ref"] in pat["refs"])
        if "castle_of" in pat:   # 「その城が要塞化しているシールド」（第178弾）: subject のシールドを要塞化している城が指定の参照に含まれる
            v = pat["castle_of"]
            refs = [env["self"]] if v == "self" else env.get("vars", {}).get(v, [])
            if not any(list(r) == list(f) for r in refs if r for f in self._castle_fortifiers(cid)):
                return False
        if "castle_only" in pat:   # 「他の城によって要塞化されていなければ」（第178弾）: subject のシールドを要塞化している城が指定の参照だけ
            v = pat["castle_only"]
            refs = [env["self"]] if v == "self" else env.get("vars", {}).get(v, [])
            forts = self._castle_fortifiers(cid)
            if not forts or any(list(f) not in [list(r) for r in refs if r] for f in forts):
                return False
        if "exlife_of" in pat:   # 「EXライフ」シールド（第190弾）: subject のカードが移動前に紐付けていたクリーチャー
            v = pat["exlife_of"]
            linked = lki.get("exlife_of") if lki is not None else self.s.cards[cid].exlife_of
            if v == "any":   # 「自分のEXライフシールド（どのクリーチャーのものでも）が離れた時」（第307弾）: 紐付けの有無だけを見る
                if linked is None:
                    return False
            else:
                refs = [env["self"]] if v == "self" else env.get("vars", {}).get(v, [])
                if linked is None or not any(list(r) == list(linked) for r in refs if r):
                    return False
        if "zone" in pat:   # subject のいるゾーン（第212弾追加: 「自分のマナゾーンのカードをタップした時」等）。離れた時は lki のゾーンで見る
            z = lki["zone"] if lki else self.s.cards[cid].zone
            if z != pat["zone"]:
                return False
        ctrl = lki["controller"] if lki else self.s.cards[cid].controller
        if "owner" in pat and pat["owner"] != "any" and ctrl != self._rel(pat["owner"], env):
            return False
        if pat.get("other") and env.get("self") and cid == env["self"][0]:
            return False
        f = pat.get("filter", {})
        if any(isinstance(v, dict) for v in f.values()):   # 式の値は照合時に計算する（「マナの枚数よりコストが大きい」など）
            f = {k: self.eval_expr(v, env) if isinstance(v, dict) else v for k, v in f.items()}
        return self.filter_match(cid, f, lki, base)

    def _pattern_match(self, when, rec, src, lki_src) -> bool:
        self_ref = lki_src["ref"] if lki_src else self.s.ref(src)
        if lki_src is None and self.s.cards[src].link:   # G・リンク: 「このクリーチャー」はグループ（代表）を指す
            self_ref = self.s.ref(self.link_rep(src))
        env = {"you": lki_src["controller"] if lki_src else self.s.cards[src].controller,
               "self": self_ref}
        return self._match_when(when, rec, env)

    def _ref_match(self, pat, ref, env) -> bool:
        """イベントに出てくるクリーチャー（攻撃先・攻撃クリーチャー）が、self か subject と同じ形の条件に合うか。"""
        if pat == "self":
            return env.get("self") is not None and ref[0] == env["self"][0]
        return self._subject_match(pat, ref[0], env, None)

    def _match_when(self, when, rec, env) -> bool:
        if when["event"] != rec["ev"]:
            return False
        for k in ("from", "to", "reason", "via"):
            if k in when:
                wv = when[k]
                if isinstance(wv, list):   # リスト指定は「いずれか」（手札以外から出る等）
                    if rec.get(k) not in wv:
                        return False
                elif rec.get(k) != wv:
                    return False
        if "not_reason" in when:   # 理由の否定（第256弾）: 「召喚以外の方法で出た時」
            nv = when["not_reason"]
            if isinstance(nv, list):
                if rec.get("reason") in nv:
                    return False
            elif rec.get("reason") == nv:
                return False
        if rec.get("ev") == "move" and rec.get("from") == "bz" and rec.get("to") == "bz" \
                and "from" in when and "to" not in when:
            # 第183弾: バトルゾーン内の移動（S級侵略で既に場にいるカードを重ねる等）は
            # 「離れた時」ではない（公式Q&A・DARK MATERIAL COMPLEX の裁定）。「出た時」側は
            # 「置くは出すと同義」の扱いで to: bz の照合は通す。
            return False
        if "target" in when:   # 攻撃先: player（シールドも含む）か creature。self や {owner, filter} なら、そのクリーチャーが攻撃された時
            tg, w = rec.get("target"), when["target"]
            if w in ("player", "creature"):
                if (tg == "player") != (w == "player"):
                    return False
            elif tg is None or tg == "player" or not self._ref_match(w, tg, env):
                return False
        if "shield" in when:   # ブレイクされるシールドの条件（第178弾・城）: rec["shield"] は束のトップの参照
            if rec.get("shield") is None or not self._ref_match(when["shield"], rec["shield"], env):
                return False
        if "attacker" in when:   # ブロックされた時などの、攻撃クリーチャーの条件（self なら「このクリーチャーがブロックされた時」）
            if rec.get("attacker") is None or not self._ref_match(when["attacker"], rec["attacker"], env):
                return False
        if "opponent" in when:   # バトルの相手（battle_start の対戦クリーチャー）。self なら「このクリーチャーが攻撃された側でバトルする時」
            if rec.get("opponent") is None or not self._ref_match(when["opponent"], rec["opponent"], env):
                return False
        if "ord" in when:   # その出来事のこのターンでの通し番号（「そのターン最初の〜」「2枚目以降の〜」。履歴基盤が rec に刻む）
            spec = when["ord"]
            v = (rec.get("ord") or {}).get(spec["kind"])
            if v is None:
                return False
            for k, fn in (("eq", int.__eq__), ("ge", int.__ge__), ("gt", int.__gt__),
                          ("le", int.__le__), ("lt", int.__lt__)):
                if k in spec and not fn(v, spec[k]):
                    return False
        if "unpaid" in when and bool(rec.get("unpaid")) != when["unpaid"]:   # マナをタップせずに（コストを支払わずに）
            return False
        if "broke" in when and bool(rec.get("broke")) != when["broke"]:   # 攻撃の終わりに、その攻撃でシールドをブレイクしたか（キリフダッシュ）
            return False
        if "blocked" in when and bool(rec.get("blocked")) != when["blocked"]:   # その攻撃がブロックされたか（attack_end レコードのみが持つ。「ブロックされなかった時」用）
            return False
        if "battle" in when and bool(rec.get("battle")) != when["battle"]:   # バトルで負けて破壊された移動か（combat の敗者 move レコードのみが持つ。「バトル中に破壊された時」用。第332弾）
            return False
        if "turn_draw" in when and bool(rec.get("turn_draw")) != when["turn_draw"]:   # ターンのはじめのドローそのものか（draw レコードのみが持つ。第219弾）
            return False
        if "face_up" in when and bool(rec.get("face_up")) != when["face_up"]:   # 表向きで置かれたか（ギャラクシールド）
            return False
        if "emblem" in when and bool(rec.get("emblem")) != when["emblem"]:   # 裁きの紋章だったか（第169弾）
            return False
        if "position" in when and rec.get("position") != when["position"]:   # 置かれた位置（山札の上か下か。第290弾）
            return False
        if "vivid" in when and bool(rec.get("vivid")) != when["vivid"]:   # ビビッドローで実行されたか（第54弾）
            return False
        if "stacked" in when and bool(rec.get("stacked")) != when["stacked"]:   # 進化として重ねて出たか（第150弾で照合を有効化。第28弾の未実装分）
            return False
        if "player" in when and rec.get("player") != self._rel(when["player"], env):
            return False
        if "opp_hand" in when:   # ジャンケンで相手が出した手（第271弾）: 相手＝この能力のコントローラーの対戦相手
            hands = rec.get("hands")
            if not hands or hands[1 - env["you"]] != when["opp_hand"]:
                return False
        if "by" in when and rec.get("by") != self._rel(when["by"], env):   # そのイベントを起こした効果の解決者（「相手の効果によって〜」）
            return False
        if "cause" in when:   # そのイベントを起こした効果の帰属（基盤B1）: by は発生源コントローラーから見た相対指定、kind は呪文／能力。発生源のない移動（状況起因・コスト）は cause_kind が無く一致しない
            cw = when["cause"]
            if "by" in cw and rec.get("by") != self._rel(cw["by"], env):
                return False
            if "kind" in cw:   # kind はリストも可（「呪文の効果またはクリーチャーの能力によって」。第290弾。defn のリスト形と対）
                kv = cw["kind"]
                if rec.get("cause_kind") not in (kv if isinstance(kv, list) else [kv]):
                    return False
            if "defn" in cw:   # 発生源カードそのもの（第246弾: 《特定カード》の能力で破壊される時）
                dv = cw["defn"]
                if rec.get("cause_defn") not in (dv if isinstance(dv, list) else [dv]):
                    return False
            if "name_has" in cw:   # 発生源カードの名前の一部（第246弾: 名前に《武者》とあるカードの効果で）。面の名前も見る
                dn = rec.get("cause_defn")
                d = self.rules.cards.get(dn) if dn else None
                names = [] if d is None else [d.name] + [f.name for f in (d.faces or [])]
                if not any(cw["name_has"] in nm for nm in names):
                    return False
        if "sealed_from" in when:   # 封印が離れた時: どのカードに付いていた封印か（「このカードの封印がすべてなくなった時」用）
            if rec.get("sealed_from") is None or not self._ref_match(when["sealed_from"], rec["sealed_from"], env):
                return False
        if "from_under" in when:   # 移動直前に他のカードの下にあったか（from_under 機構）: true=下にあった / false=下になかった / self=発生源自身の下にあった / {owner, filter}=宿主への条件（subject と同じ形で宿主の lki に当てる）
            host = rec.get("host")
            fu = when["from_under"]
            if fu is False:   # 「下から」ではない通常の移動だけを見る（例: 破壊された時と下から墓地に置かれた時を分ける）
                if host is not None:
                    return False
            elif host is None:
                return False
            elif fu is True:
                pass
            elif fu == "self":
                if not self._ref_match("self", host, env):
                    return False
            elif isinstance(fu, dict):
                if not self._subject_match(fu, host[0], env, rec.get("host_lki")):
                    return False
            else:
                return False
        if "subject" in when:
            if "subject" not in rec:
                return False
            subj = rec["subject"][0]
            if when["subject"] == "self":
                return env.get("self") is not None and subj == env["self"][0]
            lki = rec.get("lki") if rec.get("from") == "bz" or (isinstance(when.get("subject"), dict) and "exlife_of" in when["subject"]) else None
            return self._subject_match(when["subject"], subj, env, lki)
        return True

    def _trigger_abs(self, defn, face, zone, src=None):
        """誘発型能力の列挙。[(添字, 能力, 面)] を返す（面は pending_ability の解決用）。
        面が決まっている時はその面の能力、未定（手札等）のツインパクトは各面の能力を
        面つきで返す（第169弾）。面未定のカードに継続的効果のゲート類は働かないので
        素の面能力で十分。面を持たないカードは面 None で従来どおり。"""
        d = self.rules.cards[defn]
        if src is not None:
            if face >= 0:
                # 通常経路: ゲート・継続的効果つきの abilities()（面はカードの面）
                return [(i, ab, face) for i, ab in self.abilities(src, "trigger")
                        if ab.get("zone", "bz") == zone]
            if not d.faces:
                # 面を持たないカードはバトルゾーンでも face が -1 のまま（第169弾の欠陥:
                # 素の能力に落ちると fort_e 等のゲートが素通りする）。ゲートつき abilities()
                return [(i, ab, None) for i, ab in self.abilities(src, "trigger")
                        if ab.get("zone", "bz") == zone]
            # 面未定のツインパクト: 各面の能力を面つきで列挙（ゲート類は働かない）
            out = []
            for fi, f in enumerate(d.faces):
                for i, ab in enumerate(f.abilities):
                    if ab["kind"] == "trigger" and ab.get("zone", "bz") == zone:
                        out.append((i, ab, fi))
            return out
        if face >= 0:
            # lki 経路（離れたカード）: その面の能力
            return [(i, ab, face) for i, ab in enumerate(d.face(face).abilities)
                    if ab["kind"] == "trigger" and ab.get("zone", "bz") == zone]
        out = []
        for fi, f in enumerate(d.faces):
            for i, ab in enumerate(f.abilities):
                if ab["kind"] == "trigger" and ab.get("zone", "bz") == zone:
                    out.append((i, ab, fi))
        if not d.faces:
            for i, ab in enumerate(d.abilities):
                if ab["kind"] == "trigger" and ab.get("zone", "bz") == zone:
                    out.append((i, ab, None))
        return out

    def _has_trigger_def(self, defn, face) -> bool:
        """この定義（面が未定ならすべての面）に誘発型能力があるか（定義だけで決まるのでキャッシュする）。"""
        k = ("trig", defn, face)
        r = self._xcache.get(k)
        if r is None:
            d = self.rules.cards[defn]
            fs = [d] + list(d.faces or ())
            r = self._xcache[k] = any(ab["kind"] == "trigger" for f in fs for ab in f.abilities)
        return r

    def _hand_protected(self, p, ev) -> bool:
        """手札破棄の保護（第253弾）: p のバトルゾーンに protect_hand の常在型があり、
        この破棄の起因が相手の呪文またはクリーチャーの能力なら True。"""
        if ev.get("cause_kind") != "spell":
            cd = ev.get("cause_defn")
            if not cd or "creature" not in (self.rules.cards[cd].types or []):
                return False   # 呪文でもクリーチャーの能力でもない起因（ギアやタマシードの能力など）は守らない
        for src in self.bz_tops(p):
            for _, ab in self.abilities(src, "static"):
                if ab.get("protect_hand"):
                    return True
        return False

    def _static_suppressed(self, ctrl, rec):
        """第213弾: 相手のバトルゾーンの常在型 suppress_triggers がこの誘発を抑えるか。
        対象は「ctrl のクリーチャーが出た（move で bz へ）／攻撃した（attack）」出来事で
        誘発する ctrl 側の能力すべて（出た本人の能力に限らない。カードの例示どおり）。"""
        s = self.s
        if rec["ev"] == "move" and rec.get("to") == "bz":
            cls = "enter"
        elif rec["ev"] == "attack":
            cls = "attack"
        else:
            return False
        subj = rec.get("subject")
        if not subj or s.cards[subj[0]].controller != ctrl:
            return False
        st_defns = getattr(self, "_st_defns", None)
        if st_defns is None:
            st_defns = self._st_defns = {dn for dn, cd in self.rules.cards.items()
                                         if any(ab.get("suppress_triggers") for f in (cd.faces or [cd])
                                                for ab in f.abilities if ab.get("kind") == "static")}
        if not st_defns:
            return False
        opp = 1 - ctrl
        for src in self.bz_tops():
            sc = s.cards[src]
            if sc.controller != opp or sc.defn not in st_defns:
                continue
            for _, ab in self.abilities(src, "static"):
                st = ab.get("suppress_triggers")
                if not st or cls not in st["events"]:
                    continue
                if "if" in st and not self.eval_cond(st["if"], {"you": opp, "self": s.ref(src), "event": rec, "vars": {}}):
                    continue
                return True
        return False

    def _collect_triggers(self, rec):
        """誘発チェック。離れた時の誘発で過去の状態を見るのは、その能力を持つカード自身だけ（603.5d）。"""
        s = self.s
        if "_eid" not in rec:      # このイベントの通し番号（first_time の「同じイベント」判定に使う）
            s.ev_seq += 1
            rec["_eid"] = s.ev_seq
        # 発生源は (cid, lki か None, host_only か) の3つ組。host_only は from_under の宿主専用（下記）
        sources = [(c, None, False) for c in self.bz_tops()]
        for c in list(sources):   # G・リンク: グループの全員の誘発型能力が、グループ（1体）として誘発する
            if self.s.cards[c[0]].link:
                sources += [(m, None, False) for m in self.link_members(c[0]) if m != c[0]]
        zt = self.rules.zone_trigger_defs
        if zt:   # 墓地などで機能する誘発型能力（《黒神龍グールジェネレイド》など）
            zs = self._xcache.get(("zt_zones", id(zt)))
            if zs is None or zs[0] is not zt:   # 定義だけで決まる（ゾーンの並びはキャッシュする）
                zs = self._xcache[("zt_zones", id(zt))] = (zt, sorted({z for v in zt.values() for z in v}))
            for z in zs[1]:
                sources += [(c, None, False) for p in (0, 1) for c in self.zlist(z, p) if s.cards[c].defn in zt]
        lki = rec.get("lki")
        if lki and lki["zone"] == "bz" and rec.get("to") != "bz":
            sources.append((rec["subject"][0], lki, False))
        elif lki and lki["zone"] != "bz" and s.cards[rec["subject"][0]].zone != lki["zone"]:
            # 手札等から離れたカード自身の誘発（バンドC1 U26: 「手札から捨てられた時」等）。
            # 移動後のゾーンで zone_trigger として拾われる能力（zone が現在ゾーンと一致するもの）は
            # 通常経路で拾われるため、lki 経路は「能力の zone ＝ 離れる前のゾーン」のものだけを見る
            # （下の発生源フィルタ）。shield→hand の自己誘発（G・ストライク等。能力は zone: hand）は
            # lki の zone（shield）と一致しないので二重発火しない
            sources.append((rec["subject"][0], lki, False))
        host_lki = rec.get("host_lki")
        if host_lki and host_lki["zone"] == "bz" and rec.get("host") \
                and not any(src == rec["host"][0] and not ho
                            for src, _, ho in sources):
            # 下にあったカードの移動では、宿主（上にいたカード）も離れた側として発生源に加える
            # （from_under 機構: 「カードがこのクリーチャーの下を離れた時」）。宿主自身の移動は
            # 宿主自身のレコードで通常どおり収集されるため、ここでは when に from_under を書いた
            # 能力だけを見る（host_only）: 宿主の通常の観測誘発が下のカードの枚数だけ重複しない。
            # ただし宿主がまだバトルゾーンにトップとして残っている場合（下のカードだけが
            # 単独で動いた時）は、通常の発生源（bz_tops）に既に含まれており、ここで加えると
            # from_under 誘発が二重に収集されるため加えない（第299弾で実測・修正）
            sources.append((rec["host"][0], host_lki, True))
        if rec["ev"] == "evolve_base":   # 進化元になる時（第150弾）: 重ねられた側は bz_tops から外れているので、進化元自身を発生源に加える
            sources.append((rec["subject"][0], None, False))
        win = s.windows[-1] if s.windows else 0
        # 定義に誘発型能力が無く、継続的効果で能力を得る道（gain・ダイナモ）も無い発生源は、能力の列挙を省く（結果は同じ空）
        gainable = any(ce["mod"].get("gain") or ce.get("add_from") for ce in s.continuous)
        if not gainable:   # 常在型の mod.gain（第240弾）で誘発を得る道があるか（定義レベルの走査）
            for c in list(s.zones["bz"][0]) + [x for p in (0, 1) for x in s.zones["shield"][p]]:
                d = self.rules.cards[s.cards[c].defn]
                if any(ab.get("kind") == "static" and "gain" in (ab.get("mod") or {})
                       for dd in [d] + list(d.faces or []) for ab in dd.abilities):
                    gainable = True
                    break
        for src, lsrc, host_only in sources:
            if not lsrc and not gainable and not self._has_trigger_def(s.cards[src].defn, s.cards[src].face):
                continue
            if lsrc:
                face = lsrc["face"]
                abs_ = self._trigger_abs(lsrc["defn"], face, lsrc["zone"])
                defn = lsrc["defn"]
            else:
                face = s.cards[src].face
                abs_ = self._trigger_abs(s.cards[src].defn, face, s.cards[src].zone, src)
                defn = s.cards[src].defn
            for i, ab, ab_face in abs_:
                if host_only and "from_under" not in ab["when"]:
                    continue   # 宿主の lki 発生源は from_under 誘発専用（上の host_lki の注記参照）
                if not self._pattern_match(ab["when"], rec, src, lsrc):
                    continue
                ctrl = lsrc["controller"] if lsrc else s.cards[src].controller
                sref = lsrc["ref"] if lsrc else s.ref(src)
                if lsrc is None and s.cards[src].link:   # G・リンク: 発生源はグループの代表として扱う
                    sref = s.ref(self.link_rep(src))
                if "if" in ab and not lsrc and not self.eval_cond(ab["if"], {"you": ctrl, "self": sref, "event": rec, "vars": {}}):
                    continue          # 誘発条件つき（「〜場合」）の能力は、誘発時にも条件を見る（603.4）。離れた時の誘発は解決時だけ
                if rec.get("no_trigger") and lsrc is None and src == rec["subject"][0]:
                    continue          # この移動で出たカード自身の能力は誘発しない（第213弾。move の no_trigger）
                if self._static_suppressed(ctrl, rec):
                    continue          # 相手の常在型 suppress_triggers に抑えられた（第213弾）
                if ab.get("once_per_turn"):   # 「各ターンに一度」: このカード（オブジェクト）のこの能力は1ターンに1回だけ誘発する
                    key = f"once:{sref[0]}:{sref[1]}:{ab_face if ab_face is not None else ''}:{i}"
                    if s.turn_counters.get(key):
                        continue
                    s.turn_counters[key] = 1
                if ab.get("first_time"):      # 「各ターン、はじめて〜した時」: その出来事がこのターン最初に起きた時だけ誘発する
                    key = f"first:{ctrl}:{defn}:{ab_face if ab_face is not None else ''}:{i}"   # 同名カード・同能力で共有する（最初の出来事では全コピーが誘発する）
                    seen = s.turn_counters.get(key)
                    if seen is not None and seen != rec["_eid"]:
                        continue
                    s.turn_counters[key] = rec["_eid"]
                s.seq += 1
                # 待機中の効果は発生源から独立する（110.5a）。発生源の情報は env に持つ
                p = {"pid": s.seq, "kind": "normal", "win": win, "controller": ctrl, "src": sref,
                     "defn": defn, "ab": i, "env": {"you": ctrl, "self": sref, "event": rec, "vars": {}}}
                fe = ab.get("fort_e")
                if isinstance(fe, dict) and fe.get("as") and lsrc is None and not host_only:
                    # フォートE（第168弾）: 条件に合ったタップ済みマナを変数に束ねる
                    # （「タップした〜のいずれかよりパワーが小さい」等の効果で power_of が最大値を読む）
                    p["env"]["vars"][fe["as"]] = self._fort_e_tapped(src, fe)
                if ab_face is not None:
                    p["face"] = ab_face
                elif face >= 0:
                    p["face"] = face
                if i < 0:          # 継続的効果で得た能力は、能力そのものを持たせる
                    p["inline"] = ab
                s.pending.append(p)
                self._apply_trigger_doubling(p, rec, src, lsrc, win)
                w = ab.get("when") or {}
                if (lsrc is None and not host_only and w.get("event") == "move" and w.get("to") == "bz"
                        and w.get("subject") in (None, "self") and rec.get("subject")
                        and src == rec["subject"][0]):
                    # 第270弾: 自身の出た時能力が誘発したことを trigger イベントとして発表する
                    # （「その能力がトリガーした時、自分もその能力を使う」用。魔誕の斬将オルゲイト）。
                    # 観測型（subject が他カード）の誘発や、trigger イベント自体を見る能力は
                    # ここを通らないので再帰しない。2度トリガーの複製分は発表しない（1能力1回）。
                    trig = {"ev": "trigger", "subject": sref, "controller": ctrl,
                            "player": ctrl, "defn": defn, "ab": i, "ability": ab,
                            "from": rec.get("from"), "to": "bz", "reason": rec.get("reason")}
                    if ab_face is not None:
                        trig["face"] = ab_face
                    self._collect_triggers(trig)
        for dl in list(s.delayed):   # 遅延誘発型能力（603.6）
            if self._match_when(dl["when"], rec, dl["env"]):
                s.seq += 1
                env = dict(dl["env"], event=rec, vars=dict(dl["env"].get("vars", {})))
                s.pending.append({"pid": s.seq, "kind": "delayed", "win": win, "controller": dl["controller"],
                                  "src": None, "defn": "", "ab": -1, "env": env, "effect": dl["effect"],
                                  "delayed": dl["id"]})
                if dl["once"]:
                    s.delayed.remove(dl)

    def _trigger_doublers(self, rec):
        """誘発の2度トリガー（第264弾）: 今有効な trigger_double の一覧。
        [(コントローラー, 発生源の参照, defn, 能力添字, 仕様, env, 印の素)] を返す。
        常在型（バトルゾーンのカード自身）と継続的効果（modify で付与されたもの）の両方を見る。
        常在型の if はここで見る（_static_suppressed と同じ eval_cond）。
        affects が self でない常在型と、dynamic（範囲指定）の継続的効果はこの弾では扱わない。"""
        s = self.s
        out = []
        for d in self.bz_tops():
            for i, ab in self.abilities(d, "static"):
                td = (ab.get("mod") or {}).get("trigger_double")
                if not td:
                    continue
                if ab.get("affects") not in (None, "self"):
                    continue
                env = {"you": s.cards[d].controller, "self": s.ref(d), "event": rec, "vars": {}}
                if "if" in ab and not self.eval_cond(ab["if"], env):
                    continue
                out.append((s.cards[d].controller, s.ref(d), s.cards[d].defn, i, td, env,
                            f"tdbl:{d}:{s.cards[d].gen}:{i}"))
        for ce in s.continuous:
            td = (ce.get("mod") or {}).get("trigger_double")
            if not td or not ce.get("affected"):
                continue
            for ref in ce["affected"]:
                if not s.alive(ref):
                    continue
                env = {"you": ce["controller"], "self": list(ref), "event": rec, "vars": {}}
                out.append((ce["controller"], list(ref), s.cards[ref[0]].defn, -1, td, env,
                            f"tdbl:ce:{ce['id']}"))
        return out

    def _apply_trigger_doubling(self, p, rec, src, lsrc, win):
        """収集した誘発 p に対し、有効な trigger_double があれば2度トリガーにする。
        強制はその場で pending を複製する（2つ目の解決は vars を分け、同じ能力の独立した
        解決にする。bazurenda の複数解決と同型）。任意（may）は決定用の pending
        （double_ask）を同じ窓に積む。収集中は決定を尋ねられないためで、対象が先に
        解決されていたら尋ねない。遅延誘発（delayed）は対象外。
        複数の2度トリガーが同じ誘発に合う時は、それぞれが1回ずつ追加する（N+1回。重ね掛けの
        乗算は裁定待ちのためこの弾では扱わない。パイロット記録参照）。"""
        s = self.s
        for ctrl, dref, defn, ab_idx, td, env, key_base in self._trigger_doublers(rec):
            if not self._match_when(td["when"], rec, env):
                continue
            if "source" in td and not self._subject_match(td["source"], src, env, lsrc):
                continue
            if td.get("source_subject") and list(s.ref(src)) != list(rec.get("subject") or []):
                continue
            if td.get("first_per_turn"):
                fkey = f"{key_base}:first"
                if s.turn_counters.get(fkey):
                    continue
                s.turn_counters[fkey] = 1   # 「はじめて」は最初の一致で枠を使い切る（断ってもそのターンはもう来ない）
            once_key = f"{key_base}:once" if td.get("once_per_turn") else None
            if once_key and s.turn_counters.get(once_key):
                continue
            if not td.get("may"):
                if once_key:
                    s.turn_counters[once_key] = 1
                s.seq += 1
                dup = dict(p)
                dup["pid"] = s.seq
                dup["env"] = dict(p["env"], vars=dict(p["env"].get("vars", {})))
                s.pending.append(dup)
                continue
            s.seq += 1
            s.pending.append({"pid": s.seq, "kind": "double_ask", "win": win, "controller": ctrl,
                              "src": dref, "defn": defn, "ab": ab_idx, "env": env,
                              "target": p["pid"], "td": td, "once_key": once_key,
                              "cost": td.get("cost")})

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
    # G・リンクの離脱置換: リンクしたゴッドが離れる時は、グループの中から1枚だけを選んで離す
    li = t.get("link_i", 0)
    chosen = t.setdefault("link_chosen", [])
    while li < len(t["evs"]):
        ev = t["evs"][li]
        t["link_i"] = li + 1
        if ev.get("ev") != "move" or ev.get("to") == "bz" or ev.get("replaced"):
            li += 1
            continue
        cid = ev["subject"][0]
        c = eng.s.cards[cid]
        if not c.link or c.zone != "bz":
            li += 1
            continue
        members = [m for m in eng.link_members(cid) if m not in chosen]
        if len(members) <= 1:
            if members:
                ev["subject"] = eng.s.ref(members[0])
                chosen.append(members[0])
            else:
                t["skip"].append(li)
            li += 1
            continue
        opts = [eng._card_option(m, True) for m in members]
        a, d = eng.ask(t, c.controller, "choose_link_leave", opts)
        if d:
            t["link_i"] = li   # 選び直しのために戻す
            return d
        pick = members[a[0]]
        ev["subject"] = eng.s.ref(pick)
        chosen.append(pick)
        li += 1
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


@task("g_link", GLinkTask)
def h_g_link(eng, t):
    """G・リンクの手順: ゴッドが出た時に行う。（中央）まず自分のゴッドから好きな数だけ
    リンクを外し、その後リンクできるゴッドにリンクする。（左/右）リンク先を選ぶだけ。"""
    s = eng.s
    cid, p = t["cid"], t["player"]
    if s.cards[cid].zone != "bz":
        eng._pop(t)
        return None
    side = eng.link_side(cid)
    spec = eng.link_spec(cid)
    if side is None and spec:
        # 名前指定リンク（第197弾）: 指定名のゴッドがいるグループにリンクする。
        # 同じ名前のカードは1グループに1枚まで（星座が一意に決まる）。
        names = {e["name"] for e in spec}
        my_name = eng.fdef(cid).name
        targets = []
        for c in eng.bz_tops(p):
            if c == cid or eng.fdef(c).name not in names:
                continue
            if any(eng.fdef(m).name == my_name for m in eng.link_members(c)):
                continue
            targets.append(c)
        if not targets:
            eng._pop(t)
            return None
        opts = [eng._card_option(c, True) for c in targets] + [{"key": "pass"}]
        a, d = eng.ask(t, p, "choose_link_target", opts)
        if d:
            return d
        eng._pop(t)
        if opts[a[0]]["key"] != "pass":
            tgt = targets[a[0]]
            gid = s.cards[tgt].link
            if not gid:
                s.seq += 1
                gid = s.seq
                s.mut_card(tgt).link = gid
            s.mut_card(cid).link = gid
            members = eng.link_members(cid)
            eng._push(eng.ev_task([{"ev": "link_established", "subject": s.ref(m),
                                    "controller": s.cards[m].controller} for m in members]))
        return None
    if t["step"] == "start":
        t["step"] = "unlink" if side == 1 else "link"
    if t["step"] == "unlink":   # 中央のみ: リンクを外すカードを1枚ずつ選ぶ（終えたら link へ）
        members = [m for c in eng.bz_tops(p) if s.cards[c].link for m in eng.link_members(c)]
        members = sorted(set(members))
        if members:
            opts = [eng._card_option(m, True) for m in members] + [{"key": "done"}]
            a, d = eng.ask(t, p, "choose_unlink", opts)
            if d:
                return d
            if opts[a[0]]["key"] != "done":
                eng.unlink(members[a[0]])
                return None   # 続けてまた選べる
        t["step"] = "link"
    # リンク先の選択
    targets = []
    for c in eng.bz_tops(p):
        if c == cid or eng.link_side(c) is None:
            continue
        group = eng.link_members(c)
        sides = {eng.link_side(m) for m in group}
        if side in sides:
            continue   # その位置は埋まっている
        if side == 1 and not (sides & {0, 2}):
            continue   # 中央は左か右のゴッドにリンクする
        if side != 1 and 1 not in sides and not ((side == 0 and 2 in sides) or (side == 2 and 0 in sides)):
            continue   # 左は中央か右、右は中央か左のゴッドの隣にリンクする
        targets.append(c)
    if spec:
        # 位置キーワードと名前指定の併記（第250弾: 邪神M・ロマノフ型）: 位置の条件に加え、
        # 指定（名前または「中央/右 G・リンク」等の位置キーワード）に合うゴッドがいる
        # グループだけをリンク先にする。名前指定は位置キーワードを持たないゴッド単体も
        # 指せるので、その場合は位置の占有だけを見て候補に加える（OMG 型）
        names = {e["name"] for e in spec if "name" in e}
        side_ids = {"left": 0, "center": 1, "right": 2}
        want_sides = {side_ids[e["side"]] for e in spec if "side" in e}

        def _spec_ok(c):
            ms = eng.link_members(c)
            return (any(eng.fdef(m).name in names for m in ms)
                    or any(eng.link_side(m) in want_sides for m in ms))

        targets = [c for c in targets if _spec_ok(c)]
        have = set(targets)
        for c in eng.bz_tops(p):
            if c == cid or c in have:
                continue
            ms = eng.link_members(c)
            if not any(eng.fdef(m).name in names for m in ms):
                continue
            if any(eng.fdef(m).name == eng.fdef(cid).name for m in ms):
                continue   # 同名は1グループに1枚まで（第197弾と同型）
            if side in {eng.link_side(m) for m in ms}:
                continue   # 自分の位置は埋まっている
            targets.append(c)
    if not targets:
        eng._pop(t)
        return None
    opts = [eng._card_option(c, True) for c in targets] + [{"key": "pass"}]
    a, d = eng.ask(t, p, "choose_link_target", opts)
    if d:
        return d
    if opts[a[0]]["key"] != "pass":
        tgt = targets[a[0]]
        gid = s.cards[tgt].link
        if not gid:
            s.seq += 1
            gid = s.seq
            s.mut_card(tgt).link = gid
        s.mut_card(cid).link = gid
        members = eng.link_members(cid)
    else:
        members = None
    eng._pop(t)
    if members:
        # リンク成立（第155弾）: 手順の完了時点で、成立したグループの全員を subject とする
        # 合成レコード link_established を出す（第150弾 evolve_base と同型）。誘発収集では
        # グループ全員が発生源になり（_collect_triggers のリンク展開）、「リンクされる側
        # （既に場にいたゴッド）」の「リンクした時」も拾える。リンクを外しただけ・パスした
        # 場合は成立ではないので出さない。
        eng._push(eng.ev_task([{"ev": "link_established", "subject": s.ref(m),
                                "controller": s.cards[m].controller} for m in members]))
    return None


@task("seal_release", SealReleaseTask)
def h_seal_release(eng, t):
    """コマンドが出た時、その持ち主はそのコマンドと同じ文明を持つ自身のカードから封印を1つ墓地に置く（強制）。
    対象がなければ何もしない。"""
    s = eng.s
    p = t["player"]
    cands = [c for c in eng.bz_tops(p) if s.cards[c].seals and set(eng.fdef(c).civs) & set(t["civs"])]
    if not cands:
        eng._pop(t)
        return None
    opts = [{"key": f"card:{s.cards[c].defn}", "cid": c} for c in cands]
    a, d = eng.ask(t, p, "seal_release", opts)
    if d:
        return d
    eng._pop(t)
    host = cands[a[0]]
    seal = s.cards[host].seals[0]
    eng._push(eng.ev_task({"ev": "move", "subject": s.ref(seal), "to": "graveyard", "reason": "seal"}))
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
    if p["kind"] == "double_ask":   # 任意の2度トリガー（第264弾）: 決定は専用タスクへ回す
        # （この場で尋ねると、再入時に order_pending の ask が回答を誤消費するため）
        eng._push({"t": "double_ask", "target": p["target"], "controller": p["controller"],
                   "src": p.get("src"), "once_key": p.get("once_key"),
                   "cost": p.get("cost"), "env": p["env"]})
        return None
    if p["kind"] == "strigger":
        if s.alive(p["src"]):
            tasks = [eng.play_task(p["src"][0], player, True, p.get("face"), st=True)]
            if "s_trigger_x" in eng.cdef(p["src"][0]).keywords:
                # 第269弾 S・トリガーX: ジェネレートの後、自分のクリーチャー1体に
                # コストを支払わずにクロスしてもよい（may）。生成後の姿は self_entered
                # で指す（生成で gen が1増える）。生成されなかった時や自分の
                # クリーチャーがいない時は尋ねない（if の exists 2条件）。
                env = {"you": player, "self": p["src"],
                       "event": {"ev": "use_s_trigger", "player": player,
                                 "subject": p["src"], "controller": player},
                       "vars": {}}
                tasks.append(eng._child([{"op": "if",
                    "cond": {"all": [{"exists": {"ref": "self_entered"}},
                                     {"exists": {"zone": ["bz"], "owner": "you",
                                                 "filter": {"types": ["creature"]}}}]},
                    "then": [{"op": "may", "label": "S・トリガーX：クロスする",
                              "body": [{"op": "cross_free", "gear": {"ref": "self_entered"},
                                        "to": {"zone": ["bz"], "owner": "you",
                                               "filter": {"types": ["creature"]}}}]}]}], env))
            eng._push(*tasks)
    else:
        ab = eng.pending_ability(p)
        env = p["env"]
        if s.trace is not None:
            rec = env.get("event") or {}
            s.trace.append({"turn": s.turn, "src": p["defn"], "ab": p["ab"], "ev": rec.get("ev"), "from": rec.get("from"),
                            "to": rec.get("to"), "reason": rec.get("reason"), "cause": rec.get("cause"),
                            "subject": s.cards[rec["subject"][0]].defn if rec.get("subject") else None})
        if "if" in ab and not eng.eval_cond(ab["if"], env):   # 条件は解決時に確認（603.4, 605.2a）
            return None
        n = 1
        if ab.get("bazurenda") and p.get("src") and s.alive(p["src"]):
            n += s.cards[p["src"][0]].bazurenda   # バズレンダ: [OL]能力を1回+追加で支払った回数使う
        eng._push(*[eng._child(ab["effect"], env) for _ in range(n)])
    return None


@task("double_ask", DoubleAskTask)
def h_double_ask(eng, t):
    """任意の2度トリガーの決定（第264弾）。対象がまだ待機していれば「２度トリガーするか」を
    尋ね、「はい」なら対象の pending を複製し、コストがあれば解決する（複製した誘発の解決より
    先に走る）。対象が先に解決されていたり回数を使い切っていたりしたら何もしない。"""
    s = eng.s
    tgt = next((x for x in s.pending if x["pid"] == t["target"]), None)
    if tgt is None or (t.get("once_key") and s.turn_counters.get(t["once_key"])):
        eng._pop(t)
        return None
    name = eng.fdef(t["src"][0]).name if t.get("src") and s.alive(t["src"]) else ""
    a, d = eng.ask(t, t["controller"], "choose_double_trigger",
                   [{"key": "yes"}, {"key": "no"}],
                   prompt=f"{name}：２度トリガーする" if name else "２度トリガーする")
    if d:
        return d
    eng._pop(t)
    if a[0] == 0:
        if t.get("once_key"):
            s.turn_counters[t["once_key"]] = 1
        s.seq += 1
        dup = dict(tgt)
        dup["pid"] = s.seq
        dup["env"] = dict(tgt["env"], vars=dict(tgt["env"].get("vars", {})))
        s.pending.append(dup)
        if t.get("cost"):   # コストは決定の後に解決する（タップ等。複製した誘発の解決より先に走る）
            eng._push(eng._child(t["cost"], t["env"]))
    return None


@task("lose_replace", LoseReplaceTask)
def h_lose_replace(eng, t):
    """敗北の置換（S-MAX進化など）: 敗北するプレイヤーが置換能力を1つ選んで解決したら敗北はなかったことになる。
    選ばなかった（または解決後に置換源が残っていても、諮問は1回だけ）場合は敗北が確定する。"""
    s = eng.s
    if s.result is not None:
        eng._pop(t)
        return None
    if t["phase"] == 0:
        cands = eng._lose_candidates(t["loser"], t["reason"])
        if not cands:
            s.result = {"winner": 1 - t["loser"], "reason": t["reason"], "turn": s.turn}
            eng._pop(t)
            return None
        opts = [{"key": f"lose_replace:{s.cards[c].defn}:{i}", "cid": c, "ab": i} for c, i, _ in cands] + [{"key": "decline"}]
        ans, d = eng.ask(t, t["loser"], "lose_replace", opts, 0, 1)
        if d:
            return d
        o = opts[ans[0]] if ans else opts[-1]
        if o["key"] == "decline":
            s.result = {"winner": 1 - t["loser"], "reason": t["reason"], "turn": s.turn}
            eng._pop(t)
            return None
        t["phase"] = 1
        ab = dict(eng.abilities(o["cid"], "replace"))[o["ab"]]
        env = {"you": t["loser"], "self": s.ref(o["cid"]),
               "event": {"ev": "lose", "controller": t["loser"]}, "vars": {}}
        eng._push(eng._child(ab["instead"], env))
        return None
    eng._pop(t)   # 置換を解決したので敗北は回避された
    return None


@task("smax_reduce", SmaxReduceTask)
def h_smax_reduce(eng, t):
    """S-MAX進化の2体制限: 残す1体を選び、残りのS-MAX進化クリーチャーをすべて手札に戻す。"""
    s = eng.s
    p = t["player"]
    tops = [c for c in eng.bz_tops(p) if eng.fdef(c).s_max]
    if len(tops) < 2:
        eng._pop(t)
        return None
    ans, d = eng.ask(t, p, "choose_smax_keep", [eng._card_option(c) for c in tops], 1, 1)
    if d:
        return d
    eng._pop(t)
    keep = tops[ans[0]]
    evs = [{"ev": "move", "subject": s.ref(c), "to": "hand", "reason": "return"}
           for c in tops if c != keep]
    if evs:
        eng._push(eng.ev_task(evs))
    return None


@task("enqueue_st", EnqueueStTask)
def h_enqueue_st(eng, t):
    s = eng.s
    eng._pop(t)
    win = s.windows[-1] if s.windows else 0
    for c, face in t["cids"]:
        if s.cards[c].zone == "hand":
            if t.get("strigger"):   # S・トリガーとして宣言された（S・バック経由は付けない）: 「相手がS・トリガーを使った時」の合成レコード（バンドB U7）
                eng._collect_triggers({"ev": "use_s_trigger", "player": t["player"],
                                       "subject": s.ref(c), "controller": t["player"]})
            s.seq += 1
            p = {"pid": s.seq, "kind": "strigger", "win": win, "controller": t["player"],
                 "src": s.ref(c), "defn": s.cards[c].defn, "ab": -1, "env": {}}
            if face is not None:
                p["face"] = face
            s.pending.append(p)
    return None


@task("sback", SbackTask)
def h_sback(eng, t):
    """S・バック: 手札に加わったシールドのカードを捨て、そうした場合だけ、S・バックのカードをコストを支払わずに実行する（S・トリガーと同じ待機の列に入る）。"""
    s = eng.s
    eng._pop(t)
    pairs = [(h, x) for h, x in t["pairs"] if s.cards[x].zone == "hand" and s.cards[h].zone == "hand"]
    if pairs:
        eng._push(eng.ev_task([{"ev": "move", "subject": s.ref(x), "to": "graveyard", "reason": "discard"} for _, x in pairs]),
                  {"t": "enqueue_st", "cids": [[h, None] for h, _ in pairs], "player": t["player"]})
    return None


@task("battle_run", BattleRunTask)
def h_battle_run(eng, t):
    """バトルの勝敗の判定。「バトルが始まる時」の誘発を解決し終えてから、その時点のパワーで行う（701.13）。"""
    eng._pop(t)
    if eng.s.alive(t["att"]) and eng.s.alive(t["tgt"]):
        eng._push(*eng._battle(t["att"], t["tgt"]))
    return None
