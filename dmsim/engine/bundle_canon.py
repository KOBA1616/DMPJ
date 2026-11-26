"""束の正準化（抽出層の語彙統合、2026-11-26）。

束の型は dmsim.engine.zone_graph（Bundle / Premise / Move）が正準だが、束化
そのものは長く2系統あった: zone_graph.bundles_of（日次経路用）と
dmsim.discovery.loop_cond.bundles（発見側が独自に作り直し）。二重解釈の
継ぎ目から、サイクルプローブ（tools/combo_hunt3_cycleprobe.py）で測った穴が
出ていた:

- play_free の宛先が静的に解決できず '?' になる移動（実測 1,994 件は全て
  src 側で、ref 未束縛が 1,333 件と支配的）
- static（常在効果）が束化されず不可視（アカシック3 は束 0 件）
- trigger/declare の前提にならないイベント 685 件（tap・break・attack_end 等）
- 前提の理由制限（destroy のみ等）と移動の条件が落ちる

本モジュールが束化の唯一の正準であり、発見側はここを使う。解釈はエンジン
実行側（dmsim/engine/ops.py、selectors.py）に一致させる:

- セレクタの ref は env の束縛を指す（selectors.candidates）。束縛は同一効果
  内の op の "as" / set_var で生まれ、束縛先のゾーンが移動元になる。move の
  "as" は移動先、play_free の "as" は出した先（ops.op_play_free の bind
  タスクはゾーン "bz" を記録する）。choose の "as" は選んだゾーンに留まる。
- play_free の宛先: resolve_to が無ければカードの種別で決まる。クリーチャー
  等はバトルゾーン、呪文は解決後に墓地へ行く（Face.resolve_to の既定
  "graveyard"。唱える対象が呪文だけに絞られている場合に限る）。
- 特殊セレクタ（under_of / crossed_to / host_of は下のカード・進化元で
  バトルゾーン、bundle_of / exlife_of / castle_of はシールド束）は
  defs.Checker が要求する特殊キーで、実体はそのゾーンにある。
- 常在効果は origin="static" の束（prem=None, moves=[]）として表現し、
  affects / mod / if を注釈 ann["static"] に持つ。無料化（allow の
  cast_free 等）はここから読める。
- 前提イベントは defs.EVENTS の全イベントを対象にする（レジストリ方式）。
  move で行き先が無い場合は「離れる」前提（to=None）として残す。
- replace は origin="replace" の束（前提は when、移動は instead から）。
  activate は origin="activate"（prem=None）、silent は turn_start 前提の
  origin="silent" 束にする。state / partner は理由付きで除外し、
  カバレッジに数える（黙って落とさない）。

対応表は凍結せず、語彙定義側の定数から生成する:
- 子 op リストのキーは base.opvocab.OP_ARGS の引数型（ops / oplists）から
- 前提イベントは cards.defs.EVENTS から
- 特殊セレクタのゾーンは defs のセレクタ検証（特殊キー群）に対応
今後の語彙拡張は定義側への追加だけでここへ流れる。

発見側固有の情報は束への「注釈」として分離する: Bundle.ann（辞書。when の
丸ごと・理由・static ペイロード等）と、互換属性 Bundle.when / Bundle.once、
Move.conds（囲む if の条件列）。正準の束そのもの（prem / moves / origin /
cost / rearm）はエンジン解釈だけから決まる。

エンジン実行そのものと zone_graph の型は変更しない。zone_graph.bundles_of は
日次経路（loop_enum 等）の互換のため残すが、新規の発見系は本モジュールを使う。
"""
from __future__ import annotations

from dmsim.base.opvocab import OP_ARGS
from dmsim.cards import defs as _defs
from dmsim.engine import zone_graph as Z

__all__ = ["bundles", "moves_of", "premise_of", "coverage", "CHILD_KEYS",
           "SPECIAL_SELECTOR_ZONES"]

# ---------------------------------------------------------------------------
# レジストリ（定義側の定数から生成。ここに手書きの対応表を足さない）
# ---------------------------------------------------------------------------

def _derive_child_keys() -> dict[str, tuple[str, ...]]:
    """OP_ARGS の引数型が ops / oplists のキーを「子 op リスト」とする。"""
    out: dict[str, tuple[str, ...]] = {}
    for op, args in OP_ARGS.items():
        ks = tuple(k for k, t in args.items()
                   if str(t).rstrip("?") in ("ops", "oplists"))
        if ks:
            out[op] = ks
    return out


