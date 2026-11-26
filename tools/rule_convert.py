"""ルールだけで変換できるカード（モデルを呼ばない＝トークン0）。

対象はクリーチャーのうち、原文が次のどちらかのもの:
  - 能力文なし（バニラ）
  - キーワード能力だけ（data/rules/keywords.yaml の ja と一致する文を「 / 」でつないだもの）
当てはまらない・検査に通らないものは None を返し、呼び出し側（convert_cards.run）がモデルへ回す。
キーワードを増やすには keywords.yaml に足すだけでよい（ここのコードは変えない）。
"""
from __future__ import annotations

import copy
import re
import sys
import unicodedata
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.cards.defs import DATA  # noqa: E402

CIVS = {"光": "light", "水": "water", "闇": "darkness", "火": "fire", "自然": "nature", "ゼロ": "zero"}
NOTE = "ルールのみで変換（モデル不使用）"
WAVE_COND = {"cmp": [{"count": {"zone": "bz", "owner": "any", "other": True, "filter": {"keyword": "wave_striker"}}}, ">=", 2]}


def norm(s: str) -> str:
    """比較用: 全角英数を半角に、読点・句点・空白・注釈の括弧を除く。"""
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"[（(][^）)]*[）)]", "", s)
    return re.sub(r"[、。，．\s]", "", s)


def _table(with_card_kinds: bool = False) -> dict[str, str]:
    ks = yaml.safe_load((DATA / "rules" / "keywords.yaml").read_text(encoding="utf-8"))["keywords"]
    out = {}
    for name, d in ks.items():
        if ({"resolve_to", "after_resolve"} & set(d.get("card") or {})) and not with_card_kinds:       # 呪文用（チャージャー等）は全体変換の対象外。部分変換では扱う
            continue
        for ja in [d["ja"], *d.get("aliases", [])]:
            out[norm(ja)] = name
    return out


_TABLE: dict[str, str] | None = None
_ALL: dict[str, str] | None = None
_PATTERNS: list | None = None


def _noise() -> set[str]:
    """原文にあっても意味を持たない記号（{GS} など）。比較用に正規化した形の集合。"""
    global _NOISE
    if _NOISE is None:
        y = yaml.safe_load((DATA / "rules" / "keyword_patterns.yaml").read_text(encoding="utf-8"))
        _NOISE = {norm(x) for x in y.get("noise", [])}
    return _NOISE


_NOISE: set[str] | None = None


# 「このクリーチャーが出た時」の言い方（正規表現の {ETB} がこれに置き換わる）
_ETB = r"(?:このクリーチャーが(?:バトルゾーンに)?出た時|このクリーチャーをバトルゾーンに出した時)"


# 「このクリーチャーが出た時／攻撃する時／出た時または攻撃する時」。正規表現の {TRG} がこれに置き換わり、
# 能力の雛形の `when: $TRG` は実際の誘発条件（出た時または攻撃する時は2つの能力）に展開される
_TRG = r"(?P<trg>" + _ETB + r"または攻撃する時|" + _ETB + r"|このクリーチャーが攻撃する時)"
_WHEN = {"etb": {"event": "move", "to": "bz", "subject": "self"}, "atk": {"event": "attack", "subject": "self"}}


def _whens(trg: str) -> list[dict]:
    out = []
    if re.search(r"出た時|出した時", trg):
        out.append(_WHEN["etb"])
    if "攻撃する時" in trg:
        out.append(_WHEN["atk"])
    return [dict(w) for w in out]


def _expand_trg(abil: list[dict], trg: str) -> list[dict]:
    out = []
    for ab in abil:
        if ab.get("when") == "$TRG":
            out += [{**ab, "when": w} for w in _whens(trg)]
        else:
            out.append(ab)
    return out


