"""語彙パイロット第280弾: battle_does_not_occur_when_blocked
（ブロックされた場合、バトルは行われない）。

rejects の battle_does_not_occur_when_blocked 純粋3件:
- dm06-032 ピーカプ・リザード（パワーアタッカー +3000）
- dm06-101 無謀鉄人チョイヤ（パワーアタッカー +1000）
- dm19-s02 護法の精霊アムシオン（任意形＋「攻撃していない時」パワー）
3件とも不足は「ブロックされたらバトルを行わない」条項（dm19-s02 は
加えて第1条項の「攻撃していない時」条件）だけ。

本弾の語彙:
- イディオム（強制形）: 誘発 {when: {event: block, attacker: self},
  effect: [{op: cancel_attack}]}。when の attacker 照合は既存
  （dm08-033 シェル・コロシアムが「ブロックされたとき」に使用）、
  cancel_attack は第251弾の op。ブロック宣言のタップは両者とも
  済んでおり、h_attack は再開時に cancelled を見てバトルもブレイクも
  せず attack_end を出すため、原文「両クリーチャーはタップしたまま」
  まで一致する。ガードマンはブロックではない（507.2b）ので block
  イベント自体が出ず、バトルは通常どおり行われる。
- イディオム（任意・第三者形、dm19-s02）: 誘発 {when: {event: block,
  attacker: {owner: you}}, effect: [may [cancel_attack]]}。
- 拡張: mod power_when に when: not_attacking を追加（「攻撃して
  いない時」）。defs 検証・スキーマ enum・core._power_when の3箇所。
  進行中の攻撃の攻撃クリーチャーでない間ずっと付く（ブロック中・
  攻撃されている間・攻撃が無い間を含む）。dm19-s02 の第1条項は
  常在型 {affects: {zone: bz, owner: you, filter: {tapped: true}},
  mod: {power_when: {amount: 7000, when: not_attacking}}} で表す。
  新規 GameState フィールドなし（state.rs 変更なし）。

プロト:
- T793 試験用鉄人チョイヤ型（dm06-101 の形: 火・コスト2・1000・PA+1000）
- T794 試験用リザード型（dm06-032 の形: 火・コスト5・3000・PA+3000）
- T795 試験用護法精霊型（dm19-s02 の形: 光・コスト6・5500）
"""
import pytest
from tests.conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card

TABLES = load_tables()


def _cid(e, defn, player):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _drive(e, attack_key=None, block_prefix=None, yes=True, stop=None, limit=800):
    """attack_key: 攻撃決定で選ぶキー（完全一致）。block_prefix: ブロック
    決定で選ぶキーの接頭辞（None なら no_block）。yes: yes_no への回答。"""
    for _ in range(limit):
        if stop and stop(e):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and attack_key in keys:
            e.answer([keys.index(attack_key)])
        elif d["kind"] == "block":
            cand = next((i for i, k in enumerate(keys)
                         if block_prefix and k.startswith(block_prefix)), None)
            if cand is not None:
                e.answer([cand])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif d["kind"] == "yes_no":
            e.answer([0] if yes else [1])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("drive limit exceeded")


# ---------- parse / 検証 ----------

def _base_card(**kw):
    d = {"id": "Q280", "name": "試験獣", "types": ["creature"], "civs": ["light"],
         "cost": 6, "power": 5500, "races": ["テスト"]}
    d.update(kw)
    return d


def test_parse_power_when_not_attacking():
    parse_card(_base_card(abilities=[
        {"kind": "static", "affects": {"zone": "bz", "owner": "you", "filter": {"tapped": True}},
         "mod": {"power_when": {"amount": 7000, "when": "not_attacking"}}}]), TABLES)
    for bad_pw in ({"amount": 7000, "when": "defending"}, {"amount": 7000},
                   {"when": "not_attacking"}):
        with pytest.raises(DefError):
            parse_card(_base_card(abilities=[
                {"kind": "static", "affects": "self", "mod": {"power_when": bad_pw}}]), TABLES)


def test_parse_cancel_trigger_forms():
    parse_card(_base_card(abilities=[   # 強制形（dm06-032/101）
        {"kind": "trigger", "when": {"event": "block", "attacker": "self"},
         "effect": [{"op": "cancel_attack"}]}]), TABLES)
    parse_card(_base_card(abilities=[   # 任意・第三者形（dm19-s02）
        {"kind": "trigger", "when": {"event": "block", "attacker": {"owner": "you"}},
         "effect": [{"op": "may", "body": [{"op": "cancel_attack"}]}]}]), TABLES)


