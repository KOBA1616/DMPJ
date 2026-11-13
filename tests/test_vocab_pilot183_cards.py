"""語彙パイロット第183弾のカード側テスト（登録形）: ラウンド219で登録した
S級侵略 8件が converted.yaml にあり parse が通ること。差し戻した
2件は rejects に残り、洗練したギャップ名を持ち、解けた節を partial に残すこと。
"""
import json
from pathlib import Path

import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent

# id: declare の発生源ゾーン
REGISTERED = {
    "dm26ex2-015": ["hand", "mana"],
    "dm26ex2-mc006": ["hand", "graveyard", "bz"],
    "dm26rp2-tr004": ["hand", "graveyard"],
    "dm26rp2-tr006": ["hand", "mana"],
    "dmr19-017": ["hand", "graveyard"],
    "dmr19-018": ["hand", "graveyard"],
    "dmr19-s09": ["hand", "mana"],
    "dmex16-027": ["hand", "graveyard", "bz"],
}

BOUNCED = {
    "dm26ex1-n015": ["s_class_invasion_hyperdimensional"],
    "dm26rp2-tr003": ["s_class_invasion_peel"],
}


def _converted():
    data = yaml.safe_load(
        (ROOT / "data" / "cards" / "converted.yaml").read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["cards"]}


def _rejects():
    return {json.loads(line)["id"]: json.loads(line) for line in
            (ROOT / "data" / "cards" / "raw" / "rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()}


def _declares(card):
    return [a for a in card["abilities"] if a["kind"] == "declare"]


def _check_declares(card, zones):
    ds = _declares(card)
    assert sorted(a["zone"] for a in ds) == sorted(zones), card["id"]
    for a in ds:
        assert a["when"]["event"] == "attack"
        assert a["when"]["subject"]["owner"] == "you"
        assert a["effect"] == [{"op": "may",
                                "body": [{"op": "invade",
                                          "onto": {"ref": "event.subject"}}]}]


def test_s_class_invasion_cards_registered():
    conv = _converted()
    for cid, zones in REGISTERED.items():
        assert cid in conv, cid
        d = parse_card(conv[cid], TABLES)
        assert d.id == cid
        _check_declares(conv[cid], zones)
    # dm26ex2-015: 出た時（マナ置き→コスト比較破壊）＋ジャストダイバー
    c = conv["dm26ex2-015"]
    s = json.dumps(c["abilities"], ensure_ascii=False)
    assert '"cost_of"' in s and '"sum"' in s
    assert any(a["kind"] == "trigger"
               and a["when"] == {"event": "move", "to": "bz", "subject": "self"}
               for a in c["abilities"])
    # dm26ex2-mc006: 出た時（最小パワー全員に封印）
    c = conv["dm26ex2-mc006"]
    s = json.dumps(c["abilities"], ensure_ascii=False)
    assert '"attach_seal"' in s and '"min_power"' in s
    # dm26rp2-tr004: 出た時パワー-9000
    c = conv["dm26rp2-tr004"]
    s = json.dumps(c["abilities"], ensure_ascii=False)
    assert '"power": -9000' in s
    # dm26rp2-tr006: 条件付き +9000・T・ブレイカー＋ターン終了時マナ置き
    c = conv["dm26rp2-tr006"]
    s = json.dumps(c["abilities"], ensure_ascii=False)
    assert '"power": 9000' in s and '"triple_breaker"' in s
    assert any(a["kind"] == "trigger"
               and a.get("when", {}).get("event") == "turn_end"
               for a in c["abilities"])
    # dmr19-017: 出た時ミル→等コスト全回収
    c = conv["dmr19-017"]
    s = json.dumps(c["abilities"], ensure_ascii=False)
    assert '"cost_of"' in s and '"mill"' in s
    assert c["keywords"] == ["double_breaker"]
    # dmr19-018: スレイヤー＋W・ブレイカー＋次相手ターン攻撃強制
    c = conv["dmr19-018"]
    assert c["keywords"] == ["slayer", "double_breaker"]
    s = json.dumps(c["abilities"], ensure_ascii=False)
    assert '"require": ["attack"]' in s
    # dmr19-s09: 条件付き T・ブレイカー＋出た時 4体以上でマナ置き
    c = conv["dmr19-s09"]
    s = json.dumps(c["abilities"], ensure_ascii=False)
    assert '"grant": ["triple_breaker"]' in s
    assert '"mana_put"' in s
    # dmex16-027: 出た時 attach_seal
    c = conv["dmex16-027"]
    s = json.dumps(c["abilities"], ensure_ascii=False)
    assert '"attach_seal"' in s


def test_s_class_invasion_bounced_cards_keep_refined_gaps():
    rej = _rejects()
    for cid, gaps in BOUNCED.items():
        assert cid in rej, cid
        assert rej[cid]["gaps"] == gaps, (cid, rej[cid]["gaps"])
        partial = rej[cid]["partial"]
        assert partial["id"] == cid
        assert partial["source"]["unsupported"][0]["need"] == gaps[0]
    # dm26ex1-n015: 手札・墓地 declare＋出た時節が partial に残る
    p = rej["dm26ex1-n015"]["partial"]
    _check_declares(p, ["hand", "graveyard"])
    assert any(a["kind"] == "trigger"
               and a["when"] == {"event": "move", "to": "bz", "subject": "self"}
               for a in p["abilities"])
    # dm26rp2-tr003: 手札 declare＋ブレイク置換（ミル2）が partial に残る
    p = rej["dm26rp2-tr003"]["partial"]
    _check_declares(p, ["hand"])
    assert p["keywords"] == ["double_breaker", "unblockable"]
    assert any(a["kind"] == "replace"
               and a["when"].get("event") == "break"
               for a in p["abilities"])
    s = json.dumps(p["abilities"], ensure_ascii=False)
    assert '"mill"' in s
