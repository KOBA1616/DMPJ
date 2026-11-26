"""語彙パイロット第375弾: metamorph（ドリフト）。

センサス（rejects 1,958件を取り直し）: pure 1,810件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜374弾）は再提案しない。本弾で個別に
評価して見送った候補: eternal_omega（pure 1、
dmx15-s01。キーワード自体は keywords.yaml で実装済み
だが、partial が攻撃誘発〔各文明1体ずつ破壊＝却下済み
per_civilization_selection 系〕と Q・ブレイカーを欠いた
stub で、本 gap 単独では登録形が定まらない）、
destroy_replaces_to_mana（pure 1、dmex08-021。partial は
骨格のみで、付与する置換そのものが gap）、
self_return_instead（pure 1、dmr05-094。捨てたカードの
種類への条件つき自己置換で照合の仕組みが要る）、
tap_all_except_chosen（pure 1、dm10-016。選んだ1体を
除く一括タップは除外参照が要る）、no_leave_only_battle
（pure 1、dmr03-014。partial が空で種族追加条項も残る）、
trigger_when_battle_won（pure 1、dm26ex4-052。マナ枚数
パワーと攻撃強制条項が partial に未組立て）、
self_break_own_shield（pure 1、dmrp06-007。partial が
x/y の仮面 stub）、s_trigger_cast_spell_returns_to_hand
（pure 1、dm08-s05。cast イベント照合系で却下済みと同根）、
civilization_breaker（pure 1、dm27-010。ブレイク数が
マナの文明数で変わる可変ブレイクで却下済みと同根）、
shield_faceup_trigger（pure 1、dmd11-006。表向き
シールドの数え上げ系で却下済みと同根）、
last_shield_trigger（pure 1、dmx26-v01。最後の1枚が
ブレイクされた時の照合＋アンタップ付与が残る）、
indestructible_duration（pure 1、promoy13-019。マナ武装
条件つきの全体不死身付与で、バトル外も含む indestructible
の付与形が要る）。範囲内・未評価で最小の
metamorph（pure 1件、multi にも現れない）を選定した。

対象は pure 1件すべて: dm14-018 サルベージ・クラスター
（水 / コスト5 / パワー3000 / サイバー・クラスター）。
partial は「ブロックされない」（keywords [unblockable]）と
破壊置換〔replace {when: {event: move, from: bz,
to: graveyard, reason: destroy, subject: self},
instead: [move {ref: self} to hand]}〕が組立て済みで、
未解決は unsupported の metamorph 1件だけ。partial の
text は行の公式テキスト全文と一致する（補完なし）。
単面カードで未検証の面は無い。条項「メタモーフ（自分の
マナゾーンに７枚以上カードがあれば、このクリーチャーは
次の能力を得る）」は確立済みの部品で表せる（追加語彙なし）:

- 条件のイディオムは登録先例 dm14-024（同じ DM14 の
  メタモーフ持ち。static の if で同条件）・dm23bd5-056
  （呪文効果の if 分岐）と同形:
  {cmp: [{count: {zone: mana, owner: you}}, ">=", 7]}。
  数えるのは自分のマナゾーンのカードすべて（文明
  フィルタ無し。公式テキストどおり）。
- 置換能力への if は ABILITY_KEYS の共通キーで、
  エンジンも _replacement で eval_cond を評価する
  （events.py のコメント「置換効果にも条件を書ける」。
  rustcore の単純形判定も replace + if を想定内とする）。
  条件が外れれば置換候補自体が出ない（諮問も出ない）。

確立形: abilities = [replace {when: {event: move,
from: bz, to: graveyard, reason: destroy, subject: self},
if: {cmp: [{count: {zone: mana, owner: you}}, ">=", 7]},
instead: [move {select: {ref: self}, to: hand,
reason: return}]}] の1件（partial の置換に if を
足しただけ）。

**登録ブロッカー（ラウンド410への申し送り）**:
語彙としてはこの形で正確に登録できるはずだが、
agent_convert の submit は rule_convert.split の
結果を merge_split で先頭に戻し、完全一致でしか
dedupe しない。dm14-018 の原文では split が
「破壊される時、墓地に置くかわりに自分の手札に戻す」を
定型パターンとして所有し、無条件形の置換を part[2] に
返す（本弾で実測）。そのため現行パイプラインでは、
回答に条件つき置換を含めると無条件形と二重に付き、
含めなければ無条件形だけが付いて、どちらも誤りになる。
ラウンド410はこのまま submit せず、split にメタモーフ
条件を伝える改修か、merge_split に supersede（回答側の
能力が定型側を上書きする）意味論を足すかを先に判断する
こと（詳細は docs/vocab-pilot.md 第375弾）。

proto T1123（dm14-018 型）。判別役は既存 proto を
流用: T1105（パワー4000ブロッカー）/ T001（マナ役・
素のクリーチャー）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接包む
（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

REPLACE = {"kind": "replace",
           "when": {"event": "move", "from": "bz", "to": "graveyard",
                    "reason": "destroy", "subject": "self"},
           "if": {"cmp": [{"count": {"zone": "mana", "owner": "you"}},
                          ">=", 7]},
           "instead": [{"op": "move", "select": {"ref": "self"},
                        "to": "hand", "reason": "return"}]}
FORM = [REPLACE]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1123")
    assert c["abilities"] == FORM
    assert c["keywords"] == ["unblockable"]
    assert c["types"] == ["creature"] and c["civs"] == ["water"]
    assert c["cost"] == 5 and c["power"] == 3000
    assert c["races"] == ["サイバー・クラスター"]
    d = parse_card(copy.deepcopy(c), TABLES)
    assert REPLACE in d.abilities
    parse_card(proto_card("T1105"), TABLES)
    parse_card(proto_card("T001"), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX375", "name": "x",
                    "types": ["creature"], "civs": ["water"],
                    "cost": 5, "power": 3000, "mana": 1,
                    "races": ["サイバー・クラスター"],
                    "keywords": ["unblockable"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert REPLACE in d.abilities


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
    進める（第367弾の作法）。"""
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


