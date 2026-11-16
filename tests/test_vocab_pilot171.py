"""語彙パイロット第171弾: attack_redirect（攻撃先の変更）。

2つの型がある。

(1) 起動型（青守銀モルゲン型）: 「このクリーチャーをアンタップして、相手クリーチ
ャーの攻撃先をこのクリーチャーまたは自分のタップしているクリーチャーに変更しても
よい。」activate 能力の cost に {untap: self | <filter>} を追加し、能力に
redirect: true | {include_cost?: bool} を持たせる。攻撃タスクのブロック前（ph 2
開始時）に防御側へ諮問し、選ばれればコスト（アンタップ）を払って攻撃先を変更し、
もう一度諮問する（別のクリーチャーの変更も使える）。断ればブロックへ進む。
新しい攻撃先は、コストのクリーチャー（include_cost が真の時）と自分のタップして
いるクリーチャー。dmr23-s01 型は include_cost: false（コストのクリーチャー自身は
対象にならない）、dmrp10-s02 型は untap: {types: [creature], tapped: true}
（自分のタップしているクリーチャー1体をコストにする）。
attack_on の履歴は宣言時のまま書き換えない（ブロック／ガードマンと同じ既定）。

(2) 「可能なら」型: 「相手のクリーチャーが攻撃する時、そのクリーチャーは可能なら
このクリーチャーを攻撃する」は第51弾の mod must_be_attacked: true で表す
（dmx17-s03）。「このクリーチャーがタップされていて」は常在型の if
{exists: {ref: self, filter: {tapped: true}}} を足す（dmx22a-005）。
「各ターン、相手のクリーチャーがはじめて攻撃する時、可能ならクリーチャーを攻撃する」
（dm25ex4-s05。対象は任意のクリーチャー）は新 mod
must_attack_creature: true | {first_only: true} で表す。攻撃側の特性として集約し、
攻撃できるクリーチャーがいればプレイヤーへの攻撃選択肢を落とす。first_only は
第160弾と同じく攻撃側クリーチャー単位の初回攻撃だけ（dm26sd1-m001 の先例）。
"""
from pathlib import Path

import yaml
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    t357 = parse_card(_proto_card("T357"), TABLES)
    assert t357.abilities[0]["cost"] == {"untap": "self"}
    assert t357.abilities[0]["redirect"] is True
    t358 = parse_card(_proto_card("T358"), TABLES)
    assert t358.abilities[0]["redirect"] == {"include_cost": False}
    t359 = parse_card(_proto_card("T359"), TABLES)
    assert t359.abilities[0]["cost"] == {"untap": {"types": ["creature"], "tapped": True}}
    t360 = parse_card(_proto_card("T360"), TABLES)
    assert "if" in t360.abilities[0] and t360.abilities[0]["redirect"] is True
    t361 = parse_card(_proto_card("T361"), TABLES)
    assert t361.abilities[0]["mod"]["must_be_attacked"] is True
    t362 = parse_card(_proto_card("T362"), TABLES)
    assert t362.abilities[0]["mod"]["must_be_attacked"] is True
    assert "if" in t362.abilities[0]
    t363 = parse_card(_proto_card("T363"), TABLES)
    assert t363.abilities[0]["mod"]["must_attack_creature"] == {"first_only": True}
    t364 = parse_card(_proto_card("T364"), TABLES)
    assert t364.abilities[0]["mod"]["must_attack_creature"] is True


def test_invalid_forms():
    base = {"id": "test-ar-bad", "name": "試験転移獣不良", "types": ["creature"],
            "civs": ["light"], "cost": 3, "power": 2000,
            "source": {"official": "test-ar-bad", "review": "pending"}}
    bad_redirects = ({"include_cost": "yes"}, {"other": True}, "yes", 1)
    for bad in bad_redirects:
        card = {**base, "abilities": [{"kind": "activate", "cost": {"untap": "self"},
                                       "redirect": bad}]}
        try:
            parse_card(card, TABLES)
            raise AssertionError(f"should have raised: {bad}")
        except Exception as e:
            assert "redirect" in str(e)
    bad_macs = ({"first_only": False}, {"other": True}, "yes", 1)
    for bad in bad_macs:
        card = {**base, "abilities": [{"kind": "static", "affects": "self",
                                       "mod": {"must_attack_creature": bad}}]}
        try:
            parse_card(card, TABLES)
            raise AssertionError(f"should have raised: {bad}")
        except Exception as e:
            assert "must_attack_creature" in str(e)
    bad_activates = [
        # untap と tap の併用は不可
        {"kind": "activate", "cost": {"untap": "self", "tap": "self"}, "redirect": True},
        # redirect と effect の併用は不可
        {"kind": "activate", "cost": {"untap": "self"}, "redirect": True,
         "effect": [{"op": "draw", "count": 1}]},
        # untap コストには redirect が要る
        {"kind": "activate", "cost": {"untap": "self"},
         "effect": [{"op": "draw", "count": 1}]},
        # redirect には untap コストが要る（tap コスト＋effect 無しも不可）
        {"kind": "activate", "cost": {"tap": "self"}, "redirect": True},
        # untap の値は self かフィルタだけ
        {"kind": "activate", "cost": {"untap": 1}, "redirect": True},
    ]
    for bad in bad_activates:
        card = {**base, "abilities": [bad]}
        try:
            parse_card(card, TABLES)
            raise AssertionError(f"should have raised: {bad}")
        except Exception as e:
            assert "untap" in str(e) or "redirect" in str(e) or "effect" in str(e)