CHILD_KEYS = _derive_child_keys()

#: 子 op リストのうち「リストのリスト」形式のキー（modal の modes）。
OPLIST_KEYS = {op: tuple(k for k, t in args.items()
                         if str(t).rstrip("?") == "oplists")
               for op, args in OP_ARGS.items()}
OPLIST_KEYS = {op: ks for op, ks in OPLIST_KEYS.items() if ks}

#: 特殊セレクタキー → 実体のゾーン（defs.Checker の特殊キー群に対応）。
#: under_of / crossed_to / host_of はバトルゾーンのカードの下・進化元、
#: bundle_of / exlife_of / castle_of はシールドの束に付随する。
SPECIAL_SELECTOR_ZONES = {
    "under_of": "bz",
    "crossed_to": "bz",
    "host_of": "bz",
    "bundle_of": "shield",
    "exlife_of": "shield",
    "castle_of": "shield",
}

#: 前提イベントの全体（レジストリ: defs.EVENTS）。
PREMISE_EVENTS = _defs.EVENTS

#: 唱えたことになるがカードは動かない op（移動を生まない）。
_NO_MOVE_OPS = {"cast_face", "tap", "shuffle", "modify", "mark", "force_battle",
                "battle_substitute", "cancel_attack", "flip_up", "flip_down",
                "attach_seal", "remove_seal", "castle_link", "sforce_link",
                "dswitch", "hyper_release", "uncross", "rush", "strigger",
                "action_limit", "untap_limit", "no_lose", "lose", "win",
                "end_turn", "extra_turn", "janken", "gacha",
                "use_cip", "use_entry_abilities", "use_triggered_ability",
                "use_partner", "cross_free"}

#: 複合 op（内部で公開・比較・任意使用を含むため移動へ分解しない。理由付き除外）
_COMPOSITE_OPS = {"gachinko"}


class Coverage:
    """カバレッジ測定の集計器。bundles() に渡すと内訳が貯まる。"""

    def __init__(self) -> None:
        from collections import Counter
        self.abilities = Counter()          # kind 別の能力総数
        self.bundled = Counter()            # origin 別の束の数
        self.excluded = Counter()           # 除外理由 → 件数
        self.premise_none = Counter()       # 前提にならなかったイベント → 件数
        self.qmark = Counter()              # '?' の理由 → 件数
        self.qmark_ref_names = Counter()    # 未束縛 ref の名前 → 件数
        self.ops_seen = Counter()           # 走査した op 名 → 件数
        self.ops_unwalked = Counter()       # 子 op リストを辿れなかった (op, key)
        self.moves_total = 0
        self.moves_qmark = 0
        self.owner_expr = 0                 # owner が式（dict）の移動
        self.zone_list = 0                  # zone がリストの移動元
        self.play_free_dst_inferred = Counter()  # play_free 宛先の推定内訳
        self.reason_bundles = 0             # when.reason を持つ束

    def report(self) -> dict:
        return {
            "abilities_by_kind": dict(self.abilities),
            "bundles_by_origin": dict(self.bundled),
            "abilities_excluded": dict(self.excluded),
            "premise_none_by_event": dict(self.premise_none),
            "moves_total": self.moves_total,
            "qmark_moves": self.moves_qmark,
            "qmark_reasons": dict(self.qmark),
            "qmark_ref_names": dict(self.qmark_ref_names),
            "ops_seen": dict(self.ops_seen),
            "ops_unwalked_child_lists": dict(self.ops_unwalked),
            "owner_expr_moves": self.owner_expr,
            "zone_list_moves": self.zone_list,
            "play_free_dst_inferred": dict(self.play_free_dst_inferred),
            "reason_bundles": self.reason_bundles,
        }


# ---------------------------------------------------------------------------
# 前提
# ---------------------------------------------------------------------------

