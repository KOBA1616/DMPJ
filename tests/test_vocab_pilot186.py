"""語彙パイロット第186弾: super_guardman（スーパーガードマン）。

「スーパーガードマン（自分の他のクリーチャーがバトルする時、かわりにこのクリーチャー
をタップしてバトルさせてもよい）」。土台は既存のバトル相手の置換（combat の
_battle_substitute: when: {event: battle} の置換効果を攻撃フロー ph 3 で諮る）で、
新語彙は battle_substitute op の tap: true だけ。tap が真の置換は、代わりにバトルする
クリーチャーをタップし（タップ済みでは選択肢に出ない）、タップにイベントは出さない
（第171弾のリダイレクトのアンタップ・コストと同じ扱い）。

カードの型: {kind: replace,
  when: {event: battle, subject: {owner: you, filter: {types: [creature]}, other: true}},
  instead: [{op: battle_substitute, tap: true}]}
subject の other: true が「他のクリーチャー」（自分自身を除く）、owner: you が
「自分の」を表す。_battle_substitute は置き換えられる側のコントローラーのバトル
ゾーンだけを走査するため、相手のガードマンが自分のクリーチャーを守ることはない。

制限: 効果によるバトル（op force_battle）は _battle_substitute を通らないため、
スーパーガードマンは働かない（vocab-pilot.md 冒頭の既知の注記どおり）。
"""
from pathlib import Path

import yaml
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    for cid in ("T441", "T442", "T443", "T444", "T445"):
        card = parse_card(_proto_card(cid), TABLES)
        reps = [a for a in card.abilities if a["kind"] == "replace"]
        assert len(reps) == 1, (cid, card.abilities)
        ab = reps[0]
        assert ab["when"] == {"event": "battle",
                              "subject": {"owner": "you", "filter": {"types": ["creature"]},
                                          "other": True}}
        assert ab["instead"] == [{"op": "battle_substitute", "tap": True}]
    t443 = parse_card(_proto_card("T443"), TABLES)
    assert "double_breaker" in t443.keywords
    t444 = parse_card(_proto_card("T444"), TABLES)
    assert "cannot_attack" in t444.keywords


def test_invalid_forms():
    base = {"id": "test-sg-bad", "name": "試験守護獣不良", "types": ["creature"],
            "civs": ["nature"], "cost": 3, "power": 2000,
            "source": {"official": "test-sg-bad", "review": "pending"}}
    bads = [
        {"kind": "replace",
         "when": {"event": "battle", "subject": {"owner": "you", "filter": {"types": ["creature"]}, "other": True}},
         "instead": [{"op": "battle_substitute", "tap": "yes"}]},
        {"kind": "replace",
         "when": {"event": "battle", "subject": {"owner": "you", "filter": {"types": ["creature"]}, "other": True}},
         "instead": [{"op": "battle_substitute", "tap": True, "other": 1}]},
    ]
    for bad in bads:
        card = {**base, "abilities": [bad]}
        try:
            parse_card(card, TABLES)
            raise AssertionError(f"should have raised: {bad}")
        except Exception as e:
            assert "battle_substitute" in str(e)


def _cid_ctrl(e, player, defn):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _tap(e, player, defn):
    """bz は共有ゾーンなので、コントローラーまで見て対象側のカードをタップする。"""
    c = _cid_ctrl(e, player, defn)
    e.s.cards[c].tapped = True


