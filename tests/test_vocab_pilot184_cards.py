"""語彙パイロット第184弾のカード側テスト（登録形）: ラウンド220で登録した
cast_spell_side_from_battle_zone 10件が converted.yaml にあり parse が通ること。
差し戻した1件は rejects に残り、洗練したギャップ名を持つこと。
"""
import json
from pathlib import Path

import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent

REGISTERED = [
    "dm23bd5-014", "dm23bd6-018", "dm23bd6-024", "dm23rp4x-03a",
    "dm25ex4-063", "dm26ex4-057", "dm26ex4-058", "dm26ex4-059",
    "dm25ex1-011", "dm26sd1-u005",
]

BOUNCED = {
    "dm26ex1-008": ["cast_spell_side_from_reveal"],
}


def _converted():
    data = yaml.safe_load(
        (ROOT / "data" / "cards" / "converted.yaml").read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["cards"]}


def _rejects():
    return {json.loads(line)["id"]: json.loads(line) for line in
            (ROOT / "data" / "cards" / "raw" / "rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()}


def _faces(card):
    return card.get("faces") or [card]


def _has_cast_face(card, select=None):
    s = json.dumps(card, ensure_ascii=False)
    assert '"cast_face"' in s, card["id"]
    if select == "self":
        assert any(op.get("op") == "cast_face" and "select" not in op
                   for f in _faces(card)
                   for a in (f.get("abilities") or [])
                   for op in _ops(a)), card["id"]
    elif select == "twinpact":
        assert any(op.get("op") == "cast_face"
                   and op.get("select", {}).get("filter", {}).get("twinpact") is True
                   for f in _faces(card)
                   for a in (f.get("abilities") or [])
                   for op in _ops(a)), card["id"]
    elif select == "event.subject":
        assert any(op.get("op") == "cast_face"
                   and op.get("select") == {"ref": "event.subject"}
                   for f in _faces(card)
                   for a in (f.get("abilities") or [])
                   for op in _ops(a)), card["id"]


def _ops(ability):
    out = []
    for op in ability.get("effect") or []:
        out.append(op)
        out.extend(op.get("body") or [])
    return out


def test_cast_spell_side_cards_registered():
    conv = _converted()
    for cid in REGISTERED:
        assert cid in conv, cid
        d = parse_card(conv[cid], TABLES)
        assert d.id == cid

    # dm23bd5-014: CIP 山札の上から4枚までタップしてマナへ＋ターン終了時に自呪文面。
    c = conv["dm23bd5-014"]
    assert c["faces"][0]["keywords"] == ["guardman", "triple_breaker"]
    cip = c["faces"][0]["abilities"][0]
    assert cip["when"] == {"event": "move", "to": "bz", "subject": "self"}
    mv = cip["effect"][0]
    assert mv["op"] == "move" and mv["select"]["from_top"] == 4
    assert mv["select"]["count"] == {"upto": 4} and mv["tapped"] is True
    assert mv["to"] == "mana"
    _has_cast_face(c, "self")
    s = json.dumps(c["faces"][1]["spell"], ensure_ascii=False)
    assert '"cost_le"' in s and '"count"' in s and '"zone": "mana"' in s

    # dm23bd6-018: ジャストダイバー＋攻撃時に自ツインパクト1体の呪文面。呪文面は modal 5回。
    c = conv["dm23bd6-018"]
    assert c["faces"][0]["keywords"] == ["double_breaker"]
    jd = c["faces"][0]["abilities"][0]
    assert jd["when"] == {"event": "move", "to": "bz", "subject": "self"}
    assert jd["effect"][0]["mod"]["deny"] == ["be_chosen", "be_attacked"]
    assert jd["effect"][0]["duration"] == "until_next_own_turn_start"
    _has_cast_face(c, "twinpact")
    assert c["faces"][1]["spell"][0]["op"] == "modal"
    assert c["faces"][1]["spell"][0]["count"] == 5
    assert c["faces"][1]["spell"][0]["repeat"] is True

    # dm23bd6-024: 相手クリーチャーが手札以外から出た時。呪文面は S・トリガー＋破壊。
    c = conv["dm23bd6-024"]
    trig = c["faces"][0]["abilities"][0]
    assert trig["when"]["event"] == "move" and trig["when"]["to"] == "bz"
    assert "hand" not in trig["when"]["from"]
    assert trig["when"]["subject"] == {"owner": "opp", "filter": {"types": ["creature"]}}
    _has_cast_face(c, "twinpact")
    assert c["faces"][1]["keywords"] == ["s_trigger"]
    assert c["faces"][1]["spell"][0]["op"] == "destroy"
    assert c["faces"][1]["spell"][0]["select"]["filter"]["power_le"] == 12000

    # dm23rp4x-03a: バトル中パワー+3000＋自クリーチャーのバトル勝利時に自呪文面。
    c = conv["dm23rp4x-03a"]
    assert c["faces"][0]["keywords"] == ["speed_attacker", "double_breaker"]
    assert any(a["kind"] == "static"
               and a.get("mod", {}).get("battle_power") == {"amount": 3000}
               for a in c["faces"][0]["abilities"])
    assert any(a["kind"] == "trigger"
               and a["when"].get("event") == "battle_win"
               for a in c["faces"][0]["abilities"])
    _has_cast_face(c, "self")

    # dm25ex4-063: 呪文側コストが自分のマナ枚数以下の自ツインパクト1体を選び唱える。
    c = conv["dm25ex4-063"]
    assert c["faces"][0]["races"] == ["ジャイアント", "ビーストフォーク", "ハンター"]
    s = json.dumps(c["faces"][0]["abilities"], ensure_ascii=False)
    assert '"spell_cost_le"' in s and '"zone": "mana"' in s
    _has_cast_face(c, "twinpact")
    assert c["faces"][1]["keywords"] == ["s_trigger"]
    assert c["faces"][1]["spell"][0]["to"] == "mana"
    assert c["faces"][1]["spell"][0]["select"]["filter"] == {"cost_le": 3}

    # dm26ex4-057/058/059: 各ターンに1度、相手が呪文を唱えた時。破壊時はコスト7以下を手札から出す。
    for cid in ("dm26ex4-057", "dm26ex4-058", "dm26ex4-059"):
        c = conv[cid]
        assert c["faces"][0]["keywords"] == ["blocker"]
        assert c["faces"][0]["races"] == ["サイバーロード", "ジ・アンサー"]
        trig = c["faces"][0]["abilities"][0]
        assert trig["once_per_turn"] is True
        assert trig["when"] == {"event": "cast",
                                "subject": {"owner": "opp", "filter": {"types": ["spell"]}}}
        _has_cast_face(c, "twinpact")
        assert any(a["when"].get("reason") == "destroy"
                   for a in c["faces"][0]["abilities"])
        s = json.dumps(c["faces"][0]["abilities"], ensure_ascii=False)
        assert '"cost_le": 7' in s
        assert c["faces"][1]["keywords"] == ["s_trigger"]
        assert c["faces"][1]["spell"][0]["op"] == "modal"
        assert c["faces"][1]["spell"][0]["count"] == 1

    # dm25ex1-011: G-NEO進化＋攻撃時に自ツインパクト1体の呪文面。
    c = conv["dm25ex1-011"]
    f0 = c["faces"][0]
    assert f0["neo"] is True and f0["evolve_from"] == {"civs": ["nature"]}
    assert f0["keywords"] == ["g_neo", "triple_breaker"]
    _has_cast_face(c, "twinpact")
    assert any(a.get("zone") == "graveyard" for a in f0["abilities"])
    assert c["faces"][1]["spell"][0]["select"]["from_top"] == 1

    # dm26sd1-u005: 各ターンに1度、自ツインパクトが攻撃する時、そのクリーチャーの呪文面。
    c = conv["dm26sd1-u005"]
    assert c["power"] == 7000
    assert c["races"] == ["サイバーロード", "ジ・アンサー"]
    assert c["keywords"] == ["double_breaker"]
    trig = [a for a in c["abilities"]
            if a["kind"] == "trigger"
            and a["when"].get("event") == "attack"]
    assert len(trig) == 1 and trig[0]["once_per_turn"] is True
    _has_cast_face(c, "event.subject")
    assert any(a["kind"] == "trigger"
               and a["when"] == {"event": "move", "to": "bz", "subject": "self"}
               for a in c["abilities"])
    assert any(a["kind"] == "static"
               and a.get("mod", {}).get("grant") == ["speed_attacker"]
               for a in c["abilities"])


def test_cast_spell_side_bounced_card_keeps_refined_gap():
    rej = _rejects()
    for cid, gaps in BOUNCED.items():
        assert cid in rej, cid
        assert rej[cid]["gaps"] == gaps, (cid, rej[cid]["gaps"])
        partial = rej[cid]["partial"]
        assert partial["id"] == cid
        assert partial["source"]["unsupported"][0]["need"] == gaps[0]
    p = rej["dm26ex1-008"]["partial"]
    assert p["types"] == ["spell"] and p["cost"] == 9
    assert "spell" not in p  # めくり唱え＋置き換えは未表現のため効果なし
