"""2026-10-24 追加の実カード（ゾーン間移動・デメリット付き・ループ／ストックの部品）の動作確認。"""
from conftest import answer, setup

from test_real_cards import bz, keys


def names(e, z, p):
    return sorted(e.s.cards[c].defn for c in (e.bz_tops(p) if z == "bz" else e.zlist(z, p)))


def drive(e, until, pick=None, limit=200):
    """until(e, d) が真になるまで進める。pick(d) が選択肢の添字を返さなければ、pass があれば pass、なければ先頭。"""
    for _ in range(limit):
        d = e.advance()
        if d is None or until(e, d):
            return d
        i = pick(d) if pick else None
        if i is None:
            ks = keys(d)
            i = ks.index("pass") if "pass" in ks else 0
        e.answer([i] if d.get("min", 1) <= 1 or d["kind"] != "choose_cards" else list(range(d["min"])))
    raise AssertionError("did not reach the condition")


def yes(d):
    return keys(d).index("yes") if d["kind"] == "yes_no" else None


def test_bolbalzak_extra_turn_then_lose(rules):
    """出た時に他のパワー6000をすべて破壊 → 追加ターン → その追加ターンの終わりに負ける。"""
    e = setup(rules, {"bz": ["dmr01-s03"], "hand": ["dmex17-w02"], "mana": ["dm09-032"] * 3 + ["dm06-110"] * 4},
              {"bz": ["dmbd13-010", "dm01-001"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dmex17-w02")
    e.advance()
    assert names(e, "bz", 0) == ["dmex17-w02"]                 # 自分のN・ワールドも破壊
    assert names(e, "bz", 1) == ["dm01-001"]                   # 9000 は残る
    assert "dmbd13-010" in names(e, "deck", 1)                 # サイクリカは置換で山札の下へ
    assert e.s.extra_turns == [0]
    d = drive(e, lambda e, d: e.s.turn == 2 and d["kind"] == "main")
    assert e.s.active == 0 and e.s.result is None             # 追加ターンはまだ負けていない
    drive(e, lambda e, d: e.s.result is not None)
    assert e.s.result["winner"] == 1 and e.s.turn == 2


def test_hell_slash_looks_at_opponent_deck(rules):
    e = setup(rules, {"hand": ["dm06-057"], "mana": ["dm02-029"] * 8}, {"deck": ["dmex17-w02", "dm01-001"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm06-057")
    d = e.advance()
    assert d["kind"] == "choose_cards" and d["max"] == 3 and d["min"] == 0
    ks = keys(d)
    assert any("dmex17-w02" in k for k in ks)                  # 山札の中身を見て選べる
    e.answer([ks.index(next(k for k in ks if "dmex17-w02" in k)), ks.index(next(k for k in ks if "dm01-001" in k))])
    e.advance()
    assert names(e, "graveyard", 1) == ["dm01-001", "dmex17-w02"]


def test_force_again_reuses_enter_trigger(rules):
    e = setup(rules, {"bz": ["dm01-080"], "hand": ["dm31-025"], "mana": ["dm06-085"] * 4}, filler="dm06-085")
    before = e.s.cards[bz(e, 0, "dm01-080")].gen
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm31-025")
    answer(e, "yes_no", "yes")                                 # 破壊する1体は一意なので選択なし                                 # ハルカスの「出た時」がもう一度
    e.advance()
    assert names(e, "bz", 0) == ["dm01-080"] and e.s.cards[bz(e, 0, "dm01-080")].gen != before
    assert len(e.zlist("hand", 0)) == 1


def test_force_again_on_spell_cyclica_goes_to_deck_bottom(rules):
    """サイクリカは破壊される時に山札の下へ行くので、フォース・アゲインで出し直せない。"""
    e = setup(rules, {"bz": ["dmbd13-010"], "hand": ["dm31-025"], "mana": ["dm06-085"] * 4}, filler="dm06-085")
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm31-025")
    e.advance()
    assert names(e, "bz", 0) == [] and e.zlist("deck", 0)[-1] == next(
        c for c in e.zlist("deck", 0) if e.s.cards[c].defn == "dmbd13-010")


def test_spell_cyclica_recasts_and_returns_spell_to_hand(rules):
    e = setup(rules, {"hand": ["dmbd13-010"], "graveyard": ["dm06-085"], "mana": ["dm06-085"] * 7},
              filler="dm01-080")
    answer(e, "charge", "pass")
    answer(e, "main", "play:dmbd13-010")
    answer(e, "choose_cards", "graveyard:dm06-085:0")
    e.advance()
    assert "dm06-085" in names(e, "hand", 0) and names(e, "graveyard", 0) == []
    assert names(e, "hand", 0).count("dm01-080") == 2          # エナジー・ライトで2枚引いた


def test_cyber_n_world_refills_decks(rules):
    e = setup(rules, {"hand": ["dmr01-s03", "dm01-080"], "graveyard": ["dm01-080"] * 3, "mana": ["dm06-085"] * 6},
              {"hand": ["dm01-001"] * 2, "graveyard": ["dm01-001"] * 4})
    deck0, deck1 = len(e.zlist("deck", 0)), len(e.zlist("deck", 1))
    answer(e, "charge", "pass")
    answer(e, "main", "play:dmr01-s03")
    e.advance()
    drew = int(e.s.active == 1)                                # 相手のターンに移っていれば1枚引いている
    assert len(e.zlist("hand", 0)) == 5 and len(e.zlist("hand", 1)) == 5 + drew
    assert e.zlist("graveyard", 0) == [] and e.zlist("graveyard", 1) == []
    assert len(e.zlist("deck", 0)) == deck0 + 1 + 3 - 5 and len(e.zlist("deck", 1)) == deck1 + 2 + 4 - 5 - drew


def test_streaming_shaper_splits_top_four(rules):
    e = setup(rules, {"hand": ["dm03-011"], "mana": ["dm06-085"] * 3,
                      "deck": ["dm06-110", "dm01-080", "dm02-029", "dm06-085"]}, filler="T001")
    top4 = [e.s.cards[c].defn for c in e.zlist("deck", 0)[:4]]
    assert sorted(top4) == ["dm01-080", "dm02-029", "dm06-085", "dm06-110"]
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm03-011")
    e.advance()
    assert names(e, "hand", 0) == ["dm01-080", "dm06-085"]
    assert names(e, "graveyard", 0) == ["dm02-029", "dm03-011", "dm06-110"]


def test_abayo_shabayo_destroys_itself_and_ghoul_returns(rules):
    """アバヨ・シャバヨで自分（ドラゴン）を破壊 → 墓地のグールジェネレイドが戻る。相手も1体破壊。"""
    e = setup(rules, {"hand": ["dmd19-007"], "graveyard": ["dmex13-002"], "mana": ["dm02-029"] * 4},
              {"bz": ["dm01-080", "dm01-106"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dmd19-007")
    drive(e, lambda e, d: d["kind"] == "attack", pick=yes)
    assert names(e, "bz", 0) == ["dmex13-002"] and names(e, "graveyard", 0) == ["dmd19-007"]
    assert len(e.bz_tops(1)) == 1 and len(e.zlist("graveyard", 1)) == 1


def test_ghoul_does_not_return_for_non_dragon(rules):
    e = setup(rules, {"bz": ["dm01-080"], "hand": ["dm31-025"], "graveyard": ["dmex13-002"],
                      "mana": ["dm06-085"] * 4}, filler="dm06-085")
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm31-025")
    drive(e, lambda e, d: d["kind"] == "attack", pick=yes)
    assert "dmex13-002" in names(e, "graveyard", 0)


def test_mystery_box_excludes_nature(rules):
    e = setup(rules, {"hand": ["dm06-040"], "mana": ["dm06-110"] * 3,
                      "deck": ["dmex17-w02", "dm01-080", "dm06-110"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm06-040")
    d = e.advance()
    ks = keys(d)
    assert d["min"] == 0 and any("dm01-080" in k for k in ks)
    assert not any("dmex17-w02" in k or "dm06-110" in k or "T001" in k for k in ks)   # 自然を含む多色も不可
    e.answer([ks.index(next(k for k in ks if "dm01-080" in k))])
    e.advance()
    assert "dm01-080" in names(e, "mana", 0)


def test_dandy_nasuo_deck_to_mana_to_graveyard(rules):
    e = setup(rules, {"hand": ["dm17-055"], "mana": ["dm06-110"] * 2, "deck": ["dm01-080"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm17-055")
    answer(e, "choose_cards", "deck:dm01-080:0")
    answer(e, "choose_cards", "mana:dm06-110:1")
    e.advance()
    assert "dm01-080" in names(e, "mana", 0) and names(e, "graveyard", 0) == ["dm06-110"]


def test_soul_and_memory_shield_buries_creature(rules):
    e = setup(rules, {"hand": ["dm11-004"], "mana": ["dm16-007", "dm06-085", "dm06-085"]}, {"bz": ["dm01-001"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm11-004")
    e.advance()
    assert e.bz_tops(1) == [] and len(e.zlist("shield", 1)) == 6


def test_life_plan_charger(rules):
    e = setup(rules, {"hand": ["dmr16g-054"], "mana": ["dm06-110"] * 4,
                      "deck": ["dm06-085", "dm01-080", "dm02-029"]}, filler="dm06-085")
    answer(e, "charge", "pass")
    answer(e, "main", "play:dmr16g-054")
    d = e.advance()
    assert keys(d) == ["deck:dm01-080:0"] and d["min"] == 0     # クリーチャーだけ選べる
    e.answer([0])
    d = e.advance()
    assert d["kind"] == "order_cards"                          # 残りの並びを決める（好きな順序で）
    e.answer(list(range(len(d["options"]))))
    e.advance()
    assert names(e, "hand", 0) == ["dm01-080"] and "dmr16g-054" in names(e, "mana", 0)
    assert [e.s.cards[c].defn for c in e.zlist("deck", 0)[-4:]].count("dm02-029") == 1   # 残りは一番下へ


def test_apocalypse_day_needs_six(rules):
    e = setup(rules, {"bz": ["dm01-080"] * 3, "hand": ["dmd24-016"] * 2, "mana": ["dm16-007"] * 12},
              {"bz": ["dm01-001"] * 2})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dmd24-016")
    e.advance()
    assert len(e.bz_tops(0)) == 3                               # 5体なので何もしない
    e2 = setup(rules, {"bz": ["dm01-080"] * 4, "hand": ["dmd24-016"], "mana": ["dm16-007"] * 6},
               {"bz": ["dm01-001"] * 2})
    answer(e2, "charge", "pass")
    answer(e2, "main", "play:dmd24-016")
    e2.advance()
    assert e2.bz_tops(0) == [] and e2.bz_tops(1) == []


def test_bloody_cross_and_lost_charger_mill_both(rules):
    e = setup(rules, {"hand": ["dm36-094", "dm09-014"], "mana": ["dm02-029"] * 4}, {"deck": ["dmex17-w02"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm09-014")
    d = e.advance()
    ks = keys(d)
    e.answer([ks.index(next(k for k in ks if "dmex17-w02" in k))])   # 相手の山札から狙って落とす
    d = e.advance()
    assert names(e, "graveyard", 1) == ["dmex17-w02"] and "dm09-014" in names(e, "mana", 0)
    e.answer([keys(d).index("play:dm36-094")])
    answer(e, "pay_mana", "mana:dm02-029")
    e.advance()
    assert len(e.zlist("graveyard", 0)) == 3 and len(e.zlist("graveyard", 1)) == 3


def test_dimension_gate_and_inferno_sign(rules):
    e = setup(rules, {"hand": ["dm01-110", "dmx24-028"], "graveyard": ["dmex17-w02"],
                      "mana": ["dm06-110"] * 3 + ["dm02-029"] * 5, "deck": ["dm01-001"]}, filler="dm06-085")
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm01-110")
    answer(e, "pay_mana", "mana:dm06-110,dm06-110,dm06-110")   # 山札のクリーチャーは1枚だけなので選択なし
    e.advance()
    assert "dm01-001" in names(e, "hand", 0)
    answer(e, "main", "play:dmx24-028")
    e.advance()
    assert names(e, "bz", 0) == ["dmex17-w02"] and e.s.extra_turns == [0]   # 墓地から出ても「出た時」は誘発


def test_emergency_typhoon_draw_up_to_two(rules):
    e = setup(rules, {"hand": ["dmd08-015"], "mana": ["dm06-085"] * 2}, filler="dm01-080")
    answer(e, "charge", "pass")
    answer(e, "main", "play:dmd08-015")
    answer(e, "yes_no", "yes")
    answer(e, "yes_no", "no")                                  # 1枚だけ引く → 捨てる1枚は一意
    e.advance()
    assert names(e, "hand", 0) == [] and names(e, "graveyard", 0) == ["dm01-080", "dmd08-015"]


def test_evo_charger_lets_the_player_order_cards_on_the_deck(rules):
    """「好きな順序で」: 墓地から2体を山札の上に置く時、order_cards の答えの先頭が一番上になる。"""
    for first in (0, 1):
        e = setup(rules, {"hand": ["dm35-047"], "mana": ["dm01-027"] * 4, "graveyard": ["dm01-001", "dmr01-s03"]}, {})
        answer(e, "charge", "pass")
        answer(e, "main", "play:dm35-047")
        d = e.advance()
        assert d["kind"] == "choose_cards"
        e.answer([0, 1])
        d = e.advance()
        assert d["kind"] == "order_cards" and len(d["options"]) == 2
        e.answer([first, 1 - first])
        e.advance()
        assert e.s.cards[e.zlist("deck", 0)[0]].defn == d["options"][first]["key"].split(":")[1]


def test_emergency_typhoon_twinpact_spell_face(rules):
    """ツインパクト dm26ex2-071 の呪文面は単体版と同じ（2枚まで引いて1枚捨てる）。"""
    e = setup(rules, {"hand": ["dm26ex2-071"], "mana": ["dm06-085"] * 2}, filler="dm01-080")
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm26ex2-071:1")
    answer(e, "yes_no", "yes")
    answer(e, "yes_no", "no")
    e.advance()
    assert names(e, "hand", 0) == [] and names(e, "graveyard", 0) == ["dm01-080", "dm26ex2-071"]


def test_emergency_typhoon_twinpact_creature_draws_on_own_spell(rules):
    """クリーチャー面（氷牙レオポル・ディーネ公）が場にいる間、自分が呪文を唱えると1枚引いてもよい。"""
    e = setup(rules, {"bz": ["dm26ex2-071"], "hand": ["dmd08-015"], "mana": ["dm06-085"] * 2}, filler="dm01-080")
    answer(e, "charge", "pass")
    answer(e, "main", "play:dmd08-015")
    d = e.advance()
    while d is not None and d["kind"] == "yes_no":
        e.answer([0])                                # すべて引く（誘発の1枚＋呪文の2枚）
        d = e.advance()
    assert len(names(e, "hand", 0)) >= 2


def test_remming_twinpact_gets_power_and_double_breaker_when_you_discard(rules):
    """ローレンツ・タイフーン（dmpromoy22-p51 呪文面）で手札を捨てるとレミングが +4000・W・ブレイカー。"""
    e = setup(rules, {"bz": ["dmpromoy22-p51"], "hand": ["dmpromoy22-p51", "dm01-080"], "mana": ["dm06-085"] * 2}, filler="dm01-080")
    base = e.chars(e.s.zones["bz"][0][0])
    assert (base["power"], base["breaks"]) == (2000, 1)
    answer(e, "charge", "pass")
    answer(e, "main", "play:dmpromoy22-p51:1")
    d = e.advance()
    while d is not None and d["kind"] not in ("main", "attack"):
        e.answer([0])
        d = e.advance()
    ch = e.chars(e.s.zones["bz"][0][0])
    assert (ch["power"], ch["breaks"]) == (6000, 2)


def test_bruce_cannot_attack_until_graveyard_has_13_cards(rules):
    few = setup(rules, {"bz": ["dmbd17-009"], "graveyard": ["dm01-080"] * 12})
    many = setup(rules, {"bz": ["dmbd17-009"], "graveyard": ["dm01-080"] * 13})
    cid = lambda e: e.s.zones["bz"][0][0]
    assert "attack_player" in few.chars(cid(few))["deny"]
    assert few.chars(cid(few))["breaks"] == 3
    assert "attack_player" not in many.chars(cid(many))["deny"]


def test_bruce_spell_face_reanimates_cost_3_or_less_creature(rules):
    """呪文面: コスト3以下のクリーチャーを墓地から出す（コスト4以上は選べない）。"""
    e = setup(rules, {"hand": ["dmbd17-009"], "mana": ["T008"] * 3, "graveyard": ["T008", "dm22ex2-021"]}, filler="dm01-080")
    answer(e, "charge", "pass")
    answer(e, "main", "play:dmbd17-009:1")
    d = e.advance()
    while d is not None and d["kind"] not in ("main", "attack"):
        e.answer([0])
        d = e.advance()
    assert names(e, "bz", 0) == ["T008"]
