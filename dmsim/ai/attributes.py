"""カード属性ベクトル（Phase 26-4）。

2026-11-23 の導入 todo（P1）にあった「カードID丸暗記を排した共通
属性表現（語彙変換資産を特徴抽出器として再利用）」の実装。変換済み
語彙データ（load_rules の CardDef）から、全カード共通の属性ベクトル
を決定的に生成する。学習対戦に出ないカードも属性ベクトルを持つため、
属性表現のモデル（model_attr.AttrModel）は未学習カードにも意味の
ある表現を与えられる（ID 埋め込みでは未学習カードは初期値のまま）。

属性は面（ツインパクトは両面）を合算して作る。ブロック構成:
  基本      コスト（最小/最大）、パワー、種別フラグ、ブレイカー数など
  文明      6文明の有無（全フェイスの和集合）
  タイプ    creature/spell/evolution/tamaseed/cross_gear/field/…
  種族      全カード頻度 top64 の有無＋その他種族の数
  キーワード 頻出キーワード（静的キーワード含む）の有無＋希少分
  能力種別  static/trigger/replace/declare・activate の個数
  誘発      イベント種別、move の移動先（cip 判定）、主体
  効果op    効果アトム（op）の語彙ごとの個数
  move内訳  移動先ゾーン、理由、対象の所有者、対象ゾーン
  派生動詞  破壊/蘇生/マナ加速/バウンス/墓地肥やし等の意味カテゴリ
  modify    パワー修整/キーワード付与/否定/許可/離れない 等の内訳
  特殊機構  代替コスト、墓地唱え、S・バック、タップイン、進化元…
  対象      対象の取り方（クリーチャー対象、コスト指定、種族指定…）

語彙（種族・キーワード・イベント・op の採用リスト）はコーパス全体の
頻度から閾値で決定的に選ぶ。採用リストは特徴名として返し、モデル
ファイルにも一緒に保存する（model_attr.AttrModel.save）。
"""
from __future__ import annotations

from collections import Counter

import numpy as np

CIVS = ["fire", "water", "nature", "light", "darkness", "zero"]
TYPE_GROUPS = [
    ("creature", {"creature"}),
    ("spell", {"spell"}),
    ("evolution", {"evolution"}),
    ("tamaseed", {"tamaseed"}),
    ("cross_gear", {"cross_gear"}),
    ("field", {"field", "d2_field", "dragonic_field"}),
    ("exile_creature", {"exile_creature"}),
    ("other_type", {"g_castle", "dream_creature"}),
]
MOVE_TOS = ["graveyard", "hand", "mana", "deck", "bz", "shield"]
MOVE_REASONS = ["put", "destroy", "return", "discard", "charge", "draw",
                "break", "summon"]
SELECT_ZONES = ["bz", "deck", "hand", "graveyard", "mana", "shield"]
BREAKERS = {"double_breaker": 2, "triple_breaker": 3, "quad_breaker": 4,
            "world_breaker": 5, "infinite_breaker": 6, "g_breaker": 2}
SPECIAL_FLAGS = ["alt_cost", "grave_cast", "s_back", "tap_entry",
                 "evolve_from", "hyper", "neo", "ace", "star", "s_max",
                 "galaxy_shield", "soul_shift", "free_if", "recycle",
                 "rinne"]

RACE_TOP = 64
KW_MIN, KW_MAX = 10, 56     # キーワード採用: 頻度>=10、最大56
EV_MIN, EV_MAX = 5, 32      # 誘発イベント採用: 頻度>=5、最大32
OP_MIN, OP_MAX = 15, 56     # 効果op採用: 頻度>=15、最大56


def _units(cd) -> list:
    """属性を集める単位（ツインパクトは各フェイス、通常はカード自体）。"""
    faces = getattr(cd, "faces", None)
    return list(faces) if faces else [cd]


def _effect_lists(u):
    for key in ("spell", "sst_spell", "stp_spell", "odrive_spell"):
        v = getattr(u, key, None)
        if v:
            yield v


def _walk(node, on_op, on_mod):
    """効果構造を再帰走査し、op 辞書と mod 辞書をコールバックへ渡す。"""
    if isinstance(node, dict):
        if "op" in node:
            on_op(node)
        mod = node.get("mod")
        if isinstance(mod, dict):
            on_mod(mod)
        for v in node.values():
            _walk(v, on_op, on_mod)
    elif isinstance(node, (list, tuple)):
        for v in node:
            _walk(v, on_op, on_mod)


