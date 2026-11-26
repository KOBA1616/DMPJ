"""語彙パイロット第383弾: variable_breaks_by_count
（ドリフト: 第130弾の breaks {count} の別名）。

センサス（rejects 1,950件を取り直し）: pure 1,802件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜382弾）は再提案しない。本弾で個別に
評価して見送った候補: battle_indestructible（pure 1、
dmd27-012。text が空で partial が無く評価不能）、
fixed_breaks_plus_one（pure 1、dmrp07-052。同上）、
creatures_enter_tapped（pure 1、dm06-001。dmex19-m20 の
static grant [enters_tapped] 先例はあるが owner: opp＋
if 条件つきの形で、本カードは両プレイヤー対象＋進化
フィルタの affects の検証が要る。次点として残す）、
enters_tapped_rule（pure 1、dmex11-005。partial が
stub で自軍コスト3以下への speed_attacker 付与条項も
未構築）、first_battle_win（pure 1、dm26sd1-g004。
「各ターン、はじめてバトルするクリーチャーはその
バトルに勝つ」は最初のバトルの追跡＋勝敗の付け替えが
要り、タップして出る条項・革命チェンジと複合）、
first_won_battle（pure 1、dm30-055。「そのクリーチャー
がはじめて勝った時」はクリーチャー単位の初勝利の追跡が
要る。第382弾の turn_count battle_win はプレイヤー
単位の数え上げで代用できない）、battle_win_destroy
（pure 1、dmr11-051。partial が stub で G・ゼロ等の
他条項が未構築のため本 gap 単独では登録形が定まらない）、
indestructible_while_blocking（pure 1、dmrp22-029。
partial のタマシード条件 static が壊れた形で、
ブロック中の破壊不能は battle_indestructible への
when: blocking 条件の検証が要る）、
blocking_condition_indestructible（pure 1、dmrp22-1a。
partial が無く S-MAX 進化＋手札からの出場誘発と複合）、
s_trigger_lock（pure 1、dm26ex3-013。第374弾の deny
[s_trigger] はあるが本カードは「このクリーチャーが
タップしていれば」の自己タップ条件と攻撃強制条項が
未構築）、untap_trigger（pure 1、dmr02-s01。効果側が
山札ほぼ全引き＋S・トリガー無料詠唱の複合で重い）、
destroy_replaces_to_mana（pure 1、dmex08-021。破壊の
行き先を変える継続効果の付与形が未検証）。
範囲内・未評価で最小の variable_breaks_by_count
（pure 1件、multi にも現れない）を選定した。第360弾で
「breaks_add の辞書形で届く可能性はあるが数え上げの
検証が要る」として次点に残された候補であり、本弾では
第130弾の確立形で実挙動を検証して選定した。

対象は pure 1件すべて: dm06-029 シグマ・トゥレイト
（進化クリーチャー / 火 / コスト6 / パワー9000 /
サバイバー）。公式テキスト:
「進化ー自分のサバイバー１体の上に置く。
クルー・ブレイカー:サバイバー(シールドを攻撃したとき、
バトルゾーンにある自分の他のサバイバー１体につき、
シールドをさらにもう１枚ブレイクする)」

結論は完全なドリフト（新規語彙・エンジン・defs・
スキーマ変更なし）:
- クルー・ブレイカーは第130弾で確立した mod の
  breaks {count}（base 1 + amount（既定1）× セレクタの
  数）で表す。登録先例: dmc51-006（クルー・ブレイカー:
  ドラゴン。filter は race_has 版で other: true）、
  dm26-009（多色版。原文に「他の」が無いため other
  なし）、dmr01-002（keyword: blocker 版）。
- 本カードの原文は「自分の他のサバイバー」なので
  selector は {zone: bz, owner: you, filter:
  {races: [サバイバー]}, other: true}。種族フィルタは
  厳密な種族一致 races を使う（サバイバーは単一種族名。
  ドラゴンのようなカテゴリではないため race_has の
  部分一致は使わない）。
- rejects 行 partial の notes「mod の breaks は固定数
  しか書けない」は第130弾以前の記述で陳腐化している。
  partial 本体は骨格（types / civs / cost / power /
  races / mana / evolve_from / text）が組立て済みで、
  未解決は unsupported の本 gap 1件だけ。補完なし
  （partial の text は行の公式テキストの「 / 」連結形
  で全文と一致）。alias は無い。単面カードで未検証の
  面は無い。

確立形:
- abilities = [static {affects: self, mod: {breaks:
  {count: {zone: bz, owner: you, filter:
  {races: [サバイバー]}, other: true}}}}] の1件。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い。breaks の
count は defs 検証・schema.py の両方に定義済み
（第408弾の教訓で確認。スキーマ再生成不要・Rust
ミラー不要・rust_stamp への影響なし）。

proto T1141（dm06-029 型）/ T1142（他のサバイバー役）/
T1143（非サバイバー役）。

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

STATIC = {"kind": "static", "affects": "self",
          "mod": {"breaks": {"count": {"zone": "bz", "owner": "you",
                                       "filter": {"races": ["サバイバー"]},
                                       "other": True}}}}
FORM = [STATIC]
FULL_TEXT = ("進化ー自分のサバイバー１体の上に置く。 / "
             "クルー・ブレイカー:サバイバー(シールドを攻撃したとき、"
             "バトルゾーンにある自分の他のサバイバー１体につき、"
             "シールドをさらにもう１枚ブレイクする)")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1141")
    assert c["name"] == "シグマ・トゥレイト"
    assert c["types"] == ["creature", "evolution"]
    assert c["civs"] == ["fire"]
    assert c["cost"] == 6 and c["power"] == 9000 and c["mana"] == 1
    assert c["races"] == ["サバイバー"]
    assert c["evolve_from"] == {"races": ["サバイバー"]}
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(c, TABLES)
    assert d.abilities == FORM


def test_bad_breaks_dict_rejected(rules):
    # breaks {count} は amount / count / base 以外のキーを
    # 許さない（defs の検証）。未知キーは DefError
    bad = copy.deepcopy(proto_card("T1141"))
    bad["abilities"] = [{"kind": "static", "affects": "self",
                         "mod": {"breaks": {"count":
                                            {"zone": "bz", "owner": "you"},
                                            "bogus": 1}}}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn, n=0):
    return [c for c in e.zlist("bz", p)
            if e.s.cards[c].defn == defn][n]


def _breaks(e, p, defn, n=0):
    ch = e.chars(_cid(e, p, defn, n))
    return ch["breaks"], ch["break_opts"]


def test_breaks_count_chars(rules):
    # 単独では自分を数えず 1枚（other: true の判別:
    # 数えれば 2 になる）
    e = _build(rules, {"bz": ["T1141"]}, {})
    assert _breaks(e, 0, "T1141") == (1, [1])
    # 他のサバイバー1体で 2枚、2体で 3枚
    e = _build(rules, {"bz": ["T1141", "T1142"]}, {})
    assert _breaks(e, 0, "T1141") == (2, [2])
    e = _build(rules, {"bz": ["T1141", "T1142", "T1142"]}, {})
    assert _breaks(e, 0, "T1141") == (3, [3])
    # 非サバイバーは数えない
    e = _build(rules, {"bz": ["T1141", "T1143"]}, {})
    assert _breaks(e, 0, "T1141") == (1, [1])
    # 相手のサバイバーは数えない（owner: you）
    e = _build(rules, {"bz": ["T1141"]}, {"bz": ["T1142"]})
    assert _breaks(e, 0, "T1141") == (1, [1])
    # 同名2体は互いを数える（other は自分自身だけを除く）
    e = _build(rules, {"bz": ["T1141", "T1141"]}, {})
    assert _breaks(e, 0, "T1141", 0) == (2, [2])
    assert _breaks(e, 0, "T1141", 1) == (2, [2])


def _drive_attack(e, attacker):
    """p0 の attacker でプレイヤーを攻撃し、攻撃した
    ターンの2つ先のターンまで進める（第360弾の作法）。"""
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
            if "no_block" in keys:
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


def test_attack_breaks_counted_shields(rules):
    # 他のサバイバー2体: 実際にシールドを3枚ブレイクする
    # （5→2）
    e = _build(rules, {"bz": ["T1141", "T1142", "T1142"]}, {})
    st = _drive_attack(e, "T1141")
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 2
    # 単独では1枚（5→4）
    e = _build(rules, {"bz": ["T1141"]}, {})
    st = _drive_attack(e, "T1141")
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 4
