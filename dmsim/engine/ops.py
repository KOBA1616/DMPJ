"""効果DSLのコア語彙。新しい op はここ（または別モジュール）で @op("名前", 引数=型) を付けて登録する。
引数の型は defs.py の検証と schema.py の JSON Schema 生成に使われる。"""
from __future__ import annotations

from ..base.types import GachaTask, JankenTask
from .registry import op, task


@op("uncross", select="selector")
def op_uncross(eng, t, op, env):
    """クロスを外す（第170弾）: 選んだクロスギアの crossed を外す。ギアはバトルゾーンに残る（303.5）。
    「クリーチャーにクロスしてあるクロスギアをすべて、クリーチャーから外す」（dm17-012 型）。"""
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    for cid in cids:
        eng.s.mut_card(cid).crossed = None
    return None

@op("cross_free", gear="selector", to="selector")
def op_cross_free(eng, t, op, env):
    """コストを支払わずにクロスする（第195弾）: gear セレクタで選んだクロスギア
    すべてを、to セレクタで選んだクリーチャー1体にクロスする。効果によるクロスで、
    メインステップの通常クロス（cross_free 許可）とは別系統。支払いは無い。"""
    # 参照系セレクタ（ref / crossed_to 等）は決定を出さないので candidates で引く
    # （op_swap と同じ作法。select を2回呼ぶと os の chosen が衝突する）
    ref_like = ("ref", "crossed_to", "host_of", "under_of", "bundle_of")
    if any(k in op["gear"] for k in ref_like):
        gears = eng.candidates(op["gear"], env)
    else:
        gears, d = eng.select(t, op["gear"], env)
        if d:
            return d
    if any(k in op["to"] for k in ref_like):
        targets = eng.candidates(op["to"], env)
    else:
        targets, d = eng.select(t, op["to"], env)
        if d:
            return d
    if not gears or not targets:
        return None
    tg = eng.s.ref(targets[0])
    for cid in gears:
        eng.s.mut_card(cid).crossed = list(tg)
    return None


@op("move", select="selector", to="zone", reason="reason", position="position?", card_only="bool?",
    order="str?", tapped="bool?", face_up="bool?", face_down="bool?", seal="int?", stack_on="selector?",
    stack_evo="bool?", evo_source="selector?", strigger="str?", no_trigger="bool?", **{"as": "str?"})
def op_move(eng, t, op, env):
    """ゾーン移動。as を付けると、移動した後のカード（新しいオブジェクト）を変数に入れる（「その〜」で使う）。
    card_only: カードとして動かす（109.2a）。進化クリーチャーの一番上だけが離れ、下は再構築される（801.4）。
    order: choose なら、2枚以上を山札に置く時の並びをプレイヤーが決める（「好きな順序で」）。
    答えの先頭が、置いたカードの中で一番上になる。
    order: shuffle なら、動かす集合だけをシャッフルしてから置く（「残りをシャッフルし、山札の下に置く」）。
    tapped: タップして置く（置かれた時点でタップ状態）。
    face_down: 裏向きのまま置く（マナゾーンのみ意味を持つ。水晶武装の裏向きマナになる）。
    strigger: off/on = 手札に加わるカードへの S・トリガーの印（off はその S・トリガーを使えない＝
    エメラル／エスケープ型。宣言の諮問でも抑えられ、移動後のカードに印が残る。バンドC2 U68）。
    stack_on: シールドの上に重ねて置く（第148弾。to: shield の時だけ）。対象の束は効果の使用者が選ぶ
    （セレクタの owner は候補の絞り込み。相手のシールドに重ねる時は owner: opp と書く）。
    重ねる先のシールドが無い場合は置けないので、移動自体を行わない。"""
    target_ref = None
    evo_source_ref = None
    evo_source_done = False
    if "stack_on" in op:
        os_ = t.setdefault("os", {})
        if "move_cids" not in os_:
            cids, d = eng.select(t, op["select"], env)
            if d:
                return d
            os_["move_cids"] = list(cids)
            os_.pop("chosen", None)   # 2段目の選択（重ねる先）を新たに聞けるようにする（put_under と同じ型）
        cids = os_["move_cids"]
        if cids:
            tgt, d = eng.select(t, op["stack_on"], env)
            if d:
                return d
            if tgt:
                target_ref = eng.s.ref(tgt[0])
            else:
                cids = []   # 重ねる先のシールドが無い: 置けないので移動しない
    elif op.get("stack_evo") and "evo_source" in op:
        # 重ね先を固定する（第173弾）: 「このクリーチャーの上に置く」等。選択を2段に分け、
        # 1段目の答えを残す（stack_on と同じ型）。重ね先が無ければ置けないので移動しない
        os_ = t.setdefault("os", {})
        if "move_cids" not in os_:
            cids, d = eng.select(t, op["select"], env)
            if d:
                return d
            os_["move_cids"] = list(cids)
            os_.pop("chosen", None)
        cids = os_["move_cids"]
        if "evo_source_ref" not in os_:
            srcs, d = eng.select(t, op["evo_source"], env)
            if d:
                return d
            os_["evo_source_ref"] = eng.s.ref(srcs[0]) if srcs else None
        evo_source_ref = os_["evo_source_ref"]
        evo_source_done = True
    else:
        cids, d = eng.select(t, op["select"], env)
        if d:
            return d
    if op.get("order") == "shuffle" and len(cids) > 1:
        from .state import rng_below
        for i in range(len(cids) - 1, 0, -1):   # ヨビニオンの残り処理と同じ Fisher-Yates
            j = rng_below(eng.s, i + 1)
            cids[i], cids[j] = cids[j], cids[i]
    if op.get("stack_evo"):
        # 重ね出し（put_evolution_stacking）: 選んだカードを1体ずつ順に出し、進化クリーチャーは
        # その都度選んだ進化元に重ねる（put_stacked タスクへ引き渡す）
        task = {"t": "put_stacked", "cids": list(cids), "all_cids": list(cids), "player": env["you"],
                "env": env, "reason": op["reason"], "tapped": bool(op.get("tapped")),
                "face_up": bool(op.get("face_up"))}
        if op.get("evo_source"):   # 重ね先を固定する（第173弾）: 解決時に進化元の適格性も照合する
            if not evo_source_done or evo_source_ref is None:
                return None   # 重ね先が無い: 置けないので移動しない
            task["evo_source"] = evo_source_ref
        if op.get("seal"):
            task["seal"] = op["seal"]
        if "as" in op:
            task["bind"] = op["as"]
        eng._defer(t, [task])
        return None
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
                  "in_effect": bool(env.get("in_st")), "reason": op["reason"], "fire_break": False,
                  **({"strigger": op["strigger"]} if op.get("strigger") else {})}
                 for p, cs in sorted(by_owner.items(), key=lambda kv: kv[0] != eng.s.active)]   # ターン・プレイヤー側が先（111.1）
    evs = [{"ev": "move", "subject": eng.s.ref(c), "to": op["to"], "reason": op["reason"],
            "position": op.get("position", "top")} for c in cids if c not in shield_out]
    if op.get("card_only"):
        for e in evs:
            e["card_only"] = True
    if op.get("tapped"):
        for e in evs:
            e["tapped"] = True
    if op.get("face_up"):
        for e in evs:
            e["face_up"] = True
    if op.get("face_down"):
        for e in evs:
            e["face_down"] = True
    if op.get("seal"):
        for e in evs:
            e["seal"] = op["seal"]   # バトルゾーンに出る時、封印を付けた状態で出る（出た時能力は無視される）
    if op.get("strigger"):
        for e in evs:
            e["strigger"] = op["strigger"]   # 手札に加わるカードへの S・トリガーの印（off=使えない／on=得る。バンドC2 U68）
    if op.get("no_trigger"):
        for e in evs:
            e["no_trigger"] = True   # この移動でバトルゾーンに出たカード自身の出た時能力は誘発しない（第213弾）
    if target_ref is not None:
        for e in evs:
            e["shield_stack"] = target_ref   # シールドの束の上に重ねる（第148弾。イベントのキーは進化の stack_on と分ける: あちらは _record_for が stacked として照合する）
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
                 "position": "top", **({"tapped": True} if sub.get("tapped") else {}),
                 **({"face_down": True} if sub.get("face_down") else {})} for c in cids]
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
            eng.s.mut_card(c).no_untap_next = True
    if cids:
        eng._defer(t, [eng.ev_task([{"ev": kind, "subject": eng.s.ref(c)} for c in cids], env)])
    return None


