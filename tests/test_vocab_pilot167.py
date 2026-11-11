"""語彙パイロット第167弾: G・G・G（手札1枚以下を条件とする能力群）。

G・G・G の条件は手札数の count 式
{cmp: [{count: {zone: hand, owner: you}}, "<=", 1]}（第3段で既存可と裏取り済み。
T271 が軽減形の先例）。常在型・誘発型の if、op if の cond、alt_cost の if に
置いて表す。新語彙なし。

本弾のエンジン変更は1点だけ: combat._battle_bonus が条件つき常在型の if を
見ていなかったため、battle_power の条件が無視されていた（dmr09-031
「相手のターン、バトル中+4000」が自分のターンでも効く潜在不具合）。
chars の集約と同じく _static_cond で見るようにした。T319 の対照実験
（手札2枚では +3000 が付かない）がこの修正の判別テストになる。
"""
from pathlib import Path

import yaml
from conftest import setup

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

HAND_LE_1 = {"cmp": [{"count": {"zone": "hand", "owner": "you"}}, "<=", 1]}


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    for cid in ("T314", "T315", "T316", "T317", "T318", "T319", "T320", "T321", "T322", "T323"):
        parse_card(_proto_card(cid), TABLES)
    assert _proto_card("T314")["abilities"][0]["mod"] == {"grant": ["speed_attacker"]}
    assert _proto_card("T316")["abilities"][0]["mod"] == {"deny": ["attack_player", "attack_creature"]}
    assert _proto_card("T317")["abilities"][0]["affects"] == {"zone": "hand", "owner": "you",
                                                              "filter": {"types": ["creature"], "races": ["テスト"]}}
    assert _proto_card("T319")["abilities"][0]["mod"] == {"battle_power": {"amount": 3000}}
    assert _proto_card("T320")["abilities"][0]["mod"] == {"battle_power": {"amount": 10000, "only": "attacking"}}
    assert _proto_card("T321")["free_if"] == {"cmp": [{"count": {"zone": "hand", "owner": "you"}}, "==", 1]}
    assert _proto_card("T322")["spell"][0]["op"] == "if"
    assert _proto_card("T323")["abilities"][0]["mod"]["grant"] == ["double_breaker"]


def _keys(d):
    return [o["key"] for o in d["options"]]


def _cid_ctrl(e, player, defn, zone="bz"):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _zone_of(e, defn):
    return next(c.zone for c in e.s.cards if c.defn == defn)


def _play_then_attack_options(e, tid, max_steps=200):
    """手札の tid を召喚してから攻撃ステップの選択肢を返す。"""
    played = False
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None
        keys = _keys(d)
        if d["kind"] == "attack" and d["player"] == 0:
            assert played
            return keys
        if d["kind"] == "main" and d["player"] == 0 and not played and f"play:{tid}" in keys:
            played = True
            e.answer([keys.index(f"play:{tid}")])
            continue
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")] if "no" in keys else [0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("attack step not reached")


def _attack_options(e, player, max_steps=60):
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None
        if d["kind"] == "attack" and d["player"] == player:
            return _keys(d)
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("attack step not reached")


def _to_attack(e):
    d = e.advance()
    while d["kind"] in ("charge", "main"):
        e.answer([_keys(d).index("pass")])
        d = e.advance()
    assert d["kind"] == "attack", d["kind"]
    return d


def _do_battle(e, key):
    """攻撃 key を実行し、次の charge / main / attack まで進める。"""
    d = _to_attack(e)
    e.answer([_keys(d).index(key)])
    d = e.advance()
    if d is not None and d["kind"] == "block":
        e.answer([_keys(d).index("no_block")])
        d = e.advance()
    while d is not None and d["kind"] not in ("charge", "main", "attack"):
        e.answer([0])
        d = e.advance()


def _main_options(e, max_steps=60):
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None
        if d["kind"] == "main" and d["player"] == 0:
            return _keys(d)
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("main step not reached")


def _cast(e, key, max_steps=200, main_check=None):
    """メインで key（play:...）を選び、解決が落ち着くまで進める。
    main_check があれば、最初のメイン決定の選択肢に呼ぶ（未回答の決定を
    別のドライバに跨がせないため、確認と実行は同じ周回で行う）。"""
    chosen = False
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None
        keys = _keys(d)
        if d["kind"] == "main" and d["player"] == 0 and not chosen:
            if main_check is not None:
                main_check(keys)
            if key in keys:
                chosen = True
                e.answer([keys.index(key)])
                continue
        if chosen and d["kind"] in ("charge", "main", "attack"):
            return
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")] if "no" in keys else [0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("cast did not settle")


