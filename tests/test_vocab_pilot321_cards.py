"""語彙パイロット第321弾の対象カード検証（提出形の事前検証）。

trigger_when_unblocked は dm19-050 大鉄漢シルバスターズ /
dm19-069 食いしん坊チャロックの純粋2件のみ（multi-gap 行にも
現れない）。両行とも partial は骨格（abilities 無し）で、
未解決は「相手プレイヤーを攻撃してブロックされなかった時」
の1節のみ。

第321弾の結論はドリフト（追加語彙なし）。attack_end
レコードの blocked: false 照合（第175弾 T385 / 第219弾で
確立、登録先例は同じダイナモの dm20-016）で書ける:
- 形A（050）: trigger {event: attack_end, subject: self,
  target: player, blocked: false} → may [draw 1]。
- 形B（069）: 同じ when → may [move {zone: deck,
  from_top: 1} to mana, reason: put]。
ダイナモは keywords: [dynamo]（第76弾で定義済み）。

提出形は partial ＋ keywords [dynamo] ＋ abilities、
unsupported 除去。text は partial の全文（区切りが空白の
箇所は reject 行の公式全文どおり改行に直す）。
ラウンド356で reopen → submit する想定の事前検証で、
登録後は test_vocab_round356_cards.py が登録形を固定する。
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

TARGETS = ("dm19-050", "dm19-069")
GAP = "trigger_when_unblocked"
PROTO = {"dm19-050": "T984", "dm19-069": "T985"}

TRIGGER_UNBLOCKED_DRAW = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "may", "body": [{"op": "draw", "count": 1}]}]}
TRIGGER_UNBLOCKED_MANA = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "may", "body": [
        {"op": "move",
         "select": {"zone": "deck", "owner": "you", "from_top": 1},
         "to": "mana", "reason": "put"}]}]}

DYNAMO_TEXT = ("ダイナモ(バトルが始まる時、あるいはこの"
               "クリーチャーで攻撃できる時、このクリーチャーを"
               "タップしてもよい。そうした場合、そのターンの"
               "終わりまで、このクリーチャーのパワーと能力を"
               "バトルゾーンにある自分の他のダイナモ１体に加える)")

FORMS = {
    "dm19-050": {"name": "大鉄漢シルバスターズ",
                 "types": ["creature"], "civs": ["water"],
                 "cost": 3, "power": 1000,
                 "races": ["グレートメカオー", "ダイナモ"],
                 "mana": 1, "keywords": ["dynamo"],
                 "text": DYNAMO_TEXT + "\nこのクリーチャーが相手"
                         "プレイヤーを攻撃してブロックされなかった時、"
                         "カードを１枚引いてもよい。",
                 "abilities": [TRIGGER_UNBLOCKED_DRAW]},
    "dm19-069": {"name": "食いしん坊チャロック",
                 "types": ["creature"], "civs": ["nature"],
                 "cost": 3, "power": 2000,
                 "races": ["ドリームメイト", "ダイナモ"],
                 "mana": 1, "keywords": ["dynamo"],
                 "text": DYNAMO_TEXT + "\nこのクリーチャーが相手"
                         "プレイヤーを攻撃してブロックされなかった時、"
                         "自分の山札の上から１枚目を自分のマナゾーンに"
                         "置いてもよい。",
                 "abilities": [TRIGGER_UNBLOCKED_MANA]},
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


def test_targets_still_rejected_with_only_this_gap():
    rows = _rows()
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    for tid in TARGETS:
        assert tid not in ids, tid
        r = rows[tid]
        assert r.get("gaps") == [GAP], tid
        assert _unsup(r) == [GAP], tid
        assert not (r.get("partial") or {}).get("abilities"), tid
    # ファミリーはこの2件だけ（multi-gap 行にも現れない）
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(TARGETS), left


def test_submission_forms_parse_and_match_protos():
    rows = _rows()
    for tid, spec in FORMS.items():
        form = {"id": tid, **spec,
                "source": {"official": tid, "review": "pending"}}
        d = parse_card(form, TABLES)
        proto = parse_card(proto_card(PROTO[tid]), TABLES)
        assert d.abilities == proto.abilities, tid
        assert d.keywords == ["dynamo"], tid
        # partial の素性（名前・文明・コスト・パワー・種族・マナ）を保つ
        p = rows[tid]["partial"]
        for k in ("name", "types", "civs", "cost", "power",
                  "races", "mana"):
            assert form[k] == p[k], (tid, k)