# ---------- 強制形: ブロックされたらバトルは行われない ----------

def test_blocked_battle_does_not_occur_attacker_weaker():
    """T793（攻撃時2000）が T004（3000）にブロックされる: バトルが
    行われれば攻撃側は破壊されるが、中止されるので両者タップしたまま残る。"""
    e = setup(load_rules(), {"bz": ["T793", "T002"]}, {"bz": ["T004"]})
    atk, blk = _cid(e, "T793", 0), _cid(e, "T004", 1)
    sh1 = len(e.zlist("shield", 1))
    # T793 がタップし、次の攻撃決定（T002 の番）が来た時点で攻撃は終わっている
    _drive(e, attack_key="attack:T793:player", block_prefix="bz:T004",
           stop=lambda e: e.s.cards[atk].tapped and e.advance() and e.advance()["kind"] == "attack")
    assert e.s.cards[atk].zone == "bz" and e.s.cards[atk].tapped
    assert e.s.cards[blk].zone == "bz" and e.s.cards[blk].tapped   # ブロッカーもタップしたまま
    assert len(e.zlist("shield", 1)) == sh1                        # ブレイクなし
    assert not e.zlist("graveyard", 0) and not e.zlist("graveyard", 1)


def test_blocked_battle_does_not_occur_blocker_would_die():
    """T794（攻撃時6000）が T004（3000）にブロックされる: バトルが
    行われればブロッカーは破壊されるが、中止されるので破壊されない。"""
    e = setup(load_rules(), {"bz": ["T794", "T002"]}, {"bz": ["T004"]})
    atk, blk = _cid(e, "T794", 0), _cid(e, "T004", 1)
    _drive(e, attack_key="attack:T794:player", block_prefix="bz:T004",
           stop=lambda e: e.s.cards[atk].tapped and e.advance() and e.advance()["kind"] == "attack")
    assert e.s.cards[atk].zone == "bz" and e.s.cards[atk].tapped
    assert e.s.cards[blk].zone == "bz" and e.s.cards[blk].tapped
    assert not e.zlist("graveyard", 0) and not e.zlist("graveyard", 1)


def test_unblocked_attack_breaks_normally():
    """ブロックされなければ中止は起きず、通常どおりブレイクする。"""
    e = setup(load_rules(), {"bz": ["T793"]}, {"bz": ["T004"]})
    atk = _cid(e, "T793", 0)
    sh1 = len(e.zlist("shield", 1))
    _drive(e, attack_key="attack:T793:player", block_prefix=None,
           stop=lambda e: len(e.zlist("shield", 1)) < sh1)
    assert len(e.zlist("shield", 1)) == sh1 - 1
    assert e.s.cards[atk].zone == "bz"


def test_direct_creature_attack_battles_normally():
    """クリーチャーを直接攻撃した場合はブロックではないのでバトルが行われる
    （T793 攻撃時2000 vs タップした T001 2000 で相打ち）。"""
    e = setup(load_rules(), {"bz": ["T793"]}, {"bz": ["T001"]})
    atk, tgt = _cid(e, "T793", 0), _cid(e, "T001", 1)
    e.s.cards[tgt].tapped = True
    _drive(e, attack_key="attack:T793:T001",
           stop=lambda e: e.s.cards[atk].zone == "graveyard")
    assert e.s.cards[atk].zone == "graveyard"
    assert e.s.cards[tgt].zone == "graveyard"


# ---------- 任意・第三者形（dm19-s02 / T795） ----------

def test_optional_cancel_accept():
    """自分の T001 がブロックされた時、T795 の誘発で中止を選ぶ:
    両者タップしたまま残り、ブレイクもバトルもない。"""
    e = setup(load_rules(), {"bz": ["T795", "T001", "T002"]}, {"bz": ["T004"]})
    atk, blk = _cid(e, "T001", 0), _cid(e, "T004", 1)
    sh1 = len(e.zlist("shield", 1))
    _drive(e, attack_key="attack:T001:player", block_prefix="bz:T004", yes=True,
           stop=lambda e: e.s.cards[atk].tapped and e.advance() and e.advance()["kind"] == "attack")
    assert e.s.cards[atk].zone == "bz" and e.s.cards[atk].tapped
    assert e.s.cards[blk].zone == "bz" and e.s.cards[blk].tapped
    assert len(e.zlist("shield", 1)) == sh1