@op("untap", select="selector")
def op_untap(eng, t, op, env):
    return op_tap(eng, t, op, env, "untap")


@op("hyper_release", select="selector")
def op_hyper_release(eng, t, op, env):
    """ハイパーモードの解放（効果による）: 選んだクリーチャーの旗を立てる。
    ハイパー化（メインステップの hyper_act: 自分の他のクリーチャー1体をタップする手順）とは
    別物で、コストは伴わない。タップ・イベント・タスクは発行しない（Zラッシュの直接付与と同じ）。
    期限は書かない: 「次の自分のターンのはじめまで」は st_start の無条件解除（turn.py）と一致する。
    ハイパー面を持たない対象には旗を立てない（選択自体は文面どおり行い、効果だけが空振りする）。
    候補が0体なら select が決定を出さず、そのまま不発する。"""
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    for c in cids:
        if eng.fdef(c).hyper:
            eng.s.mut_card(c).hyper = True
    return None


@op("flip_down", select="selector")
def op_flip_down(eng, t, op, env):
    """水晶武装: マナゾーンのカードを裏向きにする。裏向きのマナは無色として扱う（支払いの文明に数えない）。
    シールドゾーンの表向きのカードを裏向きに戻すのにも使う（第148弾）。どちらもイベントは作らない。"""
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    for c in cids:
        card = eng.s.mut_card(c)
        if card.zone == "mana":
            card.face_down = True
        elif card.zone == "shield":
            card.face_up = False
    return None


@op("flip_up", select="selector")
def op_flip_up(eng, t, op, env):
    """カードを表向きにする（第148弾）: シールドゾーンのカードは表向きにし（公開を記録する）、
    マナゾーンの裏向きカードは表向きに戻す（エターナル・Κ 等）。イベントは作らないので
    「表向きで置かれた時」は誘発しない（向きを変えただけ。ギャラクシールドのターン開始時召喚は
    状態条件で拾う）。両方向の選択は modal で書く。束の中のカードは bundle_of で指す。"""
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    for c in cids:
        card = eng.s.mut_card(c)
        if card.zone == "shield":
            if not card.face_up:
                card.face_up = True
                eng.note_public("face_up", c)
        elif card.zone == "mana":
            card.face_down = False
    return None


@op("dswitch")
def op_dswitch(eng, t, op, env):
    """Dスイッチ（第151弾）: 発生源の D2フィールドを上下逆さまにする（使用済みの旗 dswitched を立てる）。
    イベントは作らない（flip_up／flip_down と同じ直操作）。「ゲーム中で一度」はこの旗で数え、
    ゾーン移動でリセットされる（新しいオブジェクトとして出直したら再び使える）。
    能力の出し分け（使用済み・deny: [d_switch] の間は能力自体が出ない）は abilities() 側で行う。"""
    cid = env["self"][0]
    if eng.s.alive(env["self"]):
        eng.s.mut_card(cid).dswitched = True
    return None


@op("may", body="ops", label="str?", player="str?", **{"else": "ops?"})
def op_may(eng, t, op, env):
    decider = eng._rel(op.get("player", "you"), env)
    a, d = eng.ask(t, decider, "yes_no", [{"key": "yes"}, {"key": "no"}], prompt=op.get("label", ""))
    if d:
        return d
    if a[0] == 0:
        eng._defer(t, [eng._child(op["body"], env)])
    elif op.get("else"):   # 「そうしなければ」（アバレチェーンなど）
        eng._defer(t, [eng._child(op["else"], env)])
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


@op("repeat", times="expr?", body="ops", over="str?", **{"as": "str?"})
def op_repeat(eng, t, op, env):
    if "over" in op:   # 第233弾: 変数のカード1枚ずつに body を適用する（要素は as の変数に束ねる）
        refs = env.get("vars", {}).get(op["over"], [])
        name = op.get("as", "it")
        kids = []
        for r in refs:
            e2 = {**env, "vars": {**env.get("vars", {}), name: [list(r)]}}
            kids.append(eng._child(op["body"], e2))
        eng._defer(t, kids)
        return
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


def _bake_refs(obj, eng, env):
    """生成時ベイク（バンドC2 基盤B4）: {declared: 名前} と {var: 名前} の式を、生成時点の値へ
    リテラルに固定する。宣言・変数は解決の後段（特性計算や dynamic の範囲照合）では env から
    読めないため、継続的効果へ持ち込む時はここで固定する。
    参照カードの特性式 {cost_of / power_of / name_of / races_of: 名前} も同じ理由で焼く
    （第263弾: dynamic の範囲フィルタに「表向きにしたカードのコスト以下」を書くため）。
    {count: ...} 等の集合式そのものは焼かない（中に入れ子になった参照特性式だけ焼く）。"""
    if isinstance(obj, dict):
        if len(obj) == 1 and next(iter(obj)) in ("declared", "var", "cost_of", "power_of", "name_of", "races_of"):
            return eng.eval_expr(obj, env)
        return {k: _bake_refs(v, eng, env) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_bake_refs(v, eng, env) for v in obj]
    return obj


@op("modify", select="selector", mod="mod", duration="duration?", dynamic="bool?")
def op_modify(eng, t, op, env):
    """継続的効果を生成する。既定では解決時の範囲に固定（110.2e）。
    dynamic: true は「相手のクリーチャーは〜できない」のように、後から入ったカードにも及ぶ範囲指定。"""
    s = eng.s
    s.seq += 1
    mod = op["mod"]
    # {declared:...} / {var:...} は生成時にベイクする（基盤B4。add_races は下の専用処理、gain は能力そのものなので対象外）
    mod = {k: (v if k in ("add_races", "gain") else _bake_refs(v, eng, env)) for k, v in mod.items()}
    if any(isinstance(r, dict) for r in mod.get("add_races", [])):
        # 式の種族（{race: 変数名} = choose_race で選んだ種族）は生成時の env で名前へ展開して固定する（第136弾）
        mod = dict(mod)
        mod["add_races"] = [name for r in mod["add_races"]
                            for name in (eng.eval_expr(r, env) if isinstance(r, dict) else [r])]
    ce = {"id": s.seq, "mod": mod, "duration": eng._duration(op.get("duration", "end_of_turn"), env),
          "controller": env["you"], "src": env["self"][0] if env.get("self") else None}
    if "add_of" in op["mod"]:      # ダイナモ: このクリーチャー（効果の発生源）のパワーと能力を対象に加える
        ce["add_from"] = env["self"]
    if op.get("dynamic"):
        sel = op["select"]
        ce["affected"] = None
        # dynamic の範囲フィルタは特性計算のたびに env なしで照合されるため、宣言・変数の参照は生成時にベイクする（基盤B4）
        ce["filter"] = {"zone": sel.get("zone", "bz"), "owner": eng._rel(sel["owner"], env)
                        if sel.get("owner", "you") != "any" else "any",
                        "filter": _bake_refs(sel.get("filter", {}), eng, env)}
    else:
        cids, d = eng.select(t, op["select"], env)
        if d:
            s.seq -= 1
            return d
        ce["affected"] = [s.ref(c) for c in cids]
    if mod.get("double_power"):      # 「パワーを2倍にする」: 生成時点のパワーを対象ごとに控え、加算として適用する（第141弾。範囲固定の効果のみ）
        ce["double_power"] = {r[0]: eng.chars_ro(r[0])["power"] for r in ce.get("affected") or []}
    s.continuous.append(ce)
    sba = eng._sba_tasks()
    if sba:   # パワー0以下になったら、この効果の続きより先に破壊する（703.4c, 111.2d）
        eng._defer(t, sba)
    return None


