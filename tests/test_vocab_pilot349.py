"""語彙パイロット第349弾: summon_lock（ドリフト）。

対象（pure 4件のうち3件）:
- promoy11-083 鬼丸「Ｅｎｄ」（誰もゼニスを召喚できない）
- promoy12-036 激流剣砲 カツ∞キング（自分の他の、名前に
  《剣砲》とあるエグザイル・クリーチャーを出せない）
- promoy12-085 漢のキズナ カツブードン（同名版）

形: 「召喚できない」は許可 summon の deny、「バトルゾーンに
出すことはできない」は許可 enter_bz の deny（permissions.yaml の
注記どおり召喚・効果・革命チェンジすべてを止める）。対象は
affects の filter で絞る（ゼニスは race_has、エグザイルは
types: [exile_creature]＋name_has）。
promoy11-083 の「ゼニスとバトル中パワー+11000」は
battle_power: {amount, opponent_filter} の確立形。

dmx25-s07 は対象外（partial の原文が断片のみ）。

proto: T1050（083型）/ T1051（036型）/ T1052（085型）
＋検証 fixture T1053（剣砲エグザイル）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
scenario.build を直接包む（第319弾以降の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

def _lock5(name_has):
    return [{"kind": "static",
             "affects": {"zone": z, "owner": "you",
                         "filter": {"types": ["exile_creature"],
                                    "name_has": name_has}},
             "mod": {"deny": ["enter_bz"]}}
            for z in ("hand", "graveyard", "mana", "deck", "shield")]


LOCK_ZENITH = {
    "kind": "static",
    "affects": {"zone": "hand", "owner": "any",
                "filter": {"types": ["creature"], "race_has": "ゼニス"}},
    "mod": {"deny": ["summon"]},
}
BATTLE_ZENITH = {
    "kind": "static", "affects": "self",
    "mod": {"battle_power": {"amount": 11000,
                             "opponent_filter": {"race_has": "ゼニス"}}},
}
CIP_036 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "destroy",
                "select": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"],
                                      "keyword": "blocker"},
                           "count": "all"}},
               {"op": "may", "body": [{"op": "draw", "count": 1}]}],
}
LOCK_036 = _lock5("剣砲")
CIP_085 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "may",
                "body": [{"op": "move",
                          "select": {"zone": "bz", "owner": "you",
                                     "filter": {"types": ["creature"]},
                                     "count": 1,
                                     "exclude": [{"ref": "self"}]},
                          "to": "graveyard", "reason": "destroy",
                          "as": "dead"}]},
               {"op": "if",
                "cond": {"cmp": [{"count": {"ref": "dead"}}, ">=", 1]},
                "then": [{"op": "choose",
                          "select": {"zone": "deck", "owner": "you",
                                     "look": True,
                                     "filter": {"types": ["exile_creature"]},
                                     "count": 1},
                          "as": "found"},
                         {"op": "may",
                          "body": [{"op": "move",
                                    "select": {"ref": "found",
                                               "count": "all"},
                                    "to": "hand", "reason": "draw"}]},
                         {"op": "shuffle"}]}],
}
LOCK_085 = _lock5("漢のキズナ カツブードン")

FORM_083 = [LOCK_ZENITH, BATTLE_ZENITH]
FORM_036 = [CIP_036] + LOCK_036
FORM_085 = [CIP_085] + LOCK_085


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    for tid, form in (("T1050", FORM_083), ("T1051", FORM_036),
                      ("T1052", FORM_085)):
        c = proto_card(tid)
        assert c["abilities"] == form, tid
        parse_card(c, TABLES)


def _build(rules, p0, p1, deck=None):
    spec = {"p0": p0, "p1": p1, "filler": "T002", "seed": 1,
            "deck_size": 20}
    if deck:
        spec["deck"] = deck
    return scenario.build(rules, spec)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _drive_to_main(e, player=0, limit=300):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] == "main" and d.get("player") == player:
            return d, _keys(d)
        if "pass" in _keys(d):
            e.answer([_keys(d).index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("main never came")


ALL_MANA = ["T001", "T004", "T005", "T009", "T053"]


def test_zenith_summon_locked(rules):
    # 鬼丸が場にいると、相手はゼニス（T787）を召喚できない
    zmana = ["T789", "T001", "T001"]     # ゼロ文明のマナを含む
    e = _build(rules, {"bz": ["T1050"]},
               {"hand": ["T787"], "mana": zmana})
    d, keys = _drive_to_main(e, player=1)
    assert "play:T787" not in keys
    # 発生源がいなければ召喚できる
    e = _build(rules, {}, {"hand": ["T787"], "mana": zmana})
    d, keys = _drive_to_main(e, player=1)
    assert "play:T787" in keys


def test_zenith_battle_power(rules):
    # ゼニス（9000）とのバトルでは 7000+11000 で勝つ
    e = _build(rules, {"bz": ["T1050"]}, {"bz": ["T201"]})
    _tap(e, "T201")
    _battle(e, "T1050", "T201")
    assert "T201" in [e.s.cards[c].defn for c in e.zlist("graveyard", 1)]
    assert "T1050" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    # ゼニスでない相手（17000）には負ける
    e = _build(rules, {"bz": ["T1050"]}, {"bz": ["T1014"]})
    _tap(e, "T1014")
    _battle(e, "T1050", "T1014")
    assert "T1050" in [e.s.cards[c].defn for c in e.zlist("graveyard", 0)]


def _tap(e, defn, player=1):
    cid = next(c for c in e.bz_tops(player) if e.s.cards[c].defn == defn)
    e.s.cards[cid].tapped = True


def _battle(e, attacker, defender):
    state = {}
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 1:
            return
        if d["kind"] == "attack" and d.get("player") == 0 \
                and not state.get("attacked"):
            atk = [k for k in keys
                   if k.startswith(f"attack:{attacker}:")]
            tgt = [k for k in atk if k.endswith(f":{defender}")]
            if tgt:
                state["attacked"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("battle never finished")


def test_kenpou_lock(rules):
    # カツ∞キングが場にいると剣砲エグザイル（T1053）を出せない
    e = _build(rules, {"bz": ["T1051"], "hand": ["T1053"],
                       "mana": ["T001", "T001", "T001"]}, {})
    d, keys = _drive_to_main(e)
    assert "play:T1053" not in keys
    e = _build(rules, {"hand": ["T1053"],
                       "mana": ["T001", "T001", "T001"]}, {})
    d, keys = _drive_to_main(e)
    assert "play:T1053" in keys


def _play_and_resolve(e, play_key, picks):
    """main で play_key を選び、picks（key の接頭辞）で choose を
    捌きながら相手の charge まで進める。"""
    d, keys = _drive_to_main(e)
    assert play_key in keys, keys
    e.answer([keys.index(play_key)])
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 1:
            return
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("yes")])
        elif d["kind"] == "choose_cards":
            hit = None
            for pref in picks:
                cand = [i for i, o in enumerate(d["options"])
                        if o["key"].startswith(pref)]
                if cand:
                    hit = cand[:d["min"]] or cand[:1]
                    break
            e.answer(hit if hit else list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("resolution never finished")


def test_cip036_destroys_all_blockers(rules):
    e = _build(rules, {"hand": ["T1051"],
                       "mana": ["T009", "T005"] + ["T001"] * 7},
               {"bz": ["T004", "T004", "T005"]})
    _play_and_resolve(e, "play:T1051", [])
    p1_bz = [e.s.cards[c].defn for c in e.bz_tops(1)]
    assert p1_bz == ["T005"], p1_bz       # ブロッカーだけ全滅


def test_cip085_search_exile(rules):
    e = _build(rules, {"hand": ["T1052"], "bz": ["T005"],
                       "mana": ["T053", "T005"] + ["T001"] * 4,
                       "deck": ["dmr11-013"]},
               {})
    _play_and_resolve(e, "play:T1052", ["bz:T005", "deck:dmr11-013"])
    assert "T005" in [e.s.cards[c].defn for c in e.zlist("graveyard", 0)]
    assert "dmr11-013" in [e.s.cards[c].defn for c in e.zlist("hand", 0)]