def _patterns() -> list:
    """数値つきキーワード（data/rules/keyword_patterns.yaml）。(名前, 正規表現, 能力の雛形) のリスト。"""
    global _PATTERNS
    if _PATTERNS is None:
        ps = yaml.safe_load((DATA / "rules" / "keyword_patterns.yaml").read_text(encoding="utf-8"))["patterns"]
        _PATTERNS = [(n, re.compile(d["re"].replace("{TRG}", _TRG).replace("{ETB}", _ETB)), d.get("abilities") or d["builder"], bool(d.get("whole_line")))
                     for n, d in ps.items()]
    return _PATTERNS


_SPELL: list | None = None


def _spell_effects() -> list:
    """呪文の効果文（keyword_patterns.yaml の spell_effects）。(正規表現, ops の雛形) のリスト。"""
    global _SPELL
    if _SPELL is None:
        ps = yaml.safe_load((DATA / "rules" / "keyword_patterns.yaml").read_text(encoding="utf-8")).get("spell_effects") or {}
        _SPELL = [(re.compile(d["re"]), d["spell"]) for d in ps.values()]
    return _SPELL


def match_spell(line: str) -> list[dict] | None:
    """呪文の効果文1行分を ops にする。当てはまらなければ None。"""
    c = unicodedata.normalize("NFKC", re.sub(r"[（(][^）)]*[）)]", "", line))
    c = re.sub(r"[、。，．\s]", "", c).replace("\u2212", "-")
    for rx, ops in _spell_effects():
        m = rx.fullmatch(c)
        if m:
            return _fill(ops, m.groups())
    return None


def _fill(x, groups: tuple[str, ...]):
    if isinstance(x, dict):
        return {k: _fill(v, groups) for k, v in x.items()}
    if isinstance(x, list):
        return [_fill(v, groups) for v in x]
    if isinstance(x, str):
        m = re.fullmatch(r"(-?)\{(\d)\}", x)
        if m:
            return int(groups[int(m.group(2)) - 1]) * (-1 if m.group(1) else 1)
    return x


_CIV_EN = {"光": "light", "水": "water", "闇": "darkness", "火": "fire", "自然": "nature"}


def _build_revolution_change(groups: tuple[str, ...]) -> list[dict] | None:
    """革命チェンジ：<条件> → 攻撃時に手札から入れ替える宣言。条件は「[文明]の[多色の][コストN以上の]<種族 or クリーチャー>」だけ読む。"""
    m = re.fullmatch(r"((?:自然|光|水|闇|火)(?:(?:または|、)?(?:自然|光|水|闇|火))*)?(多色)?(?:の)?(?:コスト(\d+)以上)?(?:の)?([^\sの]+)", groups[0])
    if not m or not (m.group(1) or m.group(2) or m.group(3) or m.group(4)):
        return None
    civs, multi, cost, race = m.groups()
    if "または" in race or race.startswith("名前"):
        return None
    filt: dict = {}
    if civs:
        filt["civs"] = [_CIV_EN[c] for c in re.findall(r"自然|光|水|闇|火", civs)]
    if multi:
        filt["multicolor"] = True
    if cost:
        filt["cost_ge"] = int(cost)
    if race != "クリーチャー":
        filt["race_has"] = race
    return [{"kind": "declare", "zone": "hand",
             "when": {"event": "attack", "subject": {"owner": "you", "filter": filt}},
             "effect": [{"op": "swap", "out": {"ref": "event.subject"}, "in": {"ref": "self"}}]}]


_PHRASE = re.compile(r"((?:自然|光|水|闇|火)(?:(?:または|、)?(?:自然|光|水|闇|火))*)?の?(?:コスト(\d+)(以下|以上)の)?(?:パワー(\d+)以上の)?(.+)")


def parse_filter(phrase: str) -> dict | None:
    """「光のコスト3以下のクリーチャー」「ドラゴン・クリーチャー」「呪文」などの言い方を filter にする。読めなければ None。"""
    m = _PHRASE.fullmatch(phrase)
    if not m:
        return None
    civs, cost, cmp_, power, noun = m.groups()
    if re.search(r"または|および|と|、|以外", noun):
        return None
    f: dict = {}
    if civs:
        f["civs"] = [_CIV_EN[c] for c in re.findall(r"自然|光|水|闇|火", civs)]
    if cost:
        f["cost_le" if cmp_ == "以下" else "cost_ge"] = int(cost)
    if power:
        f["power_ge"] = int(power)
    race = re.sub(r"・?クリーチャー$", "", noun)
    if noun == "呪文":
        f["types"] = ["spell"]
    elif noun == "クリーチャー" or not race:
        f["types"] = ["creature"]
    else:
        f["types"] = ["creature"]
        f["race_has"] = race
    return f


