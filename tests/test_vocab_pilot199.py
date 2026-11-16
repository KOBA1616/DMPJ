"""語彙パイロット第199弾: chosen_trigger（相手に選ばれた時）＋ must_be_chosen。

- 「相手がこのクリーチャーを選んだ時」の誘発自体は既存だった: セレクタの
  決定経路（selectors.select の通常経路と合計制限経路）が、選ぶ側と別の
  コントローラーのバトルゾーンのカードが選ばれた時に
  {ev: "choose", subject, player: chooser} を誘発収集へ流している。
  本弾はその挙動を proto で固定する（「すべて」は選んだことにならない、
  自分の選択では誘発しない、も含む）。対象が1体だけだと選択決定は
  自動解決されて表面化しないため、検証は唱えた直後の手札増減で見る。
- 新規は mod `must_be_chosen: true`（「相手が自分のクリーチャーを選ぶ時、
  相手は可能ならこのクリーチャーを選ぶ」）: セレクタの be_chosen フィルタの
  直後で、must_be_chosen を持つ候補がいるコントローラーの他の
  クリーチャーを候補から外す。このクリーチャー自体が候補にいない
  効果では制限しない。制限が効くと候補が1体になり決定は自動解決される。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T498", "T499", "T500", "T501")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def test_invalid_must_be_chosen():
    base = {"id": "test-mbc", "name": "試験不良", "types": ["creature"],
            "civs": ["nature"], "cost": 3, "power": 2000, "mana": 1,
            "abilities": [{"kind": "static", "affects": "self",
                           "mod": {"must_be_chosen": {"first_only": True}}}],
            "source": {"official": "test-mbc", "review": "pending"}}
    with pytest.raises(DefError):
        parse_card(base, TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _cast(e, caster, spell, target_key=None, limit=200):
    """caster が spell を唱える。戻り値: (対象選択で提示されたキー一覧 or None,
    唱える直前の p0 の手札枚数, 解決直後の p0 の手札枚数)。"""
    offered = None
    hand_before = None
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if hand_before is None and d["kind"] == "main" \
                and d.get("player") == caster and f"play:{spell}" in keys:
            hand_before = len(e.zlist("hand", 0))
            e.answer([keys.index(f"play:{spell}")])
            continue
        if hand_before is not None:
            if d["kind"] == "choose_cards" and offered is None:
                offered = list(keys)
                if target_key is not None and target_key in keys:
                    e.answer([keys.index(target_key)])
                else:
                    e.answer(list(range(d["min"])))
                continue
            if d["kind"] in ("attack", "charge"):
                return offered, hand_before, len(e.zlist("hand", 0))
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return offered, hand_before, len(e.zlist("hand", 0))


def _in_gy(e, defn, player=0):
    return any(e.s.cards[c].defn == defn for c in e.zlist("graveyard", player))


def _in_bz(e, defn, player=0):
    return any(e.s.cards[c].defn == defn and e.s.cards[c].controller == player
               for c in e.zlist("bz", player))


def test_choose_trigger_fires_on_opponent_target(rules):
    """相手の破壊呪文に選ばれると、破壊されても誘発して引く（手札 +1）。"""
    e = setup(rules, {"bz": ["T499"], "hand": ["T002", "T002"]},
              {"hand": ["T056"], "mana": ["T082"] * 3, "bz": ["T001"]},
              filler="T002")
    _, before, after = _cast(e, 1, "T056")
    assert _in_gy(e, "T499")
    assert after - before == 1


def test_choose_trigger_not_on_own_choice(rules):
    """自分の効果で選んだ時は誘発しない（判別。手札は呪文の分だけ減る）。"""
    e = setup(rules, {"bz": ["T499"], "hand": ["T501", "T002"],
                      "mana": ["T082"] * 3},
              {"bz": ["T001"]}, filler="T002")
    _, before, after = _cast(e, 0, "T501", "bz:T499:0")
    assert _in_gy(e, "T499")
    assert after - before == -1


def test_choose_trigger_not_on_destroy_all(rules):
    """「すべて破壊」は選んだことにならない（判別。手札は変わらない）。"""
    e = setup(rules, {"bz": ["T499"], "hand": ["T002", "T002"]},
              {"hand": ["T500"], "mana": ["T082"] * 5, "bz": ["T001"]},
              filler="T002")
    _, before, after = _cast(e, 1, "T500")
    assert _in_gy(e, "T499")
    assert after - before == 0


def test_must_be_chosen_restricts_opponent(rules):
    """T498 がいると、相手の単体破壊は T498 に自動で決まる（T001 は無事）。
    対照（T499）では選択決定が両方を提示する。"""
    e = setup(rules, {"bz": ["T498", "T001"]},
              {"hand": ["T056"], "mana": ["T082"] * 3, "bz": ["T001"]},
              filler="T002")
    offered, _, _ = _cast(e, 1, "T056")
    assert offered is None                    # 候補が1体に絞られ自動解決
    assert _in_gy(e, "T498")
    assert _in_bz(e, "T001")
    e = setup(rules, {"bz": ["T499", "T001"], "hand": ["T002", "T002"]},
              {"hand": ["T056"], "mana": ["T082"] * 3, "bz": ["T001"]},
              filler="T002")
    offered, _, _ = _cast(e, 1, "T056", "bz:T499:0")
    assert offered is not None
    assert any("T499" in k for k in offered) and any("T001" in k for k in offered)


def test_must_be_chosen_not_for_own_choice(rules):
    """自分の選択は制限されない（判別）。"""
    e = setup(rules, {"bz": ["T498", "T001"], "hand": ["T501"],
                      "mana": ["T082"] * 3},
              {"bz": ["T001"]}, filler="T002")
    offered, _, _ = _cast(e, 0, "T501", "bz:T001:0")
    assert offered is not None
    assert any("T498" in k for k in offered) and any("T001" in k for k in offered)
    assert _in_gy(e, "T001")
    assert _in_bz(e, "T498")


def test_choose_trigger_mass_destroy_by_own_power(rules):
    """T502: 選ばれた時、自分のパワー以下の相手クリーチャーをすべて破壊する
    （filter の power_le に {power_of: self} が効くことの確認）。"""
    e = setup(rules, {"bz": ["T502"]},
              {"hand": ["T056"], "mana": ["T082"] * 3, "bz": ["T001", "T491"]},
              filler="T002")
    _cast(e, 1, "T056", "bz:T502:0")
    assert _in_gy(e, "T502")                   # 選ばれて破壊された
    assert _in_gy(e, "T001", 1)                # パワー2000 <= 5000: 破壊
    assert _in_bz(e, "T491", 1)                # パワー7000 > 5000: 無事
