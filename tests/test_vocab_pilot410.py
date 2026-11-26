"""語彙パイロット第410弾: force_block（ドリフト＋最小エンジン修正）。

センサス（rejects 1,922件を取り直し）: pure 1,774件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜409弾）は再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021、
battle_opponent_reference の残り1件 dmr01-049、
untap_restriction の残り2件（dm26rp1-td004 /
dmx15-011、形が異なると判定済み）、cast_limit_
once_per_turn の multi 2件（dm26ex2-pr006 /
dm26ex4-cho031、他の gaps を併せ持つ）、
summoning_attack_rule の残り1件 dmex07-s01
（partial が素で条項未構築）、entered_turn_attack の
残り1件 dmbd11-d05（J・O・E 等が未構築）は先行弾の
評価を覆す根拠が無く再提案しない。
destroyed_this_turn_condition と count_cards_drawn_
this_turn は次点のまま残す。distinct_civ_count
（dmx19-s45、3条項の複合）は後続候補のまま残す。
本弾で個別に評価して見送った候補:
saver_race_grant（pure 1、dm24ex4-020。通常の
「セイバー：種族」はキーワードとして無く（あるのは
shield_saver のみ）、破壊置換の発生源側機構から
要るため最小でない）、cannot_be_tapped_by_opponent
（pure 1、dm10-066。相手によるタップを防ぐ特性
フラグと tap 適用側の照合が無く新機構）、
first_time_tap（pure 2、dmr08-017 / dmr06-015。
tap イベント自体はあるが個体単位の通し番号（ord）が
tap には無く、ORD_KINDS への追加＋記録器の個体別
刻印＋Rust ミラーが要る。dmr06-015 は公開＋条件
分岐の複合でもある。将来の新規語彙候補として残す）、
power_threshold_keyword_gain（pure 1、dm24-011。
自分の現在パワーを条件にする static if は
static_if_own_current_power と同根で未確立）、
each_player_mana_put（pure 1、dm24bd5-040。
各プレイヤーの任意選択と「置いた相手の数」の
数え上げが未確立）、double_freeze（pure 1、
dm37-019。freeze キーワードの2体版で keywords.yaml
への新規キーワード追加が要り、choose の「2体まで」の
上限形の検証も要る）、evolution_base（pure 1、
dm32-065。破壊時に進化元だったカードを墓地から
指す参照が未確立）。
範囲内・最小の **force_block（pure 1件、multi にも
現れない）** を選定した。force_block は第369弾
センサスで「ブロック強制は別機構」、第385弾
センサスで「ブロック強制の mod が無い」として
却下されたが、本弾で実測により覆す: mod
{require: [block]}（507.1b）は語彙として存在し
（test_vocab_require.py、登録済みの自己スコープ
「可能であればブロックする」カード群）、エンジン
combat.py のブロック宣言でも強制として働く
（ブロック可能な強制クリーチャーがいれば no_block
選択肢が消える）。残る問題はエンジン側の不整合
のみで、第384弾と同型の「実挙動が暴いたエンジン
側の隙間」として本弾で最小修正する。

対象は dmr09-004 剛鉄突破 アイアンローズ（光の
クリーチャー / コスト7 / パワー6000 / 種族
アウトレイジMAX）。公式テキスト: 「バトルゾーンに
ある相手のクリーチャーはすべて「ブロッカー」を得、
可能であればブロックする。このクリーチャーの
パワーは、バトルゾーンにある相手のクリーチャー
１体につき+2000される。W・ブレイカー（…）」。
partial は骨格完備（mana 1、keywords
[double_breaker]）で text は行の公式テキスト
全文と一致するため**補完なし**。未解決は
unsupported の force_block 1件だけ（パワー条項の
static も partial には無いが、下記の確立形で
併せて組む）。alias は無し（identity 実測で
canon_id は対象自身、aliases_for = []）。第410弾
時点で real.yaml / real_akashic.yaml /
real_vocab.yaml / real_zone.yaml / proto.yaml /
converted.yaml のいずれにも登録なし。単面カードで
未検証の面は無い。登録ブロッカーの確認
（第375弾の教訓）: rule_convert.split（対象行）は
(['double_breaker'], 条項テキスト, []) を返し、
part[2] の定型所有は**空**（ツール側ブロッカー
なし。提出形には FORM の static 2件すべてを
含めること）。

結論はドリフト（新規語彙・defs・スキーマ変更
なし）＋最小エンジン修正。確立形は abilities
2件（文面の条項順）:
- 第1条項は static {affects: {zone: bz,
  owner: opp, filter: {types: [creature]}},
  mod: {grant: [blocker], require: [block]}}。
  grant [blocker] は登録先例多数、require は
  REQUIRES の既存値で、grant と require を1つの
  mod に併記する形も登録先例あり。自己スコープの
  require [block] を相手全体への付与に一般化した
  もので、フィルタに keyword を含まないため
  第398弾の base 照合の制限は及ばない（付与された
  ブロッカーにも require が掛かる）。
- 第2条項は static {affects: self, mod:
  {power: {amount: 2000, count: {zone: bz,
  owner: opp, filter: {types: [creature]}}}}}。
  第405弾の count 形そのもの。

**エンジン修正（最小）**: combat.py のブロック
宣言（phase 2）で、タップ対象が list(forced) +
[選択された1体] になっていたため、ブロック
強制されたクリーチャーが複数いると全員が
タップしてしまう（実測: 強制ブロッカー2体で
攻撃すると、ブロックした1体だけでなく他方も
タップする。選ばれた1体が forced にも含まれる
場合は tap イベントが二重に出る）。公式には
ブロックするのは選ばれた1体だけで、他の強制
クリーチャーはタップしない（507.1b の強制は
「ブロックしない」選択肢を消すことで効く）。
修正は to_tap を選択された1体（ブロッカー
またはガードマン）だけに絞る1行。Rust
engine.rs はもともと選択された1体だけをタップ
する形であり、修正後の Python と一致するため
Rust 側の変更は不要（require の強制自体は Rust
未実装という既存の乖離は本弾では触らない。
rust_stamp は第364弾以来の先例どおり据え置き、
エンジンは Python のみで動作）。挙動が変わる
登録済みカードは require [block] を持つカード
群に限られ、変わるのは「同じ攻撃をブロック
できるアンタップの強制クリーチャーが2体以上
いる場合に、選ばれなかった側もタップしていた」
のが公式どおり選ばれた1体だけになる点と、
ガードマンで攻撃先が変更された時に強制
クリーチャーがタップしていた点のみ。単独強制の
既存テスト（test_vocab_require.py）の意味論は
不変。

proto T1178（dmr09-004 型）。判別役は既存 proto
を流用: T001（攻撃役・自軍バニラ役）/ T1091
（相手バニラ役）/ T1090（相手の印刷スピード
アタッカー役）。自己スコープ強制の回帰ピンは
tests/rule_cards.yaml の R057 を使う。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の
作法）。
"""
import copy
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import (  # noqa: E402
    DefError, card_yaml_files, load_rules, load_tables, parse_card)
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()
ROOT = Path(__file__).parent.parent

