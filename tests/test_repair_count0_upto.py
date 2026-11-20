"""修繕ステージ: choose {count: 0, up_to: true} の棚卸しと移行の記録テスト。

第299弾で発見された不発形（selectors.select は count を選択上限と
するため count: 0 では候補があっても常に空に束縛される）の棚卸し。
converted 全件を文面照合し、「最大1枚／1体まで選んでもよい」文脈の
326箇所を count: 1（up_to: true は維持）に移行した。意図が異なる
9箇所は移行から除外し、残置した形を本テストで固定する:

- dmex02-066: 「1体破壊する」は必須（gate 形）。正形は count: 1
  （up_to なし）。
- dmex10-016 / dmex10-018: 山札の上5枚／3枚を「すべて墓地に置いて
  もよい」（束縛した集合そのものを移動する all-or-nothing）。
- dmex11-037: 手札を「すべて捨ててもよい」（同上）。
- dmr12-045: 不活性な gate（束縛 ref は常時真の count>=0 判定にのみ
  使用。実際の選択は count: "all" への may）。
- dmr13-017（1件目のみ）: 任意性の無い条件束縛（見せる・加えるとも
  必須）。正形は count: 1（up_to なし）。2件目（バウンス）は移行済み。
- dmr15-022: repeat 内の上1枚の強制束縛（任意性なし）。
- dmr17-093: 山札の上2枚をマナに置く all-or-nothing。
- dmr18-005: 墓地を「すべて山札に加えて」シャッフルする all-or-nothing。

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
from dmsim.cards.defs import DATA  # noqa: E402
from dmsim.engine.scenario import build  # noqa: E402


def setup(rules, p0, p1=None, filler="T002", seed=1, deck_size=20):
    """conftest の setup と同じ薄い包み（tests.conftest は import しない）。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": seed, "deck_size": deck_size})


CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

# 移行から除外して残置した {count: 0, up_to: true}（カード id → 箇所数）
EXCLUDED = {
    "dmex02-066": 1,   # 必須の1体破壊（gate）。正形は count: 1（up_to なし）
    "dmex10-016": 1,   # 上5枚すべてを墓地に置いてもよい
    "dmex10-018": 1,   # 上3枚すべてを墓地に置いてもよい
    "dmex11-037": 1,   # 手札をすべて捨ててもよい
    "dmr12-045": 1,    # 不活性な gate（実際の選択は may の count: "all"）
    "dmr13-017": 1,    # 任意性の無い条件束縛（2件目のバウンスは移行済み）
    "dmr15-022": 1,    # repeat 内の上1枚の強制束縛
    "dmr17-093": 1,    # 上2枚をマナに置く all-or-nothing
    "dmr18-005": 1,    # 墓地をすべて山札に加える all-or-nothing
}


def _dead_selects(node, out):
    if isinstance(node, dict):
        if node.get("count") == 0 and node.get("up_to") is True \
                and not isinstance(node.get("count"), bool):
            out.append(node)
        for v in node.values():
            _dead_selects(v, out)
    elif isinstance(node, list):
        for v in node:
            _dead_selects(v, out)


def test_disposition_counts_and_remaining():
    rej = [json.loads(l) for l in open(REJECTS, encoding="utf-8") if l.strip()]
    assert len(rej) == 2096
    cards = _conv_cache.all_cards(CONVERTED)
    assert len({c["id"] for c in cards}) == 10227
    remaining = {}
    for c in cards:
        hits = []
        _dead_selects(c, hits)
        if hits:
            remaining[c["id"]] = len(hits)
    # 移行後に残る不発形は除外した9箇所だけ
    assert remaining == EXCLUDED


# ---------- 実挙動ドライバ ----------

