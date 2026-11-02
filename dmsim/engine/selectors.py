"""セレクタ・式・条件の評価（効果DSLの「何を」「いくつ」「いつなら」）。"""
from __future__ import annotations


class SelectorMixin:
    def eval_expr(self, x, env):
        if isinstance(x, int):
            return x
        if isinstance(x, dict):
            if "count" in x:
                return len(self.candidates(x["count"], env))
            if "civ_count" in x:   # 対象カード群にある文明の種類数（多色カードは持つ文明をすべて数える）
                return len({cv for c in self.candidates(x["civ_count"], env) for cv in self.chars(c)["civs"]})
            if "link_count" in x:   # このカードがリンクしているカードの枚数（リンクしていなければ1）
                return len(self.link_members(env["self"][0])) if env.get("self") else 0
            if "entered" in x:   # このターン、そのプレイヤーがバトルゾーンに出したクリーチャーの数
                spec = x["entered"]
                lst = self.s.turn_counters.get(f"entered:{self._rel(spec.get('owner', 'you'), env)}", [])
                if spec.get("other") and env.get("self"):   # 「自分の他のクリーチャー」: 自分自身は数えない
                    lst = [c for c in lst if c != env["self"][0]]
                return len(lst)
            if "var" in x:
                v = env.get("vars", {}).get(x["var"], [])
                return v if isinstance(v, int) else len(v)   # 数を数えた変数（ガチンコの勝ち数など）はそのまま
            if "cost_of" in x:   # 変数に束縛したカード（複数なら最大）のコスト
                ids = env.get("vars", {}).get(x["cost_of"], [])
                return max((self.chars(c[0])["cost"] for c in ids), default=0)
            if "race" in x:   # choose_race で選んだ種族名
                return [env.get("races", {})[x["race"]]]
            if "races_of" in x:   # 変数に束縛したカードの種族（「種族をひとつ選ぶ」の代わりに、場のカード1体を選んでその種族とする）
                return sorted({r for c in env.get("vars", {}).get(x["races_of"], []) for r in self.chars(c[0])["races"]})
            if "sum" in x:
                return sum(self.eval_expr(v, env) for v in x["sum"])
        raise ValueError(f"bad expr {x}")

    def count_of(self, v, env):
        """mod の count の評価: セレクタなら体数、式（civ_count / sum 等）ならその値。"""
        if isinstance(v, dict) and ("civ_count" in v or "sum" in v or "var" in v):
            return self.eval_expr(v, env)
        return len(self.candidates(v, env))

    def eval_cond(self, c, env) -> bool:
        if "exists" in c:
            return bool(self.candidates(c["exists"], env))
        if "cmp" in c:
            a, op, b = c["cmp"]
            a, b = self.eval_expr(a, env), self.eval_expr(b, env)
            return {"<": a < b, "<=": a <= b, "==": a == b, ">=": a >= b, ">": a > b}[op]
        if "not" in c:
            return not self.eval_cond(c["not"], env)
        if "all" in c:
            return all(self.eval_cond(x, env) for x in c["all"])
        if "any" in c:
            return any(self.eval_cond(x, env) for x in c["any"])
        if "marked" in c:   # このターンに mark した印があるか（「そのターンに他のファイナル革命を使っていなければ」）
            return bool(self.s.turn_counters.get(c["marked"]))
        if "self_marked" in c:   # このカード自身がこのターンに mark した印があるか（ターボラッシュ）
            return bool(self.s.turn_counters.get(f"{c['self_marked']}:{env['self'][0]}:{env['self'][1]}"))
        if "is_turn" in c:
            return self.s.active == self._rel(c["is_turn"], env)
        if "face_up" in c:   # このカード自身が表向きか（表向きシールドのギャラクシールド等）
            return bool(env.get("self")) and self.s.alive(env["self"]) and self.s.cards[env["self"][0]].face_up == c["face_up"]
        if "hyper" in c:   # このカード自身がハイパーモードか（ハイパー化の旗と Zラッシュの窓の両方を見る）
            return bool(env.get("self")) and self.s.alive(env["self"]) and self.is_hyper(env["self"][0]) == c["hyper"]
        if "alt_paid" in c:   # 代替コストで実行した（「この呪文を[代替]支払って唱えたら」）
            paid = bool(env.get("alt_paid")) or bool((env.get("event") or {}).get("alt"))
            return paid == bool(c["alt_paid"])
        raise ValueError(f"bad cond {c}")

    def filter_match(self, cid: int, f: dict, lki: dict | None = None, base: bool = False) -> bool:
        if base or self._in_static_cond > 1:   # 常在型能力の範囲・入れ子の条件の判定中は特性計算を再帰させない
            d = self.fdef(cid)
            ch = {"power": d.power, "cost": d.cost, "civs": d.civs, "types": d.types, "races": d.races,
                  "keywords": set(d.keywords), "name": d.name}
        else:
            ch = lki["chars"] if lki else self.chars(cid)
        c = self.s.cards[cid]
        if "any_of" in f and not any(self.filter_match(cid, sub, lki, base) for sub in f["any_of"]):
            return False
        if "types" in f and not set(f["types"]) & set(ch["types"]):
            return False
        if "not_types" in f and set(f["not_types"]) & set(ch["types"]):
            return False
        if "race_has" in f and not any(f["race_has"] in r for r in ch["races"]):
            return False
        if "name_has" in f and f["name_has"] not in ch["name"]:
            return False
        if "civs" in f and not set(f["civs"]) & set(ch["civs"]):
            return False
        if "civs_all" in f and not set(f["civs_all"]) <= set(ch["civs"]):
            return False
        if "not_civs" in f and set(f["not_civs"]) & set(ch["civs"]):
            return False
        if "races" in f and not set(f["races"]) & set(ch["races"]):
            return False
        if "name" in f and ch["name"] != f["name"]:
            return False
        if "not_name" in f and ch["name"] == f["not_name"]:
            return False
        for k, key, cmp in (("cost_le", "cost", int.__le__), ("cost_ge", "cost", int.__ge__),
                            ("power_le", "power", int.__le__), ("power_ge", "power", int.__ge__)):
            if k in f and not cmp(ch[key], f[k]):
                return False
        if "multicolor" in f and (len(ch["civs"]) > 1) != f["multicolor"]:
            return False
        if "tapped" in f and (lki["tapped"] if lki else c.tapped) != f["tapped"]:
            return False
        if "face_down" in f and c.face_down != f["face_down"]:
            return False
        if "neo" in f and bool(self.fdef(cid).neo) != f["neo"]:
            return False
        if "vanilla" in f:   # 「カードに能力が書かれていない」: 能力もキーワードも無く、進化・NEO 等の書かれた仕組みも持たない
            d = self.fdef(cid)
            is_v = not d.abilities and not d.keywords and "evolution" not in d.types \
                and not getattr(d, "neo", False) and not getattr(d, "star", False) \
                and not getattr(d, "grave_evo", False) and not getattr(d, "hyper", False)
            if is_v != f["vanilla"]:
                return False
        if "keyword" in f and f["keyword"] not in ch["keywords"]:
            return False
        return True

    def zones_of(self, z) -> list[str]:
        """セレクタ・範囲の zone: 名前 / 名前の配列（どれか） / "any"（バトルゾーン以外を含むすべてのゾーン）。"""
        if z == "any":
            return [k for k in self.rules.zones]
        return [z] if isinstance(z, str) else list(z)

    def _under_base(self, v, env) -> int | None:
        """under_of（クリーチャーの下にあるカード）で指す元クリーチャー。v は "self" / 変数名 / セレクタ。"""
        if isinstance(v, dict):
            cids = self.candidates(v, env)
            return cids[0] if cids else None
        refs = [env.get("self")] if v == "self" else env.get("vars", {}).get(v, [])
        refs = [r for r in refs if r and self.s.alive(r)]
        return refs[0][0] if refs else None

    def candidates(self, sel: dict, env: dict) -> list[int]:
        s = self.s
        if "under_of" in sel:   # 「バトルゾーンのクリーチャーの下にあるカード」（メテオバーンなど）
            base = self._under_base(sel["under_of"], env)
            if base is None:
                return []
            out = [c for c in s.cards[base].under
                   if not (sel.get("other") and env.get("self") and c == env["self"][0])]
            f = sel.get("filter", {})
            if any(isinstance(v, dict) for v in f.values()):   # 式の値は解決時に計算する
                f = {k: self.eval_expr(v, env) if isinstance(v, dict) else v for k, v in f.items()}
            return [c for c in out if self.filter_match(c, f)]
        if "exlife_of" in sel:   # 「EXライフ」シールド: そのクリーチャーに紐付いた、今もシールドゾーンにあるカード
            refs = [env["self"]] if sel["exlife_of"] == "self" else env.get("vars", {}).get(sel["exlife_of"], [])
            refs = [r for r in refs if r and s.alive(r)]
            return [c for p in (0, 1) for c in self.zlist("shield", p)
                    if s.cards[c].exlife_of is not None and list(s.cards[c].exlife_of) in [list(r) for r in refs]]
        if "ref" in sel:
            r = sel["ref"]
            if r == "self":
                refs = [env["self"]]
            elif r == "self_moved":   # このカード自身が離れた後の姿（ちょうど1回ゾーンを移った時だけ）。ラスト・バースト等
                c = s.cards[env["self"][0]]
                return [c.cid] if c.gen == env["self"][1] + 1 and c.zone != "bz" else []
            elif r == "self_entered":   # 実行されてバトルゾーンに出たこのカード自身（B・A・D / J・O・E の終了時処理）
                c = s.cards[env["self"][0]]
                return [c.cid] if c.gen == env["self"][1] + 1 and c.zone == "bz" else []
            elif r == "crossed":   # このクロスギアをクロスしているクリーチャー（303.3a）
                g = s.cards[env["self"][0]].crossed
                refs = [g] if g else []
            elif r in ("event.target", "event.attacker"):   # 攻撃された（攻撃先の）クリーチャー / ブロックされた（攻撃）クリーチャー
                v = env["event"].get(r.split(".")[1])
                refs = [v] if isinstance(v, list) else []
            elif r in ("event.subject", "subject"):   # subject は event.subject の別名（変換データが両形を使う）
                refs = [env["event"]["subject"]]
            else:
                refs = env.get("vars", {}).get(r, [])
            f = sel.get("filter")   # 「その中の水のカード」: 変数のカードをさらに絞る
            return [x[0] for x in refs if s.alive(x) and (not f or self.filter_match(x[0], f))]
        if "owner_of" in sel:   # 「持ち主の〜」「そのプレイヤーの〜」: 変数のカードの持ち主
            refs = env.get("vars", {}).get(sel["owner_of"], [])
            players = [p for p in (s.active, 1 - s.active) if p in {s.cards[r[0]].owner for r in refs}]
        else:
            owner = sel.get("owner", "you")
            # 両プレイヤーのカードを順に処理する時はターン・プレイヤーから（114.2a, 409.1e）
            players = [s.active, 1 - s.active] if owner == "any" else [self._rel(owner, env)]
        out = []
        for p in players:
            lst = []
            zs = self.zones_of(sel["zone"])
            for z in zs:
                part = self.bz_tops(p) if z == "bz" else self.zlist(z, p)
                if "from_top" in sel and len(zs) > 1 and z == "deck":      # 複数ゾーン指定の from_top は山札だけに効く（手札または山札の上1枚）
                    part = part[: self.eval_expr(sel["from_top"], env)]
                lst += part
            if "from_top" in sel and len(zs) == 1:
                lst = lst[: self.eval_expr(sel["from_top"], env)]
            f = sel.get("filter", {})
            if any(isinstance(v, dict) for v in f.values()):   # 式の値は解決時に計算する
                f = {k: self.eval_expr(v, env) if isinstance(v, dict) else v for k, v in f.items()}
            for cid in lst:
                if sel.get("other") and env.get("self") and cid == env["self"][0]:
                    continue
                if self.filter_match(cid, f):
                    out.append(cid)
        return out

    def _card_option(self, cid: int, look: bool = False, **extra) -> dict:
        c = self.s.cards[cid]
        hidden = c.zone in ("shield", "deck") and not look
        o = {"cid": cid, "key": c.zone if hidden else f"{c.zone}:{c.defn}:{int(c.tapped)}",
             "name": "?" if hidden else self.cdef(cid).name}
        o.update(extra)
        return o

    def select(self, t: dict, sel: dict, env: dict):
        """セレクタを解決して (cids, None) か (None, Decision) を返す。
        選べる範囲で可能な限り選ぶ（605.2b）。「すべて」は選んだことにならない。"""
        if "chosen" in t.get("os", {}):
            return t["os"]["chosen"], None
        cands = self.candidates(sel, env)
        # count: any = 「好きな枚数」（0枚から候補の全部まで選べる）。count: all + up_to: true と同じ
        any_n = sel.get("count") == "any" or (sel.get("count") == "all" and sel.get("up_to"))
        if ("ref" in sel and "count" not in sel) or ("under_of" in sel and "count" not in sel) \
                or ("from_top" in sel and "count" not in sel) or (sel.get("count", 1) == "all" and not any_n):
            return cands, None
        n = len(cands) if any_n else self.eval_expr(sel.get("count", 1), env)
        mx = min(n, len(cands))
        mn = 0 if sel.get("up_to") or any_n else mx
        if mx == 0:
            return [], None
        chooser = self._rel(sel.get("chooser", "you"), env)
        # 相手に選ばれないクリーチャーは候補から外す（be_chosen）。自分のカードを自分が選ぶ時は関係ない
        cands = [c for c in cands if self.s.cards[c].zone != "bz" or self.s.cards[c].controller == chooser
                 or self.permits(c, "be_chosen")]
        n = min(n, len(cands))
        if "total_cost_le" in sel or "total_cost_ge" in sel:   # コストの合計制限つきの「好きな数」選択: 1枚ずつ積み上げる
            le = self.eval_expr(sel["total_cost_le"], env) if "total_cost_le" in sel else None
            ge = self.eval_expr(sel["total_cost_ge"], env) if "total_cost_ge" in sel else None
            # 「N体まで」と併記された場合の枚数上限。count が無い「好きな数」は上限なし（従来どおり）
            cap = n if ("count" in sel and not any_n and sel.get("count") != "all") else None
            os = t.setdefault("os", {})
            picked: list[int] = []
            for ans in os.get("tc_answers", []):   # 済んだ段の答えを再生する（ask の再入対策）
                if cap is not None and len(picked) >= cap:
                    break
                rest = [c for c in cands if c not in picked]
                if le is not None:
                    rest = [c for c in rest if sum(self.chars(x)["cost"] for x in picked) + self.chars(c)["cost"] <= le]
                if not ans:
                    break
                picked.append(rest[ans[0]])
            else:
                while True:
                    if cap is not None and len(picked) >= cap:
                        break
                    total = sum(self.chars(x)["cost"] for x in picked)
                    rest = [c for c in cands if c not in picked]
                    if le is not None:
                        rest = [c for c in rest if total + self.chars(c)["cost"] <= le]
                    can_stop = ge is None or total >= ge
                    if ge is not None and not can_stop and total + sum(self.chars(c)["cost"] for c in rest) < ge:
                        can_stop = True   # どう選んでも下限に届かない時は打ち切る
                    if not rest:
                        break
                    a, d = self.ask(t, chooser, "choose_cards",
                                    [self._card_option(c, sel.get("look", False)) for c in rest], 0 if can_stop else 1, 1)
                    if d:
                        return None, d
                    os.setdefault("tc_answers", []).append(a)
                    if not a:
                        break
                    picked.append(rest[a[0]])
            chosen = picked
            t.setdefault("os", {})["chosen"] = chosen
            picked_opp = [c for c in chosen if self.s.cards[c].zone == "bz" and self.s.cards[c].controller != chooser]
            for c in picked_opp:   # 「相手がこのクリーチャーを選んだ時」
                self._collect_triggers({"ev": "choose", "subject": self.s.ref(c), "player": chooser,
                                        "controller": self.s.cards[c].controller})
            return chosen, None
        mx = n
        mn = 0 if sel.get("up_to") or any_n else mx
        if mx == 0:
            return [], None
        a, d = self.ask(t, chooser, "choose_cards", [self._card_option(c, sel.get("look", False)) for c in cands], mn, mx)
        if d:
            return None, d
        chosen = [cands[i] for i in a]
        t.setdefault("os", {})["chosen"] = chosen
        picked = [c for c in chosen if self.s.cards[c].zone == "bz" and self.s.cards[c].controller != chooser]
        for c in picked:   # 「相手がこのクリーチャーを選んだ時」。イベントの束は作らず、誘発だけを待機させる
            self._collect_triggers({"ev": "choose", "subject": self.s.ref(c), "player": chooser,
                                    "controller": self.s.cards[c].controller})
        return chosen, None