def _build_sympathy(groups: tuple[str, ...]) -> list[dict] | None:
    """シンパシー：<対象>:<N>（<対象>1体につきNコストが少なくなる）。前処理 _prenorm が注釈から N を取り出して付ける。"""
    what, n = groups
    m = re.fullmatch(r"(自分の|相手の)?(墓地にある|マナゾーンにある)?(.+)", what)
    if not m:
        return None
    owner, zone, rest = m.groups()
    sel: dict = {"zone": "bz", "owner": "opp" if owner == "相手の" else "you"}
    if zone and rest == "カード":
        sel["zone"] = "graveyard" if zone == "墓地にある" else "mana"
    else:
        f = parse_filter(rest)
        if f is None:
            return None
        sel["filter"] = f
        if zone == "墓地にある":
            sel["zone"] = "graveyard"
    return [{"kind": "static", "zone": "hand", "affects": "self", "mod": {"cost": {"amount": -int(n), "count": sel}}}]


def _build_cost_static(groups: tuple[str, ...]) -> list[dict] | None:
    """自分の<対象>の召喚コストをN少なくする／相手の<対象>のコストをN多くする などの常在型のコスト増減。"""
    who, what, n, verb = groups
    f = parse_filter(what)
    if f is None:
        return None
    sign = -1 if verb == "少なく" else 1
    return [{"kind": "static", "affects": {"owner": "you" if who == "自分" else "opp", "zone": "hand", "filter": f},
             "mod": {"cost": sign * int(n)}}]


def _build_grant_all(groups: tuple[str, ...]) -> list[dict] | None:
    """自分のクリーチャーすべてに「<キーワード>」を与える（常在型）。キーワードは辞書にある名前だけ。"""
    global _ALL
    if _ALL is None:
        _ALL = _table(with_card_kinds=True)
    k = _ALL.get(norm(groups[0]))
    if k is None:
        return None
    return [{"kind": "static", "affects": {"owner": "you", "filter": {"types": ["creature"]}}, "mod": {"grant": [k]}}]


BUILDERS = {"grant_all": _build_grant_all, "revolution_change": _build_revolution_change, "sympathy": _build_sympathy, "cost_static": _build_cost_static}


_KW_NAMES: list[str] | None = None


def _peel_line(line: str) -> list[str]:
    """行頭にキーワード名が改行なしでつながっている原文（「ブロッカーこのクリーチャーは…」「S・トリガー（…）相手の…」）を、
    キーワード1つごとの行に分ける。分けるのは直後が注釈・別のキーワード・「このクリーチャー」等の文頭の時だけ（「進化クリーチャー」を割らない）。"""
    global _KW_NAMES
    if _KW_NAMES is None:
        ks = yaml.safe_load((DATA / "rules" / "keywords.yaml").read_text(encoding="utf-8"))["keywords"]
        _KW_NAMES = sorted({unicodedata.normalize("NFKC", j) for d in ks.values() for j in [d["ja"], *d.get("aliases", [])]},
                           key=len, reverse=True)
    out, rest = [], line
    while rest:
        rest_n = unicodedata.normalize("NFKC", rest)
        for kw in _KW_NAMES:
            if not rest_n.startswith(kw):
                continue
            tail = rest_n[len(kw):]
            m = re.match(r"\s*[（(][^）)]*[）)]。?", tail)
            after = tail[m.end():] if m else tail
            if not after.strip():
                return out + [rest] if out else [line]
            cut = len(rest_n) - len(after.lstrip())     # NFKC 後の位置 → 元の文字列の位置
            starts = ("この", "自分", "相手", "バトル", "各ターン", "ターン", "次")
            if m or after.startswith(starts) or any(after.startswith(k) for k in _KW_NAMES):
                out.append(kw + (m.group(0) if m else ""))
                n, i = 0, 0
                while i < len(rest) and n < cut:
                    n += len(unicodedata.normalize("NFKC", rest[i]))
                    i += 1
                rest = rest[i:]
                break
        else:
            return out + [rest] if out else [line]
    return out or [line]


