"""語彙パイロット第321弾の対象カード検証（ラウンド356で登録済み）。

trigger_when_unblocked は dm19-050 大鉄漢シルバスターズ /
dm19-069 食いしん坊チャロックの純粋2件のみ（multi-gap 行にも
現れない）。両行とも partial は骨格（abilities 無し）で、
未解決は「相手プレイヤーを攻撃してブロックされなかった時」
の1節のみだった。

第321弾の結論はドリフト（追加語彙なし）。attack_end
レコードの blocked: false 照合（第175弾 T385 / 第219弾で
確立、登録先例は同じダイナモの dm20-016 風使いのシャイアン）
で書ける:
- 形A（050）: trigger {event: attack_end, subject: self,
  target: player, blocked: false} → may [draw 1]。
- 形B（069）: 同じ when → may [move {zone: deck,
  from_top: 1} to mana, reason: put]。
ダイナモは keywords: [dynamo]（第76弾で定義済み）。

ラウンド356で登録した。提出形は partial ＋ keywords
[dynamo] ＋ abilities、unsupported 除去。text は partial の
全文で、ダイナモ説明と本条項の区切りは reject 行の公式
全文どおり改行に直した。対象2行は gaps =
[trigger_when_unblocked] のため reopen で外してから
submit（reopen の出力は対象2件ちょうど）。正本判定:
両行とも partial に aliases 記録は無く、id は real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも無いことを
提出前に確認済み。新規登録2件・alias 畳み込み0件・
stale クリーンアップ0件・差し戻し0件。converted
10,264→10,266 / rejects 2,053→2,051、canonical
重なり0・漏れ0。trigger_when_unblocked はファミリーが
この2件だけだったため完全に解消。登録形は確立形と
完全一致（abilities は各1件ちょうど、連結・merge_split
由来の混入なし、keywords は [dynamo]）。実挙動は
test_vocab_round356_cards.py が登録カード自身で固定する。

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


def test_targets_registered():
    rows = _rows()
    assert len(rows) == 2051
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10266
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
    # trigger_when_unblocked は完全に解消（ファミリーはこの2件だけ）
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
