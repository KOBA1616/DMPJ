"""再変換ラウンド403（第368弾
draw_equal_to_chosen_cost）の記録テスト。

- 新規登録1件: dm21-011 グレート・リンク・
  テクノロジー（登録形は提出形と完全一致:
  partial の骨格〔水 / コスト10 / mana 1、
  types [spell]、abilities・spell ともに
  無し〕に第368弾の確立形〔シンパシーの
  static 1件（dm21-020 の登録先例と同形、
  cost_min: 1）＋ spell の choose
  {select: {zone: bz, owner: any, filter:
  {types: [creature]}, count: 1}, as: pick} /
  draw {count: {cost_of: pick}} の2 op〕を
  足し unsupported を外したもの。補完あり:
  partial の text は引く条項だけのため、
  シンパシー条項を abilities として補い、
  text には行の公式テキスト全文を入れた）。
- alias 畳み込み0件（alias は無い）。正本判定:
  対象 id dm21-011 を real.yaml /
  real_akashic.yaml / real_vocab.yaml /
  real_zone.yaml / proto.yaml / converted.yaml
  と照合し、いずれにも登録なし（proto.yaml の
  ヒットは T1108 の notes 内参照のみ）。
  identity 実測で canon_id = dm21-011。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [draw_equal_to_chosen_cost]
  のため reopen で外してから submit（reopen の
  出力は対象1件ちょうど）。
- converted 10,347→10,348 / rejects
  1,965→1,964、canonical 重なり0・漏れ0。
  draw_equal_to_chosen_cost はファミリーが
  この1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）は判断待ちのため本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第368弾本体の薄い包み（対象を登録カードに
差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。マナ役・
場の役は proto T1109（グレートメカオー・
コスト3、水マナ兼用）/ T1110（キカイヒーロー・
コスト5）/ T1111（対象外種族・コスト7）。
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

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm21-011"
GAP = "draw_equal_to_chosen_cost"

SYMPATHY = {"kind": "static", "zone": "hand", "affects": "self",
            "mod": {"cost": {"amount": -1,
                             "count": {"zone": "bz", "owner": "you",
                                       "filter": {"races": ["グレートメカオー",
                                                            "キカイヒーロー"]}}},
                    "cost_min": 1}}
SPELL = [{"op": "choose",
          "select": {"zone": "bz", "owner": "any",
                     "filter": {"types": ["creature"]},
                     "count": 1},
          "as": "pick"},
         {"op": "draw", "count": {"cost_of": "pick"}}]
FULL_TEXT = ("シンパシー：グレートメカオーとキカイヒーロー(この呪文を唱える時"
             "支払うコストは、バトルゾーンにある自分のグレートメカオーまたは"
             "キカイヒーロー１体につき１少なくなる。ただし、コストは１より"
             "少なくならない)\nバトルゾーンにあるクリーチャーを１体選ぶ。"
             "そのクリーチャーのコストの数と同じ枚数のカードを引く。")


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


def test_round403_disposition():
    rej = _reject_rows()
    assert len(rej) == 1964
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10348
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: abilities は static 1件ちょうど、
    # spell は choose/draw の2 op ちょうど、text は公式全文
    assert c["abilities"] == [SYMPATHY]
    assert len(c["abilities"]) == 1
    assert c["spell"] == SPELL
    assert len(c["spell"]) == 2
    assert c["text"] == FULL_TEXT
    assert c["name"] == "グレート・リンク・テクノロジー"
    assert c["types"] == ["spell"] and c["civs"] == ["water"]
    assert c["cost"] == 10 and c["mana"] == 1
    d = parse_card(c, TABLES)
    assert SYMPATHY in d.abilities
    assert [op["op"] for op in d.spell] == ["choose", "draw"]
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第368弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _boring(d):
    keys = [o["key"] for o in d["options"]]
    for want in ("pass", "end_turn", "end_attack", "end_phase"):
        if want in keys:
            return [keys.index(want)]
    return [0]


def _cast(rules, p0, p1, choose_defn):
    """p0 が登録カードを唱え、choose_defn を選んで解決まで
    進める。（唱えたか, choose の min, 唱える直前の手札数,
    解決後の手札数）を返す。"""
    e = _build(rules, p0, p1)
    cast = False
    chose_min = None
    hand_before = None
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not cast and d["kind"] == "main" and d.get("player") == 0 \
                and f"play:{TARGET}" in keys:
            hand_before = len(e.zlist("hand", 0))
            cast = True
            e.answer([keys.index(f"play:{TARGET}")])
            continue
        if cast and d["kind"] == "choose_cards":
            chose_min = d["min"]
            idx = [i for i, o in enumerate(d["options"])
                   if choose_defn in o["key"]]
            assert idx, f"{choose_defn} が選択肢に無い: {keys}"
            e.answer(idx[:1])
            continue
        if cast and d["kind"] in ("main", "charge", "attack"):
            break          # 解決が終わり次の通常判断に戻った
        e.answer(_boring(d))
    hand_after = len(e.zlist("hand", 0))
    return e, cast, chose_min, hand_before, hand_after


def test_registered_choose_own_creature_draws_its_cost(rules):
    """登録カード: 自分のコスト5（キカイヒーロー）を
    選ぶと5枚引く。唱えた呪文は墓地に置かれる。"""
    e, cast, chose_min, hb, ha = _cast(
        rules,
        {"hand": [TARGET], "mana": ["T1109"] * 10, "bz": ["T1110"]},
        {}, "T1110")
    assert cast
    assert ha == hb - 1 + 5
    assert TARGET in [e.cdef(c).id for c in e.zlist("graveyard", 0)]


def test_registered_choose_opponent_creature_draws_its_cost(rules):
    """登録カード: 相手のコスト7のクリーチャーを選んでも
    よい（owner: any）。7枚引く。"""
    e, cast, chose_min, hb, ha = _cast(
        rules,
        {"hand": [TARGET], "mana": ["T1109"] * 10},
        {"bz": ["T1111"]}, "T1111")
    assert cast
    assert ha == hb - 1 + 7


def test_registered_cast_with_sympathy_discount(rules):
    """登録カード: 実フローでシンパシー割引が効く。
    自分のグレートメカオー＋キカイヒーローが場にいれば
    支払いは8で足り、そのまま唱えてコスト3の
    グレートメカオーを選んで3枚引く（選択は必須 min=1）。"""
    e, cast, chose_min, hb, ha = _cast(
        rules,
        {"hand": [TARGET], "mana": ["T1109"] * 8,
         "bz": ["T1109", "T1110"]},
        {}, "T1109")
    assert cast and chose_min == 1
    assert ha == hb - 1 + 3


def test_registered_cast_with_no_creature_draws_zero(rules):
    """登録カード: バトルゾーンにクリーチャーが居なければ
    選べず、0枚引く（呪文自体は解決され墓地に置かれる）。"""
    e, cast, chose_min, hb, ha = _cast(
        rules,
        {"hand": [TARGET], "mana": ["T1109"] * 10},
        {}, "T1109")
    assert cast and chose_min is None    # 選択判断自体が出ない
    assert ha == hb - 1
    assert TARGET in [e.cdef(c).id for c in e.zlist("graveyard", 0)]