def _zone_set(z) -> set[str]:
    if isinstance(z, str):
        return {z}
    if isinstance(z, (list, tuple)):
        return {x for x in z if isinstance(x, str)}
    return set()


class _Corpus:
    """採用語彙（頻度で決まる）をコーパス全体から決める。"""

    def __init__(self, rules):
        races: Counter = Counter()
        kws: Counter = Counter()
        events: Counter = Counter()
        ops: Counter = Counter()
        for cd in rules.cards.values():
            for u in _units(cd):
                for r in getattr(u, "races", None) or []:
                    races[r] += 1
                for k in getattr(u, "keywords", None) or []:
                    kws[k] += 1
                for ab in getattr(u, "abilities", None) or []:
                    if not isinstance(ab, dict):
                        continue
                    if ab.get("keyword"):
                        kws[ab["keyword"]] += 1
                    w = ab.get("when")
                    if isinstance(w, dict) and w.get("event"):
                        events[w["event"]] += 1

                def on_op(o):
                    ops[o["op"]] += 1
                _walk(getattr(u, "abilities", None), on_op, lambda m: None)
                for lst in _effect_lists(u):
                    _walk(lst, on_op, lambda m: None)

        def pick(counter, mn, mx):
            items = [(k, c) for k, c in counter.items() if c >= mn]
            items.sort(key=lambda kv: (-kv[1], kv[0]))
            return [k for k, _ in items[:mx]]

        self.races = pick(races, 1, RACE_TOP)
        self.race_idx = {r: i for i, r in enumerate(self.races)}
        self.kws = pick(kws, KW_MIN, KW_MAX)
        self.kw_idx = {k: i for i, k in enumerate(self.kws)}
        self.kw_all = set(kws)
        self.events = pick(events, EV_MIN, EV_MAX)
        self.ev_idx = {e: i for i, e in enumerate(self.events)}
        self.ev_all = set(events)
        self.ops = pick(ops, OP_MIN, OP_MAX)
        self.op_idx = {o: i for i, o in enumerate(self.ops)}
        self.op_all = set(ops)


def _cap(x: float, cap: float) -> float:
    return min(x, cap) / cap


class _CardFeat:
    """1枚分の属性を数える作業領域。"""

    def __init__(self, corpus: _Corpus):
        self.c = corpus
        self.basic: dict[str, float] = {}
        self.civs: set[str] = set()
        self.types: set[str] = set()
        self.races: set[str] = set()
        self.kws: set[str] = set()
        self.rare_kw = 0
        self.kinds: Counter = Counter()
        self.events: Counter = Counter()
        self.other_events = 0
        self.move_to_when: Counter = Counter()
        self.subjects: set[str] = set()
        self.ops: Counter = Counter()
        self.other_ops = 0
        self.move_tos: Counter = Counter()
        self.move_reasons: Counter = Counter()
        self.sel_owners: Counter = Counter()
        self.sel_zones: Counter = Counter()
        self.from_top = 0
        self.derived: Counter = Counter()
        self.mods: Counter = Counter()
        self.flags: set[str] = set()
        self.targeting: set[str] = set()
        self.breaker = 0

    # ---- 効果 op の処理 ----
    def on_op(self, o: dict):
        op = o.get("op")
        if op in self.c.op_idx:
            self.ops[op] += 1
        elif op in self.c.op_all:
            self.other_ops += 1
        if op == "move":
            self._move(o)
        elif op == "modify":
            pass  # mod 本体は on_mod で処理

    def _move(self, o: dict):
        to = o.get("to")
        if isinstance(to, str):
            self.move_tos[to] += 1
        reason = o.get("reason")
        if isinstance(reason, str):
            self.move_reasons[reason] += 1
        sel = o.get("select")
        zones: set[str] = set()
        owner = None
        if isinstance(sel, dict):
            zones = _zone_set(sel.get("zone"))
            for z in zones:
                self.sel_zones[z] += 1
            owner = sel.get("owner")
            if isinstance(owner, str):
                self.sel_owners[owner] += 1
            if sel.get("from_top"):
                self.from_top += 1
            f = sel.get("filter")
            if isinstance(f, dict):
                if "creature" in (f.get("types") or []):
                    self.targeting.add("targets_creature")
                if "spell" in (f.get("types") or []):
                    self.targeting.add("targets_spell")
                if any(k.startswith("cost_") for k in f):
                    self.targeting.add("cost_filter")
                if f.get("races"):
                    self.targeting.add("race_filter")
            if owner == "opp":
                self.targeting.add("targets_opp")
        d = self.derived
        if reason == "destroy":
            d["destroy"] += 1
        if "graveyard" in zones and to == "bz":
            d["revival"] += 1
        if to == "mana" and reason in ("put", "charge") \
                and zones & {"deck", "hand"}:
            d["mana_boost"] += 1
        if to == "hand" and owner == "opp":
            d["bounce"] += 1
        if "hand" in zones and owner == "opp" and to == "graveyard":
            d["discard_opp"] += 1
        if "hand" in zones and owner == "you" and to == "graveyard" \
                and reason == "discard":
            d["self_discard"] += 1
        if to == "hand" and zones & {"graveyard", "mana"}:
            d["salvage"] += 1
        if "deck" in zones and owner == "you" and to == "graveyard":
            d["mill"] += 1
        if to == "shield":
            d["shield_add"] += 1
        if sel is not None and isinstance(sel, dict) and sel.get("from_top"):
            d["from_top_move"] += 1

    def on_mod(self, mod: dict):
        m = self.mods
        if "power" in mod:
            m["power"] += 1
        if "grant" in mod:
            m["grant"] += 1
            g = mod["grant"]
            if isinstance(g, (list, tuple)):
                for k in g:
                    if k in BREAKERS:
                        self.breaker = max(self.breaker, BREAKERS[k])
        if "deny" in mod:
            m["deny"] += 1
        if "allow" in mod:
            m["allow"] += 1
        if "no_leave" in mod or "indestructible" in mod:
            m["no_leave"] += 1
        if "breaks" in mod and isinstance(mod["breaks"], (int, float)):
            self.breaker = max(self.breaker, int(mod["breaks"]))
        m["n"] += 1


