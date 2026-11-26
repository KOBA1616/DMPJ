"""語彙パイロット第399弾: summon_turn_attack_restriction（ドリフト）。

センサス（rejects 1,934件を取り直し）: pure 1,786件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜398弾）は再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021 と
battle_opponent_reference の残り1件 dmr01-049 は
先行弾の評価を覆す根拠が無く再提案しない。
destroyed_this_turn_condition と count_cards_drawn_
this_turn は次点のまま残す。本弾で個別に評価した
後続候補2件: enters_tapped_rule（pure 1、dmex11-005。
第1条項のスピードアタッカー付与〈自分のコスト3以下
すべて〉と第2条項のタップ入り付与2系統〈相手の進化 /
相手のスピードアタッカー〉で静的効果3件となり、
付与形の登録先例 dmrp06-030 / dm06-001（第384弾）は
あるが本弾より重いため後続候補のまま残す）、
summon_turn_attack_restriction（pure 1、dmr22-s04。
第398弾と同一の条項で確立形がそのまま使え、残りの
条項はキーワード2件と多色マナのルールのみ＝本弾が
最小）。範囲内・最小の **summon_turn_attack_
restriction（pure 1件、multi にも現れない）** を選定した。

対象は pure 1件すべて: dmr22-s04 聖者の精霊龍
セレナーデ（光・水のクリーチャー / コスト7 /
パワー7500 / 種族 エンジェル・コマンド・ドラゴン /
革命軍）。partial は素で、骨格（types / civs /
cost / power / races / mana）と text の断片
（「出たターン攻撃できない」）だけがあり、keywords・
abilities は何も構築されていない。未解決は
unsupported の summon_turn_attack_restriction 1件。
alias は無い（identity 実測で canon_id(dmr22-s04) =
dmr22-s04、aliases_for = []）。第399弾時点で
real.yaml / real_akashic.yaml / real_vocab.yaml /
real_zone.yaml / proto.yaml / converted.yaml の
いずれにも登録なし。単面カードで未検証の面は無い。

結論はドリフト（追加語彙なし）:
- 条項「「スピードアタッカー」を持つクリーチャーは
  すべて、バトルゾーンに出たターン、攻撃できない」の
  確立形は第398弾と同一の static {affects: {zone: bz,
  owner: any, filter: {types: [creature], keyword:
  speed_attacker, entered_this_turn: true}}, mod:
  {deny: [attack_player, attack_creature]}} の1件
  （文面の「すべて」に所有者の限定は無い）。
- 残りの条項は partial が素のため本弾で構築する:
  ブロッカー＝keyword blocker、W・ブレイカー＝
  keyword double_breaker（いずれも標準キーワード）。
  「マナゾーンに置く時、このカードはタップして置く」
  は多色カードのルール（405.1）で、エンジン core の
  _raw_move が civs 2つ以上のカードをマナに置く時に
  タップさせるため、変換済みカード（dm10-037 /
  dm10-041 / dm10-064 / dmbd05-006 等）では一貫して
  text のみで表す（キーワード・能力は付けない）。
  提出形の text は行の公式テキスト全文を条項ごとに
  改行したもの（**補完あり: text のみ**。partial の
  text は条項の断片のため）。
- entered_this_turn / keyword は FILTER_KEYS の
  既存キーで、defs と schema.py（FILTER_KEYS を引く
  生成）の両側に定義済み（第408ラウンドの教訓）。

既知の制限（第398弾と同一・実測で固定）: 静的効果の
affects 照合は base=True（印刷特性）で行われるため、
**他の効果で付与されたスピードアタッカーは本
フィルタに掛からない**（T314 の自己付与で実測）。
keyword フィルタを使う登録済み静的効果すべてが
共有するエンジン全体の規約であり、解消は専用
ステージ送り（本弾では扱わない）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（本弾で実測）。

proto T1166（dmr22-s04 型）。判別役は既存 proto を
流用: T1090（スピードアタッカー役・火マナ役）/
T1091（標的役）/ T314（スピードアタッカー自己付与役
＝付与分の制限確認用）。

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

STATIC = {"kind": "static",
          "affects": {"zone": "bz", "owner": "any",
                      "filter": {"types": ["creature"],
                                 "keyword": "speed_attacker",
                                 "entered_this_turn": True}},
          "mod": {"deny": ["attack_player", "attack_creature"]}}
FORM = [STATIC]
FULL_TEXT = ("マナゾーンに置く時、このカードはタップして置く。\n"
             "ブロッカー\n"
             "W・ブレイカー\n"
             "「スピードアタッカー」を持つクリーチャーはすべて、"
             "バトルゾーンに出たターン、攻撃できない。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1166")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"] and c["civs"] == ["light", "water"]
    assert c["cost"] == 7 and c["power"] == 7500 and c["mana"] == 1
    assert c["races"] == ["エンジェル・コマンド・ドラゴン", "革命軍"]
    assert c["keywords"] == ["blocker", "double_breaker"]
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    assert STATIC in d.abilities
    for tid in ("T1090", "T1091", "T314"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX399", "name": "聖者の精霊龍 セレナーデ",
                    "types": ["creature"], "civs": ["light", "water"],
                    "cost": 7, "power": 7500, "mana": 1,
                    "races": ["エンジェル・コマンド・ドラゴン", "革命軍"],
                    "keywords": ["blocker", "double_breaker"],
                    "abilities": [copy.deepcopy(STATIC)]}, TABLES)
    assert STATIC in d.abilities


def _bad(ability):
    with pytest.raises(DefError):
        parse_card({"id": "TX399B", "name": "x", "types": ["creature"],
                    "civs": ["light"], "cost": 3, "power": 3000,
                    "abilities": [ability]}, TABLES)


def test_bad_unknown_keyword_in_filter():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "any",
                      "filter": {"types": ["creature"],
                                 "keyword": "no_such_kw",
                                 "entered_this_turn": True}},
          "mod": {"deny": ["attack_player"]}})


def test_bad_unknown_filter_key():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "any",
                      "filter": {"types": ["creature"],
                                 "keyword": "speed_attacker",
                                 "entered_this_turn": True,
                                 "bogus_key": 1}},
          "mod": {"deny": ["attack_player"]}})


def test_bad_unknown_mod_key():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "any",
                      "filter": {"types": ["creature"],
                                 "keyword": "speed_attacker",
                                 "entered_this_turn": True}},
          "mod": {"bogus_mod": 1}})


def test_bad_unknown_deny_action():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "any",
                      "filter": {"types": ["creature"],
                                 "keyword": "speed_attacker",
                                 "entered_this_turn": True}},
          "mod": {"deny": ["fly"]}})


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, defn, p):
    return next(c for c in e.bz_tops(p) if e.cdef(c).id == defn)


def _drive(e, player, play=None, attack=None):
    """player の最初の main のターンだけを対象に進める
    ドライバ（第398弾と同型）。攻撃できるクリーチャーが
    1体もいない場合、attack 決定自体が提示されない。"""
    seen = {"attack_keys": [], "played": False,
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


def test_own_speed_attacker_entered_this_turn_cannot_attack(rules):
    """自分のスピードアタッカーも対象（owner: any の判別。
    第362弾の owner: opp 形との差）: 発生源が自分の
    バトルゾーンにいても、出たターンには攻撃できない。"""
    e = _build(rules,
               {"bz": ["T1166"], "hand": ["T1090"],
                "mana": ["T1090", "T1090"]},
               {"bz": ["T1091"]})
    shields = len(e.zlist("shield", 1))
    seen = _drive(e, player=0, play="T1090", attack="T1090")
    assert seen["played"]
    assert not seen["attacked"]
    assert not [k for k in seen["attack_keys"]
                if k.startswith("attack:T1090:")]
    assert not e.s.cards[_cid(e, "T1090", 0)].tapped  # 攻撃していない
    assert len(e.zlist("shield", 1)) == shields        # ブレイクなし


def test_opp_speed_attacker_entered_this_turn_cannot_attack(rules):
    """相手のスピードアタッカーも、出たターンには
    プレイヤーへもクリーチャーへも攻撃できない。"""
    e = _build(rules,
               {"bz": ["T1166", "T1091"]},
               {"hand": ["T1090"], "mana": ["T1090", "T1090"]})
    shields = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, play="T1090", attack="T1090")
    assert seen["played"]
    assert not seen["attacked"]
    assert not [k for k in seen["attack_keys"]
                if k.startswith("attack:T1090:")]
    assert not e.s.cards[_cid(e, "T1090", 1)].tapped
    assert len(e.zlist("shield", 0)) == shields


def test_speed_attacker_from_previous_turn_can_attack(rules):
    """前ターンからいるスピードアタッカーには制限が
    及ばず、発生源がいても攻撃できる
    （entered_this_turn の判別）。"""
    e = _build(rules,
               {"bz": ["T1166"]},
               {"bz": ["T1090"]})
    before = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, attack="T1090")
    assert seen["attacked"]
    assert len(e.zlist("shield", 0)) == before - 1


def test_control_without_source_can_attack_on_entry_turn(rules):
    """対照: 発生源が無ければ、出たターンのスピード
    アタッカーはプレイヤーを攻撃でき、シールドが
    1枚減る。"""
    e = _build(rules,
               {"hand": ["T1090"], "mana": ["T1090", "T1090"]},
               {"bz": ["T1091"]})
    before = len(e.zlist("shield", 1))
    seen = _drive(e, player=0, play="T1090", attack="T1090")
    assert seen["played"] and seen["attacked"]
    assert len(e.zlist("shield", 1)) == before - 1


def test_chars_deny_discrimination(rules):
    """特性レベルの判別: deny の両方が付くのは
    「スピードアタッカーを持ち、entered_turn が現在の
    ターンと一致する」クリーチャーだけ（所有者は
    問わない）。スピードアタッカーを持たない
    クリーチャーと、前ターンからいるスピード
    アタッカーには付かない。"""
    e = _build(rules,
               {"bz": ["T1166", "T1090", "T1091"]},
               {"bz": ["T1090"]})
    own_sa = _cid(e, "T1090", 0)
    opp_sa = _cid(e, "T1090", 1)
    vanilla = _cid(e, "T1091", 0)
    for c in (own_sa, opp_sa, vanilla):
        e.s.mut_card(c).entered_turn = e.s.turn
    for c in (own_sa, opp_sa):
        deny = e.chars(c)["deny"]
        assert "attack_player" in deny
        assert "attack_creature" in deny
    deny_v = e.chars(vanilla)["deny"]
    assert "attack_player" not in deny_v
    assert "attack_creature" not in deny_v
    e.s.mut_card(own_sa).entered_turn = e.s.turn - 1
    deny_prev = e.chars(own_sa)["deny"]
    assert "attack_player" not in deny_prev
    assert "attack_creature" not in deny_prev


def test_source_keywords_blocker_and_double_breaker(rules):
    """発生源自身の条項: ブロッカーと W・ブレイカーを
    キーワードとして持つ（本弾で構築した部分）。"""
    e = _build(rules, {"bz": ["T1166"]}, {})
    src = _cid(e, "T1166", 0)
    kw = e.chars(src)["keywords"]
    assert "blocker" in kw
    assert "double_breaker" in kw


def test_granted_speed_attacker_not_caught_by_base_scope(rules):
    """既知の制限の固定: 静的効果の affects 照合は
    base（印刷特性）で行われるため、他の効果で
    付与されたスピードアタッカー（T314 の自己付与）は
    本フィルタに掛からず deny は付かない。keyword
    フィルタを使う登録済み静的効果すべてが共有する
    エンジン全体の規約（第398弾 docs 参照）。"""
    e = _build(rules,
               {"bz": ["T1166", "T314"]},
               {})
    granted = _cid(e, "T314", 0)
    e.s.mut_card(granted).entered_turn = e.s.turn
    ch = e.chars(granted)
    assert "speed_attacker" in ch["keywords"]   # 付与自体は有効
    assert "attack_player" not in ch["deny"]
    assert "attack_creature" not in ch["deny"]


def _charge(e, player, tid):
    """player の最初の charge で tid を選んで置く。
    置けたら True を返す。"""
    for _ in range(300):
        d = e.advance()
        if d is None:
            return False
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge" and d.get("player") == player:
            hit = [i for i, k in enumerate(keys) if tid in k]
            if hit:
                e.answer([hit[0]])
                # 回答は次の advance で処理される。マナに現れた
                # 時点で止める（次の自ターン開始のアンタップ
                # ステップで解けてしまうため、それより前に見る）
                for _ in range(4):
                    if any(e.cdef(c).id == tid
                           for c in e.zlist("mana", player)):
                        break
                    d2 = e.advance()
                    if d2 is None:
                        break
                    keys2 = [o["key"] for o in d2["options"]]
                    if "pass" in keys2:
                        e.answer([keys2.index("pass")])
                    elif "no_block" in keys2:
                        e.answer([keys2.index("no_block")])
                    elif d2["kind"] == "declare_strigger":
                        e.answer([])
                    else:
                        e.answer(list(range(d2.get("min", 0))))
                return True
            if "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        else:
            e.answer(list(range(d.get("min", 0))))
    return False


def test_multicolor_card_enters_mana_tapped(rules):
    """「マナゾーンに置く時、このカードはタップして
    置く」は多色カードのルール（405.1）: 光・水の
    2文明を持つ T1166 を手札からマナに置くと
    タップ状態で置かれる。対照として単色の T1090
    （火）はアンタップで置かれる。"""
    e = _build(rules, {"hand": ["T1166"]}, {})
    assert _charge(e, 0, "T1166")
    mana = [c for c in e.zlist("mana", 0) if e.cdef(c).id == "T1166"]
    assert len(mana) == 1
    assert e.s.cards[mana[0]].tapped
    e2 = _build(rules, {"hand": ["T1090"]}, {})
    assert _charge(e2, 0, "T1090")
    mana2 = [c for c in e2.zlist("mana", 0) if e2.cdef(c).id == "T1090"]
    assert len(mana2) == 1
    assert not e2.s.cards[mana2[0]].tapped
