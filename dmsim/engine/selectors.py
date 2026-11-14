"""セレクタ・式・条件の評価（効果DSLの「何を」「いくつ」「いつなら」）。"""
from __future__ import annotations

from .state import rng_below
from .registry import read_only


def _civ_list(v) -> list:
    """filter の civs 系の値の正規化: 式の前評価で文明名の文字列になった場合（{declared: c} 等）は
    単一文明のリストとして扱う（バンドB U3）。文字列でもリストでもない値（未宣言の既定値など）は空＝一致しない。"""
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return v
    return []


class SelectorMixin:
    def crossed_gears(self, ref) -> list[int]:
        """ref [cid, gen] にクロスされている、バトルゾーンのクロスギア（303.3）。
        参照は gen まで完全一致で見る。宿主が離れた後の古い参照（LKI）にも当たる。"""
        if not ref:
            return []
        want = list(ref)
        return [cid for p in (0, 1) for cid in self.bz_tops(p)
                if self.s.cards[cid].crossed is not None and list(self.s.cards[cid].crossed) == want]

    def crossed_host(self, ref) -> int | None:
        """ギアの参照 ref がクロスしているクリーチャーの cid。クロスしていなければ None。"""
        if not ref:
            return None
        g = self.s.cards[ref[0]].crossed
        return g[0] if g is not None and self.s.alive(g) else None

    def _refs_of(self, v, env) -> list:
        """crossed_to / host_of の参照指定（"self" / 変数名 / セレクタ）から参照の列を作る。"""
        if isinstance(v, dict):
            return [self.s.ref(c) for c in self.candidates(v, env)]
        refs = [env.get("self")] if v == "self" else env.get("vars", {}).get(v, [])
        # alive で落とさない: crossed_to / host_of は宿主が離れた後の LKI 参照で
        # 引くのが用途（crossed_gears が gen 完全一致で照合する。第195弾:
        # 破壊されたクリーチャーにクロスしてあったギアを拾うため）
        return [r for r in refs if r]

    def _expr_refs(self, v, env):
        """cost_of / power_of の参照先を ref のリストにする。
        値は変数名（文字列）または {ref: 名前}。 "self" は自分自身を指す。
        "event.<キー>" はイベントレコードの参照（event.opponent 等。バンドB U7 の基盤 expr-event-ref）。
        "crossed" はこのクロスギアをクロスしているクリーチャー（第170弾）。"""
        name = v.get("ref") if isinstance(v, dict) else v
        if name == "self":
            return [env["self"]] if env.get("self") else []
        if name == "crossed":
            if env.get("self"):
                g = self.s.cards[env["self"][0]].crossed
                return [g] if g else []
            return []
        if isinstance(name, str) and name.startswith("event.") and env.get("event"):
            r = env["event"].get(name.split(".", 1)[1])
            return [r] if isinstance(r, list) else []
        return list(env.get("vars", {}).get(name, []))

    def _chars_val(self, cid: int, key: str):
        """参照先の特性1項目。評価中のカード（_chars_busy）は印刷特性で見る（再入防止。第145弾の
        distinct_cost_count と同じ作法。affects フィルタの races_of: crossed 等が評価中の宿主を指す時に要る）"""
        if cid in self._chars_busy:
            d = self.fdef(cid)
            return {"cost": d.cost, "power": d.power, "name": d.name, "races": list(d.races)}[key]
        ch = self.chars_ro(cid)
        return list(ch["races"]) if key == "races" else ch[key]

    def eval_expr(self, x, env):
        if isinstance(x, int):
            return x
        if isinstance(x, dict):
            if "count" in x:
                return len(self.candidates(x["count"], env))
            if "civ_count" in x:   # 対象カード群にある文明の種類数（多色カードは持つ文明をすべて数える）
                return len({cv for c in self.candidates(x["civ_count"], env) for cv in self.chars_ro(c)["civs"]})
            if "distinct_cost_count" in x:   # 対象カード群にあるコストの種類数（同じコストは1つに数える。第145弾、バラバラエティ）
                # 数える対象に発生源自身が含まれるのがこのファミリーの常形（「自分のエレメント」「自分のクリーチャー」）で、
                # 素朴に chars を呼ぶと自身の常在条件・ブレイク数の評価から再入して無限再帰する（candidates の列挙中の
                # filter_match 経由でも再入する）。評価中（_distinct_costing）のカードは定義（印刷）特性・コストで見る。
                # chars の cost はリンク統合時を除き印刷コストと同一なので、数え方そのものは変わらない。
                added = []
                src = (env.get("self") or [None])[0]
                if src is not None and src not in self._distinct_costing:
                    self._distinct_costing.add(src)
                    added.append(src)
                try:
                    costs = set()
                    for c in self.candidates(x["distinct_cost_count"], env):
                        if c in self._distinct_costing:
                            costs.add(self.fdef(c).cost)
                            continue
                        self._distinct_costing.add(c)
                        try:
                            costs.add(self.chars_ro(c)["cost"])
                        finally:
                            self._distinct_costing.discard(c)
                    return len(costs)
                finally:
                    for c in added:
                        self._distinct_costing.discard(c)
            if "total_cost" in x:   # 対象カード群のコストの合計（公開集合の保持。バンドC1 U39）
                return sum(self.chars(c)["cost"] for c in self.candidates(x["total_cost"], env))
            if "total_power" in x:   # 対象カード群のパワーの合計（バンドC1 U39。U17 の「下のカードの合計パワー」でも使う）
                return sum(self.chars(c)["power"] for c in self.candidates(x["total_power"], env))
            if "link_count" in x:   # このカードがリンクしているカードの枚数（リンクしていなければ1）
                return len(self.link_members(env["self"][0])) if env.get("self") else 0
            if "seals" in x:   # そのプレイヤーの封印の総数（自分のカードに付いている封印を全部数える）
                p = self._rel(x["seals"].get("owner", "you"), env)
                return sum(len(self.s.cards[c].seals) for c in self.bz_tops(p))
            if "seals_on" in x:   # self に付いている封印の数
                return len(self.s.cards[env["self"][0]].seals) if env.get("self") else 0
            if "crossed_count" in x:   # そのカードにクロスされているギアの数（第170弾）。破壊された時の LKI 参照（古い gen）にも当たる
                return sum(len(self.crossed_gears(r)) for r in self._expr_refs(x["crossed_count"], env))
            if "bundles" in x:   # シールドの束の数（束の中身のカードは数えない。113.2）。face_up: true は「表向きのカードを含む束」だけ、false は「表向きのカードを含まない束」だけを数える
                spec = x["bundles"]
                tops = self.zlist("shield", self._rel(spec.get("owner", "you"), env))
                if "face_up" not in spec:
                    return len(tops)
                want = bool(spec["face_up"])
                return sum(1 for t in tops
                           if any(self.s.cards[c].face_up for c in [t] + self.s.cards[t].under) == want)
            if "entered" in x:   # このターン、そのプレイヤーがバトルゾーンに出したクリーチャーの数
                spec = x["entered"]
                lst = self.s.turn_counters.get(f"entered:{self._rel(spec.get('owner', 'you'), env)}", [])
                if spec.get("other") and env.get("self"):   # 「自分の他のクリーチャー」: 自分自身は数えない
                    lst = [c for c in lst if c != env["self"][0]]
                return len(lst)
            if "drew" in x:   # このターン、そのプレイヤーがカードを引いた枚数（第142弾）
                spec = x["drew"]
                return self.s.turn_counters.get(f"drew:{self._rel(spec.get('owner', 'you'), env)}", 0)
            if "var" in x:
                v = env.get("vars", {}).get(x["var"], [])
                return v if isinstance(v, int) else len(v)   # 数を数えた変数（ガチンコの勝ち数など）はそのまま
            if "declared" in x:   # 宣言した値（choose_number / choose_name / choose_civ。GameState.declares から読む。バンドC2 U97）
                return self.s.declares.get(x["declared"], 0)   # 未宣言は 0（数・名前・文明のどの読みでも「一致しない」側に倒れる既定値）
            if "turn_count" in x:   # このターンに〜した回数（履歴カウンタ基盤。バンドC1 U19）
                return self._turn_count(x["turn_count"], env)
            if "used_count" in x:   # 「使った」履歴（唱えた呪文＋via: generate で実行したカード）の特性つき数え（バンドC1 U19）
                spec = x["used_count"]
                lst = self.s.turn_counters.get(f"hist:used:{self._rel(spec.get('owner', 'you'), env)}", [])
                f = spec.get("filter")
                return len(lst) if not f else sum(1 for snap in lst if self._snapshot_match(snap, f))
            if "prev_shield_added" in x:   # 前のターンに、そのプレイヤーがシールドを加えた回数（バンドB U18。prev_counters の hist:shield_put を読む）
                spec = x["prev_shield_added"]
                return self.s.prev_counters.get(f"hist:shield_put:{self._rel(spec.get('owner', 'you'), env)}", 0)
            if "cost_of" in x:   # 参照カード（複数なら最大）のコスト
                return max((self._chars_val(c[0], "cost") for c in self._expr_refs(x["cost_of"], env)), default=0)
            if "power_of" in x:   # 参照カード（複数なら最大）の現在パワー（第116弾で追加。cost_of の対）
                return max((self._chars_val(c[0], "power") for c in self._expr_refs(x["power_of"], env)), default=0)
            if "name_of" in x:   # 参照カードのカード名（「そのクリーチャーと同じ名前の〜」フィルタ用、第140弾。複数なら先頭）
                refs = self._expr_refs(x["name_of"], env)
                return self._chars_val(refs[0][0], "name") if refs else ""
            if "race" in x:   # choose_race で選んだ種族名
                return [env.get("races", {})[x["race"]]]
            if "races_of" in x:   # 変数に束縛したカードの種族（「種族をひとつ選ぶ」の代わりに、場のカード1体を選んでその種族とする）。"self" / "crossed"（このギアをクロスしているクリーチャー。第170弾）も可
                return sorted({r for c in self._expr_refs(x["races_of"], env) for r in self._chars_val(c[0], "races")})
            if "sum" in x:
                return sum(self.eval_expr(v, env) for v in x["sum"])
            if "mul" in x:
                r = 1
                for v in x["mul"]:
                    r *= self.eval_expr(v, env)
                return r
        raise ValueError(f"bad expr {x}")

    # count_of が式として評価する単一キーの辞書（バンドB U18 の一般化: 履歴式も mod の count に書ける）
    _EXPR_KEYS = {"count", "civ_count", "distinct_cost_count", "link_count", "seals", "seals_on",
                  "crossed_count",
                  "entered", "drew", "turn_count", "used_count", "prev_shield_added",
                  "var", "cost_of", "power_of", "name_of", "race", "races_of", "sum", "mul", "bundles", "declared",
                  "total_cost", "total_power"}

    # 従来から複合キー辞書（{distinct_cost_count: ..., base: 0} 等）でも式として読んでいたキー。
    # 単一キー制限をかけると variety breaker の mod が壊れるため、これらは従来どおりキー有無で判定する
    _LEGACY_EXPR_KEYS = {"civ_count", "distinct_cost_count", "sum", "var", "bundles"}

    def count_of(self, v, env):
        """mod の count の評価: セレクタなら体数、式（civ_count / distinct_cost_count / sum / 履歴式等）ならその値。"""
        if isinstance(v, dict) and (any(k in v for k in self._LEGACY_EXPR_KEYS)
                                    or (len(v) == 1 and next(iter(v)) in self._EXPR_KEYS)):
            return self.eval_expr(v, env)
        return len(self.candidates(v, env))

    def _turn_count(self, spec: dict, env) -> int:
        """式 {turn_count: spec} の評価。記録は events の _record_history が turn_counters の hist: キーに集約する。
        kind: attack は攻撃クリーチャーの cid リスト（hist:attackers）から数える（other / filter 対応のため）。
        attack_by / attack_on はクリーチャー単位（ref で指す）。broke_by_self は env の self 固定（owner を持たない）。"""
        s = self.s
        kind = spec["kind"]
        if kind in ("attack_by", "attack_on"):
            return sum(s.turn_counters.get(f"hist:{kind}:{r[0]}", 0)
                       for r in self._expr_refs(spec.get("ref"), env))
        if kind == "broke_by_self":
            return s.turn_counters.get(f"hist:broke_by:{env['self'][0]}", 0) if env.get("self") else 0
        if kind == "broke_by_self_attack":   # 第185弾: その攻撃中に self がブレイクした枚数（broke_count の攻撃番号区切り）
            return s.turn_counters.get(f"broke_count:{env['self'][0]}:atk{s.turn_counters.get('current_attack', 0)}", 0) if env.get("self") else 0
        owner = spec.get("owner", "you")
        players = (0, 1) if owner == "any" else (self._rel(owner, env),)
        if kind == "attack":
            total = 0
            for p in players:
                lst = list(s.turn_counters.get(f"hist:attackers:{p}", []))
                if spec.get("other") and env.get("self"):
                    lst = [c for c in lst if c != env["self"][0]]
                f = spec.get("filter")
                if f:
                    if any(isinstance(v, dict) for v in f.values()):   # 式の値は問い合わせ時点の env で計算する
                        f = {k: self.eval_expr(v, env) if isinstance(v, dict) else v for k, v in f.items()}
                    lst = [c for c in lst if self.filter_match(c, f, env=env)]   # フィルタは問い合わせ時点の特性で照合する（バンドA の設計既定）
                total += len(lst)
            return total
        return sum(s.turn_counters.get(f"hist:{kind}:{p}", 0) for p in players)

    @staticmethod
    def _snapshot_match(snap: dict, f: dict) -> bool:
        """「使った」履歴の特性スナップショット（印刷特性 {cost, types, civs}）への簡易照合（バンドC1 U19）。
        filter の特性部分（types / civs / cost_ge / cost_le）だけを見る。"""
        if "types" in f and not set(f["types"]) & set(snap["types"]):
            return False
        if "civs" in f and not set(f["civs"]) & set(snap["civs"]):
            return False
        if "cost_ge" in f and snap["cost"] < f["cost_ge"]:
            return False
        if "cost_le" in f and snap["cost"] > f["cost_le"]:
            return False
        return True

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
        if "power_ge" in c:   # このカード自身のパワーが N 以上か（常在型の条件用）。特性計算の再入で無限再帰しないよう、印刷パワー＋他の常在修整で見る（_threshold_power）
            return bool(env.get("self")) and self.s.alive(env["self"]) \
                and self._threshold_power(env["self"][0]) >= c["power_ge"]
        if "marked" in c:   # mark した印があるか（「そのターンに他のファイナル革命を使っていなければ」）。
            # 辞書形 {name, scope} はスコープつき（バンドB 基盤 mark-scope）: scope: game は game_counters を読み、ターン開始で消えない
            v = c["marked"]
            if isinstance(v, dict):
                scope = v.get("scope", "turn")
                store = self.s.game_counters if scope == "game" else self.s.turn_counters
                return bool(store.get(self._mark_key(v["name"], scope, env)))
            return bool(self.s.turn_counters.get(v))
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
        if "vivid_paid" in c:   # ビビッドローで実行した（第54弾。「ビビッドロー能力を使って唱えていれば」）
            paid = bool(env.get("vivid_paid")) or bool((env.get("event") or {}).get("vivid"))
            return paid == bool(c["vivid_paid"])
        if "ddd_paid" in c:   # D・D・D で実行した（第149弾。「この呪文を『D・D・D』で唱えたなら」）
            paid = bool(env.get("ddd_paid")) or (env.get("event") or {}).get("via") == "d_d_d"
            return paid == bool(c["ddd_paid"])
        raise ValueError(f"bad cond {c}")

    def filter_match(self, cid: int, f: dict, lki: dict | None = None, base: bool = False,
                     env: dict | None = None) -> bool:
        if base or self._in_static_cond > 1 or cid in self._distinct_costing or cid in self._chars_busy:   # 常在型能力の範囲・入れ子の条件の判定中は特性計算を再帰させない（_distinct_costing は第145弾の数え中。_chars_busy は第170弾: 自身の常在型の if が自身をフィルタで見る時）
            d = self.fdef(cid)
            ch = {"power": d.power, "cost": d.cost, "civs": d.civs, "types": d.types, "races": d.races,
                  "keywords": set(d.keywords), "name": d.name, "names": [d.name]}
        else:
            ch = lki["chars"] if lki else self.chars(cid)
        names = ch.get("names") or [ch["name"]]   # 名前の集合（主名＋add_names。バンドC2 U97）
        c = self.s.cards[cid]
        is_sealed = c.zone == "bz" and bool(c.seals)
        if "sealed" in f:
            if is_sealed != bool(f["sealed"]):
                return False
        elif is_sealed and lki is None and not base and not getattr(self, "_seal_ok", 0):
            return False   # 封印されているクリーチャーは無視される（封印を対象にする効果だけが sealed で指す）
        if "any_of" in f and not any(self.filter_match(cid, sub, lki, base, env) for sub in f["any_of"]):
            return False
        if "types" in f and not set(f["types"]) & set(ch["types"]):
            return False
        if "not_types" in f and set(f["not_types"]) & set(ch["types"]):
            return False
        if "race_has" in f and not any(f["race_has"] in r for r in ch["races"]):
            return False
        if "not_race_has" in f:
            pats = f["not_race_has"] if isinstance(f["not_race_has"], list) else [f["not_race_has"]]
            if any(p in r for p in pats for r in ch["races"]):
                return False
        if "name_has" in f and not any(f["name_has"] in nm for nm in names):
            return False
        if "twinpact" in f and bool(self.cdef(cid).faces) != bool(f["twinpact"]):
            return False
        if "vividraw" in f:
            d = self.cdef(cid)
            has = bool(d.vividraw) or any(fc.vividraw for fc in d.faces)
            if has != bool(f["vividraw"]):
                return False
        if "fushigi" in f:
            d = self.cdef(cid)
            has = bool(d.fushigi) or any(fc.fushigi for fc in d.faces)
            if has != bool(f["fushigi"]):
                return False
        if "civs" in f and not set(_civ_list(f["civs"])) & set(ch["civs"]):
            return False
        if "civs_all" in f and not set(_civ_list(f["civs_all"])) <= set(ch["civs"]):
            return False
        if "not_civs" in f and set(_civ_list(f["not_civs"])) & set(ch["civs"]):
            return False
        if "races" in f and not set(f["races"]) & set(ch["races"]):
            return False
        if "name" in f and f["name"] not in names:   # 追加の名前（add_names）にも当たる
            return False
        if "not_name" in f and f["not_name"] in names:
            return False
        for k, key, cmp in (("cost_le", "cost", int.__le__), ("cost_ge", "cost", int.__ge__),
                            ("power_le", "power", int.__le__), ("power_ge", "power", int.__ge__)):
            if k in f and not cmp(ch[key], f[k]):
                return False
        if "spell_cost_le" in f or "spell_cost_ge" in f:   # 呪文面（ツインパクトの呪文側）のコスト（第184弾）
            d = self.cdef(cid)
            sp = next((fc for fc in d.faces if "spell" in fc.types), None)
            if sp is None:
                return False
            if "spell_cost_le" in f and not sp.cost <= f["spell_cost_le"]:
                return False
            if "spell_cost_ge" in f and not sp.cost >= f["spell_cost_ge"]:
                return False
        if "multicolor" in f and (len(ch["civs"]) > 1) != f["multicolor"]:
            return False
        if "colorless" in f and (len(ch["civs"]) == 0) != f["colorless"]:
            return False
        if "tapped" in f and (lki["tapped"] if lki else c.tapped) != f["tapped"]:
            return False
        if any(k in f for k in ("crossed", "crossed_ge", "crossed_le", "crossed_name")):   # クロス状態（第170弾）
            # クリーチャー: そのカードにクロスされているギア。クロスギア自身: クロスされているか（crossed は自分がクロスされているか、枚数系は0）。
            # lki（離れた後の姿）がある時は離れる前の参照で数える（破壊された時の「クロスされていたギアの数」）。
            ref = lki["ref"] if lki else self.s.ref(cid)
            gears = self.crossed_gears(ref)
            if "cross_gear" in ch["types"]:
                is_crossed = c.crossed is not None and self.s.alive(c.crossed)
                n = 0
            else:
                is_crossed = bool(gears)
                n = len(gears)
            if "crossed" in f and is_crossed != bool(f["crossed"]):
                return False
            if "crossed_ge" in f and n < f["crossed_ge"]:
                return False
            if "crossed_le" in f and n > f["crossed_le"]:
                return False
            if "crossed_name" in f and f["crossed_name"] not in {nm for g in gears for nm in self.chars_ro(g)["names"]}:
                return False
        if "face_down" in f and c.face_down != f["face_down"]:
            return False
        if "face_up" in f and bool(c.face_up) != bool(f["face_up"]):
            return False   # シールドゾーンの「表向きのカード」を絞る（シールド・ゴーの条件用）
        if "neo" in f and bool(self.fdef(cid).neo) != f["neo"]:
            return False
        if "evolution" in f and ("evolution" in self.fdef(cid).types) != bool(f["evolution"]):
            return False   # 「進化ではないクリーチャー」等（進化はタイプで表す）
        if "evo_source_of" in f:   # 「そのクリーチャーの進化元になれるカード」（第177弾・超魂レイド）。
            # 対象は env の参照（"self" / 変数名）で指定する。env が無い文脈（常在型の条件・
            # when の照合など）では解決できないので一致しない。判定は _evo_sources と同型:
            # クリーチャーであること＋対象の evolve_from（zone を除く）のいずれかに合うこと。
            if env is None:
                return False
            refs = self._refs_of(f["evo_source_of"], env)
            if not refs:
                return False
            if "creature" not in ch["types"]:
                if base or cid in self._chars_busy or self._in_static_cond > 1:
                    return False
                if not self.permits(cid, "evolve_base"):
                    return False
            ef = self.fdef(refs[0][0]).evolve_from
            if ef is None:
                return False
            efs = ef if isinstance(ef, list) else [ef]
            if not any(self.filter_match(cid, {k: v for k, v in sub.items() if k != "zone"},
                                         lki, base, env) for sub in efs):
                return False
        if "linked_god" in f:
            linked = self.link_side(cid) is not None and len(self.link_members(cid)) >= 2
            if linked != bool(f["linked_god"]):
                return False   # 「リンクしているゴッド」: リンク位置を持ち、実際に2体以上でリンクしている
        if "fortifying" in f:   # 「シールドを要塞化している城」（第178弾）: この城が今シールドを要塞化している
            is_f = c.fortifies is not None and self.s.alive(c.fortifies) \
                and self.s.cards[c.fortifies[0]].zone == "shield"
            if is_f != bool(f["fortifying"]):
                return False
        if "fortified" in f:   # 「要塞化されたシールド」（第178弾）: どの城かに要塞化されている
            forts = [x for x in self.bz_tops()
                     if self.s.cards[x].fortifies is not None and list(self.s.cards[x].fortifies) == list(self.s.ref(cid))]
            if bool(forts) != bool(f["fortified"]):
                return False
        if "entered_this_turn" in f:
            if (c.entered_turn == self.s.turn) != bool(f["entered_this_turn"]):
                return False   # 「このターン中に出た」: entered_turn はバトルゾーンに出たターン（それ以外は -1）
        if "mugen_climb" in f and (self.fdef(cid).mugen_climb is not None) != bool(f["mugen_climb"]):
            return False   # 「『ムゲンクライム』能力を持つカード」
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

    @read_only
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
            return [c for c in out if self.filter_match(c, f, env=env)]
        if "bundle_of" in sel:   # 「シールドの束に含まれるカード」（第148弾）: 解決した束（トップ）ごとに [トップ]＋その下すべてを候補にする。覆われている表向きカードも数え・選択の対象になる（ユーザー決定 2026-11-08）
            v = sel["bundle_of"]
            if isinstance(v, dict):
                tops = self.candidates(v, env)
            else:
                refs = [env.get("self")] if v == "self" else env.get("vars", {}).get(v, [])
                tops = [r[0] for r in refs if r and s.alive(r)]
            out = []
            for tp in tops:
                while s.cards[tp].top_of >= 0:   # 束の中のカードが指されたら、その束のトップへたどる
                    tp = s.cards[tp].top_of
                for c in [tp] + list(s.cards[tp].under):
                    if c not in out:
                        out.append(c)
            f = sel.get("filter", {})
            if any(isinstance(x, dict) for x in f.values()):   # 式の値は解決時に計算する
                f = {k: self.eval_expr(x, env) if isinstance(x, dict) else x for k, x in f.items()}
            return [c for c in out if self.filter_match(c, f, env=env)]
        if "exlife_of" in sel:   # 「EXライフ」シールド: そのクリーチャーに紐付いた、今もシールドゾーンにあるカード
            refs = [env["self"]] if sel["exlife_of"] == "self" else env.get("vars", {}).get(sel["exlife_of"], [])
            refs = [r for r in refs if r and s.alive(r)]
            return [c for p in (0, 1) for c in self.zlist("shield", p)
                    if s.cards[c].exlife_of is not None and list(s.cards[c].exlife_of) in [list(r) for r in refs]]
        if "castle_of" in sel:   # 「その城が要塞化しているシールド」（第178弾）: 城の fortifies が今もシールドゾーンにあるもの
            refs = [env["self"]] if sel["castle_of"] == "self" else env.get("vars", {}).get(sel["castle_of"], [])
            refs = [r for r in refs if r and s.alive(r)]
            out = []
            for r in refs:
                f = s.cards[r[0]].fortifies
                if f is not None and s.alive(f) and s.cards[f[0]].zone == "shield" and f[0] not in out:
                    out.append(f[0])
            return out
        if "crossed_to" in sel:   # 「そのクリーチャーにクロスされているクロスギア」（第170弾）。値は "self" / 変数名 / セレクタ
            out = []
            for r in self._refs_of(sel["crossed_to"], env):
                for g in self.crossed_gears(r):
                    if g not in out:
                        out.append(g)
            f = sel.get("filter", {})
            if any(isinstance(v, dict) for v in f.values()):   # 式の値は解決時に計算する
                f = {k: self.eval_expr(v, env) if isinstance(v, dict) else v for k, v in f.items()}
            return [c for c in out if self.filter_match(c, f, env=env)]
        if "host_of" in sel:   # 「そのクロスギアをクロスしているクリーチャー」（第170弾）。値は "self" / 変数名 / セレクタ
            out = []
            for r in self._refs_of(sel["host_of"], env):
                h = self.crossed_host(r)
                if h is not None and h not in out:
                    out.append(h)
            f = sel.get("filter", {})
            if any(isinstance(v, dict) for v in f.values()):   # 式の値は解決時に計算する
                f = {k: self.eval_expr(v, env) if isinstance(v, dict) else v for k, v in f.items()}
            return [c for c in out if self.filter_match(c, f, env=env)]
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
            elif r == "fuel":   # 第189弾: 召喚時の支払い行動（opt_reduce.do）で選んだカード
                refs = [list(x) for x in s.cards[env["self"][0]].summon_fuel]
            elif r == "crossed":   # このクロスギアをクロスしているクリーチャー（303.3a）
                g = s.cards[env["self"][0]].crossed
                refs = [g] if g else []
            elif r in ("event.target", "event.attacker", "event.opponent", "event.shield", "event.top", "event.under"):   # 攻撃された（攻撃先の）クリーチャー / ブロックされた（攻撃）クリーチャー / バトルの相手 / ブレイクされるシールド（第146弾）/ 進化で上に乗ったクリーチャー（第150弾）/ 離れる時に下にあったクリーチャー（leave_under_untap）
                v = env["event"].get(r.split(".")[1])
                refs = [v] if isinstance(v, list) else []
            elif r in ("event.subject", "subject"):   # subject は event.subject の別名（変換データが両形を使う）
                refs = [env["event"]["subject"]]
            else:
                refs = env.get("vars", {}).get(r, [])
            f = sel.get("filter")   # 「その中の水のカード」: 変数のカードをさらに絞る
            # zone を併記したら、そのゾーンにあるものだけ（第169弾。「そのカードが手札にあれば捨てる」
            # のような、移動済みかどうかを区別する選択に使う。従来は zone が無視されていたが、
            # ref＋zone の併記は実データに無く、素の読みどおりに絞る）
            zs = self.zones_of(sel["zone"]) if "zone" in sel else None
            return [x[0] for x in refs if s.alive(x) and (not f or self.filter_match(x[0], f, env=env))
                    and (zs is None or s.cards[x[0]].zone in zs)]
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
                if self.filter_match(cid, f, env=env):
                    out.append(cid)
        if "exclude" in sel:   # 「〜以外の」参照除外（C1 U35）: ゾーン経路の候補（filter 適用後）から、exclude が指すカードをすべて引く。ref／under_of 等の特殊経路には適用しない
            ex = sel["exclude"]
            excluded = set()
            for sub in (ex if isinstance(ex, list) else [ex]):
                excluded.update(self.candidates(sub, env))
            out = [c for c in out if c not in excluded]
        if "extremal" in sel and out:   # 「パワーが一番小さい／大きいクリーチャー」（第162弾）: 候補の中で現在パワー（常在型の修整込み）が最小／最大のものだけに絞る。同点はすべて残し、どちらを選ぶかは chooser の選択に委ねる
            pw = {c: self.chars_ro(c)["power"] for c in out}
            edge = min(pw.values()) if sel["extremal"] == "min_power" else max(pw.values())
            out = [c for c in out if pw[c] == edge]
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
                or ("bundle_of" in sel and "count" not in sel) \
                or ("crossed_to" in sel and "count" not in sel) or ("host_of" in sel and "count" not in sel) \
                or ("from_top" in sel and "count" not in sel) or (sel.get("count", 1) == "all" and not any_n):
            return cands, None
        n = len(cands) if any_n else self.eval_expr(sel.get("count", 1), env)
        mx = min(n, len(cands))
        mn = 0 if sel.get("up_to") or any_n else mx
        if mx == 0:
            return [], None
        # 第185弾: chooser: random（「見ないで選ぶ」）は決定を出さず、効果の使用者が
        # 無作為に選ぶ（従来は _rel が KeyError になり、先行カードも実行時に壊れていた）。
        # opponent は opp の同義語（dm06-005 の既存形）。be_chosen の照合は
        # 効果の使用者（random 時は you）基準で行う。
        ch = sel.get("chooser", "you")
        chooser = env["you"] if ch == "random" else (1 - env["you"] if ch == "opponent"
                                                      else self._rel(ch, env))
        # 相手に選ばれないクリーチャーは候補から外す（be_chosen）。自分のカードを自分が選ぶ時は関係ない。
        # 範囲つきの保護（deny の {action: be_chosen, other: <発生源フィルタ>}）は、選択の発生源
        # （解決中のカード = env の self）を other として照合する（第164弾。それ以外は発生源なし）
        src = env.get("self") or []
        first = src[0] if src else None
        src_cid = first[0] if isinstance(first, (list, tuple)) else first   # self は cid の列（参照 [cid, gen] の場合もある）
        cands = [c for c in cands if self.s.cards[c].zone != "bz" or self.s.cards[c].controller == chooser
                 or self.permits(c, "be_chosen", other=src_cid)]
        # 「可能ならこのクリーチャーを選ぶ」（第199弾）: 選ぶ側と別のコントローラーの候補の中に
        # must_be_chosen を持つクリーチャーがいれば、そのコントローラーの他のクリーチャーは
        # 候補から外す（このクリーチャー自体が候補にいない効果では制限しない）
        must_by_ctrl: dict[int, set[int]] = {}
        for c in cands:
            card = self.s.cards[c]
            if card.zone == "bz" and card.controller != chooser and self.chars_ro(c).get("must_be_chosen"):
                must_by_ctrl.setdefault(card.controller, set()).add(c)
        if must_by_ctrl:
            cands = [c for c in cands
                     if self.s.cards[c].zone != "bz"
                     or self.s.cards[c].controller not in must_by_ctrl
                     or c in must_by_ctrl[self.s.cards[c].controller]]
        if "distinct_from" in sel:   # 「自分のどのクリーチャーともコストが異なる」（第147弾・型1）: 参照集合のコストと重なる候補を外す。
            # 評価は選択開始時に1回だけ（＝出す前の場。選んだカードが出た後に場のコストが増えても残りの選択には影響しない）
            ref_costs = {self.chars_ro(c)["cost"] for c in self.candidates(sel["distinct_from"], env)}
            cands = [c for c in cands if self.chars_ro(c)["cost"] not in ref_costs]
        n = min(n, len(cands))
        if sel.get("chooser") == "random":   # 第185弾: 「見ないで選ぶ」。決定を出さず無作為に n 枚選ぶ
            pool = list(cands)
            picked = [pool.pop(rng_below(self.s, len(pool))) for _ in range(min(n, len(pool)))]
            t.setdefault("os", {})["chosen"] = picked
            return picked, None
        if "total_cost_le" in sel or "total_cost_ge" in sel or "total_power_le" in sel or "total_power_ge" in sel \
                or sel.get("distinct_costs"):   # 合計制限つきの「好きな数」選択: 1枚ずつ積み上げる。軸はコスト／パワー（第144弾で一般化）。distinct_costs は「コストが異なる」制約の述語として同じ分岐に乗る（第147弾・型2／型3）
            # 軸ごとの (特性キー, 上限, 下限)。パワーは chars の現在パワー（常在型の修整込み）を使う
            limits = []
            if "total_cost_le" in sel or "total_cost_ge" in sel:
                limits.append(("cost",
                               self.eval_expr(sel["total_cost_le"], env) if "total_cost_le" in sel else None,
                               self.eval_expr(sel["total_cost_ge"], env) if "total_cost_ge" in sel else None))
            if "total_power_le" in sel or "total_power_ge" in sel:
                limits.append(("power",
                               self.eval_expr(sel["total_power_le"], env) if "total_power_le" in sel else None,
                               self.eval_expr(sel["total_power_ge"], env) if "total_power_ge" in sel else None))

            def _totals(picked):
                return {k: sum(self.chars_ro(x)[k] for x in picked) for k, _, _ in limits}

            distinct = bool(sel.get("distinct_costs"))

            def _fits(picked, c, totals=None):
                if distinct and self.chars_ro(c)["cost"] in {self.chars_ro(x)["cost"] for x in picked}:
                    return False   # 「コストが異なる」: 既に選んだカードと同じコストは選べない（ハイパーエナジー支払いの used 述語と同じ形）
                totals = totals if totals is not None else _totals(picked)
                return all(le is None or totals[k] + self.chars_ro(c)[k] <= le for k, le, _ in limits)

            # 「N体まで」と併記された場合の枚数上限。count が無い「好きな数」は上限なし（従来どおり）
            cap = n if ("count" in sel and not any_n and sel.get("count") != "all") else None
            # 型3（全コスト網羅）: distinct_costs かつ count が固定（any／up_to でない）なら、必要数に達するまで止められない。
            # この規則は distinct の時だけに適用し、既存の total 系の can_stop の意味は変えない
            need = n if (distinct and not any_n and not sel.get("up_to") and "count" in sel) else None
            os = t.setdefault("os", {})
            picked: list[int] = []
            for ans in os.get("tc_answers", []):   # 済んだ段の答えを再生する（ask の再入対策）
                if cap is not None and len(picked) >= cap:
                    break
                rest = [c for c in cands if c not in picked]
                rest = [c for c in rest if _fits(picked, c)]
                if not ans:
                    break
                picked.append(rest[ans[0]])
            else:
                while True:
                    if cap is not None and len(picked) >= cap:
                        break
                    totals = _totals(picked)
                    rest = [c for c in cands if c not in picked]
                    rest = [c for c in rest if _fits(picked, c, totals)]
                    can_stop = all(ge is None or totals[k] >= ge for k, _, ge in limits)
                    if not can_stop and any(ge is not None and totals[k] < ge
                                            and totals[k] + sum(self.chars_ro(c)[k] for c in rest) < ge
                                            for k, _, ge in limits):
                        can_stop = True   # どう選んでも下限に届かない時は打ち切る
                    if need is not None and len(picked) < need:
                        # 全コスト網羅（型3）: 必要数に達するまで止められない。rest は distinct 述語で絞り済みなので、
                        # 残りのコストの種類数は rest のコスト集合の大きさ。どう選んでも届かない時は打ち切る（ge の同型）
                        can_stop = len(picked) + len({self.chars_ro(c)["cost"] for c in rest}) < need
                    if not rest:
                        break
                    a, d = self.ask(t, chooser, "choose_cards",
                                    [self._card_option(c, sel.get("look", False)) for c in rest], 0 if can_stop else 1, 1)
                    if d:
                        return None, d
                    os.setdefault("tc_answers", []).append(a)
                    if not a:
                        break
                    if a[0] >= len(rest):   # 上と同じ（隠れた札の中身が変わって候補が減った）。今の候補で聞き直す
                        os["tc_answers"].pop()
                        continue
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
        opts = [self._card_option(c, sel.get("look", False)) for c in cands]
        a, d = self.ask(t, chooser, "choose_cards", opts, mn, mx)
        if d:
            return None, d
        if any(i >= len(cands) for i in a):
            # 隠れた札（山札の上など）を条件で絞る候補は、公平探索で隠れた中身が決定の時と答えの時で違うと数が変わる。
            # 範囲外の答えは捨て、足りなければ今の候補で聞き直す
            a = [i for i in a if i < len(cands)]
            if len(a) < mn:
                a, d = self.ask(t, chooser, "choose_cards", opts, mn, mx)
                if d:
                    return None, d
        chosen = [cands[i] for i in a]
        t.setdefault("os", {})["chosen"] = chosen
        picked = [c for c in chosen if self.s.cards[c].zone == "bz" and self.s.cards[c].controller != chooser]
        for c in picked:   # 「相手がこのクリーチャーを選んだ時」。イベントの束は作らず、誘発だけを待機させる
            self._collect_triggers({"ev": "choose", "subject": self.s.ref(c), "player": chooser,
                                    "controller": self.s.cards[c].controller})
        return chosen, None
