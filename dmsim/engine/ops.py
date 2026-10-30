"""効果DSLのコア語彙。新しい op はここ（または別モジュール）で @op("名前", 引数=型) を付けて登録する。
引数の型は defs.py の検証と schema.py の JSON Schema 生成に使われる。"""
from __future__ import annotations

from .registry import op


@op("move", select="selector", to="zone", reason="reason", position="position?", card_only="bool?",
    order="str?", tapped="bool?", **{"as": "str?"})
def op_move(eng, t, op, env):
    """ゾーン移動。as を付けると、移動した後のカード（新しいオブジェクト）を変数に入れる（「その〜」で使う）。
    card_only: カードとして動かす（109.2a）。進化クリーチャーの一番上だけが離れ、下は再構築される（801.4）。
    order: choose なら、2枚以上を山札に置く時の並びをプレイヤーが決める（「好きな順序で」）。
    答えの先頭が、置いたカードの中で一番上になる。
    tapped: タップして置く（置かれた時点でタップ状態）。"""
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    if op.get("order") == "choose" and op["to"] == "deck" and len({eng.s.cards[c].defn for c in cids}) > 1:
        a, d = eng.ask(t, env["you"], "order_cards", [eng._card_option(c, True) for c in cids], len(cids), len(cids))
        if d:
            return d
        cids = [cids[i] for i in a]
        if op.get("position", "top") == "top":
            cids = cids[::-1]        # 1枚ずつ一番上に置かれるので、最後に置いたものが一番上になる
    shield_out = []     # 効果でシールドを手札に加える時は、S・トリガー等の使用宣言ができる（113.6）
    if op["to"] == "hand":
        shield_out = [c for c in cids if eng.s.cards[c].zone == "shield"]
    by_owner = {}
    for c in shield_out:
        by_owner.setdefault(eng.s.cards[c].controller, []).append(c)
    out_tasks = [{"t": "break", "victim": p, "by": env["you"], "count": len(cs), "phase": 1, "chosen": cs,
                  "in_effect": bool(env.get("in_st")), "reason": op["reason"], "fire_break": False}
                 for p, cs in sorted(by_owner.items(), key=lambda kv: kv[0] != eng.s.active)]   # ターン・プレイヤー側が先（111.1）
    evs = [{"ev": "move", "subject": eng.s.ref(c), "to": op["to"], "reason": op["reason"],
            "position": op.get("position", "top")} for c in cids if c not in shield_out]
    if op.get("card_only"):
        for e in evs:
            e["card_only"] = True
    if op.get("tapped"):
        for e in evs:
            e["tapped"] = True
    bind = [{"t": "bind", "env": env, "name": op["as"], "cids": cids, "zone": op["to"]}] if "as" in op else []
    if not evs and not out_tasks:
        if bind:
            env.setdefault("vars", {})[op["as"]] = []
        return None
    if op["to"] == "bz":   # バトルゾーンへ複数枚は1枚ずつ（409.1e）
        eng._defer(t, [eng.ev_task(e, env) for e in evs] + bind)
    else:                  # それ以外は同時（400.7）
        eng._defer(t, ([eng.ev_task(evs, env)] if evs else []) + out_tasks + bind)
    return None


@op("together", body="ops")
def op_together(eng, t, op, env):
    """body の move をすべて同時に行う（「Aを〜に戻し、同時に、Bを〜に置く」。400.7 同時の移動）。
    対象は移動の前にすべて決める。1つのイベントの束で動くので、途中の状態を誘発や置換が見ることはない。
    body は move だけで、対象は count: all か ref（プレイヤーの選択を挟まないもの）に限る。"""
    evs, binds = [], []
    for sub in op["body"]:
        if sub.get("op") != "move" or sub.get("position") or sub.get("card_only") or sub.get("order"):
            raise ValueError("together: body must be plain move ops")
        sel = sub["select"]
        if "ref" not in sel and sel.get("count") != "all":
            raise ValueError("together: move targets must be count: all or ref")
        cids = eng.candidates(sel, env)
        evs += [{"ev": "move", "subject": eng.s.ref(c), "to": sub["to"], "reason": sub["reason"],
                 "position": "top", **({"tapped": True} if sub.get("tapped") else {})} for c in cids]
        if "as" in sub:
            binds.append({"t": "bind", "env": env, "name": sub["as"], "cids": cids, "zone": sub["to"]})
    if evs:
        eng._defer(t, [eng.ev_task(evs, env)] + binds)
    return None


