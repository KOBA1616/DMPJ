"""再変換ラウンド413（第378弾
battle_power_against_high_power）の記録テスト。

- 新規登録1件: dmd15-003 超竜サンバースト・NEX
  （登録形は提出形と完全一致: partial の組立て済み部分
  〔進化クリーチャー / 火 / コスト7 / パワー11000 /
  種族 アーマード・ドラゴン、mana 1、evolve_from
  {races: [アーマード・ドラゴン]}、keywords
  [double_breaker]、battle_win may アンタップ誘発〕に
  第378弾の確立形 static〔battle_power {amount: 11000,
  opponent_filter: {power_ge: 12000}}〕を公式テキストの
  条項順どおり誘発の後に足し、unsupported を外した
  もの。abilities はこの2件ちょうど。補完なし
  （partial の text は行の公式テキスト全文と一致））。
- alias 畳み込み0件（alias 4件 dmc62-002 / dmc67-004 /
  promoy11-027 / promoy8-010 はいずれも rejects に
  独自行が無く、登録形の source.aliases に入っている）。
  正本判定: 対象 id と全 alias を real.yaml /
  real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
  proto.yaml / converted.yaml と照合し、いずれにも
  登録なし（proto.yaml のヒットは T1128 の notes 内
  参照のみ）。identity 実測で canon_id(dmd15-003) =
  dmd15-003（対象 id が正本）、全 alias の canon_id も
  dmd15-003、aliases_for(超竜サンバースト・NEX,
  dmd15-003) = alias 4件（partial の source.aliases
  と一致）。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [battle_power_against_high_power]
  のため reopen で外してから submit（reopen の出力は
  対象1件ちょうど）。
- converted 10,357→10,358 / rejects 1,955→1,954、
  canonical 重なり0・漏れ0。
  battle_power_against_high_power はファミリーが
  この1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）と dm14-073 の既存データ負債は
  判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第378弾本体と同形（攻撃側を proto T1128 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
proto T1129（水・パワー12000ブロッカー）/ T1130
（水・パワー11000ブロッカー）を流用。
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
TARGET = "dmd15-003"
GAP = "battle_power_against_high_power"
ALIASES = ["dmc62-002", "dmc67-004", "promoy11-027", "promoy8-010"]

UNTAP = {"kind": "trigger",
         "when": {"event": "battle_win", "subject": "self"},
         "effect": [{"op": "may", "body": [
             {"op": "untap", "select": {"ref": "self"}}]}]}
STATIC = {"kind": "static", "affects": "self",
          "mod": {"battle_power": {"amount": 11000,
                                   "opponent_filter": {"power_ge": 12000}}}}
FORM = [UNTAP, STATIC]
FULL_TEXT = ("進化-自分のアーマード・ドラゴン１体の上に置く。"
             "このクリーチャーがバトルに勝った時、このクリーチャーをアンタップしてもよい。"
             "パワー12000以上のクリーチャーとバトル中、このクリーチャーのパワーは+11000される。"
             "W・ブレイカー")


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


def test_round413_disposition():
    rej = _reject_rows()
    assert len(rej) == 1954
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10358
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0（aliases 欄）
    assert TARGET not in rej             # 対象行は解消
    for a in ALIASES:
        assert a not in rej              # alias に rejects の独自行は無い
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")
    # alias 4件は source.aliases に入っている
    assert (c.get("source") or {}).get("aliases") == ALIASES
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: 確立形2能力ちょうど（条項順）
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert c["keywords"] == ["double_breaker"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完なし）
    assert c["name"] == "超竜サンバースト・NEX"
    assert c["types"] == ["creature", "evolution"]
    assert c["civs"] == ["fire"]
    assert c["cost"] == 7 and c["power"] == 11000 and c["mana"] == 1
    assert c["races"] == ["アーマード・ドラゴン"]
    assert c["evolve_from"] == {"races": ["アーマード・ドラゴン"]}
    # parse は double_breaker を breaks 常在型に展開するので
    # 包含で確認する（第372弾の作法）
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities and UNTAP in d.abilities
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第378弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _battle(e, attacker_p, attacker, blocker):
    """attacker_p の attacker がプレイヤーを攻撃し、相手が
    blocker でブロックする。バトルが終わって attacker_p の
    次の charge が来たら戻る。may 判断は yes を選ぶ。"""
    state = {}
    for _ in range(3000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == attacker_p \
                and state.get("blocked"):
            return state
        if d["kind"] == "yes_no":
            state.setdefault("yes_no", []).append(keys)
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


def test_registered_beats_12000_blocker_with_bonus(rules):
    """登録カード: パワー12000ブロッカー（T1129）には
    素11000では負けるが +11000=22000 で勝ち、may
    アンタップ誘発も発火する。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1129"]})
    state = _battle(e, 0, TARGET, "T1129")
    assert state.get("attacked") and state.get("blocked"), state
    assert "T1129" in _defns(e, "graveyard", 1)
    assert TARGET in _tops(e, 0)
    cid = next(c for c in e.zlist("bz", 0)
               if e.s.cards[c].defn == TARGET)
    assert not e.s.cards[cid].tapped   # may でアンタップした


def test_registered_no_bonus_below_threshold(rules):
    """登録カード: パワー11000ブロッカー（T1130）は
    閾値12000未満なので加算は付かず、11000 vs 11000 の
    相打ちで両方破壊される。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1130"]})
    state = _battle(e, 0, TARGET, "T1130")
    assert state.get("attacked") and state.get("blocked"), state
    assert TARGET in _defns(e, "graveyard", 0)
    assert "T1130" in _defns(e, "graveyard", 1)
