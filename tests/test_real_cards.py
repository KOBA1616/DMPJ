"""実カード（data/cards/real.yaml）の動作確認。変換の妥当性を、カードごとの局面で確かめる。"""
import random

from conftest import answer, setup

from dmsim import Engine
from dmsim.engine.play import random_policy, replay, run


def names(e, z, p):
    return sorted(e.s.cards[c].defn for c in e.zlist(z, p))


def keys(d):
    return [o["key"] for o in d["options"]]


def bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def test_real_pool_random_games(rules):
    """実カードだけのランダムなデッキで対戦しても例外が出ず、シード＋ログで再現できる。"""
    ids = [i for i in rules.cards if not i.startswith("T")]
    for seed in range(40):
        rr = random.Random(seed)
        decks = [[rr.choice(ids) for _ in range(40)] for _ in range(2)]
        e = Engine.new_game(rules, decks, seed)
        rng = random.Random(seed)
        run(e, [random_policy(rng), random_policy(rng)])
        assert replay(rules, decks, seed, e.log).s.digest() == e.s.digest()


def test_crystal_lancer_evolves_and_is_unblockable(rules):
    e = setup(rules, {"bz": ["dm01-080"], "hand": ["dm02-024"], "mana": ["dm01-080"] * 6},
              {"bz": ["dm01-001"]}, filler="dm06-085")
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm02-024")
    d = e.advance()
    assert d["kind"] == "attack" and "attack:dm02-024:player" in keys(d)   # 進化は召喚酔いしない
    e.answer([keys(d).index("attack:dm02-024:player")])
    d = e.advance()
    assert d["kind"] == "choose_shields" and d["min"] == 2                 # ブロッカーがいてもブロックされない


def test_charger_goes_to_mana(rules):
    e = setup(rules, {"hand": ["dmd04-005"], "mana": ["dmd04-005"] * 3})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dmd04-005")
    e.advance()
    assert names(e, "mana", 0).count("dmd04-005") == 4 and len(e.zlist("graveyard", 0)) == 2


