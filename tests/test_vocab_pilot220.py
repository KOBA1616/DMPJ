"""語彙パイロット第220弾: hyper_subject_filter（ハイパーモード状態の主体フィルタ）。

アタック・チャンス自体は既存の declare イディオム（zone: hand、
when {event: attack, subject: {owner: you, filter: ...}}、effect は
may [play_free self]）で表現できる。足りなかったのは「そのクリーチャーが
ハイパーモード状態である」ことを subject フィルタで絞る手段だけなので、
フィルタキー hyper（真偽）を追加した（colorless と同型の同期:
defs の FILTER_KEYS、selectors の filter_match、Rust の filter 照合、
schema 再生成）。

ハイパーモードは「次の自分のターンのはじめまで」なので、解放と攻撃は
同じターンに行う。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T569", "T570", "T571")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)
            if e.s.cards[c].controller == p] if zone == "bz" else \
           [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _drive(e, handler, turns=5, limit=4000, stop_when=None):
    for _ in range(limit):
        if e.s.turn > turns:
            break
        d = e.advance()
        if d is None:
            break
        if stop_when is not None and stop_when(e, d):
            break
        if handler(e, d):
            continue
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def _make_handler(logs, release_turn=None, release_player=0, attacker=None,
                  attack_turn=None, accept=True):
    """release_turn の main で hyper:<attacker> を解放し、attack_turn の
    attack で attacker:player を選ぶ。yes_no は logs に記録して accept で答える。"""
    state = {"released": False, "attacked": False}

    def h(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "yes_no":
            logs.append((e.s.turn, d.get("player")))
            e.answer([0] if accept else [1])
            return True
        if d["kind"].startswith("declare"):
            idx = [i for i, k in enumerate(keys) if k.startswith("declare:T570")]
            if idx:
                e.answer(idx)   # アタック・チャンスを宣言する（may は yes_no 側で記録）
                return True
        if release_turn is not None and not state["released"] \
                and d["kind"] == "main" and d.get("player") == release_player \
                and e.s.turn == release_turn and f"hyper:{attacker}" in keys:
            state["released"] = True
            e.answer([keys.index(f"hyper:{attacker}")])
            return True
        if attacker is not None and not state["attacked"] \
                and d["kind"] == "attack" and e.s.turn == attack_turn \
                and f"attack:{attacker}:player" in keys:
            state["attacked"] = True
            e.answer([keys.index(f"attack:{attacker}:player")])
            return True
        return False

    return h, state


def test_attack_chance_fires_for_hyper_attacker(rules):
    logs = []
    h, state = _make_handler(logs, release_turn=3, attacker="T569", attack_turn=3)
    e = setup(rules, {"bz": ["T569", "T002"], "hand": ["T570"]}, {}, filler="T002")
    deck_at = {}

    def h2(e, d):
        if d["kind"] == "yes_no":
            deck_at["at_may"] = len(e.zlist("deck", 0))
        return h(e, d)

    _drive(e, h2, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["released"] and state["attacked"]
    assert logs == [(3, 0)]                       # 宣言の may は一度だけ
    assert "T570" in _defns(e, "graveyard", 0)    # 無料で唱えて墓地へ
    assert deck_at["at_may"] - len(e.zlist("deck", 0)) == 1   # 呪文のドロー1枚


def test_attack_chance_not_offered_without_hyper(rules):
    logs = []
    h, state = _make_handler(logs, release_turn=None, attacker="T569", attack_turn=3)
    e = setup(rules, {"bz": ["T569", "T002"], "hand": ["T570"]}, {}, filler="T002")
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["attacked"]
    assert logs == []                             # ハイパーでなければ聞かれない
    assert "T570" in _defns(e, "hand", 0)


def test_attack_chance_not_offered_for_non_hyper_attacker(rules):
    logs = []
    # ハイパー解放はするが、攻撃するのは別の（ハイパーでない）クリーチャー
    h, state = _make_handler(logs, release_turn=3, attacker="T569", attack_turn=99)
    e = setup(rules, {"bz": ["T569", "T002", "T551"], "hand": ["T570"]}, {},
              filler="T002")

    def h2(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and e.s.turn == 3 and "attack:T551:player" in keys:
            e.answer([keys.index("attack:T551:player")])
            return True
        return h(e, d)

    _drive(e, h2, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert logs == []
    assert "T570" in _defns(e, "hand", 0)


def test_attack_chance_not_offered_for_opponent_hyper(rules):
    logs = []
    h, state = _make_handler(logs, release_turn=2, release_player=1,
                             attacker="T569", attack_turn=2)
    e = setup(rules, {"hand": ["T570"]}, {"bz": ["T569", "T002"]}, filler="T002")
    _drive(e, h, turns=3, stop_when=lambda e, d: e.s.turn >= 3)
    assert state["released"] and state["attacked"]
    assert logs == []                             # 相手のハイパー攻撃では聞かれない
    assert "T570" in _defns(e, "hand", 0)


def test_graveyard_rescue_on_hyper_attack(rules):
    logs = []
    h, state = _make_handler(logs, release_turn=3, attacker="T569", attack_turn=3)
    e = setup(rules, {"bz": ["T569", "T002"], "graveyard": ["T571"]}, {},
              filler="T002")
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert logs == [(3, 0)]
    assert "T571" in _defns(e, "bz", 0)           # 墓地から出た

    logs.clear()
    h, state = _make_handler(logs, release_turn=None, attacker="T569", attack_turn=3)
    e = setup(rules, {"bz": ["T569", "T002"], "graveyard": ["T571"]}, {},
              filler="T002")
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert logs == []                             # ハイパーでなければ出てこない
    assert "T571" in _defns(e, "graveyard", 0)