def test_ggg_grants_speed_attacker_only_with_one_or_fewer_in_hand(rules):
    """T314: 手札1枚で召喚→そのターン攻撃できる。手札3枚で召喚→召喚酔い。
    攻撃不能だと攻撃ステップ自体が自動パスされるため、T005 を別に置いて
    ターン1の攻撃決定を必ず出させる。"""
    e = setup(rules, {"bz": ["T005"], "hand": ["T314"], "mana": ["T277"] * 3}, {})
    keys = _play_then_attack_options(e, "T314")
    assert "attack:T314:player" in keys
    e = setup(rules, {"bz": ["T005"], "hand": ["T314", "T001", "T001"], "mana": ["T277"] * 3}, {})
    keys = _play_then_attack_options(e, "T314")
    assert "attack:T314:player" not in keys
    assert "attack:T005:player" in keys


def test_ggg_attack_trigger_destroys_blocker_only_with_one_or_fewer_in_hand(rules):
    """T315: 手札1枚で攻撃→ブロッカーを破壊。手札2枚で攻撃→破壊しない。"""
    e = setup(rules, {"bz": ["T315"], "hand": ["T001"]}, {"bz": ["T004"]})
    _do_battle(e, "attack:T315:player")
    assert _zone_of(e, "T004") == "graveyard"
    e = setup(rules, {"bz": ["T315"], "hand": ["T001", "T001"]}, {"bz": ["T004"]})
    _do_battle(e, "attack:T315:player")
    assert _zone_of(e, "T004") == "bz"


def test_ggg_deny_attack_unless_one_or_fewer_in_hand(rules):
    """T316: 手札2枚では攻撃できない。手札1枚では攻撃できる。
    T005 を別に置いてターン1の攻撃決定を必ず出させる（T314 と同じ理由）。"""
    e = setup(rules, {"bz": ["T316", "T005"], "hand": ["T001", "T001"]}, {})
    keys = _attack_options(e, 0)
    assert "attack:T316:player" not in keys
    assert "attack:T005:player" in keys
    e = setup(rules, {"bz": ["T316", "T005"], "hand": ["T001"]}, {})
    keys = _attack_options(e, 0)
    assert "attack:T316:player" in keys
    assert "attack:T005:player" in keys


def _play_keys(e, player=0):
    """現在の状態で出せる実行選択肢のキー一覧（_play_options の直接照会）。
    出せないカードはメイン決定自体が自動パスされるため、決定を待たずに見る。"""
    with e.chars_scope():
        return [o["key"] for o in e._play_options(player)]


def test_ggg_race_cost_reduction_only_with_one_or_fewer_in_hand(rules):
    """T317: バトルゾーンの T317 が、手札1枚なら手札のテストのコストを2下げる。
    手札3枚なら軽減しない（マナ2枚では出せない）。軽減は発生源がバトルゾーンに
    いて affects: {zone: hand} で届く形（zone: hand は自分自身の軽減用で、
    群れへの軽減には使えない。T271 との対比）。"""
    e = setup(rules, {"bz": ["T317"], "hand": ["T317"], "mana": ["T277"] * 2}, {})
    assert "play:T317" in _play_keys(e)
    e = setup(rules, {"bz": ["T317"], "hand": ["T317", "T001", "T001"], "mana": ["T277"] * 2}, {})
    assert "play:T317" not in _play_keys(e)
    e = setup(rules, {"bz": ["T317"], "hand": ["T317", "T001", "T001"], "mana": ["T277"] * 4}, {})
    assert "play:T317" in _play_keys(e)


def test_ggg_battle_indestructible_only_with_one_or_fewer_in_hand(rules):
    """T318(2000): 手札1枚で T005(3000) に攻撃→破壊されない。手札2枚→破壊される。"""
    e = setup(rules, {"bz": ["T318"], "hand": ["T001"]}, {"bz": ["T005"]})
    # 共有ゾーン bz は controller 照合（第160弾の教訓）
    e.s.cards[_cid_ctrl(e, 1, "T005")].tapped = True
    _do_battle(e, "attack:T318:T005")
    assert _zone_of(e, "T318") == "bz"
    e = setup(rules, {"bz": ["T318"], "hand": ["T001", "T001"]}, {"bz": ["T005"]})
    e.s.cards[_cid_ctrl(e, 1, "T005")].tapped = True
    _do_battle(e, "attack:T318:T005")
    assert _zone_of(e, "T318") == "graveyard"


def test_ggg_battle_power_only_with_one_or_fewer_in_hand(rules):
    """T319(2000+3000): 手札1枚で T005(3000) を破壊。手札2枚では自分が破壊される。
    修正前（_battle_bonus が if を無視）だと対照実験でも T005 が破壊される。"""
    e = setup(rules, {"bz": ["T319"], "hand": ["T001"]}, {"bz": ["T005"]})
    e.s.cards[_cid_ctrl(e, 1, "T005")].tapped = True
    _do_battle(e, "attack:T319:T005")
    assert _zone_of(e, "T005") == "graveyard"
    assert _zone_of(e, "T319") == "bz"
    e = setup(rules, {"bz": ["T319"], "hand": ["T001", "T001"]}, {"bz": ["T005"]})
    e.s.cards[_cid_ctrl(e, 1, "T005")].tapped = True
    _do_battle(e, "attack:T319:T005")
    assert _zone_of(e, "T319") == "graveyard"
    assert _zone_of(e, "T005") == "bz"


