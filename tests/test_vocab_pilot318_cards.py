"""語彙パイロット第318弾の対象カード検証（ラウンド353で登録済み）。

shield_to_hand_strigger_deny は純粋2件のみだった:
dmrp22-031 エメラルの海幻 / dm24ex3-or1 超天使
ゴルドラン・ゴルギーニ。両行とも partial は完成済みで、
未解決は「効果で自分のシールドを手札に加える時、その
『S・トリガー』は使えない」の1節のみだった。

第318弾の結論はドリフト（追加語彙なし）: 第296弾の
形A＝move 引数 strigger: "off"（S・トリガーの印）が
そのまま効く。ラウンド353で登録した。登録形は partial の
手札へ加える move に印を足し、unsupported を外したもの:
- dmrp22-031（形A1）: シンカパワーの戻し move
  {zone: shield, count: 1} → hand に印。partial の text は
  「シンカライズ」だけに切れていたため公式全文に差し替え。
- dm24ex3-or1（形A2）: 攻撃誘発の束分割で、残りを
  手札に加える move {ref: fc, not_types: [creature]}
  に印（クリーチャーを場に出す move には付けない）。

正本判定は identity の実データ照合による: canon_id は
2件とも自 ID、dm24ex3-or1 の aliases_for は partial の
記録と同じ4件。対象2行は gaps = [shield_to_hand_
strigger_deny] のため reopen で外してから submit
（reopen の出力は対象2件ちょうど）。converted
10,258→10,260 / rejects 2,059→2,057、canonical
重なり0・漏れ0。shield_to_hand_strigger_deny は
ファミリー単独だったため完全に解消。

実挙動は test_vocab_round353_cards.py が登録カード
自身で固定（第318弾本体はプロト T975〜T978 で固定）。

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

TARGETS = ("dmrp22-031", "dm24ex3-or1")
GAP = "shield_to_hand_strigger_deny"
PROTO = {"dmrp22-031": "T975", "dm24ex3-or1": "T977"}
ALIASES = {"dmrp22-031": None,
           "dm24ex3-or1": ["dm24ex3-rp3or1", "dm24ex3-rp3sec01",
                           "dm24rp3-or01", "dm24rp3-sec001"]}
TEXT_031 = ("シンカライズ：このタマシードがクリーチャーであるかのように、"
            "この上に進化クリーチャーを置いてもよい。\n"
            "このタマシードが出た時、カードを１枚引く。\n"
            "シンカパワー：このタマシードが進化する時、自分の手札を１枚"
            "シールド化し、その後、自分のシールドを１つ選んで手札に加える。"
            "ただし、その「S・トリガー」は使えない。")


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


def _hand_moves(card):
    out = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("op") == "move" and node.get("to") == "hand":
                out.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(card.get("abilities") or [])
    return out


def test_targets_registered():
    rows = _rows()
    assert len(rows) == 2057
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10260
    assert not (ids & set(rows))          # canonical 重なり0
    for tid in TARGETS:
        # 漏れ0: 登録され reject 行に残っていない
        assert tid in ids and tid not in rows, tid
        c = _conv_cache.find(CONVERTED, tid)
        assert not (c.get("source") or {}).get("unsupported")
        assert (c.get("source") or {}).get("aliases") == ALIASES[tid], tid
        for a in ALIASES[tid] or []:
            assert a not in ids and a not in rows, a
        # abilities は2件ちょうど、手札 move は1件で印つき
        assert len(c["abilities"]) == 2, tid
        hm = _hand_moves(c)
        assert len(hm) == 1 and hm[0].get("strigger") == "off", tid
    # dmrp22-031 の text は公式全文（partial の切れた text ではない）
    c = _conv_cache.find(CONVERTED, "dmrp22-031")
    assert c["text"] == TEXT_031
    # shield_to_hand_strigger_deny は完全に解消
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


def test_registered_forms_parse_and_match_protos():
    for tid in TARGETS:
        c = _conv_cache.find(CONVERTED, tid)
        d = parse_card(c, TABLES)
        proto = parse_card(proto_card(PROTO[tid]), TABLES)
        # 登録形の abilities は対応プロトと完全一致（印つき）
        assert d.abilities == proto.abilities, tid
        assert not (d.source or {}).get("unsupported"), tid
