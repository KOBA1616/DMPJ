"""語彙パイロット第298弾のカード適用テスト（登録形）。

ラウンド333で same_name_cast の2行を処理した:
- dm26ex4-cho010（最新版・canon）は新規登録。提出形 = partial
  （abilities 無し）＋ 本弾の誘発 CHO010_FORM（choose の reveal: true
  → 見つけた場合の if 内で shuffle → may play_free）。
- c48-sec001（旧印刷）は submit の原文コーパスに無いため直接は
  提出できず、cho010 の登録時に validate の aliases_for で alias
  として畳み込まれた（独立エントリではない）。
- 別印刷 29-sec001 / dm29-s03 / dmc48-001 は converted の独立
  エントリとして本誘発を欠いた形（キーワードのみ）で登録されていた
  既存の欠落 → 各エントリの本文（旧印刷形）に対応する第282弾の
  詠唱形 CAST_FORM を足して是正した（件数不変）。
converted 10,224 / rejects 2,099、same_name_cast は残り0件で解消。

プロトテスト（test_vocab_pilot298.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from test_vocab_pilot282_cards import CAST_FORM  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

CHO010_FORM = {
    "kind": "trigger",
    "when": {"event": "cast", "player": "you", "from": ["hand", "graveyard"],
             "subject": {"filter": {"types": ["spell"],
                                    "civs": ["light", "water", "darkness"]}}},
    "if": {"exists": {"zone": "bz", "owner": "you", "other": True,
                      "filter": {"race_has": "ナイト"}}},
    "effect": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "look": True, "count": "all"},
         "as": "pile"},
        {"op": "choose",
         "select": {"ref": "pile",
                    "filter": {"name": {"name_of": "event.subject"},
                               "types": ["spell"]},
                    "count": 1},
         "as": "found", "reveal": True},
        {"op": "if", "cond": {"exists": {"ref": "found"}},
         "then": [
             {"op": "shuffle", "player": "you"},
             {"op": "may",
              "body": [{"op": "play_free", "select": {"ref": "found"}}]},
         ]},
    ],
}

PRINTINGS_CORRECTED = ["29-sec001", "dm29-s03", "dmc48-001"]


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject_ids():
    out = set()
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            out.add(json.loads(line)["id"])
    return out


def test_targets_registered_and_folded():
    """cho010 は CHO010_FORM で登録済み、c48-sec001 は独立エントリ
    ではなく cho010 の alias として畳み込まれ、両行とも rejects に
    残らない。same_name_cast の行は0件。"""
    rej = _reject_ids()
    c = _converted("dm26ex4-cho010")
    assert c["abilities"] == [CHO010_FORM]
    assert c["keywords"] == ["double_breaker"]
    assert "dm26ex4-cho010" not in rej
    try:
        _converted("c48-sec001")
        raise AssertionError("c48-sec001 が独立エントリとして登録されている")
    except KeyError:
        pass
    aliases = (c.get("source") or {}).get("aliases") or []
    assert "c48-sec001" in aliases
    assert "c48-sec001" not in rej
    n = 0
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            if "same_name_cast" in (r.get("gaps") or []):
                n += 1
    assert n == 0


def test_cho010_registered_form_parses():
    """登録形が parse を通り、誘発は CHO010_FORM の1つだけ。"""
    c = _converted("dm26ex4-cho010")
    d = parse_card(c, TABLES)
    assert [a for a in d.abilities if a["kind"] == "trigger"] == [CHO010_FORM]
    assert d.keywords == ["double_breaker"]


def test_c48_alias_points_at_newest_form():
    """c48-sec001 の alias 先は最新版 cho010 で、その登録形は旧印刷の
    銀行形（末尾シャッフル）ではなく最新版形（公開→シャッフル→
    詠唱）である。旧印刷形そのものは是正3件の CAST_FORM として残る。"""
    c = _converted("dm26ex4-cho010")
    assert "c48-sec001" in c["source"]["aliases"]
    ops = [step.get("op") for step in c["abilities"][0]["effect"]]
    assert ops == ["choose", "choose", "if"]  # move/shuffle の末尾節が無い


def test_converted_printings_trigger_corrected():
    """別印刷 29-sec001 / dm29-s03 / dmc48-001 は独立エントリのまま、
    本文（旧印刷形）に対応する CAST_FORM を持つよう是正された。"""
    for cid in PRINTINGS_CORRECTED:
        c = _converted(cid)
        assert c["name"] == "邪眼皇アレクサンドルIII世", cid
        assert c.get("keywords") == ["double_breaker"], cid
        assert c.get("abilities") == [CAST_FORM], cid