@op("draw", player="players?", count="expr?")
def op_draw(eng, t, op, env):
    """カードを引く。1枚ずつ（114.2）。player: each（各プレイヤー）はターン・プレイヤーが指定枚数を引いてから
    非ターン・プレイヤーが引く（114.2a）。"""
    who = op.get("player", "you")
    ps = [eng.s.active, 1 - eng.s.active] if who == "each" else [eng._rel(who, env)]
    n = eng.eval_expr(op.get("count", 1), env)
    eng._defer(t, [eng.ev_task({"ev": "draw", "player": p}, env) for p in ps for _ in range(n)])


@op("tap", select="selector", no_untap_next="bool?")
def op_tap(eng, t, op, env, kind="tap"):
    """no_untap_next: フリーズ等。そのクリーチャーは、次の持ち主のターンのはじめにアンタップしない。"""
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    if kind == "tap" and op.get("no_untap_next"):
        for c in cids:
            eng.s.cards[c].no_untap_next = True
    if cids:
        eng._defer(t, [eng.ev_task([{"ev": kind, "subject": eng.s.ref(c)} for c in cids], env)])
    return None


@op("untap", select="selector")
def op_untap(eng, t, op, env):
    return op_tap(eng, t, op, env, "untap")


@op("may", body="ops", label="str?")
def op_may(eng, t, op, env):
    a, d = eng.ask(t, env["you"], "yes_no", [{"key": "yes"}, {"key": "no"}], prompt=op.get("label", ""))
    if d:
        return d
    if a[0] == 0:
        eng._defer(t, [eng._child(op["body"], env)])
    return None


@op("modal", modes="oplists", count="int?", repeat="bool?")
def op_modal(eng, t, op, env):
    """「次のうちいずれか1つを選ぶ」「次の中から2回選ぶ（同じものを選んでもよい）」。選ぶのは効果の使用者。
    repeat なしは count 個の異なるモードを選び、書かれた順に解決する。repeat ありは1つずつ count 回選び、選んだ順に解決する。"""
    n = op.get("count", 1)
    opts = [{"key": f"mode:{i}"} for i in range(len(op["modes"]))]
    picked = t["os"].setdefault("picked", [])
    if op.get("repeat"):
        while len(picked) < n:
            a, d = eng.ask(t, env["you"], "choose_mode", opts)
            if d:
                return d
            picked.append(a[0])
        order = picked
    else:
        a, d = eng.ask(t, env["you"], "choose_mode", opts, n, n)
        if d:
            return d
        order = sorted(a)
    eng._defer(t, [eng._child(op["modes"][i], env) for i in order])


@op("if", cond="cond", then="ops?", **{"else": "ops?"})
def op_if(eng, t, op, env):
    branch = op.get("then", []) if eng.eval_cond(op["cond"], env) else op.get("else", [])
    eng._defer(t, [eng._child(branch, env)])


@op("repeat", times="expr", body="ops")
def op_repeat(eng, t, op, env):
    n = eng.eval_expr(op["times"], env)
    eng._defer(t, [eng._child(op["body"], env) for _ in range(n)])


@op("break", player="player?", count="expr?", st_first="bool?")
def op_break(eng, t, op, env):
    """効果でブレイクする。出た S・トリガーは、この効果の処理が終わってから解決する（101.4d）。
    ただし S・トリガーの解決中のブレイクなら、すでに待機している効果より先にその場で解決する（101.4g）。
    st_first: 「ブレイクしてもよい。その後、…」のように、後続の文が S・トリガーの解決を待つ効果（エメラルーダ。koba 確認 2026-10-28）。
    宣言された S・トリガーをその場で先に解決してから、続きを処理する。"""
    eng._defer(t, [{"t": "break", "victim": eng._rel(op.get("player", "opp"), env), "by": env["you"],
                     "count": eng.eval_expr(op.get("count", 1), env), "phase": 0,
                     "in_effect": bool(env.get("in_st")) or bool(op.get("st_first")), **eng._breaker(env)}])


