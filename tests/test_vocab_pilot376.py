"""語彙パイロット第376弾: mana_all_civs（ドリフト）。

センサス（rejects 1,957件を取り直し）: pure 1,809件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜375弾）は再提案しない。本弾で個別に
評価して見送った候補: after_attack_destroy（pure 2。
代替コスト＋条件つき強制攻撃＋スター進化が同居し最小
でない）、deny_be_chosen_by_opponent_spell_effect
（pure 1、dmr17-002。partial が空で win_all_battles の
全体付与条項も未組立て、呪文限定の be_chosen 否定も
要る）、fortified_shield_unbreakable（pure 1。城の
要塞化シールドへの条件つきブレイク不可で城機構側の
追跡が要る）、next_breaker（pure 1。ブレイク置換で
シールド束を表向きにする新機構が要る）、
breaks_count_effect（pure 1。ブレイクしたシールド数の
追跡と参照が要る）、attack_trigger_grant（pure 1。
ターン全体への攻撃誘発付与が要る）、
shield_added_condition（pure 1。そのターンに手札に
加えられたシールド数の履歴条件が要る）、
first_attack_reaction_battle（pure 1。反応バトルの
新機構が要る）、g_strike_effect（pure 1。G・ストライク
使用時効果の呪文側解決＋マナ枚数参照が残る）、
martial_touch（pure 1。g 能力の参照機構が要る）、
silent_skill（pure 1。アンタップ置換＋光臨の複合）、
continuous_untap_lock（pure 2。選んだ1体への発生源
存続中アンタップ否定で、選択対象への常在付与が要る）、
next_spell_cost_reduction（pure 3。「次に唱える呪文」
のワンショット軽減の保留機構が無く新語彙が要る）、
no_return_to_hand（pure 1。D2フィールドで却下済みの
フィールド系）、cannot_remove_seal（pure 1。封印
機構そのもの）、grant_all_civilizations /
all_civilizations_mana（各 pure 1。add_civs の絞り
込み自体は届くが、種族フィルタつき常在＋未組立ての
第3条項やツインパクト面が残り本弾の最小ではない）、
civ_treatment（pure 1、dmrp08-028。マナのツインパクト
だけを対象にする affects フィルタの確立形が無く、
本弾の対象より絞り込みが重い）。範囲内・未評価で
最小の mana_all_civs（pure 1件、multi にも現れない）
を選定した。

対象は pure 1件すべて: dmex14-010 暴歌の妖精
（自然 / コスト3 / パワー3000 / 種族 スノーフェアリー・
暴拳王国）。partial は stub（骨格のみで abilities 無し、
text は第1条項の断片）で、未解決は unsupported の
mana_all_civs 1件だけ。単面カードで未検証の面は無い。
条項はすべて確立済みの部品で表せる（追加語彙なし）:

- 「自分のマナゾーンにあるカードを、すべての文明の
  カードとして扱う」は第123弾の確立形そのもの:
  static {affects: {zone: mana, owner: you},
  mod: {add_civs: [light, water, darkness, fire,
  nature]}}。登録先例 dmex01-014（同文）・dmrp20-046・
  dm25rp3-021。第260弾の常在キー mana_all_civs は
  「すべての文明を持つかのようにタップする」専用で
  支払い計算にしか効かず、本カードの「カードとして
  扱う」（文明の数え上げ等にも効く）とは意味が違う
  ため使わない（add_civs は特性に効く。第123弾で
  支払い判定が特性を見るよう拡張済み）。
- 「レインボーナス：このクリーチャーがバトルゾーンに
  出た時、バトルゾーンに自分の多色クリーチャーが
  あれば、自分の山札の上から１枚目をマナゾーンに
  置く」は第206弾のイディオム（レインボーナス＝
  {exists: {zone: bz, owner: you, filter:
  {types: [creature], multicolor: true}}} の条件）。
  CIP 誘発の if に置く形は登録先例 dmex14-083 と同形、
  山札の上からマナへ置く move は登録先例多数
  （dmrp08-028 の partial 組立て形と同形）:
  move {select: {zone: deck, owner: you, from_top: 1},
  to: mana, reason: put}。このクリーチャー自身は
  単色（自然）なので自分では条件を満たさない。

確立形: abilities = [static（add_civs）, CIP 誘発] の
2件（公式テキストの条項順）。提出形は partial の骨格に
この2能力を足し、unsupported を外したもの。**補完
あり: partial の text は第1条項の断片だけのため、
提出形では text に行の公式テキスト全文を入れる**
（ラウンド403・406の作法）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し、定型所有は無いことを
本弾で実測済み。ラウンド411は通常どおり submit
できる見込み。

proto T1124（dmex14-010 型）。判別役は既存 proto を
流用: T030（光水の多色クリーチャー）/ T001（自然の
素クリーチャー＝マナ役・単色対照）/ T277（火・コスト2
＝支払い判別役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接包む
（第319弾以降の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()
ALL_CIVS = ["light", "water", "darkness", "fire", "nature"]

STATIC = {"kind": "static", "affects": {"zone": "mana", "owner": "you"},
          "mod": {"add_civs": ALL_CIVS}}
CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "if": {"exists": {"zone": "bz", "owner": "you",
                         "filter": {"types": ["creature"],
                                    "multicolor": True}}},
       "effect": [{"op": "move",
                   "select": {"zone": "deck", "owner": "you",
                              "from_top": 1},
                   "to": "mana", "reason": "put"}]}
FORM = [STATIC, CIP]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _build(rules, p0, p1=None):
    return scenario.build(rules, {"p0": p0, "p1": p1 or {},
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _find(e, zone, player, defn):
    for i, c in enumerate(e.s.cards):
        if c.defn == defn and c.zone == zone and c.owner == player:
            return i
    raise AssertionError(f"{defn} not in {zone} of p{player}")


def test_proto_form(rules):
    d = parse_card(proto_card("T1124"), TABLES)
    assert d.abilities == FORM
    assert d.types == ["creature"] and d.civs == ["nature"]
    assert d.cost == 3 and d.power == 3000
    assert d.races == ["スノーフェアリー", "暴拳王国"]


def test_chars_mana_counts_as_all_civilizations(rules):
    """特性レベル: 発生源がバトルゾーンにあれば、自分の
    マナゾーンの自然カードはすべての文明を持つ。"""
    e = _build(rules, {"bz": ["T1124"], "mana": ["T001"]})
    ch = e.chars(_find(e, "mana", 0, "T001"))
    assert set(ch["civs"]) == set(ALL_CIVS)


def test_chars_mana_single_civ_without_source(rules):
    """対照: 発生源が無ければマナの自然カードは自然のまま。"""
    e = _build(rules, {"mana": ["T001"]})
    ch = e.chars(_find(e, "mana", 0, "T001"))
    assert set(ch["civs"]) == {"nature"}


def test_payment_with_all_civs_mana(rules):
    """実挙動: 発生源がいれば、自然マナだけで火コスト
    （文明: 火）の支払いができる（第123弾の判別と同型）。"""
    e = _build(rules, {"bz": ["T1124"], "hand": ["T277"],
                       "mana": ["T001", "T001"]})
    cid = _find(e, "hand", 0, "T277")
    assert e._mana_choices(cid, 0) != []


def test_payment_without_source_cannot_pay_fire(rules):
    """対照: 発生源が無ければ自然マナでは火の文明を
    満たせず、支払い候補は無い。"""
    e = _build(rules, {"hand": ["T277"], "mana": ["T001", "T001"]})
    cid = _find(e, "hand", 0, "T277")
    assert e._mana_choices(cid, 0) == []


# ---------- CIP（レインボーナス）の実挙動 ----------

def _drive(e, on_decision, limit=600):
    for _ in range(limit):
        if e.s.result is not None:
            return "result"
        d = e.advance()
        if d is None:
            return "done"
        r = on_decision(e, d)
        if r == "stop":
            return "stopped"
        if r == "ok":
            continue
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge" and "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("driver limit reached")


def _summon_t1124(rules, bz=()):
    """T1124 を手札から召喚し、解決後の観測点（次の
    チャージ決定）まで進める。戻り値: (engine, 召喚時点の
    山札リスト)。"""
    e = scenario.build(rules,
                       {"p0": {"hand": ["T1124"], "mana": ["T001"] * 3,
                               "deck": ["T827", "T003", "T339", "T827"],
                               "bz": list(bz)},
                        "p1": {"deck": ["T827"] * 3},
                        "filler": "T002", "seed": 1, "deck_size": 20,
                        "deck_exact": [True, True]})
    snap = []
    played = []

    def on_dec(e, d):
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and "play:T1124" in keys:
            played.append(True)
            snap.append(list(e.s.zones["deck"][0]))
            e.answer([keys.index("play:T1124")])
            return "ok"
        if played and d["kind"] == "pay_mana":
            e.answer([0])
            return "ok"
        if played and d["kind"] == "charge":
            return "stop"                  # 解決済みの観測点
        return None

    _drive(e, on_dec)
    assert played, "T1124 was not played"
    return e, snap[0]


def test_cip_puts_deck_top_to_mana_with_multicolor(rules):
    """多色クリーチャー（T030）が自分のバトルゾーンに
    あれば、出た時に山札の上から１枚目がマナゾーンに
    置かれる。"""
    e, deck0 = _summon_t1124(rules, bz=["T030"])
    top = deck0[0]
    assert e.s.cards[top].zone == "mana"
    assert len(e.s.zones["mana"][0]) == 4        # 支払い3枚＋置かれた1枚
    assert list(e.s.zones["deck"][0]) == deck0[1:]


def test_cip_no_mana_put_without_multicolor(rules):
    """多色クリーチャーが無ければ（自身は単色）条件が
    外れ、山札はそのままでマナも増えない。"""
    e, deck0 = _summon_t1124(rules)
    assert list(e.s.zones["deck"][0]) == deck0
    assert len(e.s.zones["mana"][0]) == 3
