"""ゾーン変換グラフ: 実カードの効果から「どのゾーンからどのゾーンへカードが動くか」を静的に取り出し、
互いに補完し合って循環する（ループになりうる）カードの組を列挙する。

人間のデッキビルダーが「手札→盤面と盤面→手札のように、ゾーンの変換を相互にするカードの組が見つかると、
大体ループになる」と見るのと同じ観点を機械でやる。結果はループ候補（部品の組）で、実際にループするかは
シミュレーション（dmsim.loop / dmsim.loop_first）で確かめる。

- バンドル: 1つの誘発能力（または呪文・クリーチャーを出す行為）。前提（何が起きた時か）と、効果の中のカードの移動の一覧。
  前提の種類: カードの移動（ゾーンに入った時・破壊された時など）、呪文を唱えた時、ドローした時、
  攻撃時・バトルに勝った時・ブロック時・ターン開始・ターン終了。
- 呪文は「手札に入ったら唱えられる」バンドル（解決後は resolve_to へ）、クリーチャーは「手札に入ったら出せる」バンドルを
  暗黙に持つ。唱える・出すマナは Cycle.mana() で見る（払ったマナを戻す手段は別に要る）。
- バンドル A の移動が B の前提を満たす（A がカードを B の前提ゾーンへ動かし、B の主語に合うカードである）時、A → B。
  ドローや山札の上を動かす効果は特定のカードを狙えないので「運任せ」（Cycle.sure=False）。
- ターン開始・終了、ブロックは時間や相手の行動で起きるので、循環に含まれると period が gated:... になる
  （そのターンに1回起きる時計であって、ターン内で無限に回るループではない）。攻撃時・バトルに勝った時は
  アンタップを含む効果が循環にあれば自分の判断で何度でもできるので in_turn、なければ1体につき1回で回らない。
- この有向グラフの閉路がループ候補。閉路に含まれる移動の合計がゾーンごとの収支（差分）になる。
  動的な検出（dmsim.loop）が出す差分と一致する（サガ: 山札-1・墓地+1）。
- 条件つき（if / may の中）の移動は conditional として印をつける。数えるときは「起きる」前提で足す。
- 限界: 静的な過大近似。同名の別のコピー・カードが今どのゾーンにあるか・マナや召喚酔い・置換効果・
  継続的効果・選択肢の有無は見ない。候補は dmsim.loop / loop_first で確かめる。

  python -m dmsim.zone_graph --max-cards 2 --top 20
"""
from __future__ import annotations

from dataclasses import dataclass, field

CHILD_KEYS = ("then", "else", "body")


TICKS = ("attack", "battle_start", "battle_win", "block", "turn_start", "turn_end")   # 時間や戦闘の流れで起きる（カードの移動では起きない）


@dataclass
class Move:
    src: str                  # 動かす前のゾーン（"bz" "graveyard" "hand" "deck" ...）
    dst: str
    ref_self: bool = False    # 自分自身を動かす
    flt: dict = field(default_factory=dict)
    conditional: bool = False
    owner: str = "you"
    draw: bool = False        # ドロー（draw イベントも起こす）
    delayed: bool = False     # 遅延誘発の中（後のターンに起こる）
    blind: bool = False       # 山札の上から（引く・削る）。どのカードが動くか選べず、特定のカードを狙えない
    many: bool = False        # 複数枚を動かしうる（count が any / all / 2以上）。収支の目安用で、閉路の判定には使わない
    alias: str | None = None  # この移動で動かした札の名前（op の as）
    ref: str | None = None    # 前の移動で名前を付けた札を動かす（select.ref、self 以外）

    def src_zones(self) -> tuple:
        """移動元ゾーンの候補（src がリストなら「どれか」の選択肢。文字列なら1つ）。"""
        return tuple(self.src) if isinstance(self.src, (list, tuple)) else (self.src,)

    def owner_may_be(self, who: str) -> bool:
        """持ち主が who でありうるか（"any" は choose_player で自分か相手を選ぶ）。"""
        return self.owner == who or self.owner == "any"

    def from_any(self, *zones) -> bool:
        """移動元の候補のどれかが zones に入るか（リストの src を取りこぼさない）。"""
        return any(z in zones for z in self.src_zones())