def _drive_attack(e, atk_key, sub_keys=(), block_prefix=None, max_steps=300):
    """既定回答で進め、atk_key の攻撃を1回実行し、攻撃が終わった後の次の決定を返す。

    sub_keys は使う置換の key の列（現れた順に使う。無ければ decline）。
    block_prefix があればブロック決定でその接頭辞の選択肢を選ぶ（無ければ no_block）。
    戻り値: (次の決定, 現れた choose_replacement 決定の列, 現れた決定種別の列)。
    攻撃後に攻撃できるクリーチャーが残っていれば次の攻撃決定が同じターンに出るため、
    呼び出し側は T007 のような2体目の攻撃者を置いておくこと。そうしないと次の決定は
    翌ターンの charge になり、ターン開始アンタップで置換のタップが見えなくなる。
    """
    sub_keys = list(sub_keys)
    subs = []
    seen = []
    started = False
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        seen.append(d["kind"])
        if started and not any(t.get("t") == "attack" for t in e.s.tasks):
            return d, subs, seen
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and d["player"] == 0:
            assert not started
            assert atk_key in keys, f"{atk_key} not in {keys}"
            e.answer([keys.index(atk_key)])
            started = True
            continue
        if d["kind"] == "choose_replacement":
            subs.append(d)
            key = sub_keys[0] if sub_keys else None
            if key is not None and key in keys:
                sub_keys.pop(0)
                e.answer([keys.index(key)])
            else:
                e.answer([keys.index("decline")])
            continue
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "block":
            if block_prefix is not None:
                hit = [i for i, k in enumerate(keys) if k.startswith(block_prefix)]
                assert hit, f"no block option with prefix {block_prefix} in {keys}"
                e.answer([hit[0]])
            else:
                e.answer([keys.index("no_block")])
        else:
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("attack did not finish")


def _drive_two_attacks(e, plan, max_steps=600):
    """plan（(atk_key, sub_keys, block_prefix) の列）の攻撃を順に実行する。

    各攻撃の終わりに次の攻撃決定が出たら次の plan を答え、plan が尽きたらその決定で
    止まる。戻り値: (止まった決定, 現れた choose_replacement 決定の列)。
    """
    plan = [[p[0], list(p[1]), p[2] if len(p) > 2 else None] for p in plan]
    subs = []
    current = None
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and d["player"] == 0:
            if not plan:
                return d, subs
            current = plan.pop(0)
            atk_key = current[0]
            assert atk_key in keys, f"{atk_key} not in {keys}"
            e.answer([keys.index(atk_key)])
            continue
        if d["kind"] == "choose_replacement":
            subs.append(d)
            sub_keys = current[1] if current else []
            key = sub_keys[0] if sub_keys else None
            if key is not None and key in keys:
                sub_keys.pop(0)
                e.answer([keys.index(key)])
            else:
                e.answer([keys.index("decline")])
            continue
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "block":
            bp = current[2] if current else None
            if bp is not None:
                hit = [i for i, k in enumerate(keys) if k.startswith(bp)]
                assert hit, f"no block option with prefix {bp} in {keys}"
                e.answer([hit[0]])
            else:
                e.answer([keys.index("no_block")])
        else:
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("attacks did not finish")


def test_guard_substitutes_when_own_attacked(rules):
    """自分のクリーチャーが攻撃された時、ガードマンがタップしてかわりにバトルする。"""
    e = setup(rules, {"bz": ["T010", "T007"]}, {"bz": ["T001", "T441"]})
    _tap(e, 1, "T001")   # 505.2: 直接攻撃できるのはタップ状態のクリーチャーだけ
    t010 = _cid_ctrl(e, 0, "T010")
    t001 = _cid_ctrl(e, 1, "T001")
    t441 = _cid_ctrl(e, 1, "T441")
    d, subs, _ = _drive_attack(e, "attack:T010:T001", ["battle_sub:T441:0"])
    assert d["kind"] == "attack", "T007 が残るため次の攻撃決定が同じターンに出る"
    assert len(subs) == 1
    assert [o["key"] for o in subs[0]["options"]] == ["battle_sub:T441:0", "decline"]
    assert e.s.cards[t010].zone == "graveyard", "T010（4000）は T441（8000）とのバトルで破壊される"
    assert e.s.cards[t001].zone == "bz", "守られた T001 は残る"
    assert e.s.cards[t441].zone == "bz"
    assert e.s.cards[t441].tapped, "置換でタップされている"


