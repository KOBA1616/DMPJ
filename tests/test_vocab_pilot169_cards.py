"""第169弾 サバキZ の再変換ラウンド205: 登録形の検証と実挙動テスト。

対象15件（sabaki_z 単独ギャップ）。新規登録14件、差し戻し1件
（dmex19-s5 → break_preparation。解けた節は partial に残す）。
"""
import json
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import card_yaml_files, load_rules, load_tables, parse_card

ROOT = Path(__file__).parent.parent
TABLES = load_tables()


@pytest.fixture(scope="module")
def rules_all():
    """converted.yaml を含むルール（session の rules は converted を除く）。"""
    return load_rules([*card_yaml_files(), ROOT / "data/cards/converted.yaml"])

TARGETS = ["dm23ex2-042", "dmbd07-b-005", "dmex02-024", "dmex08-166",
           "dmex17-006", "dmex17-026", "dmrp07-013", "dmrp07-032",
           "dmrp07-063", "dmrp07-064", "dmrp08-031", "dmrp08-032",
           "dmsd07-004", "dmsd07-005"]
BOUNCED = {"dmex19-s5": "break_preparation"}


def _converted():
    cards = {}
    for doc in yaml.safe_load_all(open(ROOT / "data/cards/converted.yaml")):
        if doc:
            for c in doc["cards"]:
                cards[c["id"]] = c
    return cards


def _rejects():
    out = {}
    for line in open(ROOT / "data/cards/raw/rejects.jsonl"):
        r = json.loads(line)
        out[r["id"]] = r
    return out


def _sabaki_trigger(card):
    abs_ = card.get("abilities") or []
    faces = card.get("faces") or []
    for f in faces:
        abs_ += f.get("abilities") or []
    return [a for a in abs_ if a.get("kind") == "trigger"
            and a.get("zone") == "hand"
            and (a.get("when") or {}).get("emblem") is True]


def test_registered_cards_parse():
    cards = _converted()
    rejects = _rejects()
    for cid in TARGETS:
        assert cid in cards, cid
        assert cid not in rejects, cid
        parse_card(cards[cid], TABLES)
        assert _sabaki_trigger(cards[cid]), cid  # サバキZ誘発を持つ
        assert (cards[cid].get("source") or {}).get("unsupported") == []
    # 呪文は唱えた後のシールド置換を持つ
    for cid in ("dm23ex2-042", "dmbd07-b-005", "dmex17-026", "dmrp07-013",
                "dmrp07-032", "dmrp07-063", "dmrp07-064", "dmsd07-005"):
        reps = [a for a in cards[cid]["abilities"] if a.get("kind") == "replace"]
        assert reps and reps[0].get("zone") == "hold", cid
    # alias が登録に含まれる
    assert "promoy17-087" in cards["dmbd07-b-005"]["source"]["aliases"]
    assert "dmbd07-b-006" in cards["dmex08-166"]["source"]["aliases"]
    assert "dmrp06-s03" in cards["dmex17-006"]["source"]["aliases"]
    assert "dmrp07-003" in cards["dmex17-026"]["source"]["aliases"]
    # 差し戻し: 新ギャップで rejects に残り、解けた節が partial にある
    for cid, gap in BOUNCED.items():
        assert cid not in cards
        row = rejects[cid]
        assert row["gaps"] == [gap], row["gaps"]
        parse_card(row["partial"], TABLES)
        assert _sabaki_trigger(row["partial"]), cid
        assert [u["need"] for u in row["partial"]["source"]["unsupported"]] == [gap]


def _keys(d):
    return [o["key"] for o in d["options"]]


def _drive(e, play=None, yes_no="yes", max_steps=300):
    play = list(play or [])
    played = set()
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended before settling"
        keys = _keys(d)
        kind = d["kind"]
        if kind == "main" and d["player"] == 0:
            nxt = next((t for t in play if t not in played and f"play:{t}" in keys), None)
            if nxt is not None:
                played.add(nxt)
                e.answer([keys.index(f"play:{nxt}")])
                continue
            if played or not play:
                return
        if played and kind in ("charge", "attack"):
            return
        if kind == "pay_mana":
            e.answer([0])
        elif kind in ("choose_cards", "choose_shields"):
            e.answer(list(range(d["min"])))
        elif kind == "choose_replacement":
            e.answer([0])
        elif kind == "yes_no":
            e.answer([keys.index(yes_no)])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("did not settle")


