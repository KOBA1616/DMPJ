"""修繕ステージ（追補2）: 「自分のシールドを墓地に置く」条項の再変換。

前段の修繕ステージ（追補）で除外された break {count: 0, player: you}
2件（dmx05-s03 / dmx11-023）は、値の問題ではなく op 自体が誤りだっ
た。本文は「自分のシールドをひとつ、墓地に置いてもよい。そうした
場合、〜」というコスト節だが、ブレイクタスクは割ったシールドを
手札へ送り（S・トリガー宣言とブレイクイベントを伴う）、しかも
count: 0 では支払いが起きないのに後続効果だけが無条件で発火して
いた（修繕前プローブ実測: 両カードともシールド5→5のまま後続の
破壊が発火）。

センサス（op break 全115件、player: you は32件）で他カードの本文も
全件照合した結果、同じ誤用はさらに2件あった（必須形）:

- dmsd07-008 セツナノ裁徒: 離れた時「自分のシールドを１つ、墓地に
  置く」を break {count: 1, player: you} で実装（修繕前実測: シー
  ルドは手札へ行った）。
- dmx11-007 ボルカニック・アロー: 「自分のシールドをひとつ選び、
  墓地に置く」を break {count: 1, player: you} で実装（同上）。

残り28件は本文が本物のブレイク（「自分のシールドをブレイクする」
＝手札＋S・トリガー）なので無変更。dmr12-010 は text フィールドが
「G・リンク」のみで条項を照合できないため無変更。

是正形:
- 任意コスト2件は実績イディオム（dmex01-026 / dmd08-019 /
  dmbd22-021 と同形）: choose {zone: shield, owner: you, count: 1,
  up_to: true, as: sh} → if {count(ref: sh) >= 1} → [move {ref: sh}
  → graveyard (reason: put), 後続効果]。
- 必須2件は move {select: {zone: shield, owner: you, count: 1},
  to: graveyard, reason: put}。

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

MAY_CARDS = ["dmx05-s03", "dmx11-023"]        # 「置いてもよい。そうした場合」
MUST_CARDS = ["dmsd07-008", "dmx11-007"]      # 必須の「墓地に置く」
FIXED = MAY_CARDS + MUST_CARDS


def _ops(node, op, out):
    if isinstance(node, dict):
        if node.get("op") == op:
            out.append(node)
        for v in node.values():
            _ops(v, op, out)
    elif isinstance(node, list):
        for v in node:
            _ops(v, op, out)


def test_disposition_idiom_and_counts():
    rej = [json.loads(l) for l in open(REJECTS, encoding="utf-8") if l.strip()]
    assert len(rej) == 2096
    cards = _conv_cache.all_cards(CONVERTED)
    assert len({c["id"] for c in cards}) == 10227
    byid = {c["id"]: c for c in cards}
    for cid in FIXED:
        brk = []
        _ops(byid[cid], "break", brk)
        assert brk == [], (cid, brk)          # 誤用 op は残らない
        parse_card(byid[cid], TABLES)
    for cid in MAY_CARDS:
        ch = []
        _ops(byid[cid], "choose", ch)
        assert any(c.get("as") == "sh" and c["select"].get("zone") == "shield"
                   and c["select"].get("up_to") is True for c in ch), cid
        mv = []
        _ops(byid[cid], "move", mv)
        assert any(m.get("to") == "graveyard"
                   and (m.get("select") or {}).get("ref") == "sh"
                   for m in mv), cid
    for cid in MUST_CARDS:
        mv = []
        _ops(byid[cid], "move", mv)
        assert any(m.get("to") == "graveyard"
                   and (m.get("select") or {}).get("zone") == "shield"
                   and (m.get("select") or {}).get("count") == 1
                   for m in mv), cid
    # player: you の break は本物のブレイク28件だけが残る
    left = 0
    for c in cards:
        brk = []
        _ops(c, "break", brk)
        left += sum(1 for b in brk if b.get("player") == "you")
    assert left == 28, left


# ---------- 実挙動ドライバ ----------

def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)
            if e.s.cards[c].controller == p]


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _drive(e, done, casts=None, attack=None, pick_defn=None, pay=True,
           steps=900):
    """casts: {player: defn} / attack: 自分の defn で相手プレイヤーを攻撃。
    シールドゾーンの choose_cards がコスト選択（pay で払う/辞退）。
    払ったシールドの cid と、現れた決定種別の集合を返す。"""
    casts = casts or {}
    seen = []
    paid = {"cid": None}
    cast_done = set()
    attacked = {"done": False}
    for _ in range(steps):
        if done(e):
            return seen, paid["cid"]
        d = e.advance()
        assert d is not None, "game ended before done"
        kind = d["kind"]
        if kind not in seen:
            seen.append(kind)
        keys = [o["key"] for o in d["options"]]
        pl = d.get("player")
        if kind == "main" and pl in casts and pl not in cast_done \
                and f"play:{casts[pl]}" in keys:
            e.answer([keys.index(f"play:{casts[pl]}")])
            cast_done.add(pl)
        elif kind == "attack" and attack and not attacked["done"] and pl == 0:
            ak = [k for k in keys if k.startswith(f"attack:{attack}:")]
            pref = [k for k in ak if k.endswith(":player")] or ak
            if pref:
                e.answer([keys.index(pref[0])])
                attacked["done"] = True
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
        elif kind == "choose_cards":
            opts = d["options"]
            if opts and all(e.s.cards[o["cid"]].zone == "shield"
                            and e.s.cards[o["cid"]].controller == pl
                            for o in opts):
                if pay:
                    paid["cid"] = opts[0]["cid"]
                    e.answer([0])
                else:
                    e.answer([])
            elif pick_defn:
                idx = next((i for i, o in enumerate(opts)
                            if e.s.cards[o["cid"]].defn == pick_defn), None)
                e.answer([idx] if idx is not None
                         else list(range(d["max"])))
            else:
                e.answer(list(range(d["max"])))
        elif kind == "choose_shields":
            e.answer(list(range(d["max"])))
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


def test_congratulation_pay_shield_to_graveyard(rules):
    """dmx11-023（是正対象）: 出た時、シールドを1つ墓地に置くと、
    相手は自身のクリーチャーを2体選んで破壊する。払ったシールドは
    手札ではなく墓地へ行き、ブレイクイベントは発生しない。"""
    e = build(rules, {"p0": {"hand": ["dmx11-023"], "mana": ["T008"] * 8},
                      "p1": {"bz": ["T001", "T004"]},
                      "filler": "T002", "seed": 1})
    seen, paid_cid = _drive(
        e, lambda e: "dmx11-023" in _defns(e, "bz", 0) and _quiet(e),
        casts={0: "dmx11-023"}, pay=True)
    assert paid_cid is not None
    assert e.s.cards[paid_cid].zone == "graveyard"     # 手札ではない
    assert len(e.s.zones["shield"][0]) == 4
    assert _defns(e, "bz", 1) == []                    # 2体とも破壊
    assert sorted(_defns(e, "graveyard", 1)) == ["T001", "T004"]
    assert "declare_strigger" not in seen              # S・トリガー宣言なし
    assert not [r for r in e.s.pub if r.get("ev") == "break"]


def test_congratulation_decline_no_destroy(rules):
    """dmx11-023: シールドを置かない（0枚選択）と、後続の破壊は
    発火しない（修繕前は支払い無しで発火していた）。"""
    e = build(rules, {"p0": {"hand": ["dmx11-023"], "mana": ["T008"] * 8},
                      "p1": {"bz": ["T001", "T004"]},
                      "filler": "T002", "seed": 1})
    _drive(e, lambda e: "dmx11-023" in _defns(e, "bz", 0) and _quiet(e),
           casts={0: "dmx11-023"}, pay=False)
    assert len(e.s.zones["shield"][0]) == 5
    assert sorted(_defns(e, "bz", 1)) == ["T001", "T004"]
    assert _defns(e, "graveyard", 0) == []


def test_zabimetheus_pay_shield_to_graveyard(rules):
    """dmx05-s03（是正対象）: エイリアン（自身）が攻撃する時、
    シールドを1つ墓地に置くと、相手のパワー6000以下を1体破壊する。"""
    e = build(rules, {"p0": {"bz": ["dmx05-s03"]},
                      "p1": {"bz": ["T004"]},
                      "filler": "T002", "seed": 1})
    seen, paid_cid = _drive(
        e, lambda e: "T004" in _defns(e, "graveyard", 1) and _quiet(e),
        attack="dmx05-s03", pay=True)
    assert paid_cid is not None
    assert e.s.cards[paid_cid].zone == "graveyard"
    assert len(e.s.zones["shield"][0]) == 4


def test_zabimetheus_decline_no_destroy(rules):
    """dmx05-s03: シールドを置かないと、後続の破壊は発火しない。"""
    e = build(rules, {"p0": {"bz": ["dmx05-s03"]},
                      "p1": {"bz": ["T004"]},
                      "filler": "T002", "seed": 1})
    _drive(e, lambda e: _quiet(e) and e.s.turn >= 2,
           attack="dmx05-s03", pay=False)
    assert "T004" in _defns(e, "bz", 1)                 # 破壊されていない
    assert len(e.s.zones["shield"][0]) == 5            # 自分のシールド不変
    assert _defns(e, "graveyard", 0) == []


def test_volcanic_arrow_shield_to_graveyard(rules):
    """dmx11-007（是正対象・必須形）: 呪文の解決で、破壊の後に自分の
    シールドをひとつ選び墓地に置く（修繕前は手札へ行った）。"""
    e = build(rules, {"p0": {"hand": ["dmx11-007"], "mana": ["T034"] * 2},
                      "p1": {"bz": ["T001"]},
                      "filler": "T002", "seed": 1})
    seen, paid_cid = _drive(
        e, lambda e: "dmx11-007" in _defns(e, "graveyard", 0) and _quiet(e),
        casts={0: "dmx11-007"}, pick_defn="T001", pay=True)
    assert paid_cid is not None
    assert e.s.cards[paid_cid].zone == "graveyard"     # 手札ではない
    assert len(e.s.zones["shield"][0]) == 4
    assert "T001" in _defns(e, "graveyard", 1)
    assert "declare_strigger" not in seen


def test_setsuna_leave_shield_to_graveyard(rules):
    """dmsd07-008（是正対象・必須形）: バトルゾーンを離れた時、自分の
    シールドを1つ墓地に置く（修繕前は手札へ行った）。"""
    e = build(rules, {"p0": {"bz": ["dmsd07-008"]},
                      "p1": {"hand": ["T056"], "mana": ["T008"] * 3},
                      "filler": "T002", "seed": 1})
    seen, paid_cid = _drive(
        e, lambda e: "dmsd07-008" in _defns(e, "graveyard", 0) and _quiet(e),
        casts={1: "T056"}, pick_defn="dmsd07-008", pay=True)
    assert paid_cid is not None
    assert e.s.cards[paid_cid].zone == "graveyard"     # 手札ではない
    assert len(e.s.zones["shield"][0]) == 4
    assert "declare_strigger" not in seen
