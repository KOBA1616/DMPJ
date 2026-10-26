"""効果の1文パターン（keyword_patterns.yaml の whole_line）をルール変換し、エンジンで実際に動かして挙動を確かめる。"""
import sys
from pathlib import Path

import pytest
import yaml
from conftest import answer, setup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import rule_convert as rc  # noqa: E402

from dmsim.defs import DATA, load_rules  # noqa: E402

BASE = {"card_type": "クリーチャー", "civilization": "自然", "cost": "1", "power": "3000", "race": "テスト", "name": "試験"}


def card(cid, text, **kw):
    r = rc.convert({**BASE, "id": cid, "text": text, **kw})
    assert r is not None, text
    return r


@pytest.fixture()
def build(tmp_path):
    def make(*cards):
        f = tmp_path / "p.yaml"
        f.write_text(yaml.safe_dump({"cards": list(cards)}, allow_unicode=True), encoding="utf-8")
        return load_rules(sorted((DATA / "cards").glob("*.yaml")) + [f])
    return make


def play(e, key):
    answer(e, "charge", "pass")
    answer(e, "main", key)


def test_etb_draw_and_mana_and_mill_and_shield(build):
    rr = build(card("P1", "このクリーチャーが出た時、カードを２枚引く。"),
               card("P2", "このクリーチャーがバトルゾーンに出た時、自分の山札の上から1枚目をマナゾーンに置く。"),
               card("P3", "このクリーチャーが出た時、自分の山札の上から2枚を墓地に置く。"),
               card("P4", "このクリーチャーが出た時、自分のシールドを1つ手札に加える。"))
    for cid, check in (("P1", lambda e: len(e.zlist("hand", 0)) == 2), ("P2", lambda e: len(e.zlist("mana", 0)) == 2),
                       ("P3", lambda e: len(e.zlist("graveyard", 0)) == 2), ("P4", lambda e: len(e.zlist("shield", 0)) == 4 and len(e.zlist("hand", 0)) == 1)):
        e = setup(rr, {"hand": [cid], "mana": ["T001"]})
        play(e, f"play:{cid}")
        if cid == "P4":
            answer(e, "choose_cards", "shield")
        e.advance()
        assert check(e), cid


def test_etb_destroy_power_limit(build):
    rr = build(card("P5", "このクリーチャーが出た時、相手のパワー3000以下のクリーチャーを1体破壊する。"))
    e = setup(rr, {"hand": ["P5"], "mana": ["T001"]}, {"bz": ["T001", "T004"]})
    play(e, "play:P5")
    d = e.advance()
    assert d["kind"] == "choose_cards"
    e.answer([0])
    e.advance()
    assert len(e.bz_tops(1)) == 1


def test_destroyed_replacements(build):
    rr = build(card("P6", "このクリーチャーが破壊される時、墓地に置くかわりにマナゾーンに置く。", power="1000"),
               card("P7", "このクリーチャーが破壊される時、墓地に置くかわりに自分の手札に戻す。", power="1000"),
               card("P8", "エターナル・Ω（このクリーチャーが離れる時、かわりに手札に戻す）", power="1000"))
    for cid, zone in (("P6", "mana"), ("P7", "hand"), ("P8", "hand")):
        e = setup(rr, {"bz": ["T004"]}, {"bz": [cid]})
        e.s.cards[e.bz_tops(1)[0]].tapped = True
        answer(e, "attack", f"attack:T004:{cid}")
        for _ in range(4):
            d = e.advance()
            if d is None or d["kind"] != "choose_replacement":
                break
            e.answer([0])
        card_ = next(c for c in e.s.cards if c.defn == cid)
        assert card_.zone == zone and not e.zlist("graveyard", 1), cid


def test_end_of_turn_untap_and_attack_untapped(build):
    rr = build(card("P9", "自分のターンの終わりに、このクリーチャーをアンタップする。"),
               card("PA", "このクリーチャーは、タップされていないクリーチャーを攻撃できる。"))
    e = setup(rr, {"bz": ["P9"]})
    cid = e.bz_tops(0)[0]
    answer(e, "attack", "attack:P9:player")
    for _ in range(6):
        d = e.advance()
        if e.s.active == 1:
            break
        e.answer([len(d["options"]) - 1])           # 残りの選択は pass
    assert e.s.active == 1 and not e.s.cards[cid].tapped      # 自分のターンの終わりにアンタップした
    e = setup(rr, {"bz": ["PA"]}, {"bz": ["T004"]})
    d = e.advance()
    assert "attack:PA:T004" in [o["key"] for o in d["options"]]


def test_effect_sentence_with_followup_is_not_converted():
    """続く文（その後…）があるものは、取りこぼさないよう丸ごとモデルへ。部分変換でも1文だけ切り出さない。"""
    t = "このクリーチャーが出た時、カードを1枚引く。 その後、手札を1枚捨てる。"
    assert rc.convert({**BASE, "id": "x", "text": t}) is None
    assert rc.split({**BASE, "id": "x", "text": t}) is None


