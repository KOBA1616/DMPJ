"""再変換ラウンド440（第405弾 count_distinct_races）の記録テスト。

- 新規登録1件: dm20-037 反骨鉄拳バーニアン
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 光 / コスト4 / パワー2000 /
  種族 グレートメカオー、mana 1、keywords・
  abilities ともに無し〕に第405弾の確立形 static
  〔affects: self, mod {power: {amount: 2000,
  count: {distinct_race_count: {zone: bz,
  owner: opp, filter: {types: [creature]}}}}}}〕
  1件を足し、unsupported を外したもの。
  abilities はこの1件ちょうど、keywords は
  無いまま。**補完なし**〔partial の text は
  行の公式テキスト全文と一致し、登録後の
  全文一致も照合済み〕）。
- alias 畳み込み0件（alias 自体が無い。正本判定は
  通常型: 対象 id を real / real_akashic /
  real_vocab / real_zone / proto / converted と
  照合し登録なし〔proto のヒットは T1172 の notes
  内参照のみ〕、identity 実測で canon_id は対象
  自身、aliases_for = []）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔count_distinct_races〕の出力は対象
  1件ちょうど）。
- converted 10,384→10,385 / rejects 1,928→1,927、
  canonical 重なり0・漏れ0。count_distinct_races
  は完全解消。
- distinct_race_count は新規式キーの初回登録
  （第145弾 distinct_cost_count・第212弾
  distinct_type_count の種族版。式の評価は
  Python 側のみで Rust 側の式ミラーは無い）。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第405弾本体と同形（対象を proto T1172 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T001（単一種族役＝種族
テスト）/ T787（2種族役＝アンノウン＋ゼニス）/
T371（3種族役）/ T004（パワー3000ブロッカー役）。
バトルゾーンは共有ゾーンなので所有は bz_tops(p) /
zlist(zone, p) で見る。
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
from tests.test_vocab_pilot405 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm20-037"
GAP = "count_distinct_races"
NAME = "反骨鉄拳バーニアン"


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


def test_round440_disposition():
    rej = _reject_rows()
    assert len(rej) == 1927
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10385
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = [rid for rid, r in rej.items()
           if GAP in (r.get("gaps") or [])]
    assert fam == []                     # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"]
    assert c["civs"] == ["light"]
    assert c["cost"] == 4 and c["power"] == 2000 and c["mana"] == 1
    assert c["races"] == ["グレートメカオー"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は確立形 static 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("keywords")          # keywords は無いまま
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")
    d = parse_card(c, TABLES)
    assert FORM[0] in d.abilities
    assert len(d.abilities) == 1
    assert d.abilities[0]["mod"]["power"]["count"] == {
        "distinct_race_count": {"zone": "bz", "owner": "opp",
                                "filter": {"types": ["creature"]}}}
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第405弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _powers(e, tid, p):
    return [e.chars(c)["power"] for c in e.bz_tops(p)
            if e.cdef(c).id == tid]


def test_registered_power_no_opponent_creatures(rules):
    e = _build(rules, {"bz": [TARGET]}, {"bz": []})
    assert _powers(e, TARGET, 0) == [2000]


def test_registered_power_one_distinct_race(rules):
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T001"]})
    assert _powers(e, TARGET, 0) == [4000]


def test_registered_power_same_race_twice_counts_once(rules):
    # 同種族（テスト）が2体いても種類数は1 → 4000
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T001", "T001"]})
    assert _powers(e, TARGET, 0) == [4000]


def test_registered_power_multi_race_creature_counts_each_race(rules):
    # T787 は2種族（アンノウン＋ゼニス）を持つ → 2種で 6000
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T787"]})
    assert _powers(e, TARGET, 0) == [6000]
    # T371 は3種族を持つ → 3種で 8000
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T371"]})
    assert _powers(e, TARGET, 0) == [8000]


def test_registered_own_creatures_do_not_count(rules):
    # 自分の2種族獣（T787）は数えない（owner: opp の判別）
    e = _build(rules, {"bz": [TARGET, "T787"]}, {"bz": []})
    assert _powers(e, TARGET, 0) == [2000]
    # 自分の種族は相手の種族と重なっても影響しない
    e = _build(rules, {"bz": [TARGET, "T001"]}, {"bz": ["T001"]})
    assert _powers(e, TARGET, 0) == [4000]


def _keys(d):
    return [o["key"] for o in d["options"]]


def _battle(e, attacker_p, attacker, blocker):
    """attacker_p の attacker がプレイヤーを攻撃し、相手が
    blocker でブロックする。バトルが終わって attacker_p の
    次の charge が来たら戻る。"""
    state = {}
    for _ in range(3000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == attacker_p \
                and state.get("blocked"):
            return state
        if d["kind"] == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d["min"])))
        elif d["kind"] == "attack" and d.get("player") == attacker_p \
                and not state.get("attacked"):
            tgt = [k for k in keys if k == f"attack:{attacker}:player"]
            if tgt:
                state["attacked"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "block":
            pick = [i for i, k in enumerate(keys)
                    if k.startswith(f"bz:{blocker}")]
            if pick:
                state["blocked"] = True
                e.answer([pick[0]])
            else:
                e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("battle never finished")


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _tops(e, p):
    return [e.s.cards[c].defn for c in e.bz_tops(p)]


def test_registered_battle_wins_by_counted_power(rules):
    # ブロッカー T004（パワー3000・種族 テスト1種）で
    # 登録カードは 2000+2000=4000 になり勝つ（素2000では負ける判別）
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T004"]})
    state = _battle(e, 0, TARGET, "T004")
    assert state.get("attacked") and state.get("blocked"), state
    assert "T004" in _defns(e, "graveyard", 1)
    assert TARGET in _tops(e, 0)