@op("modify", select="selector", mod="mod", duration="duration?", dynamic="bool?")
def op_modify(eng, t, op, env):
    """継続的効果を生成する。既定では解決時の範囲に固定（110.2e）。
    dynamic: true は「相手のクリーチャーは〜できない」のように、後から入ったカードにも及ぶ範囲指定。"""
    s = eng.s
    s.seq += 1
    ce = {"id": s.seq, "mod": op["mod"], "duration": eng._duration(op.get("duration", "end_of_turn"), env),
          "controller": env["you"]}
    if "add_of" in op["mod"]:      # ダイナモ: このクリーチャー（効果の発生源）のパワーと能力を対象に加える
        ce["add_from"] = env["self"]
    if op.get("dynamic"):
        sel = op["select"]
        ce["affected"] = None
        ce["filter"] = {"zone": sel.get("zone", "bz"), "owner": eng._rel(sel["owner"], env)
                        if sel.get("owner", "you") != "any" else "any", "filter": sel.get("filter", {})}
    else:
        cids, d = eng.select(t, op["select"], env)
        if d:
            s.seq -= 1
            return d
        ce["affected"] = [s.ref(c) for c in cids]
    s.continuous.append(ce)
    sba = eng._sba_tasks()
    if sba:   # パワー0以下になったら、この効果の続きより先に破壊する（703.4c, 111.2d）
        eng._defer(t, sba)
    return None


@op("mark", name="str", of_self="bool?")
def op_mark(eng, t, op, env):
    """このターンの印を付ける（cond の marked で読む）。ターンが変わると消える。「各ターン1度」「他のファイナル革命を使っていなければ」用。
    of_self: このカード自身の印にする（cond の self_marked で読む。ターボラッシュ）。"""
    key = op["name"] + (f":{env['self'][0]}:{env['self'][1]}" if op.get("of_self") else "")
    eng.s.turn_counters[key] = eng.s.turn_counters.get(key, 0) + 1


@op("shuffle", player="player?")
def op_shuffle(eng, t, op, env):
    eng._shuffle(eng._rel(op.get("player", "you"), env))


@op("win", player="player?")
def op_win(eng, t, op, env):
    eng.s.result = {"winner": eng._rel(op.get("player", "you"), env), "reason": "effect", "turn": eng.s.turn}


@op("lose", player="player?")
def op_lose(eng, t, op, env):
    p = eng._rel(op.get("player", "you"), env)
    eng.s.result = {"winner": 1 - p, "reason": "effect", "turn": eng.s.turn}


@op("set_var", name="str", value="any?")
def op_set_var(eng, t, op, env):
    env.setdefault("vars", {})[op["name"]] = op.get("value", [])


@op("extra_turn", player="player?")
def op_extra_turn(eng, t, op, env):
    """追加ターン（500.5）。現在のターンの直後に1つずつ積む。"""
    eng.s.extra_turns.insert(0, eng._rel(op.get("player", "you"), env))


@op("step_mod", player="player", step="step", mode="str", turns="int?")
def op_step_mod(eng, t, op, env):
    """ターン構造の変更。mode: skip（そのステップを飛ばす）/ extra（もう一度行う）。
    例: 「次の相手のターンのドローステップを飛ばす」= {player: opp, step: draw, mode: skip}"""
    if op["mode"] not in ("skip", "extra"):
        raise ValueError(op["mode"])
    eng.s.step_mods.append({"player": eng._rel(op["player"], env), "step": op["step"], "mode": op["mode"],
                            "turns": op.get("turns", 1)})


@op("delayed_trigger", when="any", effect="ops", duration="duration?", once="bool?")
def op_delayed_trigger(eng, t, op, env):
    """遅延誘発型能力を作る（603.6）。作られた後に起きたイベントだけを見る。
    when は誘発型能力と同じ形。subject: {ref: 変数名} で「その〜」を指せる。"""
    s = eng.s
    s.seq += 1
    when = dict(op["when"])
    if isinstance(when.get("subject"), dict) and "ref" in when["subject"]:
        refs = eng.candidates(when["subject"], env)
        when["subject"] = {"refs": [s.ref(c) for c in refs]}
    s.delayed.append({"id": s.seq, "controller": env["you"], "when": when, "effect": op["effect"],
                      "env": {"you": env["you"], "self": env.get("self"), "vars": dict(env.get("vars", {}))},
                      "duration": eng._duration(op.get("duration", "end_of_turn"), env),
                      "once": op.get("once", True)})


