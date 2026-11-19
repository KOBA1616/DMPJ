"""語彙パイロット第283弾のカード適用テスト（パイロット段階）。

対象は eternal_kappa の8件:
- dm23ex3-or1 クリス=タブラ=ラーサ（クリスターナル・Κ: 離れる時＋負ける時）
- dm23ex3-s06 「使命」の頂天 グレイテスト・グレート
- dm23ex3-027 「怪異」の頂天 クリス=ベルゼ
- dm24bd6-002 「祝福」の頂天 ウェディング
- dm24bd6-011 「無上」の頂天 シャングリラ・ファンタジア
- dm24bd6-024 「異形」の頂天 クリス=ゼ=ブブ
- dm24rp3-td01 「呪怨」の頂天 サスペンス
- dm24sp2-003 「戦鬼」の頂天 ベートーベン

いずれも eternal_kappa 以外のギャップを併せ持つため、本弾では
partial＋本弾条項の提出形が parse できることと、残りギャップが
そのまま残ることを確認するだけにする（ラウンド318では対象行が
解放されない可能性が高い。docs/vocab-pilot.md の第283弾の節を参照）。

プロトテスト（test_vocab_pilot283.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

# eternal_kappa を除いた残りギャップ（ラウンド318側の注意: これらが残るため
# 対象行は本弾だけでは解放されない可能性が高い）
REMAINING_GAPS = {
    "dm23ex3-or1": ["use_opponent_etb_abilities"],
    "dm23ex3-s06": ["look_put_any_number_rest_to_hand"],
    "dm23ex3-027": ["even_shield_or_cost_attack_permission"],
    "dm24bd6-002": ["each_opponent_shieldize"],
    "dm24bd6-011": ["reveal_until", "entered_turn_attack_player"],
    "dm24bd6-024": ["battle_by_cost"],
    "dm24rp3-td01": ["cast_opponent_graveyard_spells_then_bottom"],
    "dm24sp2-003": ["tapped_self_cannot_be_attacked"],
}
IDS = sorted(REMAINING_GAPS)

EXPECTED_KAPPA = {
    "kind": "replace", "optional": True,
    "when": {"event": "move", "from": "bz", "subject": "self"},
    "if": {"cmp": [{"count": {"zone": "mana", "owner": "you",
                             "filter": {"face_down": True}}}, ">=", 3]},
    "instead": [{"op": "flip_up",
                 "select": {"zone": "mana", "owner": "you",
                            "filter": {"face_down": True}, "count": 3}}],
}

EXPECTED_LOSE = {
    "kind": "replace", "optional": True,
    "when": {"event": "lose"},
    "if": {"cmp": [{"count": {"zone": "mana", "owner": "you",
                             "filter": {"face_down": True}}}, ">=", 3]},
    "instead": [{"op": "flip_up",
                 "select": {"zone": "mana", "owner": "you",
                            "filter": {"face_down": True}, "count": 3}}],
}

_CARD_KEYS = ("id", "name", "types", "civs", "cost", "power", "races", "mana",
              "crystal_soul", "text", "keywords", "abilities")


def _reject(cid):
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            if r["id"] == cid:
                return r
    raise KeyError(cid)


def _submission_form(cid):
    """partial＋本弾条項の提出形（or1 だけ負ける時形の置換能力を足す）。"""
    row = _reject(cid)
    partial = row["partial"]
    form = {k: partial[k] for k in _CARD_KEYS if k in partial}
    form["keywords"] = list(form.get("keywords") or []) + ["eternal_kappa"]
    form["abilities"] = list(form.get("abilities") or [])
    if cid == "dm23ex3-or1":
        form["abilities"] = form["abilities"] + [EXPECTED_LOSE]
    return form


def test_targets_unregistered_and_gaps_pure():
    """対象8件は未登録で、eternal_kappa を含み、残りギャップは想定どおり。"""
    for cid in IDS:
        assert _conv_cache.find(CONVERTED, cid) is None, f"{cid} は登録済み"
        row = _reject(cid)
        assert "eternal_kappa" in row["gaps"], cid
        assert sorted(g for g in row["gaps"] if g != "eternal_kappa") == sorted(REMAINING_GAPS[cid]), cid
        assert any(u.get("need") == "eternal_kappa"
                   for u in (row["partial"].get("source") or {}).get("unsupported", [])), cid


def test_submission_forms_parse():
    """partial＋本弾条項の提出形が parse でき、置換が載る。"""
    for cid in IDS:
        form = _submission_form(cid)
        d = parse_card(json.loads(json.dumps(form)), TABLES)
        abs_k = [ab for ab in d.abilities if ab.get("keyword") == "eternal_kappa"]
        assert len(abs_k) == 1, cid
        assert {k: abs_k[0][k] for k in EXPECTED_KAPPA} == EXPECTED_KAPPA, cid
        lose = [ab for ab in d.abilities
                if ab["kind"] == "replace" and ab["when"] == {"event": "lose"}]
        if cid == "dm23ex3-or1":
            assert lose == [EXPECTED_LOSE], cid
        else:
            assert lose == [], cid
        # partial の abilities は欠けずに残る（キーワード展開分は数えない）
        n_partial = len(_reject(cid)["partial"].get("abilities") or [])
        n_other = len([ab for ab in d.abilities
                       if "keyword" not in ab
                       and not (ab["kind"] == "replace" and ab["when"] == {"event": "lose"})])
        assert n_other == n_partial, cid
