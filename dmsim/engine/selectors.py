"""セレクタ・式・条件の評価（効果DSLの「何を」「いくつ」「いつなら」）。"""
from __future__ import annotations


class SelectorMixin:
    def eval_expr(self, x, env):
        if isinstance(x, int):
            return x
        if isinstance(x, dict):
            if "count" in x:
                return len(self.candidates(x["count"], env))
            if "var" in x:
                return len(env.get("vars", {}).get(x["var"], []))
            if "sum" in x:
                return sum(self.eval_expr(v, env) for v in x["sum"])
        raise ValueError(f"bad expr {x}")

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
        if "is_turn" in c:
            return self.s.active == self._rel(c["is_turn"], env)
        raise ValueError(f"bad cond {c}")

    def filter_match(self, cid: int, f: dict, lki: dict | None = None, base: bool = False) -> bool:
        if base:   # 常在型能力の範囲判定中は自分の特性計算を再帰させない
            d = self.fdef(cid)
            ch = {"power": d.power, "cost": d.cost, "civs": d.civs, "types": d.types, "races": d.races,
                  "keywords": set(d.keywords), "name": d.name}
        else:
            ch = lki["chars"] if lki else self.chars(cid)
        c = self.s.cards[cid]
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
            elif r == "event.subject":
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
            for z in self.zones_of(sel["zone"]):
                lst += self.bz_tops(p) if z == "bz" else self.zlist(z, p)
            if "from_top" in sel:
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
        if ("ref" in sel and "count" not in sel) or ("under_of" in sel and "count" not in sel) \
                or ("from_top" in sel and "count" not in sel) or sel.get("count", 1) == "all":
            return cands, None
        n = self.eval_expr(sel.get("count", 1), env)
        mx = min(n, len(cands))
        mn = 0 if sel.get("up_to") else mx
        if mx == 0:
            return [], None
        chooser = self._rel(sel.get("chooser", "you"), env)
        # 相手に選ばれないクリーチャーは候補から外す（be_chosen）。自分のカードを自分が選ぶ時は関係ない
        cands = [c for c in cands if self.s.cards[c].zone != "bz" or self.s.cards[c].controller == chooser
                 or self.permits(c, "be_chosen")]
        n = min(n, len(cands))
        mx = n
        mn = 0 if sel.get("up_to") else mx
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
