"""再変換ラウンド451（第416弾 fixed_breaks_plus_one）
の記録テスト。

- 新規登録1件: dmrp07-052 C.W.テラス
  （登録形は提出形と完全一致: 対象行は round66
  由来の素行〔partial も reason フィールドも無し〕
  のため、骨格は公式データ行〔by_product/rp07.jsonl〕
  から決定的に構築したもの〔クリーチャー / 自然 /
  コスト4 / パワー4000 / 種族 ジョーカーズ、
  mana 1、keywords 無し〕に第416弾の確立形
  trigger 2件〔(1) Jチェンジ６ {when: {event:
  attack, subject: self}, effect: [may [swap
  {out: {ref: self}, out_to: mana, in: {zone:
  mana, owner: you, filter: {types: [creature],
  cost_le: 6, race_has: ジョーカーズ}, count:
  1}}]]}（第24弾の確立形、同セットの登録済み
  dmrp07-027 の登録形と完全一致）／ (2) CIP
  {when: {event: move, to: bz, subject: self},
  effect: [choose {select: {zone: bz, owner:
  you, filter: {types: [creature]}, other: true,
  count: 1}, as: pick}, modify {select: {ref:
  pick}, mod: {power: 4000, breaks_add: 1},
  duration: end_of_turn}]}（modify への power＋
  breaks_add 併記は登録済み dmr19-047・第159弾の
  先例。breaks_add は第360弾で確立）〕を足した
  もの。abilities はこの2件ちょうど、keywords
  は無いまま）。
- 補完なし（text は公式全文＝改行ありで、登録後の
  全文一致も照合済み）。
- split は None で定型所有なし＝ツール側
  ブロッカーなし。
- alias 畳み込み0件（alias 無し。対象 id を
  real / real_akashic / real_vocab / real_zone /
  proto / converted と照合し登録なし〔proto の
  ヒットは T1184 の notes 内参照のみ〕、identity
  実測で canon_id は対象自身、aliases_for = []
  のため登録エントリに source.aliases は付かない。
  正本判定は提出前に再確認済み）。
- stale クリーンアップ0件・差し戻し0件
  （reopen〔fixed_breaks_plus_one〕の出力は対象行に
  reason が無いため0件で、submit が登録成功時に
  行を除去したことを実測確認）。
- converted 10,395→10,396 / rejects
  1,916→1,915、canonical 重なり0・漏れ0。
  fixed_breaks_plus_one は完全解消。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）・distinct_type_count
  の count_spec 未同期（第405弾で観察）は
  本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第416弾本体と同形（対象を proto T1184 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T068（ジョーカーズ・コスト3役
＝入れ替え先）/ T1185（ジョーカーズ・コスト7役
＝閾値超過）/ T001（自然バニラ・パワー2000役＝
CIP の対象・非ジョーカーズのマナ役）/ T1139
（パワー6000役＝2体目の味方・選択判別）。
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
from tests.test_vocab_pilot416 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmrp07-052"
GAP = "fixed_breaks_plus_one"
NAME = "C.W.テラス"


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


def test_round451_disposition():
    rej = _reject_rows()
    assert len(rej) == 1915
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10396
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は submit が除去
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 4 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ジョーカーズ"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は trigger 2件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("keywords")         # keywords は無いまま
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し＝自動付与なし
    d = parse_card(c, TABLES)
    for a in FORM:
        assert a in d.abilities
    assert len(d.abilities) == 2
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第416弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn, zone="bz"):
    return next(c for c in e.zlist(zone, p)
                if e.s.cards[c].defn == defn)


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _drive(e, player=0, play=None, pick=None, attack=None,
           swap_pick=None, swap_decline=False, turns=0,
           stop_after_pick=False, stop_at_attack=False, limit=900):
    """player のターンを進める汎用ドライバ（第416弾
    本体と同型）。"""
    st = {"played": False, "picked": False, "attacked": False,
          "target_turn": None}
    for _ in range(limit):
        if st["target_turn"] is not None \
                and e.s.turn > st["target_turn"] + turns:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        pl = d.get("player")
        if kind in ("charge", "main", "attack") and pl == player \
                and st["target_turn"] is None:
            st["target_turn"] = e.s.turn
        if stop_after_pick and st["picked"]:
            break
        if stop_at_attack and st["played"] and kind == "attack" \
                and pl == player:
            break
        if play and not st["played"] and kind == "main" \
                and pl == player and f"play:{play}" in keys:
            st["played"] = True
            e.answer([keys.index(f"play:{play}")])
            continue
        if swap_decline and kind == "yes_no" and "no" in keys:
            e.answer([keys.index("no")])
            continue
        if kind == "yes_no" and "yes" in keys:
            e.answer([keys.index("yes")])
            continue
        if swap_pick and kind == "choose_cards" \
                and any(swap_pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if swap_pick in k)])
            continue
        if pick and not st["picked"] and kind == "choose_cards" \
                and any(pick in k for k in keys):
            st["picked"] = True
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
            continue
        if attack and not st["attacked"] and kind == "attack" \
                and pl == player and attack in keys:
            st["attacked"] = True
            e.answer([keys.index(attack)])
            continue
        if kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "declare_strigger":
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return st


def test_cip_buffs_chosen_other_creature(rules):
    """第2条項の特性判別: 登録カードが出た時、選んだ
    他のクリーチャー（T1139、パワー6000）だけが
    +4000 され 10000 になる。選ばなかった T001
    （2000）と発生源自身（4000）は変わらない
    （other: true の判別を含む）。"""
    e = _build(rules,
               {"bz": ["T001", "T1139"], "hand": [TARGET],
                "mana": ["T001", "T001", "T001", "T001"]},
               {})
    _drive(e, play=TARGET, pick="T1139", stop_after_pick=True)
    assert e.chars(_cid(e, 0, "T1139"))["power"] == 10000
    assert e.chars(_cid(e, 0, "T001"))["power"] == 2000
    assert e.chars(_cid(e, 0, TARGET))["power"] == 4000


def test_cip_buff_makes_two_breaks(rules):
    """第2条項の実挙動（breaks_add）: バフを受けた
    T001（パワー2000→6000）がプレイヤーを攻撃すると
    シールドを2枚ブレイクする（3枚→1枚）。"""
    e = _build(rules,
               {"bz": ["T001"], "hand": [TARGET],
                "mana": ["T001", "T001", "T001", "T001"]},
               {"shield": ["T001", "T001", "T001"]})
    st = _drive(e, play=TARGET, pick="T001",
                attack="attack:T001:player")
    assert st["played"] and st["attacked"]
    assert len(e.zlist("shield", 1)) == 1


def test_control_one_break_without_buff(rules):
    """対照: バフの無い T001 の攻撃はシールド
    1枚だけをブレイクする（3枚→2枚）。"""
    e = _build(rules, {"bz": ["T001"]},
               {"shield": ["T001", "T001", "T001"]})
    st = _drive(e, attack="attack:T001:player")
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 2


def test_cip_no_other_creature_no_self_buff(rules):
    """other: true の判別: 他のクリーチャーが
    いなければ、CIP は発生源自身を対象にできず
    パワーは 4000 のまま。"""
    e = _build(rules,
               {"hand": [TARGET],
                "mana": ["T001", "T001", "T001", "T001"]},
               {})
    _drive(e, play=TARGET, stop_at_attack=True)
    assert _in_zone(e, 0, "bz", TARGET)
    assert e.chars(_cid(e, 0, TARGET))["power"] == 4000


def test_cip_buff_expires_at_end_of_turn(rules):
    """duration の判別: バフはそのターン限りで、
    次の自分のターンには T001 のパワーは
    2000 に戻っている。"""
    e = _build(rules,
               {"bz": ["T001"], "hand": [TARGET],
                "mana": ["T001", "T001", "T001", "T001"]},
               {})
    _drive(e, play=TARGET, pick="T001", turns=2)
    assert e.chars(_cid(e, 0, "T001"))["power"] == 2000


def _attacker_ready(e, defn=TARGET):
    e.s.cards[_cid(e, 0, defn)].entered_turn = -1


def test_j_change_swaps_with_mana_jokers(rules):
    """第1条項の実挙動: 登録カードの攻撃時、
    マナゾーンのコスト6以下のジョーカーズ
    （T068、コスト3）と入れ替わり、元の
    クリーチャーはマナゾーンへ、攻撃は入れ替わった
    T068 で続いてシールドを1枚ブレイクする
    （2枚→1枚）。"""
    e = _build(rules,
               {"bz": [TARGET], "mana": ["T068", "T001", "T001"]},
               {"shield": ["T001", "T001"]})
    _attacker_ready(e)
    st = _drive(e, attack=f"attack:{TARGET}:player", swap_pick="T068")
    assert st["attacked"]
    assert _in_zone(e, 0, "bz", "T068")
    assert _in_zone(e, 0, "mana", TARGET)
    assert len(e.zlist("shield", 1)) == 1


def test_j_change_threshold_and_race_filter(rules):
    """閾値・種族フィルタの判別: マナゾーンに
    コスト7のジョーカーズ（T1185）とジョーカーズ
    でない T001 しかいなければ、入れ替えは起きず
    登録カード自身の攻撃でシールドを1枚ブレイク
    する（2枚→1枚）。"""
    e = _build(rules,
               {"bz": [TARGET], "mana": ["T1185", "T001", "T001"]},
               {"shield": ["T001", "T001"]})
    _attacker_ready(e)
    st = _drive(e, attack=f"attack:{TARGET}:player", swap_pick="T1185")
    assert st["attacked"]
    assert _in_zone(e, 0, "bz", TARGET)
    assert _in_zone(e, 0, "mana", "T1185")
    assert len(e.zlist("shield", 1)) == 1


def test_j_change_is_optional(rules):
    """任意性の判別: 入れ替えを断れば登録カード
    自身が攻撃し、T068 はマナゾーンに残る。"""
    e = _build(rules,
               {"bz": [TARGET], "mana": ["T068", "T001", "T001"]},
               {"shield": ["T001", "T001"]})
    _attacker_ready(e)
    st = _drive(e, attack=f"attack:{TARGET}:player", swap_decline=True)
    assert st["attacked"]
    assert _in_zone(e, 0, "bz", TARGET)
    assert _in_zone(e, 0, "mana", "T068")
    assert len(e.zlist("shield", 1)) == 1
