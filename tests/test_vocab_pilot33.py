"""語彙パイロット第33弾（フェーズ11）:
- G-NEO進化: 面の neo: true（重ね出し）＋キーワード g_neo（離脱置換: 下のカードすべてが同じ行き先へ）
- 「召喚によって出た時」は when の reason: summon で既存表現できることの確認
- 「相手は呪文を唱えられない」は affects（相手の手札の呪文）＋ deny: [cast] で既存表現できることの確認
- last_burst の重複定義（第31弾で誤って追加し、正規の play_free 版を覆っていた）を除去
"""
from conftest import setup


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


def test_g_neo_leave_replacement(rules):
    """G-NEO: 重ねて出して破壊されると、下のカードだけが墓地へ行き、本体は場に残る。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T101"], "mana": ["T005"] * 8}, {})

    def drive(e, d, keys):
        if d["kind"] == "choose_evo_source":
            e.answer([0])
            return True
        if d["kind"] == "choose_cards":
            hit = [i for i, k in enumerate(keys) if "T101" in k]
            if hit:
                e.answer([hit[0]])
                return True
        if d["kind"] == "main" and d["player"] == 0:
            hit = [i for i, k in enumerate(keys) if k == "play:T101:neo"]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T101" for c in e.zlist("bz", 0)), drive, 250)
    cid = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T101")
    assert len(e.s.cards[cid].under) == 1
    assert "evolution" in e.chars(cid)["types"]   # 下にあればNEO進化クリーチャーとして扱う

    # 自分の呪文 T011（自分のクリーチャーを1体破壊）で T101 を狙う → 置換で下の T001 だけが墓地へ
    e2 = setup(rules, {"bz": ["T001"], "hand": ["T101", "T011"], "mana": ["T005"] * 10}, {})
    assert _settle(e2, lambda: any(e2.s.cards[c].defn == "T101" for c in e2.zlist("bz", 0)), drive, 250)

    def drive2(e, d, keys):
        if d["kind"] == "choose_cards":
            hit = [i for i, k in enumerate(keys) if "T101" in k]
            if hit:
                e.answer([hit[0]])
                return True
        if d["kind"] == "main" and d["player"] == 0:
            hit = [i for i, k in enumerate(keys) if k == "play:T011"]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e2, lambda: any(e2.s.cards[c].defn == "T001" for c in e2.zlist("graveyard", 0)), drive2, 300)
    assert any(e2.s.cards[c].defn == "T101" for c in e2.zlist("bz", 0))          # 本体は残る
    cid2 = next(c for c in e2.zlist("bz", 0) if e2.s.cards[c].defn == "T101")
    assert not e2.s.cards[cid2].under                                          # 下は空になった
    assert "evolution" not in e2.chars(cid2)["types"]                          # もう進化クリーチャーではない


def test_summon_only_entry_reason(rules):
    """「召喚によって出た時」: 召喚では誘発し、呪文で「出す」では誘発しない。"""
    # 召喚ルート
    e = setup(rules, {"hand": ["T104"], "mana": ["T001"] * 3}, {})
    h0 = len(e.zlist("hand", 0))

    def drive(e, d, keys):
        if d["kind"] == "main":
            hit = [i for i, k in enumerate(keys) if k == "play:T104"]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T104" for c in e.zlist("bz", 0)), drive, 200)
    assert _settle(e, lambda: len(e.zlist("hand", 0)) == h0, None, 60)   # -1（出した）+1（ドロー）

    # 「出す」ルート（T102 の呪文で手札から出す）
    e2 = setup(rules, {"hand": ["T104", "T102"], "mana": ["T003", "T003", "T001", "T001"]}, {})
    h2 = len(e2.zlist("hand", 0))

    def drive2(e, d, keys):
        if d["kind"] == "choose_cards":
            hit = [i for i, k in enumerate(keys) if "T104" in k]
            if hit:
                e.answer([hit[0]])
                return True
        if d["kind"] == "main":
            hit = [i for i, k in enumerate(keys) if k == "play:T102"]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e2, lambda: any(e2.s.cards[c].defn == "T104" for c in e2.zlist("bz", 0)), drive2, 250)
    assert _settle(e2, lambda: e2.s.turn > 1 or len(e2.zlist("hand", 0)) != h2 - 1, None, 80)
    assert len(e2.zlist("hand", 0)) == h2 - 2   # T102 と T104 を使っただけで、ドローは無い


def test_cast_restriction_deny(rules):
    """詠唱封じ: 相手の静的効果がある間、呪文の play 選択肢が出ない。"""
    e = setup(rules, {"hand": ["T003", "T001"], "mana": ["T001", "T001", "T003", "T003"]}, {"bz": ["T103"]})
    seen = {}

    def drive(e, d, keys):
        if d["kind"] == "main" and d["player"] == 0 and "play:T001" in keys:
            seen["spell_offered"] = "play:T003" in keys
            if "pass" in keys:
                e.answer([keys.index("pass")])
                return True
        return False

    _settle(e, lambda: "spell_offered" in seen, drive, 120)
    assert seen.get("spell_offered") is False

    # 対照: 封じが無ければ唱えられる
    e2 = setup(rules, {"hand": ["T003", "T001"], "mana": ["T001", "T001", "T003", "T003"]}, {})
    seen2 = {}

    def drive2(e, d, keys):
        if d["kind"] == "main" and d["player"] == 0 and "play:T001" in keys:
            seen2["spell_offered"] = "play:T003" in keys
            if "pass" in keys:
                e.answer([keys.index("pass")])
                return True
        return False

    _settle(e2, lambda: "spell_offered" in seen2, drive2, 120)
    assert seen2.get("spell_offered") is True
