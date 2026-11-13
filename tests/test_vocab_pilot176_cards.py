"""第176弾 g_castle の実カード形の検証（ラウンド212 登録形）。

ラウンド212で g_castle 単独ギャップ21件のうち18件を converted へ登録し、
3件を差し戻した。g_castle ギャップは残り0件。
- dm26rp1-002 → choose_redirect（「相手がクリーチャーを選ぶ時、かわりに自分が選ぶ」）
- dm26rp1-039 → break_limit（「１度につき最大１つしかシールドをブレイクできない」。
  バトル時パワー-4000は登録済みの partial に銀行）
- dm26rp1-057 → shield_break_replacement（ブレイク置換）
- dm26rp1-035 は submit の merge_split が死んだ static（race_has: 「ブロッカー」を持つ、
  zone なし）を足すため、登録後に converted.yaml から除去済み。
  正しい static は filter keyword: blocker＋zone: shield＋face_up のみ。
- dm26rp1-027 のマナ離脱バトル誘発は to: bz を付けて「マナゾーンから出た時」を
  バトルゾーン入りに限定した。
"""
import json
from pathlib import Path

import yaml

from dmsim.cards.defs import load_tables, parse_card

ROOT = Path(__file__).parent.parent
TABLES = load_tables()

REGISTERED = ["dm26ex1-n022", "dm26ex2-047", "dm26ex4-085", "dm26rp1-001",
              "dm26rp1-023", "dm26rp1-024", "dm26rp1-025", "dm26rp1-026",
              "dm26rp1-027", "dm26rp1-031", "dm26rp1-035", "dm26rp1-043",
              "dm26rp1-047", "dm26rp1-062", "dm26rp1-067", "dm26rp1-072",
              "dm26rp1-077", "dm31-s01"]

BOUNCED = {"dm26rp1-002": ["choose_redirect"],
           "dm26rp1-039": ["break_limit"],
           "dm26rp1-057": ["shield_break_replacement"]}


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


def _ops(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _ops(v)
    elif isinstance(node, list):
        for v in node:
            yield from _ops(v)


def test_round212_registered_parse():
    cards = _converted()
    missing = [cid for cid in REGISTERED if cid not in cards]
    assert not missing, f"converted に無い: {missing}"
    for cid in REGISTERED:
        parsed = parse_card(cards[cid], TABLES)
        assert parsed is not None
        # 型ルールの離脱置換が _load_face で自動付与される（G城のみ）
        if cid != "dm31-s01":
            assert cards[cid]["types"] == ["g_castle"], cid
            assert any(a.get("keyword") == "g_castle" and a["kind"] == "replace"
                       for a in parsed.abilities), cid
    assert cards["dm31-s01"]["types"] == ["creature", "evolution"]
    # alias 引き継ぎ
    assert cards["dm26ex1-n022"]["source"]["aliases"] == ["dm26ex1-secn022"]
    assert cards["dm26rp1-023"]["source"]["aliases"] == ["promoy25-030"]
    assert cards["dm26rp1-026"]["source"]["aliases"] == ["promoy25-068"]
    assert cards["dm26rp1-047"]["source"]["aliases"] == ["dm26rp1-sec021"]
    # dm26ex4-085: T388 型（非クリーチャー実行コスト軽減）
    c85 = cards["dm26ex4-085"]["abilities"][0]
    assert c85["kind"] == "static" and c85["mod"] == {"cost": -1}
    assert c85["affects"]["filter"] == {"not_types": ["creature"]}
    # dm26rp1-001: 置かれた時 put_under＋初回攻撃 no_leave＋ドロー
    c01 = cards["dm26rp1-001"]["abilities"]
    assert any(o.get("op") == "put_under" for a in c01 for o in _ops(a.get("effect", [])))
    assert any(a.get("when", {}).get("ord") == {"kind": "attack", "eq": 1} for a in c01)
    assert any(a.get("effect") and any(
        o.get("op") == "modify" and o.get("mod", {}).get("no_leave") for o in _ops(a["effect"]))
        for a in c01)
    # dm26rp1-035: 死んだ static（race_has 版）は無い。正しい軽減 static のみ。
    c35 = cards["dm26rp1-035"]["abilities"]
    assert len(c35) == 3
    assert not any("race_has" in str(a.get("affects", {}).get("filter", {})) for a in c35)
    stat35 = [a for a in c35 if a["kind"] == "static"]
    assert len(stat35) == 1
    assert stat35[0]["affects"]["filter"] == {"types": ["creature"], "keyword": "blocker"}
    assert stat35[0]["zone"] == "shield" and stat35[0]["if"] == {"face_up": True}
    # dm26rp1-027: マナ離脱バトル誘発は to: bz 付き。force_battle を使う。
    c27 = cards["dm26rp1-027"]["abilities"]
    assert any(a.get("when", {}).get("from") == "mana" and a.get("when", {}).get("to") == "bz"
               for a in c27)
    assert any(o.get("op") == "force_battle" for a in c27 for o in _ops(a.get("effect", [])))
    # dm26rp1-047: 非召喚の出に対するマナ置換は reason: ["put"]
    c47 = cards["dm26rp1-047"]["abilities"]
    rep47 = [a for a in c47 if a["kind"] == "replace"]
    assert len(rep47) == 1
    assert rep47[0]["when"]["reason"] == ["put"]
    assert rep47[0]["instead"][0]["to"] == "mana"
    # dm26rp1-077: ハイパーモード解放は op: hyper_release
    c77 = cards["dm26rp1-077"]["abilities"]
    assert any(o.get("op") == "hyper_release" for a in c77 for o in _ops(a.get("effect", [])))
    # dm31-s01: keywords は double_breaker のみ。城数比例軽減は cost mod の count 形。
    c31 = cards["dm31-s01"]
    assert c31.get("keywords") == ["double_breaker"]
    assert len(c31["abilities"]) == 3
    red = c31["abilities"][2]
    assert red.get("sforce") is True
    assert red["mod"]["cost"] == {"amount": -1, "count": {
        "zone": "shield", "owner": "you",
        "filter": {"types": ["g_castle"], "face_up": True}}}
    assert red["mod"]["cost_min"] == 1
    # dm26rp1-026: 自己シールドブレイクは op: break（player: you）
    c26 = cards["dm26rp1-026"]["abilities"]
    assert any(o.get("op") == "break" and o.get("player") == "you"
               for a in c26 for o in _ops(a.get("effect", [])))


def test_round212_bounced():
    rows = _rejects()
    for cid, gaps in BOUNCED.items():
        assert cid in rows, f"{cid} が rejects に戻っていない"
        assert rows[cid]["gaps"] == gaps, f"{cid}: {rows[cid]['gaps']}"
    # 解けた節は partial に銀行されている
    assert len((rows["dm26rp1-002"].get("partial") or {}).get("abilities") or []) == 3
    assert len((rows["dm26rp1-039"].get("partial") or {}).get("abilities") or []) == 2
    # g_castle ギャップは残り0件
    left = [cid for cid, r in rows.items() if "g_castle" in (r.get("gaps") or [])]
    assert left == [], f"g_castle 残り: {left}"
