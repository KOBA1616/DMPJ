"""語彙パイロット第294弾: was_under_cards_return（「下にあったカード」）。

rejects の was_under_cards_return 純粋4件（dm25rp2-033 / dmex12-004 /
dmex12-037 / dm24bd5-012）。共通の不足は1点: クリーチャーが下のカードを
連れてバトルゾーン（またはシールドの束）を離れた後、その「下にあった
カード」を効果から指す語彙が無い。離脱時点で束は解体され、生成も進む
ため under_of: self は解決時に必ず空になる（ラウンド328で dm24bd5-012
がこの理由で差し戻された）。

本弾の追加は2点だけ:
- move レコードに **was_under**（一緒に離れた下のカードすべての参照列）
  を載せる。収集レコード（events._apply_one）は移動後の参照、照合用
  レコード（events._record_for）は移動直前の参照で、両ビルダに載せる
  （card_only / スター進化の再構築で下が場に残る場合は載せない）。
- セレクタの ref 参照に **event.was_under** を追加（selectors の ref 経路。
  既存の event.under＝leave_under_untap の単体形と対）。filter と zone の
  併記が効くので「墓地から」「種族で絞る」がそのまま書ける。Rust の
  _simple_selector は event. 参照を一律に対象外にしているため、この形を
  使う対局は自動で Python にフォールバックする（第283弾と同じ）。

形は4つ:
- 形A（dm25rp2-033）: 破壊された時、下にあったカードをすべて墓地から
  手札に戻す。{trigger when: 破壊, effect: [move {select: {ref:
  event.was_under, zone: graveyard}, to: hand, reason: return}]}
- 形B（dmex12-004）: 破壊された時、下にあったファンキー・ナイトメアを
  すべて墓地から出す。play_free＋filter {race_has: ...}。
- 形C（dmex12-037）: 破壊された時、下にあったカードのうち1枚を墓地から
  出してもよい。may＋play_free {count: 1}。
- 形D（dm24bd5-012）: 離れた時、下にあったカードをすべて手札に加える。
  行き先を問わない when {event: move, from: bz, subject: self}。一緒に
  手札へ離れた分は select の zone から hand を外して二重移動しない。
"""
import copy
from pathlib import Path

import yaml

from dmsim.cards.defs import load_rules, load_tables, parse_card
from tests.conftest import setup

TABLES = load_tables()
PROTO = yaml.safe_load(open(Path(__file__).parent.parent / "data" / "cards"
                            / "proto.yaml", encoding="utf-8"))["cards"]

EXPECTED = {
    "T882": {"kind": "trigger",
             "when": {"event": "move", "from": "bz", "to": "graveyard",
                      "reason": "destroy", "subject": "self"},
             "effect": [{"op": "move",
                         "select": {"ref": "event.was_under", "zone": "graveyard"},
                         "to": "hand", "reason": "return"}]},
    "T883": {"kind": "trigger",
             "when": {"event": "move", "from": "bz", "to": "graveyard",
                      "reason": "destroy", "subject": "self"},
             "effect": [{"op": "play_free",
                         "select": {"ref": "event.was_under", "zone": "graveyard",
                                    "filter": {"race_has": "ファンキー・ナイトメア"}}}]},
    "T884": {"kind": "trigger",
             "when": {"event": "move", "from": "bz", "to": "graveyard",
                      "reason": "destroy", "subject": "self"},
             "effect": [{"op": "may",
                         "body": [{"op": "play_free",
                                   "select": {"ref": "event.was_under",
                                              "zone": "graveyard", "count": 1}}]}]},
    "T885": {"kind": "trigger",
             "when": {"event": "move", "from": "bz", "subject": "self"},
             "effect": [{"op": "move",
                         "select": {"ref": "event.was_under",
                                    "zone": ["graveyard", "mana", "deck", "shield"]},
                         "to": "hand", "reason": "return"}]},
}


def _proto(tid):
    return copy.deepcopy(next(p for p in PROTO if p["id"] == tid))


# ---------- parse / 形の一致 ----------

def test_proto_parse_and_forms():
    for tid in ("T882", "T883", "T884", "T885", "T886", "T887", "T888", "T889"):
        parse_card(_proto(tid), TABLES)
    for tid, want in EXPECTED.items():
        d = parse_card(_proto(tid), TABLES)
        trigs = [a for a in d.abilities
                 if a.get("kind") == "trigger" and a.get("when", {}).get("event") == "move"]
        assert want in trigs, (tid, trigs)


