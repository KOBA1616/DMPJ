"""語彙パイロット第302弾: gachinko_break_count。

ガチンコ・ジャッジの勝ち数でブレイクが決まる3件（dm26rp2-tr009 /
dmex12-009 = R.S.F.K.、dmr05-v02 = 鬼無双 カイザー「勝」）は、既存語彙
だけで足りるギャップ名ドリフトだった。不足に見えたのは次の2形の
組み立てで、いずれも新規 op・フィールドは要らない。

- 形A（カイザー「勝」型 = その攻撃自体のブレイク数への加算）:
  partial が既に持つ gachinko {until_lose, stoppable, as: wins} +
  repeat {times: {var: wins}} の body に、modify {breaks_add: 1}
  （duration: end_of_turn）を1ステップ足す。breaks_add の modify 形は
  ドギラゴン・ガチャの出目3（「このターンの終わりまでシールドを
  さらに1枚ブレイクする」）で確立済み。
- 形B（R.S.F.K.型 = 誘発の効果としてブレイク）:
  attack 誘発 [gachinko {until_lose, stoppable, as: wins},
  break {player: opp, count: {var: wins}}]。op break の count は
  expr で、{var: wins} の後続参照は dmr05-v02 の partial 自身が
  repeat で使っている確立形。公式QA（qa/42524: 効果でブレイクする
  5枚は同時。2023.5.17 の一連のQA: 破壊・入れ替わりでこのクリーチャー
  が場を離れても能力のブレイクは効果として成立する前提）により、
  ラウンド169の「ブレイク数を変数で増やす」読み（=攻撃のブレイク
  への加算）ではなく効果ブレイクが正しい。本文に「さらに」が
  無いことも形Aとの対比で裏づけになる。

proto: T917 形B / T918 形A。山札の上（ガチンコの公開順）は
setup の deck 指定が逆順（最後尾が一番上）になる作法で脚本する。
公開はコスト比較（T201 = コスト9 が勝ち札、T002 = コスト2 が負け札）。
ブレイクの観測は choose_shields 決定の列（min = そのブレイクの枚数、
その時点の相手シールド数）で行う。効果ブレイクは誘発の中で
攻撃自身のブレイクより先に現れる。
"""
import os

os.environ.setdefault("DMSIM_SKIP_CONVERTED", "1")

from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402
from tests.conftest import setup  # noqa: E402

TABLES = load_tables()
IDS = ("T917", "T918")


def _rules():
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _shields(e, p):
    return len(e.zlist("shield", p))


def _attacker_cid(e, defn):
    for c in e.zlist("bz", 0):
        card = e.s.cards[c]
        if card.defn == defn and card.controller == 0 and card.top_of < 0:
            return c
    return None


def _drive(e, handler=None, turns=1, max_steps=500):
    for _ in range(max_steps):
        if e.s.turn > turns:
            break
        d = e.advance()
        if d is None:
            break
        if e.s.turn > turns:   # 次ターンへ跨いだ advance は答えずに止める
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


def _handler(attack=None, yes_no=(), block_with=None, breaks_log=None):
    state = {"attacked": False, "yn": list(yes_no)}

    def h(e, d):
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "choose_shields" and breaks_log is not None:
            cid = _attacker_cid(e, attack)
            breaks_log.append({"count": d.get("min"),
                               "shields": _shields(e, 1),
                               "opp_hand": len(_defns(e, "hand", 1)),
                               "power": e.chars_ro(cid)["power"] if cid is not None else None})
            return False   # 回答は _drive の既定（range(min)）に任せる
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
        if kind == "block":
            if block_with:
                for i, k in enumerate(keys):
                    if k.startswith("bz:" + block_with):
                        e.answer([i])
                        return True
            e.answer([keys.index("no_block")])
            return True
        return False

    return h


def test_proto_parse():
    for cid in IDS:
        parse_card(proto_card(cid), TABLES)


# ---- 形B（T917 = R.S.F.K.型、効果ブレイク） ----

