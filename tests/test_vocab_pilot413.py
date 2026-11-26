"""語彙パイロット第413弾: battle_result_destruction（ドリフト）。

センサス（rejects 1,919件を取り直し）: pure 1,771件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜412弾）は原則として再提案しない。
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
残置のまま。

範囲内・最小の **battle_result_destruction（pure 1件、
multi にも現れない）** を選定した。第412弾で次点として
記録された候補で、登録先例を本弾で直接照合した:
trigger {when: {event: battle_win, subject: self},
effect: [destroy {select: {ref: self}}]} は登録済み
dm01-026 ダーク・クラウン / dm01-056 捕らえる者
ボーン・スパイダー / dm01-089 ブラッディ・イヤリング /
dm06-027 虚空の翼ダークモルダー / dm06-087 砕骨の
刺客ゾルバス の5件で「このクリーチャーはバトルに
勝っても、バトルのあと、持ち主の墓地に置かれる」を
表す確立形（全5件の登録形が同一であることを確認）。
本件の文面は「バトルに勝っても、バトルの後、破壊
される」で destroy op と直接対応し（先例の「持ち主の
墓地に置かれる」と結果は同一）、敗北・相打ちの時は
バトル自体で破壊されるため battle_win 誘発のみで
挙動等価になる。行の注記「バトル結果依存の破壊を
表す語彙が無い」は既存イベント battle_win の見落としで、
完全なドリフト（新規語彙・エンジン・defs・スキーマ
変更なし）。

対象は dmx03-036 ブラッディ・シンバル（闇の
クリーチャー / コスト2 / パワー4000 / 種族
ガーゴイル）。partial は骨格完備（mana 1、keywords
[blocker, cannot_attack] が構築済み）で、未解決は
unsupported の battle_result_destruction 1件だけ。
partial の text は行の公式テキスト全文と一致する
ため**補完なし**。alias は dm14-091 / dmc42-071 の
2件で、いずれも rejects に独自行は無く、identity
実測で canon_id は対象自身（alias 側の canon も
dmx03-036）、aliases_for = [dm14-091, dmc42-071]。
第413弾時点で real.yaml / real_akashic.yaml /
real_vocab.yaml / real_zone.yaml / proto.yaml /
converted.yaml のいずれにも対象 id・alias とも
登録なし。単面カードで未検証の面は無い。
登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['blocker', 'cannot_attack'],
「このクリーチャーはバトルに勝っても、バトルの後、
破壊される。」, []) を返し、part[2] の定型所有は空
（キーワードは partial と一致）＝ツール側ブロッカー
なし。

確立形は abilities 1件:
trigger {when: {event: battle_win, subject: self},
effect: [{op: destroy, select: {ref: self}}]}。
parse では destroy は move {select: {ref: self},
to: graveyard, reason: destroy} に正規化され、
keywords の blocker / cannot_attack はそれぞれ
allow [block] / deny [attack_player, attack_creature]
の static に展開される。

proto T1181（dmx03-036 型）。判別役は既存 proto を
流用: T001（パワー2000バニラ役＝負ける攻撃側）/
T1139（パワー6000役＝勝つ攻撃側・味方の勝ち判別）/
T1140（パワー4000ブロッカー役＝相打ち判別・誘発なし
対照）。

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

TRIG = {"kind": "trigger",
        "when": {"event": "battle_win", "subject": "self"},
        "effect": [{"op": "destroy", "select": {"ref": "self"}}]}
FORM = [TRIG]
# parse 後の形: destroy は move（reason: destroy）に
# 正規化され、キーワード2件が static に展開される
PARSED_TRIG = {"kind": "trigger",
               "when": {"event": "battle_win", "subject": "self"},
               "effect": [{"op": "move", "select": {"ref": "self"},
                           "to": "graveyard", "reason": "destroy"}]}
FULL_TEXT = ("ブロッカー(相手クリーチャーが攻撃する時、このクリーチャーを"
             "タップして、その攻撃を阻止してもよい。その後、その相手"
             "クリーチャーとバトルする)\n"
             "このクリーチャーは攻撃することができない。\n"
             "このクリーチャーはバトルに勝っても、バトルの後、破壊される。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1181")
    assert c["abilities"] == FORM
    assert c["name"] == "ブラッディ・シンバル"
    assert c["types"] == ["creature"] and c["civs"] == ["darkness"]
    assert c["cost"] == 2 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ガーゴイル"]
    assert c["keywords"] == ["blocker", "cannot_attack"]
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    assert PARSED_TRIG in d.abilities
    # キーワード由来 static 2件＋誘発1件
    assert len(d.abilities) == 3
    assert d.keywords == ["blocker", "cannot_attack"]
    for tid in ("T001", "T1139", "T1140"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX413", "name": "ブラッディ・シンバル",
                    "types": ["creature"], "civs": ["darkness"],
                    "cost": 2, "power": 4000, "mana": 1,
                    "races": ["ガーゴイル"],
                    "keywords": ["blocker", "cannot_attack"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert PARSED_TRIG in d.abilities
    assert len(d.abilities) == 3


def _bad(ability):
    with pytest.raises(DefError):
        parse_card({"id": "TX413B", "name": "x", "types": ["creature"],
                    "civs": ["darkness"], "cost": 2, "power": 4000,
                    "abilities": [ability]}, TABLES)


def test_bad_unknown_event():
    _bad({"kind": "trigger",
          "when": {"event": "battle_winn", "subject": "self"},
          "effect": [{"op": "destroy", "select": {"ref": "self"}}]})


def test_bad_unknown_op():
    _bad({"kind": "trigger",
          "when": {"event": "battle_win", "subject": "self"},
          "effect": [{"op": "bogus", "select": {"ref": "self"}}]})


def test_bad_unknown_keyword():
    with pytest.raises(DefError):
        parse_card({"id": "TX413B", "name": "x", "types": ["creature"],
                    "civs": ["darkness"], "cost": 2, "power": 4000,
                    "keywords": ["bogus_kw"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


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


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _drive_battle(e, atk_player, atk, blk):
    """atk_player の atk がプレイヤーを攻撃し、相手が
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
            # ターン終了で prev_counters へ退避されるため両方を見る
            # （第382弾の観測作法）
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


