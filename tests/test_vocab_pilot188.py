"""語彙パイロット第188弾: 敗北の防止（lose_prevention / lose_replacement の防止側）。

「自分がゲームに負ける時、かわりに〜」の置換は第43弾からあるが、「負けない」
そのものの語彙が無かった。本弾で追加するもの:

- op `no_lose`: player は duration の間ゲームに負けない（＝相手は勝てない）。
  once: 一度だけ（防いだら消費。「このターン中に一度、自分がゲームに負ける時、
  かわりに負けない」）。deck_out_only: 山札切れだけを防ぐ。継続的効果として
  s.continuous に載せ、期限切れは既存の duration 仕組みに任せる。
- 常在型能力 `no_lose`: true か {deck_out_only: true}（if と併用可。マナ武装・
  自分のターン中などの条件付き防止、山札切れ限定の防止）。
- Engine.game_lose は防止を先に見て、防がれていれば何もしない（置換の諮問も出ない）。
  常在勝利（kind: state の win）・勝利効果（op win）も、負けない側がいれば働かない。
- 置換の when.reason: 敗北の reason（direct_attack / deck_out / state / effect）と
  照合できる（「相手クリーチャーの攻撃によって、相手がゲームに勝つ時」用）。
- 既存の置換フックで「山札が無い時の引く置換」も表せる（draw イベントの置換。
  ビッグバン型: 空の山札から引く時、かわりに墓地からクリーチャーを出す）。

カードの型:
  静的防止: {kind: static, if?: {...}, no_lose: true | {deck_out_only: true}}
  呪文・誘発の防止付与: {op: no_lose, player: you|opp|each,
    duration: end_of_turn|until_next_own_turn_start|permanent, once?: bool,
    deck_out_only?: bool}
  攻撃による勝利の置換: {kind: replace, optional: true,
    when: {event: lose, reason: direct_attack}, instead: [...]}
  空山札からの引く置換: {kind: replace, optional: true,
    when: {event: draw, player: you},
    if: {cmp: [{count: {zone: deck, owner: you}}, ==, 0]},
    instead: [{op: may, body: [{op: play_free,
      select: {zone: graveyard, owner: you, filter: {types: [creature]}, count: 1}}]}]}

proto T451（ビッグバン型・山札切れ防止＋引く置換）/ T452（ダイハード型・
破壊置換＋破壊時そのターン防止）/ T453（バドフレア型・呪文で一度だけ防止）/
T454（ドギラゴン・ファイアー型・次の自分のターンのはじめまで防止）/
T455（ヴァルハラ型・マナ武装の静的防止）/ T456（ミノガミ型・マナを山札に
戻す置換）/ T457（常在勝利・防止との干渉確認用）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim import scenario
from dmsim.defs import DefError, load_tables, parse_card
from dmsim.engine.ops import op_no_lose

TABLES = load_tables()
PROTOS = ("T451", "T452", "T453", "T454", "T455", "T456", "T457")


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _no_lose_entries(e, player=None):
    return [ce for ce in e.s.continuous if "no_lose" in ce
            and (player is None or ce["no_lose"]["player"] == player)]


def _drive(e, max_steps=800, on_main=None, on_attack=None, on_lose_replace=None,
           on_choose_replacement=None, yes_no=("yes",), stop=None):
    """汎用ドライバ。charge/main/attack は pass（コールバックがあればそれに従う）、
    block は no_block、pay_mana は先頭、他は最小選択。stop(e) が真か結果が出たら止める。"""
    yes_no = list(yes_no)
    for _ in range(max_steps):
        if e.s.result is not None:
            return "result"
        if stop is not None and stop(e):
            return "stop"
        d = e.advance()
        if d is None:
            return "done"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "main" and on_main is not None:
            a = on_main(e, d, keys)
            if a is not None:
                e.answer(a)
                continue
        if kind == "attack" and on_attack is not None:
            a = on_attack(e, d, keys)
            if a is not None:
                e.answer(a)
                continue
        if kind == "lose_replace" and on_lose_replace is not None:
            e.answer(on_lose_replace(keys))
            continue
        if kind == "choose_replacement" and on_choose_replacement is not None:
            e.answer(on_choose_replacement(keys))
            continue
        if kind == "yes_no":
            a = yes_no.pop(0) if yes_no else "yes"
            e.answer([keys.index(a)])
            continue
        if kind == "pay_mana":
            e.answer([0])
            continue
        if kind == "block":
            e.answer([keys.index("no_block")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
            continue
        e.answer(list(range(d["min"])))
    return "max_steps"


def _attack_player(e, d, keys, counter=None):
    atk = [k for k in keys if k.endswith(":player")]
    if not atk:
        return None
    if counter is not None:
        counter[0] += 1
    return [keys.index(atk[0])]


def _pick_replace(keys):
    rep = [i for i, k in enumerate(keys) if k.startswith("lose_replace:")]
    assert rep, keys
    return rep


def _pick_choose_replace(keys):
    rep = [i for i, k in enumerate(keys) if k.startswith("replace:")]
    assert rep, keys
    return rep


def _face0(parsed):
    """単面カードは CardDef 自体が面、ツインパクトは faces[0] が面。"""
    return parsed.faces[0] if parsed.faces else parsed


def test_proto_parse():
    for cid in PROTOS:
        assert parse_card(_proto_card(cid), TABLES) is not None
    t451 = _face0(parse_card(_proto_card("T451"), TABLES))
    static = [a for a in t451.abilities if a["kind"] == "static"]
    assert static == [{"kind": "static", "no_lose": {"deck_out_only": True}}]
    rep = [a for a in t451.abilities if a["kind"] == "replace"][0]
    assert rep["when"] == {"event": "draw", "player": "you"}
    assert rep["if"] == {"cmp": [{"count": {"zone": "deck", "owner": "you"}}, "==", 0]}
    assert rep["instead"][0]["body"][0] == {
        "op": "play_free",
        "select": {"zone": "graveyard", "owner": "you",
                   "filter": {"types": ["creature"]}, "count": 1}}
    t452 = _face0(parse_card(_proto_card("T452"), TABLES))
    rep = [a for a in t452.abilities if a["kind"] == "replace"][0]
    assert rep["when"] == {"event": "lose"} and rep["optional"] is True
    assert rep["instead"] == [{"op": "move", "select": {"ref": "self"},
                               "to": "graveyard", "reason": "destroy"}]
    trig = [a for a in t452.abilities if a["kind"] == "trigger"][0]
    assert trig["effect"] == [{"op": "no_lose", "player": "you",
                               "duration": "end_of_turn"}]
    t453 = _face0(parse_card(_proto_card("T453"), TABLES))
    # destroy はマクロで move（to: graveyard, reason: destroy）に展開される。
    assert t453.spell == [
        {"op": "move",
         "select": {"zone": "bz", "owner": "opp",
                    "filter": {"types": ["creature"], "power_le": 5000}, "count": 1},
         "to": "graveyard", "reason": "destroy"},
        {"op": "no_lose", "player": "you", "duration": "end_of_turn", "once": True}]
    t454 = _face0(parse_card(_proto_card("T454"), TABLES))
    assert t454.spell == [{"op": "no_lose", "player": "you",
                           "duration": "until_next_own_turn_start"}]
    t455 = _face0(parse_card(_proto_card("T455"), TABLES))
    static = [a for a in t455.abilities if a["kind"] == "static"][0]
    assert static["no_lose"] is True
    assert static["if"] == {"cmp": [{"count": {"zone": "mana", "owner": "you",
                                               "filter": {"civs": ["light"]}}}, ">=", 2]}
    t456 = _face0(parse_card(_proto_card("T456"), TABLES))
    rep = [a for a in t456.abilities if a["kind"] == "replace"][0]
    assert rep["instead"] == [{"op": "move",
                               "select": {"zone": "mana", "owner": "you", "count": 2},
                               "to": "deck", "position": "bottom",
                               "reason": "put", "order": "shuffle"}]
    t457 = _face0(parse_card(_proto_card("T457"), TABLES))
    state = [a for a in t457.abilities if a["kind"] == "state"][0]
    assert state["effect"] == [{"op": "win", "player": "you"}]


def test_bad_no_lose_forms_rejected():
    base = _proto_card("T451")
    bad = dict(base, abilities=[{"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
                                 "no_lose": True, "effect": []}])
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = dict(base, abilities=[{"kind": "static", "no_lose": {"player": "you"}}])
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = dict(base, abilities=[{"kind": "replace", "when": {"event": "lose", "reason": "bogus"},
                                 "instead": []}])
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    ok = dict(base, abilities=[{"kind": "replace", "when": {"event": "lose", "reason": "direct_attack"},
                                "instead": [{"op": "move", "select": {"ref": "self"},
                                             "to": "graveyard", "reason": "destroy"}]}])
    assert parse_card(ok, TABLES) is not None


def _duel(rules, p0, p1, deck_exact=(False, False), deck_size=20):
    return scenario.build(rules, {
        "p0": p0, "p1": p1, "filler": "T001", "seed": 1,
        "deck_size": deck_size, "deck_exact": list(deck_exact),
    })


def test_deck_out_immunity(rules):
    """T451: 山札が空でも、常在の山札切れ防止で負けない。"""
    e = _duel(rules, {"bz": ["T451"], "deck": []},
              {"bz": ["T001"]}, deck_exact=(True, False), deck_size=40)
    _drive(e, max_steps=60, stop=lambda e: e.s.turn >= 4)
    assert e.s.result is None
    assert e.zlist("deck", 0) == []


def test_deck_out_loses_without_immunity(rules):
    """対照: 防止が無ければ山札切れで負ける。"""
    e = _duel(rules, {"bz": ["T001"], "deck": []},
              {"bz": ["T001"]}, deck_exact=(True, False))
    _drive(e, max_steps=60)
    assert e.s.result == {"winner": 1, "reason": "deck_out", "turn": e.s.turn}


def test_draw_replacement_plays_from_graveyard(rules):
    """T451: 空の山札から引く時、かわりに墓地のクリーチャーを出す。"""
    e = _duel(rules, {"bz": ["T451"], "deck": [], "graveyard": ["T001"]},
              {"bz": ["T001"]}, deck_exact=(True, False))
    seen = {"rep": False}

    def on_rep(keys):
        seen["rep"] = True
        return _pick_choose_replace(keys)

    r = _drive(e, max_steps=120, on_choose_replacement=on_rep,
               stop=lambda e: any(e.s.cards[c].defn == "T001"
                                  and e.s.cards[c].controller == 0
                                  for c in e.zlist("bz", 0)))
    assert seen["rep"] is True
    assert r == "stop"
    assert e.s.result is None
    assert e.zlist("graveyard", 0) == []


def test_draw_replacement_decline(rules):
    """T451: 引く置換を辞退しても、山札切れ防止で負けない（引けないまま）。"""
    e = _duel(rules, {"bz": ["T451"], "deck": [], "graveyard": ["T001"], "hand": []},
              {"bz": ["T001"]}, deck_exact=(True, False), deck_size=40)
    seen = {"declined": False}

    def on_rep(keys):
        seen["declined"] = True
        return [keys.index("decline")]

    _drive(e, max_steps=60, on_choose_replacement=on_rep,
           stop=lambda e: seen["declined"])
    assert seen["declined"] is True
    # 2回目以降のドローでも置換を辞退し続ける（さもないと墓地の T001 が出てしまう）。
    _drive(e, max_steps=12, on_choose_replacement=on_rep)
    assert e.s.result is None
    assert len(e.zlist("graveyard", 0)) == 1
    assert e.zlist("deck", 0) == []


def test_lose_replace_then_turn_immunity(rules):
    """T452: ダイレクトアタックを破壊で置換し、破壊時の誘発でそのターン負けない。
    同じターンの2回目のダイレクトアタックも防ぐ。"""
    e = _duel(rules, {"bz": ["T001", "T001"]},
              {"bz": ["T452"], "shield": [], "deck": ["T005"] * 10},
              deck_exact=(False, True))
    cnt = [0]
    r = _drive(e, max_steps=200,
               on_attack=lambda e, d, k: _attack_player(e, d, k, cnt),
               on_lose_replace=_pick_replace,
               stop=lambda e: (any(e.s.cards[c].defn == "T452" for c in e.zlist("graveyard", 1))
                               and _no_lose_entries(e, 1)))
    assert r == "stop", "T452 の置換＋防止付与まで進まなかった"
    assert cnt[0] >= 1
    assert e.s.result is None
    assert _no_lose_entries(e, 1)[0]["duration"] == "end_of_turn"
    # 2回目のダイレクトアタック（もう1体の T001。置換の解決と同じ advance で
    # 決定が出るため、止まるまでに既に攻撃が選ばれていることがある）も防ぐ。
    # 残りの進行を少しだけ進めて、2回目の攻撃の解決を見届ける。
    _drive(e, max_steps=8)
    assert e.s.result is None


def test_lose_replace_decline_loses(rules):
    """T452: 置換を辞退すればダイレクトアタックで負ける。"""
    e = _duel(rules, {"bz": ["T001"]},
              {"bz": ["T452"], "shield": [], "deck": ["T005", "T005", "T005"]},
              deck_exact=(False, True))
    _drive(e, max_steps=200,
           on_attack=lambda e, d, k: _attack_player(e, d, k),
           on_lose_replace=lambda keys: [keys.index("decline")])
    assert e.s.result is not None and e.s.result["winner"] == 0


def test_spell_once_prevents_one_loss_only(rules):
    """T453: 呪文の一度だけ防止は1回目の敗北を防ぎ、2回目は防がない。
    唱えた後も出せるカード（水呪文 T003＋水マナ）を残す。唱えた advance の中で
    ターンが終わると end_of_turn の防止が切れて観測できないため。"""
    e = _duel(rules, {"hand": ["T453", "T003"], "mana": ["T003"] * 6,
              "shield": []},
              {"bz": ["T001"]})

    def on_main(e, d, keys):
        if "play:T453" in keys:
            return [keys.index("play:T453")]
        return None

    _drive(e, max_steps=120, on_main=on_main,
           stop=lambda e: _no_lose_entries(e, 0))
    assert _no_lose_entries(e, 0), "T453 の防止が付与されなかった"
    assert _no_lose_entries(e, 0)[0]["no_lose"]["once"] is True
    assert _no_lose_entries(e, 0)[0]["duration"] == "end_of_turn"
    assert e.game_lose(0, "direct_attack") == []
    assert e.s.result is None
    assert _no_lose_entries(e, 0) == []   # 一度きりは消費された
    assert e.game_lose(0, "direct_attack") == []
    assert e.s.result is not None and e.s.result["winner"] == 1


def test_spell_until_next_turn(rules):
    """T454: 次の自分のターンのはじめまで防止。相手ターン中の攻撃は防ぎ、
    自分の次のターンが始まって切れた後の攻撃は防がない。"""
    e = _duel(rules, {"hand": ["T454", "T001"], "mana": ["T452"] * 4, "shield": []},
              {"bz": ["T001", "T001"], "shield": []})

    def on_main(e, d, keys):
        if "play:T454" in keys:
            return [keys.index("play:T454")]
        return None

    _drive(e, max_steps=120, on_main=on_main,
           stop=lambda e: _no_lose_entries(e, 0))
    assert _no_lose_entries(e, 0)[0]["duration"] == "until_turn_start:0"
    cnt = [0]
    _drive(e, max_steps=200,
           on_attack=lambda e, d, k: _attack_player(e, d, k, cnt),
           stop=lambda e: cnt[0] == 1)
    assert e.s.result is None   # 相手ターン中の攻撃は防がれた
    _drive(e, max_steps=40, stop=lambda e: not _no_lose_entries(e, 0))
    assert _no_lose_entries(e, 0) == []   # 次の自分のターンのはじめに切れた
    _drive(e, max_steps=200,
           on_attack=lambda e, d, k: _attack_player(e, d, k, cnt),
           stop=lambda e: e.s.result is not None)
    assert e.s.result is not None and e.s.result["winner"] == 1


def test_mana_armed_static(rules):
    """T455: 光マナ2枚で常在防止が働く。1枚では働かない。"""
    e = _duel(rules, {"bz": ["T001"]},
              {"bz": ["T455"], "mana": ["T455", "T455"], "shield": []})
    cnt = [0]
    _drive(e, max_steps=200,
           on_attack=lambda e, d, k: _attack_player(e, d, k, cnt),
           stop=lambda e: cnt[0] == 1)
    assert e.s.result is None
    e2 = _duel(rules, {"bz": ["T001"]},
               {"bz": ["T455"], "mana": ["T455"], "shield": []})
    _drive(e2, max_steps=200,
           on_attack=lambda e, d, k: _attack_player(e, d, k),
           stop=lambda e: e.s.result is not None)
    assert e2.s.result is not None and e2.s.result["winner"] == 0


def test_lose_replace_mana_to_deck(rules):
    """T456: 敗北をマナ2枚の山札送りで置換する。"""
    e = _duel(rules, {"bz": ["T001"]},
              {"bz": ["T456"], "mana": ["T001", "T001", "T001"],
               "shield": [], "deck": ["T005", "T005", "T005"]},
              deck_exact=(False, True))
    mana_before = len(e.zlist("mana", 1))
    _drive(e, max_steps=200,
           on_attack=lambda e, d, k: _attack_player(e, d, k),
           on_lose_replace=_pick_replace,
           stop=lambda e: len(e.zlist("mana", 1)) == mana_before - 2)
    assert e.s.result is None
    assert len(e.zlist("mana", 1)) == mana_before - 2
    # 山札に送った2枚（T001）が山札にある。置換の直後に相手のドローが1枚入るため、
    # 山札の総数は +2 ではなく +1 になることがある。
    moved = [c for c in e.zlist("deck", 1) if e.s.cards[c].defn == "T001"]
    assert len(moved) == 2


def test_state_win_blocked_by_immunity(rules):
    """常在勝利（T457）は、負ける側に防止があれば働かず、防止が切れたら働く。
    防止の付与自体は op_no_lose を直接呼ぶ（付与経路は T453/T454 で別途検証）。"""
    e = _duel(rules, {"bz": ["T457", "T001", "T001"]},
              {"bz": ["T001"]})
    op_no_lose(e, {}, {"op": "no_lose", "player": "you", "duration": "end_of_turn"},
               {"you": 1})
    d = e.advance()   # 最初の決定（charge）まで進める間に SBA が走り、常在勝利が試される
    assert e.s.result is None   # 防止がある間は常在勝利が働かない
    assert _no_lose_entries(e, 1)
    keys = [o["key"] for o in d["options"]]
    e.answer([keys.index("pass")])
    _drive(e, max_steps=600, stop=lambda e: e.s.result is not None)
    assert e.s.result is not None and e.s.result["winner"] == 0   # 切れたら勝つ