def _attack_options(e, player, seed=None):
    """指定プレイヤーの攻撃ステップの決定まで進め、選択肢（辞書）の一覧を返す。

    seed があれば、ターン開始のカウンタ初期化が終わった後の最初の決定で一度だけ呼ぶ
    （履歴カウンタはターン開始でリセットされるため、setup 直後の種付けは消える）。
    """
    seeded = seed is None
    for _ in range(60):
        d = e.advance()
        assert d is not None
        if d["kind"] == "attack" and d["player"] == player:
            assert seeded, "attack decision reached before seeding"
            return d["options"]
        if not seeded:
            seed()
            seeded = True
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("attack step not reached")


def _drive_attack(e, atk_key, redirect_keys=(), max_steps=300):
    """既定回答で進め、atk_key の攻撃を1回実行し、攻撃が終わった後の次の決定を返す。

    redirect_keys は使うリダイレクトの key の列（現れた順に使う。無ければ decline）。
    戻り値: (次の決定, 現れた redirect 決定の列, 現れた決定種別の列)。
    攻撃タスクがスタックから消えた時点で攻撃終了とみなす（攻撃者がタップされて次の
    攻撃判断が出ない場合も、そこで止まる）。
    """
    redirect_keys = list(redirect_keys)
    redirects = []
    seen = []
    started = False
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        seen.append(d["kind"])
        if started and not any(t.get("t") == "attack" for t in e.s.tasks):
            return d, redirects, seen
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and d["player"] == 0:
            assert not started
            assert atk_key in keys, f"{atk_key} not in {keys}"
            e.answer([keys.index(atk_key)])
            started = True
            continue
        if d["kind"] == "redirect":
            redirects.append(d)
            key = redirect_keys[0] if redirect_keys else None
            if key is not None and key in keys:
                redirect_keys.pop(0)
                e.answer([keys.index(key)])
            else:
                e.answer([keys.index("decline")])
            continue
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        else:
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("attack did not finish")


def _tap(e, player, defn):
    """bz は共有ゾーンなので、コントローラーまで見て対象側のカードをタップする。"""
    for c in e.zlist("bz", player):
        if e.s.cards[c].defn == defn and e.s.cards[c].controller == player:
            e.s.cards[c].tapped = True
            return
    raise AssertionError(defn)


def _tap_all(e, player, defn):
    """同じ defn のカードをすべてタップする。"""
    found = False
    for c in e.zlist("bz", player):
        if e.s.cards[c].defn == defn and e.s.cards[c].controller == player:
            e.s.cards[c].tapped = True
            found = True
    assert found, defn


def _cid(e, player, defn, nth=0):
    return [c for c in e.zlist("bz", player) if e.s.cards[c].defn == defn][nth]


def _cid_ctrl(e, player, defn):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def test_redirect_to_self(rules):
    """自分自身へ変更: コストでアンタップした T357 が攻撃先になり、バトルが行われる。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T357"]})
    _tap(e, 1, "T357")
    t357 = _cid_ctrl(e, 1, "T357")
    t005 = _cid_ctrl(e, 0, "T005")
    d, redirects, _ = _drive_attack(e, "attack:T005:player",
                                    ["redirect:T357:0:T357:T357"])
    assert len(redirects) == 1
    assert e.s.cards[t005].zone == "graveyard", "T005（3000）は T357（4000）とのバトルで破壊される"
    assert e.s.cards[t357].zone == "bz"
    assert not e.s.cards[t357].tapped, "コストのアンタップが実際に起きている"


def test_redirect_to_tapped_other(rules):
    """タップしている他のクリーチャーへ変更: T357 はアンタップして残り、T001 がバトルで破壊される。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T357", "T001"]})
    _tap(e, 1, "T357")
    _tap(e, 1, "T001")
    t357 = _cid_ctrl(e, 1, "T357")
    t001 = _cid_ctrl(e, 1, "T001")
    t005 = _cid_ctrl(e, 0, "T005")
    _, redirects, _ = _drive_attack(e, "attack:T005:player",
                                    ["redirect:T357:0:T357:T001"])
    assert len(redirects) == 1
    assert e.s.cards[t001].zone == "graveyard", "攻撃先になった T001（2000）が破壊される"
    assert e.s.cards[t357].zone == "bz" and not e.s.cards[t357].tapped
    assert e.s.cards[t005].zone == "bz", "T005（3000）はバトルに勝って残る"


