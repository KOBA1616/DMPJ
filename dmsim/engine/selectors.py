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
        raise ValueError(f"bad cond {c}")

    def filter_match(self, cid: int, f: dict, lki: dict | None = None, base: bool = False) -> bool:
        if base:   # 常在型能力の範囲判定中は自分の特性計算を再帰させない
            d = self.cdef(cid)
            ch = {"power": d.power, "cost": d.cost, "civs": d.civs, "types": d.types, "races": d.races,
                  "keywords": set(d.keywords), "name": d.name}
        else:
            ch = lki["chars"] if lki else self.chars(cid)
        c = self.s.cards[cid]
        if "types" in f and not set(f["types"]) & set(ch["types"]):
            return False
        if "civs" in f and not set(f["civs"]) & set(ch["civs"]):
            return False
        if "races" in f and not set(f["races"]) & set(ch["races"]):
            return False
        if "name" in f and ch["name"] != f["name"]:
            return False
        for k, key, cmp in (("cost_le", "cost", int.__le__), ("cost_ge", "cost", int.__ge__),
                            ("power_le", "power", int.__le__), ("power_ge", "power", int.__ge__)):
            if k in f and not cmp(ch[key], f[k]):
                return False
        if "tapped" in f and (lki["tapped"] if lki else c.tapped) != f["tapped"]:
            return False
        if "keyword" in f and f["keyword"] not in ch["keywords"]:
            return False
        return True

    def candidates(self, sel: dict, env: dict) -> list[int]:
        s = self.s
        if "ref" in sel:
            r = sel["ref"]
            if r == "self":
                refs = [env["self"]]
            elif r == "event.subject":
                refs = [env["event"]["subject"]]
            else:
                refs = env.get("vars", {}).get(r, [])
            return [x[0] for x in refs if s.alive(x)]
        owner = sel.get("owner", "you")
        players = [0, 1] if owner == "any" else [self._rel(owner, env)]
        out = []
        for p in players:
            lst = self.bz_tops(p) if sel["zone"] == "bz" else self.zlist(sel["zone"], p)
            if "from_top" in sel:
                lst = lst[: self.eval_expr(sel["from_top"], env)]
            f = sel.get("filter", {})
            for cid in lst:
                if sel.get("other") and env.get("self") and cid == env["self"][0]:
                    continue
                if self.filter_match(cid, f):
                    out.append(cid)
        return out

    def _card_option(self, cid: int, **extra) -> dict:
        c = self.s.cards[cid]
        hidden = c.zone in ("shield", "deck")
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
        if "ref" in sel or "from_top" in sel or sel.get("count", 1) == "all":
            return cands, None
        n = self.eval_expr(sel.get("count", 1), env)
        mx = min(n, len(cands))
        mn = 0 if sel.get("up_to") else mx
        if mx == 0:
            return [], None
        chooser = self._rel(sel.get("chooser", "you"), env)
        a, d = self.ask(t, chooser, "choose_cards", [self._card_option(c) for c in cands], mn, mx)
        if d:
            return None, d
        chosen = [cands[i] for i in a]
        t.setdefault("os", {})["chosen"] = chosen
        return chosen, None
