"""語彙パイロット第320弾の対象カード検証（ラウンド355で登録済み）。

trigger_when_blocked は dm26ex2-068 ワダウザノミコト /
dm26rp1-074 ノーガルディ・ネギオ＆ガルダンディ・ナスオの
純粋2件のみ（multi-gap 行にも現れない）。両行とも partial は
骨格（abilities 無し）で、未解決は「ブロックした時」
（068）／「ブロックされた時」（074）の照合のみという
notes が付いている。

第320弾の結論はドリフト（追加語彙なし）。block レコードは
{subject: ブロッカー, attacker: 攻撃クリーチャー} で発行され、
when 照合は両キーを既に扱う:
- 形A（074）: trigger {event: block, attacker: self} →
  break {player: opp, count: 2}（第280弾の登録先例形）。
- 形B（068）: trigger {event: block, subject: self} →
  move {ref: self} ＋ move {ref: event.attacker} を手札へ
  （dm20-045 の登録先例）。併記の離脱条項も既存部品で構成:
  choose {from_top: 4, look, count: all} as pile →
  choose {ref: pile, count: 1} as pick → move {ref: pick}
  to hand → repeat {times: {count: {ref: pile, zone: deck}}}
  [choose {ref: pile, zone: deck, count: 1} as c → modal
  [deck top / deck bottom]]（dm24ex1-054 の repeat＋choose＋
  modal 形の山札内版）。

ラウンド355で登録した。提出形は partial ＋ abilities、
unsupported 除去。dm26rp1-074 の partial の text は
「このクリーチャーがブロックされた時」だけに切れて
いたため、reject 行の公式全文に差し替えた（dm26ex2-068
の text は全文のまま）。対象2行は gaps =
[trigger_when_blocked] のため reopen で外してから
submit（reopen の出力は対象2件ちょうど）。正本判定は
identity の canon_id 実測で2件とも自 ID、aliases は
無し。新規登録2件・alias 畳み込み0件・stale
クリーンアップ0件・差し戻し0件。converted
10,262→10,264 / rejects 2,055→2,053、canonical
重なり0・漏れ0。trigger_when_blocked はファミリーが
この2件だけだったため完全に解消。登録形は確立形と
完全一致（abilities は 068 が2件・074 が1件ちょうど、
連結・merge_split 由来の混入なし、068 の keywords は
[s_trigger, blocker] のまま）。実挙動は
test_vocab_round355_cards.py が登録カード自身で固定する。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
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

TARGETS = ("dm26ex2-068", "dm26rp1-074")
GAP = "trigger_when_blocked"
PROTO = {"dm26ex2-068": "T982", "dm26rp1-074": "T983"}

TRIGGER_BLOCKED_BREAK = {
    "kind": "trigger",
    "when": {"event": "block", "attacker": "self"},
    "effect": [{"op": "break", "player": "opp", "count": 2}]}
TRIGGER_BLOCK_BOUNCE = {
    "kind": "trigger",
    "when": {"event": "block", "subject": "self"},
    "effect": [
        {"op": "move", "select": {"ref": "self"},
         "to": "hand", "reason": "return"},
        {"op": "move", "select": {"ref": "event.attacker"},
         "to": "hand", "reason": "return"}]}
TRIGGER_LEAVE_LOOK = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "subject": "self"},
    "effect": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "from_top": 4,
                    "look": True, "count": "all"},
         "as": "pile"},
        {"op": "choose", "select": {"ref": "pile", "count": 1},
         "as": "pick"},
        {"op": "move", "select": {"ref": "pick", "count": "all"},
         "to": "hand", "reason": "draw"},
        {"op": "repeat",
         "times": {"count": {"ref": "pile", "zone": "deck"}},
         "body": [
             {"op": "choose",
              "select": {"ref": "pile", "zone": "deck", "count": 1},
              "as": "c"},
             {"op": "modal",
              "modes": [
                  [{"op": "move",
                    "select": {"ref": "c", "count": "all"},
                    "to": "deck", "position": "top",
                    "reason": "put"}],
                  [{"op": "move",
                    "select": {"ref": "c", "count": "all"},
                    "to": "deck", "position": "bottom",
                    "reason": "put"}]]}]}]}

TEXT_068 = ("S・トリガー（このカードを自分のシールドゾーンから"
            "手札に加える時、コストを支払わずにすぐ実行してもよい）\n"
            "ブロッカー（このクリーチャーをタップして、相手"
            "クリーチャーの攻撃先をこのクリーチャーに変更してもよい）\n"
            "このクリーチャーがブロックした時、このクリーチャーと"
            "攻撃しているクリーチャーを持ち主の手札に戻す。\n"
            "このクリーチャーが離れた時、自分の山札の上から４枚を"
            "見る。その中から１枚を手札に加え、残りを好きな順序で"
            "山札の上か下に置く。")
TEXT_074 = ("このクリーチャーがブロックされた時、この"
            "クリーチャーは相手のシールドを２つブレイクする。")

FORMS = {
    "dm26ex2-068": {"name": "ワダウザノミコト",
                    "types": ["creature"],
                    "civs": ["light", "water"], "cost": 4,
                    "power": 1000,
                    "races": ["ミズガミ", "ロスト・クルセイダー"],
                    "mana": 1, "keywords": ["s_trigger", "blocker"],
                    "text": TEXT_068,
                    "abilities": [TRIGGER_BLOCK_BOUNCE,
                                  TRIGGER_LEAVE_LOOK]},
    "dm26rp1-074": {"name": "ノーガルディ・ネギオ＆ガルダンディ・ナスオ",
                    "types": ["creature"], "civs": ["nature"],
                    "cost": 2, "power": 3000,
                    "races": ["ワイルド・ベジーズ"], "mana": 1,
                    "text": TEXT_074,
                    "abilities": [TRIGGER_BLOCKED_BREAK]},
}


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
    assert len(rows) == 2053
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10264
    assert not (ids & set(rows))          # canonical 重なり0
    for tid, spec in FORMS.items():
        # 漏れ0: 正本は登録され reject 行に残っていない
        # （alias は両件とも無し）
        assert tid in ids and tid not in rows, tid
        c = next(c for c in conv if c["id"] == tid)
        assert not (c.get("source") or {}).get("unsupported"), tid
        assert not (c.get("source") or {}).get("aliases"), tid
        # 登録形の完全一致（連結・merge_split 由来の混入なし）
        for k in ("name", "types", "civs", "cost", "power",
                  "races", "mana", "text", "abilities"):
            assert c.get(k) == spec[k], (tid, k)
        assert c.get("keywords") == spec.get("keywords"), tid
        assert len(c["abilities"]) == len(spec["abilities"]), tid
    # trigger_when_blocked は完全に解消（ファミリーはこの2件だけ）
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


def test_registered_forms_parse_and_match_protos():
    for tid, spec in FORMS.items():
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None, tid
        d = parse_card(c, TABLES)
        proto = parse_card(proto_card(PROTO[tid]), TABLES)
        assert d.abilities == proto.abilities, tid
        assert d.keywords == (spec.get("keywords") or []), tid