def test_optional_cancel_decline_battle_occurs():
    """中止を断ればバトルが行われる。攻撃中の T001 には「攻撃していない時」
    の +7000 は付かないので 2000 のまま T004（3000）に負ける。"""
    e = setup(load_rules(), {"bz": ["T795", "T001"]}, {"bz": ["T004"]})
    atk, blk = _cid(e, "T001", 0), _cid(e, "T004", 1)
    _drive(e, attack_key="attack:T001:player", block_prefix="bz:T004", yes=False,
           stop=lambda e: e.s.cards[atk].zone == "graveyard")
    assert e.s.cards[atk].zone == "graveyard"
    assert e.s.cards[blk].zone == "bz"


def test_optional_trigger_not_for_opponent_attacker():
    """相手のクリーチャーがブロックされても T795 の誘発は出ない
    （attacker: {owner: you}）。ドライバは yes_no に「はい」と答える
    設定なので、誤って誘発すればバトルが中止されてしまう。"""
    e = setup(load_rules(), {"bz": ["T795", "T004"]}, {"bz": ["T001", "T002"]})
    atk, blk = _cid(e, "T001", 1), _cid(e, "T004", 0)
    _drive(e, attack_key="attack:T001:player", block_prefix="bz:T004", yes=True,
           stop=lambda e: e.s.cards[atk].zone == "graveyard")
    assert e.s.cards[atk].zone == "graveyard"   # バトルは行われ、2000 は 3000 に負ける
    assert e.s.cards[blk].zone == "bz"


# ---------- power_when not_attacking（dm19-s02 第1条項） ----------

def test_not_attacking_static_chars():
    e = setup(load_rules(), {"bz": ["T795", "T001"]}, {"bz": ["T004"]})
    mine, other = _cid(e, "T001", 0), _cid(e, "T004", 1)
    assert e.chars(mine)["power"] == 2000          # アンタップ時は対象外（filter: tapped）
    e.s.cards[mine].tapped = True
    assert e.chars(mine)["power"] == 2000 + 7000   # タップしていて攻撃していない間は +7000
    e.s.cards[other].tapped = True
    assert e.chars(other)["power"] == 3000         # 相手のクリーチャーには付かない（owner: you）


def test_not_attacking_no_bonus_while_attacking():
    """攻撃クリーチャー自身はタップしていても「攻撃していない時」ではない:
    ブロック決定の時点でパワーは素のまま。"""
    e = setup(load_rules(), {"bz": ["T795", "T001"]}, {"bz": ["T004"]})
    atk = _cid(e, "T001", 0)
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and "attack:T001:player" in keys:
            e.answer([keys.index("attack:T001:player")])
            d = e.advance()
            assert d["kind"] == "block"
            assert e.s.cards[atk].tapped
            assert e.chars(atk)["power"] == 2000   # 攻撃中は +7000 が付かない
            e.answer([[o["key"] for o in d["options"]].index("no_block")])
            return
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("attack decision never came")


def test_not_attacking_defense_battle():
    """タップした自分のクリーチャーが攻撃される時、+7000 が付いて勝つ。
    T795 が無い対照では同じ攻撃で負ける。"""
    e = setup(load_rules(), {"bz": ["T795", "T001"]}, {"bz": ["T004"]})
    mine, foe = _cid(e, "T001", 0), _cid(e, "T004", 1)
    sh1 = len(e.zlist("shield", 1))
    _drive(e, attack_key="attack:T001:player", block_prefix=None,
           stop=lambda e: len(e.zlist("shield", 1)) < sh1)   # T001 が攻撃してタップする
    _drive(e, attack_key="attack:T004:T001", block_prefix=None,
           stop=lambda e: e.s.cards[foe].zone == "graveyard")
    assert e.s.cards[foe].zone == "graveyard"   # 9000 > 3000 で防御側が勝つ
    assert e.s.cards[mine].zone == "bz"

    e2 = setup(load_rules(), {"bz": ["T001"]}, {"bz": ["T004"]})
    mine2, foe2 = _cid(e2, "T001", 0), _cid(e2, "T004", 1)
    sh1b = len(e2.zlist("shield", 1))
    _drive(e2, attack_key="attack:T001:player", block_prefix=None,
           stop=lambda e: len(e.zlist("shield", 1)) < sh1b)
    _drive(e2, attack_key="attack:T004:T001", block_prefix=None,
           stop=lambda e: e.s.cards[mine2].zone == "graveyard")
    assert e2.s.cards[mine2].zone == "graveyard"   # 対照: 2000 < 3000 で負ける
    assert e2.s.cards[foe2].zone == "bz"
