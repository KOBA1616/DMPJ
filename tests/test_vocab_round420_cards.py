"""再変換ラウンド420（第385弾 cost_amount_draw）の記録テスト。

- 新規登録1件: promoy18-087 リッチ警官 キャッシュ！
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 光・水 / コスト8 / パワー2500 /
  種族 ヒューマノイド、mana 1、keywords・abilities
  ともに無し〕に第385弾の確立形1能力〔CIP 誘発
  may [choose {select: {zone: hand, owner: you,
  count: 1}, as: pick}, draw {count: {cost_of:
  pick}}]〕（「見せてもよい」は登録先例 dmr05-046 の
  may 内 choose 形、ドロー枚数は第368弾の draw
  {count: {cost_of: pick}}）を足し、unsupported を
  外したもの。abilities はこの1件ちょうど、keywords
  は無いまま。補完あり: partial の text は条項の
  断片（「コストと同じ枚数引く」）のみのため、登録形
  では text に行の公式テキスト全文が入っている）。
- alias 畳み込み0件（alias は無い）。正本判定:
  対象 id を real.yaml / real_akashic.yaml /
  real_vocab.yaml / real_zone.yaml / proto.yaml /
  converted.yaml と照合し、いずれにも登録なし
  （proto.yaml のヒットは T1148 の notes 内参照
  のみ）。identity 実測で canon_id(promoy18-087) =
  promoy18-087、aliases_for は []。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [cost_amount_draw] のため
  reopen で外してから submit（reopen の出力は
  対象1件ちょうど）。
- converted 10,364→10,365 / rejects 1,948→1,947、
  canonical 重なり0・漏れ0。cost_amount_draw は
  ファミリーがこの1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）と dm14-073 の既存データ負債は
  判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第385弾本体と同形（発生源を proto T1148 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役の手札
カードとマナは第385弾の proto を流用: T1109
（コスト3・水）/ T1110（コスト5）/ T1146（光・
マナ用）。マナは水4＋光4（多色の支払いには文明
ごとに同文明マナが要る）。
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
from tests.test_vocab_pilot385 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "promoy18-087"
GAP = "cost_amount_draw"
NAME = "リッチ警官 キャッシュ！"
MANA = ["T1109"] * 4 + ["T1146"] * 4   # 水4＋光4（多色の支払い）


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


def test_round420_disposition():
    rej = _reject_rows()
    assert len(rej) == 1947
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10365
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["light", "water"]
    assert c["cost"] == 8 and c["power"] == 2500 and c["mana"] == 1
    assert c["races"] == ["ヒューマノイド"]
    assert not c.get("keywords")         # keywords は無いまま
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形 trigger 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.abilities == FORM
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第385弾本体と同形、発生源は登録カード） ----------

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


def _summon(rules, p0, may_yes, choose_defn=None):
    """p0 が登録カードを召喚し、CIP の may / choose に
    答えて解決まで進める。（engine, 召喚したか, may が
    出たか, choose の min）を返す。"""
    e = _build(rules, p0)
    played = False
    may_seen = False
    chose_min = None
    play_key = f"play:{TARGET}"
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and play_key in keys:
            played = True
            e.answer([keys.index(play_key)])
            continue
        if played and d["kind"] == "yes_no":
            may_seen = True
            e.answer([keys.index("yes" if may_yes else "no")])
            continue
        if played and d["kind"] == "choose_cards":
            chose_min = d["min"]
            idx = [i for i, o in enumerate(d["options"])
                   if choose_defn in o["key"]]
            assert idx, f"{choose_defn} が選択肢に無い: {keys}"
            e.answer(idx[:1])
            continue
        if played and d["kind"] in ("main", "charge", "attack"):
            break          # 解決が終わり次の通常判断に戻った
        e.answer(_boring(d))
    return e, played, may_seen, chose_min


def _hand_defns(e):
    return [e.cdef(c).id for c in e.zlist("hand", 0)]


def test_registered_show_cost5_draws_five(rules):
    """実挙動: 登録カードが出た時、手札のコスト5
    （T1110）を見せると5枚引く。見せたカード自体は
    手札に留まる。"""
    e, played, may_seen, _ = _summon(
        rules, {"hand": [TARGET, "T1110"], "mana": MANA}, True, "T1110")
    assert played and may_seen
    hand = _hand_defns(e)
    assert len(hand) == 1 + 5          # 見せた1枚＋引いた5枚
    assert hand[0] == "T1110"          # 見せたカードは手札に留まる
    assert TARGET in [e.cdef(c).id for c in e.zlist("bz", 0)]


def test_registered_decline_may_draws_nothing(rules):
    """実挙動: 見せないことを選べば何も引かない
    （任意性は may が担う）。"""
    e, played, may_seen, _ = _summon(
        rules, {"hand": [TARGET, "T1110"], "mana": MANA}, False, "T1110")
    assert played and may_seen
    assert _hand_defns(e) == ["T1110"]


def test_registered_choose_cost3_among_two_draws_three(rules):
    """実挙動: 候補が2枚（コスト3とコスト5）あれば
    選択は必須（min=1）で、コスト3を選べば3枚引く
    （cost_of は束縛したカードのコストを読む判別）。"""
    e, played, may_seen, chose_min = _summon(
        rules, {"hand": [TARGET, "T1109", "T1110"], "mana": MANA},
        True, "T1109")
    assert played and may_seen
    assert chose_min == 1
    hand = _hand_defns(e)
    assert len(hand) == 2 + 3          # 残り2枚＋引いた3枚
    assert "T1109" in hand and "T1110" in hand


def test_registered_empty_hand_resolves_without_draw(rules):
    """実挙動: 召喚後に手札が無ければ、may に同意して
    も選ぶ候補が無く0枚引く（cost_of は 0）。解決は
    通常どおり終わる。"""
    e, played, may_seen, chose_min = _summon(
        rules, {"hand": [TARGET], "mana": MANA}, True, "T1109")
    assert played and may_seen
    assert chose_min is None           # 選択判断自体が出ない
    assert _hand_defns(e) == []
    assert TARGET in [e.cdef(c).id for c in e.zlist("bz", 0)]