def premise_of(ab: dict) -> Z.Premise | None:
    """能力の when から前提を作る。defs.EVENTS の全イベントが対象。

    zone_graph._premise との差: (1) player=opp の summon も落とさない
    （主体が無ければ owner=opp の主体で受ける）、(2) 行き先の無い move は
    「離れる」前提（to=None）として残す、(3) tap / break / attack_end 等の
    イベントも前提にする。move / cast / draw / TICKS の構築は従来と同一。
    """
    w = ab.get("when") or {}
    ev = w.get("event")
    if ev is None:
        return None
    zone = ab.get("zone", "bz")
    if ev == "summon":
        subj = w.get("subject")
        if w.get("player") == "opp" and subj is None:
            subj = {"owner": "opp"}
        return Z.Premise("move", "bz", None, subj, w.get("player"), zone)
    if ev in PREMISE_EVENTS:
        return Z.Premise(ev, w.get("to"), w.get("from"), w.get("subject"),
                         w.get("player"), zone)
    return None


# ---------------------------------------------------------------------------
# 移動
# ---------------------------------------------------------------------------

class _Ctx:
    __slots__ = ("zone", "after", "card", "prem", "bindings", "out", "cov")

    def __init__(self, zone, after, card, prem, cov):
        self.zone = zone
        self.after = after
        self.card = card
        self.prem = prem
        self.bindings: dict[str, str | None] = {}
        self.out: list[Z.Move] = []
        self.cov = cov


def _norm_owner(raw, cov) -> object:
    """owner は通常 "you"/"opp"/"owner" の文字列。式（dict）の場合は
    そのまま保持し（従来の両系統と同じ）、カバレッジに数える。"""
    if isinstance(raw, dict):
        if cov is not None:
            cov.owner_expr += 1
        return raw
    return raw if raw is not None else "you"


def _many(sel: dict) -> bool:
    """複数枚の移動か（従来の loop_cond._many と同じ判定）。"""
    c = (sel or {}).get("count", 1)
    return c in ("any", "all") or (isinstance(c, int) and c > 1)


def _flt(sel: dict):
    """フィルタは dict のコピーで持つ（従来の loop_cond と同じ形）。"""
    return dict((sel or {}).get("filter") or {})


def _resolve_src(sel: dict, ctx: _Ctx, default: str | None = None):
    """セレクタから移動元ゾーンを決める。返り値は (src, ref_self)。

    エンジンの実行解釈（selectors.candidates）に一致させる:
    ref が束縛済みなら束縛先のゾーン（zone 併記は絞り込みに過ぎない）、
    特殊セレクタは実体のゾーン、zone があればそれ。解決できなければ "?"
    を返し、カバレッジに理由を数える。
    """
    cov = ctx.cov
    ref = sel.get("ref")
    if ref == "self":
        return ctx.zone, True
    if ref == "self_moved":
        return (ctx.after or ctx.zone), True
    if ref == "crossed":
        # クロスギアをクロスしているクリーチャー（selectors の特殊参照）はバトルゾーン
        return "bz", False
    if ref:
        bound = ctx.bindings.get(ref)
        if bound:
            return bound, False
        if ref in ("event", "subject", "event.subject"):
            # イベントの主体カードは、イベントの行き先にいる
            prem = ctx.prem
            if prem is not None and prem.kind == "move" and prem.to:
                return prem.to, False
            if prem is not None and prem.zone:
                return prem.zone, False
            return ctx.zone, False
        if isinstance(ref, str) and ref.startswith("event."):
            # イベントレコードの参照（selectors.candidates の event.* 解釈）。
            # zone 併記があればそれが著者の主張する現在地として最も強い。
            z = sel.get("zone")
            if isinstance(z, str) or (isinstance(z, list) and z):
                if isinstance(z, list) and cov is not None:
                    cov.zone_list += 1
                return z, False
            if ref in ("event.attacker", "event.opponent", "event.target"):
                return "bz", False
            if ref == "event.shield":
                prem = ctx.prem
                return ("hand" if prem is not None and prem.kind == "break"
                        else "shield"), False
            prem = ctx.prem
            if prem is not None and prem.kind == "move" and prem.to:
                return prem.to, False
            if cov is not None:
                cov.qmark["ref_event_unresolved"] += 1
                cov.qmark_ref_names[str(ref)] += 1
            return "?", False
        if cov is not None:
            # 名前がどこにも束縛されていない（原文データの欠陥）か、
            # 束縛はあるが置き場所を決められないか、を分けて数える
            cov.qmark["ref_never_bound" if ref not in ctx.bindings
                      else "ref_unbound"] += 1
            cov.qmark_ref_names[str(ref)] += 1
        return "?", False
    for key, zone in SPECIAL_SELECTOR_ZONES.items():
        if key in sel:
            return zone, False
    if "zone" in sel:
        z = sel["zone"]
        if isinstance(z, list) and cov is not None:
            cov.zone_list += 1
        return z, False
    if "owner_of" in sel:
        if cov is not None:
            cov.qmark["owner_of"] += 1
        return "?", False
    if default is not None:
        return default, False
    if cov is not None:
        cov.qmark["no_zone_no_ref"] += 1
    return "?", False