@op("rush", select="selector")
def op_rush(eng, t, op, env):
    """このターン、対象のクリーチャーは召喚酔いでもプレイヤーを攻撃できる（第243弾）。
    combat の _attack_options が読む rush:<cid> フラグを立てる。アビスラッシュの
    付随処理と同じ印だが、ターン終了時の山札送り等の付随処理は付けない。"""
    for cid in eng.candidates(op["select"], env):
        eng.s.turn_counters[f"rush:{cid}"] = eng.s.turn
    return None


@op("cancel_attack")
def op_cancel_attack(eng, t, op, env):
    """進行中の攻撃を中止する（第251弾）。タスクスタック上の attack タスクに印を付け、
    h_attack が再開時にバトルもブレイクも行わず攻撃を終わらせる。攻撃が無ければ何もしない。"""
    for task in reversed(eng.s.tasks):
        if task.get("t") == "attack":
            task["cancelled"] = True
            break
    return None


@op("mark", name="str", of_self="bool?", scope="str?")
def op_mark(eng, t, op, env):
    """印を付ける（cond の marked で読む）。「各ターン1度」「他のファイナル革命を使っていなければ」用。
    scope（バンドB 基盤 mark-scope）: 既定は turn（ターンが変わると消える）。
    attack はその攻撃の中だけ、game はゲーム中ずっと（game_counters。ターン開始で消えない。
    「ゲーム中に一度だけ」や極限ファイナル革命の使用履歴用）。
    of_self: このカード自身の印にする（cond の self_marked で読む。ターボラッシュ）。"""
    scope = op.get("scope", "turn")
    if scope not in ("turn", "attack", "game"):
        raise ValueError(f"mark scope must be turn/attack/game, got {scope!r}")
    store = eng.s.game_counters if scope == "game" else eng.s.turn_counters
    key = eng._mark_key(op["name"], scope, env) + \
        (f":{env['self'][0]}:{env['self'][1]}" if op.get("of_self") else "")
    store[key] = store.get(key, 0) + 1


@op("shuffle", player="player?", player_from="str?")
def op_shuffle(eng, t, op, env):
    """player_from: その変数の最初のカードの持ち主の山札をシャッフルする（「その持ち主は山札をシャッフルする」）。"""
    if "player_from" in op:
        refs = env.get("vars", {}).get(op["player_from"], [])
        if refs:
            eng._shuffle(eng.s.cards[refs[0][0]].controller)
        return
    eng._shuffle(eng._rel(op.get("player", "you"), env))


@op("win", player="player?")
def op_win(eng, t, op, env):
    winner = eng._rel(op.get("player", "you"), env)
    if eng._lose_immune(1 - winner, "effect"):   # 第188弾: 「相手はゲームに勝てない」は勝利効果も防ぐ
        return None
    eng.s.result = {"winner": winner, "reason": "effect", "turn": eng.s.turn}


@op("lose", player="player?")
def op_lose(eng, t, op, env):
    p = eng._rel(op.get("player", "you"), env)
    tasks = eng.game_lose(p, "effect")   # 敗北の置換（S-MAX進化など）を諮ってから確定する
    if tasks:
        eng._defer(t, tasks)


@op("pay_or_lose", cost="int", civs="any?")
def op_pay_or_lose(eng, t, op, env):
    """指定コストを自分のマナで支払う。支払えなければゲームに負ける（第217弾: 逆転撃の後払い）。
    支払いはカードを出す行為ではないので _mana_choices は raw_cost で数える
    （コスト増減・ブーストなし。マナの数字そのものを変える置換だけが効く）。
    払える場合は支払いは任意ではない（組の選択だけがプレイヤーの決定）。
    発生源（env の self）は支払いプールから外れるため、マナゾーンの外にある前提。"""
    s = eng.s
    p = env["you"]
    anchor = env["self"][0] if env.get("self") else next(iter(s.cards))
    choices = eng._mana_choices(anchor, p, None, cost=op["cost"], civs=op.get("civs"), raw_cost=True)
    if not choices:
        tasks = eng.game_lose(p, "effect")   # 敗北の置換を諮ってから確定する（op lose と同じ口）
        if tasks:
            eng._defer(t, tasks)
        return None
    opts = [{"key": "mana:" + ",".join(sorted(s.cards[c].defn for c in ch)), "cids": ch} for ch in choices]
    ans, dd = eng.ask(t, p, "pay_mana", opts)
    if dd:
        return dd
    for c in opts[ans[0]]["cids"]:
        s.cards[c].tapped = True
    return None


@op("no_lose", player="players?", duration="duration?", once="bool?", deck_out_only="bool?")
def op_no_lose(eng, t, op, env):
    """敗北の防止（第188弾）: player は duration の間ゲームに負けない（＝相手はゲームに勝てない）。
    once: 一度だけ（敗北を防いだら消費する。「このターン中に一度、自分がゲームに負ける時、かわりに負けない」）。
    deck_out_only: 山札切れによる敗北だけを防ぐ（「自分の山札にカードがなくても、自分はゲームに負けない」）。
    継続的効果として s.continuous に載せ、duration の期限切れ（end_of_turn / until_next_own_turn_start /
    permanent）は既存の仕組みに任せる。mod は空で affected は空集合（特性には影響しない）。"""
    s = eng.s
    s.seq += 1
    who = op.get("player", "you")
    targets = (env["you"], 1 - env["you"]) if who == "each" else (eng._rel(who, env),)
    for p in targets:
        s.continuous.append({"id": s.seq, "mod": {}, "duration": eng._duration(op.get("duration", "end_of_turn"), env),
                             "controller": env["you"], "src": env["self"][0] if env.get("self") else None,
                             "affected": [],
                             "no_lose": {"player": p, "once": bool(op.get("once", False)),
                                         "deck_out_only": bool(op.get("deck_out_only", False))}})
    return None


@op("action_limit", player="player?", attack="int?", block="int?", until="str")
def op_action_limit(eng, t, op, env):
    """攻撃/ブロック回数の制限（第254弾）: player は各ターン、クリーチャーで attack 回までしか
    攻撃できず、block 回までしかブロックできない。保留として s.action_limits に積み、
    期限（until: caster_next_turn_start = 唱えた側の次のターンのはじめまで /
    opp_next_turn = 次の相手のターン中だけ）は st_start で落とす。"""
    p = eng._rel(op.get("player", "opp"), env)
    eng.s.action_limits.append({"player": p, "attack": op.get("attack"), "block": op.get("block"),
                                "caster": env["you"], "created": eng.s.turn, "until": op["until"]})
    return None


@op("untap_limit", player="player?", zone="str", count="int")
def op_untap_limit(eng, t, op, env):
    """アンタップ制限（第227弾）: player の次のターン開始時に、そのゾーンのカードは
    count 枚までしかアンタップできない。保留として s.untap_caps に積み、そのプレイヤーの
    st_start で消費する（常在型の同名キーと最小値を取る）。"""
    p = eng._rel(op.get("player", "opp"), env)
    eng.s.untap_caps.append({"player": p, "zone": op["zone"], "count": op["count"]})
    return None


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
        for c in os_["looked"]:
            eng.note_public("look", c, [p])
    looked = os_["looked"]
    f = dict(op.get("filter") or {})
    if "cost_le" in op:
        f["cost_le"] = op["cost_le"]
    cands = [c for c in looked if s.cards[c].zone == "deck" and eng.filter_match(c, f, env=env)]
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


_JANKEN_HANDS = ("rock", "scissors", "paper")   # 0=グー, 1=チョキ, 2=パー
_JANKEN_OPTS = [{"key": "rock", "name": "グー"}, {"key": "scissors", "name": "チョキ"},
                {"key": "paper", "name": "パー"}]
_JANKEN_BEATS = {("rock", "scissors"), ("scissors", "paper"), ("paper", "rock")}


