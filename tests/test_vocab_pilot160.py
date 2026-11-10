"""語彙パイロット第160弾: must_be_attacked の first_only 形（はじめて攻撃するなら）。

「各ターン、相手のクリーチャーがはじめて攻撃するなら、可能ならこのクリーチャーを
攻撃する」は、第51弾の mod must_be_attacked: true の辞書形
must_be_attacked: {first_only: true} で表す。攻撃先の制限は、そのクリーチャーが
このターンまだ攻撃していない時（履歴カウンタ hist:attack_by が 0）だけ働く。
制限はクリーチャー単位: 別のクリーチャーが先に攻撃していても、まだ攻撃して
いないクリーチャーの初回攻撃は制限される（dm26sd1-m001 アビスベル＝覇＝ロード、
dm25ex3-rp4s05「K」-9+9+9 の条項）。
"""
from pathlib import Path

import yaml
from conftest import setup

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    parsed = parse_card(_proto_card("T291"), TABLES)
    assert parsed.abilities[0]["mod"]["must_be_attacked"] == {"first_only": True}


def test_invalid_forms():
    base = {"id": "test-mba-bad", "name": "試験誘引獣不良", "types": ["creature"],
            "civs": ["darkness"], "cost": 5, "power": 4000,
            "source": {"official": "test-mba-bad", "review": "pending"}}
    for bad_value in ({"first_only": False}, {"other": True}, "yes", 1):
        card = {**base, "abilities": [{"kind": "static", "affects": "self",
                                       "mod": {"must_be_attacked": bad_value}}]}
        try:
            parse_card(card, TABLES)
            raise AssertionError(f"should have raised: {bad_value}")
        except Exception as e:
            assert "must_be_attacked" in str(e)


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


def _drive_attack(e, atk_key, max_steps=300):
    """既定回答で進め、atk_key の攻撃を1回実行し、次の攻撃判断（player 0）を返す。"""
    chosen = False
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and d["player"] == 0:
            if not chosen and atk_key in keys:
                e.answer([keys.index(atk_key)])
                chosen = True
                continue
            return d
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        else:
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("attack decision not reached")


def _tap(e, player, defn):
    """bz は共有ゾーンなので、コントローラーまで見て対象側のカードをタップする。"""
    for c in e.zlist("bz", player):
        if e.s.cards[c].defn == defn and e.s.cards[c].controller == player:
            e.s.cards[c].tapped = True
            return
    raise AssertionError(defn)


def _cid(e, player, defn, nth=0):
    return [c for c in e.zlist("bz", player) if e.s.cards[c].defn == defn][nth]


def _cid_ctrl(e, player, defn):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def test_first_attack_is_restricted(rules):
    """このターンまだ攻撃していないクリーチャーは、初撃誘引獣（T291）しか攻撃できない。"""
    e = setup(rules, {"bz": ["T005"]}, {"bz": ["T291", "T001"]})
    _tap(e, 1, "T291")
    _tap(e, 1, "T001")
    keys = [o["key"] for o in _attack_options(e, 0)]
    attacks = [k for k in keys if k.startswith("attack:")]
    assert attacks == ["attack:T005:T291"]


def test_after_attacking_once_not_restricted(rules):
    """一度攻撃したクリーチャーの次の攻撃は制限されない。

    履歴カウンタ hist:attack_by を、ターン開始の初期化後に1回分種付けして確認する
    （実際の攻撃でこのカウンタが増えることは第159弾のテストで検証済み）。
    手札を1枚持たせ、ターン開始処理の後・攻撃判断の前に来るチャージ判断で種付ける。
    """
    e = setup(rules, {"bz": ["T005"], "hand": ["T001"]}, {"bz": ["T291", "T001"]})
    _tap(e, 1, "T291")
    _tap(e, 1, "T001")
    att = _cid(e, 0, "T005")

    def seed():
        e.s.turn_counters[f"hist:attack_by:{att}"] = 1

    keys = [o["key"] for o in _attack_options(e, 0, seed=seed)]
    attacks = sorted(k for k in keys if k.startswith("attack:"))
    assert attacks == ["attack:T005:T001", "attack:T005:T291", "attack:T005:player"]


def test_restriction_is_per_creature(rules):
    """制限はターン単位ではなくクリーチャー単位: 別のクリーチャーが先に攻撃しても、
    まだ攻撃していないクリーチャーの初回攻撃は制限される。"""
    e = setup(rules, {"bz": ["T001", "T005"]}, {"bz": ["T291", "T001"]})
    _tap(e, 1, "T291")
    _tap(e, 1, "T001")
    # T001 の初回攻撃は T291 に強制され、バトルで T001（2000）は T291（4000）に負けて破壊される
    t001 = _cid_ctrl(e, 0, "T001")
    d = _drive_attack(e, "attack:T001:T291")
    assert e.s.cards[t001].zone == "graveyard", "T001 が実際に攻撃して破壊されたことの確認"
    assert e.s.cards[_cid(e, 0, "T005")].zone == "bz"
    keys = [o["key"] for o in d["options"]]
    attacks = [k for k in keys if k.startswith("attack:")]
    assert attacks == ["attack:T005:T291"]