def _choose_binding(sel: dict, ctx: _Ctx):
    """choose が束縛する名前の置き場所（ゾーン名。決められなければ None）。

    zone があればそれ、ref があれば元の束縛（選び直しは部分集合なので同じ場所）、
    特殊セレクタは実体のゾーン。どれも無ければ None（束縛先不明）。
    """
    z = sel.get("zone")
    if isinstance(z, (str, list)) and z:
        return z
    ref = sel.get("ref")
    if ref:
        # 参照は _resolve_src と同じ解釈（event.* は zone 併記・イベント先から）。
        # 解けなければ None（測定は黙って数えない: 実際に移動へ使われた時に数える）。
        probe = _Ctx(ctx.zone, ctx.after, ctx.card, ctx.prem, None)
        probe.bindings = ctx.bindings
        src, _ = _resolve_src(sel, probe)
        return None if src == "?" else src
    for key, zone in SPECIAL_SELECTOR_ZONES.items():
        if key in sel:
            return zone
    return None


def _play_free_dst(op: dict, sel: dict, ctx: _Ctx, ref_self: bool) -> str:
    """play_free の宛先（ops.op_play_free の実行解釈）。

    自分のツインパクト呪文面はその面の resolve_to、resolve_to があればそれ。
    無ければ: 唱える対象が呪文だけに絞られていれば解決後の墓地
    （Face.resolve_to の既定）、それ以外はバトルゾーン。
    """
    cov = ctx.cov
    if ref_self and op.get("face") == "spell" and ctx.card is not None:
        for f in ctx.card.faces or [ctx.card]:
            if f.spell:
                if cov is not None:
                    cov.play_free_dst_inferred["self_spell_face"] += 1
                return f.resolve_to
    if op.get("resolve_to"):
        if cov is not None:
            cov.play_free_dst_inferred["resolve_to"] += 1
        return op["resolve_to"]
    flt = sel.get("filter") or {}
    types = flt.get("types") or []
    if types and all(t == "spell" for t in types):
        if cov is not None:
            cov.play_free_dst_inferred["spell_filter_graveyard"] += 1
        return "graveyard"
    if cov is not None:
        cov.play_free_dst_inferred["bz_default"] += 1
    return "bz"


def _finish(ctx: _Ctx, mv: Z.Move, conds: tuple, conditional_extra=False) -> None:
    mv.conds = conds
    if conditional_extra and not mv.conditional:
        mv.conditional = True
    ctx.out.append(mv)
    if ctx.cov is not None:
        ctx.cov.moves_total += 1
        if mv.src == "?" or mv.dst == "?":
            ctx.cov.moves_qmark += 1


