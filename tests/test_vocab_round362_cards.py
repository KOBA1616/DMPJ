"""再変換ラウンド362（第327弾 first_attack_end）の記録テスト。

- 新規登録1件: dm26ex4-cho025 瞬閃と疾駆と双撃の決断。
- alias 畳み込み1件（dm26sd1-i004。submit 時に aliases 10件を
  自動記録。うち rejects 行の畳み込みは dm26sd1-i004 の1件）。
- stale クリーンアップ0件・差し戻し0件。
- 対象2行は gaps = [first_attack_end] のため reopen で外してから
  submit（reopen は2件とも外れた。multi-gap の dmex15-b019 は
  reopen の対象外で rejects に残る）。
- converted 10,275→10,276 / rejects 2,041→2,039、
  canonical 重なり0・漏れ0。純粋 first_attack_end は残り0件で
  ファミリー解消（multi-gap の dmex15-b019 は第328弾の候補）。

登録形は第327弾の確立形と完全一致（submit の連結・merge_split 由来の
混入なし）: modal（count: 2, repeat: true）。モード3は once 既定の
遅延誘発 {event: attack_end, subject: {ref: chosen}} → untap。

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

GAP = "first_attack_end"

FORM = [
    {"op": "modal", "count": 2, "repeat": True,
     "modes": [
         [{"op": "play_free",
           "select": {"zone": "hand", "owner": "you",
                      "filter": {"types": ["creature"], "cost_le": 3},
                      "count": 1}}],
         [{"op": "choose",
           "select": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["creature"]}, "count": 1},
           "as": "c"},
          {"op": "modify", "select": {"ref": "c", "count": "all"},
           "mod": {"grant": ["speed_attacker"]},
           "duration": "end_of_turn"}],
         [{"op": "choose",
           "select": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["creature"]}, "count": 1},
           "as": "chosen"},
          {"op": "delayed_trigger",
           "when": {"event": "attack_end", "subject": {"ref": "chosen"}},
           "effect": [{"op": "untap", "select": {"ref": "chosen"}}],
           "duration": "end_of_turn"}],
     ]},
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


def test_round362_disposition():
    rej = _reject_rows()
    assert len(rej) == 2039
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10276
    assert not (ids & set(rej))          # canonical 重なり0
    for tid in ("dm26ex4-cho025", "dm26sd1-i004"):
        assert tid not in rej, tid
    assert "dm26ex4-cho025" in ids
    # dm26sd1-i004 は正本の aliases に記録されるだけで、カードとしては
    # 登録されない（canon_id は dm26ex4-cho025）
    c = _conv_cache.find(CONVERTED, "dm26ex4-cho025")
    assert c is not None
    assert c["name"] == "瞬閃と疾駆と双撃の決断"
    assert c["spell"] == FORM
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == [
        "dm22bd2-014", "dm23rp2-tr08", "dm23rp2x-tr08", "dm23rp4-sp2",
        "dm23rp4x-sp2", "dm23sd3-002", "dm26sd1-i004", "dmart04-003",
        "dmex19-012", "dmrp11-007"]
    d = parse_card(c, TABLES)
    assert len(d.spell) == 1 and d.spell[0]["op"] == "modal"
    left = {rid for rid, r in rej.items()
            if (r.get("gaps") or []) == [GAP]}
    assert left == set(), left
    assert rej["dmex15-b019"].get("gaps") == ["filter_not_race",
                                              "first_attack_end"]


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _cast_spell(e, modes, picks):
    """main で dm26ex4-cho025 を唱え、modal のモードを modes の順に
    選ぶ。picks は choose 系の決定に対する答えの列（defn の列）。
    唱えた時点で戻る。火の呪文なのでマナは火の T005 を使う。"""
    cast = False
    pick_i = 0
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended before cast"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and "play:dm26ex4-cho025" in keys:
            e.answer([keys.index("play:dm26ex4-cho025")])
            cast = True
            continue
        if cast and d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if cast and d["kind"] == "choose_mode":
            e.answer([keys.index(f"mode:{modes.pop(0)}")])
            continue
        if cast and d["kind"] == "choose_cards":
            want = picks[pick_i]
            pick_i += 1
            idx = next(i for i, k in enumerate(keys)
                       if k.split(":")[1] == want)
            e.answer([idx])
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


def test_registered_mode3_first_attack_end_untaps_only_once(rules):
    """登録形: モード3で選んだクリーチャーは最初の攻撃の終わりに
    アンタップされる。2回目の攻撃の終わりにはもうアンタップ
    されない。"""
    e = _build(rules, {"bz": ["T001"], "hand": ["dm26ex4-cho025", "T002"],
                       "mana": ["T005"] * 3}, {})
    e.s.cards[_bz(e, 0, "T001")].entered_turn = -1
    _cast_spell(e, [2, 0], ["T001", "T002"])
    t001 = _bz(e, 0, "T001")
    assert e.s.cards[t001].tapped is False
    _attack_player(e, "T001")
    _drive_combat(e)
    assert e.s.cards[t001].tapped is False
    _attack_player(e, "T001")
    _drive_combat(e)
    assert e.s.cards[t001].tapped is True


def test_registered_mode2_grants_speed_attacker(rules):
    """登録形: モード2で選んだクリーチャー（召喚酔い中）に
    スピードアタッカーを与え、同じターンに攻撃できる。"""
    e = _build(rules, {"bz": ["T002"], "hand": ["dm26ex4-cho025"],
                       "mana": ["T005"] * 3}, {})
    _cast_spell(e, [1, 1], ["T002", "T002"])
    before = len(e.zlist("shield", 1))
    _attack_player(e, "T002")
    _drive_combat(e)
    assert len(e.zlist("shield", 1)) == before - 1