def _free_face(eng, cid, want):
    """ツインパクトをコストを支払わず出す／唱える時の面。選択条件の types に呪文だけが指定されていれば呪文面、
    それ以外はクリーチャー面（なければ先頭の面）。"""
    faces = eng.cdef(cid).faces
    if not faces:
        return None
    if want and "spell" in want and "creature" not in want:
        for i, f in enumerate(faces):
            if "spell" in f.types:
                return i
    return 0


@op("play_free", select="selector", resolve_to="zone?", resolve_position="position?", face="str?", **{"as": "str?"})
def op_play_free(eng, t, op, env):
    """コストを支払わずに召喚する／唱える（112.3g: 召喚・詠唱したことになる）。ツインパクトはクリーチャー側。
    resolve_to: 唱えた呪文を解決後に墓地ではなくそのゾーンに置く（「唱えた後、墓地に置くかわりに手札に加える」）。"""
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    want = (op["select"].get("filter") or {}).get("types") if isinstance(op["select"], dict) else None
    if op.get("face") in ("spell", "creature"):   # ツインパクトの面を明示（ラスト・バーストの「呪文側」）
        want = [op["face"]]
    tasks = [eng.play_task(c, env["you"], True, _free_face(eng, c, want)) for c in cids]
    if "resolve_to" in op:
        for x in tasks:
            x["resolve_to"] = op["resolve_to"]
            if "resolve_position" in op:
                x["resolve_position"] = op["resolve_position"]
    if "as" in op:
        tasks.append({"t": "bind", "env": env, "name": op["as"], "cids": cids, "zone": "bz"})
    eng._defer(t, tasks)
    return None


@op("mekurade", filter="filter?", cost_le="int?", look="int?")
def op_mekurade(eng, t, op, env):
    """メクレイド: 自分の山札の上からN枚（既定3）を見て、条件に合う1枚をコストを支払わずに使ってもよい。
    残りは好きな順序で山札の下に置く。条件は filter と cost_le（「コストN以下」）。"""
    s = eng.s
    p = env["you"]
    os_ = t.setdefault("os", {})
    if "looked" not in os_:
        os_["looked"] = list(s.zones["deck"][p][:op.get("look", 3)])
    looked = os_["looked"]
    f = dict(op.get("filter") or {})
    if "cost_le" in op:
        f["cost_le"] = op["cost_le"]
    cands = [c for c in looked if s.cards[c].zone == "deck" and eng.filter_match(c, f)]
    if cands and "picked" not in os_:
        ans, d = eng.ask(t, p, "choose_cards", [eng._card_option(c, True) for c in cands], 0, 1)
        if d:
            return d
        os_["picked"] = cands[ans[0]] if ans else None
    pick = os_.get("picked")
    rest = [c for c in looked if c != pick and s.cards[c].zone == "deck"]
    tasks = []
    if pick is not None:
        want = (op.get("filter") or {}).get("types")
        tasks.append(eng.play_task(pick, p, True, _free_face(eng, pick, want)))
    if rest:
        env.setdefault("vars", {})["mek_rest"] = [s.ref(c) for c in rest]
        tasks.append(eng._child([{"op": "move", "select": {"ref": "mek_rest"}, "to": "deck", "reason": "put",
                                  "position": "bottom", "order": "choose"}], env))
    if tasks:
        eng._defer(t, tasks)
    return None


@op("play_self", cost="int", civs="any?")
def op_play_self(eng, t, op, env):
    """このカード自身を代替コストで実行する（キリフダッシュ: 攻撃の終わりに [コスト] を支払って召喚する）。
    civs は代替コストで必要な文明（省略時はカード自身の文明）。"""
    task = eng.play_task(env["self"][0], env["you"], False)
    task["cost_override"] = op["cost"]
    if "civs" in op:
        task["cost_civs"] = op["civs"]
    eng._defer(t, [task])
    return None


