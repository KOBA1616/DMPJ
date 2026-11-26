"""語彙パイロット第401弾: block_break（ドリフト）。

センサス（rejects 1,932件を取り直し）: pure 1,784件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜400弾）は再提案しない。
graveyard_replacement の残り1件（dm25ex2-cho021）、
battle_opponent_reference の残り1件（dmr01-049）、
untap_restriction の残り2件（dm26rp1-td004 /
dmx15-011）は先行弾の評価を覆す根拠が無く再提案
しない。destroyed_this_turn_condition と
count_cards_drawn_this_turn は次点のまま残す。
enters_tapped_rule（dmex11-005、静的効果3件）は
後続候補のまま。本弾で個別に評価して見送った候補:
enters_tapped_grant（dm26ex3-010。第2条項のタップ
入り付与は第339弾の形で書けるが、第3条項「相手の
効果で手札から捨てられる時、かわりに出してもよい」
は発生源の相手帰属を条件にする置換で別機構のため
カード全体は登録できない）、indestructible_while_
blocking（dmrp22-029。partial のコスト軽減 static が
壊れており〔race_has に文の断片〕、本 gap 以外の
修復が要る）、disable_s_trigger_rest_of_turn
（dm23ex2-chog008。シンパシーの構築＋攻撃誘発での
全体 S・トリガー封じが要り本弾より重い）。
範囲内・最小の **block_break（pure 1件、multi にも
現れない）** を選定した。

対象は dm33-001 超神龍レイ・ソレイユ（光の進化
クリーチャー / コスト4 / パワー6000 / 種族
アポロニア・ドラゴン）。partial は骨格＋keywords
[blocker] が構築済みで、未解決は unsupported の
block_break 1件だけ。partial の text は公式全文と
一致するため text の補完は無い。alias は無い
（identity 実測で canon_id は対象自身、
aliases_for = []）。条項はすべて確立済みの部品で
表せる（追加語彙なし）:

- 「進化-自分の『ブロッカー』を持つクリーチャー
  １体の上に置く」は types [creature, evolution] ＋
  evolve_from {types: [creature], keyword: blocker}。
  第372弾・登録先例 dm32-011 と同文・同形（partial に
  欠けた要素の補完は types への evolution 追加と
  evolve_from の追加のみ）。
- 「自分のクリーチャーがブロックした時、その
  クリーチャーは相手のシールドを１枚ブレイクする」
  は、自分のクリーチャーすべてに誘発能力を与える
  静的効果で表す: static {affects: {zone: bz,
  owner: you, filter: {types: [creature]}}, mod:
  {gain: [trigger {when: {event: block, subject:
  self}, effect: [break {player: opp, count: 1}]}]}}。
  gain で誘発を与える形は登録先例 dmd26-015
  （静的効果の gain）＋第326弾形B（modify で gain
  した誘発が break を解決）の合成。発生源自身を
  監視する watcher 形（trigger {when: {event:
  block, subject: {owner: you, ...}}} を発生源に
  持つ形）では、break の帰属（combat._breaker は
  env の self＝発生源を見る）が発生源に寄って
  しまい、文面の「そのクリーチャーは」（＝ブロック
  したクリーチャー自身）とずれるため gain 形を採る。
  ブレイクはブロック宣言時（バトルの前）に解決
  する（第320・326弾で固定）。gain / evolve_from の
  keyword は defs と schema.py の両側に定義済みを
  確認（第408ラウンドの教訓）。登録ブロッカーの
  確認（第375弾の教訓）: rule_convert.split
  （対象行）は (['blocker'], 条項テキスト, []) を
  返し、part[2] の定型所有は空＝ブロッカー無し
  （本弾で実測）。

確立形: abilities = [上記 static] の1件、
types = [creature, evolution]、
evolve_from = {types: [creature], keyword: blocker}、
keywords = [blocker]。

proto T1168（dm33-001 型）。判別役は既存 proto を
流用: T1117（ブロッカー進化元役＋光マナ役）/
T004（ブロッカー役）/ T001（攻撃役）/ T1118
（パワー7000の攻撃役）/ T1107（ブロッカーを
持たない進化元対照）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED
が復活するので scenario.build を直接包む
（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

GAINED_TRIGGER = {"kind": "trigger",
                  "when": {"event": "block", "subject": "self"},
                  "effect": [{"op": "break", "player": "opp",
                              "count": 1}]}
STATIC = {"kind": "static",
          "affects": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["creature"]}},
          "mod": {"gain": [GAINED_TRIGGER]}}
FORM = [STATIC]
EVOLVE_FROM = {"types": ["creature"], "keyword": "blocker"}
FULL_TEXT = ("ブロッカー\n"
             "進化-自分の「ブロッカー」を持つクリーチャー"
             "１体の上に置く。\n"
             "自分のクリーチャーがブロックした時、その"
             "クリーチャーは相手のシールドを１枚"
             "ブレイクする。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1168")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature", "evolution"]
    assert c["evolve_from"] == EVOLVE_FROM
    assert c["civs"] == ["light"] and c["cost"] == 4
    assert c["power"] == 6000 and c["mana"] == 1
    assert c["races"] == ["アポロニア・ドラゴン"]
    assert c["keywords"] == ["blocker"]
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.abilities == rules.cards["T1168"].abilities
    assert d.evolve_from == EVOLVE_FROM
    for tid in ("T1117", "T004", "T001", "T1118", "T1107"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX401", "name": "x",
                    "types": ["creature", "evolution"],
                    "civs": ["light"], "cost": 4, "power": 6000,
                    "races": ["アポロニア・ドラゴン"], "mana": 1,
                    "keywords": ["blocker"],
                    "evolve_from": copy.deepcopy(EVOLVE_FROM),
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    p = parse_card(proto_card("T1168"), TABLES)
    assert d.abilities == p.abilities
    assert d.evolve_from == EVOLVE_FROM


def _bad(**over):
    base = {"id": "TX401", "name": "x",
            "types": ["creature", "evolution"],
            "civs": ["light"], "cost": 4, "power": 6000,
            "races": ["アポロニア・ドラゴン"], "mana": 1,
            "keywords": ["blocker"],
            "evolve_from": copy.deepcopy(EVOLVE_FROM),
            "abilities": copy.deepcopy(FORM)}
    base.update(over)
    return base


def test_invalid_forms():
    # gain の中身は能力でなければならない（未知の kind）
    bad = copy.deepcopy(FORM)
    bad[0]["mod"]["gain"] = [{"kind": "bogus_kind"}]
    with pytest.raises(DefError):
        parse_card(_bad(abilities=bad), TABLES)
    # affects の未知フィルタキー
    bad = copy.deepcopy(FORM)
    bad[0]["affects"]["filter"] = {"types": ["creature"],
                                   "bogus_key": 1}
    with pytest.raises(DefError):
        parse_card(_bad(abilities=bad), TABLES)
    # evolve_from の未知キーワード
    with pytest.raises(DefError):
        parse_card(_bad(evolve_from={"types": ["creature"],
                                     "keyword": "bogus_keyword"}),
                   TABLES)
    # break op の未知キー
    bad = copy.deepcopy(FORM)
    bad[0]["mod"]["gain"][0]["effect"] = [
        {"op": "break", "player": "opp", "count": 1, "bogus": 1}]
    with pytest.raises(DefError):
        parse_card(_bad(abilities=bad), TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive(e, attacker=None, attacker_player=1, blocker=None,
           play=None, pick=None, stop=None, limit=900):
    """汎用ドライバ（第320弾と同型）。attacker_player の
    attacker（defn）でプレイヤーを攻撃させ、blocker
    （defn）のブロック肢が現れたらブロックする。
    play は p0 の main で使う play キー、pick は進化元の
    選択で優先するキー断片。"""
    state = {"attacked": False, "played": False}
    plays = [play] if play else []
    for _ in range(limit):
        if stop is not None and stop():
            return state
        d = e.advance()
        if d is None:
            return state
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d.get("min", 0))))
        elif kind == "main" and d.get("player") == 0 and plays:
            hit = next((k for k in plays if k in keys), None)
            if hit is not None:
                plays.remove(hit)
                state["played"] = True
                e.answer([keys.index(hit)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind in ("attack", "declare_attack"):
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and d["player"] == attacker_player \
                    and not state["attacked"]:
                state["attacked"] = True
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind in ("block", "declare_block"):
            hit = [i for i, k in enumerate(keys)
                   if blocker and k.startswith(f"bz:{blocker}:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "choose_shields":
            e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("limit reached")


def _triggers(e, p, defn):
    cid = next(c for c in e.bz_tops(p) if e.cdef(c).id == defn)
    return [ab for _, ab in e.abilities(cid, "trigger")]


def test_granted_trigger_only_on_own_creatures(rules):
    """特性判別: T1168 がいる間、自分のクリーチャーは
    全員（発生源自身を含む）が「ブロックした時」の
    誘発を持ち、相手のクリーチャーは持たない。"""
    e = _build(rules, {"bz": ["T1168", "T004"]}, {"bz": ["T001"]})
    assert _triggers(e, 0, "T004") == [GAINED_TRIGGER]
    assert _triggers(e, 0, "T1168") == [GAINED_TRIGGER]
    assert _triggers(e, 1, "T001") == []


def test_block_by_other_creature_breaks_one_shield(rules):
    """実挙動: 自分の他のクリーチャー（T004）が
    ブロックすると、そのクリーチャーが相手の
    シールドを1枚ブレイクする。バトル自体も通常
    どおり行われる（T004 3000 が T001 2000 を倒す）。"""
    e = _build(rules, {"bz": ["T1168", "T004"]},
               {"bz": ["T001"], "shield": ["T007"] * 5})
    st = _drive(e, attacker="T001", attacker_player=1,
                blocker="T004",
                stop=lambda: "T001" in _defns(e, "graveyard", 1))
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 4        # 1枚ブレイク
    assert _defns(e, "hand", 1).count("T007") == 1
    assert "T004" in _defns(e, "bz", 0)          # バトルに勝つ
    assert "T1168" in _defns(e, "bz", 0)


def test_break_before_battle_even_if_blocker_dies(rules):
    """実挙動（タイミング判別）: ブロッカー（T004、
    3000）がパワー7000（T1118）にブロックしてバトルで
    落ちても、ブレイクはブロック宣言時に先に起きる。"""
    e = _build(rules, {"bz": ["T1168", "T004"]},
               {"bz": ["T1118"], "shield": ["T007"] * 5})
    st = _drive(e, attacker="T1118", attacker_player=1,
                blocker="T004",
                stop=lambda: "T004" in _defns(e, "graveyard", 0))
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 4        # 先にブレイク
    assert _defns(e, "hand", 1).count("T007") == 1
    assert "T1118" in _defns(e, "bz", 1)         # 攻撃側は残る


def test_source_itself_blocks_and_breaks(rules):
    """実挙動: 発生源自身（T1168）がブロックしても
    誘発する（「自分のクリーチャー」には自身も含む）。"""
    e = _build(rules, {"bz": ["T1168"]},
               {"bz": ["T001"], "shield": ["T007"] * 5})
    st = _drive(e, attacker="T001", attacker_player=1,
                blocker="T1168",
                stop=lambda: "T001" in _defns(e, "graveyard", 1))
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 4
    assert _defns(e, "hand", 1).count("T007") == 1
    assert "T1168" in _defns(e, "bz", 0)


def test_opponent_block_breaks_nothing(rules):
    """判別: 相手のクリーチャーがブロックしても、
    どちらのシールドも割れない（付与は自分の
    クリーチャーだけ）。自分の T001 はバトルで落ちる。"""
    e = _build(rules, {"bz": ["T1168", "T001"]}, {"bz": ["T004"]})
    st = _drive(e, attacker="T001", attacker_player=0,
                blocker="T004",
                stop=lambda: "T001" in _defns(e, "graveyard", 0))
    assert st["attacked"]
    assert len(e.zlist("shield", 0)) == 5
    assert len(e.zlist("shield", 1)) == 5
    assert "T004" in _defns(e, "bz", 1)


def test_no_source_no_break(rules):
    """対照: 発生源（T1168）がいなければ、ブロック
    してもブレイクは起きない。"""
    e = _build(rules, {"bz": ["T004"]},
               {"bz": ["T001"], "shield": ["T007"] * 5})
    st = _drive(e, attacker="T001", attacker_player=1,
                blocker="T004",
                stop=lambda: "T001" in _defns(e, "graveyard", 1))
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 5
    assert _defns(e, "hand", 1).count("T007") == 0


def test_evolution_onto_blocker_base(rules):
    """実挙動: T1168 はブロッカーを持つクリーチャー
    （T1117）の上に進化して出る。"""
    e = _build(rules,
               {"bz": ["T1117"], "hand": ["T1168"],
                "mana": ["T1117"] * 5},
               {})
    _drive(e, play="play:T1168", pick="T1117",
           stop=lambda: "T1168" in _defns(e, "bz", 0))
    assert "T1168" in _defns(e, "bz", 0)
    cid = next(c for c in e.bz_tops(0) if e.cdef(c).id == "T1168")
    assert e.chars(cid)["power"] == 6000


def test_no_evolution_onto_non_blocker_base(rules):
    """判別: ブロッカーを持たないクリーチャー
    （T1107）の上には進化できない。main の選択肢に
    play:T1168 が現れず、手札に留まる。"""
    e = _build(rules,
               {"bz": ["T1107"], "hand": ["T1168"],
                "mana": ["T1117"] * 5},
               {})
    offered = {"play": False}

    def _stop():
        return e.s.turn >= 5

    # on_main 相当: main 決定のたびに選択肢を覗くため
    # _drive を使わず簡易ループで進める
    for _ in range(300):
        if _stop():
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == 0:
            if "play:T1168" in keys:
                offered["play"] = True
            if "pass" in keys:
                e.answer([keys.index("pass")])
                continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d.get("min", 0))))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert not offered["play"]
    assert "T1168" in _defns(e, "hand", 0)
    assert "T1168" not in _defns(e, "bz", 0)