@op("janken", win="ops?", lose="ops?")
def op_janken(eng, t, op, env):
    """ジャンケン: 両プレイヤーが グー/チョキ/パー を選ぶ。勝敗で分岐する。
    第271弾で専用タスク化した。第31弾の op 内二段 ask は、1人目の答えが返った時点で
    h_effect が pc を進めて os を消してしまい、相手の手を尋ねる前に終わって分岐が
    一度も走らない不発だった（第31弾のテストはターンのドローと区別できず見逃していた）。
    DM のジャンケンは「勝敗が決まるまでやって一回」で、あいこは勝敗が決まるまで
    やり直す。あいこの投も含め各投の手は公開情報で、janken イベントとして発表する
    ので「相手がジャンケンで「X」を出した時」の誘発（when: {event: janken, opp_hand: X}）
    が投ごとに誘発する。勝敗の分岐は勝った側の効果が先に解決され、その後で溜まった
    手の誘発が解決される（誘発は能力解決中は待機する、603.3）。"""
    eng._defer(t, [{"t": "janken", "controller": env["you"], "env": env,
                    "win": op.get("win") or [], "lose": op.get("lose") or []}])
    return None


@task("janken", JankenTask)
def h_janken(eng, t):
    """ジャンケンの1回分（第271弾）: 両者の手を尋ね、決まれば勝敗分岐の子タスクを積む。
    あいこならその投のイベントだけ発表して、もう一度手を尋ねる。"""
    s = eng.s
    if t.get("done"):
        eng._pop(t)
        return None
    me = t["controller"]
    if "mine" not in t:
        a, d = eng.ask(t, me, "choose_one", _JANKEN_OPTS)
        if d:
            return d
        t["mine"] = _JANKEN_HANDS[a[0]]
    if "opp" not in t:
        a, d = eng.ask(t, 1 - me, "choose_one", _JANKEN_OPTS)
        if d:
            return d
        t["opp"] = _JANKEN_HANDS[a[0]]
    mine, opp = t.pop("mine"), t.pop("opp")
    hands = ["", ""]
    hands[me], hands[1 - me] = mine, opp
    winner = None if mine == opp else (me if (mine, opp) in _JANKEN_BEATS else 1 - me)
    rec = {"ev": "janken", "controller": me, "hands": hands, "winner": winner}
    if t["env"].get("self"):
        rec["subject"] = t["env"]["self"]
    s.pub.append({"n": len(s.pub), "turn": s.turn, "kind": "janken",
                  "viewers": [0, 1], "player": me, "hands": list(hands), "winner": winner})
    tasks = [eng.ev_task(rec)]
    if winner is None:
        eng._push(*tasks)   # あいこ: この投のイベントだけ発表して、もう一度手を尋ねる
        return None
    branch = t["win"] if winner == me else t["lose"]
    if branch:
        tasks.append(eng._child(branch, t["env"]))
    t["done"] = True
    eng._push(*tasks)
    return None


@op("move_under_to_event")
def op_move_under_to_event(eng, t, op, env):
    """G-NEO進化の離脱置換の代わり: 発生源の下のカードすべてを、置換されたイベントの行き先へ移動する。"""
    ev = env.get("event") or {}
    to = ev.get("to")
    if not to or to == "bz":
        return None
    cid = env["self"][0]
    unders = list(eng.s.cards[cid].under)
    if not unders:
        return None
    evs = []
    for u in unders:
        e = {"ev": "move", "subject": eng.s.ref(u), "to": to, "reason": ev.get("reason", "put")}
        if ev.get("position"):
            e["position"] = ev["position"]
        evs.append(e)
    eng._defer(t, [eng.ev_task(evs)])
    return None


@op("shield_plus")
def op_shield_plus(eng, t, op, env):
    """シールド・プラス: 自分の山札の上から1枚を、自分のシールド1つの下に置く（束は1つと数える）。"""
    s = eng.s
    p = env["you"]
    shields = eng.zlist("shield", p)
    deck = s.zones["deck"][p]
    if not shields or not deck:
        return None
    a, d = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in shields], 1, 1)
    if d:
        return d
    target = shields[a[0]]
    tucked = deck[0]
    eng._raw_move(tucked, "shield")
    lst = eng.mut_zlist("shield", p)
    if tucked in lst:
        lst.remove(tucked)   # 束の下のカードはゾーンの並びに入らない（113.2）
    s.mut_card(target).under.append(tucked)
    s.mut_card(tucked).top_of = target
    return None


@op("sforce_link")
def op_sforce_link(eng, t, op, env):
    """シールド・フォース: 自分のシールドを1枚選んでもよい。選んだシールドに自分への
    紐付け（sforce_of）を刻む。そのシールドがシールドゾーンにある間、自分の
    sforce 印つき能力が機能する。選ばなければ何も起きない。"""
    s = eng.s
    p = env["you"]
    shields = eng.zlist("shield", p)
    if not shields:
        return None
    a, d = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in shields], 0, 1)
    if d:
        return d
    if not a:
        return None
    me = list(env["self"])
    for c in shields:
        if s.cards[c].sforce_of is not None and list(s.cards[c].sforce_of) == me:
            s.mut_card(c).sforce_of = None
    s.mut_card(shields[a[0]]).sforce_of = me
    return None


@op("castle_link")
def op_castle_link(eng, t, op, env):
    """城（第178弾）: 自分のシールドを1枚選び、このカードを付けて要塞化する。
    シールドがなければ何も起きない。選んだシールドへの参照（fortifies）を自分に刻む。
    要塞化されたシールドがシールドゾーンを離れると、城は状況起因処理で墓地に置かれる。"""
    s = eng.s
    p = env["you"]
    shields = eng.zlist("shield", p)
    if not shields:
        return None
    a, d = eng.ask(t, p, "choose_cards", [eng._card_option(c) for c in shields], 1, 1)
    if d:
        return d
    me = list(env["self"])
    s.mut_card(me[0]).fortifies = list(s.ref(shields[a[0]]))
    return None


@op("opp_may", body="ops", label="str?")
def op_opp_may(eng, t, op, env):
    """「相手は〜してもよい」: 相手が yes/no を選び、yes なら body を相手の視点で実行する。"""
    opp = 1 - env["you"]
    a, d = eng.ask(t, opp, "yes_no", [{"key": "yes"}, {"key": "no"}], prompt=op.get("label", ""))
    if d:
        return d
    if a[0] == 0:
        env2 = dict(env)
        env2["you"] = opp
        eng._defer(t, [eng._child(op["body"], env2)])
    return None


@op("yobinion")
def op_yobinion(eng, t, op, env):
    """ヨビニオン: 自分の山札の上から、これ（発生源）よりコストが小さいクリーチャーが出るまで
    表向きにする。そのクリーチャーを出す。残りはシャッフルし、山札の下に置く。"""
    from .state import rng_below
    s = eng.s
    p = env["you"]
    threshold = eng.chars_ro(env["self"][0])["cost"]
    revealed, found = [], None
    for c in list(s.zones["deck"][p]):
        revealed.append(c)
        eng.note_public("reveal", c)
        ch = eng.chars(c)
        if "creature" in ch["types"] and ch["cost"] < threshold:
            found = c
            break
    rest = [c for c in revealed if c != found]
    if len(rest) > 1:
        eng.note_public("shuffle", player=p, zone="deck")
    for i in range(len(rest) - 1, 0, -1):   # 残りをシャッフル（Fisher-Yates）
        j = rng_below(s, i + 1)
        rest[i], rest[j] = rest[j], rest[i]
    for c in rest:
        eng._raw_move(c, "deck", "bottom")
    if found is not None:
        eng._defer(t, [eng.ev_task({"ev": "move", "subject": s.ref(found), "to": "bz",
                                     "reason": "put", "controller": p}, env)])
    return None


@op("reveal_until", player="player?", player_from="str?", filter="filter", count="expr?",
    limit="expr?", **{"as": "str", "rest_as": "str?"})