def _defns(e, zone, player=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, player)]


def _shield_top(e, player=0):
    return e.zlist("shield", player)[0]


def test_dm23ex2_042_puts_metallca_and_goes_to_shield(rules_all):
    """dm23ex2-042: 手札からメタリカを出し、唱えた後はシールドの上へ。"""
    e = setup(rules_all, {"hand": ["dm23ex2-042", "T339"], "mana": ["T030"] * 5}, {})
    _drive(e, play=["dm23ex2-042"])
    assert "T339" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert "dm23ex2-042" not in _defns(e, "graveyard")
    top = _shield_top(e)
    assert e.s.cards[top].defn == "dm23ex2-042"
    assert e.s.cards[top].face_up is True
    assert e.s.cards[top].under


def test_dmex17_006_cip_and_discount(rules_all):
    """dmex17-006: CIPで山札上をシールド表向きへ。次に使う光カードが3安くなる。
    （マナは7枚用意する: 5枚で召喚し、残り2枚でT333が名目上唱えられないと
    ターンが自動で終わってしまい、軽減の選択肢が出ない）"""
    e = setup(rules_all, {"hand": ["dmex17-006", "T333"], "mana": ["T030"] * 7}, {})
    deck_before = len(e.zlist("deck", 0))
    _drive(e, play=["dmex17-006", "T333"])
    assert "dmex17-006" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert len(e.zlist("deck", 0)) == deck_before - 2  # CIPで1枚＋T333のドローで1枚
    # T333（光・コスト2）は軽減で0コストになり、唱えられてシールドの上へ
    top = _shield_top(e)
    assert e.s.cards[top].defn == "T333"
    assert e.s.cards[top].face_up is True
    assert len(e.zlist("mana", 0)) == 7  # T333の支払いマナは不要だった


def test_dmsd07_004_cip_taps_opp(rules_all):
    """dmsd07-004: 出た時、相手のクリーチャーを1体タップする。
    （手札にT333を残す: 手札が空だとメインが自動で終わり、相手のアンタップで
    タップが解けてしまうため。メインが戻った時点でタップを確認する）"""
    e = setup(rules_all, {"hand": ["dmsd07-004", "T333"], "mana": ["T030"] * 6},
              {"bz": ["T339"]})
    opp = next(c for c in e.bz_tops(1) if e.s.cards[c].defn == "T339")
    assert e.s.cards[opp].tapped is False
    _drive(e, play=["dmsd07-004"])
    assert e.s.cards[opp].tapped is True


def test_dmrp07_064_taps_opp_and_goes_to_shield(rules_all):
    """dmrp07-064: 相手クリーチャーをタップし、唱えた後はシールドの上へ。
    （公式テキストにアンタップ節は無いので no_untap_next は付けない。
    手札にT333を残し、メインが戻った時点でタップを確認する）"""
    e = setup(rules_all, {"hand": ["dmrp07-064", "T333"], "mana": ["T030"] * 4},
              {"bz": ["T339"]})
    opp = next(c for c in e.bz_tops(1) if e.s.cards[c].defn == "T339")
    _drive(e, play=["dmrp07-064"])
    assert e.s.cards[opp].tapped is True
    top = _shield_top(e)
    assert e.s.cards[top].defn == "dmrp07-064"
    assert e.s.cards[top].face_up is True


def test_dmrp08_032_attack_denied_until_shield_put(rules_all):
    """dmrp08-032: 今ターンにシールドが置かれていなければ相手プレイヤーを攻撃できない。"""
    e = setup(rules_all, {"bz": ["dmrp08-032"]}, {})
    mine = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "dmrp08-032")
    assert not e.permits(mine, "attack_player")
    e.s.turn_counters["hist:shield_put:0"] = 1  # このターンにシールドが置かれたことにする
    assert e.permits(mine, "attack_player")