@dataclass
class Premise:
    """誘発の前提。kind は move / cast / draw / TICKS のどれか。"""
    kind: str
    to: str | None = None
    frm: str | None = None
    subject: object = None    # None / "self" / {owner, filter}
    player: str | None = None
    zone: str = "bz"          # その能力が働くゾーン
    draw_gated: bool = False  # draw 前提のみ: ターン開始時のドロー(turn_draw)や「n枚目」(ord)に限る。効果のドローでは満たせない


@dataclass
class Bundle:
    card: str                 # カードID
    name: str
    prem: Premise | None      # None なら自分から起動するもの
    moves: list[Move]
    origin: str = "trigger"   # trigger / spell / summon
    cost: int = 0             # 唱える・召喚するのに払うマナ（origin が spell / summon の時）
    rearm: bool = False       # アンタップを含む（攻撃・バトルし直せる）

    @property
    def premise(self) -> str | None:       # 互換: "enter:bz" など
        p = self.prem
        return f"enter:{p.to}" if p and p.kind == "move" and p.to else (p.kind if p else None)

    @property
    def subject_self(self) -> bool:
        return self.prem is not None and self.prem.subject == "self"


def _walk(ops, cond=False, delayed=False):
    for op in ops:
        o = op.get("op")
        if o in ("move", "draw", "play_free", "put_under", "swap", "untap"):
            yield op, cond, delayed
        for k in CHILD_KEYS:
            if k in op:
                yield from _walk(op[k], cond or o in ("if", "may"), delayed)
        if o == "delayed_trigger":
            yield from _walk(op.get("effect", []), True, True)


def _rearms(ops) -> bool:
    """効果の中にアンタップがある（もう一度攻撃できる）か。"""
    return any(op["op"] == "untap" for op, _, _ in _walk(ops))


def _many(sel: dict) -> bool:
    c = sel.get("count", 1)
    return c in ("any", "all") or (isinstance(c, int) and c > 1)


def _moves_of(ops, zone: str = "bz") -> list[Move]:
    """zone: その効果を持つ能力が働くゾーン（「自分を動かす」の動かす前のゾーン）。"""
    out = []
    for op, cond, dl in _walk(ops):
        o = op["op"]
        if o == "untap":
            continue
        if o == "draw":
            out.append(Move("deck", "hand", conditional=cond, draw=True, delayed=dl, blind=True,
                            owner=op.get("player", "you")))
        elif o == "move":
            sel = op["select"]
            ref_self = sel.get("ref") == "self"
            src = zone if ref_self else sel.get("zone", "?")
            out.append(Move(src, op["to"], ref_self, dict(sel.get("filter", {})), cond, sel.get("owner", "you"),
                            delayed=dl, blind=src == "deck" and "from_top" in sel, many=_many(sel),
                            alias=op.get("as"), ref=None if ref_self else sel.get("ref")))
        elif o == "play_free":
            sel = op["select"]
            ref_self = sel.get("ref") == "self"
            out.append(Move(sel.get("zone", "hand"), op.get("resolve_to", "bz"), ref_self, dict(sel.get("filter", {})), cond,
                            sel.get("owner", "you"), delayed=dl, many=_many(sel), alias=op.get("as")))
        elif o == "swap":   # 革命チェンジ: out（攻撃クリーチャー）が手札へ、in（自分）がバトルゾーンへ
            out.append(Move("bz", "hand", False, {}, cond, delayed=dl))
            out.append(Move("hand", "bz", True, {}, cond, delayed=dl))
    return out


def draw_feeds(m: "Move", p: "Premise") -> bool:
    """効果のドロー m が draw 前提 p を満たせるか。引く主体を区別する:
    前提が自分(you/None)のドローなら自分が引く移動、opp なら相手が引く移動だけ。
    ターン開始のドロー・「n枚目」に限る前提は、効果のドローでは満たせない。"""
    if not m.draw or p.draw_gated:
        return False
    want = "opp" if p.player == "opp" else "you"
    own = m.owner if isinstance(m.owner, str) else "you"
    if p.player == "each" or own == "each":
        return True
    return own == want


