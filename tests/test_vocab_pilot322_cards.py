"""語彙パイロット第322弾の対象カード検証（ラウンド357で登録済み）。

trigger_when_unblocked_and_extra_breaks_per_dynamo_tap は dm19-003
電脳鉄人センジュオー / dm23ex2-045 の純粋2件のみ（multi-gap 行にも
現れない）。dm19-003 は partial あり（骨格）。dm23ex2-045 は rejects 行が
partial 空・name None・text はクリーチャー面のみで、by_product
（23ex2.jsonl）で原文照合済みのツインパクト（クリーチャー面は dm19-003
と同名・同能力で「１つ、シールドを追加でブレイクする」と読む。呪文面
センジュ・チューンは S・トリガーで「自分の手札の数と同じ枚数のカードを
引き、その後、こうして引いた枚数と同じ数、手札を捨てる」）。

第322弾の結論はエンジン拡張。新 turn_count kind `dynamo_tap`
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

ラウンド357で登録した。dm19-003 は partial ＋ keywords
[dynamo, unblockable] ＋確立形、unsupported 除去。dm23ex2-045 は
faces 形式（top text は convert_twin の形「面名: 面文 ／ 面名: 面文」）。
対象2行は gaps = [trigger_when_unblocked_and_extra_breaks_per_dynamo_tap]
のため reopen で外してから submit（reopen は dm19-003 の1件だけが外れた。
dm23ex2-045 の rejects 行には reason が無く reopen の条件に合わなかった
ためで、submit で rejects から外れた）。正本判定: 両 id とも
real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも無く、aliases 記録も無いことを
提出前に確認済み。新規登録2件・alias 畳み込み0件・stale クリーンアップ0件・
差し戻し0件。converted 10,266→10,268 / rejects 2,051→2,049、canonical
重なり0・漏れ0。trigger_when_unblocked_and_extra_breaks_per_dynamo_tap は
ファミリーがこの2件だけだったため完全に解消。登録形は確立形と完全一致
（連結・merge_split 由来の混入なし。dm23ex2-045 の top レベルに
keywords/abilities は無く、面ごとに keywords/abilities/spell が付く）。
実挙動は test_vocab_round357_cards.py が登録カード自身で固定する。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
_conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"
TABLES = load_tables()

TARGETS = ("dm19-003", "dm23ex2-045")
GAP = "trigger_when_unblocked_and_extra_breaks_per_dynamo_tap"

SENJUOH_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "break", "player": "opp",
                "count": {"turn_count": {"kind": "dynamo_tap",
                                         "owner": "you"}}}]}

# 提出形（converted.yaml に保存される形。discard はマクロで、parse 時に
# move（to: graveyard, reason: discard）へ展開される）
TUNE_SPELL_RAW = [
    {"op": "set_var", "name": "hand_n",
     "value": {"count": {"zone": "hand", "owner": "you"}}},
    {"op": "draw", "count": {"var": "hand_n"}},
    {"op": "discard", "select": {"zone": "hand", "owner": "you",
                                 "count": {"var": "hand_n"}}},
]

TUNE_SPELL = [
    {"op": "set_var", "name": "hand_n",
     "value": {"count": {"zone": "hand", "owner": "you"}}},
    {"op": "draw", "count": {"var": "hand_n"}},
    {"op": "move", "select": {"zone": "hand", "owner": "you",
                              "count": {"var": "hand_n"}},
     "to": "graveyard", "reason": "discard"},
]

DM19_003_TEXT = ("ダイナモ(バトルが始まる時、あるいはこのクリーチャーで攻撃できる時、このクリーチャーを"
                 "タップしてもよい。そうした場合、そのターンの終わりまで、このクリーチャーのパワーと能力を"
                 "バトルゾーンにある自分の他のダイナモ１体に加える)\nこのクリーチャーはブロックされない。\n"
                 "このクリーチャーが相手プレイヤーを攻撃してブロックされなかった時、このターンに「ダイナモ」"
                 "能力を使うためにタップした自分のダイナモ１体につき１枚、シールドを余分にブレイクする。")

CREATURE_FACE_TEXT = ("ダイナモ\nこのクリーチャーはブロックされない。\nこのクリーチャーが相手プレイヤーを攻撃して"
                     "ブロックされなかった時、このターンに「ダイナモ」能力を使うためにタップした自分のダイナモ"
                     "１体につき１つ、シールドを追加でブレイクする。")

TUNE_TEXT = ("S・トリガー\n自分の手札の数と同じ枚数のカードを引き、その後、こうして引いた枚数と同じ数、"
             "手札を捨てる。")

COMBINED_TEXT = ("電脳鉄人センジュオー: ダイナモ / このクリーチャーはブロックされない。 / このクリーチャーが"
                 "相手プレイヤーを攻撃してブロックされなかった時、このターンに「ダイナモ」能力を使うために"
                 "タップした自分のダイナモ１体につき１つ、シールドを追加でブレイクする。 ／ センジュ・チューン: "
                 "S・トリガー / 自分の手札の数と同じ枚数のカードを引き、その後、こうして引いた枚数と同じ数、"
                 "手札を捨てる。")


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


def test_targets_registered():
    rows = _rows()
    assert len(rows) <= 2049  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10268  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    for tid in TARGETS:
        # 漏れ0: 正本は登録され reject 行に残っていない
        # （alias は両件とも無し）
        assert tid in ids and tid not in rows, tid
        c = next(c for c in conv if c["id"] == tid)
        assert not (c.get("source") or {}).get("unsupported"), tid
        assert not (c.get("source") or {}).get("aliases"), tid
    # dm19-003: 登録形の完全一致（連結・merge_split 由来の混入なし）
    c003 = _conv_cache.find(CONVERTED, "dm19-003")
    assert c003["name"] == "電脳鉄人センジュオー"
    assert c003["types"] == ["creature"] and c003["civs"] == ["water"]
    assert c003["cost"] == 5 and c003["power"] == 3000
    assert c003["races"] == ["グレートメカオー", "ダイナモ"]
    assert c003["mana"] == 1
    assert c003["keywords"] == ["dynamo", "unblockable"]
    assert c003["text"] == DM19_003_TEXT
    assert c003["abilities"] == [SENJUOH_TRIGGER]
    # dm23ex2-045: faces 形式（top レベルに keywords/abilities は無い）
    c045 = _conv_cache.find(CONVERTED, "dm23ex2-045")
    assert "keywords" not in c045 and "abilities" not in c045
    assert c045["mana"] == 1
    assert c045["text"] == COMBINED_TEXT
    assert len(c045["faces"]) == 2
    f0, f1 = c045["faces"]
    assert f0["name"] == "電脳鉄人センジュオー"
    assert f0["types"] == ["creature"] and f0["civs"] == ["water"]
    assert f0["cost"] == 5 and f0["power"] == 3000
    assert f0["races"] == ["グレートメカオー", "ダイナモ"]
    assert f0["mana"] == 1
    assert f0["keywords"] == ["dynamo", "unblockable"]
    assert f0["text"] == CREATURE_FACE_TEXT
    assert f0["abilities"] == [SENJUOH_TRIGGER]
    assert f1["name"] == "センジュ・チューン"
    assert f1["types"] == ["spell"] and f1["civs"] == ["water"]
    assert f1["cost"] == 4 and f1["mana"] == 1
    assert f1["keywords"] == ["s_trigger"]
    assert f1["text"] == TUNE_TEXT
    assert f1["spell"] == TUNE_SPELL_RAW
    # trigger_when_unblocked_and_extra_breaks_per_dynamo_tap は完全に解消
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


def test_registered_forms_parse_and_match_protos():
    c003 = _conv_cache.find(CONVERTED, "dm19-003")
    d = parse_card(c003, TABLES)
    assert SENJUOH_TRIGGER in d.abilities
    assert d.keywords == ["dynamo", "unblockable"]
    proto = parse_card(proto_card("T986"), TABLES)
    assert SENJUOH_TRIGGER in proto.abilities
    c045 = _conv_cache.find(CONVERTED, "dm23ex2-045")
    d45 = parse_card(c045, TABLES)
    assert SENJUOH_TRIGGER in d45.faces[0].abilities
    assert d45.faces[0].keywords == ["dynamo", "unblockable"]
    assert d45.faces[1].spell == TUNE_SPELL
    assert d45.faces[1].keywords == ["s_trigger"]
    proto987 = parse_card(proto_card("T987"), TABLES)
    assert proto987.spell == TUNE_SPELL