def test_magic_bomber_puts_creature_from_deck_top_or_hand(build):
    """マジボンバーN: 攻撃する時、コストN以下のクリーチャーを手札または山札の上1枚から出してもよい（山札は上1枚だけが候補）。"""
    rr = build(card("MB", "マジボンバー ４（このクリーチャーが攻撃する時、…）", cost="5", civilization="火"))
    e = setup(rr, {"bz": ["MB"]})
    answer(e, "attack", "attack:MB:player")
    answer(e, "yes_no", "yes")
    d = e.advance()
    while d is not None and d["kind"] in ("choose_cards", "choose_shields", "choose_breaker"):
        e.answer([0])
        d = e.advance()
    assert len(e.bz_tops(0)) == 2                                    # 山札の上1枚（T001, コスト2）が出た


def test_magic_bomber_cost_limit(build):
    rr = build(card("MB", "マジボンバー １（…）", cost="5", civilization="火"))
    e = setup(rr, {"bz": ["MB"]})
    answer(e, "attack", "attack:MB:player")
    answer(e, "yes_no", "yes")
    d = e.advance()
    while d is not None and d["kind"] in ("choose_cards", "choose_shields", "choose_breaker"):
        e.answer([0])
        d = e.advance()
    assert len(e.bz_tops(0)) == 1                                    # コスト2 > 1 なので出ない


def test_spell_converts_from_keywords_and_known_effect_lines():
    import rule_convert as rc
    from dmsim.defs import load_tables, parse_card
    row = {"id": "sp1", "name": "試験呪文", "card_type": "呪文", "civilization": "水", "cost": "3", "mana": "1",
           "text": "S・トリガー（この呪文をシールドゾーンから手札に加える時、コストを支払わずにすぐ唱えてもよい）\nカードを２枚引く。\n相手のクリーチャーを１体選ぶ。このターン、そのクリーチャーのパワーを－3000する。"}
    row["text"] = row["text"].replace("\\\n", "\n")
    c = rc.convert(row)
    assert c["types"] == ["spell"] and c["keywords"] == ["s_trigger"]
    assert c["spell"][0] == {"op": "draw", "count": 2} and c["spell"][2]["mod"] == {"power": -3000}
    parse_card(c, load_tables())
    assert rc.convert({**row, "text": "カードを２枚引く。\n何か未知の効果を行う。"}) is None


def test_keyword_glued_to_following_sentence_is_split_into_lines():
    import rule_convert as rc
    r = rc.split({"id": "g", "text": "ブロッカーこのクリーチャーが出た時、カードを１枚引く。"})
    assert r[0] == ["blocker"] and r[2]       # 出た時のドローも続けてルールで変換される
    assert rc.split({"id": "g2", "text": "進化クリーチャー…"}) is None


def test_peel_keeps_annotation_with_its_keyword():
    import rule_convert as rc
    one = "T・ブレイカー(このクリーチャーはシールドを３枚ブレイクする)。"
    assert rc._peel_line(one) == [one]                                    # 注釈の後の句点だけを別の行にしない
    out = rc._peel_line("S・トリガー（この呪文をシールドゾーンから手札に加える時、コストを支払わずにすぐ唱えてもよい）相手のクリーチャーを１体破壊する。")
    assert out[0].startswith("S・トリガー(") and out[0].endswith(")") and out[1] == "相手のクリーチャーを１体破壊する。"
    assert rc._peel_line("進化クリーチャー") == ["進化クリーチャー"]                  # 名前の一部は割らない
    assert rc._peel_line("ブロッカーを持つクリーチャーは") == ["ブロッカーを持つクリーチャーは"]


def test_trigger_prefix_variants_and_spell_sentences_reused_for_creatures():
    import rule_convert as rc
    from dmsim.defs import load_tables, parse_card
    base = {"card_type": "クリーチャー", "civilization": "水", "cost": "3", "power": "2000", "race": "テスト"}
    both = rc.convert({**base, "id": "t1", "text": "このクリーチャーが出た時または攻撃する時、カードを１枚引く。"})
    assert [a["when"]["event"] for a in both["abilities"]] == ["move", "attack"]
    parse_card(both, load_tables())
    atk = rc.convert({**base, "id": "t2", "text": "このクリーチャーが攻撃する時、相手の手札を１枚見ないで選び、捨てさせる。"})
    assert atk["abilities"][0]["when"] == {"event": "attack", "subject": "self"}
    assert atk["abilities"][0]["effect"][0]["op"] == "discard"
    parse_card(atk, load_tables())
    two = rc.convert({**base, "id": "t3", "text": "このクリーチャーが出た時、カードを１枚引く。相手のクリーチャーを１体破壊する。"})
    assert two is None          # 1行に複数の文があるものは続きを取りこぼさないようモデルへ


def test_grant_keyword_to_all_my_creatures():
    import rule_convert as rc
    base = {"card_type": "クリーチャー", "civilization": "火", "cost": "3", "power": "2000", "race": "テスト"}
    r = rc.convert({**base, "id": "g1", "text": "自分のクリーチャーすべてに「スピードアタッカー」を与える。"})
    assert r["abilities"][0]["mod"] == {"grant": ["speed_attacker"]}
    assert rc.convert({**base, "id": "g2", "text": "自分のクリーチャーすべてに「謎の力」を与える。"}) is None      # 辞書にないキーワードはモデルへ
