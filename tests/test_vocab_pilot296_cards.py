"""語彙パイロット第296弾のカード側テスト（登録形）: ラウンド331の結果。

- 新規登録4件: dm26rp2-066（partial の CIP move に strigger: "off"）/
  dmx18-003（split 由来の power_when 常在形＋攻撃誘発 ADDITION）/
  dmr13-003（マナ武装7 CIP＋CIP ゲート形）/ dmrp01-s03（CIP シールド化＋形B 常在）。
- 差し戻し1件: dmx21-064 は公式データ自体がカード名・種族を欠く
  （name: No Data / race: ???）ため、構築した提出形を partial に銀行して
  data_incomplete で rejects に残る。
- stale 解消1件: dmx22b-023 は正本 dm26ex4-cho049 が変換済みのため
  登録せず reject 行の除去のみ。正本の戻す move には strigger: "off" が
  無く宣言諮問が出ていた（実挙動で確認）ため、ラウンド331で外科的に
  付与し、dmx22b-023 を source.aliases に追加した。同条項の欠落が
  あった dm03-042（同じカードの別変換エントリ）にも同じ修繕をした。
- shield_trigger_restriction / s_trigger_disable は rejects に残らない。

プロトテスト（test_vocab_pilot296.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが
汚染される）。
"""
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

CIP = {"event": "move", "to": "bz", "subject": "self"}
SHIELD_TO_HAND_OFF = {"op": "move",
                      "select": {"zone": "shield", "owner": "you", "count": 1},
                      "to": "hand", "reason": "return", "strigger": "off"}
SHIELDIZE = {"op": "move",
             "select": {"zone": "hand", "owner": "you", "count": 1},
             "to": "shield", "reason": "put", "face_down": True, "as": "put"}
GATED_RETURN = {"op": "if", "cond": {"exists": {"ref": "put"}},
                "then": [dict(SHIELD_TO_HAND_OFF)]}

NEW = ["dm26rp2-066", "dmx18-003", "dmr13-003", "dmrp01-s03"]


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round331_disposition():
    rej = _reject_rows()
    for cid in NEW:
        c = _conv(cid)
        assert c is not None, cid                      # 登録された
        assert cid not in rej, cid                     # rejects に残らない
        assert not (c.get("source") or {}).get("unsupported"), cid
        parse_card(c, TABLES)
    # ファミリー解消: 両ギャップ名は rejects のどこにも残らない
    assert not [r["id"] for r in rej.values()
                if set(r.get("gaps") or []) &
                {"shield_trigger_restriction", "s_trigger_disable"}]


def test_registered_forms():
    # dm26rp2-066: CIP move に strigger: "off"（partial の形そのまま）
    d = parse_card(_conv("dm26rp2-066"), TABLES)
    assert {"kind": "trigger", "when": dict(CIP),
            "effect": [dict(SHIELD_TO_HAND_OFF)]} in d.abilities
    # dmx18-003: power_when 常在形（split 由来）＋攻撃誘発。partial の
    # 攻撃誘発＋modify 形は登録されていない
    d = parse_card(_conv("dmx18-003"), TABLES)
    assert {"kind": "static", "affects": "self",
            "mod": {"power_when": {"amount": 2000,
                                   "when": "attacking"}}} in d.abilities
    assert not [a for a in d.abilities
                if a.get("kind") == "trigger"
                and any(isinstance(s, dict) and s.get("op") == "modify"
                        for s in a.get("effect") or [])]
    assert "dmx11-002" in (_conv("dmx18-003")["source"].get("aliases") or [])
    # dmr13-003: ブロッカー＋W・ブレイカー、能力2つ（武装・ゲート）
    c = _conv("dmr13-003")
    assert set(c["keywords"]) == {"blocker", "double_breaker"}
    d = parse_card(c, TABLES)
    assert {"kind": "trigger", "when": dict(CIP),
            "effect": [{"op": "may", "body": [dict(SHIELDIZE),
                                              dict(GATED_RETURN)]}]} in d.abilities
    # dmrp01-s03: 形B 常在が登録形にある
    d = parse_card(_conv("dmrp01-s03"), TABLES)
    assert {"kind": "static",
            "affects": {"zone": "shield", "owner": "you",
                        "filter": {"not_civs": ["light"]}},
            "mod": {"deny": ["s_trigger"]}} in d.abilities


def test_bounced_and_stale():
    rej = _reject_rows()
    # dmx21-064: data_incomplete で差し戻し、提出形が partial に銀行済み
    r = rej["dmx21-064"]
    assert r["gaps"] == ["data_incomplete"]
    banked = r["partial"]["abilities"]
    assert {"kind": "trigger", "when": {"event": "turn_start", "player": "you"},
            "effect": [{"op": "draw", "count": 1}]} in banked
    assert {"kind": "trigger", "when": {"event": "turn_end", "player": "you"},
            "effect": [{"op": "may", "body": [dict(SHIELDIZE),
                                              dict(GATED_RETURN)]}]} in banked
    # dmx22b-023: 正本 dm26ex4-cho049 が変換済み（stale 解消）
    assert "dmx22b-023" not in rej
    assert _conv("dmx22b-023") is None
    cho = _conv("dm26ex4-cho049")
    assert "dmx22b-023" in (cho["source"].get("aliases") or [])
    d = parse_card(cho, TABLES)
    hand_moves = []
    def walk(o):
        if isinstance(o, dict):
            if o.get("op") == "move" and o.get("to") == "hand":
                hand_moves.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk([dict(a) for a in d.abilities])
    assert hand_moves and all(m.get("strigger") == "off" for m in hand_moves)
    # dm03-042（同じカードの別変換エントリ）も同じ修繕済み
    d = parse_card(_conv("dm03-042"), TABLES)
    hand_moves = []
    walk([dict(a) for a in d.abilities])
    assert hand_moves and all(m.get("strigger") == "off" for m in hand_moves)
