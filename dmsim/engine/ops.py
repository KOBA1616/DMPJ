"""効果DSLのコア語彙。新しい op はここ（または別モジュール）で @op("名前", 引数=型) を付けて登録する。
引数の型は defs.py の検証と schema.py の JSON Schema 生成に使われる。"""
from __future__ import annotations

from .registry import op


@op("move", select="selector", to="zone", reason="reason", position="position?", card_only="bool?",
    order="str?", **{"as": "str?"})
def op_move(eng, t, op, env):
    """ゾーン移動。as を付けると、移動した後のカード（新しいオブジェクト）を変数に入れる（「その〜」で使う）。
    card_only: カードとして動かす（109.2a）。進化クリーチャーの一番上だけが離れ、下は再構築される（801.4）。
    order: choose なら、2枚以上を山札に置く時の並びをプレイヤーが決める（「好きな順序で」）。
    答えの先頭が、置いたカードの中で一番上になる。"""
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
    evs = [{"ev": "move", "subject": eng.s.ref(c), "to": op["to"], "reason": op["reason"],
            "position": op.get("position", "top")} for c in cids]
    if op.get("card_only"):
        for e in evs:
            e["card_only"] = True
    bind = [{"t": "bind", "env": env, "name": op["as"], "cids": cids, "zone": op["to"]}] if "as" in op else []
    if not evs:
        if bind:
            env.setdefault("vars", {})[op["as"]] = []
        return None
    if op["to"] == "bz":   # バトルゾーンへ複数枚は1枚ずつ（409.1e）
        eng._defer(t, [eng.ev_task(e, env) for e in evs] + bind)
    else:                  # それ以外は同時（400.7）
        eng._defer(t, [eng.ev_task(evs, env)] + bind)
    return None


@op("draw", player="players?", count="expr?")
def op_draw(eng, t, op, env):
    """カードを引く。1枚ずつ（114.2）。player: each（各プレイヤー）はターン・プレイヤーが指定枚数を引いてから
    非ターン・プレイヤーが引く（114.2a）。"""
    who = op.get("player", "you")
    ps = [eng.s.active, 1 - eng.s.active] if who == "each" else [eng._rel(who, env)]
    n = eng.eval_expr(op.get("count", 1), env)
    eng._defer(t, [eng.ev_task({"ev": "draw", "player": p}, env) for p in ps for _ in range(n)])


@op("tap", select="selector")
def op_tap(eng, t, op, env, kind="tap"):
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    if cids:
        eng._defer(t, [eng.ev_task([{"ev": kind, "subject": eng.s.ref(c)} for c in cids], env)])
    return None


@op("untap", select="selector")
def op_untap(eng, t, op, env):
    return op_tap(eng, t, op, env, "untap")


@op("may", body="ops")
def op_may(eng, t, op, env):
    a, d = eng.ask(t, env["you"], "yes_no", [{"key": "yes"}, {"key": "no"}])
    if d:
        return d
    if a[0] == 0:
        eng._defer(t, [eng._child(op["body"], env)])
    return None


@op("if", cond="cond", then="ops?", **{"else": "ops?"})
def op_if(eng, t, op, env):
    branch = op.get("then", []) if eng.eval_cond(op["cond"], env) else op.get("else", [])
    eng._defer(t, [eng._child(branch, env)])


@op("repeat", times="expr", body="ops")
def op_repeat(eng, t, op, env):
    n = eng.eval_expr(op["times"], env)
    eng._defer(t, [eng._child(op["body"], env) for _ in range(n)])


@op("break", player="player?", count="expr?")
def op_break(eng, t, op, env):
    """効果でブレイクする。出た S・トリガーは、この効果の処理が終わってから解決する（101.4d）。
    ただし S・トリガーの解決中のブレイクなら、すでに待機している効果より先にその場で解決する（101.4g）。"""
    eng._defer(t, [{"t": "break", "victim": eng._rel(op.get("player", "opp"), env), "by": env["you"],
                     "count": eng.eval_expr(op.get("count", 1), env), "phase": 0,
                     "in_effect": bool(env.get("in_st"))}])


@op("modify", select="selector", mod="mod", duration="duration?", dynamic="bool?")
def op_modify(eng, t, op, env):
    """継続的効果を生成する。既定では解決時の範囲に固定（110.2e）。
    dynamic: true は「相手のクリーチャーは〜できない」のように、後から入ったカードにも及ぶ範囲指定。"""
    s = eng.s
    s.seq += 1
    ce = {"id": s.seq, "mod": op["mod"], "duration": eng._duration(op.get("duration", "end_of_turn"), env),
          "controller": env["you"]}
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


@op("play_free", select="selector", resolve_to="zone?", **{"as": "str?"})
def op_play_free(eng, t, op, env):
    """コストを支払わずに召喚する／唱える（112.3g: 召喚・詠唱したことになる）。ツインパクトはクリーチャー側。
    resolve_to: 唱えた呪文を解決後に墓地ではなくそのゾーンに置く（「唱えた後、墓地に置くかわりに手札に加える」）。"""
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    tasks = [eng.play_task(c, env["you"], True, 0 if eng.cdef(c).faces else None) for c in cids]
    if "resolve_to" in op:
        for x in tasks:
            x["resolve_to"] = op["resolve_to"]
    if "as" in op:
        tasks.append({"t": "bind", "env": env, "name": op["as"], "cids": cids, "zone": "bz"})
    eng._defer(t, tasks)
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


@op("put_under", select="selector", onto="selector")
def op_put_under(eng, t, op, env):
    """カードを、バトルゾーンのクリーチャーの下に重ねる（Evoチャージャーなど）。"""
    os_ = t.setdefault("os", {})
    if "card" not in os_:
        cids, d = eng.select(t, op["select"], env)
        if d:
            return d
        if not cids:
            return None
        os_["card"] = cids[0]
        os_.pop("chosen", None)
    onto, d = eng.select(t, op["onto"], env)
    if d:
        return d
    if onto:
        eng._defer(t, [{"t": "put_under", "cid": os_["card"], "gen": eng.s.cards[os_["card"]].gen,
                        "onto": eng.s.ref(onto[0])}])
    return None