def test_guard_declined(rules):
    """断れば置換は起きず、元のクリーチャーがバトルする。"""
    e = setup(rules, {"bz": ["T010"]}, {"bz": ["T001", "T441"]})
    _tap(e, 1, "T001")   # 505.2: 直接攻撃できるのはタップ状態のクリーチャーだけ
    t010 = _cid_ctrl(e, 0, "T010")
    t001 = _cid_ctrl(e, 1, "T001")
    t441 = _cid_ctrl(e, 1, "T441")
    d, subs, _ = _drive_attack(e, "attack:T010:T001")
    assert len(subs) == 1
    assert e.s.cards[t001].zone == "graveyard", "T001（2000）は T010（4000）に負ける"
    assert e.s.cards[t010].zone == "bz"
    assert not e.s.cards[t441].tapped, "使わなかったガードマンはタップされない"


def test_guard_substitutes_when_own_attacks_blocked(rules):
    """自分のクリーチャーが攻撃してブロックされた時も、ガードマンがかわりにバトルする。"""
    e = setup(rules, {"bz": ["T005", "T441"]}, {"bz": ["T004"]})
    t005 = _cid_ctrl(e, 0, "T005")
    t004 = _cid_ctrl(e, 1, "T004")
    t441 = _cid_ctrl(e, 0, "T441")
    d, subs, _ = _drive_attack(e, "attack:T005:player", ["battle_sub:T441:0"],
                               block_prefix="bz:T004")
    assert len(subs) == 1
    assert e.s.cards[t004].zone == "graveyard", "T004（3000）は T441（8000）とのバトルで破壊される"
    assert e.s.cards[t005].zone == "bz", "攻撃した T005 は残る"
    assert e.s.cards[t441].tapped, "置換でタップされている"


def test_tapped_guard_cannot_substitute(rules):
    """タップ済みのガードマンは置換の選択肢に出ない。"""
    e = setup(rules, {"bz": ["T010", "T007"]}, {"bz": ["T001", "T441"]})
    _tap(e, 1, "T001")   # 505.2: 直接攻撃できるのはタップ状態のクリーチャーだけ
    _tap(e, 1, "T441")
    t001 = _cid_ctrl(e, 1, "T001")
    t441 = _cid_ctrl(e, 1, "T441")
    d, subs, _ = _drive_attack(e, "attack:T010:T001")
    assert d["kind"] == "attack", "T007 が残るため次の攻撃決定が同じターンに出る"
    assert subs == [], "タップ済みでは choose_replacement が出ない"
    assert e.s.cards[t001].zone == "graveyard"
    assert e.s.cards[t441].tapped


def test_guard_does_not_protect_opponents_creature(rules):
    """相手のクリーチャーが攻撃される時、自分のガードマンは置換に出ない。

    攻撃側（自分の T010）の置換は諮られるが、断れば防御側（相手の T001）の置換は
    出ない（自分のガードマンは自分のクリーチャーしか守らない）。
    """
    e = setup(rules, {"bz": ["T010", "T441"]}, {"bz": ["T001"]})
    _tap(e, 1, "T001")   # 505.2: 直接攻撃できるのはタップ状態のクリーチャーだけ
    t010 = _cid_ctrl(e, 0, "T010")
    t001 = _cid_ctrl(e, 1, "T001")
    t441 = _cid_ctrl(e, 0, "T441")
    d, subs, _ = _drive_attack(e, "attack:T010:T001")
    assert len(subs) == 1, "攻撃側の置換だけが諮られる"
    assert e.s.cards[t001].zone == "graveyard"
    assert e.s.cards[t010].zone == "bz"
    assert not e.s.cards[t441].tapped


