"""語彙パイロット第361弾: deck_milled_trigger（ドリフト）。

センサス（rejects 1,972件を取り直し）: pure 1,824件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜360弾）は再提案しない。本弾で個別に
評価して見送った候補: cross_event_trigger（pure 1、
dm16-033。クロスはタスクであって照合可能なイベント
レコードが無く、イベント化はエンジン変更で最小でない）、
mana_enters_untapped（pure 1、dm25-028。多色マナの
タップ置きを置換する語彙が無く新設が要る）、
first_time_tap（pure 2。「はじめてタップした時」の
first_time 共有キーが無い。第360弾の
first_time_cast_or_summon 却下と同根）、
mirror_opponent_draw / draw_mirror（各 pure 1。ドロー
イベントの照合＋枚数参照が要る）、spell_return
（pure 1。唱えた後の行き先置換が要る）、
fixed_breaks_plus_one（pure 1、dmrp07-052。round66 の
旧形式行でテキスト・partial が無く評価不能）。
範囲内・未評価で最小の deck_milled_trigger
（pure 1件、multi にも現れない）を選定した:
dm36-023 奈落の魔黒ジャック・ライガー
「進化-自分の(E・ソウル)クリーチャー１体の上に置く。
このクリーチャーが自分の山札から墓地に置かれた時、
このクリーチャーを墓地から手札に加えてもよい。
W・ブレイカー」。partial は骨格（keywords
[double_breaker] のみ）で、未解決は unsupported の
deck_milled_trigger 1件だけ（partial の注記:
「山札から墓地に置かれることを照合する語彙が無い」）。

結論はドリフト（追加語彙なし）:
- 「自分の山札から墓地に置かれた時」は move 誘発
  {event: move, from: deck, to: graveyard,
  subject: self} ＋ zone: graveyard。登録先例
  dm22ex1-110（同形で効果は「出す」）と
  闇コスト4の登録カード（同形＋if＋may play_free）が
  あり、照合語彙は既に存在する（partial の注記は
  その後の実装で解消済みだった）。
- 「墓地から手札に加えてもよい」は
  may [move {ref: self, count: 1} to: hand,
  reason: return]。
- 進化元「(E・ソウル)」は evolve_from
  {race_has: E・ソウル}（ソウルは races に載る。
  dm36-025 の登録形が races に E・ソウルを含む）。

proto T1086（dm36-023型）/ T1087（ミル役）/
T1088（E・ソウル進化元役）。

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

TRIG = {"kind": "trigger", "zone": "graveyard",
        "when": {"event": "move", "from": "deck", "to": "graveyard",
                 "subject": "self"},
        "effect": [{"op": "may",
                    "body": [{"op": "move",
                              "select": {"ref": "self", "count": 1},
                              "to": "hand", "reason": "return"}]}]}
FORM = [TRIG]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1086")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature", "evolution"]
    assert c["evolve_from"] == {"race_has": "E・ソウル"}
    assert c["keywords"] == ["double_breaker"]
    d = parse_card(copy.deepcopy(c), TABLES)
    assert TRIG in d.abilities
    for tid in ("T1087", "T1088"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX361", "name": "x",
                    "types": ["creature", "evolution"],
                    "civs": ["darkness"], "cost": 4, "power": 6000,
                    "races": ["ゴースト"],
                    "evolve_from": {"race_has": "E・ソウル"},
                    "keywords": ["double_breaker"],
                    "abilities": [copy.deepcopy(TRIG)]}, TABLES)
    assert TRIG in d.abilities


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive(e, plays=(), yes=True, pick=None, stop=None,
           on_main=None, limit=400):
    """汎用ドライバ。plays は p0 の main で使う play キーの
    順序付きリスト。yes_no は yes で答え、見た回数を返す。
    pick は choose 系で優先するキー断片。stop が真になったら
    （またはゲームが終わったら）止める。on_main は p0 の
    main 決定のキー一覧を受け取るコールバック。"""
    plays = list(plays)
    seen = {"yes_no": 0}
    for _ in range(limit):
        if stop is not None and stop():
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "yes_no":
            seen["yes_no"] += 1
            want = "yes" if yes else "no"
            e.answer([keys.index(want)] if want in keys
                     else list(range(d.get("min", 0))))
        elif kind == "main" and d.get("player") == 0:
            if on_main is not None:
                on_main(keys)
            hit = next((k for k in plays if k in keys), None)
            if hit is not None:
                plays.remove(hit)
                e.answer([keys.index(hit)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return seen


def _mill_setup(rules):
    # 山札リストの末尾が一番上（deck[0]）なので T1086 が上。
    return _build(rules,
                  {"hand": ["T1087"], "mana": ["T1087", "T1087"],
                   "deck": ["T002", "T1086"]},
                  {})


def test_milled_may_add_to_hand(rules):
    """山札から墓地に置かれた時、may で手札に加えられる。"""
    e = _mill_setup(rules)
    seen = _drive(e, plays=["play:T1087"], yes=True,
                  stop=lambda: "T1086" in _defns(e, "hand", 0))
    assert seen["yes_no"] >= 1
    assert "T1086" in _defns(e, "hand", 0)
    assert "T1086" not in _defns(e, "graveyard", 0)


def test_milled_may_decline_stays_in_graveyard(rules):
    """may を断れば墓地に留まる。"""
    e = _mill_setup(rules)
    seen = _drive(e, plays=["play:T1087"], yes=False,
                  stop=lambda: e.s.turn >= 4
                  and "T1086" in _defns(e, "graveyard", 0))
    assert seen["yes_no"] >= 1
    assert "T1086" in _defns(e, "graveyard", 0)
    assert "T1086" not in _defns(e, "hand", 0)


def test_discarded_from_hand_does_not_trigger(rules):
    """手札から墓地に置かれた時は誘発しない
    （from: deck の照合が効いていることの判別）。"""
    e = _build(rules,
               {"hand": ["T1086", "T118"],
                "mana": ["T1088", "T1088"]},
               {})
    seen = _drive(e, plays=["play:T118"], pick="zone:T1086",
                  stop=lambda: "T1086" in _defns(e, "graveyard", 0))
    # 墓地に落ちた後もしばらく進めて、誘発が積まれていない
    # ことを確認する
    seen2 = _drive(e, limit=30)
    assert "T1086" in _defns(e, "graveyard", 0)
    assert seen["yes_no"] == 0 and seen2["yes_no"] == 0


def test_evolution_onto_e_soul_base(rules):
    """E・ソウルを持つクリーチャーの上に進化できる。"""
    e = _build(rules,
               {"bz": ["T1088"], "hand": ["T1086"],
                "mana": ["T1088"] * 4},
               {})
    _drive(e, plays=["play:T1086"], pick="T1088",
           stop=lambda: "T1086" in _defns(e, "bz", 0), limit=200)
    assert "T1086" in _defns(e, "bz", 0)
    assert "T1088" in _defns(e, "bz", 0)   # 進化元は下に残る


def test_no_evolution_onto_non_e_soul(rules):
    """E・ソウルを持たないクリーチャーには進化できない。"""
    e = _build(rules,
               {"bz": ["T1087"], "hand": ["T1086"],
                "mana": ["T1088"] * 4},
               {})
    # 出せるカードが無いと main 決定自体が提示されないため、
    # 数ターン進めても手札に留まり場に出ないことで固定する
    # （正例 test_evolution_onto_e_soul_base と対）。
    _drive(e, stop=lambda: e.s.turn >= 5, limit=200)
    assert "T1086" in _defns(e, "hand", 0)
    assert "T1086" not in _defns(e, "bz", 0)
