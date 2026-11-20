"""修繕ステージ（追補）: op 引数レベルの count: 0 不発形の修繕記録テスト。

前段の修繕ステージ（choose {count: 0, up_to: true} の移行）で「対象外」
とされた op 引数レベルの count: 0 は、実は同じ不発形だった:

- mill {count: 0} ×11: mill マクロ（data/rules/op_macros.yaml）は
  select の from_top: $count に展開されるため、count: 0 では山札の
  上から0枚しか動かない。本文の「山札の上からN枚を墓地に置いて
  もよい」（N はカードごとに 1〜6）が一切起きなかった。
- break {count: 0, player: you} ×2: op_break は count を評価して
  ブレイクタスクに渡すため 0 では何もブレイクしない。ただしこちらは
  値の問題ではなく op 自体が誤り（後述）。

本ステージでは mill 11件を本文の N に是正した（周囲の構造は不変）:

  dmr16g-008: 3 / dmr16g-008d: 3 / dmr17-075: 1 / dmr19-066: 4 /
  dmr21-089: 1 / dmr23-003: 6 / dmrp04m-s05: 1（能力2件） /
  dmrp21-035: 2 / dmx10-009: 4 / dmx10-030: 3

break 2件（dmx05-s03 / dmx11-023）は本ステージから除外し、count: 0
のまま残置した。理由: ブレイクタスクは割ったシールドを手札へ送る
（S・トリガー宣言とブレイクイベントを伴う）ため、count を 1 にしても
本文の「自分のシールドをひとつ、墓地に置いてもよい。そうした場合」
にならない。現行形は支払い無しで後続の破壊だけが発火する壊れた形
（dmx11-023 で実測: シールド5→5のまま相手のクリーチャー2体が破壊
された）。正形は実績のあるイディオム（dmex01-026 / dmd08-019 /
dmx11-022 等）:

  - {op: choose, as: sh, select: {zone: shield, owner: you,
     count: 1, up_to: true}}
  - {op: if, cond: {cmp: [{count: {ref: sh}}, ">=", 1]}, then:
     [{op: move, select: {ref: sh}, to: graveyard, reason: put},
      <後続効果>]}

への組み替えであり、値の修繕ではなく構造の再変換なので別ステージに
切り出した。

【追補2で解消】その別ステージ（修繕ステージ（追補2））で、2件とも
上記イディオムへ再変換済み。あわせてセンサスで見つかった必須形の
同種誤用2件（dmsd07-008 / dmx11-007）も move 形に是正した。詳細と
実挙動の固定は tests/test_repair_break_selfshield.py。本テストでは
「mill / break の count: 0 は converted に1件も残らない」ことと、
2件に break op が残らないことを固定する。

converted 10,227 / rejects 2,096 は不変（件数の増減なし）。

プロトテストとは別プロセスで実行すること（conftest の
DMSIM_SKIP_CONVERTED 復活の汚染回避のため tests.conftest は
import しない）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine.scenario import build  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

# mill: 本文の「山札の上からN枚」を適用した値（カード id → count の列）
MILL_VALUES = {
    "dmr16g-008": [3],
    "dmr16g-008d": [3],
    "dmr17-075": [1],
    "dmr19-066": [4],
    "dmr21-089": [1],
    "dmr23-003": [6],
    "dmrp04m-s05": [1, 1],   # 出た時と攻撃する時の2能力
    "dmrp21-035": [2],
    "dmx10-009": [4],
    "dmx10-030": [3],
}
# break: 本ステージでは除外したが、追補2でイディオムへ再変換済み
BREAK_RECONVERTED = ["dmx05-s03", "dmx11-023"]


def _op_counts(node, op, out):
    if isinstance(node, dict):
        if node.get("op") == op and isinstance(node.get("count"), int) \
                and not isinstance(node.get("count"), bool):
            out.append(node["count"])
        for v in node.values():
            _op_counts(v, op, out)
    elif isinstance(node, list):
        for v in node:
            _op_counts(v, op, out)


def test_disposition_counts_and_values():
    rej = [json.loads(l) for l in open(REJECTS, encoding="utf-8") if l.strip()]
    assert len(rej) == 2096
    cards = _conv_cache.all_cards(CONVERTED)
    assert len({c["id"] for c in cards}) == 10227
    byid = {c["id"]: c for c in cards}
    # mill は全件が本文の N になっている（count: 0 の mill は残らない）
    for cid, want in MILL_VALUES.items():
        got = []
        _op_counts(byid[cid], "mill", got)
        assert got == want, (cid, got, want)
        parse_card(byid[cid], TABLES)
    # break 2件は追補2で再変換済み（break op 自体が残らない）
    for cid in BREAK_RECONVERTED:
        got = []
        _op_counts(byid[cid], "break", got)
        assert got == [], (cid, got)
        parse_card(byid[cid], TABLES)
    # mill / break の count: 0 は converted に1件も残らない
    remaining = []
    for c in cards:
        for op in ("mill", "break"):
            got = []
            _op_counts(c, op, got)
            if 0 in got:
                remaining.append(c["id"])
    assert remaining == [], remaining


# ---------- 実挙動ドライバ（前段の修繕テストと同形） ----------

def _defns(e, zone, p=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _drive(e, done, cast=None, pick_defn=None, within_turn=None, steps=600):
    st = {"cast": False}
    for _ in range(steps):
        if done(e):
            return st
        if within_turn is not None and e.s.turn > within_turn:
            raise AssertionError(f"not resolved within turn {within_turn}")
        d = e.advance()
        assert d is not None, "game ended before done"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "main" and cast and not st["cast"] \
                and d.get("player") == 0 and f"play:{cast}" in keys:
            e.answer([keys.index(f"play:{cast}")])
            st["cast"] = True
        elif kind == "choose_cards":
            idx = None
            if pick_defn:
                for i, o in enumerate(d["options"]):
                    if e.s.cards[o["cid"]].defn == pick_defn:
                        idx = i   # key はゾーン名で重複するので位置で指す
                        break
            e.answer([idx] if idx is not None else list(range(d["min"])))
        elif kind == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d["min"])))
        elif kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("drive budget exhausted")


def test_mill_cip_moves_printed_four(rules):
    """dmr19-066 不死 デッド（修繕対象）: 出た時、山札の上から4枚が
    墓地に置かれる（修繕前は mill {count: 0} で0枚だった）。"""
    e = build(rules, {"p0": {"hand": ["dmr19-066"], "mana": ["T008"] * 4},
                      "p1": {"bz": ["T001"]}, "filler": "T002", "seed": 1})
    deck0 = len(e.s.zones["deck"][0])
    _drive(e, lambda e: "dmr19-066" in _defns(e, "bz") and _quiet(e),
           cast="dmr19-066", within_turn=1)
    assert _defns(e, "graveyard") == ["T002"] * 4   # 上から4枚が墓地へ
    assert len(e.s.zones["deck"][0]) == deck0 - 4


def test_mill_gate_opens_spell_return(rules):
    """dmr16g-008 アクア呪文師 スペルビー（修繕対象）: 出た時、上から
    3枚を墓地に置き、そうした場合に呪文を墓地から手札に戻せる
    （修繕前は milled が空で if ゲートが開かなかった）。"""
    e = build(rules, {"p0": {"hand": ["dmr16g-008"], "mana": ["T010"] * 4,
                             "graveyard": ["T003"]},
                      "p1": {"bz": ["T001"]}, "filler": "T002", "seed": 1})
    _drive(e, lambda e: "T003" in _defns(e, "hand") and _quiet(e),
           cast="dmr16g-008", pick_defn="T003", within_turn=1)
    # 墓地には mill した3枚だけが残る（T003 は手札へ戻った）
    assert _defns(e, "graveyard") == ["T002"] * 3


def test_mill_then_chain_mana_armed(rules):
    """dmr17-075 暗黒鎧 ゴルドバット（修繕対象・then 内包）: マナ武装3
    で、出た時に上から1枚目を墓地に置き、その後クリーチャーを墓地
    から手札に戻せる（修繕前は then 内の mill が0枚だった）。"""
    e = build(rules, {"p0": {"hand": ["dmr17-075"], "mana": ["T008"] * 4,
                             "graveyard": ["T001"]},
                      "p1": {"bz": ["T001"]}, "filler": "T002", "seed": 1})
    _drive(e, lambda e: "T001" in _defns(e, "hand") and _quiet(e),
           cast="dmr17-075", pick_defn="T001", within_turn=1)
    # 墓地には mill した1枚だけが残る（T001 は手札へ戻った）
    assert _defns(e, "graveyard") == ["T002"]


def test_mill_gate_opens_play_free(rules):
    """dmrp04m-s05 ハインリヒ・ダーマルク（修繕対象）: 出た時、上から
    1枚目を墓地に置き、そうしたら闇のコスト4以下のクリーチャーを
    墓地から出せる（修繕前は milled が空でゲートが開かなかった）。"""
    e = build(rules, {"p0": {"hand": ["dmrp04m-s05"], "mana": ["T008"] * 6,
                             "graveyard": ["T008"]},
                      "p1": {"bz": ["T001"]}, "filler": "T002", "seed": 1})

    def _summoned(e):
        return any(e.s.cards[c].defn == "T008"
                   and e.s.cards[c].controller == 0
                   for c in e.zlist("bz", 0))

    _drive(e, lambda e: _summoned(e) and _quiet(e),
           cast="dmrp04m-s05", pick_defn="T008", within_turn=1)
    # 墓地には mill した1枚（自然の filler）だけが残る
    assert _defns(e, "graveyard") == ["T002"]