def op_reveal_until(eng, t, op, env):
    """「〜が出るまで表向きにする」: 対象プレイヤー（player。既定 you。player_from があれば、その変数の
    最初のカードの持ち主 = 「その持ち主」）の山札を上から1枚ずつ公開し、filter に合うカードが
    count 枚（既定1）出た時点で止める。合ったカード群を as に、出なかった公開カード群を
    rest_as（既定 as + "_rest"）に束縛する。公開したカードは山札に残るので、行き先は後続の
    op（move で出す／墓地に置く／山札の下に置く、shuffle で山札に戻す）が決める。
    count が 0 以下のときは何も公開しない（「破壊した数と同じ数」が 0 の場合）。
    limit（第181弾）: 公開する合計枚数の上限。limit 枚公開した時点で、合うカードが
    count 枚に満たなくても止める。「山札の上から1枚目を表向きにし、それが多色なら手札に
    加える」（ロスト・プリズム）は limit: 1, count: 1, filter: {multicolor: true} で書く。
    limit が 0 以下のときも何も公開しない。"""
    s = eng.s
    vars_ = env.setdefault("vars", {})
    rest_name = op.get("rest_as") or (op["as"] + "_rest")
    if "player_from" in op:
        refs = vars_.get(op["player_from"], [])
        if not refs:
            vars_[op["as"]], vars_[rest_name] = [], []
            return None
        p = s.cards[refs[0][0]].controller
    else:
        p = eng._rel(op.get("player", "you"), env)
    want = eng.eval_expr(op["count"], env) if "count" in op else 1
    if want <= 0:
        vars_[op["as"]], vars_[rest_name] = [], []
        return None
    limit = eng.eval_expr(op["limit"], env) if "limit" in op else None
    if limit is not None and limit <= 0:
        vars_[op["as"]], vars_[rest_name] = [], []
        return None
    f = {k: (eng.eval_expr(v, env) if isinstance(v, dict) else v)
         for k, v in (op.get("filter") or {}).items()}
    hit, rest = [], []
    for c in list(s.zones["deck"][p]):
        if limit is not None and len(hit) + len(rest) >= limit:
            break
        eng.note_public("reveal", c)
        if eng.filter_match(c, f, env=env):
            hit.append(c)
            if len(hit) >= want:
                break
        else:
            rest.append(c)
    vars_[op["as"]] = [s.ref(c) for c in hit]
    vars_[rest_name] = [s.ref(c) for c in rest]
    return None


@op("gachinko", times="expr?", until_lose="bool?", stoppable="bool?", by="str?", mine_as="str?", **{"as": "str?"})
def op_gachinko(eng, t, op, env):
    """ガチンコ・ジャッジ: 各プレイヤーは自身の山札の上から1枚を見せ、それを一番下に置く。
    そのカードのコストが相手以上であれば自分の勝ち。times 回（式可）繰り返すか、
    until_lose（自分が負けるまで）/ stoppable（自分が中止するまで）の組み合わせ。
    勝った回数を env の変数（既定 wins）に書き、後続の op が {var: wins} で参照する。
    第223弾: by: "power" でパワー比較になる（パワー・ガチンコ・ジャッジ。
    パワーがないカードは 0 として扱う）。mine_as を付けると、自分の見せた
    カードを一番下に置かずにその参照を変数へ残す（「下に置くかわりに〜」
    の代替先を後続 op が決めるため。複数回繰り返す場合は最後の1枚だけが
    残り、それ以前の分は通常どおり一番下へ置く）。"""
    s = eng.s
    me, opp = env["you"], 1 - env["you"]
    os_ = t.setdefault("os", {})
    st = os_.setdefault("gj", {"done": 0, "wins": 0, "stopped": False, "held": None})
    times = eng.eval_expr(op["times"], env) if "times" in op else None
    key = "power" if op.get("by") == "power" else "cost"
    while not st["stopped"] and (times is None or st["done"] < times):
        if op.get("stoppable") and st.get("stop_for") != st["done"]:
            ans, d = eng.ask(t, me, "yes_no", [{"key": "yes"}, {"key": "no"}], prompt="ガチンコ・ジャッジを続ける")
            if d:
                return d
            st["stop_for"] = st["done"]
            if ans[0] == 1:
                st["stopped"] = True
                break
        if st["held"] is not None:   # 前の回に見せて保留した自分のカードは通常どおり下へ
            eng._raw_move(st["held"], "deck", "bottom")
            st["held"] = None
        mine, theirs = s.zones["deck"][me], s.zones["deck"][opp]
        if not mine or not theirs:
            break
        a, b = mine[0], theirs[0]
        eng.note_public("reveal", a)
        eng.note_public("reveal", b)
        win = (eng.chars_ro(a)[key] or 0) >= (eng.chars_ro(b)[key] or 0)
        if "mine_as" in op:
            st["held"] = a
        else:
            eng._raw_move(a, "deck", "bottom")
        eng._raw_move(b, "deck", "bottom")
        st["done"] += 1
        if win:
            st["wins"] += 1
        elif op.get("until_lose"):
            break
    env.setdefault("vars", {})[op.get("as", "wins")] = st["wins"]
    if "mine_as" in op:
        env.setdefault("vars", {})[op["mine_as"]] = [s.ref(st["held"])] if st["held"] is not None else []
    return None


_GACHA_KINDS = ("dogiragon",)   # ガチャの種類（今はドギラゴン・ガチャのみ。ドキンダム・ガチャは別表）
_GACHA_NAMES = {1: "boost", 2: "replenish", 3: "break", 4: "destroy", 5: "fight", 6: "strike"}


def _gacha_spin_ops(roll: int) -> list[dict]:
    """ドギラゴン・ガチャ 1 回分の効果（出目 → op 列）。出目は 1..6。
    1 ブースト: 山札の上から1枚をマナゾーンに置く / 2 リプレニッシュ: カードを1枚引く /
    3 ブレイク: 自分のクリーチャー1体がこのターンの終わりまでシールドをさらに1枚ブレイクする /
    4 デストロイ: 相手のコスト7以下のクリーチャー1体を破壊する /
    5 ファイト: 自分のクリーチャー1体と相手のクリーチャー1体をバトルさせる /
    6 ストライク: 自分のマナゾーンから進化ではないクリーチャー1体をバトルゾーンに出す。
    選ぶものが無い出目は、そのまま何も起きない（選べない選択は決定を出さない）。"""
    if roll == 1:
        return [{"op": "move",
                 "select": {"zone": "deck", "owner": "you", "from_top": 1},
                 "to": "mana", "reason": "put"}]
    if roll == 2:
        return [{"op": "draw", "count": 1}]
    if roll == 3:
        return [{"op": "modify",
                 "select": {"zone": "bz", "owner": "you",
                            "filter": {"types": ["creature"]}, "count": 1},
                 "mod": {"breaks_add": 1}, "duration": "end_of_turn"}]
    if roll == 4:
        return [{"op": "move",
                 "select": {"zone": "bz", "owner": "opp",
                            "filter": {"types": ["creature"], "cost_le": 7}, "count": 1},
                 "to": "graveyard", "reason": "destroy"}]
    if roll == 5:
        return [{"op": "choose",
                 "select": {"zone": "bz", "owner": "you",
                            "filter": {"types": ["creature"]}, "count": 1},
                 "as": "gacha_a"},
                {"op": "choose",
                 "select": {"zone": "bz", "owner": "opp",
                            "filter": {"types": ["creature"]}, "count": 1},
                 "as": "gacha_b"},
                {"op": "force_battle", "a": {"ref": "gacha_a"}, "b": {"ref": "gacha_b"}}]
    return [{"op": "move",
             "select": {"zone": "mana", "owner": "you",
                        "filter": {"types": ["creature"], "not_types": ["evolution"]},
                        "count": 1},
             "to": "bz", "reason": "put"}]