def test_ggg_battle_power_only_attacking_not_defending(rules):
    """T320(2000+10000 only: attacking): 攻撃時は T005 を破壊するが、
    タップされて攻撃される側（防御側）では修整が付かず T005(3000) に破壊される。
    ブロッカーではないためブロックではなく「タップ状態で攻撃される」形で見る。"""
    e = setup(rules, {"bz": ["T320"], "hand": ["T001"]}, {"bz": ["T005"]})
    e.s.cards[_cid_ctrl(e, 1, "T005")].tapped = True
    _do_battle(e, "attack:T320:T005")
    assert _zone_of(e, "T005") == "graveyard"
    # 防御側: p0 のターン開始でアンタップされるため、最初の決定でタップし直す
    # （第160弾の種付けと同じ考え方）。タップされた T320 を p1 の T005 が攻撃する。
    e = setup(rules, {"bz": ["T320"], "hand": ["T001"]}, {"bz": ["T005"]})
    attacked = False
    seeded = False
    for _ in range(300):
        d = e.advance()
        assert d is not None
        keys = _keys(d)
        if not seeded:
            e.s.cards[_cid_ctrl(e, 0, "T320")].tapped = True
            seeded = True
        if d["kind"] == "attack" and d["player"] == 1 and "attack:T005:T320" in keys:
            e.answer([keys.index("attack:T005:T320")])
            attacked = True
            continue
        if attacked and d["kind"] in ("charge", "main", "attack"):
            break
        if d["kind"] == "block":
            e.answer([keys.index("no_block")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert attacked
    assert _zone_of(e, "T320") == "graveyard"
    assert _zone_of(e, "T005") == "bz"


def test_master_ggg_free_if_only_with_this_card_in_hand(rules):
    """T321: 手札がこの呪文だけなら free_if で無料で唱えられる（マナはタップされない）。
    手札2枚なら無料選択肢は出ない。呪文の free_if が選択肢に出るのは
    本弾の turn.py 修正による（従来はクリーチャーのみ）。"""
    e = setup(rules, {"hand": ["T321"], "mana": ["T277"] * 6}, {"bz": ["T004"]})
    assert "play:T321:free" in _play_keys(e)

    def _free_offered(keys):
        assert "play:T321:free" in keys

    _cast(e, "play:T321:free", main_check=_free_offered)
    assert _zone_of(e, "T004") == "graveyard"
    assert all(not e.s.cards[c].tapped for c in e.zlist("mana", 0))
    e = setup(rules, {"hand": ["T321", "T001"], "mana": ["T277"] * 6}, {"bz": ["T004"]})
    keys = _play_keys(e)
    assert "play:T321:free" not in keys
    assert "play:T321" in keys


def test_ggg_spell_branch_all_or_one(rules):
    """T322: 手札1枚（解決時0枚）なら相手のパワー5000以下をすべて破壊。
    手札3枚（解決時2枚）なら1体だけ破壊する。"""
    e = setup(rules, {"hand": ["T322"], "mana": ["T277"] * 4}, {"bz": ["T004", "T005"]})
    _cast(e, "play:T322")
    assert _zone_of(e, "T004") == "graveyard"
    assert _zone_of(e, "T005") == "graveyard"
    e = setup(rules, {"hand": ["T322", "T001", "T001"], "mana": ["T277"] * 4}, {"bz": ["T004", "T005"]})
    _cast(e, "play:T322")
    dead = [_zone_of(e, d) == "graveyard" for d in ("T004", "T005")]
    assert sum(dead) == 1


def test_ggg_power_attacker_and_double_breaker_grant(rules):
    """T323: 手札1枚なら攻撃中パワー+5000（T005 を破壊）かつ W・ブレイカー。
    手札2枚ならどちらも付かない。"""
    e = setup(rules, {"bz": ["T323"], "hand": ["T001"]}, {"bz": ["T005"]})
    assert e.chars(_cid_ctrl(e, 0, "T323"))["breaks"] == 2
    e.s.cards[_cid_ctrl(e, 1, "T005")].tapped = True
    _do_battle(e, "attack:T323:T005")
    assert _zone_of(e, "T005") == "graveyard"
    e = setup(rules, {"bz": ["T323"], "hand": ["T001", "T001"]}, {"bz": ["T005"]})
    assert e.chars(_cid_ctrl(e, 0, "T323"))["breaks"] == 1
    e.s.cards[_cid_ctrl(e, 1, "T005")].tapped = True
    _do_battle(e, "attack:T323:T005")
    assert _zone_of(e, "T323") == "graveyard"
