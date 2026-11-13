"""語彙パイロット第136弾: choose_a_race（選んだ種族の付与）。

mod.add_races に式 {race: 変数名} を書けるようにし、op_modify が継続効果の生成時に
env（choose_race の選択）で種族名へ展開する。エンジン拡張。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def _proto_card():
    with open(Path(__file__).parent.parent / "data/cards/proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == "T168")


def keys(d):
    return [o["key"] for o in d["options"]]


def test_add_races_expr_parses():
    card = parse_card(_proto_card(), TABLES)
    assert card is not None
    assert card.spell[1]["mod"]["add_races"] == [{"race": "kind"}]


def test_add_races_expr_behavior(rr):
    """R099 の起動で「ドラゴン」を選び、自分の R099（テスト種族）がドラゴンを追加で得る。"""
    e = setup(rr, {"bz": ["R099", "R100"]}, {"shield": ["R002"]})
    target = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "R099")
    assert "ドラゴン" not in e.chars(target)["races"]

    d = e.advance()
    for _ in range(10):
        if d is None:
            break
        if "activate:R099:0" in keys(d):
            e.answer([keys(d).index("activate:R099:0")])
            break
        e.answer([keys(d).index("pass")] if "pass" in keys(d) else [0])
        d = e.advance()
    else:
        raise AssertionError("activate 決定に到達しなかった")

    chosen = None
    for _ in range(10):
        d = e.advance()
        if d is None:
            break
        if d["kind"] == "choose_race":
            idx = next(i for i, o in enumerate(d["options"]) if o["name"] == "ドラゴン")
            chosen = "ドラゴン"
            e.answer([idx])
            e.advance()   # 解決を進める（同じターンの次の決定が返る）
            assert "ドラゴン" in e.chars(target)["races"]   # その場で種族が追加されている
            break
        if "pass" in keys(d):
            e.answer([keys(d).index("pass")])
        elif d["kind"] == "block":
            e.answer([keys(d).index("no_block")])
        else:
            e.answer([0])
    assert chosen == "ドラゴン"
