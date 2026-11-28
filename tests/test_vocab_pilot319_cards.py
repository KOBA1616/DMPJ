"""語彙パイロット第319弾の対象カード検証（ラウンド354で登録済み）。

destroy_self_after_attacking は純粋2件のみだった:
dm22rp1-038 レター＝ジェンゲガー / dm22rp2x-061
ディッシュ＝ウィッシュ。両行とも partial は骨格
（キーワードのみ、abilities 無し）で、未解決は
「攻撃の後、このクリーチャーを破壊する」の1節のみ。

第319弾の結論はドリフト（追加語彙なし）。確立形は
第315弾 dmex12-s19 の登録形そのもの:
- 形A（dm22rp1-038）: 攻撃誘発 → delayed_trigger
  {when: {event: attack_end, subject: self},
  duration: during_attack} → destroy {ref: self}。
- 形B（dm22rp2x-061）: 形A ＋ ブロック誘発 →
  delayed_trigger {when: {event: attack_end,
  target: self}, ...}。
変換済み9件の旧近似形（when: turn_end ＋
during_attack）は発火しない死に形（第319弾本体で
実挙動固定）。登録形はこの確立形を使う。

ラウンド354で登録した。dm22rp1-038 の残りの条項
（自分のターンの終わりに山札の上から1枚目を墓地に
置き、それがアビスなら1枚引く）はラウンドで構築した:
turn_end 誘発 {player: you} ＋ move {from_top: 1,
as: milled} ＋ if {count {ref: milled, filter:
race_has アビス} == 1} → draw 1（判定は dm23rp2x-037
の登録先例と同形）。提出前に全アビス／全非アビス山札で
実挙動を検証し、登録後も test_vocab_round354_cards.py
が登録カード自身で固定する。
対象2行は gaps = [destroy_self_after_attacking] の
ため reopen で外してから submit（出力は対象2件
ちょうど）。正本判定は identity の canon_id 実測で
2件とも自 ID（alias は登録エントリの source.aliases
への記録のみで、alias 側の reject 行は元々無かった）。
新規登録2件・stale クリーンアップ0件・差し戻し0件。
converted 10,260→10,262 / rejects 2,057→2,055、
canonical 重なり0・漏れ0。destroy_self_after_attacking
はファミリーがこの2件だけだったため完全に解消。
登録形は確立形と完全一致（abilities は両件とも
2件ちょうど、連結・merge_split 由来の混入なし）。

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

TARGETS = ("dm22rp1-038", "dm22rp2x-061")
GAP = "destroy_self_after_attacking"
PROTO = {"dm22rp1-038": "T979", "dm22rp2x-061": "T980"}

DESTROY_SELF = {"op": "destroy", "select": {"ref": "self"}}
TRIGGER_A = {"kind": "trigger",
             "when": {"event": "attack", "subject": "self"},
             "effect": [{"op": "delayed_trigger",
                         "when": {"event": "attack_end",
                                  "subject": "self"},
                         "duration": "during_attack",
                         "effect": [DESTROY_SELF]}]}
TRIGGER_B_BLOCK = {"kind": "trigger",
                   "when": {"event": "block", "subject": "self"},
                   "effect": [{"op": "delayed_trigger",
                               "when": {"event": "attack_end",
                                        "target": "self"},
                               "duration": "during_attack",
                               "effect": [DESTROY_SELF]}]}
# ラウンド354で構築した dm22rp1-038 のターン終了条項
TURN_END_038 = {"kind": "trigger",
                "when": {"event": "turn_end", "player": "you"},
                "effect": [
                    {"op": "move",
                     "select": {"zone": "deck", "owner": "you",
                                "from_top": 1, "count": "all"},
                     "to": "graveyard", "reason": "put",
                     "as": "milled"},
                    {"op": "if",
                     "cond": {"cmp": [{"count": {"ref": "milled",
                                                 "filter": {"race_has": "アビス"}}},
                                      "==", 1]},
                     "then": [{"op": "draw", "count": 1}]}]}

TEXT_038 = ("ブロッカー（このクリーチャーをタップして、相手クリーチャーの攻撃先を"
            "このクリーチャーに変更してもよい）\n"
            "このクリーチャーが攻撃する時、攻撃の後、このクリーチャーを破壊する。\n"
            "自分のターンの終わりに、自分の山札の上から１枚目を墓地に置く。"
            "それがアビスなら、カードを１枚引く。")
TEXT_061 = ("S・トリガー（このクリーチャーをシールドゾーンから手札に加える時、"
            "コストを支払わずにすぐ召喚してもよい）\n"
            "ブロッカー（このクリーチャーをタップして、相手クリーチャーの攻撃先を"
            "このクリーチャーに変更してもよい）\n"
            "このクリーチャーが攻撃する時またはブロックした時、その攻撃の後、"
            "このクリーチャーを破壊する。")

FORMS = {
    "dm22rp1-038": {"name": "レター＝ジェンゲガー",
                    "types": ["creature"], "civs": ["darkness"],
                    "cost": 3, "power": 2000,
                    "races": ["アビスロイヤル"], "mana": 1,
                    "text": TEXT_038, "keywords": ["blocker"],
                    "abilities": [TRIGGER_A, TURN_END_038],
                    "aliases": ["promoy21-052"]},
    "dm22rp2x-061": {"name": "ディッシュ＝ウィッシュ",
                     "types": ["creature"], "civs": ["darkness"],
                     "cost": 2, "power": 5000,
                     "races": ["アビスロイヤル"], "mana": 1,
                     "text": TEXT_061,
                     "keywords": ["s_trigger", "blocker"],
                     "abilities": [TRIGGER_A, TRIGGER_B_BLOCK],
                     "aliases": ["dm22rp2-061", "dm22rp2-20a",
                                 "dm22rp2x-20a", "promoy21-069"]},
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
    assert len(rows) <= 2055  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10262  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    for tid, spec in FORMS.items():
        # 漏れ0: 正本は登録され reject 行に残っていない。
        # alias は独立エントリにも reject 行にも無い
        assert tid in ids and tid not in rows, tid
        for a in spec["aliases"]:
            assert a not in ids and a not in rows, a
        c = next(c for c in conv if c["id"] == tid)
        assert not (c.get("source") or {}).get("unsupported"), tid
        assert (c.get("source") or {}).get("aliases") == spec["aliases"], tid
        # 登録形の完全一致（連結・merge_split 由来の混入なし）
        for k in ("name", "types", "civs", "cost", "power", "races",
                  "mana", "text", "keywords", "abilities"):
            assert c.get(k) == spec[k], (tid, k)
        assert len(c["abilities"]) == 2, tid
    # destroy_self_after_attacking は完全に解消（ファミリーはこの2件だけ）
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


def test_registered_forms_parse_and_match_protos():
    for tid, spec in FORMS.items():
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None, tid
        d = parse_card(c, TABLES)
        proto = parse_card(proto_card(PROTO[tid]), TABLES)
        # 自壊誘発は対応プロトの abilities と完全一致
        # （038 はそれにターン終了条項が1件加わる）
        for ab in proto.abilities:
            assert ab in d.abilities, tid
        assert len(d.abilities) >= len(proto.abilities), tid
        assert d.keywords == spec["keywords"], tid
