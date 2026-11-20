"""語彙パイロット第322弾の対象カード検証（提出前）。

trigger_when_unblocked_and_extra_breaks_per_dynamo_tap は純粋2件のみ
（multi-gap 行にも現れない）:
- dm19-003 電脳鉄人センジュオー: partial あり（骨格。abilities 無し）。
  未解決は「攻撃してブロックされなかった時、このターンに「ダイナモ」能力を
  使うためにタップした自分のダイナモ１体につき１枚、シールドを余分に
  ブレイクする」の1節のみ。partial の注記「ダイナモの語彙が無い」は
  stale（dynamo は第76弾で定義済み）。
- dm23ex2-045: rejects 行は partial 空・name None・text はクリーチャー面
  のみ。by_product（23ex2.jsonl）で原文照合済み: ツインパクトで、
  クリーチャー面は dm19-003 と同名・同能力（「１つ、シールドを追加で
  ブレイクする」と読む）、呪文面 センジュ・チューンは S・トリガーで
  「自分の手札の数と同じ枚数のカードを引き、その後、こうして引いた枚数と
  同じ数、手札を捨てる」。submit は by_product 行（faces 付き）を正本と
  して読むため、faces 形式で提出する。

第322弾の結論: エンジン拡張あり。新 turn_count kind `dynamo_tap`
（op_modify の add_of 適用で記録。重複は数えない）と、op_set_var の
式評価の修正（呪文面のため。従来は {count: ...} を辞書のまま束縛し
{var:} の読みが1になっていた）。
- 形（両カードのクリーチャー面共通）: trigger {event: attack_end,
  subject: self, target: player, blocked: false} →
  [{op: break, player: opp, count: {turn_count: {kind: dynamo_tap,
  owner: you}}}]
- 呪文面の形: [set_var hand_n {count: {zone: hand, owner: you}},
  draw {var: hand_n}, discard {zone: hand, owner: you, count: {var: hand_n}}]
  （discard は parse 時に move（to: graveyard, reason: discard）へ展開）

ラウンド357で登録する。提出形は dm19-003 が partial ＋ keywords
[dynamo, unblockable] ＋確立形、unsupported 除去。dm23ex2-045 は
faces 形式（top text は convert_twin の形「面名: 面文 ／ 面名: 面文」）。
正本判定: 両 id とも real.yaml / real_akashic.yaml / real_vocab.yaml /
real_zone.yaml / proto.yaml / converted.yaml のいずれにも無く、aliases
記録も無いことを提出前に確認すること。実挙動は test_vocab_pilot322.py
が試験カードで、test_vocab_round357_cards.py が登録カード自身で固定する。
"""
import json
from pathlib import Path

from dmsim.cards.defs import load_tables, parse_card
from tests._conv_cache import proto_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"

GAP = "trigger_when_unblocked_and_extra_breaks_per_dynamo_tap"
TARGETS = ("dm19-003", "dm23ex2-045")

SENJUOH_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "break", "player": "opp",
                "count": {"turn_count": {"kind": "dynamo_tap",
                                         "owner": "you"}}}]}

TUNE_SPELL = [
    {"op": "set_var", "name": "hand_n",
     "value": {"count": {"zone": "hand", "owner": "you"}}},
    {"op": "draw", "count": {"var": "hand_n"}},
    {"op": "move", "select": {"zone": "hand", "owner": "you",
                              "count": {"var": "hand_n"}},
     "to": "graveyard", "reason": "discard"},
]


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _unsup(r):
    return [u.get("need") if isinstance(u, dict) else u
            for u in (((r.get("partial") or {}).get("source") or {})
                      .get("unsupported") or [])]


def test_targets_are_the_whole_family():
    rows = _rows()
    assert len(rows) == 2051
    fam = {rid for rid, r in rows.items()
           if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert fam == set(TARGETS), fam
    r003 = rows["dm19-003"]
    assert r003["gaps"] == [GAP]
    assert (r003.get("partial") or {}).get("abilities") in (None, [])
    assert (r003.get("partial") or {}).get("keywords") == ["unblockable"]
    r045 = rows["dm23ex2-045"]
    assert r045["gaps"] == [GAP]
    assert r045.get("partial") in (None, {})
    assert r045.get("name") is None


def test_proto_forms():
    c986 = parse_card(proto_card("T986"), TABLES)
    assert SENJUOH_TRIGGER in c986.abilities
    assert c986.keywords == ["dynamo", "unblockable"]
    c987 = parse_card(proto_card("T987"), TABLES)
    assert c987.spell == TUNE_SPELL
    assert c987.keywords == ["s_trigger"]