@op("swap", out="selector", **{"in": "selector"})
def op_swap(eng, t, op, env):
    """入れ替える（701.26）。out をバトルゾーンから手札へ、in をバトルゾーンへ。
    入ったクリーチャーは出たクリーチャーのタップ状態と攻撃中の状態を引き継ぐ（701.26a: 革命チェンジ）。
    out が正常に離れなければ入れ替えは行わない（701.26b）。"""
    outs, d = eng.select(t, op["out"], env)
    if d:
        return d
    ins = eng.candidates(op["in"], env)
    if not outs or not ins:
        return None
    o, i = outs[0], ins[0]
    if not eng.permits(i, "enter_bz"):   # 「コスト７以下のクリーチャーを出せない」: 入れ替えもできない
        return None
    eng._defer(t, [eng.ev_task({"ev": "move", "subject": eng.s.ref(o), "to": "hand", "reason": "return"}, env),
                   {"t": "swap_in", "out": eng.s.ref(o), "out_gen_next": eng.s.cards[o].gen + 1,
                    "in": eng.s.ref(i), "tapped": eng.s.cards[o].tapped, "env": env}])
    return None


@op("end_turn")
def op_end_turn(eng, t, op, env):
    """ターンの残りをとばす（次のプレイヤーのターンをすぐに始める）。今の効果の解決は最後まで行う。"""
    eng.s.skip_rest = True


@op("choose", select="selector", **{"as": "str"})
def op_choose(eng, t, op, env):
    """カードを選んで変数に入れるだけ（「〜を1体選ぶ。このターン、そのクリーチャーが〜」）。"""
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    env.setdefault("vars", {})[op["as"]] = [eng.s.ref(c) for c in cids]
    return None


@op("choose_race", **{"as": "str"})
def op_choose_race(eng, t, op, env):
    """「種族をひとつ選ぶ」: ゲームに出てくるカードの種族名（「/」で区切られた1種族ずつ）から1つ選び、変数に入れる。"""
    names = sorted({r for d in {c.defn for c in eng.s.cards} for r in eng.rules.cards[d].races})
    opts = [{"key": f"race:{r}", "name": r} for r in names]
    a, d = eng.ask(t, env["you"], "choose_race", opts, 1, 1)
    if d:
        return d
    env.setdefault("races", {})[op["as"]] = names[a[0]]
    return None


@op("put_under", select="selector", onto="selector")
def op_put_under(eng, t, op, env):
    """カードを、クリーチャーの下に重ねる（Evoチャージャーなど）。onto がシールドなら、そのシールドの束にする（113.2, 406.2）。
    select が複数枚なら、同じ重ね先の下に順に重ねる。"""
    os_ = t.setdefault("os", {})
    if "cards" not in os_:
        cids, d = eng.select(t, op["select"], env)
        if d:
            return d
        if not cids:
            return None
        os_["cards"] = list(cids)
        os_.pop("chosen", None)
    onto, d = eng.select(t, op["onto"], env)
    if d:
        return d
    if onto:
        eng._defer(t, [{"t": "put_under", "cid": c, "gen": eng.s.cards[c].gen, "onto": eng.s.ref(onto[0])}
                       for c in os_["cards"]])
    return None


@op("battle_substitute")
def op_battle_substitute(eng, t, op, env):
    """バトル相手の置換（when: {event: battle}）の印。実際の入れ替えは combat の _battle_substitute が行う。"""
    return None


@op("force_battle", a="selector", b="selector?")
def op_force_battle(eng, t, op, env):
    """選んだクリーチャー同士をバトルさせる（「その2体をバトルさせる」）。
    a が攻撃側。b を省略すると a の先頭2体同士。対象は choose で変数に入れてから ref で指すのが基本。
    バトル相手の置換（battle_substitute）は攻撃時のフローでのみ判定しており、ここでは未判定。"""
    aa = eng.candidates(op["a"], env)
    if op.get("b"):
        bb = eng.candidates(op["b"], env)
        pairs = [(aa[0], bb[0])] if aa and bb else []
    else:
        pairs = [(aa[0], aa[1])] if len(aa) >= 2 else []
    tasks = []
    for x, y in pairs:
        if eng.s.cards[x].zone == "bz" and eng.s.cards[y].zone == "bz" and x != y:
            tasks.extend(eng._battle(eng.s.ref(x), eng.s.ref(y)))
    if tasks:
        eng._defer(t, tasks)
    return None
