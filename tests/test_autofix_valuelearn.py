import json
import random
from dmsim.autofix import valuelearn as VL
from dmsim.autofix.loop import Knobs
from dmsim.search.leaf_parts import Part, PartsSpec

SPEC = PartsSpec(parts=(Part("hand", ("A",), 1, 1.0), Part("graveyard", ("B",), 2, 1.0)))


def snap(hand=0, gy_b=0, opp=5, turn=1):
    return {"turn": turn, "own_hand": hand, "own_mana": 0, "own_bz": 0, "own_gy": gy_b, "opp_shield": opp, "opp_deck": 30,
            "defs": {"hand": {"A": 1} if hand else {}, "graveyard": {"B": gy_b}}}


def test_features_and_names_align():
    assert len(VL.features(snap(1, 2), SPEC)) == len(VL.feature_names(SPEC)) == 8
    assert VL.features(snap(1, 3), SPEC)[-1] == 2.0          # need=2 で頭打ち


def test_fit_recovers_signal_and_handles_degenerate():
    rng = random.Random(0)
    rows = []
    for _ in range(200):
        h, g = rng.randint(0, 1), rng.randint(0, 2)
        y = -(5 - 2 * h - g) + rng.uniform(-0.1, 0.1)       # 部品が多いほど早いキル
        rows.append(VL.features(snap(h, g), SPEC) + [y])
    m = VL.fit(rows)
    assert VL.score(m, VL.features(snap(1, 2), SPEC)) > VL.score(m, VL.features(snap(0, 0), SPEC))
    assert VL.fit(rows[:5]) is None
    assert VL.fit([r[:-1] + [-3.0] for r in rows]) is None   # ラベルに差が無い


def test_rows_from_curves_skips_turn0_and_labels_by_kill():
    cur = [[snap(turn=0), snap(1, 0, turn=1), snap(1, 1, turn=2)]]
    rows = VL.rows_from_curves(cur, [None], SPEC, 4)
    assert len(rows) == 2 and -5.0 <= rows[0][-1] < -4.0
    assert VL.rows_from_curves(cur, [3], SPEC, 4)[0][-1] == -3.0


def test_append_rows_resets_on_name_change(tmp_path):
    p = str(tmp_path / "x.jsonl")
    names = VL.feature_names(SPEC)
    assert len(VL.append_rows(p, [[1.0, 2.0]], names)) == 1
    assert len(VL.append_rows(p, [[3.0, 4.0]], names)) == 2
    assert len(VL.append_rows(p, [[5.0, 6.0]], names + ["extra"])) == 1
    assert json.loads(open(p).readline())["names"] == names + ["extra"]


def test_knobs_default_learned_off():
    assert Knobs().learned_mult == 0.0
