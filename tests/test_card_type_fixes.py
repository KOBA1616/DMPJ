"""カードタイプ別処理の整合性修正（2026-11-27 koba 裁定）。

- シンカパワー（進化元になる時）は、効果で進化クリーチャー（NEO 等を含む）の下に置かれた時も発動する
  （創世竜 Drache der’Zen 型）。進化でないクリーチャーの下では発動しない。
- ドリーム・エレメントは、自分のバトルゾーンに同名のドリーム・エレメントがある間、出せない（817.2）。
  すでに複数ある場合はそのまま残る（817.3）。
- 通常フィールド（D2 でないもの）は枚数制限なし。D2 フィールドだけが 1 枚（703.4l）。
"""
import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules

X_CARDS = """
cards:
  - id: XS1
    name: 試験シンカパワーのタマシード
    civs: [nature]
    cost: 1
    power: 0
    types: [tamaseed]
    text: シンカパワー：このタマシードが進化元になる時、カードを１枚引く。
    abilities:
      - kind: trigger
        when: {event: evolve_base, subject: self}
        effect:
          - {op: draw, count: 1}
  - id: XE1
    name: 試験進化クリーチャー
    civs: [nature]
    cost: 3
    power: 3000
    types: [creature, evolution]
    races: [テスト]
    evolve_from: {civs: [nature]}
    text: 進化
  - id: XP1
    name: 試験通常クリーチャー
    civs: [nature]
    cost: 1
    power: 1000
    types: [creature]
    races: [テスト]
    text: ""
  - id: XC1
    name: 試験下置きクリーチャー（進化の下）
    civs: [nature]
    cost: 1
    power: 1000
    types: [creature]
    races: [テスト]
    text: このクリーチャーが出た時、自分のタマシードを１枚、自分の進化クリーチャー１体の下に置く。
    abilities:
      - kind: trigger
        when: {event: move, subject: self, to: bz}
        effect:
          - op: put_under
            select: {zone: bz, owner: you, count: 1, filter: {types: [tamaseed]}}
            onto: {zone: bz, owner: you, count: 1, filter: {types: [evolution]}}
  - id: XC2
    name: 試験下置きクリーチャー（通常の下）
    civs: [nature]
    cost: 1
    power: 1000
    types: [creature]
    races: [テスト]
    text: このクリーチャーが出た時、自分のタマシードを１枚、自分のクリーチャー１体の下に置く。
    abilities:
      - kind: trigger
        when: {event: move, subject: self, to: bz}
        effect:
          - op: put_under
            select: {zone: bz, owner: you, count: 1, filter: {types: [tamaseed]}}
            onto: {zone: bz, owner: you, count: 1, filter: {types: [creature], not_types: [evolution]}}
"""


@pytest.fixture(scope="session")
def xr(tmp_path_factory):
    p = tmp_path_factory.mktemp("cardtypefix") / "x_cards.yaml"
    p.write_text(X_CARDS, encoding="utf-8")
    return load_rules(card_yaml_files() + [p])


def _run(e, steps=120):
    """メインで最初の play を行い、効果が解決して再びメインの選択に戻るまで進める。"""
    played = False
    for _ in range(steps):
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        if played and d["kind"] in ("main", "attack"):
            return   # 効果が解決し終わって、次の選択（攻撃・メイン）に戻った
        if d["kind"] == "main":
            if played:
                return
            e.h0 = _hand(e)   # 出す直前の手札枚数（出すカードを含む）
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:"))])
            played = True
            continue
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))


def _hand(e):
    return len(e.zlist("hand", 0))


def test_shinka_power_fires_when_put_under_evolution(xr):
    e = setup(xr, {"hand": ["XC1"], "bz": ["XS1", "XE1"], "mana": ["T001"]})
    _run(e)
    top = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "XE1")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["XS1"]
    assert _hand(e) == e.h0 - 1 + 1   # XC1 を出して 1 枚減り、シンカパワーで 1 枚引く


def test_shinka_power_not_fired_under_non_evolution(xr):
    e = setup(xr, {"hand": ["XC2"], "bz": ["XS1", "XP1"], "mana": ["T001"]})
    _run(e)
    top = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "XP1")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["XS1"]
    assert _hand(e) == e.h0 - 1   # 引いていない


# ---------- ドリーム同名制限（817.2 / 817.3） ----------

DREAM_CARDS = """
cards:
  - id: XD1
    name: 試験ドリーム甲
    civs: [nature]
    cost: 1
    power: 1000
    types: [creature, dream_creature]
    races: [テスト]
    text: ""
  - id: XD2
    name: 試験ドリーム乙
    civs: [nature]
    cost: 1
    power: 1000
    types: [creature, dream_creature]
    races: [テスト]
    text: ""
"""


@pytest.fixture(scope="session")
def dr(tmp_path_factory):
    p = tmp_path_factory.mktemp("dreamfix") / "d_cards.yaml"
    p.write_text(DREAM_CARDS, encoding="utf-8")
    return load_rules(card_yaml_files() + [p])


def _can_play(e, defn):
    cid = next(c for c in e.zlist("hand", 0) if e.s.cards[c].defn == defn)
    return e._can_play_face(cid, 0, None)


def test_dream_same_name_cannot_be_played(dr):
    e = setup(dr, {"hand": ["XD1"], "bz": ["XD1"], "mana": ["T001"]})
    assert not _can_play(e, "XD1")


def test_dream_alone_and_other_name_can_be_played(dr):
    e = setup(dr, {"hand": ["XD1"], "mana": ["T001"]})
    assert _can_play(e, "XD1")
    e = setup(dr, {"hand": ["XD1"], "bz": ["XD2"], "mana": ["T001"]})
    assert _can_play(e, "XD1")


def test_dream_already_two_stay_817_3(dr):
    """817.3: 何らかの方法で同名のドリーム・エレメントが2つ以上存在することになっても、両方残る。"""
    e = setup(dr, {"bz": ["XD1", "XD1"]})
    assert [e.s.cards[c].defn for c in e.bz_tops(0)] == ["XD1", "XD1"]
    e.advance()
    assert len(e.bz_tops(0)) == 2


def test_dream_other_players_same_name_is_not_blocked(dr):
    """持ち主ごとの制限: 相手の場に同名がいても出せる。"""
    e = setup(dr, {"hand": ["XD1"], "mana": ["T001"]}, {"bz": ["XD1"]})
    assert _can_play(e, "XD1")