def test_mother_earth(rules):
    """相手のクリーチャーをマナへ → 相手はそのマナから（枚数以下のコストの）クリーチャーを出す。"""
    e = setup(rules, {"hand": ["dm10-036"], "mana": ["dm06-110"] * 3},
              {"bz": ["dm01-001"], "mana": ["dm01-080", "dm01-106"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm10-036")
    answer(e, "yes_no", "yes")
    d = e.advance()                                   # マナの3枚のうちコスト3以下: ハルカスと青銅
    assert d["kind"] == "choose_cards" and d["player"] == 0
    e.answer([keys(d).index("mana:dm01-080:0")])
    e.advance()
    assert [e.s.cards[c].defn for c in e.bz_tops(1)] == ["dm01-080"] and "dm01-001" in names(e, "mana", 1)


def test_the_clock_skips_rest_of_turn(rules):
    """S・トリガーで出たザ・クロックが、攻撃中の相手のターンを終わらせる。"""
    e = setup(rules, {"bz": ["dm01-080", "dm01-080"]}, {"shield": ["dmr09-021"] * 5})
    answer(e, "attack", "attack:dm01-080:player")
    answer(e, "choose_shields", "shield")
    d = e.advance()
    assert d["kind"] == "declare_strigger"
    e.answer([0])
    d = e.advance()
    assert d["player"] == 1 and e.s.active == 1       # 2体目は攻撃できずに相手のターンへ
    assert [e.s.cards[c].defn for c in e.bz_tops(1)] == ["dmr09-021"]


def test_kiryu_slayer_and_mana_replacement(rules):
    """キリュー・ジルヴェス: スピードアタッカーとスレイヤーを得て、破壊される時はマナへ。"""
    e = setup(rules, {"hand": ["dm25-035"], "mana": ["dm01-027", "dm09-032"] + ["dm06-110"] * 3},
              {"bz": ["dm01-001"]})
    e.s.cards[bz(e, 1, "dm01-001")].tapped = True
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm25-035")
    d = e.advance()
    e.answer([keys(d).index("attack:dm25-035:dm01-001")])
    while (d := e.advance()) and d["player"] == 0 and d["kind"] != "attack":
        e.answer([0])
    assert "dm25-035" in names(e, "mana", 0)          # バトルに負けたがマナへ
    assert "dm01-001" in names(e, "graveyard", 1)     # スレイヤーで相手も破壊


def test_mad_demon_triggers_on_hand_spell(rules):
    e = setup(rules, {"bz": ["dmrp06-006"], "hand": ["dm01-027"], "graveyard": ["dm01-080"],
                      "mana": ["dm01-027"] * 6}, {"bz": ["dm01-106"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm01-027")
    while (d := e.advance())["kind"] != "attack":
        e.answer([0])
    assert "dm01-080" in names(e, "hand", 0) and "dm01-106" in names(e, "graveyard", 1)


def test_heavens_gate(rules):
    e = setup(rules, {"hand": ["dm16-007", "dm01-001", "dm01-001", "dm02-024"], "mana": ["dm16-007"] * 6})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm16-007")
    d = e.advance()
    assert d["kind"] == "choose_cards" and d["max"] == 2 and all("dm01-001" in k for k in keys(d))
    e.answer([0, 1])
    e.advance()
    assert names(e, "bz", 0) == ["dm01-001", "dm01-001"]


def test_bolmeteus_grants_strigger_in_shield(rules):
    e = setup(rules, {"bz": ["dm24ex4-015"], "shield": ["dm24ex4-015"] + ["dm06-085"] * 4})
    sh = next(c for c in e.zlist("shield", 0) if e.s.cards[c].defn == "dm24ex4-015")
    assert e.permits(sh, "s_trigger")
    other = next(c for c in e.zlist("shield", 0) if e.s.cards[c].defn == "dm06-085")
    assert not e.permits(other, "s_trigger")
    assert e.permits(bz(e, 0, "dm24ex4-015"), "attack_summoning_sick")   # 自分自身にもスピードアタッカー


def test_infinite_palm_untaps_after_win(rules):
    e = setup(rules, {"bz": ["dm01-001"], "hand": ["dm09-032"], "mana": ["dm25-035"]},
              {"bz": ["dm01-080", "dm01-080"]})
    for c in e.bz_tops(1):
        e.s.cards[c].tapped = True
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm09-032")
    d = e.advance()
    # グラン・ギューレはプレイヤーを攻撃できないが、タップしたクリーチャーは攻撃できる
    assert set(keys(d)) == {"attack:dm01-001:dm01-080", "pass"}
    e.answer([0])
    d = e.advance()
    assert d["kind"] == "attack" and "attack:dm01-001:dm01-080" in keys(d)   # 勝ってアンタップ → もう一度


def _finish(e, d):
    while d is not None and d["kind"] not in ("attack", "main"):
        e.answer(list(range(d["max"])) if d["kind"] == "choose_cards" else [0])
        d = e.advance()
    return d


def test_hydro_commune_bounces_same_race_then_up_to_that_many_opp(rules):
    e = setup(rules, {"bz": ["dm01-001", "dm01-001", "dm01-080"], "hand": ["dmx11-082"], "mana": ["dm01-080"] * 3},
              {"bz": ["dm01-080", "dm01-080", "dm01-080"]}, filler="dm06-085")
    answer(e, "charge", "pass")
    answer(e, "main", "play:dmx11-082")
    d = e.advance()
    assert d["kind"] == "choose_race"
    e.answer([next(i for i, o in enumerate(d["options"]) if o["name"] == "ガーディアン")])
    _finish(e, e.advance())
    assert [n for n in names(e, "hand", 0) if n == "dm01-001"] == ["dm01-001"] * 2 
    assert [e.s.cards[c].defn for c in e.bz_tops(0)] == ["dm01-080"]
    assert len(e.bz_tops(1)) == 1                            # 相手は2体戻る


def test_rebirth_switch_puts_cheaper_creature_from_hand(rules):
    e = setup(rules, {"bz": ["dm01-001"], "hand": ["dm23ex2-cho018", "dm01-080"], "mana": ["dm01-080"] * 5},
              filler="dm06-085")
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm23ex2-cho018")
    d = e.advance()
    while d["kind"] == "yes_no":                              # 出してもよい（コスト6 → 3 のアクア・ハルカス）
        e.answer([0])
        d = e.advance()
    assert [e.s.cards[c].defn for c in e.bz_tops(0)] == ["dm01-080"] and "dm01-001" in names(e, "hand", 0)


def test_olive_oil_returns_graveyard_to_deck(rules):
    e = setup(rules, {"hand": ["dmd24-024"], "mana": ["dm01-080"] * 5, "graveyard": ["dm31-025", "dm31-025"]}, filler="dm06-085")
    answer(e, "charge", "pass")
    answer(e, "main", "play:dmd24-024")
    d = e.advance()
    assert d is not None
    _finish(e, d)
    assert names(e, "graveyard", 0) == [] and names(e, "bz", 0) == ["dmd24-024"]


def test_races_are_split_by_slash_into_single_races():
    from dmsim.cards.defs import split_races
    assert split_races(["デーモン・コマンド/スチーム・ナイト/フュージョナー"]) == ["デーモン・コマンド", "スチーム・ナイト", "フュージョナー"]
    assert split_races(["オラクル", "グレートメカオー"]) == ["オラクル", "グレートメカオー"]


def test_aleftina_wins_when_ten_or_more_shields_and_not_with_nine(rules):
    for n, won in ((9, False), (10, True)):
        e = setup(rules, {"bz": ["dmx12b-031"], "shield": ["dm06-085"] * n}, filler="dm06-085")
        e.advance()
        assert (e.s.result is not None and e.s.result["winner"] == 0) == won, n



def test_aleftina_costs_one_more_per_own_shield_while_in_hand(rules):
    from dmsim.engine import scenario
    for shields, mana, playable in ((0, 4, True), (3, 6, False), (3, 7, True)):
        spec = {"p0": {"hand": ["dmx12b-031"], "mana": ["dm16-007"] * mana, "shield": ["dm06-085"] * shields}, "p1": {}, "filler": "dm06-085"}
        e = scenario.build(rules, spec)
        d = e.advance()
        e.answer([next(i for i, o in enumerate(d["options"]) if o["key"] == "pass")])   # マナはチャージしない（手札のアレフティナのコストだけ見る）
        d = e.advance()
        can = d["kind"] == "main" and any(o["key"].startswith("play:dmx12b-031") for o in d["options"])   # 払えないなら main は出ない
        assert can == playable, (shields, mana)
