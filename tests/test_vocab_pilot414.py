"""語彙パイロット第414弾: chosen_creature_can_be_attacked_while_untapped
（ドリフト）。

センサス（rejects 1,918件を取り直し）: pure 1,770件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜413弾）は原則として再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021、
battle_opponent_reference の残り1件 dmr01-049、
untap_restriction の残り2件（dm26rp1-td004 /
dmx15-011、形が異なると判定済み）、cast_limit_
once_per_turn の multi 2件（dm26ex2-pr006 /
dm26ex4-cho031、他の gaps を併せ持つ）、
summoning_attack_rule の残り1件 dmex07-s01
（partial が素で条項未構築）、entered_turn_attack の
残り1件 dmbd11-d05（J・O・E 等が未構築）、madness の
残り1件 dmx26-028（CIP が look/reorder 系の未確立
機構）は先行弾の評価を覆す根拠が無く再提案しない。
destroyed_this_turn_condition と count_cards_drawn_
this_turn は次点のまま残す。distinct_civ_count
（3条項の複合）は後続候補のまま残す。first_time_tap
（pure 2、第410弾で記録）は新規語彙候補として
残置のまま。本弾で個別に評価して見送った候補:
blocker_dies_after_battle_even_if_wins（dm01-028。
ターン範囲の監視・付与形が未確立）、after_battle_
trigger（pure 2、素行。勝者参照が未確立／文面の
目的語欠落）、does_not_untap（pure 2、いずれも複合）、
power_set（pure 2、3条項複合）、after_attack_destroy
（pure 2、複合）、enters_tapped_optional（pure 2、
素行で任意出場機構が未確立）、draw_up_to（pure 2、
G・リンク／ハイパー化を含む複合）、battle_win_power_
difference（pure 2。敗者とのパワー差参照が未確立）、
mana_enters_untapped（置換機構が未確立）、s_trigger_
lock（複合）、slayer_while_attacking_low_cost
（条件つき付与が未確立）、grant_all_civilizations
（ツインパクト。クリーチャー面はドリフトだが呪文面の
次回召喚一回限りの軽減に確立形が無い）、
attack_target_condition（第2条項が攻撃対象の文明
条件を要する複合）。

範囲内・最小の **chosen_creature_can_be_attacked_
while_untapped（pure 1件、multi にも現れない）** を
選定した。対象は dm01-034 カオス・ストライク
（火の呪文 / コスト2）。文面は「バトルゾーンにある
相手のクリーチャーを１体選ぶ。このターン、選んだ
クリーチャーがタップされていなくても攻撃できる。」
partial の注記は「攻撃側すべてにタップされていない
クリーチャーへの攻撃許可を与えると、選んでいない
クリーチャーまで攻撃できてしまうため代用せず
unsupported に残した」としていたが、それは第275弾
（attack_specific_target）で追加された allow 項目の
`only: {var: 名前}` が解決済みの問題であり、登録済み
dmr09-102 戦場のロックンロール（同じく火・コスト2の
呪文）の登録形を本弾で直接照合して確認した:
spell [choose {select: {zone: bz, owner: opp,
filter: {types: [creature], tapped: false}, count: 1},
as: tgt}, modify {select: {zone: bz, owner: you,
filter: {types: [creature]}, count: all},
mod: {allow: [{action: attack_creature,
other: {tapped: false}, only: {var: tgt}}]},
duration: end_of_turn}]。本件との差は選択フィルタに
tapped: false が無いことだけ（本件はタップ状態を
問わず選べる）。partial の注記の解釈懸念（「選んだ
クリーチャーが攻撃できる」とも読める）は文法上
成り立たない（第2文の主節の述語「攻撃できる」の
主体は呪文のコントローラーで、選んだクリーチャーは
攻撃の対象。「タップされていなくても」はその
クリーチャーの状態を述べる従属節）。登録先例
dmr14-050 / dmrp06-080 の CIP 形とも同型。完全な
ドリフト（新規語彙・エンジン・defs・スキーマ
変更なし）。

partial は骨格完備（呪文 / 火 / コスト2 / mana 1）で、
未解決は unsupported 1件だけ。partial の text は
行の公式テキスト全文と内容が一致し文間の改行だけが
欠けるため、提出形の text は行の公式テキストを
そのまま使い**補完なし**（内容の追加・変更なし）。
alias は無し（公式データで カオス・ストライク の
収録は dm01-034 のみ。identity 実測で canon_id は
対象自身、aliases_for = []）。第414弾時点で
real.yaml / real_akashic.yaml / real_vocab.yaml /
real_zone.yaml / proto.yaml / converted.yaml の
いずれにも対象 id は登録なし。単面カードで未検証の
面は無い。登録ブロッカーの確認（第375弾の教訓）:
rule_convert.split（対象行）は None を返し、定型
所有は無い＝ツール側ブロッカーなし。

proto T1182（dm01-034 型）。判別役は既存 proto を
流用: T1090（印刷スピードアタッカー役＝攻撃側・
火マナ役）/ T008（パワー1000バニラ役＝選ぶ対象）/
T1091（パワー2000バニラ役＝選ばない対照）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の
作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

CHOOSE = {"op": "choose",
          "select": {"zone": "bz", "owner": "opp",
                     "filter": {"types": ["creature"]}, "count": 1},
          "as": "tgt"}
MODIFY = {"op": "modify",
          "select": {"zone": "bz", "owner": "you",
                     "filter": {"types": ["creature"]}, "count": "all"},
          "mod": {"allow": [{"action": "attack_creature",
                             "other": {"tapped": False},
                             "only": {"var": "tgt"}}]},
          "duration": "end_of_turn"}
FORM = [CHOOSE, MODIFY]
FULL_TEXT = ("バトルゾーンにある相手のクリーチャーを１体選ぶ。\n"
             "このターン、選んだクリーチャーがタップされていなくても攻撃できる。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1182")
    assert c["spell"] == FORM
    assert c["name"] == "カオス・ストライク"
    assert c["types"] == ["spell"] and c["civs"] == ["fire"]
    assert c["cost"] == 2 and c["mana"] == 1
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    assert [op["op"] for op in d.spell] == ["choose", "modify"]
    assert d.spell[0]["select"] == {"zone": "bz", "owner": "opp",
                                    "filter": {"types": ["creature"]},
                                    "count": 1}
    assert d.spell[0]["as"] == "tgt"
    # 選択フィルタに tapped: false は無い（第275弾形との差）
    assert "tapped" not in d.spell[0]["select"]["filter"]
    assert d.spell[1]["mod"] == {"allow": [
        {"action": "attack_creature", "other": {"tapped": False},
         "only": {"var": "tgt"}}]}
    assert d.spell[1]["duration"] == "end_of_turn"
    for tid in ("T1090", "T008", "T1091"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX414", "name": "カオス・ストライク",
                    "types": ["spell"], "civs": ["fire"],
                    "cost": 2, "mana": 1, "text": FULL_TEXT,
                    "spell": copy.deepcopy(FORM)}, TABLES)
    assert [op["op"] for op in d.spell] == ["choose", "modify"]
    assert d.spell[1]["mod"]["allow"][0]["only"] == {"var": "tgt"}


def _bad(spell):
    with pytest.raises(DefError):
        parse_card({"id": "TX414B", "name": "x", "types": ["spell"],
                    "civs": ["fire"], "cost": 2,
                    "spell": spell}, TABLES)


def test_bad_unknown_op():
    s = copy.deepcopy(FORM)
    s[0]["op"] = "bogus"
    _bad(s)


def test_bad_unknown_select_key():
    s = copy.deepcopy(FORM)
    s[0]["select"]["bogus"] = 1
    _bad(s)


def test_bad_unknown_allow_action():
    s = copy.deepcopy(FORM)
    s[1]["mod"]["allow"][0]["action"] = "bogus_action"
    _bad(s)


def test_bad_unknown_mod_key():
    s = copy.deepcopy(FORM)
    s[1]["mod"]["bogus_mod"] = []
    _bad(s)


def test_bad_only_shape():
    s = copy.deepcopy(FORM)
    s[1]["mod"]["allow"][0]["only"] = {"bogus": "tgt"}
    _bad(s)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _setup(rules):
    return _build(rules,
                  {"bz": ["T1090"], "hand": ["T1182"],
                   "mana": ["T1090", "T1090"]},
                  {"bz": ["T008", "T1091"]})


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _drive(e, choose_defn=None, attack_key=None, stop=None, limit=1200,
           log=None):
    """汎用ドライバ: player 0 が T1182 を唱えて
    choose_defn を選び、attack_key があれば一度だけ
    攻撃する。stop(e) が真になったら止める。
    観測した player 0 の攻撃決定を (turn, keys) の
    リストで返す（log を渡せばそこへ追記する）。"""
    st = {"played": False, "chose": False, "attacked": False}
    if log is None:
        log = []
    for _ in range(limit):
        if stop and stop(e):
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "main" and d.get("player") == 0 \
                and not st["played"] and "play:T1182" in keys:
            st["played"] = True
            e.answer([keys.index("play:T1182")])
            continue
        if kind == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if kind == "choose_cards" and choose_defn is not None \
                and not st["chose"]:
            hit = [i for i, o in enumerate(d["options"])
                   if e.cdef(o["cid"]).id == choose_defn]
            if hit:
                st["chose"] = True
                e.answer([hit[0]])
                continue
        if kind == "attack" and d.get("player") == 0:
            log.append((e.s.turn, list(keys)))
            if attack_key is not None and not st["attacked"] \
                    and attack_key in keys:
                st["attacked"] = True
                e.answer([keys.index(attack_key)])
                continue
        if kind == "declare_strigger":
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return st, log


def test_control_untapped_cannot_be_attacked(rules):
    """対照: 唱えなければ、アンタップしている相手
    クリーチャーはどちらも攻撃できない（プレイヤー
    への攻撃だけが選択肢に出る）。"""
    e = _setup(rules)
    keys = [o["key"] for o in e._attack_options(0)]
    assert keys == ["attack:T1090:player"]


def test_cast_choose_untapped_attack_only_chosen(rules):
    """本弾の判別: 唱えてアンタップの T008 を選ぶと、
    このターン T008 だけが（タップされていなくても）
    攻撃でき、選ばなかった T1091 は攻撃できない。
    実際に攻撃すると T008（パワー1000）はバトルで
    破壊され、T1090（パワー2000）は残る。"""
    e = _setup(rules)
    st, log = _drive(
        e, choose_defn="T008", attack_key="attack:T1090:T008",
        stop=lambda e: _in_zone(e, 1, "graveyard", "T008"))
    assert st["played"] and st["chose"] and st["attacked"]
    first = log[0][1]
    assert "attack:T1090:T008" in first       # 選んだ対象は攻撃可
    assert "attack:T1090:T1091" not in first  # 選んでいない対象は不可
    assert "attack:T1090:player" in first
    assert _in_zone(e, 1, "graveyard", "T008")
    assert _in_zone(e, 0, "bz", "T1090")          # 勝者は残る
    assert _in_zone(e, 1, "bz", "T1091")          # 対照は無事
    assert _in_zone(e, 0, "graveyard", "T1182")   # 呪文は墓地へ


def test_cast_choose_tapped_target(rules):
    """選択フィルタに tapped: false が無いことの判別:
    タップしている T008 も選べる（第275弾形なら
    選べない）。タップしている対象はもともと攻撃
    できるが、選ばなかった T1091 は攻撃できない。"""
    e = _setup(rules)
    cid = next(c for c in e.zlist("bz", 1)
               if e.s.cards[c].defn == "T008")
    e.s.cards[cid].tapped = True
    st, log = _drive(
        e, choose_defn="T008", attack_key="attack:T1090:T008",
        stop=lambda e: _in_zone(e, 1, "graveyard", "T008"))
    assert st["played"] and st["chose"] and st["attacked"]
    first = log[0][1]
    assert "attack:T1090:T008" in first
    assert "attack:T1090:T1091" not in first
    assert _in_zone(e, 1, "graveyard", "T008")


def test_effect_expires_next_turn(rules):
    """duration: end_of_turn の判別: 唱えて T008 を
    選んでも攻撃しなければ、自分の次のターンには
    T008（アンタップのまま）を攻撃できない。"""
    e = _setup(rules)
    log = []
    st, log = _drive(e, choose_defn="T008", attack_key=None, log=log,
                     stop=lambda e: len({t for t, _ in log}) >= 2)
    assert st["played"] and st["chose"]
    turns = {}
    for t, keys in log:
        turns.setdefault(t, keys)
    ts = sorted(turns)
    assert len(ts) >= 2
    assert "attack:T1090:T008" in turns[ts[0]]       # 当ターンは攻撃可
    assert "attack:T1090:T008" not in turns[ts[1]]   # 次ターンは不可
    assert "attack:T1090:player" in turns[ts[1]]
    assert _in_zone(e, 1, "bz", "T008")              # 攻撃されず残る
