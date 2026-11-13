"""語彙パイロット第43弾（フェーズ17-4）: S-MAX進化（s_max_evolution 単独17件）。

実装したもの:
- カード属性 s_max（defs / schema）: 進化クリーチャーでも evolve_from を不要にし、通常召喚として扱う
- 敗北の置換: when: {event: lose} の kind: replace を新設。敗北の確定はすべて Engine.game_lose を通り、
  置換候補があれば敗北するプレイヤーに諮問する（ダイレクトアタック／デッキ切れ／状況起因／効果による敗北）
- 2体制限: 状況起因処理で自分の S-MAX が2体以上あれば、残す1体以外をすべて手札に戻す
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dmsim.engine import scenario  # noqa: E402
from conftest import answer, setup  # noqa: E402


def test_smax_summons_without_base(rules):
    """進化元が場に無くても、通常のクリーチャーとして召喚できる。"""
    e = setup(rules, {"hand": ["T121"], "mana": ["T005"] * 6}, {})
    answer(e, "charge", "pass")
    d = e.advance()
    keys = [o["key"] for o in d["options"]]
    assert "play:T121" in keys
    e.answer([keys.index("play:T121")])
    for _ in range(10):   # マナが全て同種なら支払いは自動で済むこともあるので、判断が出たら払う
        if any(e.s.cards[c].defn == "T121" for c in e.zlist("bz", 0)):
            break
        d = e.advance()
        if d is None:
            break
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        else:
            ks = [o["key"] for o in d["options"]]
            e.answer([ks.index("pass")] if "pass" in ks else list(range(d["min"])))
    assert any(e.s.cards[c].defn == "T121" for c in e.zlist("bz", 0))
    top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T121")
    assert e.s.cards[top].under == []


def test_smax_two_or_more_rule(rules):
    """自分の S-MAX が2体あれば、状況起因で1体を残して残りが手札に戻る。"""
    e = setup(rules, {"bz": ["T121", "T122"]}, {})
    kept = None
    for _ in range(40):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_smax_keep":
            e.answer([0])
            kept = True
            continue
        if kept and sum(1 for c in e.zlist("bz", 0) if e.s.cards[c].defn in ("T121", "T122")) == 1:
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    bz = [e.s.cards[c].defn for c in e.zlist("bz", 0) if e.s.cards[c].defn in ("T121", "T122")]
    hand = [e.s.cards[c].defn for c in e.zlist("hand", 0)]
    assert kept is True
    assert len(bz) == 1 and len([h for h in hand if h in ("T121", "T122")]) == 1


def _duel(rules, p1_hand):
    return scenario.build(rules, {
        "p0": {"bz": ["T001"]},
        "p1": {"bz": ["T121"], "hand": p1_hand, "shield": [], "deck": ["T005", "T005", "T005"]},
        "filler": "T001", "seed": 1, "deck_size": 20, "deck_exact": [False, True],
    })


def _drive_attack(e, on_lose_replace, mode_key="mode:0"):
    """P0 がプレイヤー攻撃。lose_replace の諮問が出たら on_lose_replace(keys) の戻り値で答える。"""
    seen = False
    for _ in range(100):
        if e.s.result is not None:
            break
        if seen and any(e.s.cards[c].defn == "T121" for c in e.zlist("graveyard", 1)):
            break   # 置換で破壊して敗北を回避できた時点で観察終了（その後の通常進行で負けるのは別問題）
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and "attack:T001:player" in keys:
            e.answer([keys.index("attack:T001:player")])
            continue
        if d["kind"] == "lose_replace":
            seen = True
            e.answer(on_lose_replace(keys))
            continue
        if d["kind"] == "choose_mode":
            e.answer([keys.index(mode_key)])
            continue
        if d["kind"] == "block":
            e.answer([keys.index("no_block")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
            continue
        e.answer(list(range(d["min"])))
    return seen


def test_smax_lose_replacement_averts_direct_attack_loss(rules):
    """シールド0でダイレクトアタックを受けても、S-MAX を破壊して敗北を回避できる。"""
    e = _duel(rules, [])
    seen = _drive_attack(e, lambda keys: [i for i, k in enumerate(keys) if k.startswith("lose_replace:")])
    assert seen is True
    assert e.s.result is None
    assert any(e.s.cards[c].defn == "T121" for c in e.zlist("graveyard", 1))


def test_smax_lose_replacement_by_discarding_same_name(rules):
    """手札に同名カードがあれば、それを捨てる方を選んで本体を残せる。"""
    e = _duel(rules, ["T121"])
    seen = _drive_attack(e, lambda keys: [i for i, k in enumerate(keys) if k.startswith("lose_replace:")],
                         mode_key="mode:1")
    assert seen is True
    assert e.s.result is None
    assert any(e.s.cards[c].defn == "T121" for c in e.zlist("bz", 1))          # 本体は残った
    assert any(e.s.cards[c].defn == "T121" for c in e.zlist("graveyard", 1))   # 捨てた同名が墓地へ


def test_smax_lose_replacement_declined_loses(rules):
    """置換を辞退すれば通常どおり敗北する。"""
    e = _duel(rules, [])
    seen = _drive_attack(e, lambda keys: [keys.index("decline")])
    assert seen is True
    assert e.s.result is not None and e.s.result["winner"] == 0
