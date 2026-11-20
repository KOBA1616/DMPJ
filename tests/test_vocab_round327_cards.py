"""再変換ラウンド327（第292弾「破壊して払う代替コスト」）の記録テスト。

- 新規登録5件: dm22rp2x-038 / dm23rp2x-004 / dm22rp2x-015 /
  dm24ex1-003 / dm26rp3-011。
- alias 畳み込み1件: dm26rp3-sec015 → dm26rp3-011（同一本文の
  シークレット印刷。canon は 011）。
- 差し戻し0件。ラウンド直後: converted 10,189 / rejects 2,140、
  重なり0・漏れ0。alternative_cost_destroy と
  optional_cost_reduction_with_sacrifice は残り0件で両ファミリー解消。
- ラウンド側の修正: dm24ex1-003 の CIP 二重登録（split 由来の
  chooser: random 形を残し partial 由来を除去）と、dm26rp3-011
  モード3 の owner: any 化。詳細と実挙動は
  tests/test_vocab_pilot292_cards.py（登録形）側に固定した。

本ファイルはラウンド時点の登録状態だけを見る（後続ラウンドで
総数が変わっても壊れないよう、対象6件の帰属だけを assert する）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

NEW = ["dm22rp2x-038", "dm23rp2x-004", "dm22rp2x-015",
       "dm24ex1-003", "dm26rp3-011"]
FOLDED = {"dm26rp3-sec015": "dm26rp3-011"}
GAPS = {"alternative_cost_destroy", "optional_cost_reduction_with_sacrifice"}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round327_disposition():
    rej = _reject_rows()
    for cid in NEW:
        c = _conv_cache.find(CONVERTED, cid)
        assert c is not None, cid                      # 新規登録された
        assert cid not in rej, cid                     # rejects に残らない
        assert "unsupported" not in (c.get("source") or {}), cid
    for alias, canon in FOLDED.items():
        # 独立 id では登録されず、canon の alias としてのみ存在し、
        # reject 行も残らない（漏れなし）
        assert _conv_cache.find(CONVERTED, alias) is None, alias
        c = _conv_cache.find(CONVERTED, canon)
        assert alias in ((c.get("source") or {}).get("aliases") or []), alias
        assert alias not in rej, alias
    # 両ファミリー解消: 対象ギャップを含む行は rejects に1件も残らない
    assert not [r["id"] for r in rej.values()
                if GAPS & set(r.get("gaps") or [])]
    # 対象範囲の重なり0: 新規登録 id が rejects に重複しない
    assert not [cid for cid in NEW if cid in rej]
