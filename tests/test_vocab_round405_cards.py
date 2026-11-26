"""再変換ラウンド405（第370弾 set_power_to_zero）の記録テスト。

- 新規登録1件: dm24ex2-042 騎士のコード
  オルタナティブ（登録形は提出形と完全一致:
  partial〔水晶ソウル2（crystal_soul: 2）、
  keywords [double_breaker]、破壊時誘発1件が
  組立て済み〕の abilities の先頭に第370弾の
  確立形 CIP 誘発〔trigger {event: move, to: bz,
  subject: self} → choose {owner: opp,
  as: victim} / modify {power_set: 0,
  duration: end_of_turn}（dmrp11-zs01 の登録
  先例と同形）〕を足し、unsupported を外した
  もの。abilities は [CIP, 破壊時] の2件
  ちょうど。補完なし: partial の text は行の
  公式テキスト全文と一致。civs は partial の
  骨格どおり [] のまま（proto T1113 の civs
  [zero] はフィクスチャ側の表記で持ち込まない））。
- alias 畳み込み0件（alias は無い）。正本判定:
  対象 id dm24ex2-042 を real.yaml /
  real_akashic.yaml / real_vocab.yaml /
  real_zone.yaml / proto.yaml / converted.yaml
  と照合し、いずれにも登録なし（proto.yaml の
  ヒットは T1113 の notes 内参照のみ）。
  identity 実測で canon = dm24ex2-042、
  aliases_for = []。stale クリーンアップ0件・
  差し戻し0件。
- 対象1行は gaps = [set_power_to_zero] のため
  reopen で外してから submit（reopen の出力は
  対象1件ちょうど）。
- converted 10,349→10,350 / rejects
  1,963→1,962、canonical 重なり0・漏れ0。
  set_power_to_zero はファミリーがこの1件
  だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）は判断待ちのため本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第370弾本体の薄い包み（対象を登録カードに
差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
proto T1105（パワー4000ブロッカー）/ T1114
（実効6000の加算役）/ T1107（能力なしパワー
2000）/ T1106（win_all_battles 持ちブロッカー）/
T789（無色ゼニス）。マナ役は zero 文明の T1112
（本エンジンは支払いでも civs の zero を文字
どおり照合するため）。
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
TARGET = "dm24ex2-042"
GAP = "set_power_to_zero"

CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "effect": [
           {"op": "choose",
            "select": {"zone": "bz", "owner": "opp",
                       "filter": {"types": ["creature"]}, "count": 1},
            "as": "victim"},
           {"op": "modify",
            "select": {"ref": "victim"},
            "mod": {"power_set": 0},
            "duration": "end_of_turn"}]}
DESTROYED = {"kind": "trigger",
             "when": {"event": "move", "from": "bz",
                      "to": "graveyard", "reason": "destroy",
                      "subject": "self"},
             "effect": [
                 {"op": "may",
                  "body": [
                      {"op": "play_free",
                       "select": {"zone": "hand", "owner": "you",
                                  "filter": {"types": ["creature"],
                                             "colorless": True,
                                             "race_has": "ゼニス"},
                                  "count": 1}}]}]}
FORM = [CIP, DESTROYED]
FULL_TEXT = ("水晶ソウル２（このクリーチャーを召喚する時、自分のマナゾーンにある"
             "裏向きのカードのマナの数字は２になる）\n"
             "W・ブレイカー\n"
             "このクリーチャーが出た時、相手のクリーチャーを１体選ぶ。このターン、"
             "そのクリーチャーのパワーを０にする。（パワー０以下のクリーチャーは破壊される）\n"
             "このクリーチャーが破壊された時、無色ゼニス・クリーチャーを１体、"
             "自分の手札からコストを支払わずに召喚してもよい。")


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


def test_round405_disposition():
    rej = _reject_rows()
    assert len(rej) == 1962
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10350
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: abilities は [CIP, 破壊時] の
    # 2件ちょうど（条項順も一致）、civs は [] のまま
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert c["abilities"][0] == CIP and c["abilities"][1] == DESTROYED
    assert c["crystal_soul"] == 2
    assert c["keywords"] == ["double_breaker"]
    assert c["text"] == FULL_TEXT
    assert c["name"] == "騎士のコード オルタナティブ"
    assert c["types"] == ["creature"] and c["civs"] == []
    assert c["cost"] == 7 and c["power"] == 6543
    assert c["races"] == ["アンノウン・セレス"] and c["mana"] == 1
    d = parse_card(c, TABLES)
    assert CIP in d.abilities and DESTROYED in d.abilities
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第370弾本体と同形、対象は登録カード） ----------

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


def _drive(e, plays=(), yes=True, pick=None, stop=None, limit=600):
    plays = list(plays)
    for _ in range(limit):
        if stop is not None and stop():
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "yes_no":
            want = "yes" if yes else "no"
            e.answer([keys.index(want)] if want in keys
                     else list(range(d.get("min", 0))))
        elif kind == "main" and d.get("player") == 0:
            hit = next((k for k in plays if k in keys), None)
            if hit is not None:
                plays.remove(hit)
                e.answer([keys.index(hit)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


def test_registered_cip_sets_chosen_power_zero_and_destroys(rules):
    """登録カード: 召喚し、相手のパワー4000（T1105）を
    選ぶと、そのパワーが0になり状況起因処理で破壊されて
    墓地に行く。登録カード自身は場に残る。"""
    e = _build(rules,
               {"hand": [TARGET], "mana": ["T1112"] * 7},
               {"bz": ["T1105"]})
    _drive(e, plays=[f"play:{TARGET}"], pick="T1105",
           stop=lambda: "T1105" in _defns(e, "graveyard", 1))
    assert TARGET in _defns(e, "bz", 0)
    assert "T1105" not in _defns(e, "bz", 1)
    assert "T1105" in _defns(e, "graveyard", 1)


def test_registered_cip_power_set_overwrites_power_additions(rules):
    """登録カード: 実効パワー6000（印刷3000＋static +3000）の
    T1114 を選んでも、power_set は加算ごと上書きして
    0にするため破壊される。"""
    e = _build(rules, {}, {"bz": ["T1114"]})
    ch = e.chars(_find(e, "bz", 1, "T1114"))
    assert ch["power"] == 6000          # 前提: 加算が効いている
    e = _build(rules,
               {"hand": [TARGET], "mana": ["T1112"] * 7},
               {"bz": ["T1114"]})
    _drive(e, plays=[f"play:{TARGET}"], pick="T1114",
           stop=lambda: "T1114" in _defns(e, "graveyard", 1))
    assert "T1114" not in _defns(e, "bz", 1)
    assert "T1114" in _defns(e, "graveyard", 1)
    assert TARGET in _defns(e, "bz", 0)


def test_registered_cip_no_opponent_creature_no_effect(rules):
    """登録カード: 相手のクリーチャーがいなければ choose の
    候補は無く（自分のクリーチャーは owner: opp で候補に
    入らない）、効果は空振りで解決する。"""
    e = _build(rules,
               {"bz": ["T1107"], "hand": [TARGET],
                "mana": ["T1112"] * 7},
               {})
    _drive(e, plays=[f"play:{TARGET}"],
           stop=lambda: TARGET in _defns(e, "bz", 0)
           and e.s.turn >= 3)
    assert TARGET in _defns(e, "bz", 0)
    assert "T1107" in _defns(e, "bz", 0)
    assert _defns(e, "graveyard", 0) == []
    assert _defns(e, "graveyard", 1) == []


def test_registered_destroyed_trigger_summons_zenith_free(rules):
    """登録カード（partial 既存の破壊時誘発）: バトルで
    破壊された時、may で手札の無色ゼニス（T789）を
    コストを支払わずに召喚できる。登録カードはブロッカー
    ではないので、その攻撃をブロッカーかつ
    win_all_battles 持ちの T1106 にブロックさせて破壊する。"""
    e = _build(rules,
               {"bz": [TARGET], "hand": ["T789"]},
               {"bz": ["T1106"]})
    state = {"attacked": False, "attack_turn": None}
    for _ in range(1500):
        if "T789" in _defns(e, "bz", 0) and state["attacked"]:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "charge":
            e.answer([keys.index("pass")] if "pass" in keys
                     else list(range(d.get("min", 0))))
        elif kind == "attack" and d.get("player") == 0:
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{TARGET}:player"]
            if hit and not state["attacked"]:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            hit = [i for i, k in enumerate(keys)
                   if k.startswith("bz:T1106:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d.get("min", 0))))
        elif any("T789" in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if "T789" in k)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert state["attacked"]
    assert TARGET in _defns(e, "graveyard", 0)   # バトルで破壊された
    assert "T789" in _defns(e, "bz", 0)           # 無料で召喚された
    assert "T1106" in _defns(e, "bz", 1)          # 勝者は残る
