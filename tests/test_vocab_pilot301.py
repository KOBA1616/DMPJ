"""語彙パイロット第301弾（2026-11-20）の検証。

reveal_stay（純粋3件: dmr05-v03 黄金世代 鬼丸「爆」 / dmx15-006
夢幻界廊 ヴァリアント / dmx16-006 インフィニティ・ドラゴン）。
3件とも同じ条項「離れる／破壊される時、山札の上から1枚目を見せて
（または墓地に置いて）、それが指定種族であれば、かわりにバトル
ゾーンにとどまる」。partial の注記がそろって「置換の instead 内で
条件を見て元の移動を再適用する手段が無い」と書いており、不足は
その1点だけだった。そこで新 op **move_to_event** を追加した:
置換されたイベントレコードの行き先・理由・位置と効果帰属
（by / cause）を引き継いで選んだカードを移動し、no_replace の印で
再置換されないようにする（G-NEO の move_under_to_event と対:
あちらは発生源の下のカード専用、こちらは select で選んだカード用）。

確立した3形（いずれも必須の置換。instead の先頭で公開／墓地置きを
行い、束縛したカードが種族に合わなければ move_to_event で元の
移動を再適用する。合えば元の移動は置換されたまま＝とどまる）:

- 形A（dmr05-v03、破壊のみ・公開形）: choose {from_top: 1,
  reveal: true} で上を全員に見せ、ヒューマノイドでなければ
  move_to_event で破壊を再適用する。第2節（破壊された時、下に
  あったカードをすべて墓地から出す）は第294弾の event.was_under
  ＋ play_free の既存形で、再適用された破壊レコードから通常どおり
  誘発することをあわせて固定する（とどまった場合は誘発しない）。
- 形B（dmx15-006、離脱全般・任意で墓地置き）: may（中身を見ない
  盲目選択）で上1枚を choose 束縛し、束縛があれば墓地へ移し、
  アウトレイジでなければ元の移動（行き先はイベント依存）を
  再適用する。墓地に置かない選択でも離れる。
- 形C（dmx16-006、監視者形）: 自分のドラゴンが離れる時に自分の
  山札の上1枚を（必須で）墓地に置き、ドラゴンまたはファイアー・
  バードであればそのドラゴンはとどまる。監視者自身（ドラゴン）も
  対象に含む。相手のドラゴン・ドラゴンでない味方は監視しない。

設計上の要点（実装で実証）: instead 内の移動は capture され、束の
適用は instead 全体の解決後に回る。そのため move の as 束縛は
（移動先ゾーンで照合する h_bind が適用前に走り）空になり、移動した
カードを if で見る形は instead 内では成立しない。確立形は
「choose で束縛 → ref のまま判定 → 移動を発行」の順: 判定時点では
capture は未適用で ref が生きている（gen は適用時に増える）。

なお rejects の dmrp22-005 にも reveal_stay のラベルがあるが、その
unsupported は「山札の上をこのターンの終わりまで表向きにする」条項
（play_from_deck_top と対の別条項）で、本ファミリーの誤ラベル。
本弾の対象外として docs に記録のみ。
"""
from dmsim.cards.defs import load_tables, parse_card
from tests.conftest import setup

TABLES = load_tables()
PROTOS = ("T910", "T911", "T912", "T913", "T914", "T915", "T916")

FORM_A = {"kind": "replace",
          "when": {"event": "move", "from": "bz", "to": "graveyard",
                   "reason": "destroy", "subject": "self"},
          "instead": [
              {"op": "choose",
               "select": {"zone": "deck", "owner": "you", "from_top": 1,
                          "count": 1},
               "reveal": True, "as": "top"},
              {"op": "if",
               "cond": {"not": {"exists": {"ref": "top",
                                           "filter": {"race_has": "ヒューマノイド"}}}},
               "then": [{"op": "move_to_event",
                         "select": {"ref": "event.subject"}}]}]}
FORM_A_C2 = {"kind": "trigger",
             "when": {"event": "move", "from": "bz", "to": "graveyard",
                      "reason": "destroy", "subject": "self"},
             "effect": [{"op": "may", "body": [
                 {"op": "play_free",
                  "select": {"ref": "event.was_under",
                             "zone": "graveyard"}}]}]}
FORM_B = {"kind": "replace",
          "when": {"event": "move", "from": "bz", "subject": "self"},
          "instead": [
              {"op": "may", "body": [
                  {"op": "choose",
                   "select": {"zone": "deck", "owner": "you", "from_top": 1,
                              "count": 1},
                   "as": "picked"}]},
              {"op": "if",
               "cond": {"exists": {"ref": "picked"}},
               "then": [{"op": "move", "select": {"ref": "picked"},
                         "to": "graveyard", "reason": "put"}]},
              {"op": "if",
               "cond": {"not": {"exists": {"ref": "picked",
                                           "filter": {"race_has": "アウトレイジ"}}}},
               "then": [{"op": "move_to_event",
                         "select": {"ref": "event.subject"}}]}]}
