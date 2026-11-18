"""語彙パイロット第217弾: reversal_strike（逆転撃）。

逆転撃 {支払い}: クリーチャーが自分を攻撃する時、その攻撃中にまだ
「逆転撃」を使っていなければ、この呪文を自分の手札からコストを支払わずに
唱えてもよい。そうしたら、次の自分のターンのはじめに {支払い} を支払う。
支払えなければ、自分はゲームに負ける。

イディオム（既存部品の組み合わせ＋新規 op 1つ）:
  declare {zone: hand,
           when: {event: attack, subject: {owner: opp}, target: player},
           if: {not: {marked: {name: reversal_strike, scope: attack}}},
           effect: [if {not marked} then
                      [mark scope: attack,
                       play_free {ref: self},
                       delayed_trigger {when: {event: turn_start, player: you},
                                        duration: permanent,
                                        effect: [pay_or_lose {cost, civs}]}]]}
- 攻撃中の共有ゲートは mark の scope: attack（第216弾の game と対）。
  使用宣言は窓の中でまとめて選ばれるため、効果の解決時にも再確認する
  （第216弾の同時トリガー再確認と同じ形）。
- delayed_trigger の duration は until_next_own_turn_start ではダメ:
  ターン開始ステップで失効処理が先に走り、turn_start の記録に間に合わない。
  permanent＋once（既定）で「次の自分のターンのはじめに一度だけ」にする
  （登録カードにも同じ形の先例がある）。
- 支払いの {ll03} 記法は「合計03・そのうち光2枚」の形: pay_or_lose の
  {cost: 合計, civs: [必要文明を1枚分ずつ並べたもの]} に写す。
  印刷コストとは別物（例: 印刷3でも支払いは {ww02} = 合計2）。

新規 op pay_or_lose {cost, civs}: 指定コストをマナで支払い、支払えなければ
ゲームに負ける。支払いはカードを出す行為ではないので、_mana_choices を
raw_cost で数える（コスト増減・水晶ソウル・ブーストは適用しない。
マナの数字そのものを変える mod mana_number は効く）。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T557", "T558")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def _run(e, declare_pick, attack_turns=(), creature_attack=False, stop_turn=None,
         p0_attack_turns=(), max_iter=900):
    """汎用ドライバ。declare_pick(keys) は declare_attack（P0）の回答 index リスト。
    ログ [(turn, kind, player, keys)] を返す。stop_turn を過ぎたら止める
    （支払いのタップ状態など、そのターン時点の状態を検証するため）。"""
    log = []
    for _ in range(max_iter):
        if e.s.result is not None:
            break
        if stop_turn is not None and e.s.turn > stop_turn:
            break
        d = e.advance()
        if d is None:
            break
        kind, p = d["kind"], d.get("player")
        keys = [o["key"] for o in d["options"]]
        log.append((e.s.turn, kind, p, tuple(keys)))
        if kind == "declare_attack" and p == 0:
            e.answer(declare_pick(keys))
        elif kind == "attack" and p == 1 and e.s.turn in attack_turns:
            if creature_attack:
                k = next(k for k in keys if k.startswith("attack:") and not k.endswith(":player"))
            else:
                k = next(k for k in keys if k.startswith("attack:") and k.endswith(":player"))
            e.answer([keys.index(k)])
        elif kind == "attack" and p == 0 and e.s.turn in p0_attack_turns:
            k = next(k for k in keys if k.startswith("attack:") and k.endswith(":player"))
            e.answer([keys.index(k)])
        elif kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return log


def _zone_defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _tapped_mana(e, p):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def test_strike_casts_free_and_pays_next_turn(rules):
    """攻撃時に無料で唱えられ（ドロー1）、次の自分のターンのはじめに
    {ll03}（合計3・光2枚）を払う。支払いはアンタップ後に行われる。"""
    e = setup(rules,
              {"hand": ["T557"], "mana": ["T004", "T004", "T001", "T001"]},
              {"bz": ["T001"]}, filler="T002")
    log = _run(e, lambda keys: [i for i, k in enumerate(keys) if k.startswith("declare:")],
               attack_turns=(2,), stop_turn=3)
    # 唱えた呪文は墓地にあり、手札には残っていない
    assert "T557" in _zone_defns(e, "graveyard", 0)
    assert "T557" not in _zone_defns(e, "hand", 0)
    # 次の自分のターンのはじめに4枚中3枚をタップして払い、ゲームは続く
    # （支払いのタイミングそのものは test_strike_again_on_next_attack の
    # pay_mana 決定ログ [3, 5] で固定する。ここでは組が一意に定まるため
    # 決定を経ずに支払われる）
    assert _tapped_mana(e, 0) == 3
    assert e.s.result is None


def test_cannot_pay_loses(rules):
    """次の自分のターンのはじめに支払えなければ負ける（マナ合計2 < 3）。"""
    e = setup(rules,
              {"hand": ["T557"], "mana": ["T004", "T001"]},
              {"bz": ["T001"]}, filler="T002")
    _run(e, lambda keys: [i for i, k in enumerate(keys) if k.startswith("declare:")],
         attack_turns=(2,))
    assert e.s.result is not None and e.s.result["winner"] == 1


def test_gate_shared_once_per_attack(rules):
    """2枚の逆転撃を同じ攻撃で両方宣言しても、解決するのは1枚だけ。
    もう1枚は手札に残り、支払いの義務も1回分だけ発生する。"""
    e = setup(rules,
              {"hand": ["T557", "T558"], "mana": ["T004", "T004", "T001", "T001"]},
              {"bz": ["T001"]}, filler="T002")
    log = _run(e, lambda keys: [i for i, k in sorted(enumerate(keys), key=lambda t: t[1])
                                if k.startswith("declare:")],
               attack_turns=(2,), stop_turn=3)
    grave = _zone_defns(e, "graveyard", 0)
    hand = _zone_defns(e, "hand", 0)
    assert ("T557" in grave) != ("T558" in grave)   # どちらか1枚だけが唱えられた
    assert ("T557" in hand) != ("T558" in hand)     # もう1枚は手札に残る
    # 支払いの義務は1回分だけ: T557 の分（合計3）が払われてゲームが続く。
    # T558 が唱えられていれば水マナが無く支払えずに負けているはず
    assert _tapped_mana(e, 0) == 3
    assert e.s.result is None


def test_strike_again_on_next_attack(rules):
    """印は攻撃ごとなので、次の攻撃では別の逆転撃を使える。
    支払いの義務はそれぞれ次の自分のターンのはじめに発生する。"""
    e = setup(rules,
              {"hand": ["T557", "T557"],
               "mana": ["T004", "T004", "T004", "T004", "T001", "T001"]},
              {"bz": ["T001"]}, filler="T002")
    log = _run(e, lambda keys: [i for i, k in enumerate(keys) if k.startswith("declare:")][:1],
               attack_turns=(2, 4), stop_turn=5)
    assert _zone_defns(e, "graveyard", 0).count("T557") == 2
    pays = [lg[0] for lg in log if lg[1] == "pay_mana" and lg[2] == 0]
    assert pays == [3, 5]
    assert e.s.result is None


def test_no_strike_when_creature_attacked(rules):
    """自分のクリーチャーへの攻撃では逆転撃は使えない（「自分を攻撃する時」）。
    攻撃対象にできるよう、自分のクリーチャーはターン1に攻撃してタップしておく。"""
    e = setup(rules,
              {"hand": ["T557"], "bz": ["T001"], "mana": ["T004", "T004", "T001"]},
              {"bz": ["T001"]}, filler="T002")
    log = _run(e, lambda keys: [i for i, k in enumerate(keys) if k.startswith("declare:")],
               attack_turns=(2,), creature_attack=True, stop_turn=2, p0_attack_turns=(1,))
    assert not [lg for lg in log if lg[1] == "declare_attack" and lg[2] == 0
                and any(k.startswith("declare:T557") for k in lg[3])]
    assert "T557" in _zone_defns(e, "hand", 0)
    assert not [lg for lg in log if lg[1] == "pay_mana" and lg[2] == 0]