DERIVED = ["destroy", "revival", "mana_boost", "bounce", "discard_opp",
           "self_discard", "salvage", "mill", "shield_add", "from_top_move"]
MODS = ["power", "grant", "deny", "allow", "no_leave", "n"]
TARGETING = ["targets_creature", "targets_spell", "cost_filter",
             "race_filter", "targets_opp"]


def _card_vector(cd, corpus: _Corpus) -> tuple[np.ndarray, list[str]]:
    f = _CardFeat(corpus)
    units = _units(cd)
    costs, powers = [], []
    for u in units:
        if getattr(u, "cost", None):
            costs.append(float(u.cost))
        if getattr(u, "power", None):
            powers.append(float(u.power))
        f.civs |= set(getattr(u, "civs", None) or [])
        f.types |= set(getattr(u, "types", None) or [])
        f.races |= set(getattr(u, "races", None) or [])
        for k in getattr(u, "keywords", None) or []:
            if k in corpus.kw_idx:
                f.kws.add(k)
            elif k in corpus.kw_all:
                f.rare_kw += 1
            if k in BREAKERS:
                f.breaker = max(f.breaker, BREAKERS[k])
        for flag in SPECIAL_FLAGS:
            v = getattr(u, flag, None)
            if v:
                f.flags.add(flag)
        for ab in getattr(u, "abilities", None) or []:
            if not isinstance(ab, dict):
                continue
            kind = ab.get("kind")
            if kind in ("static", "trigger", "replace"):
                f.kinds[kind] += 1
            elif kind in ("declare", "activate"):
                f.kinds["declare_activate"] += 1
            elif kind:
                f.kinds["other_kind"] += 1
            if ab.get("keyword"):
                k = ab["keyword"]
                if k in corpus.kw_idx:
                    f.kws.add(k)
                if k in BREAKERS:
                    f.breaker = max(f.breaker, BREAKERS[k])
            w = ab.get("when")
            if isinstance(w, dict):
                ev = w.get("event")
                if ev:
                    if ev in corpus.ev_idx:
                        f.events[ev] += 1
                    elif ev in corpus.ev_all:
                        f.other_events += 1
                if ev == "move" and isinstance(w.get("to"), str):
                    f.move_to_when[w["to"]] += 1
                subj = w.get("subject")
                if subj == "self":
                    f.subjects.add("self")
                elif isinstance(subj, dict):
                    if subj.get("owner") == "you":
                        f.subjects.add("you")
                    elif subj.get("owner") == "opp":
                        f.subjects.add("opp")
            _walk(ab, f.on_op, f.on_mod)
        for lst in _effect_lists(u):
            _walk(lst, f.on_op, f.on_mod)
    if getattr(cd, "mana_boost", None):
        f.derived["mana_boost"] += 1
    if f.types & {"creature", "evolution"} and f.breaker == 0:
        f.breaker = 1

    names: list[str] = []
    vals: list[float] = []

    def add(name, v):
        names.append(name)
        vals.append(float(v))

    add("cost_min", min(costs) / 10.0 if costs else 0.0)
    add("cost_max", max(costs) / 10.0 if costs else 0.0)
    add("power_max", max(powers) / 10000.0 if powers else 0.0)
    add("has_creature", 1.0 if f.types & {"creature", "evolution",
                                          "exile_creature",
                                          "dream_creature"} else 0.0)
    add("has_spell", 1.0 if "spell" in f.types else 0.0)
    add("has_evolution", 1.0 if "evolution" in f.types
        or "evolve_from" in f.flags else 0.0)
    add("is_twinpact", 1.0 if len(units) > 1 else 0.0)
    add("n_faces", len(units) / 2.0)
    add("n_civs", len(f.civs) / 2.0)
    add("breaker", min(f.breaker, 6) / 5.0)
    for civ in CIVS:
        add(f"civ_{civ}", 1.0 if civ in f.civs else 0.0)
    for gname, members in TYPE_GROUPS:
        add(f"type_{gname}", 1.0 if f.types & members else 0.0)
    for r in corpus.races:
        add(f"race_{r}", 1.0 if r in f.races else 0.0)
    add("n_other_races", _cap(len(f.races - set(corpus.races)), 3))
    add("n_races", _cap(len(f.races), 4))
    for k in corpus.kws:
        add(f"kw_{k}", 1.0 if k in f.kws else 0.0)
    add("n_rare_keywords", _cap(f.rare_kw, 3))
    add("n_keywords", _cap(len(f.kws) + f.rare_kw, 6))
    for kind in ("static", "trigger", "replace", "declare_activate",
                 "other_kind"):
        add(f"kind_{kind}", _cap(f.kinds[kind], 4))
    add("n_abilities", _cap(sum(f.kinds.values()), 6))
    for e in corpus.events:
        add(f"ev_{e}", _cap(f.events[e], 2))
    add("n_other_events", _cap(f.other_events, 2))
    for z in MOVE_TOS:
        add(f"when_to_{z}", _cap(f.move_to_when[z], 2))
    for s in ("self", "you", "opp"):
        add(f"subj_{s}", 1.0 if s in f.subjects else 0.0)
    for o in corpus.ops:
        add(f"op_{o}", _cap(f.ops[o], 4))
    add("n_other_ops", _cap(f.other_ops, 4))
    for z in MOVE_TOS:
        add(f"move_to_{z}", _cap(f.move_tos[z], 4))
    add("move_to_other", _cap(sum(v for k, v in f.move_tos.items()
                                  if k not in MOVE_TOS), 2))
    for r in MOVE_REASONS:
        add(f"reason_{r}", _cap(f.move_reasons[r], 4))
    for o_ in ("you", "opp"):
        add(f"sel_owner_{o_}", _cap(f.sel_owners[o_], 4))
    add("sel_owner_other", _cap(sum(v for k, v in f.sel_owners.items()
                                    if k not in ("you", "opp")), 2))
    for z in SELECT_ZONES:
        add(f"sel_zone_{z}", _cap(f.sel_zones[z], 4))
    add("sel_from_top", _cap(f.from_top, 3))
    for d in DERIVED:
        add(f"verb_{d}", _cap(f.derived[d], 3))
    for m in MODS:
        add(f"mod_{m}", _cap(f.mods[m], 3))
    for flag in SPECIAL_FLAGS:
        add(f"flag_{flag}", 1.0 if flag in f.flags else 0.0)
    for t in TARGETING:
        add(f"tgt_{t}", 1.0 if t in f.targeting else 0.0)
    return np.asarray(vals, dtype=np.float32), names


def build_attribute_matrix(rules, vocab) -> tuple[np.ndarray, list[str]]:
    """全カードの属性行列 [len(vocab), D] と特徴名リストを返す。

    行は vocab の添字（0 = PAD はゼロ行）。語彙の採用リストは
    コーパス頻度から決定的に決まるため、同じ rules では常に同じ
    行列になる。
    """
    corpus = _Corpus(rules)
    mat = None
    names: list[str] = []
    for defn, i in vocab.index.items():
        vec, names = _card_vector(rules.cards[defn], corpus)
        if mat is None:
            mat = np.zeros((len(vocab), len(vec)), dtype=np.float32)
        mat[i] = vec
    assert mat is not None
    return mat, names