def _handle_op(op: dict, conds: tuple, delayed: bool, ctx: _Ctx) -> None:
    """1つの op を処理する（移動の生成・束縛の更新）。子 op リストは
    呼び出し側（_walk_ops）がレジストリのキーで辿る。"""
    cov = ctx.cov
    name = op.get("op")
    if cov is not None and name:
        cov.ops_seen[name] += 1
    zone = ctx.zone

    if name == "move":
        sel = op.get("select") or {}
        src, ref_self = _resolve_src(sel, ctx)
        dst = op.get("to")
        mv = Z.Move(src, dst, ref_self, _flt(sel),
                    bool(conds), _norm_owner(sel.get("owner", "you"), cov),
                    delayed=delayed,
                    blind=src == "deck" and "from_top" in sel,
                    many=_many(sel),
                    alias=op.get("as"),
                    ref=None if ref_self else sel.get("ref"))
        _finish(ctx, mv, conds)
        if op.get("as"):
            ctx.bindings[op["as"]] = dst
        return

    if name == "draw":
        # 従来の発見側の解釈に合わせ、ドローは blind（中身は伏せた移動）
        mv = Z.Move("deck", "hand", False, {}, bool(conds),
                    _norm_owner(op.get("player", "you"), cov), delayed=delayed,
                    draw=True, blind=True)
        _finish(ctx, mv, conds)
        return

    if name == "play_free":
        sel = op.get("select") or {}
        ref = sel.get("ref")
        ref_self = ref in ("self", "self_moved")
        if ref_self:
            src = ctx.after or zone
        elif ref or "zone" in sel or any(k in sel for k in SPECIAL_SELECTOR_ZONES):
            src, _ = _resolve_src(sel, ctx)
        else:
            src = "hand"
        dst = _play_free_dst(op, sel, ctx, ref_self)
        mv = Z.Move(src, dst, ref_self, _flt(sel), bool(conds),
                    _norm_owner(sel.get("owner", "you"), cov), delayed=delayed,
                    many=_many(sel),
                    alias=op.get("as"), ref=None if ref_self else ref)
        _finish(ctx, mv, conds)
        if op.get("as"):
            # ops.op_play_free の bind タスクは出した先（ゾーン "bz" 固定の
            # 記録ではなく、実際に置かれた先）として扱う。解決後の置き場所が
            # 墓地の呪文は墓地に束縛される。
            ctx.bindings[op["as"]] = dst
        if ref_self and op.get("face") == "spell" and ctx.card is not None:
            for f in ctx.card.faces or [ctx.card]:
                if f.spell:
                    sub = _Ctx(zone, ctx.after, ctx.card, ctx.prem, cov)
                    sub.bindings = ctx.bindings
                    _walk_ops(f.spell, (), delayed, sub)
                    for m2 in sub.out:
                        m2.conds = conds + m2.conds
                    ctx.out.extend(sub.out)
                    break
        return

    if name == "swap":
        in_sel = op.get("in") or {}
        _finish(ctx, Z.Move("bz", op.get("out_to", "hand"), False,
                            {}, bool(conds), "you", delayed=delayed),
                conds)
        in_zone = in_sel.get("zone")
        _finish(ctx, Z.Move(in_zone if isinstance(in_zone, str) else "hand",
                            "bz", True, {}, bool(conds), "you", delayed=delayed),
                conds)
        return

    if name == "put_under":
        sel = op.get("select") or {}
        src, ref_self = _resolve_src(sel, ctx, default="bz")
        _finish(ctx, Z.Move(src, "bz", ref_self, _flt(sel), bool(conds),
                            _norm_owner(sel.get("owner", "you"), cov), delayed=delayed),
                conds)
        return

    if name in ("play_self", "summon_self"):
        dst = "bz"
        if name == "play_self" and ctx.card is not None \
                and not ctx.card.is_creature():
            dst = (ctx.card.faces or [ctx.card])[0].resolve_to \
                if (ctx.card.faces or [ctx.card]) else "graveyard"
        _finish(ctx, Z.Move(zone, dst, True, {}, bool(conds), "you", delayed=delayed),
                conds)
        return

    if name == "summon_on":
        src = zone if zone in ("hand", "graveyard") else "hand"
        _finish(ctx, Z.Move(src, "bz", True, {}, bool(conds), "you", delayed=delayed),
                conds)
        return

    if name == "invade":
        _finish(ctx, Z.Move("hand", "bz", True, {}, bool(conds), "you",
                            delayed=delayed), conds)
        return

    if name == "break":
        player = op.get("player", "opp")
        if not isinstance(player, str):
            player = "opp"
        _finish(ctx, Z.Move("shield", "hand", False, {}, bool(conds),
                            player, delayed=delayed,
                            many=op.get("count") not in (None, 1)), conds)
        return

    if name == "shield_plus":
        _finish(ctx, Z.Move("deck", "shield", False, {}, bool(conds), "you",
                            delayed=delayed, blind=True,
                            many=bool(op.get("each"))
                            or op.get("count") not in (None, 1)), conds)
        return

    if name == "yobinion":
        _finish(ctx, Z.Move("deck", "bz", False, {"types": ["creature"]},
                            bool(conds), "you", delayed=delayed, blind=True), conds)
        return

    if name == "mekurade":
        flt = dict(op.get("filter") or {})
        if op.get("cost_le") is not None:
            flt.setdefault("cost_le", op["cost_le"])
        types = flt.get("types") or []
        dst = "graveyard" if types and all(t == "spell" for t in types) else "bz"
        _finish(ctx, Z.Move("deck", dst, False, flt, bool(conds),
                            "you", delayed=delayed, blind=True), conds)
        return

    if name == "move_to_event":
        prem = ctx.prem
        if prem is None or not prem.to or prem.to == "bz":
            if cov is not None:
                cov.excluded["move_to_event_no_event_dst"] += 1
            return
        sel = op.get("select") or {}
        src, ref_self = _resolve_src(sel, ctx)
        _finish(ctx, Z.Move(src, prem.to, ref_self, _flt(sel),
                            bool(conds),
                            _norm_owner(sel.get("owner", "you"), cov), delayed=delayed),
                conds)
        return

    if name == "move_under_to_event":
        prem = ctx.prem
        if prem is None or not prem.to or prem.to == "bz":
            if cov is not None:
                cov.excluded["move_under_to_event_no_event_dst"] += 1
            return
        _finish(ctx, Z.Move("bz", prem.to, False, {}, bool(conds), "you",
                            delayed=delayed), conds)
        return

    if name == "reveal_until":
        # 公開した札は山札に留まり、名前だけが束縛される（後続の move が使う）
        if op.get("as"):
            ctx.bindings[op["as"]] = "deck"
        if op.get("rest_as"):
            ctx.bindings[op["rest_as"]] = "deck"
        return

    if name in ("choose", "choose_player", "choose_race", "choose_number",
                "choose_name", "choose_civ"):
        if op.get("as"):
            ctx.bindings[op["as"]] = _choose_binding(op.get("select") or {}, ctx)
        return

    if name == "repeat":
        # 「over の各要素を as に束縛して body を回す」: as は over と同じ場所
        if op.get("as"):
            ctx.bindings[op["as"]] = ctx.bindings.get(op.get("over"))
        return

    if name == "set_var":
        val = op.get("value")
        nm = op.get("name")
        if nm:
            if isinstance(val, dict) and isinstance(val.get("select"), dict):
                z = val["select"].get("zone")
                ctx.bindings[nm] = z if isinstance(z, str) else None
            elif isinstance(val, dict) and val.get("ref") in ctx.bindings:
                ctx.bindings[nm] = ctx.bindings[val["ref"]]
            else:
                ctx.bindings[nm] = None
        return

    if name in _COMPOSITE_OPS:
        if cov is not None:
            cov.excluded[f"composite_op:{name}"] += 1
        if op.get("as"):
            ctx.bindings[op["as"]] = "deck"
        if op.get("mine_as"):
            ctx.bindings[op["mine_as"]] = "deck"
        return
    # それ以外の op はゾーン移動を生まない（_NO_MOVE_OPS ほか）


