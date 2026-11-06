"""語彙パイロット第81弾: not_race_filter（〜でないクリーチャー）。

種族否定フィルタ filter: {not_race_has: X} を追加した（race_has の否定）。
defs.py の FILTER_KEYS と engine/selectors.py の filter_match に対応。
"""
from conftest import setup

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-nr",
    "name": "試験非龍獣",
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 5,
    "power": 4000,
    "races": ["テスト"],
    "text": "このクリーチャーがバトルゾーンに出た時、相手のドラゴンでないクリーチャーを１体破壊する。",
    "abilities": [
        {"kind": "trigger",
         "when": {"event": "summon", "subject": "self"},
         "effect": [
             {"op": "destroy",
              "select": {"zone": "bz", "owner": "opp", "count": 1,
                         "filter": {"types": ["creature"],
                                    "not_race_has": "ドラゴン"}}},
         ]},
    ],
    "source": {"official": "test-nr", "review": "pending"},
}


def test_not_race_has_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["effect"][0]["select"]["filter"]["not_race_has"] == "ドラゴン"


def test_not_race_has_filter_match(rules):
    """T156（アーマード・ドラゴン）は not_race_has: ドラゴン にマッチせず、
    T001（テスト）はマッチする。"""
    e = setup(rules, {"bz": ["T156", "T001"]}, {})
    by_defn = {e.s.cards[c].defn: c for c in e.zlist("bz", 0)}
    assert not e.filter_match(by_defn["T156"], {"not_race_has": "ドラゴン"})
    assert e.filter_match(by_defn["T001"], {"not_race_has": "ドラゴン"})
    # race_has と対になることの確認
    assert e.filter_match(by_defn["T156"], {"race_has": "ドラゴン"})
    assert not e.filter_match(by_defn["T001"], {"race_has": "ドラゴン"})


def test_not_race_has_partial_match(rules):
    """部分一致: 種族「アーマード・ドラゴン」は 'ドラゴン' を含むため除外される。"""
    e = setup(rules, {"bz": ["T156"]}, {})
    cid = e.zlist("bz", 0)[0]
    assert not e.filter_match(cid, {"not_race_has": "アーマード"})
    assert e.filter_match(cid, {"not_race_has": "エンジェル"})


def test_not_race_has_list_form(rules):
    """リスト形式: いずれかの種族に部分一致したら除外される（第81弾拡張）。"""
    e = setup(rules, {"bz": ["T156", "T001"]}, {})
    by_defn = {e.s.cards[c].defn: c for c in e.zlist("bz", 0)}
    f = {"not_race_has": ["ゴッド", "ドラゴン", "オラクル"]}
    assert not e.filter_match(by_defn["T156"], f)   # アーマード・ドラゴンはドラゴンに一致
    assert e.filter_match(by_defn["T001"], f)       # テストはいずれにも一致しない