def _drive_destroyed_in_battle(e, target="T1123", hunter="T1105"):
    """target（p1）はブロックされないため、破壊経路は
    「プレイヤーを攻撃してタップした後、相手の hunter に
    クリーチャー攻撃される」形にする。まず target が
    プレイヤーを攻撃し（タップする）、次の相手ターンに
    hunter が target を攻撃してバトルで破壊する。
    choose_replacement の諮問が出たら置換を選ぶ。
    バトルのターンの2つ先まで進め、状態を返す。"""
    state = {"charged": False, "hunted": False, "hunt_turn": None,
             "replace_offered": False}
    for _ in range(1500):
        if state["hunted"] and e.s.turn >= state["hunt_turn"] + 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack" and d.get("player") == 1:
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{target}:player"]
            if hit and not state["charged"]:
                state["charged"] = True
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "attack" and d.get("player") == 0:
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{hunter}:{target}"]
            if hit and state["charged"] and not state["hunted"]:
                state["hunted"] = True
                state["hunt_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "choose_replacement":
            state["replace_offered"] = True
            hit = [i for i, k in enumerate(keys)
                   if k.startswith(f"replace:{target}:")]
            assert hit, keys
            e.answer([hit[0]])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


def test_destroy_returns_to_hand_with_seven_mana(rules):
    """実挙動: 自分のマナが7枚あれば、バトルに負けて
    破壊される代わりに手札に戻る（墓地には行かない）。
    置換は強制のため、この破壊経路では諮問を介さず
    適用される（ゾーン結果で判別する）。"""
    e = _build(rules, {"bz": ["T1105"]},
               {"bz": ["T1123"], "mana": ["T001"] * 7})
    st = _drive_destroyed_in_battle(e)
    assert st["charged"] and st["hunted"]
    assert "T1123" in _defns(e, "hand", 1)
    assert "T1123" not in _defns(e, "graveyard", 1)
    assert "T1123" not in _defns(e, "bz", 1)
    assert "T1105" in _defns(e, "bz", 0)


def test_destroy_goes_to_graveyard_with_six_mana(rules):
    """対照: 自分のマナが6枚ではメタモーフ条件が外れ、
    置換は適用されず、そのまま破壊され墓地に行く。"""
    e = _build(rules, {"bz": ["T1105"]},
               {"bz": ["T1123"], "mana": ["T001"] * 6})
    st = _drive_destroyed_in_battle(e)
    assert st["charged"] and st["hunted"] and not st["replace_offered"]
    assert "T1123" in _defns(e, "graveyard", 1)
    assert "T1123" not in _defns(e, "hand", 1)
    assert "T1105" in _defns(e, "bz", 0)


def test_unblockable_cannot_be_blocked(rules):
    """実挙動: ブロックされないため、ブロッカーがいても
    プレイヤー攻撃が通りシールドが1枚ブレイクされる
    （キーワードは partial の組立て済み部分）。"""
    e = _build(rules, {"bz": ["T1105"]}, {"bz": ["T1123"]})
    before = len(e.zlist("shield", 0))
    st = _drive_attack(e, "T1123", block_with="T1105")
    assert st["attacked"]
    assert len(e.zlist("shield", 0)) == before - 1
    assert "T1123" in _defns(e, "bz", 1)
    assert "T1105" in _defns(e, "bz", 0)