def _defns(e, zone, p=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _drive(e, done, cast=None, pick_defn=None, decline_pick=False,
           attack_defn=None, within_turn=None, steps=600):
    st = {"cast": False, "attacked": False}
    for _ in range(steps):
        if done(e):
            return st
        if within_turn is not None and e.s.turn > within_turn:
            raise AssertionError(f"not resolved within turn {within_turn}")
        d = e.advance()
        assert d is not None, "game ended before done"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        atk = [k for k in keys if k.startswith("attack:")]
        if atk and attack_defn and not st["attacked"]:
            want = [k for k in atk
                    if attack_defn in k and k.endswith(":player")]
            if want:
                e.answer([keys.index(want[0])])
                st["attacked"] = True
                continue
        if kind == "main" and cast and not st["cast"] \
                and d.get("player") == 0 and f"play:{cast}" in keys:
            e.answer([keys.index(f"play:{cast}")])
            st["cast"] = True
        elif kind == "choose_cards":
            if decline_pick and d["min"] == 0 and pick_defn and any(
                    e.s.cards[o["cid"]].defn == pick_defn
                    for o in d["options"]):
                e.answer([])          # 「選ばない」を選ぶ（up_to の辞退）
                continue
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


def _searcher_game(rules):
    """dmex09-002 の局面。T001 は山札の一番下（deck spec は末尾が上）に
    置くので、ドローでは手札に来ず、探索の選択でだけ動く。山札の残りは
    filler と同名だと deck_exact に剥がされるため T003 で埋める。"""
    e = build(rules, {"p0": {"hand": ["dmex09-002"],
                             "mana": ["T010"] + ["T002"] * 5,
                             "deck": ["T001"] + ["T003"] * 9},
                      "p1": {"bz": ["T001"]}, "filler": "T002", "seed": 1,
                      "deck_exact": [True, False]})
    assert "T001" not in _defns(e, "hand")
    assert _defns(e, "deck").count("T001") == 1
    assert len(e.s.zones["deck"][0]) == 10
    return e


def test_searcher_choice_now_offered(rules):
    """dmex09-002 シンカイサーチャー（移行対象）: 出た時、山札から
    1枚選んで手札に加える選択が実際に出る（移行前は空束縛で不発）。"""
    e = _searcher_game(rules)
    # ターン1（出た時の解決中）に手札へ来ること。ドローでいつか来る
    # ケースと区別するためターンで区切る。
    _drive(e, lambda e: "T001" in _defns(e, "hand") and _quiet(e),
           cast="dmex09-002", pick_defn="T001", within_turn=1)
    assert _defns(e, "deck").count("T001") == 0   # 山札からは無くなった


def test_searcher_choice_can_still_be_declined(rules):
    """dmex09-002: 移行後も up_to の辞退は可能（選ばなければ何も起きない）。"""
    e = _searcher_game(rules)
    _drive(e, lambda e: "dmex09-002" in _defns(e, "bz") and _quiet(e),
           cast="dmex09-002", pick_defn="T001", decline_pick=True)
    assert "T001" not in _defns(e, "hand")
    assert _defns(e, "deck").count("T001") == 1   # 山札に残ったまま


def test_graveyard_return_now_offered(rules):
    """dmr05-s06 偽りの名 ヤバスギル・スキル（移行対象）: 出た時、
    コスト7以上のクリーチャーを墓地から手札に戻す選択が実際に出る。"""
    e = setup(rules,
              {"hand": ["dmr05-s06"], "mana": ["T008"] * 8,
               "graveyard": ["dmr08-008"]},
              {"bz": ["T001"]}, filler="T002")
    _drive(e, lambda e: "dmr08-008" in _defns(e, "hand") and _quiet(e),
           cast="dmr05-s06", pick_defn="dmr08-008")
    assert "dmr08-008" not in _defns(e, "graveyard")


def test_rapusodi_attack_bind_now_shieldizes(rules):
    """dmr08-008 絆の戦士ラプソディ（第299弾の発見元・移行対象）:
    攻撃時、山札の上が呪文なら新しいシールドとして加えられる
    （移行前は choose が空束縛でシールドは増えなかった）。"""
    e = build(rules, {"p0": {"bz": ["dmr08-008"], "deck": ["T003"] * 4},
                      "p1": {"bz": ["T001"]}, "filler": "T002", "seed": 1,
                      "deck_exact": [True, False]})
    before = len(e.s.zones["shield"][0])
    _drive(e, lambda e: len(e.s.zones["shield"][0]) == before + 1
           and "T003" in _defns(e, "shield") and _quiet(e),
           attack_defn="dmr08-008", pick_defn="T003")
    assert "T003" in _defns(e, "shield")
