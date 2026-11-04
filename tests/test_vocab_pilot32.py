"""語彙パイロット第32弾（フェーズ10）:
- when の attacker: crossed を defs 検証でも許可（照合側は対応済みだった）
- split（変換ツール）が攻撃時型メテオバーンに離脱置換キーワードを誤って付けない
"""
import sys
from pathlib import Path

from conftest import setup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import rule_convert  # noqa: E402


def _settle(e, done, drive=None, max_steps=120):
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if drive and drive(e, d, keys):
            continue
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    return done()


def test_blocked_crossed_attacker_trigger(rules):
    """クロスギアの誘発「これをクロスしたクリーチャーがブロックされた時」が引ける。"""
    e = setup(rules, {"hand": ["T100"], "bz": ["T001"], "mana": ["T001"] * 5},
              {"bz": ["T004"]})
    state = {}

    def drive(e, d, keys):
        if d["kind"] == "main" and "cross:T100:T001" in keys:
            e.answer([keys.index("cross:T100:T001")])
            return True
        if d["kind"] == "main" and "play:T100" in keys:
            e.answer([keys.index("play:T100")])
            return True
        if d["kind"] == "attack" or any(k.startswith("attack:") for k in keys):
            hit = [i for i, k in enumerate(keys) if k == "attack:T001:player"]
            if hit:
                state["hand_before"] = len(e.zlist("hand", 0))
                e.answer([hit[0]])
                return True
        if d["player"] == 1 and any("T004" in k for k in keys):
            hit = [i for i, k in enumerate(keys) if "T004" in k and "no_block" not in k]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    ok = _settle(e, lambda: "hand_before" in state and len(e.zlist("hand", 0)) == state["hand_before"] + 1,
                 drive, 300)
    assert ok, "ブロックされた時の誘発で1ドローするはず"


def test_split_attack_time_meteor_burn_is_not_keyword():
    row = {"id": "x1", "text": "進化-自分のオリジン１体の上に置く。 メテオバーン - このクリーチャーが攻撃する時、"
                              "このクリーチャーの下にあるカードを１枚選び墓地に置いてもよい。そうした場合、"
                              "このクリーチャーをアンタップする。 W・ブレイカー"}
    kws, _rest, _extra = rule_convert.split(row)
    assert "meteor_burn" not in kws and "double_breaker" in kws


def test_split_leave_meteor_burn_stays_keyword():
    row = {"id": "x2", "text": "メテオバーン W・ブレイカー"}
    kws, _rest, _extra = rule_convert.split(row)
    assert "meteor_burn" in kws