def _prenorm(text: str) -> str:
    """注釈を除く前に、注釈の中にだけある数値を本文に移す（シンパシー: 「1体につき2少なくなる」→ 「シンパシー:<対象>:2」）。
    行頭につながったキーワードは行に分ける。"""
    text = "\n".join("\n".join(_peel_line(l)) for l in (text or "").split("\n"))
    t = unicodedata.normalize("NFKC", text or "")
    new = re.sub(r"シンパシー[:：]\s*([^\s（(:：]+)\s*[（(][^）)]*?(?<!\d)1体につき(\d+)少なく[^）)]*[）)]", r"シンパシー:\1:\2", t)
    return new if new != t else (text or "")      # 該当がなければ原文のまま（半角全角を変えない）


def _glue(tokens: list[str]) -> list[str]:
    """数字だけの語は直前のキーワード名に、末尾が「：」の語は次の語につなぐ（「ニンジャ・ストライク ４」「革命チェンジ： 火のドラゴン」）。"""
    out: list[str] = []
    for t in tokens:
        u = unicodedata.normalize("NFKC", t)
        if out and (re.fullmatch(r"[+＋]?\d+", u) or re.search(r"[:：]$", out[-1])):
            out[-1] += t
        else:
            out.append(t)
    return out


def match_pattern(clause: str, whole_line: bool = False) -> list[dict] | None:
    """注釈・数値つきキーワード1つ分の文を能力の並びにする。当てはまらなければ None。
    whole_line=True は、その文が1行（1つの能力）の全体である場合。効果の文（出た時、カードを引く など）は
    「その後」「そうしたら」で続く文を取りこぼさないよう、1行まるごとの時だけ変換する（yaml の whole_line: true）。"""
    c = unicodedata.normalize("NFKC", re.sub(r"[（(][^）)]*[）)]", "", clause))
    c = re.sub(r"[、。，．\s]", "", c).replace("\u2212", "-").replace("\uff0b", "+")
    for _, rx, abil, wl in _patterns():
        if wl and not whole_line:
            continue
        m = rx.fullmatch(c)
        if m:
            gs = tuple(g for i, g in enumerate(m.groups(), 1) if i != rx.groupindex.get("trg"))   # 誘発条件の名前つきグループは番号に数えない
            if isinstance(abil, str):        # builder 名: 正規表現のグループから能力をコードで組み立てる
                return BUILDERS[abil](gs)
            filled = _fill(abil, gs)
            return _expand_trg(filled, m.group("trg")) if "trg" in rx.groupindex else filled
    if whole_line:      # 呪文の定型文は、出た時・攻撃する時の誘発効果としてもそのまま使える
        m = re.match(_TRG, c)
        if m:
            ops = match_spell(c[m.end():])
            if ops is not None:
                return [{"kind": "trigger", "when": w, "effect": ops} for w in _whens(m.group("trg"))]
    return None


def base_card(row: dict) -> dict | None:
    """クリーチャーの土台（id・名前・文明・コスト・パワー・種族・マナ）。取得データの欠けや数値の読めないものは None。"""
    civs = [CIVS.get(c) for c in str(row.get("civilization", "")).split("/")]
    if not civs or None in civs:
        return None
    try:
        cost, power = int(row["cost"]), int(row["power"])
    except (KeyError, ValueError, TypeError):
        return None
    card = {"id": row["id"], "name": row.get("name", ""), "types": ["creature"], "civs": civs, "cost": cost, "power": power}
    races = [r for r in re.split(r"\s*/\s*", row.get("race", "") or "") if r]
    if races:
        card["races"] = races
    if row.get("mana") not in (None, ""):
        try:
            card["mana"] = int(row["mana"])
        except ValueError:
            return None
    return card