def _walk_ops(ops, conds: tuple, delayed: bool, ctx: _Ctx) -> None:
    """op 列をエンジン解釈で走査する。if は分岐ごとに条件を積み、
    delayed_trigger は遅延印を付ける。子 op リストは OP_ARGS 由来の
    レジストリ（CHILD_KEYS）で辿る（modal の各モードも含む）。"""
    for op in ops or []:
        if not isinstance(op, dict):
            continue
        name = op.get("op")
        if name == "if":
            c = conds + (op.get("cond"),)
            _walk_ops(op.get("then"), c, delayed, ctx)
            _walk_ops(op.get("else"), conds + ({"not": op.get("cond")},),
                      delayed, ctx)
            continue
        if name == "delayed_trigger":
            if ctx.cov is not None:
                ctx.cov.ops_seen[name] += 1
            _walk_ops(op.get("effect"), conds, True, ctx)
            continue
        _handle_op(op, conds, delayed, ctx)
        for key in CHILD_KEYS.get(name or "", ()):
            v = op.get(key)
            if key in OPLIST_KEYS.get(name or "", ()):
                for mode in v or []:
                    _walk_ops(mode, conds, delayed, ctx)
            elif isinstance(v, list):
                _walk_ops(v, conds, delayed, ctx)
        if ctx.cov is not None:
            # 子 op リストらしき値がレジストリ外のキーにあれば数える
            for k, v in op.items():
                if k in CHILD_KEYS.get(name or "", ()) or k == "op":
                    continue
                if isinstance(v, list) and v and isinstance(v[0], dict) \
                        and "op" in v[0]:
                    ctx.cov.ops_unwalked[f"{name}.{k}"] += 1


