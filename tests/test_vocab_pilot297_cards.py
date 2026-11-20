"""語彙パイロット第297弾のカード側テスト（登録形）: ラウンド332の結果。

- 新規登録6件: dm25ex2-018 / dm26sd1-g005 / dmex17-w06（形A）/
  dmr04-018（形B）/ dm24bd6-037（形C）/ dm26ex4-002（形A。partial の
  無い行のため公式全文から全構築: civ_count 式のコスト軽減、
  召喚時 CIP の全体シールド化＋無色獣の数だけ相手の手札シールド化、
  キーワード eternal_omega）。
- dm26sd1-g005 のパワーアタッカーは split 由来の power_when 常在形が
  正本で、partial の攻撃誘発＋modify 形は登録されていない
  （ラウンド331の先例）。
- 差し戻し0件。break_replacement_graveyard / break_to_graveyard は
  解消。shield_break_to_graveyard は promoy11-011 のみ残る
  （ガチンコ条件つきの別機構で、本弾の対象ではない）。

プロトテスト（test_vocab_pilot297.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが
汚染される）。
"""
import copy
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402

import _conv_cache  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

INSTEAD = [{"op": "move", "select": {"ref": "event.shield", "count": 1},
            "to": "graveyard", "reason": "put"}]
FORM_A = {"kind": "replace", "when": {"event": "break", "subject": "self"},
          "instead": copy.deepcopy(INSTEAD)}
FORM_B = {"kind": "replace", "when": {"event": "break", "subject": "self"},
          "if": {"cmp": [{"count": {"zone": "hand", "owner": "opp"}}, "==", 0]},
          "instead": copy.deepcopy(INSTEAD)}
FORM_C = {"kind": "replace", "when": {"event": "break", "subject": "self"},
          "if": {"cmp": [{"count": {"zone": "mana", "owner": "you",
                                    "filter": {"face_down": True}}}, ">=", 4]},
          "instead": copy.deepcopy(INSTEAD)}

FORMS = {
    "dm26sd1-g005": FORM_A,
    "dmex17-w06": FORM_A,
    "dm25ex2-018": FORM_A,
    "dmr04-018": FORM_B,
    "dm24bd6-037": FORM_C,
    "dm26ex4-002": FORM_A,
}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_targets_registered():
    rej = _reject_rows()
    for cid, form in FORMS.items():
        c = _conv(cid)
        assert c is not None, cid                       # 登録された
        assert cid not in rej, cid                      # rejects に残らない
        assert not (c.get("source") or {}).get("unsupported"), cid
        d = parse_card(c, TABLES)
        assert form in d.abilities, cid                 # 置換能力が登録形にある
    left = {g: [r["id"] for r in rej.values() if g in (r.get("gaps") or [])]
            for g in ("break_replacement_graveyard", "break_to_graveyard",
                      "shield_break_to_graveyard")}
    assert left["break_replacement_graveyard"] == []
    assert left["break_to_graveyard"] == []
    assert left["shield_break_to_graveyard"] == ["promoy11-011"]


def test_registered_details():
    # dm26sd1-g005: power_when 常在形（split 由来）。攻撃誘発＋modify 形は無い
    d = parse_card(_conv("dm26sd1-g005"), TABLES)
    assert {"kind": "static", "affects": "self",
            "mod": {"power_when": {"amount": 3000,
                                   "when": "attacking"}}} in d.abilities
    assert not [a for a in d.abilities
                if a.get("kind") == "trigger"
                and any(isinstance(s, dict) and s.get("op") == "modify"
                        for s in a.get("effect") or [])]
    assert len((_conv("dm26sd1-g005")["source"].get("aliases") or [])) == 20
    # dm26ex4-002: 全構築の要点（コスト軽減・召喚時 CIP・キーワード）
    c = _conv("dm26ex4-002")
    assert set(c["keywords"]) == {"triple_breaker", "eternal_omega"}
    assert c["civs"] == [] and c["cost"] == 13 and c["power"] == 13000
    d = parse_card(c, TABLES)
    assert {"kind": "static", "zone": "hand", "affects": "self",
            "mod": {"cost": {"amount": -2,
                             "count": {"civ_count": {"zone": "bz",
                                                      "owner": "opp"}}}}} \
        in d.abilities
    assert any(a.get("kind") == "trigger"
               and (a.get("when") or {}).get("reason") == "summon"
               for a in d.abilities)
    # alias 併記
    assert (_conv("dm25ex2-018")["source"].get("aliases") or []) == \
        ["dm25ex2-chog10"]
    assert set(_conv("dmex17-w06")["source"].get("aliases") or []) == \
        {"dmd24-009", "dmex04-003"}
    assert (_conv("dm24bd6-037")["source"].get("aliases") or []) == \
        ["dm23ex3-022"]
