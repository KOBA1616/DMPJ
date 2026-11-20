"""再変換ラウンド350（第315弾 under_dragons_return_on_destroy）の記録テスト。

- 新規登録1件: dmex12-s19 燃える侵略 レッドギラゴン。
- alias 畳み込み0件（identity の canon_id は自id、
  aliases_for は空）。
- stale クリーンアップ0件・差し戻し0件。
- 対象行は gaps が空のため reopen では外れず直接 submit
  （第323・343・347・348・349弾の先例）。
- converted 10,253→10,254 / rejects 2,065→2,064、
  canonical 重なり0・漏れ0。under_dragons_return_on_destroy
  はファミリー単独行だったため完全に解消。

登録形は第315弾の確立形と完全一致（submit の連結・
merge_split 由来の混入なし、abilities は [攻撃の終わり
誘発, 破壊誘発] の2件ちょうど、keywords は double_breaker
のまま）:
- partial（NEO進化、侵略＝面フィールド declare、攻撃の
  終わりに山札の上から1枚目を表向きにして下に重ねる
  誘発は完成済み）に、第294弾 form B（破壊トリガー＋
  play_free {select: {ref: event.was_under, zone:
  graveyard, filter}}、登録済み dmex12-004 と同形）の
  filter を {race_has: ドラゴン, not_types: [evolution]}
  に替えた破壊誘発を追加し、unsupported を除去したもの。

実挙動は登録カード自身で固定する（下カードには第315弾
プロト T967/T968/T969 を使う）。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾
以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

TARGET = "dmex12-s19"
GAP = "under_dragons_return_on_destroy"

TEXT = ("NEO進化：自分のドラゴン１体の上に置いてもよい。\n"
        "侵略：コスト５以上のドラゴン（自分のコスト５以上のドラゴンが攻撃する時、"
        "自分の手札にあるこのクリーチャーをその上に重ねてもよい）\n"
        "W・ブレイカー\n"
        "このクリーチャーの攻撃の終わりに、自分の山札の上から１枚目を表向きにして、"
        "このクリーチャーの下に重ねてもよい。\n"
        "このクリーチャーが破壊された時、その下に重ねてあった進化ではないドラゴンを"
        "すべてバトルゾーンに出す。")

ATTACK_END_TRIGGER = {"kind": "trigger",
                      "when": {"event": "attack_end", "subject": "self"},
                      "effect": [{"op": "may",
                                  "body": [{"op": "put_under",
                                            "select": {"zone": "deck",
                                                       "owner": "you",
                                                       "from_top": 1},
                                            "onto": {"ref": "self"}}]}]}

DESTROY_TRIGGER = {"kind": "trigger",
                   "when": {"event": "move", "from": "bz", "to": "graveyard",
                            "reason": "destroy", "subject": "self"},
                   "effect": [{"op": "play_free",
                               "select": {"ref": "event.was_under",
                                          "zone": "graveyard",
                                          "filter": {"race_has": "ドラゴン",
                                                     "not_types": ["evolution"]}}}]}

FORM = {"id": TARGET,
        "name": "燃える侵略 レッドギラゴン",
        "types": ["creature"],
        "civs": ["light", "darkness", "fire"],
        "cost": 6, "power": 9000,
        "races": ["メガ・コマンド・ドラゴン", "侵略者"],
        "mana": 1,
        "neo": True,
        "evolve_from": {"owner": "you", "races": ["ドラゴン"],
                        "types": ["creature"]},
        "declare": {"subject": {"owner": "you",
                                "filter": {"race_has": "ドラゴン",
                                           "cost_ge": 5,
                                           "types": ["creature"]}}},
        "text": TEXT,
        "abilities": [ATTACK_END_TRIGGER, DESTROY_TRIGGER],
        "keywords": ["double_breaker"]}


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


def test_round350_disposition():
    rej = _reject_rows()
    assert len(rej) == 2064
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10254
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET in ids and TARGET not in rej   # 漏れ0
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert not (c.get("source") or {}).get("aliases")   # alias なし
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "neo", "evolve_from", "declare", "text",
              "abilities", "keywords"):
        assert c.get(k) == FORM[k], k
    assert len(c["abilities"]) == 2      # [攻撃の終わり誘発, 破壊誘発]
    d = parse_card(c, TABLES)
    assert d.neo and d.types == ["creature"]
    assert d.keywords == ["double_breaker"]
    # under_dragons_return_on_destroy は完全に解消（ファミリー単独行）
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


# ---------- 実挙動ドライバ（scenario.build 直包み、第315弾と同型） ----------

CARD = TARGET


def _build(rules, p0, p1):
    return scenario.build(
        rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                "deck_size": 20, "deck_exact": [True, True]})


def _wire(e, host_defn, under_defns, p=0):
    """bz に置いた札同士で進化スタックを組む（top_of / under / stack_bases）。"""
    host = next(c for c in e.zlist("bz", p) if e.s.cards[c].defn == host_defn
                and e.s.cards[c].top_of < 0)
    unders = []
    for ud in under_defns:
        u = next(c for c in e.zlist("bz", p) if e.s.cards[c].defn == ud
                 and e.s.cards[c].top_of < 0 and c != host)
        e.s.cards[u].top_of = host
        unders.append(u)
    e.s.cards[host].under = unders
    e.s.cards[host].stack_bases = list(unders)
    return host, unders


def _drive(e, done, cast=None, cast_player=1, target_defn=None,
           yes=True, attack_with=None, steps=600):
    st = {"cast": False, "attacked": False}
    for _ in range(steps):
        if done(e):
            return st
        d = e.advance()
        assert d is not None, "game ended before done"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "main" and cast and not st["cast"] \
                and d.get("player") == cast_player and f"play:{cast}" in keys:
            e.answer([keys.index(f"play:{cast}")])
            st["cast"] = True
        elif kind == "attack" and attack_with and not st["attacked"]:
            cand = [k for k in keys if k.startswith(f"attack:{attack_with}:")
                    and k.endswith(":player")]
            if cand:
                e.answer([keys.index(cand[0])])
                st["attacked"] = True
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
        elif kind == "yes_no":
            want = "yes" if yes else "no"
            e.answer([keys.index(want)] if want in keys else list(range(d["min"])))
        elif kind == "choose_cards":
            idx = None
            if target_defn:
                for o in d["options"]:
                    if e.s.cards[o["cid"]].defn == target_defn:
                        idx = keys.index(o["key"])
                        break
            e.answer([idx] if idx is not None else list(range(d["min"])))
        elif kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert done(e), "drive budget exhausted"


def _settle(e, steps=12):
    for _ in range(steps):
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


P1_DESTROY = {"hand": ["T056"], "mana": ["T008"] * 3,
              "deck": ["T002"] * 6}
P0_DECK = {"deck": ["T002"] * 6}


# ---------- 実挙動（登録形） ----------

def test_registered_destroy_returns_only_non_evolution_dragons(rules):
    """dmex12-s19: 破壊された時、下にあった進化ではない
    ドラゴンだけがすべて出る。"""
    e = _build(rules,
               {"bz": [CARD, "T967", "T968", "T969"],
                "graveyard": ["T967"], **P0_DECK},
               dict(P1_DESTROY))
    host, unders = _wire(e, CARD, ["T967", "T968", "T969"])
    under_dragon, under_evo, under_beast = unders
    grave_dragon = next(c for c in e.zlist("graveyard", 0)
                        if e.s.cards[c].defn == "T967")
    # 下カードは束の一部として bz に居るため zone では判定
    # できない。done は本体の墓地行きで見る
    _drive(e, lambda e: e.s.cards[host].zone == "graveyard",
           cast="T056", target_defn=CARD)
    _settle(e)
    assert e.s.cards[host].zone == "graveyard"
    # 下にあった非進化ドラゴンは独立したクリーチャーとして出る
    assert e.s.cards[under_dragon].zone == "bz"
    assert e.s.cards[under_dragon].top_of < 0
    # 下にあった進化ドラゴン・非ドラゴンは墓地に残る
    assert e.s.cards[under_evo].zone == "graveyard"
    assert e.s.cards[under_beast].zone == "graveyard"
    # 下に無かった同種ドラゴン（最初から墓地）は出ない
    assert e.s.cards[grave_dragon].zone == "graveyard"


def test_registered_attack_end_tuck_then_destroy_returns_dragons(rules):
    """実カードの条項連鎖: NEO進化元（ドラゴン）の上に乗り、
    攻撃の終わりに山札の上（ドラゴン）を下に重ね、破壊
    されると下のドラゴンが両方出る。"""
    e = _build(rules,
               {"bz": [CARD, "T967"],
                "deck": ["T002", "T002", "T002", "T002", "T967", "T967"]},
               dict(P1_DESTROY))
    # 山札 spec は末尾が上（リスト index 0 が上）: トップ2枚が
    # T967（ドロー＋タック分）、下の T002 は破壊解決後にターンが
    # 進んでも deck_out しないための余り
    assert e.s.cards[e.s.zones["deck"][0][0]].defn == "T967"
    host, unders = _wire(e, CARD, ["T967"])
    base = unders[0]
    # 攻撃 → 攻撃の終わりに山札の上を下に重ねる（yes）
    _drive(e, lambda e: len(e.s.cards[host].under) == 2,
           attack_with=CARD)
    tucked = next(c for c in e.s.cards[host].under if c != base)
    assert e.s.cards[tucked].defn == "T967"
    # 相手が破壊 → 下にあった非進化ドラゴン2枚とも出る
    _drive(e, lambda e: e.s.cards[host].zone == "graveyard",
           cast="T056", target_defn=CARD)
    _settle(e)
    assert e.s.cards[host].zone == "graveyard"
    assert e.s.cards[base].zone == "bz" and e.s.cards[base].top_of < 0
    assert e.s.cards[tucked].zone == "bz" and e.s.cards[tucked].top_of < 0


def test_registered_no_under_dragon_nothing_comes_out(rules):
    """対照: 下が非ドラゴンだけなら、破壊されても何も出ない。"""
    e = _build(rules,
               {"bz": [CARD, "T969"], **P0_DECK},
               dict(P1_DESTROY))
    host, unders = _wire(e, CARD, ["T969"])
    beast = unders[0]
    _drive(e, lambda e: e.s.cards[host].zone == "graveyard",
           cast="T056", target_defn=CARD)
    _settle(e)
    assert e.s.cards[beast].zone == "graveyard"
    assert [e.s.cards[c].defn for c in e.zlist("bz", 0)
            if e.s.cards[c].controller == 0] == []
