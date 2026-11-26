"""語彙パイロット第417弾: battle_win_destroy（ドリフト）。

センサス（rejects 1,915件を取り直し）: pure 1,767件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜416弾）は原則として再提案しない。
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
次点候補を本弾で再評価した: destroyed_this_turn_
condition（dm26ex2-mc012。素行で、手札ゾーンの
ターン終了時無償詠唱付与が未検証＝最小でない）、
count_cards_drawn_this_turn（dm12-010。相手ターン
終了誘発＋手札全捨ての組み合わせが未検証）、
distinct_civ_count（dmx19-s45。3条項の複合＝後続
候補のまま）、first_time_tap（pure 2。第410弾で
記録の新規語彙候補＝本弾では着手しない）。

範囲内・最小の **battle_win_destroy（pure 1件、
multi にも現れない）** を選定した。第415弾で
「第413弾の battle_win 自壊形そのものだが、partial が
骨格のみで3条項が未構築。次弾以降の候補として残す」
と記録された候補で、本弾で未構築3条項の確立形を
すべて確認した完全なドリフト:
- 自壊条項は trigger {when: {event: battle_win,
  subject: self}, effect: [destroy {select:
  {ref: self}}]}（第413弾の確立形、登録済み
  dm01-026 の登録形と完全一致を直接照合）。
  敗北・相打ち時はバトル自体で破壊されるため
  battle_win 誘発のみで挙動等価。
- G・ゼロは free_if {exists: {zone: bz, owner: you,
  filter: {race_has: ゴッド}}}（登録済み
  dm22rp2x-tf14 の条件形と同一。ゴッド参照の
  フィルタは登録先例すべて race_has: ゴッド）。
- ブロッカーはキーワード blocker、相手プレイヤーを
  攻撃できないはキーワード cannot_attack_player
  （同一文面の自己制限は converted でキーワード形
  328件 vs static deny 形23件＝キーワードが標準形。
  本弾で実測）。parse では allow [block] /
  deny [attack_player] の static に展開される。
- 「マナゾーンに置く時タップして置く」は多色
  ルール（405.1）でエンジン core が適用済み
  （第399弾）＝text のみ。

対象は dmr11-051 護神のインガ イヌハッカ（光/闇の
クリーチャー / コスト3 / パワー5500 / 種族
オラクル）。partial は骨格のみ（keywords・
abilities・free_if は無く、text は断片）。
**補完あり: text のみ**（行の公式テキスト全文を
使う）。alias は dmr11-051m の1件で rejects に
独自行は無く、identity 実測で canon_id は対象自身
（alias 側の canon も dmr11-051）、aliases_for =
[dmr11-051m]。第417弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも対象 id・
alias とも登録なし。単面カードで未検証の面は無い。
登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（convert も None）＝ツール側ブロッカーなし。

proto T1186（dmr11-051 型）。判別役は既存 proto を
流用: T001（パワー2000バニラ役）/ T1139（パワー
6000役）/ T1140（パワー4000ブロッカー役＝対照）/
T873（光マナ役）/ T872（闇マナ役）/ T1090（単色の
マナ置き対照）。新規判別役 T1187（ゴッドのバニラ
役）/ T1188（ゴッド・ノヴァ OMG のバニラ役＝
race_has の部分一致判別）。

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

FREE_IF = {"exists": {"zone": "bz", "owner": "you",
                      "filter": {"race_has": "ゴッド"}}}
TRIG = {"kind": "trigger",
        "when": {"event": "battle_win", "subject": "self"},
        "effect": [{"op": "destroy", "select": {"ref": "self"}}]}
FORM = [TRIG]
KEYWORDS = ["blocker", "cannot_attack_player"]
# parse 後の形: キーワード2件が static に展開され、
# destroy は move（reason: destroy）に正規化される
PARSED_TRIG = {"kind": "trigger",
               "when": {"event": "battle_win", "subject": "self"},
               "effect": [{"op": "move", "select": {"ref": "self"},
                           "to": "graveyard", "reason": "destroy"}]}
FULL_TEXT = ("マナゾーンに置く時、このカードはタップして置く。"
             "G・ゼロ - バトルゾーンに自分のゴッドがあれば、"
             "このクリーチャーをコストを支払わずに召喚してもよい。 "
             "ブロッカー"
             "このクリーチャーは、相手プレイヤーを攻撃できない。"
             "このクリーチャーはバトルに勝っても、バトルの後、破壊される。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1186")
    assert c["free_if"] == FREE_IF
    assert c["abilities"] == FORM
    assert c["name"] == "護神のインガ イヌハッカ"
    assert c["types"] == ["creature"] and c["civs"] == ["light", "darkness"]
    assert c["cost"] == 3 and c["power"] == 5500 and c["mana"] == 1
    assert c["races"] == ["オラクル"]
    assert c["keywords"] == KEYWORDS
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.free_if == FREE_IF
    assert PARSED_TRIG in d.abilities
    # キーワード由来 static 2件＋誘発1件
    assert len(d.abilities) == 3
    assert d.keywords == KEYWORDS
    for tid in ("T001", "T872", "T873", "T1090", "T1139",
                "T1140", "T1187", "T1188"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX417", "name": "護神のインガ イヌハッカ",
                    "types": ["creature"], "civs": ["light", "darkness"],
                    "cost": 3, "power": 5500, "mana": 1,
                    "races": ["オラクル"],
                    "keywords": list(KEYWORDS),
                    "free_if": copy.deepcopy(FREE_IF),
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert d.free_if == FREE_IF
    assert PARSED_TRIG in d.abilities
    assert len(d.abilities) == 3
    assert d.keywords == KEYWORDS


def _bad(mut):
    c = {"id": "TX417B", "name": "x", "types": ["creature"],
         "civs": ["light", "darkness"], "cost": 3, "power": 5500,
         "mana": 1, "races": ["オラクル"],
         "keywords": list(KEYWORDS),
         "free_if": copy.deepcopy(FREE_IF),
         "abilities": copy.deepcopy(FORM)}
    mut(c)
    with pytest.raises(DefError):
        parse_card(c, TABLES)


def test_bad_free_if_unknown_key():
    _bad(lambda c: c.update(free_if={"bogus": 1}))


def test_bad_exists_filter_key():
    _bad(lambda c: c.update(
        free_if={"exists": {"zone": "bz", "owner": "you",
                            "filter": {"bogus_key": 1}}}))


def test_bad_exists_zone():
    _bad(lambda c: c.update(
        free_if={"exists": {"zone": "sideways", "owner": "you",
                            "filter": {"race_has": "ゴッド"}}}))


def test_bad_exists_owner():
    _bad(lambda c: c.update(
        free_if={"exists": {"zone": "bz", "owner": "bogus",
                            "filter": {"race_has": "ゴッド"}}}))


def test_bad_unknown_keyword():
    _bad(lambda c: c.update(keywords=["bogus_kw"]))


def test_bad_unknown_event():
    _bad(lambda c: c.update(abilities=[
        {"kind": "trigger",
         "when": {"event": "battle_winn", "subject": "self"},
         "effect": [{"op": "destroy", "select": {"ref": "self"}}]}]))


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _tapped_mana(e, p):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _main_keys(e, player):
    """player の最初の main 決定の選択肢キーを返す。"""
    for _ in range(900):
        d = e.advance()
        if d is None:
            return None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == player:
            return keys
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return None


def _play_and_settle(e, player, key, done):
    """player の main で key を選び、done() になるまで進める。"""
    played = False
    for _ in range(600):
        if played and done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" \
                and d.get("player") == player and key in keys:
            played = True
            e.answer([keys.index(key)])
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return done()


MANA3 = ["T873", "T872", "T873"]   # 光・闇を含む3枚（コスト3の支払い用）


def test_no_free_without_god(rules):
    """ゴッドがいなければ無料選択肢は出ず、有料だけが出る
    （場の非ゴッド T001 では条件を満たさない判別込み）。"""
    e = _build(rules,
               {"hand": ["T1186"], "mana": list(MANA3), "bz": ["T001"]},
               {})
    keys = _main_keys(e, 0)
    assert "play:T1186" in keys
    assert "play:T1186:free" not in keys


def test_free_with_god_and_no_mana_tapped(rules):
    """自分のゴッド（T1187）がいれば無料選択肢が出て、
    無料召喚ではマナは1枚もタップされない。"""
    e = _build(rules,
               {"hand": ["T1186"], "mana": list(MANA3), "bz": ["T1187"]},
               {})
    keys = _main_keys(e, 0)
    assert "play:T1186:free" in keys
    ok = _play_and_settle(e, 0, "play:T1186:free",
                          lambda: _in_zone(e, 0, "bz", "T1186"))
    assert ok
    assert _tapped_mana(e, 0) == 0


def test_free_with_god_nova_race_has(rules):
    """race_has の判別: 種族ゴッド・ノヴァ OMG（T1188）も
    「ゴッド」に数えられ、無料選択肢が出る。"""
    e = _build(rules,
               {"hand": ["T1186"], "mana": list(MANA3), "bz": ["T1188"]},
               {})
    keys = _main_keys(e, 0)
    assert "play:T1186:free" in keys


def test_no_free_with_opponent_god(rules):
    """owner: you の判別: 相手のゴッドだけでは
    無料にならない。"""
    e = _build(rules,
               {"hand": ["T1186"], "mana": list(MANA3)},
               {"bz": ["T1187"]})
    keys = _main_keys(e, 0)
    assert "play:T1186" in keys
    assert "play:T1186:free" not in keys


def test_paid_summon(rules):
    """通常の支払いでも召喚できる（free_if は支払い経路を
    妨げない）。光・闇を含む3枚がタップされる。"""
    e = _build(rules, {"hand": ["T1186"], "mana": list(MANA3)}, {})
    ok = _play_and_settle(e, 0, "play:T1186",
                          lambda: _in_zone(e, 0, "bz", "T1186"))
    assert ok
    assert _tapped_mana(e, 0) == 3


def test_attack_player_denied_creature_allowed(rules):
    """相手プレイヤーを攻撃できない（cannot_attack_player）:
    permits では attack_player のみ不許可で、
    attack_creature と block は許可。攻撃選択肢でも
    タップした相手クリーチャーへの攻撃だけが出て、
    プレイヤー攻撃は出ない（cannot_attack との判別）。"""
    e = _build(rules, {"bz": ["T1186"]}, {"bz": ["T001"]})
    cid = next(c for c in e.zlist("bz", 0)
               if e.s.cards[c].defn == "T1186")
    opp = next(c for c in e.zlist("bz", 1)
               if e.s.cards[c].defn == "T001")
    assert not e.permits(cid, "attack_player")
    assert e.permits(cid, "attack_creature")
    assert e.permits(cid, "block")
    assert e._attack_options(0) == []
    e.s.mut_card(opp).tapped = True
    keys = [o["key"] for o in e._attack_options(0)]
    assert keys == ["attack:T1186:T001"]


def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "yes_no":
        e.answer([keys.index("yes")] if "yes" in keys
                 else list(range(d["min"])))
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _drive_battle(e, atk_player, atk, blk):
    """第413弾と同型: atk がプレイヤーを攻撃し、相手が
    blk でブロックするバトルを1回行い、攻撃側のターンが
    終わる（防御側の charge）まで進める。観測した
    hist:battle_win の最大値を併せて返す。"""
    state = {"attacked": False, "blocked": False,
             "win_seen": {0: 0, 1: 0}}
    for _ in range(4000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        for p in (0, 1):
            v = max(e.s.turn_counters.get(f"hist:battle_win:{p}") or 0,
                    e.s.prev_counters.get(f"hist:battle_win:{p}") or 0)
            state["win_seen"][p] = max(state["win_seen"][p], v)
        if state["blocked"] and d["kind"] == "charge" \
                and d.get("player") != atk_player:
            break
        if d["kind"] == "attack" and d.get("player") == atk_player \
                and not state["attacked"]:
            state["attacked"] = True
            e.answer([keys.index(f"attack:{atk}:player")])
            continue
        if d["kind"] == "block":
            pick = [i for i, k in enumerate(keys)
                    if k.startswith(f"bz:{blk}")]
            if pick:
                state["blocked"] = True
                e.answer([pick[0]])
            else:
                e.answer([keys.index("no_block")])
            continue
        _answer_default(e, d)
    assert state["attacked"] and state["blocked"], state
    return state


def test_block_win_destroys_self(rules):
    """本弾の判別: パワー2000の攻撃をブロックして
    バトルに勝つと、バトルの後に自身が破壊される
    （攻撃側はバトルで破壊され、シールドは割れない）。"""
    e = _build(rules, {"bz": ["T1186"]}, {"bz": ["T001"]})
    shields_before = len(e.zlist("shield", 0))
    state = _drive_battle(e, 1, "T001", "T1186")
    assert state["win_seen"][0] == 1
    assert _in_zone(e, 1, "graveyard", "T001")
    assert _in_zone(e, 0, "graveyard", "T1186")
    assert not _in_zone(e, 0, "bz", "T1186")
    assert len(e.zlist("shield", 0)) == shields_before


def test_block_win_control_blocker_survives(rules):
    """対照: 誘発を持たないブロッカー（T1140、パワー
    4000）が同じ攻撃をブロックして勝てば生き残る。"""
    e = _build(rules, {"bz": ["T1140"]}, {"bz": ["T001"]})
    state = _drive_battle(e, 1, "T001", "T1140")
    assert state["win_seen"][0] == 1
    assert _in_zone(e, 1, "graveyard", "T001")
    assert _in_zone(e, 0, "bz", "T1140")
    assert not _in_zone(e, 0, "graveyard", "T1140")


def test_block_lose_destroyed_by_battle_not_trigger(rules):
    """敗北時: パワー6000の攻撃をブロックして負ければ
    バトル自体で破壊される。勝ちは記録されず（誘発は
    発火しない）、攻撃側は生き残る。"""
    e = _build(rules, {"bz": ["T1186"]}, {"bz": ["T1139"]})
    state = _drive_battle(e, 1, "T1139", "T1186")
    assert state["win_seen"][0] == 0
    assert state["win_seen"][1] == 1
    assert _in_zone(e, 0, "graveyard", "T1186")
    assert _in_zone(e, 1, "bz", "T1139")


def _charge(e, player, tid):
    """第399弾と同型: player の最初の charge で tid を
    選んで置く。置けたら True を返す。"""
    for _ in range(300):
        d = e.advance()
        if d is None:
            return False
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge" and d.get("player") == player:
            hit = [i for i, k in enumerate(keys) if tid in k]
            if hit:
                e.answer([hit[0]])
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
    """第1条項「マナゾーンに置く時、このカードはタップ
    して置く」は多色カードのルール（405.1）: 光/闇の
    T1186 を手札からマナに置くとタップ状態で置かれる。
    対照として単色の T1090（火）はアンタップで置かれる
    （第399弾と同型の検証）。"""
    e = _build(rules, {"hand": ["T1186"]}, {})
    assert _charge(e, 0, "T1186")
    mana = [c for c in e.zlist("mana", 0) if e.cdef(c).id == "T1186"]
    assert len(mana) == 1
    assert e.s.cards[mana[0]].tapped
    e2 = _build(rules, {"hand": ["T1090"]}, {})
    assert _charge(e2, 0, "T1090")
    mana2 = [c for c in e2.zlist("mana", 0) if e2.cdef(c).id == "T1090"]
    assert len(mana2) == 1
    assert not e2.s.cards[mana2[0]].tapped