def _premise(ab) -> Premise | None:
    w = ab.get("when") or {}
    ev = w.get("event")
    if ev == "summon":   # 「出した時」（召喚・踏み倒し）はバトルゾーンに入ったこと。相手が出した時は自分の移動では満たせない
        return None if w.get("player") == "opp" else Premise("move", "bz", subject=w.get("subject"), zone=ab.get("zone", "bz"))
    if ev not in ("move", "cast", "draw", *TICKS) or (ev == "move" and "to" not in w):
        return None
    return Premise(ev, w.get("to"), w.get("from"), w.get("subject"), w.get("player"), ab.get("zone", "bz"),
                   draw_gated=ev == "draw" and bool(w.get("turn_draw") or w.get("ord")))


def bundles_of(rules) -> list[Bundle]:
    out = []
    for cd in rules.cards.values():
        faces = cd.faces or [cd]
        for f in faces:
            if f.free_if and f.is_creature():   # G・ゼロ: 手札にある間、コストなしでバトルゾーンへ（手札に入ったことが前提）
                out.append(Bundle(cd.id, cd.name, Premise("move", "hand", subject="self", zone="hand"),
                                  [Move("hand", "bz", True)], origin="free"))
            for ab in f.abilities:
                if ab.get("kind") not in ("trigger", "declare"):
                    continue
                pr = _premise(ab)
                ms = _moves_of(ab.get("effect", []), ab.get("zone", "bz"))
                if pr and (ms or _rearms(ab.get("effect", []))):
                    out.append(Bundle(cd.id, cd.name, pr, ms, rearm=_rearms(ab.get("effect", []))))
            if f.spell:
                # 呪文: 手札から唱えて墓地へ。手札に入ったら（再び）唱えられる
                ms = ([Move("hand", f.resolve_to, True)] + _moves_of(f.spell)
                      + _moves_of(f.after_resolve, f.resolve_to))
                out.append(Bundle(cd.id, cd.name, Premise("move", "hand", subject="self", zone="hand"), ms,
                                  origin="spell", cost=f.cost))
        if "creature" in cd.types:   # クリーチャー: 手札から出す。手札に入ったら出せる
            out.append(Bundle(cd.id, cd.name, Premise("move", "hand", subject="self", zone="hand"),
                              [Move("hand", "bz", True)], origin="summon", cost=cd.cost))
    return out


def _match(flt: dict, cd) -> bool:
    """移動の絞り込みが、そのカードに当てはまりうるか（式や未知の条件は通す）。"""
    types = set(cd.types) | ({"creature"} if getattr(cd, "ace", False) else set())   # ACEタマシードはバトルゾーン以外ではクリーチャー（タマシード/クリーチャー）
    if "types" in flt and not set(flt["types"]) & types:
        return False
    if "not_types" in flt and set(flt["not_types"]) >= types:
        return False
    if "races" in flt and not set(flt["races"]) & set(cd.races):
        return False
    if "race_has" in flt and not any(flt["race_has"] in r for r in cd.races):
        return False
    if isinstance(flt.get("cost_le"), int) and cd.cost > flt["cost_le"]:
        return False
    if isinstance(flt.get("cost_ge"), int) and cd.cost < flt["cost_ge"]:
        return False
    if "civs" in flt and not set(flt["civs"]) & set(cd.civs):
        return False
    if "name_has" in flt and flt["name_has"] not in cd.name:
        return False
    if "not_name" in flt and flt["not_name"] == cd.name:
        return False
    return True


def _compat(mf: dict, sf: dict) -> bool:
    """「動かす対象の絞り込み」と「誘発の主語の絞り込み」が重なりうるか（片方しか書かない条件は通す）。"""
    for k in ("types", "races", "civs"):
        if k in mf and k in sf and not set(mf[k]) & set(sf[k]):
            return False
    return True


