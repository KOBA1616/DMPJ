"""語彙パイロット第398弾: speed_attacker_rule（ドリフト）。

センサス（rejects 1,935件を取り直し）: pure 1,787件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
106 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜397弾）は再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021 と
battle_opponent_reference の残り1件 dmr01-049 は
先行弾の評価を覆す根拠が無く再提案しない。
destroyed_this_turn_condition と count_cards_drawn_
this_turn は第392〜397弾の次点のまま残す。本弾で
個別に評価して見送った候補: drew_this_turn_condition
（pure 1、dmx22b-038。G・ゼロの複合条件〈このターン
6枚以上引いた＋同名カードが自分の bz に無い〉で、
partial にはキーワードも能力も何も構築されておらず、
G・ゼロ側の条件付き形の検証が要る）、shield_added_
condition（pure 1、dmrp03-048。手札ゾーンのターン
終了時誘発＋「シールドが手札に加えられた」履歴の
数え上げが未検証）、untap_trigger（pure 1、
dmr02-s01。アンタップ時誘発自体が未検証で、山札
ほぼ全引き＋無償詠唱・召喚が同居する複合）、
mana_tap_trigger（pure 1、dmx08-010。支払いタップの
イベント化が前提＝ラウンド248の差し戻し記録どおり
エンジン側の作業）、hand_add_event（pure 1、
dmrp04s-s04。手札追加イベントの誘発＋加えられた
呪文の無償詠唱が未検証）、leave_trigger（pure 1、
dm37-045。相手クリーチャーの離脱誘発＋名前指定の
公開・選択が同居する複合）、attack_end_trigger
（pure 1、dmrp21-002。攻撃の終わりの自己退場＋
タマシードへの重ね置きが未検証）、battle_win_destroy
（pure 1、dmr11-051。partial には G・ゼロ／ブロッカー／
攻撃制限のいずれも構築されておらず本 gap 単独では
登録形が定まらない）、tap_event_count（pure 1、
dmex09-003。クリーチャーのタップ回数の ord が
未検証で mana_tap_trigger と同根）、first_attack_of_
turn_condition（pure 1、promoy20-003。行の text に
unsupported の条項自体が現れないデータ不整合があり
評価不能）、nth_attack_of_turn_condition（pure 1、
dmrp20-s05。N度目以降の攻撃誘発が3条項同居する複合）、
turn_entry_count（pure 1、dm26rp2-tr007。モード
呪文の2回選択＋無償詠唱条件の複合）、entered_count_
with_filter（pure 1、dm23ex2-038。ツインパクトで、
登場数の文明フィルタが無いという partial の注記
どおり）、grant_all_civilizations /
all_civilizations_mana（いずれも pure 1 でツイン
パクト＋他条項が未構築）、summon_turn_attack_
restriction（pure 1、dmr22-s04。本弾と同一の条項
だが、対象カードの partial が素で〈マナにタップ
して置く〉等の他条項の構築から要る。本弾の確立形は
そのまま使えるため後続候補として残す）、
enters_tapped_rule（pure 1、dmex11-005。第1条項の
スピードアタッカー付与と第2条項の2系統のタップ入り
付与で静的効果3件となり本弾より重い。付与形は
dmrp06-030 等の登録先例があるため後続候補として
残す）。範囲内・最小の **speed_attacker_rule
（pure 1件、multi にも現れない）** を選定した。

対象は pure 1件すべて: dmex11-004 ディオーネ
（水のクリーチャー / コスト3 / パワー3000 /
種族 シー・ハッカー）。partial は骨格完備で、
構築済みは keywords [blocker, cannot_attack]、
未解決は unsupported の speed_attacker_rule
1件だけ。partial の text は行の公式テキスト全文と
一致するため**補完なし**。alias は dm14-004 /
dmx22a-002 の2件で、いずれも rejects に独自行は
無く、identity 実測で canon_id は対象・全 alias
とも dmex11-004、aliases_for = [dm14-004,
dmx22a-002]。第398弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも登録なし
（proto のヒットは T1165 の notes 内参照のみ）。
単面カードで未検証の面は無い。

結論はドリフト（追加語彙なし）:
- 条項「「スピードアタッカー」を持つクリーチャーは、
  バトルゾーンに出たターン、攻撃できない」の確立形は
  static {affects: {zone: bz, owner: any, filter:
  {types: [creature], keyword: speed_attacker,
  entered_this_turn: true}}, mod: {deny:
  [attack_player, attack_creature]}} の1件。
- 土台は第362弾の登録先例 dm23rp4x-014 /
  dm23bd6-003 の形（owner: opp + entered_this_turn
  フィルタ + deny 両方）。本件の文面には対象の
  所有者の限定が無いため owner を any に広げ
  （第384弾の affects owner: any の先例）、フィルタに
  keyword: speed_attacker を足す。keyword フィルタの
  静的効果は登録先例が8件あり、うち dmrp06-030 は
  {keyword: speed_attacker} + enters_tapped 付与で
  同じ照合系統。
- entered_this_turn（第134弾）/ keyword は FILTER_KEYS
  の既存キーで、defs と schema.py（FILTER_KEYS を
  引いて生成）の両側に定義済み（第408ラウンドの教訓）。

既知の制限（実測・第386弾と同型の扱い）: 静的効果の
affects 照合は base=True（印刷特性）で行われる
（selectors.filter_match）ため、**他の効果で付与された
スピードアタッカーは本フィルタに掛からない**
（T314 の自己付与で実測）。これは本弾の形固有では
なく、keyword フィルタを使う登録済み静的効果8件
すべてが共有するエンジン全体の規約であり、付与分を
含む特性値での範囲照合は静的効果の範囲決定の設計
判断として専用ステージ送りとする（本弾では扱わない）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['blocker', 'cannot_attack'],
条項テキスト, []) を返し、part[2] の定型所有は空
＝ブロッカー無し（本弾で実測）。

proto T1165（dmex11-004 型）。判別役は既存 proto を
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
FULL_TEXT = ("ブロッカー\n「スピードアタッカー」を持つクリーチャーは、"
             "バトルゾーンに出たターン、攻撃できない。\n"
             "このクリーチャーは攻撃できない。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1165")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"] and c["civs"] == ["water"]
    assert c["cost"] == 3 and c["power"] == 3000 and c["mana"] == 1
    assert c["races"] == ["シー・ハッカー"]
    assert c["keywords"] == ["blocker", "cannot_attack"]
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    assert STATIC in d.abilities
    for tid in ("T1090", "T1091", "T314"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX398", "name": "ディオーネ",
                    "types": ["creature"], "civs": ["water"],
                    "cost": 3, "power": 3000, "mana": 1,
                    "races": ["シー・ハッカー"],
                    "keywords": ["blocker", "cannot_attack"],
                    "abilities": [copy.deepcopy(STATIC)]}, TABLES)
    assert STATIC in d.abilities


def _bad(ability):
    with pytest.raises(DefError):
        parse_card({"id": "TX398B", "name": "x", "types": ["creature"],
                    "civs": ["water"], "cost": 3, "power": 3000,
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
    ドライバ（第362弾と同型）。攻撃できるクリーチャーが
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
               {"bz": ["T1165"], "hand": ["T1090"],
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
               {"bz": ["T1165", "T1091"]},
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
               {"bz": ["T1165"]},
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
               {"bz": ["T1165", "T1090", "T1091"]},
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


def test_granted_speed_attacker_not_caught_by_base_scope(rules):
    """既知の制限の固定: 静的効果の affects 照合は
    base（印刷特性）で行われるため、他の効果で
    付与されたスピードアタッカー（T314 の自己付与）は
    本フィルタに掛からず deny は付かない。keyword
    フィルタを使う登録済み静的効果8件すべてが共有する
    エンジン全体の規約（第398弾 docs 参照）。"""
    e = _build(rules,
               {"bz": ["T1165", "T314"]},
               {})
    granted = _cid(e, "T314", 0)
    e.s.mut_card(granted).entered_turn = e.s.turn
    ch = e.chars(granted)
    assert "speed_attacker" in ch["keywords"]   # 付与自体は有効
    assert "attack_player" not in ch["deny"]
    assert "attack_creature" not in ch["deny"]
