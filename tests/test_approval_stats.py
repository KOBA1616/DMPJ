import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import approval_stats as s  # noqa: E402


def test_excluded():
    assert s.excluded("サイキック・クリーチャー") and s.excluded("GRクリーチャー")
    assert not s.excluded("クリーチャー") and not s.excluded("呪文")


def test_reject_kind():
    assert s.reject_kind({"gaps": ["x"]}).endswith("（語彙不足）")
    assert s.reject_kind({"error": "opencode が1200.0秒以内に終わらなかった"}) == "変換失敗: 時間切れ"


def test_rule_convert_template_fixes():
    import rule_convert as rc
    base = dict(id="x-1", name="t", card_type="クリーチャー", civilization="火", cost="2", power="1500",
                race="ファイアー・バード", mana="1")
    c = rc.convert({**base, "text": "自分のドラゴン・クリーチャーの召喚コストを２少なくする。ただしコストは０以下にならない。"})
    assert c["abilities"][0]["mod"] == {"cost": -2, "cost_min": 1}
    c = rc.convert({**base, "text": "このクリーチャーが攻撃する時、相手の手札を１枚見ないで選び、捨てさせる。"})
    assert c["abilities"][0]["effect"][0]["select"]["chooser"] == "random"