def test_cannot_attack(rules):
    """攻撃することができない: 攻撃選択肢に出ず、
    permits でも attack_player / attack_creature が
    どちらも不許可（cannot_attack の deny 展開）。"""
    e = _build(rules, {"bz": ["T1181"]}, {"bz": []})
    assert e._attack_options(0) == []
    cid = next(c for c in e.zlist("bz", 0)
               if e.s.cards[c].defn == "T1181")
    assert not e.permits(cid, "attack_player")
    assert not e.permits(cid, "attack_creature")
    # ブロック自体は可能（blocker は allow [block]）
    assert e.permits(cid, "block")


def test_block_win_destroys_self(rules):
    """本弾の判別: パワー2000の攻撃をブロックして
    バトルに勝つと、バトルの後に自身が破壊される
    （攻撃側はバトルで破壊され、シールドは割れない）。"""
    e = _build(rules, {"bz": ["T1181"]}, {"bz": ["T001"]})
    shields_before = len(e.zlist("shield", 0))
    state = _drive_battle(e, 1, "T001", "T1181")
    assert state["win_seen"][0] == 1     # 自分の勝ちが記録された
    assert _in_zone(e, 1, "graveyard", "T001")   # 敗者はバトルで破壊
    assert _in_zone(e, 0, "graveyard", "T1181")  # 勝っても破壊される
    assert not _in_zone(e, 0, "bz", "T1181")
    assert len(e.zlist("shield", 0)) == shields_before


def test_block_win_control_blocker_survives(rules):
    """対照: 誘発を持たないブロッカー（T1140、パワー
    4000）が同じ攻撃をブロックして勝てば生き残る。
    T1181 の消滅は誘発によるものであることの判別。"""
    e = _build(rules, {"bz": ["T1140"]}, {"bz": ["T001"]})
    state = _drive_battle(e, 1, "T001", "T1140")
    assert state["win_seen"][0] == 1
    assert _in_zone(e, 1, "graveyard", "T001")
    assert _in_zone(e, 0, "bz", "T1140")          # 勝者は残る
    assert not _in_zone(e, 0, "graveyard", "T1140")


def test_block_lose_destroyed_by_battle_not_trigger(rules):
    """敗北時: パワー6000の攻撃をブロックして負ければ
    バトル自体で破壊される。勝ちは記録されず（誘発は
    発火しない）、攻撃側は生き残る。"""
    e = _build(rules, {"bz": ["T1181"]}, {"bz": ["T1139"]})
    state = _drive_battle(e, 1, "T1139", "T1181")
    assert state["win_seen"][0] == 0     # 勝ちは無い
    assert state["win_seen"][1] == 1     # 勝ちは攻撃側のもの
    assert _in_zone(e, 0, "graveyard", "T1181")
    assert _in_zone(e, 1, "bz", "T1139")


def test_block_draw_both_destroyed_by_battle(rules):
    """相打ち（4000 vs 4000）: 両者ともバトル自体で
    破壊され、勝ちはどちらにも記録されない。"""
    e = _build(rules, {"bz": ["T1181"]}, {"bz": ["T1140"]})
    state = _drive_battle(e, 1, "T1140", "T1181")
    assert state["win_seen"][0] == 0
    assert state["win_seen"][1] == 0
    assert _in_zone(e, 0, "graveyard", "T1181")
    assert _in_zone(e, 1, "graveyard", "T1140")


def test_ally_win_does_not_destroy_self(rules):
    """subject: self の判別: 味方（T1139、パワー6000）が
    相手のブロッカー（T1140）に勝っても、バトルを
    していない T1181 は破壊されず場に残る。"""
    e = _build(rules, {"bz": ["T1181", "T1139"]}, {"bz": ["T1140"]})
    state = _drive_battle(e, 0, "T1139", "T1140")
    assert state["win_seen"][0] == 1     # 味方の勝ちは記録される
    assert _in_zone(e, 1, "graveyard", "T1140")
    assert _in_zone(e, 0, "bz", "T1139")     # 勝った味方は残る
    assert _in_zone(e, 0, "bz", "T1181")     # 自身は無事
    assert not _in_zone(e, 0, "graveyard", "T1181")