_SPELL_KWS: dict[str, str] | None = None


def _spell_keywords() -> dict[str, str]:
    """呪文に付くキーワード（S・トリガー、G・ストライク、チャージャーなど）の表。ブロッカーなどは呪文にない。"""
    global _SPELL_KWS, _ALL
    if _SPELL_KWS is None:
        if _ALL is None:
            _ALL = _table(with_card_kinds=True)
        ks = yaml.safe_load((DATA / "rules" / "keywords.yaml").read_text(encoding="utf-8"))["keywords"]
        ok = {k for k, d in ks.items() if k in ("s_trigger", "g_strike") or {"resolve_to", "after_resolve"} & set(d.get("card") or {})}
        _SPELL_KWS = {n: k for n, k in _ALL.items() if k in ok}
    return _SPELL_KWS


def convert_spell(row: dict) -> dict | None:
    """呪文（二面でないもの）。キーワード（S・トリガー、チャージャーなど）と、定型の効果文（spell_effects）だけでできている時に変換する。"""
    if row.get("faces") or row.get("missing"):
        return None
    civs = [CIVS.get(c) for c in str(row.get("civilization", "")).split("/")]
    if not civs or None in civs or not (row.get("text") or "").strip():
        return None
    try:
        card = {"id": row["id"], "name": row.get("name", ""), "types": ["spell"], "civs": civs, "cost": int(row["cost"])}
        if row.get("mana") not in (None, ""):
            card["mana"] = int(row["mana"])
    except (KeyError, ValueError, TypeError):
        return None
    table = _spell_keywords()
    kws, ops = [], []
    for line in re.split(r"\s*[\n/／]\s*", _prenorm(row["text"])):
        stripped = re.sub(r"[（(][^）)]*[）)]", "", line)
        clauses = [c for c in _glue(re.split(r"[\s。]+", stripped)) if norm(c) and norm(c) not in _noise()]
        if not clauses:
            continue
        if all(table.get(norm(c)) for c in clauses):          # キーワードだけの行
            for c in clauses:
                k = table[norm(c)]
                if k not in kws:
                    kws.append(k)
            continue
        o = match_spell(line)
        if o is None:
            return None
        ops += o
    if not kws and not ops:
        return None
    if kws:
        card["keywords"] = kws
    if ops:
        card["spell"] = ops
    card["text"] = row["text"]
    card["source"] = {"official": row["id"], "review": "pending", "notes": NOTE}
    return card


def convert_twin(row: dict) -> dict | None:
    """ツインパクト（二面カード）。両面ともルールだけで変換できる時だけ、面ごとの変換結果を faces にまとめる。"""
    faces = row.get("faces") or []
    if len(faces) != 2 or set(row.get("missing") or []):
        return None
    out = []
    for i, f in enumerate(faces):
        sub = convert({**f, "id": row["id"], "mana": f.get("mana", row.get("mana"))})
        if sub is None:
            return None
        out.append({k: v for k, v in sub.items() if k not in ("id", "mana", "text", "source")})
    card = {"id": row["id"], "faces": out}
    if row.get("mana") not in (None, ""):
        try:
            card["mana"] = int(row["mana"])
        except ValueError:
            return None
    card["text"] = " ／ ".join(f"{f.get('name', '')}: {(f.get('text') or '').replace(chr(10), ' / ')}" for f in faces)
    card["source"] = {"official": row["id"], "review": "pending", "notes": NOTE + "（ツインパクト）"}
    return card


