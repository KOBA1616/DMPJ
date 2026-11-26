"""再変換ラウンド450（第415弾 battle_indestructible）
の記録テスト。

- 新規登録1件: dmd27-012 燃えるメラッチ
  （登録形は提出形と完全一致: 対象行は partial も
  reason も無い素行のため、骨格は公式データ行
  〔by_product/d27.jsonl〕から決定的に構築したもの
  〔クリーチャー / 火 / コスト4 / パワー4000 /
  種族 ファイアー・バード炎 / 革命軍、mana 1、
  keywords 無し〕に第415弾の確立形 static 2件
  〔コスト軽減 {affects: {owner: you, zone: hand,
  filter: {types: [evolution], civs: [fire]}},
  mod: {cost: -2, cost_min: 1}}（登録済み
  dm17-022 の形＋文明フィルタ。下限1読みは
  dm24ex1-087 / dm24bd2-016 の同文面先例と一致）／
  {affects: self, mod: {battle_indestructible:
  true}}（第59弾の素形、登録済み dm25rp3-055 /
  dmr21-077 と同一文面）〕を足したもの。
  abilities はこの2件ちょうど、keywords は
  無いまま）。
- 補完なし（text は公式全文で、登録後の全文一致も
  照合済み）。
- split は None で定型所有なし＝ツール側
  ブロッカーなし。
- alias 畳み込み0件（alias dmr17-082 /
  promoy14-010 / promoy14-019 は rejects に
  独自行が無く converted にも登録なし。登録
  エントリの source.aliases は validate が
  identity.aliases_for から自動付与した3件。
  正本判定は通常型で対象 id と alias 3件を
  real / real_akashic / real_vocab / real_zone /
  proto / converted と照合し登録なし〔proto の
  ヒットは T1183 の notes 内参照のみ〕、identity
  実測で canon_id は対象自身、alias 側の canon も
  dmd27-012。正本判定は提出前に再確認済み）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔battle_indestructible〕の出力は
  対象行に reason が無いため0件で、submit が
  登録成功時に行を除去したことを実測確認）。
- converted 10,394→10,395 / rejects
  1,917→1,916、canonical 重なり0・漏れ0。
  battle_indestructible は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第415弾本体と同形（対象を proto T1183 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T328（火の進化・コスト3役）/
T077（水の進化・コスト3役）/ T1090（火の非進化・
コスト2役＋進化元役＋火マナ役）/ T1139（パワー
6000役）/ T1140（パワー4000ブロッカー役＝
不破壊なし対照）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests import _conv_cache  # noqa: E402
from tests.test_vocab_pilot415 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmd27-012"
ALIASES = ["dmr17-082", "promoy14-010", "promoy14-019"]
GAP = "battle_indestructible"
NAME = "燃えるメラッチ"


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round450_disposition():
    rej = _reject_rows()
    assert len(rej) == 1916
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10395
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は submit が除去
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    for a in ALIASES:
        assert a not in rej              # alias に独自行なし
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 4 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ファイアー・バード炎", "革命軍"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は static 2件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("keywords")         # keywords は無いまま
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES  # validate の自動付与
    d = parse_card(c, TABLES)
    for a in FORM:
        assert a in d.abilities
    assert len(d.abilities) == 2
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第415弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _hand_cid(e, p, defn):
    return next(c for c in e.zlist("hand", p)
                if e.s.cards[c].defn == defn)


def _bz_cid(e, p, defn):
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn)


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def test_pay_cost_fire_evolution_reduced(rules):
    """第1条項の特性判別: 登録カードがいれば、自分の
    火の進化（T328、コスト3）の支払いコストは
    3-2=1 になる。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T328"]}, {})
    assert e.chars_ro(_hand_cid(e, 0, "T328"))["pay_cost"] == 1


def test_pay_cost_floor_with_two_sources(rules):
    """下限の判別: 登録カードが2体いても支払いコストは
    1で止まる（cost_min: 1。「0以下にならない」）。"""
    e = _build(rules, {"bz": [TARGET, TARGET], "hand": ["T328"]}, {})
    assert e.chars_ro(_hand_cid(e, 0, "T328"))["pay_cost"] == 1


def test_pay_cost_water_evolution_not_reduced(rules):
    """文明フィルタの判別: 水の進化（T077、コスト3）は
    軽減されず 3 のまま。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T077"]}, {})
    assert e.chars_ro(_hand_cid(e, 0, "T077"))["pay_cost"] == 3


def test_pay_cost_fire_non_evolution_not_reduced(rules):
    """種別フィルタの判別: 火でも進化でない
    クリーチャー（T1090、コスト2）は軽減されず 2。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T1090"]}, {})
    assert e.chars_ro(_hand_cid(e, 0, "T1090"))["pay_cost"] == 2