def test_was_under_selector_without_event_is_empty(rules):
    """event が無い文脈（常在型のフィルタ等）では空を返し、例外にしない。"""
    e = setup(rules, {"bz": ["T001"]}, {"bz": ["T001"]})
    env = {"you": 0, "self": None, "vars": {}, "event": None}
    assert e.candidates({"ref": "event.was_under"}, env) == []
    env2 = {"you": 0, "self": None, "vars": {}, "event": {"ev": "move"}}
    assert e.candidates({"ref": "event.was_under"}, env2) == []


# ---------- レコードの単体検証 ----------

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


def test_record_for_carries_was_under(rules):
    """_record_for（置換照合用）: 一緒に離れる束だけ移動直前の姿で載る。"""
    e = setup(rules, {"bz": ["T882", "T001"]}, {"bz": ["T001"]})
    host, unders = _wire(e, "T882", ["T001"])
    ref = e.s.ref(host)
    rec = e._record_for({"ev": "move", "subject": ref, "to": "graveyard",
                         "reason": "destroy"})
    assert rec["was_under"] == [e.s.ref(unders[0])]
    # カードとして離れる（下は再構築で場に残る）場合は載せない
    rec2 = e._record_for({"ev": "move", "subject": ref, "to": "graveyard",
                          "reason": "destroy", "card_only": True})
    assert "was_under" not in rec2
    # バトルゾーンへの移動（束は解体されない）も載せない
    rec3 = e._record_for({"ev": "move", "subject": ref, "to": "bz",
                          "reason": "put"})
    assert "was_under" not in rec3


# ---------- 実挙動ドライバ ----------

