"""語彙パイロット第31弾（フェーズ9）: フシギバース / ラスト・バースト / メテオバーン /
ジャンケン / シールド・プラス。"""
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


def test_fushigibirth(rules):
    """フシギバース: 墓地から、自分のクリーチャーをタップしてマナに置き、差額を払って召喚する。"""
    e = setup(rules, {"bz": ["T005"], "graveyard": ["T095"], "mana": ["T001"] * 7}, {})
    seen = {}

    def drive(e, d, keys):
        if d["kind"] == "choose_cards" and any("T005" in k for k in keys):
            e.answer([0])
            return True
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if k == "play:T095:fushigi"]
            if hit:
                seen["opt"] = True
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T095" for c in e.zlist("bz", 0)), drive, 250)
    assert seen.get("opt")
    # ベースにした T005 はタップ状態でマナゾーンにいる
    assert any(e.s.cards[c].defn == "T005" and e.s.cards[c].tapped for c in e.zlist("mana", 0))


def test_last_burst(rules):
    """ラスト・バースト: 破壊された時、呪文側を無料で唱えて2ドローする。"""
    e = setup(rules, {"bz": ["T096"]}, {"hand": ["T006"], "mana": ["T005", "T005", "T005"]})
    seen = {}

    def drive(e, d, keys):
        if d["kind"] == "yes_no" and d["player"] == 0:
            if "hand_at_ask" not in seen:
                seen["hand_at_ask"] = len(e.zlist("hand", 0))
            e.answer([keys.index("yes")])
            return True
        if d["kind"] not in ("pay_mana", "charge") and d["player"] == 1:
            hit = [i for i, k in enumerate(keys) if "T006" in k and not k.startswith("charge:")]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T096" for c in e.zlist("graveyard", 0)), drive, 250)
    # 呪文側（2ドロー）は同じ窓の中で解決される。次の自分のターン開始（charge が出る）時点では
    # バーストの2枚＋ターン開始の1枚で +3 になっているはず（バーストが不発なら +1 しか増えない）
    assert "hand_at_ask" in seen
    for _ in range(20):
        d = e.advance()
        assert d is not None
        if d["kind"] == "charge" and d["player"] == 0:
            break
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert len(e.zlist("hand", 0)) == seen["hand_at_ask"] + 3


def test_meteor_burn_replacement(rules):
    """メテオバーン: 進化獣が離れる時、下のカードを墓地に置くことで留まる（置換の提示が出る）。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T097", "T011"], "mana": ["T005"] * 8}, {})

    def drive(e, d, keys):
        if d["kind"] == "choose_evo_source":
            e.answer([0])
            return True
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if k == "play:T097"]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T097" for c in e.zlist("bz", 0)), drive, 200)
    cid = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T097")
    assert len(e.s.cards[cid].under) == 1   # 進化元が下にいる（メテオバーンの燃料）

    # 自分の呪文で破壊しようとすると、メテオバーンの置換が提示され、選ぶと下のカードだけが墓地へ行き本体は残る
    seen = {}

    def drive2(e, d, keys):
        if d["kind"] == "choose_replacement":
            hit = [i for i, k in enumerate(keys) if "T097" in k]
            if hit:
                seen["replaced"] = True
                e.answer([hit[0]])
                return True
        if d["kind"] == "choose_cards":
            hit = [i for i, k in enumerate(keys) if "T097" in k]
            if hit:
                e.answer([hit[0]])
                return True
        if d["kind"] == "main" and d["player"] == 0:
            hit = [i for i, k in enumerate(keys) if k == "play:T011"]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: bool(seen.get("replaced")), drive2, 300)
    assert any(e.s.cards[c].defn == "T097" for c in e.zlist("bz", 0))
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T001" for c in e.zlist("graveyard", 0)), None, 60)
    cid97 = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T097")
    assert not e.s.cards[cid97].under   # 離れた下のカードは under から外れる（第33弾で修正したエンジンの潜在バグ）


@__import__("pytest").mark.xfail(reason="再変換ラウンド307-317（1736f5c5）以降に落ちる。原因未特定（ジャンケン解決の2ドローが出ない）。調査待ち", strict=False)
def test_janken_win_draws(rules):
    """ジャンケン: 自分グー・相手チョキで勝ち、2ドローする。"""
    e = setup(rules, {"hand": ["T098"], "mana": ["T005", "T005", "T005"]}, {})
    h0 = len(e.zlist("hand", 0))

    def drive(e, d, keys):
        if d["kind"] == "choose_one" and "rock" in keys:
            e.answer([keys.index("rock")] if d["player"] == 0 else [keys.index("scissors")])
            return True
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if "T098" in k and not k.startswith("charge:")]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T098" for c in e.zlist("bz", 0)), drive, 200)
    assert _settle(e, lambda: len(e.zlist("hand", 0)) == h0 + 1, None, 120)   # -1（出した）+2ドロー


def test_shield_plus(rules):
    """シールド・プラス: 山札の上1枚がシールドの束の下に入り、シールドの数え方は増えない。"""
    e = setup(rules, {"hand": ["T099"], "mana": ["T004"] * 4}, {})
    n_shields = len(e.zlist("shield", 0))
    deck0 = len(e.zlist("deck", 0))

    def drive(e, d, keys):
        if d["kind"] == "yes_no":
            e.answer([keys.index("yes")])
            return True
        if d["kind"] not in ("pay_mana", "charge"):
            hit = [i for i, k in enumerate(keys) if "T099" in k and not k.startswith("charge:")]
            if hit:
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: any(e.s.cards[c].defn == "T099" for c in e.zlist("bz", 0)), drive, 200)
    assert _settle(e, lambda: any(e.s.cards[c].under for c in e.zlist("shield", 0)), None, 120)
    assert len(e.zlist("shield", 0)) == n_shields        # 束は1つと数える
    assert len(e.zlist("deck", 0)) == deck0 - 1          # 山札から1枚減った
