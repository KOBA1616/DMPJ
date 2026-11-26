"""語彙パイロット第384弾: creatures_enter_tapped
（ドリフト: 第339弾 grant [enters_tapped] の一般化）。

センサス（rejects 1,949件を取り直し）: pure 1,801件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜383弾）は再提案しない。本弾で個別に
評価して見送った候補: enters_tapped_rule（pure 1、
dmex11-005。第383弾の評価どおり partial が stub で
自軍コスト3以下への speed_attacker 付与条項も未構築）、
battle_indestructible（pure 1、dmd27-012。text が空で
partial が無く評価不能。第383弾と同じ）、
fixed_breaks_plus_one（pure 1、dmrp07-052。同上）、
destroy_after_battle（pure 1、dm07-003。「このターンに
バトルした自分の闇クリーチャーはバトルの後、勝っても
墓地に置かれる」は、バトルしたクリーチャーの動的集合への
バトル後破壊の付与で、追跡＋付与の確立形が無い）、
blocker_dies_after_battle_even_if_wins（pure 1、
dm01-028。ブロックした相手クリーチャーへの勝敗の
付け替えで確立形が無い）、
battle_does_not_occur_when_blocking（pure 1、dm06-072。
ブロック時のバトル自体の取消しで確立形が無い）、
first_attack_reaction_battle（pure 1、dm24ex3-rp4s10。
「各ターンはじめて攻撃された時」の反応バトルで、
初回追跡＋強制バトルの複合）。
範囲内・最小の **creatures_enter_tapped（pure 1件、
multi にも現れない）** を選定した。第383弾で「dmex19-m20
の static {grant: [enters_tapped]} 先例はあるが owner: opp
＋if 条件つきの形で、本カードは両プレイヤー対象＋進化
フィルタの affects の実挙動検証が要る。次点として残す」
とされた候補であり、本弾では指示どおり実挙動で検証して
選定した。

対象は pure 1件すべて: dm06-001 銀界の守護者
ル・ギラ・レシール（クリーチャー / 光 / コスト5 /
パワー4000 / ガーディアン）。公式テキスト:
「ブロッカー(相手クリーチャーが攻撃するとき、この
クリーチャーをタップして、その攻撃を阻止してよい。
その後、その相手クリーチャーとバトルする)
このクリーチャーがバトルゾーンにある間、進化
クリーチャーはタップされた状態でバトルゾーンに出る。
このクリーチャーは、相手プレイヤーを攻撃できない。」

結論は語彙としてはドリフト（新規語彙・defs・スキーマ
変更なし）だが、実挙動検証でエンジン側の意味論ギャップが
判明し、最小のエンジン修正を併せて行った:
- 「進化クリーチャーはタップされた状態でバトルゾーンに
  出る」は第339弾で確立した **static {affects:
  {zone: bz, owner: opp}, mod: {grant: [enters_tapped]}}**
  （登録先例 dmex19-m20 卍 デ・スザーク 卍／「非道」の鬼
  ゴウケン齋型）の一般化で表す。本カードは両プレイヤーの
  進化クリーチャーが対象のため owner: any とし、進化
  クリーチャーだけが対象のため filter {types:
  [evolution]} を足す。確立形は **static {affects:
  {zone: bz, owner: any, filter: {types: [evolution]}},
  mod: {grant: [enters_tapped]}}**。
- エンジン修正: 進化の重ね処理（events._stack）は
  進化元のタップ状態を top に代入しており、移動適用の
  時点で付いていた入場タップ（enters_tapped の
  キーワード／付与、「タップして置く」指定）をアンタップ
  状態の進化元の位相で上書きして消していた。位相は
  「進化元の状態の引き継ぎ」であると同時に「次に出る
  クリーチャーの出され方」でもある（タップインが
  置換効果でアンタップインに変わりうるという公式の
  引き継ぎ整理）ため、_stack の引き継ぎを or 合成に
  変更した（片方でもタップならタップ。進化V等の複数
  進化元の more 側は従来どおり or 合成）。Rust
  engine.rs の stack にも同変更のミラーを入れた
  （ソース同期のみ。cargo 無しのため rust_stamp は
  第364・382弾の先例どおり据え置き＝Python のみ動作）。
  登録済みで影響を受けるのは自身が enters_tapped を
  持つ進化クリーチャー dmex01-032 の1件だけで、その
  キーワードどおりタップして出るようになる（従来は
  アンタップの進化元では素通りしていた）。
- owner: any は selector の汎用検証（you/opp/any）で
  許され、_subject_match も any を明示的に両者一致として
  扱う（第408弾の教訓で schema.py 側も確認: grant の
  items は keywords 列挙で enters_tapped を含み、selector
  の owner も any を含む。スキーマ再生成不要・Rust
  ミラー不要・rust_stamp への影響なし）。
- 入るカードの chars に enters_tapped が含まれ、
  events の移動適用（to: bz）でタップして置かれる
  （第339弾と同機構）。発生源自身は進化クリーチャーでは
  ないため自分はタップしない。
- partial は組立て済み: 骨格（クリーチャー / 光 /
  コスト5 / パワー4000 / ガーディアン、mana 1、
  keywords [blocker, cannot_attack_player]）と
  unsupported の creatures_enter_tapped 1件だけ。
  text は行の公式テキスト全文と一致するため補完なし。
  alias は無い。単面カードで未検証の面は無い。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['blocker', 'cannot_attack_player'],
残りテキスト, []) を返し、keywords は定型所有だが
partial の keywords と同一で、能力の定型所有は無い
（part[2] は空）。提出形の static は定型と重ならない
ため二重付きは起きない。

proto T1144（dm06-001 型）/ T1145（進化ガーディアン役）/
T1146（非進化ガーディアン役。進化元兼対照）/
T1147（自身が enters_tapped を持つ進化役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の作法）。
バトルゾーンは共有ゾーンなので所有は zlist(zone, p) で見る。
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
                      "filter": {"types": ["evolution"]}},
          "mod": {"grant": ["enters_tapped"]}}
FORM = [STATIC]
FULL_TEXT = ("ブロッカー(相手クリーチャーが攻撃するとき、このクリーチャーを"
             "タップして、その攻撃を阻止してよい。その後、その相手"
             "クリーチャーとバトルする)\n"
             "このクリーチャーがバトルゾーンにある間、進化クリーチャーは"
             "タップされた状態でバトルゾーンに出る。\n"
             "このクリーチャーは、相手プレイヤーを攻撃できない。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1144")
    assert c["name"] == "銀界の守護者ル・ギラ・レシール"
    assert c["types"] == ["creature"]
    assert c["civs"] == ["light"]
    assert c["cost"] == 5 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ガーディアン"]
    assert c["keywords"] == ["blocker", "cannot_attack_player"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(c, TABLES)
    # keywords は常在型に展開され、確立形 static も含まれる
    assert STATIC in d.abilities
    assert len(d.abilities) == 3


def test_bad_grant_keyword_rejected(rules):
    # grant の未知キーワードは DefError（defs の検証）
    bad = copy.deepcopy(proto_card("T1144"))
    bad["abilities"] = [{"kind": "static",
                         "affects": {"zone": "bz", "owner": "any",
                                     "filter": {"types": ["evolution"]}},
                         "mod": {"grant": ["bogus_kw"]}}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _zone_card(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p)
                if e.s.cards[c].defn == defn)


def _play(e, player, play_key, pick=None, limit=600):
    """player の main で play_key を使い、対象カードが
    バトルゾーンに出るまで進める汎用ドライバ
    （第339・372弾と同形）。"""
    defn = play_key.split(":", 1)[1]
    for _ in range(limit):
        if any(e.s.cards[c].defn == defn
               for c in e.zlist("bz", player)):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == player \
                and play_key in keys:
            e.answer([keys.index(play_key)])
            continue
        if pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("play never happened")


def test_opponent_evolution_enters_tapped(rules):
    """実挙動: 相手の進化クリーチャー（T1145）が
    T1144 のいる場に出るとタップして出る
    （owner: any の相手側）。"""
    e = _build(rules, {"bz": ["T1144"]},
               {"bz": ["T1146"], "hand": ["T1145"],
                "mana": ["T1146", "T001", "T001"]})
    _play(e, 1, "play:T1145", pick="T1146")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1145")].tapped is True


def test_own_evolution_enters_tapped(rules):
    """実挙動: 自分の進化クリーチャー（T1145）も
    タップして出る（owner: any の自分側。owner: opp の
    先例形では届かない側の判別）。"""
    e = _build(rules, {"bz": ["T1144", "T1146"], "hand": ["T1145"],
                       "mana": ["T1146", "T001", "T001"]},
               {})
    _play(e, 0, "play:T1145", pick="T1146")
    assert e.s.cards[_zone_card(e, "bz", 0, "T1145")].tapped is True


def test_non_evolution_enters_untapped(rules):
    """判別: 進化ではないクリーチャー（T1146）は
    フィルタで外れ、タップせずに出る。"""
    e = _build(rules, {"bz": ["T1144"]},
               {"hand": ["T1146"],
                "mana": ["T1146", "T001", "T001"]})
    _play(e, 1, "play:T1146")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1146")].tapped is False


def test_no_source_evolution_enters_untapped(rules):
    """判別: 発生源（T1144）がいなければ進化
    クリーチャーもタップせずに出る（常在型の発生源が
    バトルゾーンにいる間だけ働く）。"""
    e = _build(rules, {},
               {"bz": ["T1146"], "hand": ["T1145"],
                "mana": ["T1146", "T001", "T001"]})
    _play(e, 1, "play:T1145", pick="T1146")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1145")].tapped is False


def test_own_keyword_evolution_enters_tapped(rules):
    """実挙動（第384弾のエンジン修正の判別）: 自身が
    enters_tapped キーワードを持つ進化クリーチャー
    （T1147、登録済みでは dmex01-032 と同型）は、
    アンタップ状態の進化元に進化してもタップして出る。
    修正前は _stack が進化元の位相で上書きし、入場
    タップが消えていた。"""
    e = _build(rules, {"bz": ["T1146"], "hand": ["T1147"],
                       "mana": ["T1146", "T001", "T001"]},
               {})
    _play(e, 0, "play:T1147", pick="T1146")
    assert e.s.cards[_zone_card(e, "bz", 0, "T1147")].tapped is True


def test_tapped_base_inherited_without_source(rules):
    """判別（引き継ぎの温存）: 発生源が無くても、
    タップ状態の進化元から進化すればタップを引き継ぐ
    （801.2。第384弾の修正は or 合成なので引き継ぎは
    そのまま残る）。"""
    e = _build(rules, {},
               {"bz": ["T1146"], "hand": ["T1145"],
                "mana": ["T1146", "T001", "T001"]})
    # p1 の main に着いたところで進化元をタップ状態にする
    # （ターン開始のアンタップで戻らないよう main 以後に置く。
    # test_mechanics の進化テストと同作法）
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] == "main" and d.get("player") == 1:
            base = _zone_card(e, "bz", 1, "T1146")
            e.s.cards[base].tapped = True
            break
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    _play(e, 1, "play:T1145", pick="T1146")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1145")].tapped is True