FORCE_BLOCK = {"kind": "static",
               "affects": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"]}},
               "mod": {"grant": ["blocker"], "require": ["block"]}}
POWER_UP = {"kind": "static", "affects": "self",
            "mod": {"power": {"amount": 2000,
                              "count": {"zone": "bz", "owner": "opp",
                                        "filter": {"types": ["creature"]}}}}}
FORM = [FORCE_BLOCK, POWER_UP]
FULL_TEXT = ("バトルゾーンにある相手のクリーチャーはすべて「ブロッカー」を得、"
             "可能であればブロックする。このクリーチャーのパワーは、"
             "バトルゾーンにある相手のクリーチャー１体につき+2000される。"
             "W・ブレイカー（このクリーチャーはシールドを２枚ブレイクする）")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


@pytest.fixture(scope="module")
def rules_rc():
    return load_rules(card_yaml_files()
                      + [Path(__file__).parent / "rule_cards.yaml"])


def test_proto_form(rules):
    c = proto_card("T1178")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 7 and c["power"] == 6000 and c["mana"] == 1
    assert c["races"] == ["アウトレイジMAX"]
    assert c["keywords"] == ["double_breaker"]
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    for a in FORM:
        assert a in d.abilities
    for tid in ("T001", "T1090", "T1091"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX410", "name": "剛鉄突破 アイアンローズ",
                    "types": ["creature"], "civs": ["light"],
                    "cost": 7, "power": 6000, "mana": 1,
                    "races": ["アウトレイジMAX"],
                    "keywords": ["double_breaker"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    for a in FORM:
        assert a in d.abilities
    # parse 後の double_breaker 派生 static を除き2件
    assert len(d.abilities) == 3


def _bad(ability):
    with pytest.raises(DefError):
        parse_card({"id": "TX410B", "name": "x", "types": ["creature"],
                    "civs": ["light"], "cost": 7, "power": 6000,
                    "abilities": [ability]}, TABLES)


def test_bad_require_value():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"]}},
          "mod": {"require": ["fly"]}})


