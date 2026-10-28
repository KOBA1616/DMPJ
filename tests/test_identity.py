import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import canonicalize  # noqa: E402
from dmsim import approval as ap  # noqa: E402
from dmsim import cardstore, identity  # noqa: E402
from dmsim.defs import DATA, load_rules, load_tables  # noqa: E402

CARD = {"name": "テスト", "types": ["creature"], "civs": ["light"], "cost": 3, "power": 1000, "keywords": ["blocker"],
        "text": "ブロッカー", "source": {"review": "pending"}}


def card(i, **kw):
    return {**CARD, "id": i, **kw, "source": {"official": i, "review": "pending"}}


def fake_index(monkeypatch, text="ブロッカー"):
    from dmsim import canonical
    idx = {"テスト": {"id": "dm05-001", "text": text, "aliases": ["dm01-001"], "product": "5", "text_variants": 1}}
    monkeypatch.setattr(canonical, "canonical_index", lambda: idx)
    monkeypatch.setattr(canonical, "alias_to_canonical", lambda: {"dm05-001": "dm05-001", "dm01-001": "dm05-001"})


def test_canonical_rows_and_aliases(monkeypatch):
    fake_index(monkeypatch)
    rows = [{"id": "dm01-001"}, {"id": "dm05-001"}, {"id": "zz-9"}]
    assert [r["id"] for r in identity.canonical_rows(rows)] == ["dm05-001", "zz-9"]
    assert identity.aliases_for("テスト", "dm05-001") == ["dm01-001"] and identity.aliases_for("テスト", "dm01-001") == []


def test_relocate_inherits_when_text_same(monkeypatch, tmp_path):
    fake_index(monkeypatch, text="ブロッカー（相手の…）")      # 注釈は正規化で吸収される
    v = ap.vocab_versions(load_tables())
    cards = [card("dm01-001")]
    ledger = {"dm01-001": ap.entry(cards[0], "approved", "rule", v)}
    st = identity.relocate(cards, ledger, v)
    assert st["renamed"] == 1 and st["inherited"] == 1
    assert cards[0]["id"] == "dm05-001" and cards[0]["source"]["aliases"] == ["dm01-001"]
    assert "dm01-001" not in ledger and ledger["dm05-001"]["by"] == "inherit" and ledger["dm05-001"]["inherited_from"] == "dm01-001"
    assert ap.stale_reason(ledger["dm05-001"], cards[0], v) is None


def test_relocate_cancels_when_text_differs(monkeypatch):
    fake_index(monkeypatch, text="スピードアタッカー")
    v = ap.vocab_versions(load_tables())
    cards = [card("dm01-001")]
    ledger = {"dm01-001": ap.entry(cards[0], "approved", "rule", v)}
    st = identity.relocate(cards, ledger, v)
    assert st["dropped_text_changed"] == 1 and cards == []
    assert ledger["dm01-001"]["status"] == "pending" and "本文が違う" in ledger["dm01-001"]["stale"]


def test_relocate_drops_duplicate_and_moves_shard(monkeypatch, tmp_path):
    fake_index(monkeypatch)
    conv, led = tmp_path / "converted", tmp_path / "approvals"
    cardstore.write(conv, [card("dm01-001"), card("dm05-001")], "# h\n")
    ap.save({}, led)
    assert canonicalize.run(conv, led)["dropped_dup"] == 1
    assert [p.name for p in conv.glob("*.yaml")] == ["dm05.yaml"]              # 旧IDの弾ファイルは消える
    assert yaml.safe_load((conv / "dm05.yaml").read_text(encoding="utf-8"))["cards"][0]["source"]["aliases"] == ["dm01-001"]
    cardstore.write(conv, [card("dm01-001")], "# h\n")                         # 最新版が未変換なら付け替えで弾が移る
    canonicalize.run(conv, led)
    assert [p.name for p in conv.glob("*.yaml")] == ["dm05.yaml"]


def test_old_id_resolves_at_load(monkeypatch, tmp_path):
    f = tmp_path / "c.yaml"
    c = card("dm05-001")
    c["source"]["aliases"] = ["dm01-001"]
    f.write_text(yaml.safe_dump({"cards": [c]}, allow_unicode=True), encoding="utf-8")
    r = load_rules([f, DATA / "cards" / "proto.yaml"])
    assert r.cards["dm01-001"].id == "dm05-001" and "dm01-001" in r.cards and r.cards.get("zz") is None
    assert "dm01-001" not in list(r.cards)


def test_deep_checks_catch_mismatch_and_effect(tmp_path):
    from dmsim import effectcheck as ec
    good = {"id": "dm01-901", "name": "デーモン", "types": ["spell"], "civs": ["darkness"], "cost": 2, "keywords": [],
            "text": "バトルゾーンにある相手のクリーチャーを１体選び、破壊する。",
            "spell": [{"op": "destroy", "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}, "count": 1}}],
            "source": {"official": "dm01-901", "review": "pending"}}
    noop = {**good, "id": "dm01-902", "text": "相手のカードを１枚引く。", "spell": [{"op": "draw", "count": 1}]}
    kw = {**CARD, "id": "dm01-903", "text": "スピードアタッカー", "keywords": ["blocker"], "source": {"review": "pending"}}
    f = tmp_path / "c.yaml"
    f.write_text(yaml.safe_dump({"cards": [good, noop, kw]}, allow_unicode=True), encoding="utf-8")
    r = load_rules([f, DATA / "cards" / "proto.yaml", DATA / "cards" / "real.yaml"])
    assert ec.effect_check(r, "dm01-901")["status"] == "ok"
    assert ec.text_check(r, "dm01-903")["status"] == "fail"          # 原文に無いキーワード
    assert ec.text_check(r, "dm01-901")["status"] == "ok"
