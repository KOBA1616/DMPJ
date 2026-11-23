"""再変換ラウンド357（第322弾 trigger_when_unblocked_and_extra_breaks_per_dynamo_tap）の記録テスト。

- 新規登録2件: dm19-003 電脳鉄人センジュオー /
  dm23ex2-045（ツインパクト: 電脳鉄人センジュオー / センジュ・チューン）。
- alias 畳み込み0件（両 id とも提出前に real / proto / converted の
  いずれにも無く、aliases 記録も無し）。stale クリーンアップ0件・
  差し戻し0件。
- 対象2行は gaps = [trigger_when_unblocked_and_extra_breaks_per_dynamo_tap]
  のため reopen で外してから submit（reopen は dm19-003 の1件だけが
  外れた。dm23ex2-045 の rejects 行には reason が無く reopen の条件に
  合わなかったためで、submit で rejects から外れた）。
- converted 10,266→10,268 / rejects 2,051→2,049、
  canonical 重なり0・漏れ0。trigger_when_unblocked_and_extra_breaks_per_dynamo_tap は
  ファミリーがこの2件だけだったため完全に解消。

登録形は第322弾の確立形と完全一致（submit の連結・merge_split 由来の
混入なし）:
- クリーチャー面（両カード共通）: trigger {event: attack_end,
  subject: self, target: player, blocked: false} → [{op: break,
  player: opp, count: {turn_count: {kind: dynamo_tap, owner: you}}}]
- dm23ex2-045 の呪文面: [set_var hand_n {count: {zone: hand,
  owner: you}}, draw {var: hand_n}, discard {var: hand_n}]
keywords はクリーチャー面が [dynamo, unblockable]、呪文面が [s_trigger]。

実挙動は登録カード自身で固定する。ドライバは scenario.build の薄い包みで、
tests.conftest は import しない（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

GAP = "trigger_when_unblocked_and_extra_breaks_per_dynamo_tap"

SENJUOH_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "break", "player": "opp",
                "count": {"turn_count": {"kind": "dynamo_tap",
                                         "owner": "you"}}}]}

# 提出形（converted.yaml に保存される形。discard はマクロで、parse 時に
# move（to: graveyard, reason: discard）へ展開される）
TUNE_SPELL_RAW = [
    {"op": "set_var", "name": "hand_n",
     "value": {"count": {"zone": "hand", "owner": "you"}}},
    {"op": "draw", "count": {"var": "hand_n"}},
    {"op": "discard", "select": {"zone": "hand", "owner": "you",
                                 "count": {"var": "hand_n"}}},
]

TUNE_SPELL = [
    {"op": "set_var", "name": "hand_n",
     "value": {"count": {"zone": "hand", "owner": "you"}}},
    {"op": "draw", "count": {"var": "hand_n"}},
    {"op": "move", "select": {"zone": "hand", "owner": "you",
                              "count": {"var": "hand_n"}},
     "to": "graveyard", "reason": "discard"},
]


def _reject_rows():
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


def test_round357_disposition():
    rej = _reject_rows()
    assert len(rej) == 2049
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10268
    assert not (ids & set(rej))          # canonical 重なり0
    for tid in ("dm19-003", "dm23ex2-045"):
        assert tid in ids and tid not in rej, tid
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None
        assert not (c.get("source") or {}).get("unsupported")
        assert not (c.get("source") or {}).get("aliases"), tid
    c003 = _conv_cache.find(CONVERTED, "dm19-003")
    assert c003["keywords"] == ["dynamo", "unblockable"]
    assert c003["abilities"] == [SENJUOH_TRIGGER]
    d003 = parse_card(c003, TABLES)
    assert SENJUOH_TRIGGER in d003.abilities
    c045 = _conv_cache.find(CONVERTED, "dm23ex2-045")
    assert len(c045["faces"]) == 2
    f0, f1 = c045["faces"]
    assert f0["abilities"] == [SENJUOH_TRIGGER]
    assert f0["keywords"] == ["dynamo", "unblockable"]
    assert f1["spell"] == TUNE_SPELL_RAW
    assert f1["keywords"] == ["s_trigger"]
    d45 = parse_card(c045, TABLES)
    assert SENJUOH_TRIGGER in d45.faces[0].abilities
    assert d45.faces[1].spell == TUNE_SPELL
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
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


def _drive_attack(e, attacker, activates=(), limit=600):
    """attacker がプレイヤーを攻撃する。activates のダイナモは攻撃決定で
    先に起動する。S・トリガーの宣言はすべて断る。攻撃が終わり次のステップに
    来たら止め、その時点の dynamo_tap 体数（turn/prev 両方）を返す。"""
    max_taps = 0
    attacked = False
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return max_taps
        for store in (e.s.turn_counters, e.s.prev_counters):
            lst = store.get("dynamo_tap:0")
            if isinstance(lst, list):
                max_taps = max(max_taps, len(lst))
        kind = d["kind"]
        keys = _keys(d)
        if attacked and kind in ("charge", "main", "attack"):
            return max_taps
        if kind in ("charge", "main", "attack"):
            if kind == "attack" and not attacked:
                todo = [a for a in activates
                        if not e.s.cards[_bz(e, 0, a)].tapped]
                if todo:
                    hit = [i for i, x in enumerate(keys)
                           if x.startswith(f"activate:{todo[0]}:")]
                    assert hit, keys
                    e.answer([hit[0]])
                    continue
                hit = [i for i, x in enumerate(keys)
                       if x == f"attack:{attacker}:player"]
                if hit and d["player"] == 0:
                    attacked = True
                    e.answer([hit[0]])
                    continue
            if "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind in ("block", "declare_block"):
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "yes_no":
            e.answer([keys.index("no")])
        elif kind == "choose_cards":
            e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("attack drive did not settle")


def test_registered_003_no_dynamo_use_breaks_one(rules):
    """登録形: dm19-003 がダイナモを使っていなければ余分は0枚。"""
    e = _build(rules, {"bz": ["dm19-003"]}, {})
    e.s.cards[_bz(e, 0, "dm19-003")].entered_turn = -1
    before = len(e.zlist("shield", 1))
    assert _drive_attack(e, "dm19-003") == 0
    assert len(e.zlist("shield", 1)) == before - 1


def test_registered_003_one_dynamo_use_breaks_two(rules):
    """登録形: dm19-050 がダイナモを使うと、dm19-003 は余分に1枚割る。"""
    e = _build(rules, {"bz": ["dm19-003", "dm19-050"]}, {})
    e.s.cards[_bz(e, 0, "dm19-003")].entered_turn = -1
    before = len(e.zlist("shield", 1))
    assert _drive_attack(e, "dm19-003", activates=["dm19-050"]) == 1
    assert len(e.zlist("shield", 1)) == before - 2


def test_registered_045_creature_face_breaks_two(rules):
    """登録形（ツインパクトのクリーチャー面）: dm19-050 がダイナモを使うと、
    dm23ex2-045 のクリーチャー面も余分に1枚割る。"""
    e = _build(rules, {"bz": ["dm23ex2-045", "dm19-050"]}, {})
    e.s.cards[_bz(e, 0, "dm23ex2-045")].entered_turn = -1
    before = len(e.zlist("shield", 1))
    assert _drive_attack(e, "dm23ex2-045", activates=["dm19-050"]) == 1
    assert len(e.zlist("shield", 1)) == before - 2


def test_registered_045_spell_face_draws_and_discards(rules):
    """登録形（ツインパクトの呪文面）: センジュ・チューンを唱えると、
    手札の数だけ引いて同じ数捨てる。唱えた時点で手札は T001/T002 の2枚。"""
    e = _build(rules, {"hand": ["dm23ex2-045", "T001", "T002"],
                       "mana": ["T030", "T030", "T030", "T030"]},
               {})
    deck0 = len(e.zlist("deck", 0))
    cast = False
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and not cast and "play:dm23ex2-045:1" in keys:
            # ツインパクトの呪文面は face 1（:1 付き）で唱える
            e.answer([keys.index("play:dm23ex2-045:1")])
            cast = True
            continue
        if "dm23ex2-045" in [e.s.cards[c].defn
                             for c in e.zlist("graveyard", 0)]:
            break
        if d["kind"] == "choose_cards":
            e.answer(list(range(d.get("min", 0))))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert cast
    assert len(e.zlist("hand", 0)) == 2
    assert len(e.zlist("deck", 0)) == deck0 - 2
    assert len(e.zlist("graveyard", 0)) == 3