FORM_C = {"kind": "replace",
          "when": {"event": "move", "from": "bz",
                   "subject": {"owner": "you",
                               "filter": {"types": ["creature"],
                                          "race_has": "ドラゴン"}}},
          "instead": [
              {"op": "choose",
               "select": {"zone": "deck", "owner": "you", "from_top": 1,
                          "count": 1},
               "as": "seen"},
              {"op": "move", "select": {"ref": "seen"},
               "to": "graveyard", "reason": "put"},
              {"op": "if",
               "cond": {"not": {"any": [
                   {"exists": {"ref": "seen",
                               "filter": {"race_has": "ドラゴン"}}},
                   {"exists": {"ref": "seen",
                               "filter": {"race_has": "ファイアー・バード"}}}]}},
               "then": [{"op": "move_to_event",
                         "select": {"ref": "event.subject"}}]}]}


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


# ---------- ハーネス（第299弾と同型） ----------

def _defns(e, zone, p=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _wire(e, host_defn, under_defns, p=0):
    """bz に置いた札同士で進化スタックを組む（第294弾と同じ作法）。"""
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
           pick_defn=None, yes=True, steps=400):
    """done(e) が真になるまで汎用に答える（第299弾 _drive と同型）。"""
    st = {"cast": False}
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
        elif kind == "choose_cards":
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
        elif kind == "yes_no":
            want = "yes" if yes else "no"
            e.answer([keys.index(want)] if want in keys
                     else list(range(d["min"])))
        elif kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("drive budget exhausted")


def _pub(e, kind, defn=None):
    return [r for r in e.s.pub if r["kind"] == kind
            and (defn is None or r.get("defn") == defn)]


def _build_exact(rules, p0, deck_card, p1):
    """p0 の山札を指定カードだけにする（第299弾 _build_exact と同型）。"""
    from dmsim.engine import scenario
    spec0 = dict(p0)
    spec0["deck"] = [deck_card] * 4
    return scenario.build(
        rules, {"p0": spec0, "p1": p1, "filler": "T002", "seed": 1,
                "deck_exact": [True, False]})


P1_DESTROY = {"hand": ["T056"], "mana": ["T008"] * 3}
P1_BOUNCE = {"hand": ["T140"], "mana": ["T010"] * 3}


# ---------- parse / 形の一致 ----------

def test_protos_parse_and_forms():
    for tid in PROTOS:
        parse_card(_proto_card(tid), TABLES)
    from tests._conv_cache import proto_card
    d = parse_card(proto_card("T910"), TABLES)
    assert FORM_A in d.abilities
    assert FORM_A_C2 in d.abilities
    assert parse_card(proto_card("T911"), TABLES).abilities == [FORM_B]
    assert parse_card(proto_card("T912"), TABLES).abilities == [FORM_C]


def test_move_to_event_op_registered():
    import json
    from pathlib import Path

    from dmsim.base.opvocab import OP_ARGS
    assert OP_ARGS["move_to_event"] == {"select": "selector"}
    schema = json.loads((Path(__file__).parent.parent / "data" / "schema"
                         / "card.schema.json").read_text(encoding="utf-8"))
    assert "move_to_event" in json.dumps(schema)


# ---------- 実挙動: 形A（T910、破壊・公開形） ----------

def test_form_a_match_stays_and_reveals(rules):
    """上がヒューマノイドなら破壊されずにとどまる（スタックも無事）。
    公開は記録され、下にあったカードの第2節は誘発しない。"""
    e = _build_exact(rules, {"bz": ["T910", "T001"]}, "T914",
                     dict(P1_DESTROY))
    host, unders = _wire(e, "T910", ["T001"])
    _drive(e, lambda e: "T056" in _defns(e, "graveyard", 1) and _quiet(e),
           cast="T056", target_defn="T910")
    assert "T910" in _defns(e, "bz")
    assert e.s.cards[host].under == unders          # スタックは崩れていない
    assert "T910" not in _defns(e, "graveyard")
    assert "T001" not in _defns(e, "graveyard")
    assert _pub(e, "reveal", defn="T914")           # 上は全員に公開された
    assert len(e.s.zones["deck"][0]) == 3           # 公開のみで山札は減らない


def test_form_a_nomatch_destroyed_and_under_returns(rules):
    """上がヒューマノイドでなければ通常どおり破壊される（公開はされる）。
    再適用された破壊から第2節が誘発し、下にあったカードが戻る。"""
    e = _build_exact(rules, {"bz": ["T910", "T001"]}, "T003",
                     dict(P1_DESTROY))
    _wire(e, "T910", ["T001"])
    _drive(e, lambda e: "T910" in _defns(e, "graveyard") and _quiet(e),
           cast="T056", target_defn="T910")
    assert "T910" in _defns(e, "graveyard")
    assert _pub(e, "reveal", defn="T003")           # 外れても公開はされる
    assert "T001" in _defns(e, "bz")                # 第2節で下のカードが出た
    assert "T001" not in _defns(e, "graveyard")


# ---------- 実挙動: 形B（T911、離脱全般・任意ミル） ----------

