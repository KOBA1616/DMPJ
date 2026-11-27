"""語彙パイロット第445弾: fury_charge
（ドリフト＋最小エンジン修正）。

センサス（rejects 1,886件を取り直し）: pure は
1〜4件の小家族が多数で、大半は範囲外（gr_summon
147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜444弾）と残置群（graveyard_replacement
残り dm25ex2-cho021、battle_opponent_reference
残り dmr01-049、untap_restriction 残り2件、
does_not_untap 残り dm25ex2-031、revolution_2
残り dm26sd1-o004、cast_limit_once_per_turn の
multi 2件、summoning_attack_rule 残り
dmex07-s01、entered_turn_attack 残り
dmbd11-d05、madness 残り dmx26-028、
after_battle_trigger 残り dmrp09-074、
s_trigger_suppression＝専用ステージ送り、次点の
destroyed_this_turn_condition /
count_cards_drawn_this_turn /
player_not_attacked_while_tapped /
mana_tap_placement、後続候補の
distinct_civ_count、新規語彙候補 first_time_tap /
turn_history_entry / played_free_condition、
第438〜444弾で見送られた各候補）は覆す根拠が
無く再提案しない。本弾で個別に評価して見送った
候補: destroy_after_battle（pure 2。ターン全体の
バトル参加者への事後破壊＝新機構）、
blocker_dies_after_battle_even_if_wins（pure 1。
destroy_after_battle と同根）、battle_lose
（pure 1。第1条項も未構築＋敗北時の相手参照が
残置と同根）、trigger_when_battle_won（pure 1。
5条項中2条項も未構築で最小でない）、
end_of_attack_effect / attack_end_trigger
（pure 1。攻撃の終わりの複合）、
opponent_creatures_never_untap（pure 1。
unsupported 条項が行自身の text に無い＋複合）、
g_strike_effect / tap_each_civilization /
leave_trigger / next_shield_grant /
choose_own_shields_to_be_broken /
super_s_back（pure 1。いずれも複合・未確立機構・
設計領域・範囲外条項）。

範囲内・最小の **fury_charge（pure 1件、multi
にも現れない）** を選定した。対象は dmx12b-015
Tatsurion。条項は1つだけ: 「フュリー・チャージ：
このクリーチャーは、バトルゾーンに出たターンに、
タップしているクリーチャーを攻撃できる」＋
W・ブレイカー。形はマッハファイターの確立形
（第58弾・keyword_patterns.yaml の mach_fighter
パターン、登録済み195件）の鏡像:
trigger {when: {event: move, to: bz, subject:
self}, effect: [modify {select: {ref: self},
mod: {allow: [{action: attack_creature, other:
{tapped: true}}]}, duration: end_of_turn}]}
（マッハファイターは other: {tapped: false} で
アンタップ対象を広げる。フュリー・チャージは
タップ対象のみ＝既定の合法対象そのもの）。

ただし実測でエンジン側の不整合が判明した:
combat._attack_options は _can_attack（召喚酔い）
で全攻撃を門前払いするため、出たターンの
クリーチャーは allow {action: attack_creature}
を持っていても攻撃選択肢が一切出ない（登録済み
マッハファイター dm22rp1-071 を scenario で
実測: 出たターンは攻撃判断自体が提示されず、
翌ターンには modify が切れて allow は空）。
つまり現行エンジンではマッハファイターの
「出たターンの間」も機能しておらず、形だけ
書いても死に形になる。**結論: ドリフト＋最小
エンジン修正**（第410弾と同型）。修正は
combat._attack_options の1か所: 攻撃できない
理由が召喚酔いだけのクリーチャーに allow
{action: attack_creature}（辞書形）がある場合、
プレイヤー攻撃は出さず、クリーチャー攻撃の
選択肢だけを通常と同じ合法性判定（タップ対象
＋allow の other フィルタ、permits 照合、誘引・
must_attack_creature の絞り込み）で出す。
フュリー・チャージ（tapped: true）は「出た
ターンにタップしているクリーチャーだけを攻撃
できる」、マッハファイター（tapped: false）は
「出たターンにタップ／アンタップ両方を攻撃
できる（プレイヤーは不可）」と公式どおりになる。
Rust 側は st_attack がアンタップ対象の拡大自体を
持たず本機構も無い＝既存の乖離区分（第410・
426・428弾と同型）で触らない。verified_engine
のハッシュは第436弾以降 stale で Rust は自動
無効化・Python のみ動作が現行運用のため
rust_stamp は先例どおり据え置く。新規の状態
フィールドは無いため state.rs ミラー不要。
defs・スキーマ変更なし。

partial は骨格完備（text 公式全文、keywords
[double_breaker]）で abilities 未構築、
unsupported は本 gap 1件のみ。**補完あり:
abilities**（trigger 1件のみ）。alias 無し
（identity 実測で canon は対象自身）。
登録ブロッカーの確認: rule_convert.split は
keywords [double_breaker] のみ定型所有し、
フュリー・チャージ条項の text は定型化されず
残る＝ツール側ブロッカーなし。

proto T1236（dmx12b-015 型）。判別役: T001
（アンタップ・パワー2000＝出たターンは攻撃
できない）/ T008（タップ・パワー1000＝出た
ターンに攻撃でき、バトルで破壊される）/
T1234（スピードアタッカー＝従来経路の不変確認）/
dm22rp1-071（登録済みマッハファイター＝修正で
出たターンに両対象を攻撃できるようになる）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import (  # noqa: E402
    DefError, load_rules, load_tables, parse_card)
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

TRIGGER = {"kind": "trigger",
           "when": {"event": "move", "to": "bz", "subject": "self"},
           "effect": [{"op": "modify", "select": {"ref": "self"},
                       "mod": {"allow": [{"action": "attack_creature",
                                          "other": {"tapped": True}}]},
                       "duration": "end_of_turn"}]}

NAME = "Tatsurion"
TEXT = ("フュリー・チャージ：このクリーチャーは、バトルゾーンに出たターンに、"
        "タップしているクリーチャーを攻撃できる。\n"
        "W・ブレイカー（このクリーチャーはシールドを２枚ブレイクする）")
ABILITIES = [TRIGGER]
FORM = {"name": NAME, "types": ["creature"],
        "civs": ["fire"], "cost": 6, "power": 6000,
        "races": ["アーマード・ドラゴン", "ビーストフォーク"], "mana": 1,
        "keywords": ["double_breaker"],
        "text": TEXT, "abilities": ABILITIES}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1236")
    for k, v in FORM.items():
        assert c[k] == v, k
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.name == NAME
    # キーワード由来の static（keyword マーカーつき）を除いた
    # 残りが FORM の abilities と一致する
    plain = [a for a in d.abilities if "keyword" not in a]
    assert plain == FORM["abilities"]


def test_form_def_errors():
    base = {"id": "X445", **copy.deepcopy(FORM)}
    parse_card(copy.deepcopy(base), TABLES)
    # allow 項目の未知アクション
    bad = copy.deepcopy(base)
    bad["abilities"][0]["effect"][0]["mod"]["allow"][0]["action"] = \
        "attack_creatur"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # other フィルタの未知キー
    bad = copy.deepcopy(base)
    bad["abilities"][0]["effect"][0]["mod"]["allow"][0]["other"] = \
        {"tappedd": True}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # 未知の op
    bad = copy.deepcopy(base)
    bad["abilities"][0]["effect"][0]["op"] = "modifyy"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # duration の不正値
    bad = copy.deepcopy(base)
    bad["abilities"][0]["effect"][0]["duration"] = "end_of_game"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


# ---------- ドライバ ----------

def _keys(d):
    return [o.get("key") for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif d["kind"] in ("declare_strigger", "declare_sback"):
        e.answer([])
    elif d["kind"] == "pay_mana":
        e.answer([0])
    elif d["kind"] == "yes_no":
        e.answer([keys.index("no")] if "no" in keys else [0])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _drive(e, play=None, attacks=(), arrange=None, stop=None,
           limit=3000):
    """play（手札から出す対象）を1回だけ出し、attacks を順に実行する。
    攻撃判断は st["attack_options"] に (player, turn, keys) で記録する。
    stop(e, d, st) が True を返した時点で止める。"""
    st = {"played": False, "attack_options": [], "done": []}
    queue = list(attacks)
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if arrange:
            arrange(e, d)
        if d["kind"] == "attack":
            st["attack_options"].append((d.get("player"), e.s.turn, keys))
        if stop and stop(e, d, st):
            return st
        if play and not st["played"] and d["kind"] == "main" \
                and d.get("player") == 0 and f"play:{play}" in keys:
            e.answer([keys.index(f"play:{play}")])
            st["played"] = True
            continue
        if queue and d["kind"] == "attack" and queue[0] in keys:
            e.answer([keys.index(queue[0])])
            st["done"].append(queue.pop(0))
            continue
        _answer_default(e, d)
    raise AssertionError("driver limit reached")


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    # bz は共有ゾーンなのでコントローラーまで見て引く
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn
                and e.s.cards[c].controller == p)


def _tap(e, p, defn):
    e.s.cards[_cid(e, p, defn)].tapped = True


def _atk_keys(st, player, turn, attacker):
    out = []
    for p, t, keys in st["attack_options"]:
        if p == player and t == turn:
            out += [k for k in keys
                    if k and k.startswith(f"attack:{attacker}:")]
    return out


def _first_attack_stop(player, turn):
    def stop(e, d, st):
        return d["kind"] == "attack" and d.get("player") == player \
            and e.s.turn == turn
    return stop


# ---------- T1236（フュリー・チャージ） ----------

def test_fury_entry_turn_attacks_tapped_only(rules):
    """出たターン: タップした T008 だけを攻撃でき、
    アンタップの T001 とプレイヤーは攻撃できない。"""
    e = _build(rules,
               {"hand": ["T1236"], "mana": ["T1234"] * 6},
               {"bz": ["T001", "T008"]})
    _tap(e, 1, "T008")
    st = _drive(e, play="T1236", stop=_first_attack_stop(0, 1))
    assert st["played"]
    assert _atk_keys(st, 0, 1, "T1236") == ["attack:T1236:T008"]


def test_fury_entry_turn_battle_destroys_tapped(rules):
    """出たターンにタップした T008 を攻撃するとバトルで
    破壊し、T1236 は場に残る（6000 vs 1000）。"""
    e = _build(rules,
               {"hand": ["T1236"], "mana": ["T1234"] * 6},
               {"bz": ["T001", "T008"]})
    _tap(e, 1, "T008")
    t008 = _cid(e, 1, "T008")

    def stop(eng, d, st):
        return eng.s.cards[t008].zone == "graveyard"

    st = _drive(e, play="T1236", attacks=["attack:T1236:T008"],
                stop=stop)
    assert st["done"] == ["attack:T1236:T008"]
    assert e.s.cards[t008].zone == "graveyard"
    assert e.s.cards[_cid(e, 0, "T1236")].zone == "bz"


def test_fury_entry_turn_no_legal_target(rules):
    """出たターンにタップした相手クリーチャーがいなければ、
    T1236 の攻撃選択肢は一切出ない（プレイヤーも不可）。"""
    e = _build(rules,
               {"hand": ["T1236"], "mana": ["T1234"] * 6},
               {"bz": ["T001"]})

    def stop(eng, d, st):
        return d["kind"] == "charge" and d.get("player") == 1

    st = _drive(e, play="T1236", stop=stop)
    assert st["played"]
    assert _atk_keys(st, 0, 1, "T1236") == []
    assert e.s.cards[_cid(e, 0, "T1236")].zone == "bz"
    assert e.s.cards[_cid(e, 1, "T001")].zone == "bz"


def test_fury_next_turn_is_normal_creature(rules):
    """翌ターン以降は通常のクリーチャー: プレイヤーと
    タップした T008 を攻撃できるが、アンタップの T001 は
    攻撃できない（modify は切れており、対象は広がらない）。"""
    e = _build(rules,
               {"hand": ["T1236"], "mana": ["T1234"] * 6},
               {"bz": ["T001", "T008"]})

    def arrange(eng, d):
        # 相手ターン中、T008 をタップ状態に保つ
        # （タップは charge / main の判断でのみ行う＝第442弾の作法）
        if eng.s.active == 1 and d["kind"] in ("charge", "main"):
            _tap(eng, 1, "T008")

    st = _drive(e, play="T1236", arrange=arrange,
                stop=_first_attack_stop(0, 3))
    keys = _atk_keys(st, 0, 3, "T1236")
    assert "attack:T1236:player" in keys
    assert "attack:T1236:T008" in keys
    assert "attack:T1236:T001" not in keys


# ---------- エンジン修正の判別（既存形への影響） ----------

def test_mach_fighter_entry_turn_now_works(rules):
    """登録済みマッハファイター dm22rp1-071: 修正前は出た
    ターンに攻撃選択肢が一切出なかった。修正後は出た
    ターンにタップ／アンタップ両方を攻撃でき、
    プレイヤーは攻撃できない（公式どおり）。"""
    e = _build(rules,
               {"hand": ["dm22rp1-071"], "mana": ["T002"] * 3},
               {"bz": ["T001", "T008"]})
    _tap(e, 1, "T008")
    st = _drive(e, play="dm22rp1-071", stop=_first_attack_stop(0, 1))
    assert st["played"]
    keys = _atk_keys(st, 0, 1, "dm22rp1-071")
    assert "attack:dm22rp1-071:T008" in keys
    assert "attack:dm22rp1-071:T001" in keys
    assert "attack:dm22rp1-071:player" not in keys


def test_speed_attacker_entry_turn_unchanged(rules):
    """スピードアタッカー（T1234）は従来どおり出たターンに
    プレイヤーを攻撃でき、アンタップの T001 は攻撃
    できない（文字列 allow の経路は不変）。"""
    e = _build(rules,
               {"hand": ["T1234"], "mana": ["T1234"] * 4},
               {"bz": ["T001", "T008"]})
    _tap(e, 1, "T008")
    st = _drive(e, play="T1234", stop=_first_attack_stop(0, 1))
    assert st["played"]
    keys = _atk_keys(st, 0, 1, "T1234")
    assert "attack:T1234:player" in keys
    assert "attack:T1234:T008" in keys
    assert "attack:T1234:T001" not in keys