def test_bad_grant_keyword():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"]}},
          "mod": {"grant": ["bogus_kw"], "require": ["block"]}})


def test_bad_unknown_mod_key():
    _bad({"kind": "static",
          "affects": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"]}},
          "mod": {"bogus_mod": ["block"]}})


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, defn, p, nth=0):
    return [c for c in e.bz_tops(p) if e.cdef(c).id == defn][nth]


def _keys(d):
    return [o["key"] for o in d["options"]]


def _attack_player(e, attacker_key):
    """charge / main を pass して player 0 の攻撃宣言まで
    進め、attacker_key でプレイヤーを攻撃する。"""
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended before attack"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0:
            assert attacker_key in keys, keys
            e.answer([keys.index(attacker_key)])
            return
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("attack never happened")


def _next_block_decision(e, limit=300):
    """ブロック決定が出ればそれを返し、出なければ None
    （choose_shields は先頭を選んで進める）。"""
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return None
        if d["kind"] == "block":
            return d
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return None


def _settle_until(e, done, limit=600):
    for _ in range(limit):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return done()


def test_chars_discrimination(rules):
    """特性レベルの判別: 相手のクリーチャー（バニラ・
    印刷スピードアタッカーとも）は blocker と
    require [block] を得る。自分のクリーチャーと
    発生源自身は得ない。"""
    e = _build(rules,
               {"bz": ["T1178", "T001"]},
               {"bz": ["T1091", "T1090"]})
    src = _cid(e, "T1178", 0)
    own = _cid(e, "T001", 0)
    opp_v = _cid(e, "T1091", 1)
    opp_sa = _cid(e, "T1090", 1)
    for c in (opp_v, opp_sa):
        ch = e.chars(c)
        assert "blocker" in ch["keywords"]
        assert "block" in ch["require"]
    for c in (src, own):
        ch = e.chars(c)
        assert "blocker" not in ch["keywords"]
        assert "block" not in ch["require"]


def test_power_scales_with_opponent_creatures(rules):
    """第2条項: パワーは相手のクリーチャー1体につき
    +2000（自分のクリーチャーは数えない）。"""
    e = _build(rules, {"bz": ["T1178"]}, {})
    assert e.chars(_cid(e, "T1178", 0))["power"] == 6000
    e = _build(rules, {"bz": ["T1178"]}, {"bz": ["T1091"]})
    assert e.chars(_cid(e, "T1178", 0))["power"] == 8000
    e = _build(rules, {"bz": ["T1178", "T001"]},
               {"bz": ["T1091", "T1091"]})
    assert e.chars(_cid(e, "T1178", 0))["power"] == 10000


