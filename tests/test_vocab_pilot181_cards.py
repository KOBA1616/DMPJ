"""語彙パイロット第181弾のカード側テスト（登録形）: ラウンド217で登録した
ロスト・プリズム 8件が converted.yaml にあり parse が通ること。差し戻した
1件は rejects に残り、洗練したギャップ名（draw_reveal_branch）を持ち、
解けたロスト・プリズム節を partial に残すこと。
"""
import json
from pathlib import Path

import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent

REGISTERED = [
    "dm24-033", "dm24-036", "dm24-063", "dm24-065", "dm24-067",
    "dm24-069", "dm24-s09", "dmex03-032",
]

BOUNCED = {
    "dm24-s06": ["draw_reveal_branch"],
}


def _converted():
    data = yaml.safe_load(
        (ROOT / "data" / "cards" / "converted.yaml").read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["cards"]}


def _rejects():
    return {json.loads(line)["id"]: json.loads(line) for line in
            (ROOT / "data" / "cards" / "raw" / "rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()}


def _lost_prism_trigger(ability):
    """CIP 時のロスト・プリズム誘発の形か。"""
    assert ability["kind"] == "trigger"
    assert ability["when"] == {"event": "move", "to": "bz", "subject": "self"}
    s = json.dumps(ability, ensure_ascii=False)
    assert "reveal_until" in s and '"limit": 1' in s
    assert '"multicolor": true' in s


def test_lost_prism_cards_registered():
    conv = _converted()
    for cid in REGISTERED:
        assert cid in conv, cid
        d = parse_card(conv[cid], TABLES)
        assert d.id == cid
        _lost_prism_trigger(
            next(a for a in conv[cid]["abilities"]
                 if a["kind"] == "trigger"
                 and a["when"] == {"event": "move", "to": "bz", "subject": "self"}))
    # dm24-033: スピードアタッカー＋ターン終了時自アンタップ
    c = conv["dm24-033"]
    assert c["keywords"] == ["speed_attacker"]
    assert any(a["kind"] == "trigger"
               and a.get("when", {}).get("event") == "turn_end"
               for a in c["abilities"])
    # dm24-036: 文明数比較の常在型（+3000 / W・ブレイカー）
    c = conv["dm24-036"]
    static = [a for a in c["abilities"] if a["kind"] == "static"]
    assert len(static) == 1
    assert static[0]["if"]["cmp"][1] == ">"
    assert "civ_count" in json.dumps(static[0]["if"], ensure_ascii=False)
    assert static[0]["mod"] == {"power": 3000, "breaks": 2}
    # dm24-065: 破壊時手札戻し置換
    c = conv["dm24-065"]
    assert any(a["kind"] == "replace"
               and a["when"].get("reason") == "destroy"
               for a in c["abilities"])
    # dm24-067: W・ブレイカー / dm24-069: S・トリガー
    assert conv["dm24-067"]["keywords"] == ["double_breaker"]
    assert conv["dm24-069"]["keywords"] == ["s_trigger"]
    # dm24-s09: 破壊時山札探索（自然/水・コスト3以下・2体まで→BZ＋シャッフル）
    c = conv["dm24-s09"]
    s = json.dumps(c["abilities"], ensure_ascii=False)
    assert '"look": true' in s and '"cost_le": 3' in s
    assert '"shuffle"' in s
    assert any(a["kind"] == "trigger"
               and a.get("when", {}).get("reason") == "destroy"
               for a in c["abilities"])
    # dmex03-032: 攻撃時ミル分岐（コスト10以上→他全破壊／5以下→シールド化）
    c = conv["dmex03-032"]
    assert c["keywords"] == ["speed_attacker"]
    atk = next(a for a in c["abilities"]
               if a["kind"] == "trigger"
               and a.get("when", {}).get("event") == "attack")
    s = json.dumps(atk, ensure_ascii=False)
    assert '"cost_of": "milled"' in s
    assert '"destroy"' in s and '"to": "shield"' in s
    # 山札切れの誤発防止（cost_of 0 で5以下分岐に入らないよう exists で守る）
    assert '"exists"' in s


def test_lost_prism_bounced_card_keeps_refined_gap():
    rej = _rejects()
    for cid, gaps in BOUNCED.items():
        assert cid in rej, cid
        assert rej[cid]["gaps"] == gaps, (cid, rej[cid]["gaps"])
        partial = rej[cid]["partial"]
        assert partial["id"] == cid
        # 解けたロスト・プリズム節と W・ブレイカーが partial に残っている
        assert partial["keywords"] == ["double_breaker"]
        _lost_prism_trigger(
            next(a for a in partial["abilities"]
                 if a["kind"] == "trigger"
                 and a["when"] == {"event": "move", "to": "bz", "subject": "self"}))
