"""再変換ラウンド439（第404弾 draw_count_by_card）の記録テスト。

- 新規登録1件: dmr05-021 知識の包囲網
  （登録形は提出形と完全一致: partial の骨格
  〔呪文 / 水 / コスト7 / mana 1、spell・
  abilities ともに無し〕に第404弾の確立形 spell
  [choose {select: {zone: hand, owner: you,
  count: 1}, as: pick}, draw {count: {cost_of:
  pick}}] の2 op を足し、unsupported を外した
  もの。spell はこの2 op ちょうど、abilities は
  無いまま。**補完あり: spell と text**〔partial
  の text は断片「そのカードのコストと同じ枚数」
  のため、text には行の公式テキスト全文を入れた。
  登録後の全文一致も照合済み〕）。
- alias 畳み込み0件（alias 自体が無い。正本判定は
  通常型: 対象 id を real / real_akashic /
  real_vocab / real_zone / proto / converted と
  照合し登録なし〔proto のヒットは T1171 の notes
  内参照のみ〕、identity 実測で canon_id は対象
  自身、aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔draw_count_by_card〕の出力は対象
  1件ちょうど）。
- converted 10,383→10,384 / rejects 1,929→1,928、
  canonical 重なり0・漏れ0。draw_count_by_card
  は完全解消。
- 確立形は第385弾の手札 choose（「見せる」）と
  第368弾の呪文形 draw {count: {cost_of: pick}}
  の合成で、文面に任意性が無いため may で包ま
  ないのが第385弾との差。候補が無ければ cost_of
  は 0 で引かない（第368弾と同じ読み）。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）は本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第404弾本体と同形（対象を proto T1171 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T1109（コスト3・水マナ役）/
T1110（コスト5役）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests import _conv_cache  # noqa: E402
from tests.test_vocab_pilot404 import FULL_TEXT, SPELL  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmr05-021"
GAP = "draw_count_by_card"
NAME = "知識の包囲網"
MANA = ["T1109"] * 7   # 水7（コスト7の支払い）


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round439_disposition():
    rej = _reject_rows()
    assert len(rej) == 1928
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10384
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = [rid for rid, r in rej.items()
           if GAP in (r.get("gaps") or [])]
    assert fam == []                     # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["spell"]
    assert c["civs"] == ["water"]
    assert c["cost"] == 7 and c["mana"] == 1
    assert c["text"] == FULL_TEXT        # 公式全文（補完: text）
    # 登録形は提出形と完全一致: spell は確立形2 op ちょうど
    assert c["spell"] == SPELL
    assert len(c["spell"]) == 2
    assert not c.get("abilities")        # abilities は無いまま
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")
    d = parse_card(c, TABLES)
    assert [op["op"] for op in d.spell] == ["choose", "draw"]
    assert d.spell[0]["select"] == {"zone": "hand", "owner": "you",
                                    "count": 1}
    assert d.spell[0]["as"] == "pick"
    assert d.spell[1]["count"] == {"cost_of": "pick"}
    assert not d.abilities
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第404弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1=None):
    return scenario.build(rules, {"p0": p0, "p1": p1 or {},
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _boring(d):
    keys = [o["key"] for o in d["options"]]
    for want in ("pass", "end_turn", "end_attack", "end_phase"):
        if want in keys:
            return [keys.index(want)]
    return [0]


def _cast(rules, p0, p1=None, choose_defn=None):
    """p0 が登録カードを唱え、choose が出たら choose_defn を
    選んで解決まで進める。（engine, 唱えたか, choose の
    min, 唱える直前の手札数, 解決後の手札数）を返す。"""
    e = _build(rules, p0, p1)
    cast = False
    chose_min = None
    hand_before = None
    play_key = f"play:{TARGET}"
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not cast and d["kind"] == "main" and d.get("player") == 0 \
                and play_key in keys:
            hand_before = len(e.zlist("hand", 0))
            cast = True
            e.answer([keys.index(play_key)])
            continue
        if cast and d["kind"] == "choose_cards":
            chose_min = d["min"]
            if choose_defn is not None:
                idx = [i for i, o in enumerate(d["options"])
                       if choose_defn in o["key"]]
                assert idx, f"{choose_defn} が選択肢に無い: {keys}"
                e.answer(idx[:1])
            else:
                e.answer([0])
            continue
        if cast and d["kind"] in ("main", "charge", "attack"):
            break          # 解決が終わり次の通常判断に戻った
        e.answer(_boring(d))
    return e, cast, chose_min, hand_before, len(e.zlist("hand", 0))


def test_registered_show_cost5_draws_5(rules):
    """実挙動: 手札のコスト5を見せると5枚引く。見せた
    カードは手札に留まる。唱えた呪文は墓地に置かれる。"""
    e, cast, chose_min, hb, ha = _cast(
        rules, {"hand": [TARGET, "T1110"], "mana": MANA},
        choose_defn="T1110")
    assert cast
    assert ha == hb - 1 + 5
    assert "T1110" in [e.cdef(c).id for c in e.zlist("hand", 0)]
    assert TARGET in [e.cdef(c).id for c in e.zlist("graveyard", 0)]


def test_registered_show_choice_is_mandatory(rules):
    """実挙動: 候補が2枚あれば選択は必須（min=1）で、
    コスト3を選べば3枚引く（文面に任意性は無い）。"""
    e, cast, chose_min, hb, ha = _cast(
        rules, {"hand": [TARGET, "T1109", "T1110"], "mana": MANA},
        choose_defn="T1109")
    assert cast
    assert chose_min == 1
    assert ha == hb - 1 + 3
    assert "T1109" in [e.cdef(c).id for c in e.zlist("hand", 0)]


def test_registered_no_other_hand_draws_0(rules):
    """実挙動: 手札がこの呪文だけなら見せるカードが
    無く、0枚で解決して墓地に置かれる（cost_of は
    未束縛で 0。第368弾と同じ読み）。"""
    e, cast, chose_min, hb, ha = _cast(
        rules, {"hand": [TARGET], "mana": MANA})
    assert cast
    assert ha == hb - 1
    assert TARGET in [e.cdef(c).id for c in e.zlist("graveyard", 0)]


def test_registered_opponent_hand_not_a_candidate(rules):
    """判別（範囲）: 見せられるのは自分の手札だけ
    （owner: you）。相手の手札にコスト5があっても
    引けない。"""
    e, cast, chose_min, hb, ha = _cast(
        rules, {"hand": [TARGET], "mana": MANA},
        p1={"hand": ["T1110"]})
    assert cast
    assert ha == hb - 1
