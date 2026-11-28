"""語彙パイロット第316弾の対象カード検証（ラウンド351で登録済み）。

filter_not_keyword は dm06-016 / dm18-022 ジャスティス・
バインドの純粋2件のみだった（同名カードの2刷。他の行には
multi-gap でも現れない）。両行とも gaps に当該ギャップを
持ち、partial の notes 自身が「フィルタにキーワードの否定が
無いため絞れない」と明記していた。

第316弾の結論は最小語彙追加: フィルタキー not_keyword
（defs FILTER_KEYS ＋ selectors.filter_match の keyword の
鏡像 ＋ スキーマ再生成。差分は not_keyword の3行のみ）。
判定は付与分を含む特性値の keywords で見るため、静的で
「ブロッカー」を得たクリーチャーも対象から外れる
（第316弾本体で実挙動固定）。

ラウンド351で登録した。正本は dm18-022（identity の
canon_id 実測。partial の aliases 記録だけで決めたのでは
ない）で、dm06-016 は alias として畳み込んだ。登録形は
dm18-022 の partial の完成済み tap 形の filter に
not_keyword: blocker を追加し unsupported を外したもの
（dm06-016 の partial は spell 本体を持たない骨組みの
ため、提出形は同じ spell を補って構築した。本文の表記差:
dm06-016 は旧表記「S(シールド)・トリガー」、dm18-022 は
「S・トリガー」で、正本側の本文が登録されている）。
対象2行は gaps = [filter_not_keyword] のため reopen で
外してから submit。新規登録1件・alias 畳み込み1件・
stale クリーンアップ0件・差し戻し0件。converted
10,254→10,255 / rejects 2,064→2,062、canonical 重なり0・
漏れ0。filter_not_keyword はファミリーがこの2行だけ
だったため完全に解消。登録後は spell が [tap 1件]
ちょうどで、filter が {types: [creature],
not_keyword: blocker}、keywords は [s_trigger] のまま。
実挙動は test_vocab_round351_cards.py が登録カード自身で
固定。

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

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"
TABLES = load_tables()

TARGET = "dm18-022"
ALIAS = "dm06-016"
GAP = "filter_not_keyword"

TEXT = ("S・トリガー(この呪文をシールドゾーンから手札に加える時、"
        "コストを支払わずにすぐ唱えてもよい)\n"
        "バトルゾーンにある、「ブロッカー」以外のクリーチャーをすべてタップする。")

SPELL = [{"op": "tap",
          "select": {"zone": "bz", "owner": "any",
                     "filter": {"types": ["creature"],
                                "not_keyword": "blocker"},
                     "count": "all"}}]

FORM = {"id": TARGET,
        "name": "ジャスティス・バインド",
        "types": ["spell"],
        "civs": ["light"],
        "cost": 4,
        "mana": 1,
        "text": TEXT,
        "spell": SPELL,
        "keywords": ["s_trigger"]}


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


def test_target_registered():
    rows = _rows()
    assert len(rows) <= 2062  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10255  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    # 漏れ0: 正本は登録され、alias は独立エントリにも
    # reject 行にも残っていない
    assert TARGET in ids and TARGET not in rows
    assert ALIAS not in ids and ALIAS not in rows
    c = next(c for c in conv if c["id"] == TARGET)
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == [ALIAS]
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    for k in ("name", "types", "civs", "cost", "mana", "text",
              "spell", "keywords"):
        assert c.get(k) == FORM[k], k
    assert len(c["spell"]) == 1           # tap 1件ちょうど
    assert c["spell"][0]["select"]["filter"] == {
        "types": ["creature"], "not_keyword": "blocker"}
    # filter_not_keyword は完全に解消（ファミリーはこの2行だけ）
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


def test_established_form_parses():
    d = parse_card(FORM, TABLES)
    assert d.types == ["spell"] and d.civs == ["light"]
    assert d.cost == 4 and d.keywords == ["s_trigger"]
    assert d.spell == SPELL
    # 登録カード自身も parse でき、同じ形になる
    c = _conv_cache.find(CONVERTED, TARGET)
    d2 = parse_card(c, TABLES)
    assert d2.types == ["spell"] and d2.keywords == ["s_trigger"]
    assert d2.spell == SPELL