def _defns(e, zone, p=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _drive(e, done, cast=None, cast_player=1, target_defn=None, pick_defn=None,
           yes=True, attack_with=None, steps=400):
    """done(e) が真になるまで汎用に答える。cast は cast_player の main で
    1回だけ唱え、choose_cards では target_defn（呪文の対象）または
    pick_defn（効果の選択）を優先する。"""
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
            # 効果の選択（pick_defn）が候補にあればそれを、無ければ呪文の
            # 対象（target_defn）を選ぶ。対象が単独候補の時は選択自体が
            # 自動で済み、最初の choose_cards が効果の選択になるため、
            # 順番ではなく候補の有無で判別する
            idx = None
            for want in (pick_defn, target_defn):
                if not want:
                    continue
                for o in d["options"]:
                    if e.s.cards[o["cid"]].defn == want:
                        idx = keys.index(o["key"])
                        break
                if idx is not None:
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


# ---------- 形A: 破壊 → 下にあったカードをすべて手札へ ----------

def test_form_a_destroy_returns_was_under_to_hand(rules):
    e = setup(rules, {"bz": ["T882", "T001"], "graveyard": ["T003"]},
              dict(P1_DESTROY), filler="T002")
    host, unders = _wire(e, "T882", ["T001"])
    base = unders[0]
    # T882 のターン終了の下置きは辞退する（yes=False）
    _drive(e, lambda e: e.s.cards[base].zone == "hand",
           cast="T056", target_defn="T882", yes=False)
    _settle(e)
    assert e.s.cards[host].zone == "graveyard"
    assert e.s.cards[base].zone == "hand"
    # 墓地にあっただけのカード（下に無かった T003）は戻らない
    assert _defns(e, "graveyard") == ["T882", "T003"] or \
        sorted(_defns(e, "graveyard")) == ["T003", "T882"]
    assert "T003" not in _defns(e, "hand")


def test_form_a_put_under_then_destroy_returns_both(rules):
    e = setup(rules, {"bz": ["T882", "T001"]}, dict(P1_DESTROY), filler="T002")
    host, unders = _wire(e, "T882", ["T001"])
    base = unders[0]
    top_before = e.s.zones["deck"][0][0]
    _drive(e, lambda e: len(e.s.cards[host].under) == 2, yes=True)
    assert e.s.cards[host].under == [base, top_before]
    _drive(e, lambda e: e.s.cards[base].zone == "hand"
           and e.s.cards[top_before].zone == "hand",
           cast="T056", target_defn="T882")
    assert e.s.cards[host].zone == "graveyard"


# ---------- 形B: 破壊 → 下にあった対象種族をすべて出す ----------

def test_form_b_destroy_summons_only_was_under_funky(rules):
    e = setup(rules, {"bz": ["T883", "T001"],
                      "graveyard": ["T886", "T886", "T886"]},
              dict(P1_DESTROY), filler="T002")
    host, unders = _wire(e, "T883", ["T001"])
    base = unders[0]
    funky_all = [c for c in e.zlist("graveyard", 0)
                 if e.s.cards[c].defn == "T886"]
    assert len(funky_all) == 3
    # T883 で攻撃 → 攻撃の終わりに墓地のファンキー1体を下に置く
    _drive(e, lambda e: len(e.s.cards[host].under) == 2, attack_with="T883")
    tucked = e.s.cards[host].under[1]
    assert tucked in funky_all
    # 相手が T883 を破壊 → 下にあったファンキーだけが場に出る
    # （下カードの zone は元々 bz なので、トップとして出たことを top_of で見る）
    _drive(e, lambda e: e.s.cards[tucked].zone == "bz"
           and e.s.cards[tucked].top_of < 0,
           cast="T056", target_defn="T883")
    _settle(e)
    assert e.s.cards[host].zone == "graveyard"
    assert e.s.cards[base].zone == "graveyard"      # 対象種族でない下カードは出ない
    rest = [c for c in funky_all if c != tucked]
    assert all(e.s.cards[c].zone == "graveyard" for c in rest)  # 下に無かった分は出ない
    assert _defns(e, "bz").count("T886") == 1


# ---------- 形C: 破壊 → 下にあったカードのうち1枚を出してもよい ----------

def _form_c_setup(rules):
    e = setup(rules, {"bz": ["T884", "T001", "T002"]},
              dict(P1_DESTROY), filler="T007")
    host, unders = _wire(e, "T884", ["T001", "T002"])
    return e, host, unders


def test_form_c_destroy_may_summon_one(rules):
    e, host, unders = _form_c_setup(rules)
    picked = next(u for u in unders if e.s.cards[u].defn == "T002")
    other = next(u for u in unders if e.s.cards[u].defn == "T001")
    _drive(e, lambda e: e.s.cards[picked].zone == "bz"
           and e.s.cards[picked].top_of < 0,
           cast="T056", target_defn="T884", pick_defn="T002", yes=True)
    _settle(e)
    assert e.s.cards[host].zone == "graveyard"
    assert e.s.cards[other].zone == "graveyard"   # 選ばなかった方は墓地に残る


def test_form_c_decline_summons_nothing(rules):
    e, host, unders = _form_c_setup(rules)
    _drive(e, lambda e: e.s.cards[host].zone == "graveyard",
           cast="T056", target_defn="T884", yes=False)
    _settle(e)
    assert all(e.s.cards[u].zone == "graveyard" for u in unders)
    assert _defns(e, "bz") == []


# ---------- 形D: 離れた時 → 下にあったカードをすべて手札へ ----------

def _form_d_setup(rules, p1):
    e = setup(rules, {"bz": ["T885", "T001", "T002"]}, p1, filler="T007")
    host, unders = _wire(e, "T885", ["T001", "T002"])
    return e, host, unders


def test_form_d_destroy_sends_was_under_to_hand(rules):
    e, host, unders = _form_d_setup(rules, dict(P1_DESTROY))
    _drive(e, lambda e: all(e.s.cards[u].zone == "hand" for u in unders),
           cast="T056", target_defn="T885")
    _settle(e)
    assert e.s.cards[host].zone == "graveyard"   # 本体は手札ではなく墓地


def test_form_d_bounce_keeps_everything_in_hand(rules):
    e, host, unders = _form_d_setup(rules, {"hand": ["T888"], "mana": ["T010"] * 2})
    _drive(e, lambda e: e.s.cards[host].zone == "hand",
           cast="T888", target_defn="T885")
    _settle(e)
    # 本体と一緒に手札へ離れた下カードは二重移動せず手札に残る
    assert all(e.s.cards[u].zone == "hand" for u in unders)


def test_form_d_mana_put_sends_was_under_to_hand(rules):
    e, host, unders = _form_d_setup(rules, {"hand": ["T889"], "mana": ["T007"] * 2})
    _drive(e, lambda e: all(e.s.cards[u].zone == "hand" for u in unders),
           cast="T889", target_defn="T885")
    _settle(e)
    assert e.s.cards[host].zone == "mana"        # 本体はマナへ、下は手札へ


# ---------- 対照: 下を持たない通常クリーチャーでは何も起きない ----------

def test_no_under_creature_leave_does_nothing(rules):
    e = setup(rules, {"bz": ["T887"], "graveyard": ["T003"]},
              dict(P1_DESTROY), filler="T002")
    host = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T887")
    _drive(e, lambda e: e.s.cards[host].zone == "graveyard",
           cast="T056", target_defn="T887")
    _settle(e)
    assert _defns(e, "graveyard") == ["T887", "T003"] or \
        sorted(_defns(e, "graveyard")) == ["T003", "T887"]
    assert "T003" not in _defns(e, "hand")