@op("gacha", kind="str", times="expr?")
def op_gacha(eng, t, op, env):
    """ドギラゴン・ガチャ（第268弾）: 1d6 を times 回（既定1）振り、回すたびにその出目の能力を使う。
    出目はガチャフィギュアの結果と同じく両プレイヤーに見える公開情報で、s.pub に kind: "gacha" で記録する。
    1回分の振りと効果の解決は専用タスク gacha が1回ずつ行う（後の出目は前の効果の解決が終わってから振る）。
    kind はガチャの種類（今は dogiragon のみ）。"""
    if op["kind"] not in _GACHA_KINDS:
        raise ValueError(f"unknown gacha kind '{op['kind']}'")
    n = eng.eval_expr(op.get("times", 1), env)
    eng._defer(t, [{"t": "gacha", "kind": op["kind"], "remaining": max(n, 0),
                    "controller": env["you"], "env": env}])
    return None


@task("gacha", GachaTask)
def h_gacha(eng, t):
    """ドギラゴン・ガチャの1回分: 出目を振って公開記録し、その効果を子タスクで解決してから次を振る。
    （第268弾。_defer した子タスクが終わるとこのタスクが再び頂点に来るので、spin を消して次へ進む）"""
    from .state import rng_below
    s = eng.s
    if "spin" in t:
        del t["spin"]   # 前の出目の効果の子タスクが終わった
    if t["remaining"] <= 0:
        eng._pop(t)
        return None
    roll = rng_below(s, 6) + 1
    t["spin"] = roll
    t["remaining"] -= 1
    s.pub.append({"n": len(s.pub), "turn": s.turn, "kind": "gacha",
                  "viewers": [0, 1], "player": t["controller"],
                  "result": roll, "name": _GACHA_NAMES[roll]})
    eng._push(eng._child(_gacha_spin_ops(roll), t["env"]))
    return None


@op("cast_face", face="expr?", select="selector?")
def op_cast_face(eng, t, op, env):
    """ツインパクトの呪文面を、カードをバトルゾーンに置いたまま唱える（スマッシュ・バースト）。
    唱えたことにはなる（cast イベント、コストは支払わない）が、カード自体は動かず、
    解決後に墓地へも行かない。face: "spell" なら呪文面を探す（ラスト・バースト）。
    第184弾: select を付けると選んだツインパクト・クリーチャーの呪文面を唱える
    （「バトルゾーンにある自分のツインパクト・クリーチャー1体の呪文側を、バトルゾーンに
    置いたままコストを支払わずに唱えてもよい」）。select が無い時は従来どおり自分自身。
    face の既定は -1（呪文面を探す）。"""
    s = eng.s
    if "select" in op:
        cids, d = eng.select(t, op["select"], env)
        if d:
            return d
        if not cids:
            return None
        ref = s.ref(cids[0])
    else:
        if not s.alive(env["self"]):
            return
        ref = env["self"]
    cid = ref[0]
    d = eng.cdef(cid)
    fi = op.get("face", -1)
    if fi == -1:   # 呪文面を探す（ラスト・バースト）
        fi = next((i for i, f in enumerate(d.faces) if f.spell), None)
        if fi is None:
            return
    if fi >= len(d.faces):
        return
    f = d.faces[fi]
    ref = s.ref(cid)
    tasks = [eng.ev_task({"ev": "cast", "player": env["you"], "subject": ref, "unpaid": True,
                          "from": s.cards[cid].zone}),   # 唱えた元のゾーン（第226弾）
             eng._child(f.spell, {"you": env["you"], "self": ref, "vars": dict(env.get("vars", {}))})]
    if f.after_resolve:
        tasks.append(eng._child(f.after_resolve, {"you": env["you"], "self": ref, "vars": dict(env.get("vars", {}))}))
    eng._defer(t, tasks)


@op("summon_self")
def op_summon_self(eng, t, op, env):
    """このカード自身をコストを支払ったものとして召喚する（ギャラクシールドのターン開始時召喚）。
    支払いはしないが、召喚イベントでは「コストを支払わずに召喚した」扱いにならない。"""
    task = eng.play_task(env["self"][0], env["you"], True)
    task["as_paid"] = True
    eng._defer(t, [task])


@op("play_self", cost="int", civs="any?", via="any?")
def op_play_self(eng, t, op, env):
    """このカード自身を代替コストで実行する（キリフダッシュ: 攻撃の終わりに [コスト] を支払って召喚する）。
    civs は代替コストで必要な文明（省略時はカード自身の文明）。
    via は出し方の印（第149弾。D・D・D の declare だけが via: d_d_d を付ける。キリフダッシュには付けない）。"""
    task = eng.play_task(env["self"][0], env["you"], False)
    task["cost_override"] = op["cost"]
    if "civs" in op:
        task["cost_civs"] = op["civs"]
    if "via" in op:
        task["via"] = op["via"]
    eng._defer(t, [task])
    return None


@op("swap", out="selector", out_to="zone?", **{"in": "selector"})
def op_swap(eng, t, op, env):
    """入れ替える（701.26）。out をバトルゾーンから out_to（既定は手札）へ、in をバトルゾーンへ。
    入ったクリーチャーは出たクリーチャーのタップ状態と攻撃中の状態を引き継ぐ（701.26a: 革命チェンジ）。
    out が正常に離れなければ入れ替えは行わない（701.26b）。out_to: mana が J・チェンジ。"""
    outs, d = eng.select(t, op["out"], env)
    if d:
        return d
    if "ref" in op["in"]:
        ins = eng.candidates(op["in"], env)
    else:                                   # 入る側も選べる（J・チェンジのマナゾーンから等）
        ins, d = eng.select(t, op["in"], env)
        if d:
            return d
    if not outs or not ins:
        return None
    o, i = outs[0], ins[0]
    if not eng.permits(i, "enter_bz"):   # 「コスト７以下のクリーチャーを出せない」: 入れ替えもできない
        return None
    eng._defer(t, [eng.ev_task({"ev": "move", "subject": eng.s.ref(o), "to": op.get("out_to", "hand"), "reason": "return"}, env),
                   {"t": "swap_in", "out": eng.s.ref(o), "out_gen_next": eng.s.cards[o].gen + 1,
                    "in": eng.s.ref(i), "tapped": eng.s.cards[o].tapped, "env": env}])
    return None


@op("invade", onto="selector")
def op_invade(eng, t, op, env):
    """侵略: 手札にあるこのクリーチャーを、攻撃中のクリーチャーの上に重ねて出す。
    下になったクリーチャーのタップ状態と攻撃中の状態を引き継ぐ。"""
    ontos, d = eng.select(t, op["onto"], env)
    if d:
        return d
    if not ontos:
        return None
    me = env["self"][0]
    if not eng.permits(me, "enter_bz"):
        return None
    a = ontos[0]
    if a == me:   # 第183弾: 自分自身の上には重ねられない（S級侵略の自己攻撃除外の受け皿）
        return None
    eng._defer(t, [eng.ev_task({"ev": "move", "subject": eng.s.ref(me), "to": "bz", "reason": "put", "via": "invasion"}, env),
                   {"t": "invade_fix", "cid": me, "onto": eng.s.ref(a), "tapped": eng.s.cards[a].tapped}])
    return None


