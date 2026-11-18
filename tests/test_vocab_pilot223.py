"""語彙パイロット第223弾: power_gachinko_judge。

パワー・ガチンコ・ジャッジ（dm26rp2 の6枚）: 既存 op gachinko（コスト比較）
へ2つの arg を足すだけで表せる。

- by: "power" — 比較軸がパワーになる。パワーがないカード（呪文等）は
  chars の power が無いため 0 として扱う（公式説明文どおり）。同点は
  「相手以上」なので自分の勝ち（コスト版と同じ >= ）。
- mine_as — 自分の見せたカードを山札の下に置かず、その参照を変数に
  残す（dm26rp2-004「下に置くかわりに召喚してもよい」の代替先を後続
  op が決める）。繰り返す場合は最後の1枚だけが残り、前の分は通常どおり
  下へ置く。保留状態は task の os に持つ（stoppable の ask で中断・再入
  しても失われない）。

proto: T583 基本形（勝ったら1ドロー）/ T584 mine_as 形（勝ったら見せた
カードをかわりに召喚、断るか負けたら下へ）/ T585 until_lose＋stoppable
＋repeat {var: wins} 形。
"""
import os

os.environ.setdefault("DMSIM_SKIP_CONVERTED", "1")

from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402
from tests.conftest import setup  # noqa: E402

TABLES = load_tables()
IDS = ("T583", "T584", "T585")


def _rules():
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _bz(e, p):
    return [e.s.cards[c].defn for c in e.zlist("bz", p)
            if e.s.cards[c].controller == p and e.s.cards[c].top_of < 0]


def _drive(e, handler=None, turns=1, max_steps=500):
    for _ in range(max_steps):
        if e.s.turn > turns:
            break
        d = e.advance()
        if d is None:
            break
        if e.s.turn > turns:   # 次ターンへ跨いだ advance は答えずに止める（ドロー汚染防止）
            break
        if handler and handler(e, d):
            continue
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return e


def _handler(play=None, attack=None, yes_no=()):
    state = {"played": False, "attacked": False, "yn": list(yes_no)}

    def h(e, d):
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "main" and play and not state["played"]:
            for i, k in enumerate(keys):
                if k.startswith("play:" + play):
                    state["played"] = True
                    e.answer([i])
                    return True
            return False
        if kind == "attack" and attack and not state["attacked"]:
            for i, k in enumerate(keys):
                if k == f"attack:{attack}:player":
                    state["attacked"] = True
                    e.answer([i])
                    return True
            return False
        if kind == "yes_no":
            e.answer([state["yn"].pop(0) if state["yn"] else 0])
            return True
        if kind == "choose_shields":
            e.answer([0])
            return True
        return False

    return h


def test_proto_parse():
    for cid in IDS:
        parse_card(proto_card(cid), TABLES)


def test_583_win_draws_and_bottoms_both():
    e = setup(_rules(), {"hand": ["T583"], "mana": ["T060"] * 3,
                         "deck": ["T002", "T002", "T201"]},
              {"deck": ["T002", "T201", "T002"]})
    _drive(e, _handler(play="T583", yes_no=[0]))
    assert len(_defns(e, "hand", 0)) == 1        # 勝って1枚引く
    assert _defns(e, "deck", 0)[0] == "T002"     # 見せた T201 は一番下へ
    assert _defns(e, "deck", 1)[-1] == "T002"    # 相手の見せた T002 も一番下へ


def test_583_lose_no_draw():
    e = setup(_rules(), {"hand": ["T583"], "mana": ["T060"] * 3,
                         "deck": ["T002", "T201", "T002"]},
              {"deck": ["T002", "T002", "T201"]})
    _drive(e, _handler(play="T583", yes_no=[0]))
    assert len(_defns(e, "hand", 0)) == 0


def test_583_spell_counts_as_zero_power():
    # 自分の見せた呪文（パワーなし=0）はパワー1000に負ける
    e = setup(_rules(), {"hand": ["T583"], "mana": ["T060"] * 3,
                         "deck": ["T002", "T201", "T006"]},
              {"deck": ["T002", "T201", "T002"]})
    _drive(e, _handler(play="T583", yes_no=[0]))
    assert len(_defns(e, "hand", 0)) == 0
    # 両方とも呪文なら 0 >= 0 で勝ち
    e = setup(_rules(), {"hand": ["T583"], "mana": ["T060"] * 3,
                         "deck": ["T002", "T201", "T006"]},
              {"deck": ["T002", "T201", "T006"]})
    _drive(e, _handler(play="T583", yes_no=[0]))
    assert len(_defns(e, "hand", 0)) == 1


def test_584_win_and_summon_revealed_instead_of_bottom():
    e = setup(_rules(), {"hand": ["T584"], "mana": ["T030"] * 4,
                         "deck": ["T002", "T002", "T201"]},
              {"deck": ["T002", "T201", "T002"]})
    _drive(e, _handler(play="T584", yes_no=[0, 0]))   # ジャッジする→召喚する
    assert "T201" in _bz(e, 0)                        # 見せたカードを召喚
    assert "T201" not in _defns(e, "deck", 0)         # 下には置かれていない


def test_584_win_but_decline_summon_bottoms_revealed():
    e = setup(_rules(), {"hand": ["T584"], "mana": ["T030"] * 4,
                         "deck": ["T002", "T002", "T201"]},
              {"deck": ["T002", "T201", "T002"]})
    _drive(e, _handler(play="T584", yes_no=[0, 1]))   # ジャッジする→召喚しない
    assert "T201" not in _bz(e, 0)
    assert _defns(e, "deck", 0)[-1] == "T201"         # かわりに一番下へ


def test_584_lose_bottoms_revealed():
    e = setup(_rules(), {"hand": ["T584"], "mana": ["T030"] * 4,
                         "deck": ["T002", "T201", "T002"]},
              {"deck": ["T002", "T002", "T201"]})
    _drive(e, _handler(play="T584", yes_no=[0]))       # ジャッジする（負け）
    assert _defns(e, "deck", 0)[-1] == "T002"          # 見せたカードは一番下へ


def test_585_until_lose_stoppable_repeat_wins():
    e = setup(_rules(), {"bz": ["T585"],
                         "deck": ["T002", "T002", "T201", "T201"]},
              {"deck": ["T002", "T201", "T002", "T002"]})
    # 続ける→勝ち、続ける→勝ち、中止する（ans の index 1 が中止）
    _drive(e, _handler(attack="T585", yes_no=[0, 0, 1]))
    assert len(_defns(e, "hand", 0)) == 2             # 勝った回数だけ引く