def test_two_guardmen_choose_one(rules):
    """ガードマンが2体いればどちらで置換するか選べる。選ばれなかった方は残る。"""
    e = setup(rules, {"bz": ["T010", "T007"]}, {"bz": ["T001", "T441", "T442"]})
    _tap(e, 1, "T001")   # 505.2: 直接攻撃できるのはタップ状態のクリーチャーだけ
    t010 = _cid_ctrl(e, 0, "T010")
    t001 = _cid_ctrl(e, 1, "T001")
    t441 = _cid_ctrl(e, 1, "T441")
    t442 = _cid_ctrl(e, 1, "T442")
    d, subs, _ = _drive_attack(e, "attack:T010:T001", ["battle_sub:T442:0"])
    assert len(subs) == 1
    keys = [o["key"] for o in subs[0]["options"]]
    assert keys == ["battle_sub:T441:0", "battle_sub:T442:0", "decline"]
    assert e.s.cards[t442].zone == "graveyard", "T442（2000）は T010（4000）に負ける"
    assert e.s.cards[t010].zone == "bz"
    assert e.s.cards[t001].zone == "bz", "守られた T001 は残る"
    assert e.s.cards[t441].zone == "bz"
    assert not e.s.cards[t441].tapped, "選ばれなかったガードマンはタップされない"
    # 置換した T442 はバトルで破壊され、ゾーン移動でタップ印は消える（置換時のタップは
    # test_guardman_tapped_by_first_battle_cannot_substitute_again で機能的に検証する）


def test_guardman_itself_cannot_substitute_for_itself(rules):
    """ガードマン自身が攻撃される時、自身では置換できない（other: true）。

    T441 だけが防御側にいる状態で T441 を攻撃すると、choose_replacement は出ない。
    """
    e = setup(rules, {"bz": ["T010"]}, {"bz": ["T441"]})
    _tap(e, 1, "T441")   # 505.2: 直接攻撃できるのはタップ状態のクリーチャーだけ
    t010 = _cid_ctrl(e, 0, "T010")
    t441 = _cid_ctrl(e, 1, "T441")
    d, subs, _ = _drive_attack(e, "attack:T010:T441")
    assert subs == [], "自分自身の置換は出ない"
    assert e.s.cards[t441].zone == "bz", "T441（8000）は T010（4000）に勝つ"
    assert e.s.cards[t010].zone == "graveyard"
    assert not e.s.cards[t441].tapped


def test_guardman_tapped_by_first_battle_cannot_substitute_again(rules):
    """置換でタップされたガードマンは、同じターンの2回目のバトルでは置換に出ない。

    1回目: T010 が T001 を攻撃し、T441 がかわりにバトルして T010 を破壊する。
    2回目: T007 が T008 を攻撃する時、T441 はタップ済みのため choose_replacement は
    出ず、T008 がそのままバトルする。
    """
    e = setup(rules, {"bz": ["T010", "T007"]}, {"bz": ["T001", "T008", "T441"]})
    _tap(e, 1, "T001")   # 505.2: 直接攻撃できるのはタップ状態のクリーチャーだけ
    _tap(e, 1, "T008")
    t010 = _cid_ctrl(e, 0, "T010")
    t007 = _cid_ctrl(e, 0, "T007")
    t001 = _cid_ctrl(e, 1, "T001")
    t008 = _cid_ctrl(e, 1, "T008")
    t441 = _cid_ctrl(e, 1, "T441")
    d, subs = _drive_two_attacks(e, [
        ("attack:T010:T001", ["battle_sub:T441:0"]),
        ("attack:T007:T008", []),
    ])
    assert len(subs) == 1, "2回目の攻撃では置換が出ない"
    assert e.s.cards[t010].zone == "graveyard"
    assert e.s.cards[t001].zone == "bz", "1回目で守られた T001 は残る"
    assert e.s.cards[t008].zone == "graveyard", "T008（1000）は T007（2000）に負ける"
    assert e.s.cards[t007].zone == "bz"
