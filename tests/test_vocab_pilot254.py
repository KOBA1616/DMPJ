"""第254弾: action_limit（攻撃/ブロック回数の制限）。"""
from tests.conftest import setup
from dmsim.cards.defs import load_rules


def _drive(e, player, stop, limit=500, block_first=False):
    """player の視点で進める。攻撃はプレイヤー攻撃を優先し、ブロック諮問では block_first で切り替える。"""
    for _ in range(limit):
        if stop(e):
            return True
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if any(k.startswith("play:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:"))])
        elif d["kind"] == "block":
            blocks = [i for i, k in enumerate(keys) if k != "no_block"]
            if block_first and blocks:
                e.answer([blocks[0]])
            else:
                e.answer([keys.index("no_block")])
        else:
            a = next((i for i, k in enumerate(keys) if k.startswith("attack:") and k.endswith(":player")), None)
            if a is not None:
                e.answer([a])
            elif d["kind"] == "yes_no":
                e.answer([0])
            elif d["kind"] == "choose_breaker":
                e.answer([0])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
    return stop(e)


def _attack_opts(e, player):
    """現在の決定が player のメイン/攻撃ステップなら、攻撃選択肢のキーを返す。"""
    d = e.advance()
    assert d is not None
    return d, [o["key"] for o in d["options"]]


def test_opp_next_turn_attack_once():
    # P0 が T689 を唱える → 次の P1 のターン、P1 は1度しか攻撃できない
    e = setup(load_rules(),
              {"hand": ["T689"], "mana": ["T010"] * 3},
              {"bz": ["T001", "T002", "T034"]})
    attacks_seen = 0
    second_attack_decision = False
    cast_turn = None
    for _ in range(500):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if cast_turn is not None and e.s.turn != cast_turn:
            break   # 対象ターンを抜けた
        if d["kind"] == "attack" and d.get("player") == 1:
            if attacks_seen == 0:
                cast_turn = e.s.turn
                assert any(k.startswith("attack:") for k in keys), keys   # 1回目は攻撃できる
                attacks_seen += 1
                e.answer([next(i for i, k in enumerate(keys) if k.startswith("attack:") and k.endswith(":player"))])
                continue
            second_attack_decision = True   # 上限到達後に攻撃の諮問が来たら記録（来ないのが正しい）
            e.answer([keys.index("pass")])
            continue
        if any(k.startswith("play:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:"))])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif d["kind"] == "choose_breaker":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert attacks_seen == 1
    assert not second_attack_decision   # 1回攻撃した後は、攻撃ステップの諮問自体が来ない（選択肢が空でステップが進む）


def test_sustained_limit_two_attacks_and_blocks():
    # P0 が T690 を唱える → P1 は攻撃2回まで。さらに P0 のその後の攻撃でもブロック2回まで
    e = setup(load_rules(),
              {"hand": ["T690"], "mana": ["T010"] * 5, "bz": ["T001", "T002", "T034"]},
              {"bz": ["T003", "T004", "T005"]})
    # まず唱える（P0 のメインで play される）。その後 P0 は攻撃しない（pass 優先にしたいので手動で進める）
    for _ in range(300):
        if e.s.active == 1:
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if any(k.startswith("play:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:"))])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "yes_no":
            e.answer([0])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert e.s.action_limits, "制限が保留されていない"
    # P1 のターン: 2回攻撃でき、3回目はできない
    _drive(e, 1, lambda e: e.s.turn_counters.get("atk_decl:1", 0) >= 2 and e.s.active == 1)
    d = e.advance()
    keys = [o["key"] for o in d["options"]] if d else []
    assert not any(k.startswith("attack:") for k in keys), keys


def test_block_limit_two():
    # P0 が T690 を唱えたターン、P0 の3体の攻撃に対し P1 は2回しかブロックできない
    e = setup(load_rules(),
              {"hand": ["T690"], "mana": ["T010"] * 5, "bz": ["T001", "T002", "T034"]},
              {"bz": ["T004", "T004", "T004"]})
    blocks = {"n": 0}
    for _ in range(600):
        if e.s.turn_counters.get("atk_decl:0", 0) >= 3:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if any(k.startswith("play:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:"))])
        elif d["kind"] == "block":
            cand = [i for i, k in enumerate(keys) if k != "no_block"]
            if cand:
                blocks["n"] += 1
                e.answer([cand[0]])
            else:
                e.answer([keys.index("no_block")])
        else:
            a = next((i for i, k in enumerate(keys) if k.startswith("attack:") and k.endswith(":player")), None)
            if a is not None:
                e.answer([a])
            elif d["kind"] == "yes_no":
                e.answer([0])
            elif d["kind"] == "choose_breaker":
                e.answer([0])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
    assert blocks["n"] == 2, blocks   # 3回目の攻撃ではブロック候補が出ず、ブロックできなかった