def _subject_ok(m: Move, a: Bundle, prem: Premise, bcd, rules) -> bool:
    """a の移動 m が動かしたカードが、b の前提の主語になりうるか。"""
    subj = prem.subject
    if subj is None:
        return True
    if subj == "self":
        if m.owner == "opp":   # 相手のカードを相手の手札などへ動かしても、自分のカードの前提は満たさない
            return False
        return (a.card == bcd.id) if m.ref_self else _match(m.flt, bcd)
    if not isinstance(subj, dict):   # "self" 以外の文字列は主語を絞らない
        return True
    sf = subj.get("filter", {})
    if (subj.get("owner") == "opp") != (m.owner == "opp") and subj.get("owner") in ("you", "opp"):
        return False
    if m.ref_self:
        return _match(sf, rules.cards[a.card])
    return _compat(m.flt, sf)


def feeds(a: Bundle, b: Bundle, rules) -> int:
    """a の効果が b の前提を満たしうるか。0=満たさない、1=山札の上から動かす効果が偶然当たる時だけ、2=狙って満たせる。"""
    p = b.prem
    if p is None:
        return 0
    bcd = rules.cards[b.card]

    def best(ms):
        r = 0
        for m in ms:
            r = max(r, 1 if m.blind else 2)
        return r

    if p.kind == "move":
        return best(m for m in a.moves if m.dst == p.to and (p.frm is None or m.src == p.frm)
                    and _subject_ok(m, a, p, bcd, rules))
    if p.kind == "cast":
        if a.origin != "spell":
            return 0
        sf = (p.subject or {}).get("filter", {}) if isinstance(p.subject, dict) else {}
        return 2 if _match(sf, rules.cards[a.card]) else 0
    if p.kind == "draw":
        return 2 if any(draw_feeds(m, p) for m in a.moves) else 0
    # TICKS: そのターンの流れで起きる。a の効果で b のカードがその働くゾーンにあれば、次の機会にも誘発する
    if a is b:
        if p.kind in ("attack", "battle_win") and not a.rearm:
            return 0                  # 攻撃もバトルも1体につき1回。アンタップがなければ繰り返せない
        return 0 if any(m.ref_self and m.src == p.zone for m in a.moves) else 2
    return best(m for m in a.moves if m.dst == p.zone and m.owner != "opp" and (a.card == b.card if m.ref_self else _match(m.flt, bcd)))


@dataclass
class Cycle:
    bundles: list[Bundle]
    sure: bool = True         # すべての受け渡しが狙って満たせる（偶然のドロー頼みでない）

    @property
    def cards(self) -> list[str]:
        return sorted({b.card for b in self.bundles})

    def gates(self) -> list[str]:
        """時間や戦闘の流れに頼る誘発（ターン開始・攻撃時など）。空なら、ターン内でカードの移動だけで回る。"""
        rearm = any(b.rearm for b in self.bundles)    # アンタップがあれば、攻撃・バトルは自分の判断で何度でもできる
        return sorted({b.prem.kind for b in self.bundles if b.prem and b.prem.kind in TICKS
                       and not (rearm and b.prem.kind in ("attack", "battle_win"))})

    @property
    def period(self) -> str:
        g = self.gates()
        return "in_turn" if not g else "gated:" + ",".join(g)

    def mana(self) -> int:
        """1周で払うマナの合計（呪文を唱える・クリーチャーを出す分）。マナが戻る手段が別に要る。"""
        return sum(b.cost for b in self.bundles if b.origin in ("spell", "summon"))

    def delta(self) -> dict[str, int]:
        d: dict[str, int] = {}
        for b in self.bundles:
            for m in b.moves:
                if m.owner == "opp":
                    continue
                s, e = (m.src if isinstance(m.src, str) else "/".join(map(str, m.src))), (m.dst if isinstance(m.dst, str) else "/".join(map(str, m.dst)))
                d[s] = d.get(s, 0) - 1
                d[e] = d.get(e, 0) + 1
        return {k: v for k, v in d.items() if v}

    def opp_delta(self) -> dict[str, int]:
        """相手のゾーンの収支（山札を削る・シールドを割るなど）。"""
        d: dict[str, int] = {}
        for b in self.bundles:
            for m in b.moves:
                if m.owner == "opp":
                    s, e = (m.src if isinstance(m.src, str) else "/".join(map(str, m.src))), (m.dst if isinstance(m.dst, str) else "/".join(map(str, m.dst)))
                    d[s] = d.get(s, 0) - 1
                    d[e] = d.get(e, 0) + 1
        return {k: v for k, v in d.items() if v}

    def conditional(self) -> bool:
        return any(m.conditional for b in self.bundles for m in b.moves)


