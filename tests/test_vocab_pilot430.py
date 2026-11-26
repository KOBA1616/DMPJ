"""語彙パイロット第430弾: infinity_power_attacker（ドリフト）。

センサス（rejects 1,901件を取り直し）: pure 1,753件
（988家族）/ multi 130件 / 空 gaps 18件。pure の大半は
範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜429弾）は原則として再提案しない。残置群
（graveyard_replacement 残り dm25ex2-cho021、
battle_opponent_reference 残り dmr01-049、
untap_restriction 残り2件、does_not_untap 残り
dm25ex2-031、cast_limit_once_per_turn の multi 2件、
summoning_attack_rule 残り dmex07-s01、
entered_turn_attack 残り dmbd11-d05、madness 残り
dmx26-028、次点の destroyed_this_turn_condition /
count_cards_drawn_this_turn、後続候補の
distinct_civ_count、将来の新規語彙候補 first_time_tap /
turn_history_entry、turn_history_noncreature_played_
count、専用ステージ送りの power_threshold_keyword_
gain）は覆す根拠が無く再提案しない。

範囲内・最小の **infinity_power_attacker（pure 1件、
multi にも現れない）** を選定した。本候補は第428弾で
「キーワードは第272弾で確立済みだが、partial の
races [アウトレイジMAX] 代理と登録先例 dmd11-001 の
types [exile_creature] の同値性検証が前提」として
記録されたもので、本弾はその検証自体を本体とする。
検証結果（ドリフト。新規語彙・エンジン・defs・
スキーマ変更なし）:
- **代理は同値でない（実測で否定）**: 公式コーパス
  全体では種族アウトレイジMAX は 280件あるが
  エグザイル・クリーチャーは 84件しかなく、残りは
  通常のクリーチャー等。name_has: 武闘 と組み
  合わせても、熱血武闘 カツキング（dm22rp2-tr2 /
  dm22rp2x-tr2 / dmbd17-002）、武闘世代
  カツキングJr.（dmex12-s17 / dmr23-s06）、武闘親父
  カツドン（dmr23-016）、登録済み dmsp02-009
  （GS 版、公式 card_type はクリーチャー）が代理に
  一致してしまうが、いずれもエグザイルではない。
  逆方向（《武闘》名のエグザイルで MAX 種族を
  持たないもの）は存在しない。つまり代理は正しい
  集合より一方向に広く、partial 構築済みの
  ドロン・ゴー誘発と deny 静的効果5件はそのまま
  では誤り。正しい形は登録先例 dmd11-001
  暴剣王邪 ハリケーン / dmd11-005 武闘龍 カツドン
  （同じドロン・ゴー＋制限の文面）の filter
  {name_has: 武闘, types: [exile_creature]}。
- **partial の欠落2件**: (1) types に exile_creature
  が無い（公式 card_type はエグザイル・
  クリーチャー。登録済みエグザイルはすべて
  [creature, exile_creature]。型印は第266弾）。
  (2) deny 5件にチーム・エグザイル無視の if が
  無い。登録済み dm22ex1-cho22 の文面は制限一般
  への例外で、登録先例2件とも制限側に if
  {not: {exists: {zone: [hand, bz], owner: you,
  filter: {name_has: チーム・エグザイル}}}} を
  保持する（第266弾の確立した表し方）。対象の
  制限文面は同一の定型文なので同じ if が要る。
- **「自分の他の」の自己除外**: 静的効果は
  バトルゾーンの発生源からのみ働くため、5ゾーン
  側の一致カードは定義上つねに「他の」カードで、
  2枚目の同名（手札）は正しく禁止され、1枚目の
  自身の召喚は妨げられない（実挙動で確認）。
- 残りは確立形のみ: 第1条項は partial 構築済みの
  CIP 誘発 → modify {select: {ref: self}, mod:
  {allow: [{action: attack_creature, other:
  {tapped: false}}]}, duration: end_of_turn}
  （allow の形は dmd11-005 の常在型と第414弾の
  modify が先例。ターン制限の差は CIP＋duration）。
  第3条項は partial 構築済みの battle_win 誘発 →
  break {count: 1, player: opp}。unsupported は
  ∞パワーアタッカー 1件だけで、キーワード
  infinite_power_attacker（第272弾。登録済み
  3件には本カードの GS 版 dmsp02-009 を含む）の
  追加で解ける。

対象は dmr09-v02 武闘将軍 カツキング（火 /
コスト8 / パワー11000 / 種族 アウトレイジMAX /
mana 1）。partial は骨格＋条項構築済みで text は
公式全文。**補完・修正あり: types に exile_creature
追加／keywords に infinite_power_attacker 追加／
ドロン・ゴーと deny 5件の filter を races 代理から
types へ修正／deny 5件に if 追加**。alias は無し
（identity 実測で canon_id は対象自身、
aliases_for = []）。第430弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも対象 id は
登録なし。登録ブロッカーの確認（第375弾の教訓）:
rule_convert.split（対象行）は (['speed_attacker',
'double_breaker'], 条項テキスト, []) を返し、
定型所有はキーワードのみで part[2] の能力所有は
空＝二重付着ブロッカー無し。単面カードで未検証の
面は無い。

proto T1209（dmr09-v02 型）。判別役は新規
T1210（《武闘》名エグザイル）/ T1211（《武闘》名・
非エグザイル＝代理なら一致してしまう対照）と
既存 proto の T736（チーム・エグザイル）/
T763（パワー99999ブロッカー）/ T1204
（パワー13000 の対照）/ T1207（火マナ役）/
T011（自軍破壊呪文）を流用。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の
作法）。バトルゾーンは共有ゾーンなので対象カードの
cid は controller でも絞ること（第423弾の注意）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

NAME = "武闘将軍 カツキング"
EXILE_FILTER = {"name_has": "武闘", "types": ["exile_creature"]}
PROXY_FILTER = {"name_has": "武闘", "races": ["アウトレイジMAX"]}
IGNORE_IF = {"not": {"exists": {"zone": ["hand", "bz"], "owner": "you",
                                "filter": {"name_has": "チーム・エグザイル"}}}}
KEYWORDS = ["speed_attacker", "double_breaker", "infinite_power_attacker"]
FULL_TEXT = ("スピードアタッカーW・ブレイカー"
             "このクリーチャーをバトルゾーンに出した時、そのターン、"
             "このクリーチャーはタップされていないクリーチャーを"
             "攻撃できる。∞ (ルビ：インフィニティ）"
             "パワーアタッカー（攻撃中、このクリーチャーのパワーは"
             "無限大になる）このクリーチャーがバトルに勝った時、"
             "シールドを１枚ブレイクする。ドロン・ゴー："
             "このクリーチャーが破壊された時、名前に《武闘》とある"
             "エグザイル・クリーチャーを１体、自分の手札から"
             "バトルゾーンに出してもよい。自分の他の、名前に"
             "《武闘》とあるエグザイル・クリーチャーをバトルゾーンに"
             "出すことはできない。")
ZONES5 = ["hand", "graveyard", "mana", "deck", "shield"]
ABILITIES = [
    {"kind": "trigger",
     "when": {"event": "move", "to": "bz", "subject": "self"},
     "effect": [{"op": "modify", "select": {"ref": "self"},
                 "mod": {"allow": [{"action": "attack_creature",
                                    "other": {"tapped": False}}]},
                 "duration": "end_of_turn"}]},
    {"kind": "trigger",
     "when": {"event": "battle_win", "subject": "self"},
     "effect": [{"op": "break", "count": 1, "player": "opp"}]},
    {"kind": "trigger",
     "when": {"event": "move", "from": "bz", "to": "graveyard",
              "reason": "destroy", "subject": "self"},
     "effect": [{"op": "may", "body": [
         {"op": "move",
          "select": {"zone": "hand", "owner": "you",
                     "filter": copy.deepcopy(EXILE_FILTER), "count": 1},
          "to": "bz", "reason": "put"}]}]},
] + [
    {"kind": "static",
     "affects": {"zone": z, "owner": "you",
                 "filter": copy.deepcopy(EXILE_FILTER)},
     "if": copy.deepcopy(IGNORE_IF),
     "mod": {"deny": ["enter_bz"]}}
    for z in ZONES5
]
FORM = {"name": NAME, "types": ["creature", "exile_creature"],
        "civs": ["fire"], "cost": 8, "power": 11000,
        "races": ["アウトレイジMAX"], "mana": 1,
        "keywords": list(KEYWORDS), "text": FULL_TEXT,
        "abilities": ABILITIES}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _check_form(c):
    for k, v in FORM.items():
        assert c[k] == v, k
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.types == ["creature", "exile_creature"]
    assert d.keywords == KEYWORDS
    kw = [ab for ab in d.abilities if ab.get("keyword")]
    assert {"kind": "static", "affects": "self",
            "mod": {"power_when": {"amount": 1073741824,
                                   "when": "attacking"}},
            "keyword": "infinite_power_attacker"} in kw
    assert {"kind": "static", "affects": "self",
            "mod": {"breaks": 2}, "keyword": "double_breaker"} in kw
    trigs = [ab for ab in d.abilities if ab["kind"] == "trigger"]
    assert len(trigs) == 3
    dg = [ab for ab in trigs
          if ab["when"].get("reason") == "destroy"][0]
    mv = dg["effect"][0]["body"][0]
    assert mv["op"] == "move" and mv["to"] == "bz"
    assert mv["select"]["filter"] == EXILE_FILTER
    statics = [ab for ab in d.abilities
               if ab["kind"] == "static" and not ab.get("keyword")]
    assert len(statics) == 5
    assert sorted(ab["affects"]["zone"] for ab in statics) == \
        sorted(ZONES5)
    for ab in statics:
        assert ab["affects"]["filter"] == EXILE_FILTER
        assert ab["if"] == IGNORE_IF
        assert ab["mod"] == {"deny": ["enter_bz"]}


def test_proto_form(rules):
    c = proto_card("T1209")
    _check_form(c)
    for tid in ("T1210", "T1211", "T736", "T763", "T1204", "T011"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    _check_form({"id": "dmr09-v02", **copy.deepcopy(FORM)})


def _bad(mutate):
    c = {"id": "TX430B", "name": "x",
         "types": ["creature", "exile_creature"], "civs": ["fire"],
         "cost": 8, "power": 11000, "mana": 1,
         "keywords": list(KEYWORDS),
         "abilities": copy.deepcopy(ABILITIES)}
    mutate(c)
    with pytest.raises(DefError):
        parse_card(c, TABLES)


def test_bad_forms_rejected():
    # 未知のキーワード
    _bad(lambda c: c.update(
        {"keywords": KEYWORDS + ["infinite_power_attackerx"]}))
    # ドロン・ゴーの select filter の未知キー
    _bad(lambda c: c["abilities"][2]["effect"][0]["body"][0]
         ["select"].update({"filter": {"name_has": "武闘", "bogus": 1}}))
    # deny 静的効果の未知ゾーン
    _bad(lambda c: c["abilities"][3].update(
        {"affects": {"zone": "handd", "owner": "you",
                     "filter": copy.deepcopy(EXILE_FILTER)}}))
    # 未知の誘発イベント
    _bad(lambda c: c["abilities"][1].update(
        {"when": {"event": "battle_winn", "subject": "self"}}))


# ---------- 駆動ヘルパ ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    return sorted(e.s.cards[c].defn for c in e.zlist(zone, p))


def _cid(e, p, defn):
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif d["kind"] == "pay_mana":
        e.answer([0])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _play_once(defn, seen):
    def play(e, d):
        keys = _keys(d)
        if f"play:{defn}" in keys and seen["n"] < 1:
            seen["n"] += 1
            return [keys.index(f"play:{defn}")]
        return None
    return play


# ---------- フィルタ判別（代理が同値でないことの実測） ----------

def test_filter_discrimination(rules):
    """T1210（《武闘》名エグザイル）は types フィルタに一致し、
    T1211（《武闘》名・非エグザイル）は一致しない。ところが
    partial の代理フィルタ {races: [アウトレイジMAX]} には
    両方とも一致する＝代理は正しい集合より広い（実測）。"""
    e = _build(rules, {"bz": ["T1210", "T1211"]}, {"bz": []})
    c_exile = _cid(e, 0, "T1210")
    c_plain = _cid(e, 0, "T1211")
    assert e.filter_match(c_exile, copy.deepcopy(EXILE_FILTER))
    assert not e.filter_match(c_plain, copy.deepcopy(EXILE_FILTER))
    assert e.filter_match(c_exile, copy.deepcopy(PROXY_FILTER))
    assert e.filter_match(c_plain, copy.deepcopy(PROXY_FILTER))


# ---------- ∞パワーアタッカー＋バトル勝利ブレイク ----------

def _battle_vs_99999(rules, attacker):
    """attacker でプレイヤーを攻撃し、T763 にブロックさせる。"""
    e = _build(rules, {"bz": [attacker]}, {"bz": ["T763"]})
    st = {"attacked": False}
    for _ in range(800):
        if st["attacked"] and len(e.zlist("shield", 1)) < 5:
            break
        if attacker in _defns(e, "graveyard", 0):
            break
        if "T763" in _defns(e, "graveyard", 1):
            break
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if d["kind"] == "attack" and not st["attacked"] \
                and f"attack:{attacker}:player" in keys:
            e.answer([keys.index(f"attack:{attacker}:player")])
            st["attacked"] = True
            continue
        if d["kind"] == "block":
            hit = [i for i, k in enumerate(keys)
                   if k.startswith("bz:T763")]
            if hit:
                e.answer([hit[0]])
                continue
        _answer_default(e, d)
    return e, st


def test_infinite_power_beats_99999_and_breaks(rules):
    """パワー99999 のブロッカーにブロックされても ∞ のため
    バトルに勝ち（T763 は破壊され、T1209 は残る）、
    バトル勝利誘発でシールドを1枚ブレイクする。"""
    e, st = _battle_vs_99999(rules, "T1209")
    # バトル勝利誘発のブレイクまで進める
    for _ in range(200):
        if len(e.zlist("shield", 1)) == 4:
            break
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        _answer_default(e, d)
    assert st["attacked"]
    assert "T763" in _defns(e, "graveyard", 1)
    assert "T1209" in _defns(e, "bz", 0)
    assert len(e.zlist("shield", 1)) == 4


def test_control_13000_loses_to_99999(rules):
    """対照: ∞ でないパワー13000（T1204）は 99999 に
    ブロックされるとバトルに負けて破壊され、
    シールドは減らない。"""
    e, st = _battle_vs_99999(rules, "T1204")
    assert st["attacked"]
    assert "T1204" in _defns(e, "graveyard", 0)
    assert "T763" in _defns(e, "bz", 1)
    assert len(e.zlist("shield", 1)) == 5


# ---------- 第1条項: 出たターンだけアンタップを攻撃できる ----------

def test_attack_untapped_only_on_entry_turn(rules):
    """召喚したターン: アンタップ状態の相手クリーチャー
    （T1211）への攻撃が選択肢に出る。次の自分のターン:
    出ない（プレイヤーへの攻撃は出る）。"""
    e = _build(rules, {"hand": ["T1209"], "mana": ["T1207"] * 8},
               {"bz": ["T1211"]})
    seen = {"n": 0, "steps": []}
    play = _play_once("T1209", seen)
    for _ in range(1200):
        if len(seen["steps"]) >= 2:
            break
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if d["kind"] == "main":
            ans = play(e, d)
            if ans is not None:
                e.answer(ans)
                continue
        if d["kind"] == "attack" and d.get("player") == 0 \
                and "attack:T1209:player" in keys:
            seen["steps"].append(list(keys))
            e.answer([keys.index("pass")])
            continue
        _answer_default(e, d)
    assert seen["n"] == 1
    assert len(seen["steps"]) == 2
    first, second = seen["steps"]
    assert "attack:T1209:T1211" in first       # 出たターン: 可
    assert "attack:T1209:T1211" not in second  # 次のターン: 不可
    assert "attack:T1209:player" in second


# ---------- ドロン・ゴー ----------

def _destroy_own_then_doron(rules, hand):
    """T011 で自軍の T1209 を破壊し、ドロン・ゴーを解決する。"""
    e = _build(rules, {"bz": ["T1209"], "hand": hand,
                       "mana": ["T1207"] * 2}, {"bz": []})
    seen = {"n": 0, "may": False, "doron_opts": None, "post": 0}
    play = _play_once("T011", seen)
    for _ in range(800):
        if "T1209" in _defns(e, "graveyard", 0):
            seen["post"] += 1
            # may に答えた後は数手で解決が完了する（候補が
            # 1枚だけなら選択は自動、無ければ何も出ない）
            if seen["may"] and seen["post"] > 3:
                break
            if seen["post"] > 40:
                break
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if d["kind"] == "main":
            ans = play(e, d)
            if ans is not None:
                e.answer(ans)
                continue
        if d["kind"] == "choose_cards":
            defns = [e.s.cards[o["cid"]].defn for o in d["options"]]
            if "T1209" in defns and "T1209" in _defns(e, "bz", 0):
                e.answer([defns.index("T1209")])  # T011 の破壊対象
                continue
            if defns:
                seen["doron_opts"] = defns       # ドロン・ゴーの候補
                if "T1210" in defns:
                    e.answer([defns.index("T1210")])
                    continue
            e.answer(list(range(d.get("min", 0))))
            continue
        if d["kind"] == "yes_no":
            seen["may"] = True
            e.answer([0])  # may は「はい」
            continue
        _answer_default(e, d)
    return e, seen


def test_doron_go_chooses_only_exile(rules):
    """破壊された時、手札の《武闘》名エグザイル（T1210）
    だけが候補になり、非エグザイルの T1211 は候補に
    出ない（代理フィルタでは T1211 も出てしまう）。
    候補を2枚にして選択決定を提示させ、候補集合その
    ものを実測する（候補1枚だと選択は自動解決される）。"""
    e, seen = _destroy_own_then_doron(
        rules, ["T1210", "T1210", "T1211", "T011"])
    assert seen["n"] == 1 and seen["may"]
    assert seen["doron_opts"] == ["T1210", "T1210"]
    assert "T1210" in _defns(e, "bz", 0)
    assert "T1211" in _defns(e, "hand", 0)
    assert "T1209" in _defns(e, "graveyard", 0)


def test_doron_go_no_exile_in_hand(rules):
    """手札に《武闘》名エグザイルが無ければ（T1211 のみ）、
    ドロン・ゴーでは何も出ない。"""
    e, seen = _destroy_own_then_doron(rules, ["T1211", "T011"])
    assert seen["n"] == 1
    assert "T1211" in _defns(e, "hand", 0)
    assert "T1211" not in _defns(e, "bz", 0)
    assert _defns(e, "bz", 0) == []


# ---------- 出場制限（deny enter_bz） ----------

def _play_keys(e, p=0):
    return [o["key"] for o in e._play_options(p)]


def test_restriction_discrimination(rules):
    """T1209 が場にいる間、《武闘》名エグザイル（T1210）は
    召喚できないが、非エグザイルの T1211 は召喚できる
    （代理フィルタでは T1211 も誤って禁止される）。
    2枚目の T1209 自身も「他の」にあたるため出せない。"""
    e = _build(rules, {"bz": ["T1209"], "hand": ["T1210", "T1211"],
                       "mana": ["T1207"] * 8}, {"bz": []})
    keys = _play_keys(e)
    assert "play:T1210" not in keys
    assert "play:T1211" in keys
    e2 = _build(rules, {"bz": ["T1209"], "hand": ["T1209"],
                        "mana": ["T1207"] * 8}, {"bz": []})
    assert "play:T1209" not in _play_keys(e2)


def test_restriction_lifted_by_team_exile_and_absent_source(rules):
    """チーム・エグザイル（T736）が手札にあれば制限は
    働かない。発生源が場に無ければ当然に制限は無い
    （1枚目の召喚は妨げられない）。"""
    e = _build(rules, {"bz": ["T1209"], "hand": ["T1210", "T736"],
                       "mana": ["T1207"] * 8}, {"bz": []})
    assert "play:T1210" in _play_keys(e)
    e2 = _build(rules, {"hand": ["T1210"], "mana": ["T1207"] * 8},
                {"bz": []})
    assert "play:T1210" in _play_keys(e2)
