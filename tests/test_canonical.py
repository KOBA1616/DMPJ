"""dmsim.canonical: 同名カードは最新の版を採用し、古い ID は別名として控える。"""
from dmsim.cards import canonical as c


def test_normalize_absorbs_notation_and_old_multicolor_note():
    old = "マナゾーンに置く時、このカードはタップして置く。このクリーチャーが出た時、カードを１枚引く。（注釈）"
    new = "このクリーチャーが出たとき、カードを1枚引く。"
    assert c.normalize_text(old) == c.normalize_text(new)
    meta = {"card_type": "進化クリーチャー（究極進化）", "civilization": "火/水", "cost": "6", "power": "6000+"}
    assert c.normalize_meta(meta) == c.normalize_meta({**meta, "card_type": "進化クリーチャー", "civilization": "水/火", "power": "6000"})


def test_product_rank_orders_by_release_date():
    r = c.product_rank()
    assert r["26ex4"] < r["25ex4"] < r["22rp1"] < r["rp22"] < r["r23"] < r["39"] < r["1"]
    assert "promoy1" not in r and "art01" not in r            # 発売日の無い商品は順位を持たない（最も古い扱い）


def test_canonical_index_prefers_latest_and_keeps_old_ids_as_aliases():
    ix = c.canonical_index()
    v = ix["目的不明の作戦"]
    assert v["id"] == "dmx24-017" and v["aliases"] == ["dmx21-066"]
    assert c.alias_to_canonical()["dmx21-066"] == "dmx24-017"
    assert ix["絶望神サガ"]["id"] == "dm22ex2-021"
    assert all(v["id"] not in v["aliases"] for v in ix.values())