@op("summon_on", parts="any", tapped="bool?")
def op_summon_on(eng, t, op, env):
    """無月の門: parts で指定した枚数を自分のゾーンから選び、その上に self をコストを支払わずに召喚する。
    parts: [{zone: <zone>, count: N, filter?: {...}}] の並び（zones: [z1, z2] なら複数ゾーンの合算から選ぶ）。
    選んだカードは進化と同じ仕組みで下に重なるが、召喚酔いとタップ状態は通常の召喚として扱う（summon_on_fix）。
    どこか1パートでも必要枚数を満たせなければ、何もしない。"""
    s = eng.s
    you = env["you"]
    me = env["self"][0]
    if s.cards[me].zone not in ("hand", "graveyard"):
        return None

    def cands(part, picked):
        zones = part.get("zones") or [part["zone"]]
        return [c for z in zones for c in eng.zlist(z, you)
                if c != me and c not in picked and s.cards[c].top_of == -1
                and eng.filter_match(c, part.get("filter", {}), env=env)]

    os_ = t["os"]
    if "picked" not in os_:
        acc = []
        for part in op["parts"]:
            if len(cands(part, acc)) < part["count"]:
                return None   # 実現可能性がない場合は誘発しても何もしない
            acc += cands(part, acc)[:part["count"]]
        os_["picked"] = []
        os_["stage"] = 0
    parts = op["parts"]
    while os_["stage"] < len(parts):
        part = parts[os_["stage"]]
        cs = cands(part, os_["picked"])
        if len(cs) < part["count"]:
            return None
        opts = [{"key": f"card:{s.cards[c].defn}", "cid": c} for c in cs]
        a, d = eng.ask(t, you, "summon_on", opts, part["count"], part["count"])
        if d:
            return d
        os_["picked"] += [cs[i] for i in a]
        os_["stage"] += 1
    picked = os_["picked"]
    if not picked:
        return None
    ev = {"ev": "move", "subject": s.ref(me), "to": "bz", "reason": "summon", "unpaid": True,
          "stack_on": s.ref(picked[0]), "stack_more": [s.ref(c) for c in picked[1:]]}
    used = {"ev": "mugon_used", "subject": s.ref(me), "player": you}   # 「無月の門能力を使った時」の追随用
    eng._defer(t, [eng.ev_task(ev, env), {"t": "summon_on_fix", "cid": me, "tapped": bool(op.get("tapped"))},
                   eng.ev_task(used, env)])
    return None


@op("attach_seal", select="selector", count="int?")
def op_attach_seal(eng, t, op, env):
    """封印を付ける: 選んだカードそれぞれに、その持ち主の山札の上から count 枚（既定1）を裏向きで重ねる。
    封印されたカードは無視される（特性・能力が機能しない）。山札が足りなければあるだけ付ける。
    すでに封印されているカードにも追加で付けられる（選択の間だけ無視を外す）。"""
    eng._seal_ok = getattr(eng, "_seal_ok", 0) + 1
    try:
        cids, d = eng.select(t, op["select"], env)
    finally:
        eng._seal_ok -= 1
    if d:
        return d
    s = eng.s
    n = op.get("count", 1)
    for cid in cids:
        c = s.mut_card(cid)
        if c.zone != "bz" or c.top_of >= 0:
            continue
        deck = s.zones["deck"][c.controller]
        for _ in range(n):
            if not deck:
                break
            top = deck[0]
            eng._raw_move(top, "bz")
            sc = s.mut_card(top)
            sc.top_of = cid
            sc.seal_of = cid
            c.seals.append(top)
    return None


@op("remove_seal", select="selector", count="int?")
def op_remove_seal(eng, t, op, env):
    """封印を外す: 選んだカードそれぞれから count 枚（既定1）までの封印を墓地に置く。
    移動イベントとして処理するので、「封印が離れた時」「封印がすべてなくなった時」が誘発する。
    対象は封印されたカードなので、選択の間だけ無視を外す。"""
    eng._seal_ok = getattr(eng, "_seal_ok", 0) + 1
    try:
        cids, d = eng.select(t, op["select"], env)
    finally:
        eng._seal_ok -= 1
    if d:
        return d
    s = eng.s
    n = op.get("count", 1)
    evs = []
    for cid in cids:
        for seal in list(s.cards[cid].seals)[:n]:
            evs.append({"ev": "move", "subject": s.ref(seal), "to": "graveyard", "reason": "seal"})
    if evs:
        eng._defer(t, [eng.ev_task(evs, env)])
    return None


@op("end_turn")
def op_end_turn(eng, t, op, env):
    """ターンの残りをとばす（次のプレイヤーのターンをすぐに始める）。今の効果の解決は最後まで行う。"""
    eng.s.skip_rest = True


@op("use_partner", of="str?", exclude_self="bool?", pending="bool?", any_number="bool?")
def op_use_partner(eng, t, op, env):
    """キズナ: 自分のクリーチャー1体の[P]能力（kind: partner）を選んで使う。
    効果の self は [P] を持つクリーチャーに移る。[P] を持つクリーチャーがいなければ何もしない。
    of: self = 候補をこのクリーチャー自身の[P]だけに絞る。exclude_self: true = 自分を候補から除く
    （どちらもキズナプラス用。第153弾）。引数なしは従来どおり全候補から1つ選ぶ（キズナ）。
    pending: true = 選んだ[P]をその場で解決せず、待機中の効果として登録する。
    キズナプラスの2つの[P]は支払いの時点でそれぞれ確定した待機効果になり、解決順は使う側が
    好きな順番で選べる（603.3a／605.1）。発生源が解決前に離れても不発にならない（110.5a）。
    any_number: true = キズナコンプ（第235弾）。好きな数だけ使う: 1件使うたびに次を聞き、
    使った能力（cid, gen, 能力index）はこの解決中は候補から外れる。0件で終えてよい。"""
    s = eng.s
    you = env["you"]
    self_cid = env["self"][0] if env.get("self") else None
    used = {tuple(u) for u in t.get("os", {}).get("up_used", [])} if op.get("any_number") else set()
    cands = []
    for c in eng.bz_tops(you):
        if op.get("of") == "self" and c != self_cid:
            continue
        if op.get("exclude_self") and c == self_cid:
            continue
        for i, ab in eng.abilities(c, "partner"):
            if (c, s.cards[c].gen, i) in used:
                continue
            cands.append((c, i, ab))
    if not cands:
        return None
    opts = [{"key": f"partner:{eng.s.cards[c].defn}:{i}", "cid": c, "ab": i} for c, i, _ in cands]
    if op.get("any_number"):
        a, d = eng.ask(t, you, "use_partner", opts, 0, 1)
    else:
        a, d = eng.ask(t, you, "use_partner", opts)
    if d:
        return d
    if not a:
        return None
    c, i, ab = cands[a[0]]
    if op.get("any_number"):
        st = t.setdefault("os", {})
        st.setdefault("up_used", []).append([c, s.cards[c].gen, i])
        again = {"t": "effect", "ops": [op], "pc": 0, "env": env,
                 "os": {"up_used": [list(u) for u in st["up_used"]]}}
        eng._defer(t, [eng._child(ab["effect"], dict(env, self=eng.s.ref(c))), again])
        return None
    if op.get("pending"):
        ref = s.ref(c)
        s.seq += 1
        p = {"pid": s.seq, "kind": "normal", "win": s.windows[-1] if s.windows else 0,
             "controller": you, "src": ref, "defn": s.cards[c].defn, "ab": i,
             "env": {"you": you, "self": ref, "event": env.get("event"), "vars": {}}}
        face = s.cards[c].face
        if face >= 0:
            p["face"] = face
        if i < 0:          # 継続的効果で得た[P]は、能力そのものを持たせる（誘発収集と同じ形）
            p["inline"] = ab
        s.pending.append(p)
        return None
    eng._defer(t, [eng._child(ab["effect"], dict(env, self=eng.s.ref(c)))])
    return None


@op("use_entry_abilities", select="selector", count="int?")
def op_use_entry_abilities(eng, t, op, env):
    """対象カードの「このクリーチャーが出た時」で始まる能力を、使う側の能力として使う（第261弾）。
    効果の self は使う側のクリーチャーのまま（対象は能力の提供だけ）。count があればその数だけ
    （候補が多い時は使う側が選ぶ）。なければすべてを印刷順に使う。"""
    s = eng.s
    you = env["you"]
    cands = []   # (対象 cid, 能力 index, ability)
    for c in eng.candidates(op["select"], env):
        fd = eng.cdef(c).face(s.cards[c].face)
        for i, ab in enumerate(fd.abilities):
            if ab.get("kind") != "trigger":
                continue
            w = ab.get("when") or {}
            if w.get("event") == "move" and w.get("to") == "bz" and w.get("subject") in (None, "self"):
                cands.append((c, i, ab))
    if not cands:
        return None
    count = op.get("count")
    chosen = cands
    if count is not None and len(cands) > count:
        opts = [{"key": f"cip:{s.cards[c].defn}:{i}", "cid": c, "ab": i} for c, i, _ in cands]
        a, d = eng.ask(t, you, "use_entry", opts, count, count)
        if d:
            return d
        chosen = [cands[j] for j in a]
    child_env = dict(env, event={**(env.get("event") or {}), "subject": env.get("self")})
    children = []
    for c, i, ab in chosen:
        if "if" in ab and not eng.eval_cond(ab["if"], child_env):
            continue
        children.append(eng._child(ab["effect"], child_env))
    if children:
        eng._defer(t, children)
    return None