def convert(row: dict) -> dict | None:
    """行を効果データ（dict）にする。ルールだけで決められなければ None。検査は呼び出し側（validate）が行う。"""
    global _TABLE
    if row.get("faces"):
        return convert_twin(row)
    if row.get("card_type") == "呪文":
        return convert_spell(row)
    # 取得時に text だけが空と印の付いた行（能力文のないバニラ）は許す。他の項目が欠けた行は取得のやり直しが先
    if row.get("faces") or set(row.get("missing") or []) - {"text"} or row.get("card_type") != "クリーチャー":
        return None
    if row.get("missing") and (row.get("text") or "").strip():
        return None
    card = base_card(row)
    if card is None:
        return None
    if _TABLE is None:
        _TABLE = _table()
    text = re.sub(r"[（(][^）)]*[）)]", " ", _prenorm(row.get("text", "")))   # 注釈（カッコ内）を除く。空白に置き換え、「スレイヤー（…）W・ブレイカー」が1語にくっつかないようにする
    kws, extra = [], []
    for line in re.split(r"\s*[\n/／]\s*", text):      # 行（スラッシュ・改行）ごとに、空白・句点でキーワードを区切る
        clauses = [c for c in _glue(re.split(r"[\s。]+", line)) if norm(c) and norm(c) not in _noise()]
        for c in clauses:
            k = _TABLE.get(norm(c))
            if k is None:
                a = match_pattern(c, whole_line=len(clauses) == 1)
                if a is None:
                    return None         # キーワード以外の能力文がある → モデルへ
                extra += a
                continue
            if k not in kws:
                kws.append(k)
    if "turbo_rush" in kws:         # ターボラッシュの能力は self_marked の条件が要る。付け忘れの誤変換を避けてモデルへ
        return None
    if "silent_skill" in kws:       # サイレントスキルの効果文は kind: silent に入れる。ルールの能力文では置けないのでモデルへ
        return None
    if "wave_striker" in kws:       # ウェーブストライカー: 続く能力はすべて「他に2体以上」の間だけ得る。他のキーワードが混ざる原文はモデルへ
        if len(kws) > 1 or not extra:
            return None
        for ab in extra:
            ab["if"] = {"all": [ab["if"], WAVE_COND]} if "if" in ab else dict(WAVE_COND)
    if re.search(r"[0０]以下に(は)?ならない|[1１]より少なくならない", row.get("text", "")):
        for ab in extra:        # 「ただし、コストは0以下にはならない」= 軽減後の最低は1（noise で照合から除いた分をここで反映）
            m = ab.get("mod") or {}
            c = m.get("cost")
            if (isinstance(c, int) and c < 0) or (isinstance(c, dict) and c.get("amount", 0) < 0):
                m["cost_min"] = 1
    if extra:
        card["abilities"] = extra
    if kws or extra:
        if kws:
            card["keywords"] = kws
        card["text"] = row.get("text", "")
    card["source"] = {"official": row["id"], "review": "pending",
                      "notes": NOTE + ("" if kws or extra or row.get("text") else "。取得時に原文が空だったのでバニラ扱い（原文の取りこぼしでないか確認）")}
    return card


def reuse_same_text(row: dict, cards: list[dict]) -> dict | None:
    """原文が完全に同じ変換済みクリーチャー（再録・色違い・名前違い）があれば、その能力を写して作る（モデル不使用）。
    写すのは能力・キーワードなど。id・名前・文明・コスト・パワー・種族・マナは row のもの。単純なクリーチャー同士（進化・二面は除く）だけ。"""
    text = (row.get("text") or "").strip()
    if not text or row.get("faces") or row.get("missing") or row.get("card_type") != "クリーチャー":
        return None
    base = base_card(row)
    if base is None:
        return None
    for c in cards:
        if c.get("types") == ["creature"] and not c.get("faces") and (c.get("text") or "").strip() == text and c["id"] != row["id"]:
            new = {k: copy.deepcopy(v) for k, v in c.items() if k not in ("id", "name", "civs", "cost", "power", "races", "mana", "source")}
            new = {**base, **new}
            new["text"] = row["text"]
            new["source"] = {"official": row["id"], "review": "pending",
                             "notes": f"原文が同じ {c['id']} の変換結果を写した（モデル不使用）。能力は元カードの確認に従う"}
            return new
    return None





_METAMORPH = re.compile(r"メタモーフ\(自分のマナゾーンに(\d+)枚以上カードがあれば、このクリーチャーは次の能力を得る\)。?")


