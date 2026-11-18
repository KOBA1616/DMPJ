"""語彙パイロット第225弾: cross_gear_mechanic の切り分けイディオム。

未クロス時の軽減（if で自カードの crossed 状態を見る）、名前制限付き cross_free、
ブレイク誘発 subject: crossed、マナから出す呪文。proto T592-T598。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests._conv_cache import proto_card as _proto_card
from tests.conftest import setup


def test_proto_parse():
    t592 = _proto_card("T592")
    assert t592["abilities"][0]["mod"] == {"cost_may": {"amount": 1, "min": 1}}
    assert t592["abilities"][0]["if"] == {"not": {"exists": {"ref": "self", "filter": {"crossed": True}}}}
    assert t592["abilities"][2]["mod"] == {"allow": [{"action": "cross_free", "other": {"name_has": "武者"}}]}
    assert _proto_card("T593")["abilities"][2]["when"] == {"event": "break", "subject": "crossed"}
    for cid in ("T594", "T595", "T596", "T597", "T598"):
        _proto_card(cid)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _cid(e, p, defn, zone="bz"):
    return next(c for c in e.zlist(zone, p) if e.s.cards[c].defn == defn)


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _cross(e, gear, host, p=0):
    e.s.cards[_cid(e, p, gear)].crossed = e.s.ref(_cid(e, p, host))


def _drive(e, play=None, pick=None, max_steps=300):
    """汎用ドライバ。play: 使う play キーの接頭辞。pick: choose_cards で優先する defn。"""
    for _ in range(max_steps):
        d = e.advance()
        if d is None:
            return None
        keys = _keys(d)
        kind = d["kind"]
        if kind == "main" and play:
            pk = next((k for k in keys if k.startswith(play)), None)
            if pk is not None:
                e.answer([keys.index(pk)])
                continue
            return d
        if kind in ("main", "attack"):
            return d
        if kind == "charge":
            e.answer([keys.index("pass")])
            continue
        if kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "choose_cards":
            idx = next((i for i, k in enumerate(keys) if pick and pick in k), None)
            e.answer([idx] if idx is not None else list(range(d["min"])))
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif kind == "choose_shields":
            e.answer(list(range(d["min"])))
        elif kind == "yes_no":
            e.answer([0])
        elif kind.startswith("declare"):
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("did not settle")


def test_592_uncrossed_dragon_reduction(rules):
    e = setup(rules, {"bz": ["T592"], "hand": ["T598"],
                      "mana": ["T030", "T001", "T001", "T001"]}, {},
              filler="T001", seed=1)
    _drive(e, play="play:T598")
    _drive(e)                                   # 解決まで（軽減の諮問→支払い→登場）
    assert "T598" in _defns(e, "bz", 0)         # 4マナでコスト5ドラゴンが出た


def test_592_crossed_no_reduction(rules):
    e = setup(rules, {"bz": ["T592", "T002"], "hand": ["T598"],
                      "mana": ["T030", "T001", "T001", "T001"]}, {},
              filler="T001", seed=1)
    _cross(e, "T592", "T002")
    seen = []
    for _ in range(12):
        d = e.advance()
        if d is None:
            break
        if d["kind"] == "main":
            seen += _keys(d)
            break
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d.get("min", 0))))
    assert not any(k.startswith("play:T598") for k in seen)   # クロス中は軽減なし（4マナでは出せない）


def test_592_restricted_free_cross(rules):
    e = setup(rules, {"bz": ["T592", "T596", "T002"]}, {}, filler="T001", seed=1)
    d = None
    for _ in range(12):
        d = e.advance()
        if d is not None and d["kind"] == "main":
            break
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d.get("min", 0))))
    keys = _keys(d)
    assert "cross:T592:T596:free" in keys            # 武者には無料クロス可
    assert "cross:T592:T002:free" not in keys        # それ以外は不可
    e.answer([keys.index("cross:T592:T596:free")])
    _drive(e)
    assert e.s.cards[_cid(e, 0, "T592")].crossed is not None
    ch = e.chars(_cid(e, 0, "T596"))
    assert ch["power"] == 5000 and ch["breaks"] == 2  # ホスト付与 +2000＆ブレイク+1


def _run(e, play=None, pick=None, attack=None, stop_when=None, cross=None,
         max_steps=400):
    """単一ドライバ（ステップ決定を持ち越さない）。stop_when は状態で判定する。

    cross: そのキー（cross:<gear>:<host>:free 等）がメイン決定に出たら選ぶ。
    """
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        if stop_when is not None and stop_when(e):
            return
        keys = _keys(d)
        kind = d["kind"]
        if kind == "main" and cross and cross in keys:
            e.answer([keys.index(cross)])
            continue
        if kind == "main" and play:
            pk = next((k for k in keys if k.startswith(play)), None)
            if pk is not None:
                e.answer([keys.index(pk)])
                continue
        if kind == "attack" and attack and f"attack:{attack}:player" in keys:
            e.answer([keys.index(f"attack:{attack}:player")])
            continue
        if kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "choose_cards":
            idx = next((i for i, k in enumerate(keys) if pick and pick in k), None)
            e.answer([idx] if idx is not None else list(range(d["min"])))
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif kind == "choose_shields":
            e.answer(list(range(d["min"])))
        elif kind == "yes_no":
            e.answer([0])
        elif kind.startswith("declare"):
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("did not settle")


def test_593_cip_and_break_trigger(rules):
    e = setup(rules, {"bz": ["T002"], "hand": ["T593"],
                      "mana": ["T030", "T551", "T001", "T001"]},
              {"bz": ["T587", "T060"]}, filler="T001", seed=1)
    # CIP で相手のギアを破壊 → フリー・クロスで T002 にクロス → そのまま攻撃へ
    _run(e, play="play:T593", pick="T587", attack="T002",
         cross="cross:T593:T002:free",
         stop_when=lambda e: "T060" in _defns(e, "graveyard", 1)
         and len(_defns(e, "hand", 0)) == 1)
    assert "T587" in _defns(e, "graveyard", 1)       # CIP: バトルゾーンのクロスギアを墓地へ
    assert "T060" in _defns(e, "graveyard", 1)       # ブレイク誘発で破壊
    assert len(_defns(e, "hand", 0)) == 1            # その後1枚引く


def test_594_spell_puts_from_mana(rules):
    e = setup(rules, {"bz": ["T002"], "hand": ["T594"],
                      "mana": ["T551", "T597", "T587"] + ["T001"] * 7}, {},
              filler="T001", seed=1)
    _drive(e, play="play:T594")
    _drive(e)
    bz = _defns(e, "bz", 0)
    assert "T597" in bz and "T587" in bz             # ボルベルグ名とクロスギアがマナから出た
    assert "T002" in _defns(e, "mana", 0)            # 代わりに自分のクリーチャーをマナへ


def test_595_attack_mana_cycle(rules):
    e = setup(rules, {"bz": ["T002", "T595"]}, {}, filler="T001", seed=1)
    _cross(e, "T595", "T002")
    assert e.chars(_cid(e, 0, "T002"))["power"] == 4000
    _run(e, attack="T002",
         stop_when=lambda e: len(_defns(e, "mana", 0)) == 1
         and len(_defns(e, "hand", 0)) == 1)
    assert len(_defns(e, "mana", 0)) == 1            # 2枚置いて1枚戻す
    assert len(_defns(e, "hand", 0)) == 1
