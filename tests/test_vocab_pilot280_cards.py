"""語彙パイロット第280弾のカード適用テスト（登録形）。

ラウンド315で battle_does_not_occur_when_blocked の純粋3件をすべて
新規登録、差し戻しなし。
- dm06-032 ピーカプ・リザード（パワーアタッカー +3000）
- dm06-101 無謀鉄人チョイヤ（パワーアタッカー +1000）
- dm19-s02 護法の精霊アムシオン（任意形＋「攻撃していない時」+7000）
3件とも alias は無く、rejects に alias 行も無かったため stale 整理なし。
converted 10,148 / rejects 2,185、重複0・漏れ0。
battle_does_not_occur_when_blocked は残り0件でファミリー解消。

登録形:
- dm06-032 / dm06-101: partial に block 誘発 {when: {event: block,
  attacker: self}, effect: [{op: cancel_attack}]}（第280弾の強制形
  イディオム）を追加して提出。ただし submit がテキスト由来の
  パワーアタッカー常在型 {kind: static, affects: self, mod:
  {power_when: {amount, when: attacking}}} を加え、partial の
  パワーアタッカー誘発（攻撃時 modify）と二重適用になるため、
  登録後に誘発側を除去して常在型に一本化した（第307弾 dm26ex3-079・
  第313弾の post-submit 修正先例どおり）。本ファイルの
  test_registered_forms が一本化後の abilities を固定し、
  test_registered_101_blocked_no_battle が攻撃中のパワーが
  2000（+1000 の一回だけ）であることまで実挙動で固定する。
- dm19-s02: partial は abilities を持たないため、常在型 {affects:
  {zone: bz, owner: you, filter: {tapped: true}}, mod: {power_when:
  {amount: 7000, when: not_attacking}}} と誘発 {when: {event: block,
  attacker: {owner: you}}, effect: [may [cancel_attack]]} を公式
  全文から構築して追加。登録形は回答と完全一致。

プロトテスト（test_vocab_pilot280.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine.scenario import build  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
IDS = ["dm06-032", "dm06-101", "dm19-s02"]

TEXTS = {
    "dm06-032":
        "パワーアタッカー +3000(攻撃中、このクリーチャーのパワーは+3000される)\n"
        "このクリーチャーの攻撃がブロックされた場合、バトルは行われない。ただし、両クリーチャーはタップしたままである。",
    "dm06-101":
        "パワーアタッカー +1000(攻撃中、このクリーチャーのパワーは+1000される)\n"
        "このクリーチャーの攻撃がブロックされた場合、バトルは行われない。ただし、両クリーチャーはタップしたままである。",
    "dm19-s02":
        "バトルゾーンにある自分の、タップされているクリーチャーのパワーは、攻撃していない時、+7000される。"
        "自分のクリーチャーがブロックされた時、その攻撃を中止してもよい。そうした場合、バトルは行われない。ただし、両クリーチャーはタップしたままである。",
}

BLOCK_CANCEL_SELF = {"kind": "trigger",
                     "when": {"event": "block", "attacker": "self"},
                     "effect": [{"op": "cancel_attack"}]}

ABILITIES = {
    "dm06-032": [
        {"kind": "static", "affects": "self",
         "mod": {"power_when": {"amount": 3000, "when": "attacking"}}},
        BLOCK_CANCEL_SELF],
    "dm06-101": [
        {"kind": "static", "affects": "self",
         "mod": {"power_when": {"amount": 1000, "when": "attacking"}}},
        BLOCK_CANCEL_SELF],
    "dm19-s02": [
        {"kind": "static",
         "affects": {"zone": "bz", "owner": "you", "filter": {"tapped": True}},
         "mod": {"power_when": {"amount": 7000, "when": "not_attacking"}}},
        {"kind": "trigger", "when": {"event": "block", "attacker": {"owner": "you"}},
         "effect": [{"op": "may", "body": [{"op": "cancel_attack"}]}]}],
}

META = {
    "dm06-032": ("ピーカプ・リザード", ["fire"], 5, 3000, ["デューンゲッコー"]),
    "dm06-101": ("無謀鉄人チョイヤ", ["fire"], 2, 1000, ["ヒューマノイド"]),
    "dm19-s02": ("護法の精霊アムシオン", ["light"], 6, 5500, ["エンジェル・コマンド"]),
}


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject(cid):
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            if r["id"] == cid:
                return r
    raise KeyError(cid)


def _setup(p0, p1=None):
    return build(load_rules(), {"p0": p0, "p1": p1 or {}, "filler": "T001",
                                "seed": 1, "deck_size": 20})


def _cid(e, defn, player):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _drive(e, attack_key=None, block_prefix=None, yes=True, stop=None,
           on_block=None, limit=800):
    """第280弾本体の _drive と同形（build ゲーム用）。on_block は block
    決定に答える直前に (e, d) で呼ばれる観測フック。"""
    for _ in range(limit):
        if stop and stop(e):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and attack_key in keys:
            e.answer([keys.index(attack_key)])
        elif d["kind"] == "block":
            if on_block is not None:
                on_block(e, d)
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


# ---------- 登録形 ----------

def test_registered_forms():
    for cid in IDS:
        c = _converted(cid)
        parse_card(json.loads(json.dumps(c)), TABLES)
        assert "unsupported" not in (c.get("source") or {}), cid
        assert (c.get("source") or {}).get("aliases") in (None, []), cid
        try:
            _reject(cid)
            raise AssertionError(f"{cid} が rejects に残っている")
        except KeyError:
            pass
        name, civs, cost, power, races = META[cid]
        assert c["name"] == name and c["civs"] == civs, cid
        assert c["types"] == ["creature"] and c["cost"] == cost, cid
        assert c["power"] == power and c["races"] == races, cid
        assert c.get("keywords") in (None, []), cid
        assert c["text"] == TEXTS[cid], cid
        # abilities は登録形と完全一致（dm06 2件は一本化後の形）
        assert c["abilities"] == ABILITIES[cid], cid


# ---------- 実挙動: dm06-101（登録形・強制形） ----------

def test_registered_101_blocked_no_battle():
    """dm06-101（攻撃時2000）が T004（3000）にブロックされる: バトルは
    行われず両者タップしたまま残る。ブロック決定時点で攻撃側のパワーが
    2000 であることも確認する（パワーアタッカーの一本化＝二重適用なし）。"""
    e = _setup({"bz": ["dm06-101", "T002"], "mana": ["T001"]}, {"bz": ["T004"]})
    atk, blk = _cid(e, "dm06-101", 0), _cid(e, "T004", 1)
    sh1 = len(e.zlist("shield", 1))
    seen = {}

    def on_block(ev, d):
        if "power" not in seen:
            seen["power"] = ev.chars(atk)["power"]

    _drive(e, attack_key="attack:dm06-101:player", block_prefix="bz:T004",
           on_block=on_block,
           stop=lambda e: e.s.cards[atk].tapped and e.advance()
           and e.advance()["kind"] == "attack")
    assert seen["power"] == 2000            # 1000 + 1000（一回だけ）
    assert e.s.cards[atk].zone == "bz" and e.s.cards[atk].tapped
    assert e.s.cards[blk].zone == "bz" and e.s.cards[blk].tapped
    assert len(e.zlist("shield", 1)) == sh1
    assert not e.zlist("graveyard", 0) and not e.zlist("graveyard", 1)


def test_registered_032_unblocked_breaks_normally():
    """dm06-032 がブロックされなければ通常どおりブレイクする。"""
    e = _setup({"bz": ["dm06-032"], "mana": ["T001"]}, {"bz": ["T004"]})
    atk = _cid(e, "dm06-032", 0)
    sh1 = len(e.zlist("shield", 1))
    _drive(e, attack_key="attack:dm06-032:player", block_prefix=None,
           stop=lambda e: len(e.zlist("shield", 1)) < sh1)
    assert len(e.zlist("shield", 1)) == sh1 - 1
    assert e.s.cards[atk].zone == "bz"


# ---------- 実挙動: dm19-s02（登録形・任意形＋常在型） ----------

def test_registered_s02_not_attacking_static():
    """タップしている自分のクリーチャーは攻撃していない時 +7000、
    アンタップ時は対象外、相手のクリーチャーには付かない。"""
    e = _setup({"bz": ["dm19-s02", "T001"]}, {"bz": ["T004"]})
    mine, other = _cid(e, "T001", 0), _cid(e, "T004", 1)
    assert e.chars(mine)["power"] == 2000
    e.s.cards[mine].tapped = True
    assert e.chars(mine)["power"] == 2000 + 7000
    e.s.cards[other].tapped = True
    assert e.chars(other)["power"] == 3000


def test_registered_s02_optional_cancel_accept():
    """自分の T001 がブロックされた時、dm19-s02 の誘発で中止を選ぶ:
    両者タップしたまま残り、ブレイクもバトルもない。"""
    e = _setup({"bz": ["dm19-s02", "T001", "T002"], "mana": ["T001"]},
               {"bz": ["T004"]})
    atk, blk = _cid(e, "T001", 0), _cid(e, "T004", 1)
    sh1 = len(e.zlist("shield", 1))
    _drive(e, attack_key="attack:T001:player", block_prefix="bz:T004", yes=True,
           stop=lambda e: e.s.cards[atk].tapped and e.advance()
           and e.advance()["kind"] == "attack")
    assert e.s.cards[atk].zone == "bz" and e.s.cards[atk].tapped
    assert e.s.cards[blk].zone == "bz" and e.s.cards[blk].tapped
    assert len(e.zlist("shield", 1)) == sh1
    assert not e.zlist("graveyard", 0) and not e.zlist("graveyard", 1)
