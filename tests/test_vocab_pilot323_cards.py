"""語彙パイロット第323弾の対象カード検証（ラウンド358で登録済み）。

unblocked_condition は dmx04-011 ケロディ二郎 / dmx09-049 誕生の祈
の純粋2件のみ（multi-gap 行にも現れない）。両行とも partial は空で、
by_product（x04.jsonl / x09.jsonl）で原文照合済み。両カードとも
単一能力のクリーチャーで、全文が「このクリーチャーが相手プレイヤーを
攻撃してブロックされなかった時」の1節だけ。

第323弾の結論はドリフト（追加語彙なし）。第321弾で確立した
attack_end {subject: self, target: player, blocked: false} そのもの。
- 形A（dmx04-011）: trigger {event: attack_end, subject: self,
  target: player, blocked: false} → may [move {zone: bz, owner: any,
  filter: {types: [creature]}, count: 1} to hand, reason: return]
  （select の owner 既定は you。両プレイヤーのクリーチャーが対象の
  ため owner: any が必要。第292弾と同じ罠で、提出前の実挙動プローブで
  相手のクリーチャーが候補に出ないことを検出して修正した）
- 形B（dmx09-049）: 同じ when → may [choose {zone: deck, owner: you,
  look: true, filter: {types: [creature]}, count: 1} as t;
  move {ref: t, count: all} to hand, reason: draw; shuffle]

ラウンド358で登録した。dmx04-011 は水・コスト4・パワー2000・
ゲル・フィッシュ/ハンター・マナ1、dmx09-049 は自然・コスト3・
パワー2000・ビーストフォーク・マナ1。対象2行は gaps =
[unblocked_condition] のため reopen で外してから submit（reopen は
2件とも外れた）。新規登録2件・alias 畳み込み0件・stale クリーンアップ
0件・差し戻し0件。converted 10,268→10,270 / rejects 2,049→2,047、
canonical 重なり0・漏れ0。unblocked_condition はファミリーがこの
2件だけだったため完全に解消。登録形は確立形と完全一致（連結・
merge_split 由来の混入なし）。

注意: dmx09-049 は submit 時に同名再録3件（dm09-054 / dmc34-053 /
dmc39-031、いずれも「誕生の祈」）が source.aliases に記録された。
この3件は converted.yaml にも rejects.jsonl にも無く、rejects 行の
畳み込みではない（提出前の「aliases 記録も無し」という確認は、
対象 id 自体に aliases が無いことの確認で、同名再録の存在までは
見ていなかった。訂正）。実挙動は test_vocab_round358_cards.py が
登録カード自身で固定する。

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

TARGETS = ("dmx04-011", "dmx09-049")
GAP = "unblocked_condition"

FORM_A = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "may", "body": [
        {"op": "move",
         "select": {"zone": "bz", "owner": "any",
                    "filter": {"types": ["creature"]}, "count": 1},
         "to": "hand", "reason": "return"}]}]}
FORM_B = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "may", "body": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "look": True,
                    "filter": {"types": ["creature"]}, "count": 1},
         "as": "t"},
        {"op": "move", "select": {"ref": "t", "count": "all"},
         "to": "hand", "reason": "draw"},
        {"op": "shuffle"}]}]}

DMX04_011_TEXT = ("このクリーチャーが相手プレイヤーを攻撃してブロックされなかった時、"
                  "バトルゾーンにあるクリーチャーを１体選び、持ち主の手札に戻してもよい。")
DMX09_049_TEXT = ("このクリーチャーが相手プレイヤーを攻撃してブロックされなかった時、"
                  "自分の山札を見る。その中からクリーチャーを１体選び、相手に見せてから"
                  "自分の手札に加えてもよい。その後、山札をシャッフルする。")


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_registered():
    rows = _rows()
    assert len(rows) <= 2047  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10270  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    for tid in TARGETS:
        # 漏れ0: 正本は登録され reject 行に残っていない
        assert tid in ids and tid not in rows, tid
        c = next(c for c in conv if c["id"] == tid)
        assert not (c.get("source") or {}).get("unsupported"), tid
    # dmx04-011: 登録形の完全一致（連結・merge_split 由来の混入なし）
    c011 = _conv_cache.find(CONVERTED, "dmx04-011")
    assert c011["name"] == "ケロディ二郎"
    assert c011["types"] == ["creature"] and c011["civs"] == ["water"]
    assert c011["cost"] == 4 and c011["power"] == 2000
    assert c011["races"] == ["ゲル・フィッシュ", "ハンター"]
    assert c011["mana"] == 1
    assert c011["text"] == DMX04_011_TEXT
    assert c011["abilities"] == [FORM_A]
    assert not (c011.get("source") or {}).get("aliases"), "dmx04-011"
    # dmx09-049: 登録形の完全一致。同名再録3件が aliases に記録される
    c049 = _conv_cache.find(CONVERTED, "dmx09-049")
    assert c049["name"] == "誕生の祈"
    assert c049["types"] == ["creature"] and c049["civs"] == ["nature"]
    assert c049["cost"] == 3 and c049["power"] == 2000
    assert c049["races"] == ["ビーストフォーク"]
    assert c049["mana"] == 1
    assert c049["text"] == DMX09_049_TEXT
    assert c049["abilities"] == [FORM_B]
    assert (c049.get("source") or {}).get("aliases") == [
        "dm09-054", "dmc34-053", "dmc39-031"]
    # unblocked_condition は完全に解消
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left


def test_registered_forms_parse_and_match_protos():
    c011 = _conv_cache.find(CONVERTED, "dmx04-011")
    d = parse_card(c011, TABLES)
    assert FORM_A in d.abilities
    proto = parse_card(proto_card("T988"), TABLES)
    assert FORM_A in proto.abilities
    c049 = _conv_cache.find(CONVERTED, "dmx09-049")
    d49 = parse_card(c049, TABLES)
    assert FORM_B in d49.abilities
    proto989 = parse_card(proto_card("T989"), TABLES)
    assert FORM_B in proto989.abilities
