"""第175弾 accel の実カード形の検証（ラウンド211 登録形）。

ラウンド211で accel 単独ギャップ18件＋dm28-065（partial 無し）＋dm15-004
（accel＋first_attack_of_turn の複合ギャップ）の計20件を converted へ登録し、
差し戻しは0件。残る accel は複合ギャップ4件のみ。
- dm15-009 は unblockable を accel 静的の中だけに持つ（素の keywords には無い。
  submit の merge_split が足す分は登録後に converted.yaml から除去済み）。
- dm15-004 の「攻撃の後」は attack_end 誘発＋turn_count {kind: attack_by, ref: self} == 1。
"""
import json
from pathlib import Path

import yaml

from dmsim.defs import load_tables, parse_card

ROOT = Path(__file__).parent.parent
TABLES = load_tables()

REGISTERED = ["dm28-083", "dm28-097", "dm29-054", "dmpcd02-a10", "dmpcd02-a12",
              "promoy4-011", "promoy7-022", "dm15-001", "dm15-009", "dm15-018",
              "dm15-028", "dm15-037", "dm15-041", "dm15-045", "dm15-049",
              "dmpcd02-a04", "dm15-052", "dm16-018", "dm28-065", "dm15-004"]

# 残る accel は複合ギャップのみ（各々のもう一方のギャップが未対応）
REMAINING_ACCEL = {"dm28-035": ["accel", "cross_free_while_linked"],
                   "dm23ex2-065": ["cross_free_op", "accel"],
                   "dm16-029": ["accel", "unblocked_trigger"],
                   "dm17-037": ["accel", "crossed_state"]}


def _converted():
    d = yaml.safe_load((ROOT / "data" / "cards" / "converted.yaml").read_text(encoding="utf-8"))
    cards = d.get("cards") if isinstance(d, dict) else d
    return {c["id"]: c for c in cards}


def _rejects():
    rows = {}
    for line in (ROOT / "data" / "cards" / "raw" / "rejects.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["id"]] = r
    return rows


def _accel_abs(card):
    return [a for a in (card.get("abilities") or []) if a.get("accel") is True]


def test_round211_registered_parse():
    cards = _converted()
    missing = [cid for cid in REGISTERED if cid not in cards]
    assert not missing, f"converted に無い: {missing}"
    for cid in REGISTERED:
        parsed = parse_card(cards[cid], TABLES)
        assert _accel_abs(cards[cid]), f"{cid}: accel 能力が無い"
        assert parsed is not None
    # T382/T383 型: 静的パワー＋付与／種族追加
    assert cards["dm28-097"]["abilities"][0]["mod"] == {"power": 3000, "grant": ["speed_attacker"]}
    assert cards["dm29-054"]["abilities"][0]["mod"] == {"power": 2000}
    for cid, race in [("dm15-037", "エンジェル・コマンド"), ("dm15-041", "サイバー・ムーン"),
                      ("dm15-045", "デーモン・コマンド"), ("dm15-049", "ボルケーノ・ドラゴン"),
                      ("dm15-052", "アース・ドラゴン")]:
        assert cards[cid]["abilities"][0]["mod"] == {"power": 3000, "add_races": [race]}, cid
    # dm15-009: unblockable は accel 静的の中だけ。素の keywords は無い。
    c9 = cards["dm15-009"]
    assert "unblockable" not in (c9.get("keywords") or [])
    assert c9["abilities"][0] == {"kind": "static", "accel": True,
                                  "mod": {"grant": ["unblockable"]}}
    rep = c9["abilities"][1]
    assert rep["kind"] == "replace" and rep["accel"] is True
    assert rep["instead"][0]["select"] == {"crossed_to": "self", "count": 1}
    # dm15-018: T387 型ブレイク置換
    c18 = cards["dm15-018"]["abilities"][0]
    assert c18["kind"] == "replace" and c18["when"] == {"event": "break", "subject": "self"}
    assert c18["instead"][0]["to"] == "mana"
    # dm28-083: T385 型（ブロックされなかった時バウンス）
    c83 = cards["dm28-083"]["abilities"][0]
    assert c83["when"] == {"event": "attack_end", "subject": "self",
                           "target": "player", "blocked": False}
    # dm15-028: 破壊時、相手が自分の手札を2枚選び捨てる
    c28 = cards["dm15-028"]["abilities"][0]
    assert c28["effect"][0]["op"] == "discard"
    assert c28["effect"][0]["select"]["chooser"] == "opp"
    assert c28["effect"][0]["select"]["count"] == 2
    # dmpcd02-a04: partial の侍流ジェネレート＋accel 攻撃時マナ送り
    a04 = cards["dmpcd02-a04"]["abilities"]
    assert len(a04) == 2
    assert any(a.get("when", {}).get("event") == "move" for a in a04)
    assert any(a.get("accel") is True and a.get("when", {}).get("event") == "attack"
               for a in a04)
    assert cards["dmpcd02-a04"]["source"]["aliases"] == ["dm30-s05"]
    assert cards["dmpcd02-a12"]["source"]["aliases"] == ["dm28-105", "dm28-105hc", "dmc45-033"]
    # dm15-001: 山札から S・トリガー呪文を選び、シャッフル後に唱える（手札を経由しない）
    def _ops(node):
        if isinstance(node, dict):
            yield node
            for v in node.values():
                yield from _ops(v)
        elif isinstance(node, list):
            for v in node:
                yield from _ops(v)
    eff = cards["dm15-001"]["abilities"][0]["effect"]
    assert any(o.get("op") == "play_free" for o in _ops(eff))
    assert not any(o.get("op") == "move" and o.get("to") == "hand" for o in _ops(eff))
    # dm15-004: 「攻撃の後」は attack_end＋turn_count
    c04 = cards["dm15-004"]["abilities"][0]
    assert c04["when"] == {"event": "attack_end", "subject": "self"}
    assert c04["if"] == {"cmp": [{"turn_count": {"kind": "attack_by", "ref": "self"}},
                                 "==", 1]}
    assert c04["effect"] == [{"op": "untap", "select": {"ref": "self"}}]
    # dm28-065: partial 無しからの起草。侍流ジェネレート＋accel 静的
    c65 = cards["dm28-065"]["abilities"]
    assert any(a.get("when", {}).get("event") == "move" for a in c65)
    assert c65[-1]["mod"] == {"power": 4000, "grant": ["double_breaker"]}
    # promoy4-011: そのターンの終わりまで自分のクリーチャー全てにスピードアタッカー
    mod = cards["promoy4-011"]["abilities"][0]["effect"][0]
    assert mod["op"] == "modify" and mod["duration"] == "end_of_turn"
    assert mod["mod"] == {"grant": ["speed_attacker"]}
    # dm16-018: クリーチャーまたはクロスギアの any_of
    ch = cards["dm16-018"]["abilities"][0]["effect"][0]["body"][0]["select"]["filter"]
    assert ch == {"any_of": [{"types": ["creature"]}, {"types": ["cross_gear"]}]}


def test_round211_remaining_accel():
    rows = _rejects()
    left = {cid: rows[cid]["gaps"] for cid in rows
            if "accel" in (rows[cid].get("gaps") or [])}
    assert left == REMAINING_ACCEL, f"残 accel が想定と違う: {left}"
