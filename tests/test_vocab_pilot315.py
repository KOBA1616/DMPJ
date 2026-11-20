"""語彙パイロット第315弾: under_dragons_return_on_destroy
（「破壊された時、その下に重ねてあった進化ではないドラゴンをすべて出す」）。

対象は dmex12-s19 燃える侵略 レッドギラゴン の純粋1件。gaps は空で、
partial の source.unsupported にだけギャップ名が残る監査行
（第312〜314弾の監査の継続）。partial の他節（NEO進化・侵略 declare・
W・ブレイカー・攻撃の終わりの下置き）は完成済みで、不足は最終節1つだけ。

結論はドリフト（追加語彙なし）: 第294弾 form B（破壊トリガー＋
play_free {select: {ref: event.was_under, zone: graveyard,
filter: {race_has: ...}}}、登録済み dmex12-004 と同形）の filter に
not_types: [evolution] を足すだけ。not_types は既存フィルタキー
（第294弾 T883 の put_under filter でも使用）。「進化ではないドラゴン」
= race_has: ドラゴン（種族文字列への部分一致）かつ types に
evolution を含まない、で正確に一致する。

プロト:
- T966: dmex12-s19 型（NEO進化＋攻撃の終わりの下置き＋本弾の破壊誘発）
- T967: 非進化ドラゴン（下にあれば出る）
- T968: 進化ドラゴン（下にあっても出ない）
- T969: 非ドラゴン（下にあっても出ない）
"""
import copy
from pathlib import Path

import yaml

from dmsim.cards.defs import load_tables, parse_card
from tests.conftest import setup

TABLES = load_tables()
PROTO = yaml.safe_load(open(Path(__file__).parent.parent / "data" / "cards"
                            / "proto.yaml", encoding="utf-8"))["cards"]

FORM_TRIGGER = {"kind": "trigger",
                "when": {"event": "move", "from": "bz", "to": "graveyard",
                         "reason": "destroy", "subject": "self"},
                "effect": [{"op": "play_free",
                            "select": {"ref": "event.was_under",
                                       "zone": "graveyard",
                                       "filter": {"race_has": "ドラゴン",
                                                  "not_types": ["evolution"]}}}]}


def _proto(tid):
    return copy.deepcopy(next(p for p in PROTO if p["id"] == tid))


# ---------- parse / 形の一致 ----------

def test_proto_parse_and_form():
    for tid in ("T966", "T967", "T968", "T969"):
        parse_card(_proto(tid), TABLES)
    d = parse_card(_proto("T966"), TABLES)
    trigs = [a for a in d.abilities
             if a.get("kind") == "trigger"
             and a.get("when", {}).get("event") == "move"]
    assert trigs == [FORM_TRIGGER], trigs
    # partial と同じ攻撃の終わりの下置きも併せ持つ
    ae = [a for a in d.abilities
          if a.get("when", {}).get("event") == "attack_end"]
    assert len(ae) == 1 and ae[0]["effect"][0]["op"] == "may"


# ---------- 実挙動ドライバ（第294弾と同型） ----------

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
           yes=True, attack_with=None, steps=400):
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


P1_DESTROY = {"hand": ["T056"], "mana": ["T008"] * 3}


# ---------- 本筋: 破壊 → 下の非進化ドラゴンだけが出る ----------

def test_destroy_returns_only_non_evolution_dragons_from_under(rules):
    e = setup(rules, {"bz": ["T966", "T967", "T968", "T969"],
                      "graveyard": ["T967"]},
              dict(P1_DESTROY), filler="T002")
    host, unders = _wire(e, "T966", ["T967", "T968", "T969"])
    under_dragon, under_evo, under_beast = unders
    grave_dragon = next(c for c in e.zlist("graveyard", 0)
                        if e.s.cards[c].defn == "T967")
    # 注意: 下カードは束の一部として bz ゾーンに居るため zone では
    # 判定できない。done は本体の墓地行きで見る
    _drive(e, lambda e: e.s.cards[host].zone == "graveyard",
           cast="T056", target_defn="T966")
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


def test_attack_end_tuck_then_destroy_returns_tucked_dragon(rules):
    """実カードの条項連鎖: NEO進化元（ドラゴン）の上に乗り、攻撃の終わりに
    山札の上（ドラゴン）を下に重ね、破壊されると下のドラゴンが両方出る。"""
    e = setup(rules, {"bz": ["T966", "T967"], "deck": ["T967"]},
              dict(P1_DESTROY), filler="T002")
    host, unders = _wire(e, "T966", ["T967"])
    base = unders[0]
    top = e.s.zones["deck"][0][0]
    assert e.s.cards[top].defn == "T967"
    # 攻撃 → 攻撃の終わりに山札の上を下に重ねる（yes）
    _drive(e, lambda e: e.s.cards[top].top_of == host, attack_with="T966")
    assert e.s.cards[host].under == [base, top]
    # 相手が破壊 → 下にあった非進化ドラゴン2枚とも出る
    _drive(e, lambda e: e.s.cards[host].zone == "graveyard",
           cast="T056", target_defn="T966")
    _settle(e)
    assert e.s.cards[host].zone == "graveyard"
    assert e.s.cards[base].zone == "bz" and e.s.cards[base].top_of < 0
    assert e.s.cards[top].zone == "bz" and e.s.cards[top].top_of < 0


def test_no_under_dragon_nothing_comes_out(rules):
    """対照: 下が非ドラゴンだけなら、破壊されても何も出ない。"""
    e = setup(rules, {"bz": ["T966", "T969"]}, dict(P1_DESTROY), filler="T002")
    host, unders = _wire(e, "T966", ["T969"])
    beast = unders[0]
    _drive(e, lambda e: e.s.cards[host].zone == "graveyard",
           cast="T056", target_defn="T966")
    _settle(e)
    assert e.s.cards[beast].zone == "graveyard"
    assert [e.s.cards[c].defn for c in e.zlist("bz", 0)] == []