@op("use_triggered_ability")
def op_use_triggered_ability(eng, t, op, env):
    """トリガーした能力を、使う側の能力として使う（第270弾）。
    env.event は trigger レコード（subject=誘発したカード、ability=誘発した能力そのもの）。
    効果の self は使う側のまま、event.subject も使う側に差し替える（第261弾の
    use_entry_abilities と同型）。trigger イベントの外（通常の効果）で呼ばれた時は
    何もしない。"""
    s = eng.s
    ev = env.get("event") or {}
    ab = ev.get("ability")
    if not isinstance(ab, dict) or not ab.get("effect"):
        return None
    child_env = dict(env, event={**(env.get("event") or {}), "subject": env.get("self")})
    if "if" in ab and not eng.eval_cond(ab["if"], child_env):
        return None
    eng._defer(t, [eng._child(ab["effect"], child_env)])
    return None


@op("choose_player", **{"as": "str"})
def op_choose_player(eng, t, op, env):
    """プレイヤーを1人選んで変数に入れる（「プレイヤーを1人選ぶ。そのプレイヤーは〜」第192弾）。
    選ぶのは効果の使用者。変数には相対指定 "you"/"opp" を入れ、player / owner / chooser の
    {var: 名前} が _rel 経由で解決する。「選んでもよい」は may の body に入れて表す。"""
    a, d = eng.ask(t, env["you"], "choose_player",
                   [{"key": "you", "player": env["you"]},
                    {"key": "opp", "player": 1 - env["you"]}], 1, 1)
    if d:
        return d
    env.setdefault("vars", {})[op["as"]] = "you" if a[0] == 0 else "opp"
    return None


@op("choose", select="selector", reveal="bool?", **{"as": "str"})
def op_choose(eng, t, op, env):
    """カードを選んで変数に入れるだけ（「〜を1体選ぶ。このターン、そのクリーチャーが〜」）。
    reveal: true の時は束縛したカードを全プレイヤーに公開する（「表向きにする」。公開集合の保持。バンドC1 U39）。"""
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    env.setdefault("vars", {})[op["as"]] = [eng.s.ref(c) for c in cids]
    if op.get("reveal"):
        for c in cids:
            eng.note_public("reveal", c)
    return None


@op("strigger", select="selector", mode="str")
def op_strigger(eng, t, op, env):
    """S・トリガーの印だけを付ける（移動を伴わない。バンドC2 U68）。
    mode: on = 本来の定義になくても S・トリガーを宣言できる／off = 宣言できない。
    印は手札にある間だけ有効で、手札を離れる移動で消える（core._raw_move）。"""
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    if op["mode"] not in ("on", "off"):
        raise ValueError(f"strigger mode must be on/off: {op['mode']}")
    for c in cids:
        if op["mode"] == "off":
            eng.s.mut_card(c).strigger_off = True
        else:
            eng.s.mut_card(c).strigger_on = True
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


@op("choose_number", min="int?", max="int?", **{"as": "str"})
def op_choose_number(eng, t, op, env):
    """「数字を1つ言う」（宣言プリミティブ。バンドC2 U97／バンドB U3）: min〜max の整数から1つ選び、
    GameState.declares に入れる。後段は式 {declared: 名前} で読む。範囲は原文どおり指定する（既定は 0〜10）。
    chooser は効果の解決者（env の you）。相手に選ばせる形は今回の範囲外（統一の未確定事項）。"""
    lo, hi = op.get("min", 0), op.get("max", 10)
    opts = [{"key": f"num:{n}", "name": str(n)} for n in range(lo, hi + 1)]
    a, d = eng.ask(t, env["you"], "choose_one", opts, 1, 1)
    if d:
        return d
    eng.s.declares[op["as"]] = lo + a[0]
    return None


@op("choose_name", **{"as": "str"})
def op_choose_name(eng, t, op, env):
    """「カードの名前を1つ言う」（宣言プリミティブ）: 対戦中の両デッキ＋各ゾーンに存在するカード名から
    1つ選び、GameState.declares に入れる。後段は式 {declared: 名前} で読む（filter の name 等）。"""
    names = sorted({eng.rules.cards[c.defn].name for c in eng.s.cards})
    opts = [{"key": f"name:{n}", "name": n} for n in names]
    a, d = eng.ask(t, env["you"], "choose_name", opts, 1, 1)
    if d:
        return d
    eng.s.declares[op["as"]] = names[a[0]]
    return None


@op("choose_civ", **{"as": "str"})
def op_choose_civ(eng, t, op, env):
    """「文明をひとつ選ぶ」（宣言プリミティブ）: 5文明から1つ選び、GameState.declares に入れる。
    後段は式 {declared: 名前} で読む（filter の civs / not_civs は文字列を単一文明として扱う）。"""
    civs = ["light", "water", "darkness", "fire", "nature"]
    opts = [{"key": f"civ:{cv}", "name": cv} for cv in civs]
    a, d = eng.ask(t, env["you"], "choose_civ", opts, 1, 1)
    if d:
        return d
    eng.s.declares[op["as"]] = civs[a[0]]
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


@op("battle_substitute", tap="bool?")
def op_battle_substitute(eng, t, op, env):
    """バトル相手の置換（when: {event: battle}）の印。実際の入れ替えは combat の _battle_substitute が行う。
    tap: true なら、代わりにバトルするクリーチャーをタップする（スーパーガードマン。第186弾）。"""
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


def _is_cip(ab: dict) -> bool:
    w = ab.get("when") or {}
    return ab.get("kind") == "trigger" and w.get("event") == "move" and w.get("to") == "bz" and w.get("subject") == "self"


def _uses_cip(x) -> bool:
    if isinstance(x, dict):
        return x.get("op") == "use_cip" or any(_uses_cip(v) for v in x.values())
    if isinstance(x, list):
        return any(_uses_cip(v) for v in x)
    return False


@op("use_cip", select="selector", optional="bool?")
def op_use_cip(eng, t, op, env):
    """選んだカードの「出た時」にトリガーする能力（when: move to bz subject self）を1つ使う
    （Jビッグ、マーダン=ロウ、Dr.富士山ッピングなど。どのゾーンのカードでもよい）。
    使うのは効果の使用者で、効果の self は選んだカードに移る。トリガー条件の if は見ない
    （能力を「使う」のでトリガーではない）。use_cip を含む能力は候補から除く（Jビッグ以外）。
    optional: true = 使わないこともできる。候補が無ければ何もしない。"""
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    you = env["you"]
    cands = [(c, i, ab) for c in cids for i, ab in eng.abilities(c, "trigger")
             if _is_cip(ab) and not _uses_cip(ab.get("effect"))]
    if not cands:
        return None
    opts = [{"key": f"cip:{eng.s.cards[c].defn}:{i}", "cid": c, "ab": i} for c, i, _ in cands]
    if op.get("optional"):
        opts.append({"key": "none"})
    a, d = eng.ask(t, you, "use_cip", opts)
    if d:
        return d
    if a[0] >= len(cands):
        return None
    c, i, ab = cands[a[0]]
    eng._defer(t, [eng._child(ab["effect"], dict(env, self=eng.s.ref(c), event=None, vars={}))])
    return None
