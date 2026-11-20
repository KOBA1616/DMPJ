"""語彙パイロット第317弾の対象カード検証（ラウンド352で登録済み）。

all_civilizations_condition は純粋3件のみだった:
dm26sd1-b013 フェアリー・ミラクル / dm27-050 ゴレン・
キャノン / dm26sd1-b005 魔誕と光喜と楽識と炎怒と哀樹の
決断。3行とも gaps は当該ギャップのみで、partial は
いずれも骨格（タイプ・文明・コスト・マナ数と
unsupported のみ。本文は切れている）だったため、提出形は
公式全文から spell を構築した。

第317弾の結論はドリフト（追加語彙なし）。条件の確立
イディオムは登録済み dmx16-064（同文の CIP）の
{op: if, cond: {all: [cmp: [{count: {zone, owner: you,
filter: {civs: [文明]}}}, ">=", 1] ×5]}, then: [...]}。
- 形A（b013）: mana_put（from_top: 1）の後に if。
  条件は1枚目を置いた後に判定する。
- 形B（dm27-050）: destroy の後に if＋destroy。
- 形C（b005）: 条件の「自分のエレメント」はマナでは
  なくバトルゾーン（総合ルール403.1）。if の then は
  may [modal 全モード] else [modal 2回・同選択可]、
  else も modal 2回。モードは既存先例の合成
  （シールド化 move to: shield / reason: charge、
  discard chooser: random、エレメント破壊 destroy
  {zone: bz, filter: cost_le: 6}、マナ置き＋may 回収）。
  実挙動は第317弾本体と test_vocab_round352_cards.py
  （登録カード自身）で固定。

ラウンド352で登録した。対象3行は gaps =
[all_civilizations_condition] のため reopen で外して
から submit（reopen の出力は対象3件ちょうど）。
正本判定は identity の canon_id 実測で3件とも自 ID
（b005 の partial の source.aliases 記録だけで決めた
のではない）。新規登録3件・stale クリーンアップ0件・
差し戻し0件。converted 10,255→10,258 / rejects
2,062→2,059、canonical 重なり0・漏れ0。
all_civilizations_condition はファミリーがこの3件
だけだったため完全に解消。登録形は確立形と完全一致
（形A/B の spell は2ステップ、形C は if 1件ちょうど、
keywords なし、連結・merge_split 由来の混入なし）。
alias は登録エントリの source.aliases への記録のみ
（b013 は17件、b005 は4件。alias 側の reject 行は
元々無かった）。

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

TARGETS = ("dm26sd1-b013", "dm27-050", "dm26sd1-b005")
GAP = "all_civilizations_condition"
CIVS5 = ["light", "water", "darkness", "fire", "nature"]

ALIASES = {
    "dm26sd1-b013": ["dm24bd4-015", "dm27-053", "dm27-053cc",
                     "dmart03-003", "dmbd01-015", "dmex06-095",
                     "dmex08-099", "dmrp18-a13", "dmrp18-b13",
                     "dmx01-039", "dmx14-080", "dmx16-070",
                     "dmx22b-078", "dmx26-026", "promoy17-056",
                     "promoy23-070", "promoy23-073"],
    "dm27-050": [],
    "dm26sd1-b005": ["dm24ex3-rp4011", "dm24ex3-rp4sec15",
                     "dm24rp4-011", "dm24rp4-sec15"],
}


def _all_civs(zone):
    return {"all": [{"cmp": [{"count": {"zone": zone, "owner": "you",
                                         "filter": {"civs": [c]}}},
                             ">=", 1]}
                    for c in CIVS5]}


# 登録形の spell（マクロ表記。格納形もこの表記のまま）
MANA_PUT_TOP = {"op": "mana_put",
                "select": {"zone": "deck", "owner": "you", "from_top": 1}}
DESTROY_3000 = {"op": "destroy",
                "select": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"],
                                      "power_le": 3000},
                           "count": 1}}
SPELL_A = [MANA_PUT_TOP,
           {"op": "if", "cond": _all_civs("mana"), "then": [MANA_PUT_TOP]}]
SPELL_B = [DESTROY_3000,
           {"op": "if", "cond": _all_civs("mana"), "then": [DESTROY_3000]}]

MODES = [
    [{"op": "move",
      "select": {"zone": "deck", "owner": "you", "from_top": 1},
      "to": "shield", "reason": "charge"}],
    [{"op": "draw", "count": 2}],
    [{"op": "discard",
      "select": {"zone": "hand", "owner": "opp", "count": 1,
                 "chooser": "random"}}],
    [{"op": "destroy",
      "select": {"zone": "bz", "owner": "opp",
                 "filter": {"cost_le": 6}, "count": 1}}],
    [MANA_PUT_TOP,
     {"op": "may",
      "body": [{"op": "move",
                "select": {"zone": "mana", "owner": "you", "count": 1},
                "to": "hand", "reason": "return"}]}],
]
_MODAL_ALL = {"op": "modal", "count": 5, "modes": MODES}
_MODAL_TWO = {"op": "modal", "count": 2, "repeat": True, "modes": MODES}
SPELL_C = [{"op": "if", "cond": _all_civs("bz"),
            "then": [{"op": "may", "body": [_MODAL_ALL],
                      "else": [_MODAL_TWO]}],
            "else": [_MODAL_TWO]}]

TEXT_A = ("自分の山札の上から１枚をマナゾーンに置く。"
          "自分のマナゾーンにすべての文明が揃っていれば、"
          "自分の山札の上からもう１枚、マナゾーンに置く。")
TEXT_B = ("相手のパワー3000以下のクリーチャーを１体破壊する。\n"
          "自分のマナゾーンにすべての文明が揃っていれば、"
          "相手のパワー3000以下のクリーチャーをもう１体、破壊する。")
TEXT_C = ("次の中から２回選ぶ。同じものを選んでもよい。"
          "自分のエレメントにすべての文明が揃っていれば、"
          "かわりにすべてを１回ずつ使ってもよい。\n"
          "▶自分の山札の上から１枚をシールド化する。\n"
          "▶カードを２枚引く。\n"
          "▶相手の手札を１枚見ないで選び、捨てさせる。\n"
          "▶相手のコスト６以下のエレメントを１つ選び、破壊する。\n"
          "▶自分の山札の上から１枚をマナゾーンに置く。"
          "その後、カードを１枚、自分のマナゾーンから手札に戻してもよい。")

FORMS = {
    "dm26sd1-b013": {"name": "フェアリー・ミラクル",
                     "civs": ["nature"], "cost": 3,
                     "text": TEXT_A, "spell": SPELL_A, "proto": "T972"},
    "dm27-050": {"name": "ゴレン・キャノン",
                 "civs": ["fire"], "cost": 5,
                 "text": TEXT_B, "spell": SPELL_B, "proto": "T973"},
    "dm26sd1-b005": {"name": "魔誕と光喜と楽識と炎怒と哀樹の決断",
                     "civs": CIVS5, "cost": 5,
                     "text": TEXT_C, "spell": SPELL_C, "proto": "T974"},
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
    assert len(rows) == 2059
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10258
    assert not (ids & set(rows))          # canonical 重なり0
    for tid, spec in FORMS.items():
        # 漏れ0: 正本は登録され reject 行に残っていない。
        # alias は独立エントリにも reject 行にも無い
        assert tid in ids and tid not in rows, tid
        for a in ALIASES[tid]:
            assert a not in ids and a not in rows, a
        c = next(c for c in conv if c["id"] == tid)
        assert not (c.get("source") or {}).get("unsupported"), tid
        assert (c.get("source") or {}).get("aliases") \
            == (ALIASES[tid] or None), tid
        # 登録形の完全一致（連結・merge_split 由来の混入なし）
        for k in ("name", "civs", "cost", "text", "spell"):
            assert c.get(k) == spec[k], (tid, k)
        assert c["types"] == ["spell"] and c["mana"] == 1, tid
        assert not c.get("keywords"), tid
    # all_civilizations_condition は完全に解消（ファミリーはこの3件だけ）
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


def test_registered_forms_parse_and_match_protos():
    for tid, spec in FORMS.items():
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None, tid
        d = parse_card(c, TABLES)
        assert d.types == ["spell"] and d.civs == spec["civs"], tid
        assert d.cost == spec["cost"], tid
        assert d.spell == parse_card(proto_card(spec["proto"]),
                                     TABLES).spell, tid
