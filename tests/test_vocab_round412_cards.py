"""再変換ラウンド412（第377弾
battle_power_against_specific_civ）の記録テスト。

- 新規登録1件: dmd05-001 無限鉄拳オニナグリ
  （登録形は提出形と完全一致: partial の組立て済み部分
  〔進化クリーチャー / 闇・火 / コスト6 / パワー7000 /
  種族 ヒューマノイド・ハンター・エイリアン、mana 1、
  evolve_from {races: [ハンター]}、keywords
  [double_breaker]、battle_win アンタップ誘発〕に
  第377弾の確立形 static〔battle_power {amount: 2000,
  opponent_filter: {civs: [light]}}〕を公式テキストの
  条項順どおりアンタップ誘発の前に足し、unsupported を
  外したもの。abilities はこの2件ちょうど。補完なし
  （partial の text は行の公式テキスト全文と一致））。
- alias 畳み込み0件（alias 自体が無い）。正本判定:
  対象 id dmd05-001 を real.yaml / real_akashic.yaml /
  real_vocab.yaml / real_zone.yaml / proto.yaml /
  converted.yaml と照合し、いずれにも登録なし
  （proto.yaml のヒットは T1125 の notes 内参照のみ）。
  identity 実測で canon(dmd05-001) = dmd05-001
  （対象 id が正本）、aliases_for(無限鉄拳オニナグリ,
  dmd05-001) = []。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [battle_power_against_specific_civ]
  のため reopen で外してから submit（reopen の出力は
  対象1件ちょうど）。
- converted 10,356→10,357 / rejects 1,956→1,955、
  canonical 重なり0・漏れ0。
  battle_power_against_specific_civ はファミリーが
  この1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）と dm14-073 の既存データ負債は
  判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第377弾本体と同形（攻撃側を proto T1125 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
proto T1126（光・パワー8000ブロッカー）/ T1127
（火・パワー8000ブロッカー）を流用。
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
TARGET = "dmd05-001"
GAP = "battle_power_against_specific_civ"

STATIC = {"kind": "static", "affects": "self",
          "mod": {"battle_power": {"amount": 2000,
                                   "opponent_filter": {"civs": ["light"]}}}}
UNTAP = {"kind": "trigger",
         "when": {"event": "battle_win", "subject": "self"},
         "effect": [{"op": "untap", "select": {"ref": "self"}}]}
FORM = [STATIC, UNTAP]
FULL_TEXT = ("マナゾーンに置く時、このカードはタップして置く。\n"
             "進化-自分のハンター・クリーチャー１体の上に置く。\n"
             "光のクリーチャーとバトル中、このクリーチャーのパワーは+2000される。\n"
             "このクリーチャーがバトルに勝った時、このクリーチャーをアンタップする。\n"
             "W・ブレイカー(このクリーチャーはシールドを２枚ブレイクする)")


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


def test_round412_disposition():
    rej = _reject_rows()
    assert len(rej) == 1955
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10357
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0（aliases 欄）
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: 確立形2能力ちょうど（条項順）
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert c["keywords"] == ["double_breaker"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完なし）
    assert c["name"] == "無限鉄拳オニナグリ"
    assert c["types"] == ["creature", "evolution"]
    assert c["civs"] == ["darkness", "fire"]
    assert c["cost"] == 6 and c["power"] == 7000 and c["mana"] == 1
    assert c["races"] == ["ヒューマノイド", "ハンター", "エイリアン"]
    assert c["evolve_from"] == {"races": ["ハンター"]}
    # parse は double_breaker を breaks 常在型に展開するので
    # 包含で確認する（第372弾の作法）
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities and UNTAP in d.abilities
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第377弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _attack_and_block(e, attacker, blocker, state):
    """p0 の attacker がプレイヤーを攻撃し、block 判断が
    出たら blocker でブロックする。p1 の charge まで進める。"""
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 1:
            return
        if d["kind"] == "attack" and d.get("player") == 0 \
                and not state.get("attacked"):
            tgt = [k for k in keys
                   if k == f"attack:{attacker}:player"]
            if tgt:
                state["attacked"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "block":
            state["block_decision"] = keys
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
    raise AssertionError("attack never finished")


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def test_registered_beats_light_blocker_with_bonus(rules):
    """登録カード: 光ブロッカー8000（T1126）には素7000では
    負けるが battle_power +2000=9000 で勝ち、バトルに
    勝ったのでアンタップ誘発も発火する。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1126"]})
    state = {}
    _attack_and_block(e, TARGET, "T1126", state)
    assert state.get("attacked") and state.get("blocked"), state
    assert "T1126" in _defns(e, "graveyard", 1)
    assert TARGET in [e.s.cards[c].defn for c in e.bz_tops(0)]
    cid = next(c for c in e.zlist("bz", 0)
               if e.s.cards[c].defn == TARGET)
    assert not e.s.cards[cid].tapped


def test_registered_loses_to_non_light_blocker(rules):
    """登録カード: 火ブロッカー8000（T1127）には文明
    フィルタに合わず +2000 は付かないため負ける。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1127"]})
    state = {}
    _attack_and_block(e, TARGET, "T1127", state)
    assert state.get("attacked") and state.get("blocked"), state
    assert TARGET in _defns(e, "graveyard", 0)
    assert "T1127" in [e.s.cards[c].defn for c in e.bz_tops(1)]
