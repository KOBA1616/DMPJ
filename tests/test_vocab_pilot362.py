"""語彙パイロット第362弾: entry_turn_attack_restriction（ドリフト）。

センサス（rejects 1,971件を取り直し）: pure 1,823件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜361弾）は再提案しない。本弾で個別に
評価して見送った候補: king_cell（pure 2。キング・セル
というカードタイプと2種セルの合体召喚そのものが無い
大型機構）、ignore_breaker（pure 1。「ブレイカー能力を
無視する」はキーワード由来の breaks 修整を種類単位で
落とす照合が無く、ignore / ignore_ids の既存形では
届かない）、graveyard_lock（pure 2。no_leave は
バトルゾーンを離れる移動だけを止める形で、墓地の
カードが墓地を離れる移動には及ばない＝エンジン拡張が
要る）、being_attacked_power（pure 1。power_when の
when は attacking / blocking / not_attacking のみで、
「攻撃されている間」（攻撃対象でブロックしていない
状態）だけを指す値が無い。not_attacking では攻撃の
無い間も付いてしまい一致しない）、
state_condition_destruction（pure 1。状態条件での
自己破壊は状況起因の継続チェックが前提で、誘発の
既存形では書けない）、cannot_be_tapped_by_opponent
（pure 1。partial の注記どおり be_tapped の許可が
無く、deny では広すぎる。第361弾までの評価と同根）。
範囲内・未評価で最小の entry_turn_attack_restriction
（pure 1件、multi にも現れない）を選定した:
dm23bd6-003 アカシック・B「相手のクリーチャーは
出たターン、自分や自分のクリーチャーを攻撃できない」。
partial は骨格（能力なし）で、未解決は unsupported の
本 gap 1件だけ。

結論はドリフト（追加語彙なし）:
- 「出たターン」は affects の対象フィルタの
  entered_this_turn: true（第134弾のフィルタ。
  entered_turn == 現在ターンで照合するため、出た
  ターンだけに効き、次のターンからは外れる）。
- 「自分や自分のクリーチャーを攻撃できない」は
  mod {deny: [attack_player, attack_creature]}。
- 登録先例 dm23rp4x-014 巨魔天 アオフェシーが同文の
  条項「相手のクリーチャーは、出たターン、攻撃
  できない」を static {affects: {zone: bz, owner: opp,
  filter: {types: [creature], entered_this_turn: true}},
  mod: {deny: [attack_player, attack_creature]}} で
  登録済み（本弾の形はその一致そのもの）。もう1件の
  先例 dm25ex1-005 は「自分を攻撃できない」分として
  deny: [attack_player] のみを使う。

proto T1089（dm23bd6-003 クリーチャー面型）/
T1090（スピードアタッカー役）/ T1091（標的役）。

注意: dm23bd6-003 はツインパクトで、呪文面
「「バブルの泡に溺れるのヨ！」」（S・トリガー、
相手1人につき、その相手のクリーチャーを1体選んで
手札に戻し、カードを1枚引いてもよい）は partial に
含まれておらず、本弾では未検証（ラウンド397で
検証すること）。conftest を import すると
DMSIM_SKIP_CONVERTED が復活するので scenario.build
を直接包む（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

STATIC = {"kind": "static",
          "affects": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"],
                                 "entered_this_turn": True}},
          "mod": {"deny": ["attack_player", "attack_creature"]}}
FORM = [STATIC]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1089")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"]
    assert c["cost"] == 3 and c["power"] == 3000
    d = parse_card(copy.deepcopy(c), TABLES)
    assert STATIC in d.abilities
    for tid in ("T1090", "T1091"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX362", "name": "x",
                    "types": ["creature"], "civs": ["water"],
                    "cost": 3, "power": 3000,
                    "races": ["マジック・コマンド", "マーメイド"],
                    "abilities": [copy.deepcopy(STATIC)]}, TABLES)
    assert STATIC in d.abilities


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _cid(e, defn, p):
    return next(c for c in e.bz_tops(p) if e.cdef(c).id == defn)


def _drive(e, player, play=None, attack=None):
    """player の最初の main のターン（target_turn）だけを
    対象に進めるドライバ。

    play があればそのターンの main で1回だけ使い、使った
    直後（まだ同じターン）の chars の deny を記録する。
    attack があれば target_turn の attack 決定で
    attack:<attack>:player を選ぶ。target_turn の次の
    ターンに入ったら止める。なお攻撃できるクリーチャーが
    1体もいない場合、attack 決定自体が提示されない
    （自動で読み飛ばされる）ことを実測で確認済み。"""
    seen = {"attack_keys": [], "deny": None, "played": False,
            "attacked": False, "target_turn": None}
    for _ in range(600):
        if seen["target_turn"] is not None \
                and e.s.turn > seen["target_turn"] + 1:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        pl = d.get("player")
        if kind in ("charge", "main", "attack") \
                and pl == player and seen["target_turn"] is None:
            seen["target_turn"] = e.s.turn
        if kind == "main" and pl == player and play \
                and not seen["played"]:
            hit = [i for i, k in enumerate(keys)
                   if k == f"play:{play}"]
            if hit:
                seen["played"] = True
                seen["target_turn"] = e.s.turn
                e.answer([hit[0]])
                continue
        if kind == "attack" and pl == player \
                and e.s.turn == seen["target_turn"]:
            seen["attack_keys"].extend(keys)
            hit = [i for i, k in enumerate(keys)
                   if attack and k == f"attack:{attack}:player"]
            if hit and not seen["attacked"]:
                seen["attacked"] = True
                e.answer([hit[0]])
                continue
        if kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return seen


def test_entered_this_turn_opp_speed_attacker_cannot_attack(rules):
    """相手のスピードアタッカーが出たターン、プレイヤーへも
    クリーチャーへも攻撃できない（deny が両方付く）。"""
    e = _build(rules,
               {"bz": ["T1089", "T1091"]},
               {"hand": ["T1090"], "mana": ["T1090", "T1090"]})
    shields = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, play="T1090")
    assert seen["played"]
    assert not [k for k in seen["attack_keys"]
                if k.startswith("attack:T1090:")]
    assert "T1090" in _defns(e, "bz", 1)
    assert not e.s.cards[_cid(e, "T1090", 1)].tapped  # 攻撃していない
    assert len(e.zlist("shield", 0)) == shields        # ブレイクなし


def test_control_without_source_speed_attacker_can_attack_on_entry_turn(rules):
    """対照: 発生源が無ければ、出たターンのスピード
    アタッカーはプレイヤーを攻撃でき、シールドが1枚減る。"""
    e = _build(rules,
               {"bz": ["T1091"]},
               {"hand": ["T1090"], "mana": ["T1090", "T1090"]})
    before = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, play="T1090", attack="T1090")
    assert seen["played"] and seen["attacked"]
    assert len(e.zlist("shield", 0)) == before - 1


def test_speed_attacker_from_previous_turn_can_attack_despite_source(rules):
    """前ターンからいるスピードアタッカーには制限が
    及ばず、発生源がいてもプレイヤーを攻撃できる
    （entered_this_turn の判別）。"""
    e = _build(rules,
               {"bz": ["T1089", "T1091"]},
               {"bz": ["T1090"]})
    before = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, attack="T1090")
    assert seen["attacked"]
    assert len(e.zlist("shield", 0)) == before - 1


def test_own_speed_attacker_entered_this_turn_can_attack(rules):
    """自分のクリーチャーには及ばない: 自分のスピード
    アタッカーは出たターンに相手プレイヤーを攻撃できる。"""
    e = _build(rules,
               {"bz": ["T1089"], "hand": ["T1090"],
                "mana": ["T1090", "T1090"]},
               {})
    before = len(e.zlist("shield", 1))
    seen = _drive(e, player=0, play="T1090", attack="T1090")
    assert seen["played"] and seen["attacked"]
    assert len(e.zlist("shield", 1)) == before - 1


def test_chars_deny_only_for_opponent_entered_this_turn(rules):
    """特性レベルの判別: entered_turn が現在のターンと
    一致する相手クリーチャーだけに deny の両方が付き、
    前ターンからいる相手クリーチャーと、自分の
    クリーチャーには付かない。"""
    e = _build(rules,
               {"bz": ["T1089", "T1090"]},
               {"bz": ["T1090"]})
    opp = _cid(e, "T1090", 1)
    own = _cid(e, "T1090", 0)
    e.s.mut_card(opp).entered_turn = e.s.turn
    e.s.mut_card(own).entered_turn = e.s.turn
    deny_opp = e.chars(opp)["deny"]
    assert "attack_player" in deny_opp
    assert "attack_creature" in deny_opp
    deny_own = e.chars(own)["deny"]
    assert "attack_player" not in deny_own
    assert "attack_creature" not in deny_own
    e.s.mut_card(opp).entered_turn = e.s.turn - 1
    deny_prev = e.chars(opp)["deny"]
    assert "attack_player" not in deny_prev
    assert "attack_creature" not in deny_prev
