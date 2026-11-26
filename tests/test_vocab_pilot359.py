"""語彙パイロット第359弾: after_battle_bounce（ドリフト）。

センサス（rejects 1,974件を取り直し）: pure 1,826件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone 105 /
dragheart 45 / psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。残りは pure 1〜4件の小家族が多数で、
評価済み却下（第316〜320・355〜358弾）は再提案しない。
本弾で個別に評価して見送った候補: after_battle_trigger
（2件。dmrp09-074 は「勝ったクリーチャー」の勝者参照が要り、
dmrp14-072 は自己破壊で形が相異なり均一でない）、
cast_event_trigger（pure 1。詠唱イベント照合に加え唱えた
呪文のコスト参照が要る）、attack_event_trigger（pure 1。
シンパシーと《漢》への静的付与が残り条項単独では登録
できない）、block_event_target（pure 1。block 照合自体は
第320弾で確立だが、-9000 の継続付与とターン終わりの
タップ条件破壊が併記され重い）、bottom_deck_mill
（pure 1。山札の下からの選択が無く新語彙が要る）、
turn_draw_trigger（pure 1。ターン開始ドローを他のドローと
区別するイベント照合が無い）。範囲内・未評価で最小の
after_battle_bounce（pure 1件、multi にも現れない）を選定した:
dm27-042 パナオン「このクリーチャーがブロックする時、
バトルの後、ブロックされたクリーチャーを持ち主の手札に戻す」。
partial は骨格（keywords [blocker, cannot_attack]）で、
未解決は unsupported の本 gap 1件だけ。

結論はドリフト（追加語彙なし）。部品はすべて確立済み:
- block レコードの subject 照合（ブロッカー自身）は
  第320弾形B（dm20-045 先例）。
- 「バトルの後」は第319弾形Bの delayed_trigger
  {when: {event: attack_end, target: self},
  duration: during_attack}（dmr06-043 / dm22rp2x-061 の
  登録形そのもの）。delayed は状態レベルで保持され
  発生源がバトルで破壊されても発火する。
- 戻す対象は attack_end レコードの event.subject
  （攻撃したクリーチャー。第358弾が破壊対象に使った
  参照と同一）。バトルで既に破壊されていれば no-op。

proto T1079（パナオン型）/ T1080（パワー3000アタッカー）/
T1081（パワー500アタッカー）/ T1082（対照ブロッカー）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接包む（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

TRIGGER = {"kind": "trigger",
           "when": {"event": "block", "subject": "self"},
           "effect": [{"op": "delayed_trigger",
                       "when": {"event": "attack_end",
                                "target": "self"},
                       "duration": "during_attack",
                       "effect": [{"op": "move",
                                   "select": {"ref": "event.subject"},
                                   "to": "hand",
                                   "reason": "return"}]}]}
FORM = [TRIGGER]
KEYWORDS = ["blocker", "cannot_attack"]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1079")
    assert c["abilities"] == FORM
    assert c["keywords"] == KEYWORDS
    d = parse_card(copy.deepcopy(c), TABLES)
    assert TRIGGER in d.abilities


def test_form_raw_parse():
    d = parse_card({"id": "TX359", "name": "x",
                    "types": ["creature"], "civs": ["water"],
                    "cost": 3, "power": 1000,
                    "keywords": list(KEYWORDS),
                    "abilities": [copy.deepcopy(TRIGGER)]}, TABLES)
    assert TRIGGER in d.abilities


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive_attack(e, attacker, block_with=None):
    """p1 の attacker でプレイヤーを攻撃する。block_with が
    あればそのブロッカー（p0）でブロックし、無ければ
    ブロックしない。攻撃したターンの2つ先のターンまで
    進めて状態を返す。"""
    state = {"attacked": False, "attack_turn": None}
    for _ in range(1500):
        if state["attacked"] and e.s.turn >= state["attack_turn"] + 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack":
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and not state["attacked"]:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            hit = [i for i, k in enumerate(keys)
                   if block_with and k.startswith(f"bz:{block_with}:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


def test_blocked_attacker_bounced_after_battle_even_if_blocker_dies(rules):
    """パワー3000の攻撃をパナオン型（1000）がブロックすると、
    パナオン型はバトルで破壊されるが、バトルの後に攻撃
    クリーチャーは持ち主の手札に戻る。"""
    e = _build(rules, {"bz": ["T1079"]}, {"bz": ["T1080"]})
    st = _drive_attack(e, "T1080", block_with="T1079")
    assert st["attacked"]
    assert "T1079" in _defns(e, "graveyard", 0)   # バトル敗北
    assert "T1080" in _defns(e, "hand", 1)        # バトルの後に手札へ
    assert "T1080" not in _defns(e, "bz", 1)
    assert "T1080" not in _defns(e, "graveyard", 1)


def test_blocked_attacker_destroyed_in_battle_stays_in_graveyard(rules):
    """パワー500の攻撃をブロックすると攻撃側はバトルで
    破壊され、戻しは no-op（墓地に留まる）。パナオン型は残る。"""
    e = _build(rules, {"bz": ["T1079"]}, {"bz": ["T1081"]})
    st = _drive_attack(e, "T1081", block_with="T1079")
    assert st["attacked"]
    assert "T1081" in _defns(e, "graveyard", 1)
    assert "T1081" not in _defns(e, "hand", 1)
    assert "T1079" in _defns(e, "bz", 0)


def test_unblocked_attacker_not_bounced(rules):
    """ブロックしなければ誘発せず、攻撃クリーチャーは
    バトルゾーンに残る。"""
    e = _build(rules, {"bz": ["T1079"]}, {"bz": ["T1080"]})
    st = _drive_attack(e, "T1080", block_with=None)
    assert st["attacked"]
    assert "T1080" in _defns(e, "bz", 1)
    assert "T1080" not in _defns(e, "hand", 1)
    assert "T1079" in _defns(e, "bz", 0)


def test_other_blocker_blocking_does_not_trigger(rules):
    """別のブロッカーがブロックした場合はパナオン型の
    誘発は起きず、攻撃クリーチャーはバトルゾーンに残る。"""
    e = _build(rules, {"bz": ["T1079", "T1082"]}, {"bz": ["T1080"]})
    st = _drive_attack(e, "T1080", block_with="T1082")
    assert st["attacked"]
    assert "T1082" in _defns(e, "graveyard", 0)   # バトル敗北
    assert "T1080" in _defns(e, "bz", 1)          # 戻されない
    assert "T1080" not in _defns(e, "hand", 1)
    assert "T1079" in _defns(e, "bz", 0)
