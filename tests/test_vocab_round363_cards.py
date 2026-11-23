"""再変換ラウンド363（第328弾 滅亡の光）の記録テスト。

- 新規登録1件: dmex15-b019 滅亡の光。
- alias 畳み込み0件・stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [filter_not_race, first_attack_end] のため
  reopen filter_not_race first_attack_end で外してから submit
  （reopen は1件だけ外れた。両 gap を指定しないと multi-gap 行は
  外れない）。
- converted 10,276→10,277 / rejects 2,039→2,038、
  canonical 重なり0・漏れ0。filter_not_race / first_attack_end は
  残り0件で両ファミリー解消。

登録形は第328弾の確立形と完全一致（submit の連結・merge_split 由来の
混入なし）: アタック・チャンス（declare＋play_free）＋destroy
{not_race_has}＋modify による once_per_turn 付き付与型誘発。

実挙動は登録カード自身で固定する。ドライバは scenario.build の薄い包みで、
tests.conftest は import しない（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

TARGET = "dmex15-b019"

DECLARE = {"kind": "declare", "zone": "hand",
           "when": {"event": "attack",
                    "subject": {"owner": "you",
                                "filter": {"race_has": "クリエイター"}}},
           "effect": [{"op": "play_free", "select": {"ref": "self"}}]}

TRIGGER = {"kind": "trigger",
           "when": {"event": "attack_end", "subject": "self"},
           "effect": [{"op": "untap", "select": {"ref": "self"}}],
           "once_per_turn": True}

FORM = [
    {"op": "destroy",
     "select": {"zone": "bz", "owner": "any",
                "filter": {"types": ["creature"],
                           "not_race_has": ["ゴッド", "フェニックス",
                                            "クリエイター"]},
                "count": "all"}},
    {"op": "modify",
     "select": {"zone": "bz", "owner": "any",
                "filter": {"any_of": [{"race_has": "ゴッド"},
                                      {"race_has": "フェニックス"},
                                      {"race_has": "クリエイター"}]},
                "count": "all"},
     "mod": {"gain": [TRIGGER]},
     "duration": "end_of_turn"},
]


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


def test_round363_disposition():
    rej = _reject_rows()
    assert len(rej) == 2038
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10277
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET in ids and TARGET not in rej
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["abilities"] == [DECLARE]
    assert c["spell"] == FORM
    assert not (c.get("source") or {}).get("unsupported")
    assert not (c.get("source") or {}).get("aliases")
    d = parse_card(c, TABLES)
    assert len(d.spell) == 2
    left = {rid for rid, r in rej.items()
            if "filter_not_race" in (r.get("gaps") or [])
            or "first_attack_end" in (r.get("gaps") or [])}
    assert left == set(), left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _cast_spell(e, cid, mana_n):
    """main で指定の呪文を唱える（コストは火5＋闇4のマナで払う。
    多色呪文には両文明のマナが要る）。唱えた時点で戻る。"""
    cast = False
    for _ in range(120):
        d = e.advance()
        assert d is not None, "game ended before cast"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and f"play:{cid}" in keys:
            e.answer([keys.index(f"play:{cid}")])
            cast = True
            continue
        if cast and d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if cast and d["kind"] in ("charge", "main", "attack"):
            return
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("spell did not resolve")


def _attack_player(e, attacker_defn, player=0):
    for _ in range(120):
        d = e.advance()
        assert d is not None, "game ended before attack"
        if d["kind"] == "attack" and d.get("player") == player:
            keys = _keys(d)
            e.answer([keys.index(f"attack:{attacker_defn}:player")])
            return
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys
                 else list(range(d["min"])))
    raise AssertionError("attack decision did not appear")


def _drive_combat(e, max_steps=200):
    for _ in range(max_steps):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            return
        keys = _keys(d)
        if d["kind"] == "block":
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("combat did not settle")


def test_registered_destroy_only_non_god_phoenix_creator(rules):
    """登録形: ゴッド／フェニックス／クリエイター以外は両プレイヤー
    とも破壊される。ゴッドは両プレイヤーとも残る。残ったゴッドは
    付与された誘発（once_per_turn）を持つ。"""
    e = _build(rules, {"bz": ["T053", "T001"],
                       "hand": ["dmex15-b019"],
                       "mana": ["T005"] * 5 + ["T056"] * 4},
               {"bz": ["T004", "T055"]})
    _cast_spell(e, "dmex15-b019", 9)
    assert e.s.cards[_bz(e, 0, "T053")].zone == "bz"
    assert e.s.cards[_bz(e, 1, "T055")].zone == "bz"
    gy0 = [c for c in e.zlist("graveyard", 0)]
    gy1 = [c for c in e.zlist("graveyard", 1)]
    assert any(e.s.cards[c].defn == "T001" for c in gy0)
    assert any(e.s.cards[c].defn == "T004" for c in gy1)
    for p, dfn in ((0, "T053"), (1, "T055")):
        trigs = [ab for _, ab in e.abilities(_bz(e, p, dfn), "trigger")]
        assert any(ab.get("once_per_turn") for ab in trigs), (p, trigs)


def test_registered_each_god_untaps_after_first_attack_end(rules):
    """登録形: ゴッドは最初の攻撃の終わりにアンタップされる。
    2回目の攻撃の終わりにはもうアンタップされない
    （once_per_turn）。"""
    e = _build(rules, {"bz": ["T053"], "hand": ["dmex15-b019"],
                       "mana": ["T005"] * 5 + ["T056"] * 4}, {})
    e.s.cards[_bz(e, 0, "T053")].entered_turn = -1
    _cast_spell(e, "dmex15-b019", 9)
    t053 = _bz(e, 0, "T053")
    assert e.s.cards[t053].tapped is False
    _attack_player(e, "T053")
    _drive_combat(e)
    assert e.s.cards[t053].tapped is False
    _attack_player(e, "T053")
    _drive_combat(e)
    assert e.s.cards[t053].tapped is True