def _next_attack_decision(e, limit=300):
    """player 0 の次の攻撃決定（同一ターンの攻撃ステップ
    継続）まで進めて返す。タップ状態の観測は防御側の
    ターン開始アンタップより前のこの時点で行う。"""
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return None
        if d["kind"] == "attack" and d.get("player") == 0:
            return d
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return None


def test_opponent_must_block_and_only_chosen_taps(rules):
    """第1条項の実挙動＋エンジン修正の判別: 相手の
    バニラ2体は両方ともブロッカーを得て強制される
    （no_block は出ない）。ブロックするのは選ばれた
    1体だけで、選ばれなかった側はタップしない
    （修正前は強制全員がタップしていた）。攻撃役は
    パワー1000の T002 で、ブロッカー（2000）は
    バトルに勝って場に残る。"""
    e = _build(rules,
               {"bz": ["T1178", "T002", "T002"]},
               {"bz": ["T1091", "T1091"]})
    b0 = _cid(e, "T1091", 1, 0)
    b1 = _cid(e, "T1091", 1, 1)
    _attack_player(e, "attack:T002:player")
    d = _next_block_decision(e)
    assert d is not None and d["player"] == 1
    keys = _keys(d)
    assert "no_block" not in keys
    block_opts = [i for i, o in enumerate(d["options"])
                  if o.get("cid") in (b0, b1)]
    assert len(block_opts) == 2
    chosen, other = b0, b1
    e.answer([next(i for i, o in enumerate(d["options"])
                   if o.get("cid") == chosen)])
    # 同一ターンの次の攻撃決定時点で観測する
    d = _next_attack_decision(e)
    assert d is not None
    # ブロックされたのでシールドは割れていない
    assert len(e.zlist("shield", 1)) == 5
    # 選ばれた1体はタップし、選ばれなかった強制
    # クリーチャーはタップしていない
    assert e.s.cards[chosen].tapped is True
    assert other in e.bz_tops(1)
    assert e.s.cards[other].tapped is False


def test_self_scope_forced_blockers_only_chosen_taps(rules_rc):
    """エンジン修正の回帰ピン（既存語彙の経路）:
    自己スコープ require [block] の R057 が2体いても、
    タップするのは選ばれた1体だけ（test_vocab_require.py
    の単独強制の意味論は不変）。"""
    e = _build(rules_rc, {"bz": ["T002", "T002"]},
               {"bz": ["R057", "R057"]})
    b0 = _cid(e, "R057", 1, 0)
    b1 = _cid(e, "R057", 1, 1)
    _attack_player(e, "attack:T002:player")
    d = _next_block_decision(e)
    assert d is not None and d["player"] == 1
    assert "no_block" not in _keys(d)
    e.answer([next(i for i, o in enumerate(d["options"])
                   if o.get("cid") == b0)])
    d = _next_attack_decision(e)
    assert d is not None
    assert len(e.zlist("shield", 1)) == 5
    assert e.s.cards[b0].tapped is True       # 選ばれた1体はタップ
    assert e.s.cards[b1].tapped is False      # 他方はタップしない


def test_no_source_no_block(rules):
    """対照: 発生源が無ければ相手のバニラはブロック
    できず、攻撃は通ってシールドが1枚割れる。"""
    e = _build(rules, {"bz": ["T001"]}, {"bz": ["T1091", "T1091"]})
    _attack_player(e, "attack:T001:player")
    d = _next_block_decision(e)
    assert d is None
    assert _settle_until(e, lambda: len(e.zlist("shield", 1)) == 4)


def test_tapped_opponent_creature_does_not_force(rules):
    """「可能であれば」の判別: 相手のクリーチャーが
    タップ状態ならブロックできず、強制も働かない
    （攻撃は通る）。"""
    e = _build(rules,
               {"bz": ["T1178", "T001"]},
               {"bz": ["T1091"]})
    opp = _cid(e, "T1091", 1)
    e.s.cards[opp].tapped = True
    _attack_player(e, "attack:T001:player")
    d = _next_block_decision(e)
    assert d is None
    assert _settle_until(e, lambda: len(e.zlist("shield", 1)) == 4)