def _metamorph_cond(line: str) -> dict | None:
    """メタモーフのヘッダ行（行全体がヘッダの時だけ）から条件を取り出す。呪文形（「この呪文は次の能力を得る」）は
    次の文が前の効果の置き換えになるため対象にしない（クリーチャー形だけ）。"""
    m = _METAMORPH.fullmatch(unicodedata.normalize("NFKC", line).strip())
    return {"cmp": [{"count": {"zone": "mana", "owner": "you"}}, ">=", int(m.group(1))]} if m else None


def split(row: dict) -> tuple[list[str], str, list[dict]] | None:
    """原文からキーワード能力だけを取り出す（部分変換）。(キーワード名のリスト, キーワードを除いた原文, 数値つきキーワードの能力) を返す。
    キーワードが1つも見つからない・二面カード・取得が不完全な行は None。残りの原文はモデルに渡す（キーワードの分だけ短く、迷いが減る）。"""
    global _ALL
    if row.get("faces") or row.get("missing") or not (row.get("text") or "").strip():
        return None
    if _ALL is None:
        _ALL = _table(with_card_kinds=True)
    kws: list[str] = []
    extra: list[dict] = []
    rest: list[str] = []
    pending: tuple[dict, int] | None = None      # メタモーフの (条件, rest に残したヘッダの位置)。次の能力を定型が所有した時にだけ使う
    for line in re.split(r"\s*[\n/／]\s*", _prenorm(row["text"])):
        cond = _metamorph_cond(line)
        before = len(extra)
        tokens = [x for x in _glue(re.sub(r"[（(][^）)]*[）)]", " ", line).split()) if norm(x) not in _noise()]
        sents = [x for t_ in tokens for x in re.split(r"(?<=。)", t_) if x]    # 句点で終わる文も1つずつ照合する
        tokens = [x for x in sents if norm(x) not in _noise()]       # 文の途中にある記号・ルールの念押し文も除く
        def take(i: int) -> bool:
            k = _ALL.get(norm(tokens[i]))
            if k:
                tokens.pop(i)
                if k not in kws:
                    kws.append(k)
                return True
            a = match_pattern(tokens[i], whole_line=len(tokens) == 1)
            if a is not None:
                tokens.pop(i)
                extra.extend(a)
            return a is not None

        while tokens and take(0):      # 行の先頭・末尾に並んだキーワードを外す
            pass
        while tokens and take(-1):
            pass
        for i in range(len(tokens) - 1, -1, -1):      # 文の途中に挟まったキーワード単独の語も外す
            k = _ALL.get(norm(tokens[i]))
            if k and len(tokens) > 1:
                tokens.pop(i)
                if k not in kws:
                    kws.append(k)
        if tokens:
            rest.append(" ".join(tokens))
        if cond is not None and tokens == ["メタモーフ"]:
            pending = (cond, len(rest) - 1)     # ヘッダ行は注釈を除くと「メタモーフ」だけが残る。条件の伝達先が定型能力の時だけ rest からも外す
        elif pending is not None and len(extra) > before:
            # メタモーフが与える「次の能力」を定型が所有した: その行で得た能力に条件を付け、ヘッダは rest から外す。
            # 次の能力が定型でない（rest に残る）場合は条件を付けず、ヘッダも rest に残してモデルに渡す（従来どおり）
            c, idx = pending
            for ab in extra[before:]:
                ab["if"] = {"all": [ab["if"], copy.deepcopy(c)]} if "if" in ab else copy.deepcopy(c)
            del rest[idx]
            pending = None
    if "meteor_burn" in kws and re.search(r"メテオバーン\s*[-―ー－]?\s*(?:このクリーチャー|自分のクリーチャー)が攻撃", row.get("text") or ""):
        # 攻撃時型メテオバーン（「攻撃する時／攻撃できる時」に下のカードを墓地に置く誘発能力）は
        # 離脱置換キーワードではない。本文は rest に残るので、キーワードとして付けずモデルに誘発として変換させる
        kws.remove("meteor_burn")
    return (kws, " / ".join(rest), extra) if kws or extra else None