def moves_of(ops, zone: str = "bz", after: str | None = None, card=None,
             prem: Z.Premise | None = None, cov: Coverage | None = None,
             ) -> list[Z.Move]:
    """op 列から移動列を作る（正準）。全ての移動に m.conds が付く。"""
    ctx = _Ctx(zone, after, card, prem, cov)
    _walk_ops(ops, (), False, ctx)
    return ctx.out


def _rearms(ops) -> bool:
    """効果内に untap op があるか（従来の _rearms と同じ判定）。"""
    for op in ops or []:
        if not isinstance(op, dict):
            continue
        if op.get("op") == "untap":
            return True
        for key in CHILD_KEYS.get(op.get("op") or "", ()):
            v = op.get(key)
            if key in OPLIST_KEYS.get(op.get("op") or "", ()):
                if any(_rearms(mode) for mode in v or []):
                    return True
            elif isinstance(v, list) and _rearms(v):
                return True
        if op.get("op") == "delayed_trigger" and _rearms(op.get("effect")):
            return True
        if op.get("op") == "if" and (_rearms(op.get("then"))
                                     or _rearms(op.get("else"))):
            return True
    return False


def _annotate(b: Z.Bundle, ab: dict) -> None:
    """発見側の注釈を付ける: ann（構造化）と互換属性 when / once。"""
    w = ab.get("when") or {}
    ann = {"kind": ab.get("kind")}
    if w:
        ann["when"] = w
        if w.get("reason") is not None:
            ann["reason"] = w["reason"]
        if w.get("via") is not None:
            ann["via"] = w["via"]
        if w.get("unpaid") is not None:
            ann["unpaid"] = w["unpaid"]
    if ab.get("once_per_turn"):
        ann["once"] = True
    b.ann = ann
    b.when = w
    b.once = bool(ab.get("once_per_turn"))


def _ability_bundle(cd, ab: dict, cov: Coverage | None) -> Z.Bundle | None:
    """1能力から束を作る。作らなければ理由をカバレッジに数えて None。"""
    kind = ab.get("kind")
    if cov is not None:
        cov.abilities[kind] += 1
    zone = ab.get("zone", "bz")

    if kind == "static":
        b = Z.Bundle(cd.id, cd.name, None, [], origin="static")
        b.ann = {"kind": "static",
                 "static": {"affects": ab.get("affects"), "mod": ab.get("mod"),
                            "if": ab.get("if"), "keyword": ab.get("keyword")}}
        b.when = {}
        b.once = False
        if cov is not None:
            cov.bundled["static"] += 1
        return b

    if kind in ("state", "partner"):
        if cov is not None:
            cov.excluded[f"kind:{kind}"] += 1
        return None

    if kind == "activate":
        ms = moves_of(ab.get("effect"), zone, card=cd, cov=cov)
        if not ms:
            if cov is not None:
                cov.excluded["activate:no_moves"] += 1
            return None
        b = Z.Bundle(cd.id, cd.name, None, ms, origin="activate",
                     rearm=_rearms(ab.get("effect")))
        _annotate(b, ab)
        b.ann["cost"] = ab.get("cost")
        if cov is not None:
            cov.bundled["activate"] += 1
        return b

    if kind == "silent":
        pr = Z.Premise("turn_start", None, None, "self", "you", zone)
        ms = moves_of(ab.get("effect"), zone, card=cd, prem=pr, cov=cov)
        if not ms:
            if cov is not None:
                cov.excluded["silent:no_moves"] += 1
            return None
        b = Z.Bundle(cd.id, cd.name, pr, ms, origin="silent",
                     rearm=_rearms(ab.get("effect")))
        _annotate(b, ab)
        if cov is not None:
            cov.bundled["silent"] += 1
        return b

    if kind == "replace":
        pr = premise_of(ab)
        if pr is None:
            if cov is not None:
                cov.excluded["replace:no_premise"] += 1
                cov.premise_none[(ab.get("when") or {}).get("event")] += 1
            return None
        ms = moves_of(ab.get("instead"), zone,
                      after=pr.to,
                      card=cd, prem=pr, cov=cov)
        if not ms and not _rearms(ab.get("instead")):
            if cov is not None:
                cov.excluded["replace:no_moves"] += 1
            return None
        b = Z.Bundle(cd.id, cd.name, pr, ms, origin="replace",
                     rearm=_rearms(ab.get("instead")))
        _annotate(b, ab)
        if cov is not None:
            cov.bundled["replace"] += 1
            if (ab.get("when") or {}).get("reason") is not None:
                cov.reason_bundles += 1
        return b

    if kind in ("trigger", "declare"):
        pr = premise_of(ab)
        if pr is None:
            if cov is not None:
                ev = (ab.get("when") or {}).get("event")
                cov.excluded["trigger:no_premise"] += 1
                cov.premise_none[ev] += 1
            return None
        ms = moves_of(ab.get("effect"), zone,
                      after=pr.to,
                      card=cd, prem=pr, cov=cov)
        if ab.get("if") is not None:
            for m in ms:
                m.conds = (ab["if"],) + tuple(m.conds or ())
                m.conditional = True
        rearm = _rearms(ab.get("effect"))
        if not ms and not rearm:
            if cov is not None:
                cov.excluded["trigger:no_moves"] += 1
            return None
        b = Z.Bundle(cd.id, cd.name, pr, ms, origin="trigger", rearm=rearm)
        _annotate(b, ab)
        if cov is not None:
            cov.bundled["trigger"] += 1
            if (ab.get("when") or {}).get("reason") is not None:
                cov.reason_bundles += 1
        return b

    if cov is not None:
        cov.excluded[f"kind:unknown:{kind}"] += 1
    return None