def find_cycles(rules, max_cards: int = 2, max_len: int = 4) -> list[Cycle]:
    bs = bundles_of(rules)
    st: dict = {}      # 受け渡せる組だけを持つ（全組を持つと札が多い時にメモリを使い切る）
    succ: dict = {i: [] for i in range(len(bs))}
    # feeds(a, b) が 0 でない必要条件で a を絞る（結果は総当たりと同じ。succ は j の昇順に並べ直す）
    by_dst: dict = {}
    drawers, spells = [], []
    for i, a in enumerate(bs):
        for z in {m.dst for m in a.moves}:
            by_dst.setdefault(z, []).append(i)
        if any(m.draw for m in a.moves):
            drawers.append(i)
        if a.origin == "spell":
            spells.append(i)
    for j, b in enumerate(bs):
        p = b.prem
        if p is None:
            continue
        if p.kind == "move":
            cand = by_dst.get(p.to, [])
        elif p.kind == "cast":
            cand = spells
        elif p.kind == "draw":
            cand = drawers
        else:
            cand = sorted(set(by_dst.get(p.zone, [])) | {j})
        for i in cand:
            v = feeds(bs[i], b, rules)
            if v:
                st[i, j] = v
                succ[i].append(j)
    for i in succ:
        succ[i].sort()
    seen, out = set(), []

    from bisect import bisect_left

    def dfs(start, path):
        i = path[-1]
        sj = succ[i]
        k0 = bisect_left(sj, start)            # succ は昇順: start より小さい j は何もしない
        if k0 < len(sj) and sj[k0] == start:   # 閉じる（総当たりの順でも start は start より大きい j より先）
            key = tuple(sorted(path))
            if key not in seen:
                seen.add(key)
                out.append(Cycle([bs[k] for k in path], all(st[x, y] == 2 for x, y in zip(path, path[1:] + path[:1]))))
            k0 += 1
        if len(path) >= max_len:
            return
        pcards = {bs[k].card for k in path}
        room = len(pcards) < max_cards
        for j in sj[k0:]:
            if j not in path and (room or bs[j].card in pcards):
                dfs(start, path + [j])

    for s in range(len(bs)):
        dfs(s, [s])
    out.sort(key=lambda c: (not c.sure, c.period != 'in_turn', len(c.cards), len(c.bundles)))
    return out


def main(argv=None):
    import argparse

    from ..cards.defs import load_rules
    ap = argparse.ArgumentParser(description="ゾーン変換の循環（ループ候補）を列挙する")
    ap.add_argument("--max-cards", type=int, default=2)
    ap.add_argument("--max-len", type=int, default=4)
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--period", default=None, help="in_turn なら移動だけで回るものに絞る")
    a = ap.parse_args(argv)
    rules = load_rules()
    cyc = [c for c in find_cycles(rules, a.max_cards, a.max_len) if a.period in (None, c.period)]
    for c in cyc[:a.top]:
        print(f"{' + '.join(rules.cards[x].name for x in c.cards)}  [{c.period}{'' if c.sure else ' 運任せ'}] 差分={c.delta()} 相手={c.opp_delta()} マナ={c.mana()}"
              f"  {'条件つき' if c.conditional() else ''}")
    print(f"{len(cyc)} 件")


if __name__ == "__main__":
    main()
