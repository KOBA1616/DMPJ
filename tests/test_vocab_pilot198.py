"""語彙パイロット第198弾: ggg_condition（G・G・G の条件違い）のイディオム確認。

rejects の ggg_condition 9件は、第167弾で G・G・G 本体（手札1枚以下条件）
を実装した後に残った複合カード群。unsupported は全件「G・G・G」の文言だけで、
実際の不足は GGG の当て方とカードごとの他条項だった。本弾は新規エンジン
語彙なしで、以下の当て方を proto で固定する:

- 自分自身のコスト軽減: static {zone: hand, affects: self, if: 手札<=1,
  mod: {cost: -N}}（第167弾 T271 の形）
- 自分へのキーワード付与: static {affects: self, if: 手札<=1,
  mod: {grant: [...]}}。「マッハファイター」の付与はキーワードではなく
  allow attack_creature（other {tapped: false}）で表す
- 複合条件の free_if: {all: [手札<=1, {not: {exists: 指定名が場にいる}}]}
- 「各ターン、相手がはじめて攻撃する時、可能ならこのクリーチャーを攻撃する」:
  static {affects: self, if: {cmp: [{turn_count: {kind: attack, owner: opp}},
  "==", 0]}, mod: {must_be_attacked: true}}
- 攻撃時の公開→条件つきで出す: choose で event.subject を束ね（atk）、
  look の pile から filter（種族＋cost_le {cost_of: atk}）で hit を分ける
  （dm21-013 の登録形と同じ骨格）
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T491", "T492", "T493", "T494", "T496")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def _play_keys(e, player=0):
    return [o["key"] for o in e._play_options(player)]


def _keys(d):
    return [o["key"] for o in d["options"]]


def test_ggg_cost_reduction(rules):
    """T491: 手札1枚（このカードだけ）なら実質コスト1で出せる。2枚なら出せない。"""
    e = setup(rules, {"hand": ["T491"], "mana": ["T277"]}, {"bz": ["T001"]},
              filler="T002")
    assert "play:T491" in _play_keys(e)
    e = setup(rules, {"hand": ["T491", "T002"], "mana": ["T277"]}, {"bz": ["T001"]},
              filler="T002")
    assert "play:T491" not in _play_keys(e)


def test_ggg_free_if_compound(rules):
    """T493: 手札1枚以下＋指定名が場にいなければ無料。どちらか欠けると出ない。"""
    e = setup(rules, {"hand": ["T493"]}, {"bz": ["T001"]}, filler="T002")
    assert "play:T493:free" in _play_keys(e)
    e = setup(rules, {"hand": ["T493"], "bz": ["T487"]}, {"bz": ["T001"]},
              filler="T002")
    assert "play:T493:free" not in _play_keys(e)
    e = setup(rules, {"hand": ["T493", "T002"]}, {"bz": ["T001"]}, filler="T002")
    assert "play:T493:free" not in _play_keys(e)


def _summon_then_attack_keys(e, defn, limit=120):
    """defn を召喚し、そのターンの攻撃決定で提示されたキーを返す。"""
    played = False
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not played and d["kind"] == "main" and f"play:{defn}" in keys:
            e.answer([keys.index(f"play:{defn}")])
            played = True
            continue
        if played and d["kind"] == "attack" and d.get("player") == 0:
            return keys
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return []


def test_ggg_grant_speed_attacker(rules):
    """T492: 手札1枚以下で召喚すると即攻撃できる。手札が残ると召喚酔い。"""
    e = setup(rules, {"bz": ["T005"], "hand": ["T492"], "mana": ["T277"] * 3},
              {"bz": ["T001"]}, filler="T002")
    keys = _summon_then_attack_keys(e, "T492")
    assert "attack:T492:player" in keys
    e = setup(rules, {"bz": ["T005"], "hand": ["T492", "T001", "T001"],
                      "mana": ["T277"] * 3},
              {"bz": ["T001"]}, filler="T002")
    keys = _summon_then_attack_keys(e, "T492")
    assert "attack:T492:player" not in keys
    assert "attack:T005:player" in keys


def test_first_attack_taunt(rules):
    """T494: 相手のそのターン最初の攻撃は（可能なら）このクリーチャーへ。
    2回目の攻撃はプレイヤーへ向けてよい。"""
    e = setup(rules, {"bz": ["T494"]}, {"bz": ["T001", "T001"]}, filler="T002")
    p1_attack_keys = []
    tapped_self = False
    for _ in range(200):
        d = e.advance()
        if d is None or len(p1_attack_keys) >= 2:
            break
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 and not tapped_self:
            # 自分のターン: T494 で攻撃してタップ状態にする
            if "attack:T494:player" in keys:
                e.answer([keys.index("attack:T494:player")])
                tapped_self = True
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "attack" and d.get("player") == 1:
            p1_attack_keys.append(list(keys))
            # どちらの攻撃も、提示された最初のクリーチャー対象（あれば）で実行
            hit = next((k for k in keys if k.endswith(":T494")), None)
            if hit is not None:
                e.answer([keys.index(hit)])
            elif "pass" in keys and len(p1_attack_keys) >= 2:
                e.answer([keys.index("pass")])
            else:
                e.answer([0])
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert tapped_self and len(p1_attack_keys) == 2
    first, second = p1_attack_keys
    assert any(k.endswith(":T494") for k in first)
    assert not any(k.endswith(":player") for k in first)   # プレイヤー攻撃は選べない
    assert any(k.endswith(":player") for k in second)      # 2回目は自由


def _attack_and_resolve(e, limit=200):
    """T496 で攻撃し、誘発の解決まで進める（look の選択は先頭を取る）。"""
    attacked = False
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 and not attacked:
            if "attack:T496:player" in keys:
                e.answer([keys.index("attack:T496:player")])
                attacked = True
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            continue
        if attacked and d["kind"] == "charge":
            break   # 次のターンに入った = 解決済み
        if d["kind"] == "choose_cards" and keys:
            e.answer([0])
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def test_attack_reveal_put_qualifying(rules):
    """T496: 公開したカードがビートジョッキーでコスト以下なら出る。"""
    e = setup(rules, {"bz": ["T496"]}, {"bz": ["T001"]}, filler="T496")
    _attack_and_resolve(e)
    n = sum(1 for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T496")
    assert n == 2


def test_attack_reveal_put_non_qualifying(rules):
    """T496: 条件に合わないカードは山札の下へ（判別）。"""
    e = setup(rules, {"bz": ["T496"]}, {"bz": ["T001"]}, filler="T002")
    _attack_and_resolve(e)
    n = sum(1 for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T496")
    assert n == 1


def test_turn_end_return_if_untapped(rules):
    """T497: 自分のターン終わりにアンタップしていれば手札に戻る。
    攻撃してタップしていれば戻らない（exists {ref: self, filter: tapped} の判別）。"""
    # 攻撃しない → 戻る
    e = setup(rules, {"bz": ["T497"]}, {"bz": ["T001"]}, filler="T002")
    for _ in range(120):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if any(e.s.cards[c].defn == "T497" for c in e.zlist("hand", 0)):
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert any(e.s.cards[c].defn == "T497" for c in e.zlist("hand", 0))
    # 攻撃する → タップしたまま自分のターンが終わるので戻らない
    e = setup(rules, {"bz": ["T497"]}, {"bz": ["T001"]}, filler="T002")
    for _ in range(120):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 1:
            break   # 相手のターンに入った（自分のターンは終わった）
        if d["kind"] == "attack" and d.get("player") == 0 and "attack:T497:player" in keys:
            e.answer([keys.index("attack:T497:player")])
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert any(e.s.cards[c].defn == "T497" for c in e.zlist("bz", 0))