def test_redirect_loop_two_redirects(rules):
    """1回の攻撃で2体の変更を使える: T357 で自分へ、さらに T358 で T001 へ。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T357", "T358", "T001"]})
    _tap(e, 1, "T357")
    _tap(e, 1, "T358")
    _tap(e, 1, "T001")
    t357 = _cid_ctrl(e, 1, "T357")
    t358 = _cid_ctrl(e, 1, "T358")
    t001 = _cid_ctrl(e, 1, "T001")
    _, redirects, _ = _drive_attack(e, "attack:T005:player",
                                    ["redirect:T357:0:T357:T357",
                                     "redirect:T358:0:T358:T001"])
    assert len(redirects) == 2, "2回目の諮問が出る"
    assert e.s.cards[t001].zone == "graveyard", "最終的な攻撃先は T001"
    assert not e.s.cards[t357].tapped and not e.s.cards[t358].tapped
    assert e.s.cards[t357].zone == "bz" and e.s.cards[t358].zone == "bz"


def test_redirect_not_offered_when_untapped(rules):
    """タップしていない T357 はコストを払えないので、redirect の決定自体が出ない。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T357", "T001"]})
    _tap(e, 1, "T001")
    t357 = _cid_ctrl(e, 1, "T357")
    _, _, seen = _drive_attack(e, "attack:T005:player")
    assert "redirect" not in seen
    assert not e.s.cards[t357].tapped


def test_redirect_include_cost_false_no_target(rules):
    """T358（include_cost: false）は、他にタップしているクリーチャーが無ければ使えない。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T358", "T001"]})
    _tap(e, 1, "T358")
    _, _, seen = _drive_attack(e, "attack:T005:player")
    assert "redirect" not in seen


def test_redirect_include_cost_false_only_other(rules):
    """T358 の攻撃先は自分のタップしているクリーチャーだけで、自身は選べない。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T358", "T001"]})
    _tap(e, 1, "T358")
    _tap(e, 1, "T001")
    t358 = _cid_ctrl(e, 1, "T358")
    t001 = _cid_ctrl(e, 1, "T001")
    _, redirects, _ = _drive_attack(e, "attack:T005:player",
                                    ["redirect:T358:0:T358:T001"])
    assert len(redirects) == 1
    keys = [o["key"] for o in redirects[0]["options"]]
    assert keys == ["redirect:T358:0:T358:T001", "decline"], keys
    assert e.s.cards[t001].zone == "graveyard"
    assert e.s.cards[t358].zone == "bz" and not e.s.cards[t358].tapped


def test_redirect_filter_cost(rules):
    """T359 は自分のタップしているクリーチャー1体をコストにする（自身でなくてもよい）。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T359", "T001"]})
    _tap(e, 1, "T359")
    _tap(e, 1, "T001")
    t359 = _cid_ctrl(e, 1, "T359")
    t001 = _cid_ctrl(e, 1, "T001")
    t005 = _cid_ctrl(e, 0, "T005")
    _, redirects, _ = _drive_attack(e, "attack:T005:player",
                                    ["redirect:T359:0:T001:T359"])
    # T001 をコストに使った後も T359 自身がタップしているので、もう一度諮問が出る（断る）
    assert len(redirects) == 2
    keys2 = [o["key"] for o in redirects[1]["options"]]
    assert keys2 == ["redirect:T359:0:T359:T359", "decline"], keys2
    assert not e.s.cards[t001].tapped, "コストにした T001 がアンタップしている"
    assert e.s.cards[t001].zone == "bz"
    assert e.s.cards[t005].zone == "graveyard", "T005（3000）は T359（6000）とのバトルで破壊される"
    assert e.s.cards[t359].zone == "bz"


def test_redirect_condition_false(rules):
    """T360 は自分のクリーチャー数が相手より多くなければ使えない（1体 vs 1体）。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T360"]})
    _tap(e, 1, "T360")
    _, _, seen = _drive_attack(e, "attack:T005:player")
    assert "redirect" not in seen