def test_pay_cost_no_source_control(rules):
    """対照: 登録カードが無ければ火の進化（T328）も 3。"""
    e = _build(rules, {"hand": ["T328"]}, {})
    assert e.chars_ro(_hand_cid(e, 0, "T328"))["pay_cost"] == 3


def test_pay_cost_opponent_hand_not_reduced(rules):
    """owner: you の判別: 相手の手札の火の進化
    （T328）は、自分の登録カードでは軽減されない。"""
    e = _build(rules, {"bz": [TARGET]}, {"hand": ["T328"]})
    assert e.chars_ro(_hand_cid(e, 1, "T328"))["pay_cost"] == 3


def _play_evolution(e, player=0, limit=600):
    """player が T328 を進化元 T1090 の上に召喚する
    まで進める（第415弾本体と同型）。"""
    for _ in range(limit):
        if _in_zone(e, player, "bz", "T328"):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == player \
                and "play:T328" in keys:
            e.answer([keys.index("play:T328")])
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if any("T1090" in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if "T1090" in k)])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("play never happened")


def test_summon_fire_evolution_pays_one(rules):
    """第1条項の実挙動: 登録カードと進化元（T1090）が
    いれば、火の進化 T328（コスト3）はマナ1枚の
    タップだけで召喚できる（残り2枚はアンタップ）。"""
    e = _build(rules,
               {"bz": [TARGET, "T1090"], "hand": ["T328"],
                "mana": ["T1090", "T1090", "T1090"]},
               {})
    _play_evolution(e)
    assert _in_zone(e, 0, "bz", "T328")
    tapped = sum(1 for c in e.zlist("mana", 0) if e.s.cards[c].tapped)
    assert tapped == 1


def _drive_battle(e, atk_player, atk_key, settle=1, limit=900):
    """atk_player の攻撃決定で atk_key を一度だけ
    選び、バトルを解決して settle ターン先まで進める
    （第415弾本体と同型）。"""
    st = {"attacked": False, "attack_turn": None}
    for _ in range(limit):
        if st["attacked"] and e.s.turn > st["attack_turn"] + settle:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack" and d.get("player") == atk_player \
                and not st["attacked"] and atk_key in keys:
            st["attacked"] = True
            st["attack_turn"] = e.s.turn
            e.answer([keys.index(atk_key)])
            continue
        if kind == "declare_strigger":
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return st


def test_attack_loses_battle_but_not_destroyed(rules):
    """第2条項の判別（攻撃側）: 登録カード（パワー4000）が
    タップしている T1139（パワー6000）を攻撃して
    バトルに負けても、破壊されずバトルゾーンに残る
    （勝者の T1139 も残る）。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1139"]})
    e.s.cards[_bz_cid(e, 1, "T1139")].tapped = True
    st = _drive_battle(e, 0, f"attack:{TARGET}:T1139")
    assert st["attacked"]
    assert _in_zone(e, 0, "bz", TARGET)
    assert not _in_zone(e, 0, "graveyard", TARGET)
    assert _in_zone(e, 1, "bz", "T1139")


def test_attack_control_without_indestructible_destroyed(rules):
    """対照: battle_indestructible の無い T1140
    （パワー4000）が同じ攻撃をすると、バトルに
    負けて破壊され墓地に置かれる。"""
    e = _build(rules, {"bz": ["T1140"]}, {"bz": ["T1139"]})
    e.s.cards[_bz_cid(e, 1, "T1139")].tapped = True
    st = _drive_battle(e, 0, "attack:T1140:T1139")
    assert st["attacked"]
    assert not _in_zone(e, 0, "bz", "T1140")
    assert _in_zone(e, 0, "graveyard", "T1140")
    assert _in_zone(e, 1, "bz", "T1139")


def test_attacked_loses_battle_but_not_destroyed(rules):
    """第2条項の判別（防御側）: 登録カードがプレイヤーを
    攻撃してタップした後、T1139（パワー6000）に
    攻撃され、バトルに負けても破壊されず
    バトルゾーンに残る。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1139"]})
    st1 = _drive_battle(e, 0, f"attack:{TARGET}:player", settle=0)
    assert st1["attacked"]
    assert e.s.cards[_bz_cid(e, 0, TARGET)].tapped is True
    st2 = _drive_battle(e, 1, f"attack:T1139:{TARGET}")
    assert st2["attacked"]
    assert _in_zone(e, 0, "bz", TARGET)
    assert not _in_zone(e, 0, "graveyard", TARGET)
    assert _in_zone(e, 1, "bz", "T1139")