def _play_premise() -> Z.Premise:
    """「手札から出す」疑似前提（従来の loop_cond と同じ形）。
    手札へ戻す移動がこの前提を受け、再登場のサイクルとして読める。"""
    return Z.Premise("move", "hand", subject="self", zone="hand")


def _direct_move(src: str, dst: str) -> Z.Move:
    m = Z.Move(src, dst, True)
    m.conds = ()
    return m


def bundles(rules, cov: Coverage | None = None) -> list[Z.Bundle]:
    """全カードの束（正準）。並びは従来の loop_cond.bundles と同じ
    （面ごと: 無料条件 → 能力 → 呪文、最後に召喚）。"""
    out: list[Z.Bundle] = []
    for cd in rules.cards.values():
        for f in cd.faces or [cd]:
            if f.free_if and f.is_creature():
                b = Z.Bundle(cd.id, cd.name, _play_premise(),
                             [_direct_move("hand", "bz")], origin="free")
                b.ann = {"kind": "free"}
                b.when = {}
                b.once = False
                out.append(b)
                if cov is not None:
                    cov.bundled["free"] += 1
            for ab in f.abilities:
                b = _ability_bundle(cd, ab, cov)
                if b is not None:
                    out.append(b)
            if f.spell:
                ms = [_direct_move("hand", f.resolve_to)]
                ms += moves_of(f.spell, card=cd, cov=cov)
                ms += moves_of(f.after_resolve, f.resolve_to, card=cd, cov=cov)
                b = Z.Bundle(cd.id, cd.name, _play_premise(), ms,
                             origin="spell", cost=f.cost)
                b.ann = {"kind": "spell"}
                b.when = {}
                b.once = False
                out.append(b)
                if cov is not None:
                    cov.bundled["spell"] += 1
        if cd.is_creature():
            b = Z.Bundle(cd.id, cd.name, _play_premise(),
                         [_direct_move("hand", "bz")], origin="summon",
                         cost=cd.cost)
            b.ann = {"kind": "summon"}
            b.when = {}
            b.once = False
            out.append(b)
            if cov is not None:
                cov.bundled["summon"] += 1
    return out


def coverage(rules) -> dict:
    """全カードのカバレッジを測って辞書で返す（常設の測定）。"""
    cov = Coverage()
    bundles(rules, cov)
    rep = cov.report()
    n_cards = len(rules.cards)
    total_ab = sum(rep["abilities_by_kind"].values())
    bundled_ab = sum(v for k, v in rep["bundles_by_origin"].items()
                     if k in ("trigger", "replace", "activate", "silent",
                              "static"))
    rep["cards"] = n_cards
    rep["abilities_total"] = total_ab
    rep["abilities_bundled"] = bundled_ab
    rep["ability_bundle_rate"] = round(bundled_ab / total_ab, 4) if total_ab else 0
    return rep