def test_b_two_wins_break_during_trigger_then_attack_breaks_one():
    e = setup(_rules(), {"bz": ["T917"],
                         "deck": ["T002", "T002", "T201", "T201"]},
              {"deck": ["T002", "T201", "T002", "T002"]})
    log = []
    _drive(e, _handler(attack="T917", yes_no=[0, 0, 1], breaks_log=log))
    # 1件目 = 誘発中の効果ブレイク2枚、2件目 = 攻撃自身のブレイク1枚。
    # 2件目の時点でシールドは3枚（効果ブレイクが先に着地している）。
    assert [(x["count"], x["shields"]) for x in log] == [(2, 5), (1, 3)]
    assert log[1]["opp_hand"] == 2    # 割れたシールドは相手の手札へ
    assert _shields(e, 1) == 2


def test_b_blocked_after_effect_break():
    # 判別テスト: 効果ブレイクはブロックより前に起きる。攻撃のブレイク
    # への加算（形A読み）なら、ブロックされた攻撃では1枚も割れない。
    e = setup(_rules(), {"bz": ["T917"],
                         "deck": ["T002", "T002", "T002", "T201"]},
              {"bz": ["T004"],
               "deck": ["T002", "T201", "T002", "T002"]})
    log = []
    _drive(e, _handler(attack="T917", yes_no=[0, 1],
                       block_with="T004", breaks_log=log))
    assert [(x["count"], x["shields"]) for x in log] == [(1, 5)]
    assert _shields(e, 1) == 4        # ブロックされても効果の1枚は割れている
    assert "T004" in _defns(e, "graveyard", 1)   # 3000 は 5000 に負ける
    assert "T917" in _defns(e, "bz", 0)


def test_b_lose_immediately_no_effect_break():
    e = setup(_rules(), {"bz": ["T917"],
                         "deck": ["T002", "T002", "T201", "T002"]},
              {"deck": ["T002", "T002", "T002", "T201"]})
    log = []
    _drive(e, _handler(attack="T917", yes_no=[0], breaks_log=log))
    # 勝ち0回 → 効果ブレイクは count 0 の決定だけが出て1枚も割れず、
    # 攻撃自身の1枚だけが割れる
    assert [(x["count"], x["shields"]) for x in log] == [(0, 5), (1, 5)]
    assert _shields(e, 1) == 4


def test_b_win_then_lose_breaks_one():
    e = setup(_rules(), {"bz": ["T917"],
                         "deck": ["T002", "T002", "T201"]},
              {"deck": ["T002", "T201", "T002"]})
    log = []
    _drive(e, _handler(attack="T917", yes_no=[0, 0], breaks_log=log))
    assert [(x["count"], x["shields"]) for x in log] == [(1, 5), (1, 4)]
    assert _shields(e, 1) == 3


# ---- 形A（T918 = カイザー「勝」型、攻撃のブレイク数への加算） ----

def test_a_two_wins_power_and_breaks_scale():
    e = setup(_rules(), {"bz": ["T918"],
                         "deck": ["T002", "T002", "T201", "T201"]},
              {"bz": ["T004", "T004"],
               "deck": ["T002", "T201", "T002", "T002"]})
    log = []
    _drive(e, _handler(attack="T918", yes_no=[0, 0, 1], breaks_log=log))
    # 誘発中はシールドを割らない（形Bとの対比）。ブレイクは攻撃自身の
    # 1件だけで、枚数は W・ブレイカー2 + 勝ち数2 = 4。パワーは +6000×2。
    assert [(x["count"], x["shields"]) for x in log] == [(4, 5)]
    assert log[0]["power"] == 19000
    # repeat の破壊でブロッカー2体とも墓地へ
    assert _defns(e, "graveyard", 1).count("T004") == 2
    assert _shields(e, 1) == 1


def test_a_lose_immediately_plain_w_breaker():
    e = setup(_rules(), {"bz": ["T918"],
                         "deck": ["T002", "T002", "T201", "T002"]},
              {"deck": ["T002", "T002", "T002", "T201"]})
    log = []
    _drive(e, _handler(attack="T918", yes_no=[0], breaks_log=log))
    assert [(x["count"], x["shields"]) for x in log] == [(2, 5)]
    assert log[0]["power"] == 7000    # 勝ち0回 → 増幅なし
    assert _shields(e, 1) == 3        # 通常の W・ブレイカー2枚だけ