def test_form_b_match_stays(rules):
    """バウンスされても、墓地に置いた上がアウトレイジならとどまる。"""
    e = _build_exact(rules, {"bz": ["T911"]}, "T915", dict(P1_BOUNCE))
    _drive(e, lambda e: "T140" in _defns(e, "graveyard", 1) and _quiet(e),
           cast="T140", target_defn="T911", pick_defn="T911")
    assert "T911" in _defns(e, "bz")
    assert "T911" not in _defns(e, "hand")
    assert "T915" in _defns(e, "graveyard")         # 置いた1枚は墓地にある


def test_form_b_nomatch_bounced(rules):
    """上がアウトレイジでなければ、元の移動（手札へ）が再適用される。"""
    e = _build_exact(rules, {"bz": ["T911"]}, "T003", dict(P1_BOUNCE))
    _drive(e, lambda e: "T911" in _defns(e, "hand") and _quiet(e),
           cast="T140", target_defn="T911", pick_defn="T911")
    assert "T911" in _defns(e, "hand")
    assert "T003" in _defns(e, "graveyard")         # 置いた1枚は墓地にある


def test_form_b_decline_mill_bounced(rules):
    """墓地に置かないことを選んでも、そのまま離れる（山札は減らない）。"""
    e = _build_exact(rules, {"bz": ["T911"]}, "T915", dict(P1_BOUNCE))
    _drive(e, lambda e: "T911" in _defns(e, "hand") and _quiet(e),
           cast="T140", target_defn="T911", pick_defn="T911", yes=False)
    assert "T911" in _defns(e, "hand")
    assert len(e.s.zones["deck"][0]) == 3           # ドロー分のみ減った
    assert "T915" not in _defns(e, "graveyard")


# ---------- 実挙動: 形C（T912、監視者形） ----------

def test_form_c_dragon_milled_stays(rules):
    """自分のドラゴンが破壊される時、置いた上がドラゴンならとどまる。"""
    e = _build_exact(rules, {"bz": ["T912", "T913"]}, "T913",
                     dict(P1_DESTROY))
    _drive(e, lambda e: "T056" in _defns(e, "graveyard", 1) and _quiet(e),
           cast="T056", target_defn="T913")
    assert "T913" in _defns(e, "bz")                # 場のドラゴンは残った
    assert _defns(e, "graveyard").count("T913") == 1  # 落ちたのはミルの1枚


def test_form_c_firebird_milled_stays(rules):
    """置いた上がファイアー・バードでもとどまる。"""
    e = _build_exact(rules, {"bz": ["T912", "T913"]}, "T916",
                     dict(P1_DESTROY))
    _drive(e, lambda e: "T056" in _defns(e, "graveyard", 1) and _quiet(e),
           cast="T056", target_defn="T913")
    assert "T913" in _defns(e, "bz")
    assert "T916" in _defns(e, "graveyard")


def test_form_c_nomatch_destroyed(rules):
    """上がどちらでもなければ、ドラゴンは通常どおり破壊される。"""
    e = _build_exact(rules, {"bz": ["T912", "T913"]}, "T003",
                     dict(P1_DESTROY))
    _drive(e, lambda e: "T913" in _defns(e, "graveyard") and _quiet(e),
           cast="T056", target_defn="T913")
    assert "T913" not in _defns(e, "bz")
    assert "T003" in _defns(e, "graveyard")         # ミルは必須（落ちている）


def test_form_c_watcher_itself_stays(rules):
    """監視者自身（ドラゴン）が離れる時も、自分の置換が働く。"""
    e = _build_exact(rules, {"bz": ["T912"]}, "T913", dict(P1_DESTROY))
    _drive(e, lambda e: "T056" in _defns(e, "graveyard", 1) and _quiet(e),
           cast="T056", target_defn="T912")
    assert "T912" in _defns(e, "bz")
    assert _defns(e, "graveyard").count("T913") == 1


def test_form_c_opponent_dragon_not_watched(rules):
    """相手のドラゴンの離脱は監視しない（ミルも起きない）。"""
    e = setup(rules, {"bz": ["T912"], "hand": ["T056"], "mana": ["T008"] * 3},
              {"bz": ["T913"]}, filler="T002")
    n_deck = len(e.s.zones["deck"][0])
    _drive(e, lambda e: "T913" in _defns(e, "graveyard", 1) and _quiet(e),
           cast="T056", cast_player=0, target_defn="T913")
    assert "T913" in _defns(e, "graveyard", 1)
    # p0 の山札は setup 時点（初回ドロー済み）から減っていない＝ミルは無い
    assert len(e.s.zones["deck"][0]) == n_deck


def test_form_c_nondragon_no_mill(rules):
    """ドラゴンでない味方の離脱は監視しない（ミルも起きない）。"""
    e = _build_exact(rules, {"bz": ["T912", "T001"]}, "T913",
                     dict(P1_DESTROY))
    _drive(e, lambda e: "T001" in _defns(e, "graveyard") and _quiet(e),
           cast="T056", target_defn="T001")
    assert "T001" in _defns(e, "graveyard")
    assert "T913" not in _defns(e, "graveyard")     # ミルは起きていない
    assert len(e.s.zones["deck"][0]) == 3           # ドロー分のみ減った
