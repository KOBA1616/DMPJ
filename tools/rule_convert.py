"""ルールだけで変換できるカード（モデルを呼ばない＝トークン0）。

対象はクリーチャーのうち、原文が次のどちらかのもの:
  - 能力文なし（バニラ）
  - キーワード能力だけ（data/rules/keywords.yaml の ja と一致する文を「 / 」でつないだもの）
当てはまらない・検査に通らないものは None を返し、呼び出し側（convert_cards.run）がモデルへ回す。
キーワードを増やすには keywords.yaml に足すだけでよい（ここのコードは変えない）。
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.defs import DATA  # noqa: E402

CIVS = {"光": "light", "水": "water", "闇": "darkness", "火": "fire", "自然": "nature", "ゼロ": "zero"}
NOTE = "ルールのみで変換（モデル不使用）"


def norm(s: str) -> str:
    """比較用: 全角英数を半角に、読点・句点・空白・注釈の括弧を除く。"""
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"[（(][^）)]*[）)]", "", s)
    return re.sub(r"[、。，．\s]", "", s)


def _table(with_card_kinds: bool = False) -> dict[str, str]:
    ks = yaml.safe_load((DATA / "rules" / "keywords.yaml").read_text(encoding="utf-8"))["keywords"]
    out = {}
    for name, d in ks.items():
        if (d.get("card") or {}) and not with_card_kinds:       # 呪文用（チャージャー等）は全体変換の対象外。部分変換では扱う
            continue
        out[norm(d["ja"])] = name
    return out


_TABLE: dict[str, str] | None = None
_PATTERNS: list | None = None


def _patterns() -> list:
    """数値つきキーワード（data/rules/keyword_patterns.yaml）。(名前, 正規表現, 能力の雛形) のリスト。"""
    global _PATTERNS
    if _PATTERNS is None:
        ps = yaml.safe_load((DATA / "rules" / "keyword_patterns.yaml").read_text(encoding="utf-8"))["patterns"]
        _PATTERNS = [(n, re.compile(d["re"]), d["abilities"]) for n, d in ps.items()]
    return _PATTERNS


def _fill(x, groups: tuple[str, ...]):
    if isinstance(x, dict):
        return {k: _fill(v, groups) for k, v in x.items()}
    if isinstance(x, list):
        return [_fill(v, groups) for v in x]
    if isinstance(x, str):
        m = re.fullmatch(r"\{(\d)\}", x)
        if m:
            return int(groups[int(m.group(1)) - 1])
    return x


def match_pattern(clause: str) -> list[dict] | None:
    """注釈・数値つきキーワード1つ分の文を能力の並びにする。当てはまらなければ None。"""
    c = unicodedata.normalize("NFKC", re.sub(r"[（(][^）)]*[）)]", "", clause))
    c = re.sub(r"[、。，．\s]", "", c).replace("\u2212", "-").replace("\uff0b", "+")
    for _, rx, abil in _patterns():
        m = rx.fullmatch(c)
        if m:
            return _fill(abil, m.groups())
    return None


def convert(row: dict) -> dict | None:
    """行を効果データ（dict）にする。ルールだけで決められなければ None。検査は呼び出し側（validate）が行う。"""
    global _TABLE
    # 取得時に text だけが空と印の付いた行（能力文のないバニラ）は許す。他の項目が欠けた行は取得のやり直しが先
    if row.get("faces") or set(row.get("missing") or []) - {"text"} or row.get("card_type") != "クリーチャー":
        return None
    if row.get("missing") and (row.get("text") or "").strip():
        return None
    civs = [CIVS.get(c) for c in str(row.get("civilization", "")).split("/")]
    if not civs or None in civs:
        return None
    try:
        cost, power = int(row["cost"]), int(row["power"])
    except (KeyError, ValueError, TypeError):
        return None
    if _TABLE is None:
        _TABLE = _table()
    text = re.sub(r"[（(][^）)]*[）)]", "", unicodedata.normalize("NFKC", row.get("text", "") or ""))   # 注釈（カッコ内）を除く
    clauses = [c for c in re.split(r"[\s/／]+", text) if norm(c)]      # 改行・スラッシュ・空白でキーワードを区切る
    kws, extra = [], []
    for c in clauses:
        k = _TABLE.get(norm(c))
        if k is None:
            a = match_pattern(c)
            if a is None:
                return None         # キーワード以外の能力文がある → モデルへ
            extra += a
            continue
        if k not in kws:
            kws.append(k)
    card = {"id": row["id"], "name": row.get("name", ""), "types": ["creature"], "civs": civs, "cost": cost, "power": power}
    races = [r for r in re.split(r"\s*/\s*", row.get("race", "") or "") if r]
    if races:
        card["races"] = races
    if row.get("mana") not in (None, ""):
        try:
            card["mana"] = int(row["mana"])
        except ValueError:
            return None
    if extra:
        card["abilities"] = extra
    if kws or extra:
        if kws:
            card["keywords"] = kws
        card["text"] = row.get("text", "")
    card["source"] = {"official": row["id"], "review": "pending",
                      "notes": NOTE + ("" if kws or extra or row.get("text") else "。取得時に原文が空だったのでバニラ扱い（原文の取りこぼしでないか確認）")}
    return card


_ALL: dict[str, str] | None = None


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
    for line in re.split(r"\s*[\n/／]\s*", row["text"]):
        tokens = re.sub(r"[（(][^）)]*[）)]", "", line).split()
        def take(i: int) -> bool:
            k = _ALL.get(norm(tokens[i]))
            if k:
                tokens.pop(i)
                if k not in kws:
                    kws.append(k)
                return True
            a = match_pattern(tokens[i])
            if a is not None:
                tokens.pop(i)
                extra.extend(a)
            return a is not None

        while tokens and take(0):      # 行の先頭・末尾に並んだキーワードを外す
            pass
        while tokens and take(-1):
            pass
        if tokens:
            rest.append(" ".join(tokens))
    return (kws, " / ".join(rest), extra) if kws or extra else None
