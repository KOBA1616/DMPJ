"""再変換ラウンド406（第371弾 set_power_zero）の記録テスト。

- 新規登録1件: dmex15-b025 永遠の無（登録形は
  提出形と完全一致: partial の骨格〔闇 / コスト5 /
  mana 1、types [spell]、abilities・spell ともに
  無し〕に第371弾の確立形〔spell の choose
  {owner: opp, as: victim} / modify {power_set: 0,
  duration: end_of_turn} の2 op（第370弾
  set_power_to_zero の確立形と同形。登録先例
  dmrp11-zs01・dm24ex2-042）〕を足し、unsupported
  を外したもの。spell は2 op ちょうど、abilities は
  無いまま。**補完あり**: partial の text は第2条項の
  断片（「そのクリーチャーのパワーを０にする」）だけ
  のため、text には行の公式テキスト全文を入れた）。
- alias 畳み込み0件（alias は無い）。正本判定:
  対象 id dmex15-b025 を real.yaml /
  real_akashic.yaml / real_vocab.yaml /
  real_zone.yaml / proto.yaml / converted.yaml と
  照合し、いずれにも登録なし（proto.yaml のヒットは
  T1115 の notes 内参照のみ）。identity 実測で
  canon = dmex15-b025、aliases_for = []。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [set_power_zero] のため reopen で
  外してから submit（reopen の出力は対象1件ちょうど）。
- converted 10,350→10,351 / rejects 1,962→1,961、
  canonical 重なり0・漏れ0。set_power_zero は
  ファミリーがこの1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）は判断待ちのため本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第371弾本体の薄い包み（対象を登録カードに差し
替えたもの）で、tests.conftest は import しない
（第319弾以降の作法）。判別役は proto T1105
（パワー4000ブロッカー）/ T1114（実効6000の
加算役）/ T1107（能力なしパワー2000）/ T872
（闇マナ役）。
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
TARGET = "dmex15-b025"
GAP = "set_power_zero"

SPELL = [{"op": "choose",
          "select": {"zone": "bz", "owner": "opp",
                     "filter": {"types": ["creature"]},
                     "count": 1},
          "as": "victim"},
         {"op": "modify",
          "select": {"ref": "victim"},
          "mod": {"power_set": 0},
          "duration": "end_of_turn"}]
FULL_TEXT = ("相手のクリーチャーを１体選ぶ。このターン、そのクリーチャーの"
             "パワーを０にする。（パワー０以下のクリーチャーは破壊される）")


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


def test_round406_disposition():
    rej = _reject_rows()
    assert len(rej) == 1961
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10351
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: spell は2 op ちょうど、
    # abilities は無いまま、text は公式全文（補完あり）
    assert c["spell"] == SPELL
    assert len(c["spell"]) == 2
    assert not c.get("abilities")
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT
    assert c["name"] == "永遠の無"
    assert c["types"] == ["spell"] and c["civs"] == ["darkness"]
    assert c["cost"] == 5 and c["mana"] == 1
    d = parse_card(c, TABLES)
    assert [op["op"] for op in d.spell] == ["choose", "modify"]
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第371弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _find(e, zone, p, defn):
    cards = e.bz_tops(p) if zone == "bz" else e.zlist(zone, p)
    return next(c for c in cards if e.cdef(c).id == defn)


def _boring(d):
    keys = [o["key"] for o in d["options"]]
    for want in ("pass", "end_turn", "end_attack", "end_phase"):
        if want in keys:
            return [keys.index(want)]
    return [0]


def _cast(rules, p0, p1, choose_defn=None):
    """p0 が登録カードを唱え、choose_defn を選んで解決まで
    進める。（engine, 唱えたか, choose の min）を返す
    （第371弾の作法）。"""
    e = _build(rules, p0, p1)
    cast = False
    chose_min = None
    play_key = f"play:{TARGET}"
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not cast and d["kind"] == "main" and d.get("player") == 0 \
                and play_key in keys:
            cast = True
            e.answer([keys.index(play_key)])
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
    return e, cast, chose_min


def test_registered_cast_sets_chosen_power_zero_and_destroys(rules):
    """登録カード: 唱え、相手のパワー4000（T1105）を
    選ぶと、そのパワーが0になり状況起因処理で破壊されて
    墓地に行く。唱えた呪文自身も墓地に置かれる。"""
    e, cast, _ = _cast(rules,
                       {"hand": [TARGET], "mana": ["T872"] * 5},
                       {"bz": ["T1105"]}, "T1105")
    assert cast
    assert "T1105" not in _defns(e, "bz", 1)
    assert "T1105" in _defns(e, "graveyard", 1)
    assert TARGET in _defns(e, "graveyard", 0)


def test_registered_cast_power_set_overwrites_power_additions(rules):
    """登録カード: 実効パワー6000（印刷3000＋static +3000）の
    T1114 を選んでも、power_set は加算ごと上書きして
    0にするため破壊される。"""
    e0 = _build(rules, {}, {"bz": ["T1114"]})
    ch = e0.chars(_find(e0, "bz", 1, "T1114"))
    assert ch["power"] == 6000          # 前提: 加算が効いている
    e, cast, _ = _cast(rules,
                       {"hand": [TARGET], "mana": ["T872"] * 5},
                       {"bz": ["T1114"]}, "T1114")
    assert cast
    assert "T1114" not in _defns(e, "bz", 1)
    assert "T1114" in _defns(e, "graveyard", 1)


def test_registered_cast_two_candidates_choice_is_mandatory(rules):
    """登録カード: 候補が2体いれば選択は必須（min=1）で、
    選ばなかった方は残る。"""
    e, cast, chose_min = _cast(
        rules,
        {"hand": [TARGET], "mana": ["T872"] * 5},
        {"bz": ["T1105", "T1107"]}, "T1105")
    assert cast and chose_min == 1
    assert "T1105" in _defns(e, "graveyard", 1)
    assert "T1107" in _defns(e, "bz", 1)


def test_registered_cast_no_opponent_creature_no_effect(rules):
    """登録カード: 相手のクリーチャーがいなければ choose の
    候補は無く（自分のクリーチャーは owner: opp で候補に
    入らない）、効果は空振りで解決する。自分の T1107 は
    無事で、呪文は墓地に置かれる。"""
    e, cast, chose_min = _cast(
        rules,
        {"hand": [TARGET], "mana": ["T872"] * 5, "bz": ["T1107"]},
        {}, None)
    assert cast and chose_min is None    # 選択判断自体が出ない
    assert "T1107" in _defns(e, "bz", 0)
    assert _defns(e, "graveyard", 0) == [TARGET]
    assert _defns(e, "graveyard", 1) == []
