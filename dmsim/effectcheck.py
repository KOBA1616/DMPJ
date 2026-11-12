"""承認のための深い検証。モデル不使用。

verify.verify_card は「落ちずに回るか」だけを見る。ここでは次の2つを足す。
- text_check: 原文の語（キーワード名・数値・ゾーン名）と変換結果が過不足なく対応しているか
- effect_check: 呪文を実際に唱え、無条件の効果（移動・ドロー）が盤面に起きたか

結果は {"status": "ok" | "fail" | "skip", "problems": [...]}。skip は検査できる材料が無い（条件付き・対象なし等）。
"""
from __future__ import annotations

import re
from . import scenario as sc
from .cards.canonical import normalize_text as norm
from .verify import greedy_policy

from .cards.approval import VERIFIER  # noqa: F401  検証の版（実体は approval。旧名の再公開）

_ZONE_WORDS = {"墓地": "graveyard", "マナゾーン": "mana", "手札": "hand", "シールド": "shield", "山札": "deck",
               "バトルゾーン": "bz"}
_KANJI = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_NUM = re.compile(r"(\d+)\s*(?:枚|体|つ|回|ターン|マナ|コスト|以下|以上|ドロー)|([一二三四五六七八九])(?:枚|体|つ|回)")
_PLUS = re.compile(r"(?:パワー|コスト)\D{0,3}(\d+)")


def _walk(o, out: list):
    if isinstance(o, dict):
        out.append(o)
        for v in o.values():
            _walk(v, out)
    elif isinstance(o, list):
        for v in o:
            _walk(v, out)


def _all_dicts(cd) -> list[dict]:
    out: list = []
    for f in ([cd] + list(cd.faces)):
        _walk([ab for ab in f.abilities if not ab.get("keyword")], out)     # キーワード由来の能力は辞書側の定義なので見ない
        _walk(f.spell, out)
    return out


_REASON_ZONE = {"destroy": "graveyard", "discard": "graveyard", "sba": "graveyard", "battle": "graveyard", "return": "hand",
                "draw": "hand", "charge": "mana", "summon": "bz", "cast": "bz", "break": "hand", "put": None}
_PUNCT = re.compile(r"[、。，．,.]")


def _n(t: str) -> str:
    return _PUNCT.sub("", norm(t))


def text_check(rules, card_id: str) -> dict:
    """キーワードは原文⇔定義で双方向、数値と移動先のゾーン語は定義⊆原文で突き合わせる。"""
    cd = rules.cards[card_id]
    text = _n(cd.text or "")
    heads = [_n(x) for x in re.split(r"[/\n]", cd.text or "")]
    problems = []
    for k in cd.keywords:
        ja = (rules.keywords.get(k) or {}).get("ja")
        if ja and len(_n(ja)) <= 8 and _n(ja) not in text:      # 長い文の語は言い回しが揺れるので見ない
            problems.append(f"キーワード {k}({ja}) が原文に無い")
    for k, kw in rules.keywords.items():
        ja = _n(kw.get("ja") or "")
        if ja and len(ja) >= 3 and any(h.startswith(ja) for h in heads) and k not in cd.keywords and not any(
                k == x for f in cd.faces for x in f.keywords):
            problems.append(f"原文に {ja} があるが {k} が定義に無い")
    dicts = _all_dicts(cd)
    nums_text = {int(a) if a else _KANJI[b] for a, b in _NUM.findall(text)} | {int(x) for x in _PLUS.findall(text)}
    for d in dicts:
        for key in ("count", "amount", "times"):
            v = d.get(key)
            if isinstance(v, int) and v > 1 and nums_text and v not in nums_text and str(v) not in text:
                problems.append(f"定義の数値 {key}={v} が原文に無い")
    zones_text = {z for w, z in _ZONE_WORDS.items() if w in text}
    for d in dicts:
        to = d.get("to") if d.get("op") == "move" else None
        if isinstance(to, str) and to in _ZONE_WORDS.values() and zones_text and to not in zones_text \
                and _REASON_ZONE.get(d.get("reason")) != to:
            problems.append(f"移動先 {to} が原文に無い")
    return {"status": "fail" if problems else "ok", "problems": sorted(set(problems))}


def _expectations(ops: list) -> list[tuple]:
    """無条件に起きるはずの効果。条件・任意・選択・繰り返し・遅延が絡むものは対象外。"""
    out = []
    for o in ops or []:
        if not isinstance(o, dict) or o.get("op") in ("if", "may", "modal", "repeat", "delayed_trigger"):
            continue
        if o.get("op") == "move" and isinstance(o.get("to"), str):
            out.append(("move", o["to"], o.get("select")))
        elif o.get("op") == "draw":
            out.append(("move", "hand", None))
    return out


def effect_check(rules, card_id: str, steps: int = 200) -> dict:
    """呪文を唱え、無条件の移動・ドローが実際に起きるか確かめる。呪文以外・条件付きは skip。"""
    cd = rules.cards[card_id]
    if "spell" not in cd.types or cd.faces:
        return {"status": "skip", "problems": []}
    expect = _expectations(cd.spell)
    if not expect:
        return {"status": "skip", "problems": []}
    eng = sc.build(rules, sc.try_card(rules, card_id), check=True)
    moves, self_cids = [], set()
    raw = eng._raw_move

    def spy(cid, to, *a, **kw):
        if eng.s.cards[cid].defn == card_id:
            self_cids.add(cid)
        moves.append((cid, to))
        return raw(cid, to, *a, **kw)
    eng._raw_move = spy
    played = False
    unverifiable: set = set()
    for _ in range(steps):
        d = eng.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["player"] == 0 and f"play:{card_id}" in keys:
            cid = next(c for c in eng.zlist("hand", 0) if eng.s.cards[c].defn == card_id)
            env = {"you": 0, "self": eng.s.ref(cid), "vars": {}}
            for _, to, sel in expect:        # 対象が1つも無い効果は、起きなくて当然なので検査しない
                try:
                    if sel is not None and not [c for c in eng.candidates(sel, env) if c != cid]:
                        unverifiable.add(to)
                except Exception:
                    unverifiable.add(to)
            eng.answer([keys.index(f"play:{card_id}")])
            played = True
            continue
        if played and d["kind"] in ("main", "charge", "attack"):
            break
        if d["player"] == 0 and d["kind"] in ("charge", "main") and "pass" in keys:
            eng.answer([keys.index("pass")])
        elif d["player"] == 0 and d["kind"].startswith("choose") and d.get("max"):
            eng.answer(list(range(min(d["max"], len(d["options"])))))      # 「まで」の選択は上限まで選ぶ
        else:
            eng.answer(greedy_policy(eng, d))
    if not played:
        return {"status": "skip", "problems": ["唱えられなかった（マナ・対象の不足）"]}
    seen = {to for cid, to in moves if cid not in self_cids}
    problems = [f"{to} への移動が起きなかった" for _, to, _ in expect if to not in seen and to not in unverifiable]
    if not problems and not (seen & {to for _, to, _ in expect}):
        return {"status": "skip", "problems": ["対象が無く検査できなかった"]}
    return {"status": "fail" if problems else "ok", "problems": sorted(set(problems))}