def test_redirect_condition_true(rules):
    """T360 は自分のクリーチャー数が相手より多ければ使える（2体 vs 1体）。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T360", "T001"]})
    _tap(e, 1, "T360")
    _tap(e, 1, "T001")
    t360 = _cid_ctrl(e, 1, "T360")
    t001 = _cid_ctrl(e, 1, "T001")
    _, redirects, _ = _drive_attack(e, "attack:T005:player",
                                    ["redirect:T360:0:T360:T001"])
    assert len(redirects) == 1
    assert e.s.cards[t001].zone == "graveyard"
    assert e.s.cards[t360].zone == "bz" and not e.s.cards[t360].tapped


def test_taunt(rules):
    """T361（dmx17-s03型）: タップしていれば、攻撃先は T361 に限られる。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T361", "T001"]})
    _tap(e, 1, "T361")
    _tap(e, 1, "T001")
    keys = [o["key"] for o in _attack_options(e, 0)]
    attacks = [k for k in keys if k.startswith("attack:")]
    assert attacks == ["attack:T005:T361"]


def test_tapped_taunt(rules):
    """T362（dmx22a-005型）: タップしている時だけ誘引し、アンタップ時は制限しない。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T362", "T001"]})
    _tap(e, 1, "T362")
    _tap(e, 1, "T001")
    keys = [o["key"] for o in _attack_options(e, 0)]
    attacks = [k for k in keys if k.startswith("attack:")]
    assert attacks == ["attack:T005:T362"]
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T362", "T001"]})
    _tap(e, 1, "T001")
    keys = [o["key"] for o in _attack_options(e, 0)]
    attacks = sorted(k for k in keys if k.startswith("attack:"))
    assert attacks == ["attack:T005:T001", "attack:T005:player"]


def test_must_attack_creature_first_only(rules):
    """T363（dm25ex4-s05型）: 初回攻撃は、攻撃できるクリーチャーがいればプレイヤーを攻撃できない。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T363", "T001", "T001"]})
    _tap_all(e, 1, "T001")
    keys = [o["key"] for o in _attack_options(e, 0)]
    attacks = [k for k in keys if k.startswith("attack:")]
    assert attacks == ["attack:T005:T001", "attack:T005:T001"]
    assert "attack:T005:player" not in attacks


def test_must_attack_creature_first_only_after_attack(rules):
    """T363: 一度攻撃したクリーチャーの次の攻撃は制限されない（履歴カウンタの種付けで確認）。"""
    e = setup(rules, {"bz": ["T005"], "hand": ["T001"]}, {"bz": ["T363", "T001", "T001"]})
    _tap_all(e, 1, "T001")
    att = _cid(e, 0, "T005")

    def seed():
        e.s.turn_counters[f"hist:attack_by:{att}"] = 1

    keys = [o["key"] for o in _attack_options(e, 0, seed=seed)]
    attacks = sorted(k for k in keys if k.startswith("attack:"))
    assert "attack:T005:player" in attacks
    assert attacks == ["attack:T005:T001", "attack:T005:T001", "attack:T005:player"]


def test_must_attack_creature_first_only_per_attacker(rules):
    """T363 の制限はクリーチャー単位: 別のクリーチャーが先に攻撃しても、まだ攻撃して
    いないクリーチャーの初回攻撃は制限される（実戦で確認）。"""
    e = setup(rules, {"bz": ["T001", "T005"]}, {"bz": ["T363", "T001", "T001"]})
    _tap_all(e, 1, "T001")
    t001 = _cid_ctrl(e, 0, "T001")
    d, _, _ = _drive_attack(e, "attack:T001:T001")
    assert e.s.cards[t001].zone == "graveyard", "T001（2000）は T001（2000）とのバトルで破壊される"
    keys = [o["key"] for o in d["options"]]
    attacks = [k for k in keys if k.startswith("attack:")]
    assert attacks == ["attack:T005:T001"], attacks
    assert "attack:T005:player" not in attacks


def test_must_attack_creature_plain(rules):
    """T364（常時形）: 一度攻撃した後も、攻撃できるクリーチャーがいればプレイヤーを攻撃できない。"""
    e = setup(rules, {"bz": ["T005"], "hand": ["T001"]}, {"bz": ["T364", "T001", "T001"]})
    _tap_all(e, 1, "T001")
    att = _cid(e, 0, "T005")

    def seed():
        e.s.turn_counters[f"hist:attack_by:{att}"] = 1

    keys = [o["key"] for o in _attack_options(e, 0, seed=seed)]
    attacks = sorted(k for k in keys if k.startswith("attack:"))
    assert attacks == ["attack:T005:T001", "attack:T005:T001"]
    assert "attack:T005:player" not in attacks


def test_must_attack_creature_no_option(rules):
    """T363: 攻撃できるクリーチャーが無ければ「可能なら」は不成立で、プレイヤーを攻撃できる。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T363", "T001"]})
    keys = [o["key"] for o in _attack_options(e, 0)]
    attacks = [k for k in keys if k.startswith("attack:")]
    assert attacks == ["attack:T005:player"]
