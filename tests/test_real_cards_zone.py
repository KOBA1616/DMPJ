"""ゾーン間移動系の実カード（data/cards/real_zone.yaml）の動作確認。"""
from conftest import answer, setup

DARK = "dm01-027"      # 闇のマナ用（マナ数値1）
NATURE = "dm06-110"
WATER = "dm01-080"
LIGHT = "dm01-001"


def names(e, z, p):
    return sorted(e.s.cards[c].defn for c in e.zlist(z, p))


def keys(d):
    return [o["key"] for o in d["options"]]


def bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def finish(e, p=0):
    """自分の選択が要らなくなるまで 0 番目を選んで進める（攻撃の選択まで）。"""
    while (d := e.advance()) and d["kind"] not in ("attack", "main") and d["player"] == p:
        e.answer([0])
    return d


def test_forass_destroys_entering_creature_and_mills_mana(rules):
    e = setup(rules, {"bz": ["dm20-027"], "hand": [WATER, DARK], "mana": [WATER] * 3})
    answer(e, "charge", f"charge:{DARK}")                 # マナに置いた闇のカードは墓地へ
    e.advance()
    assert DARK not in names(e, "mana", 0) and DARK in names(e, "graveyard", 0)
    answer(e, "main", f"play:{WATER}")
    finish(e)
    assert WATER in names(e, "graveyard", 0) and names(e, "bz", 0) == ["dm20-027"]   # 出したクリーチャーは破壊


def test_vaizas_returns_shield_on_attack(rules):
    e = setup(rules, {"bz": ["dm20-011"]}, {"bz": [LIGHT]})
    answer(e, "attack", "attack:dm20-011:player")
    d = finish(e)
    assert len(e.zlist("shield", 0)) == 4                  # 攻撃時に自分のシールドが1枚手札へ


def test_magnum_punishes_unpaid_summon(rules):
    """マナを払わずに出した側は自分のクリーチャーを破壊する。マナを払って出したなら何も起きない。"""
    e = setup(rules, {"bz": ["dm20-013"], "hand": [WATER], "mana": [WATER] * 3})
    answer(e, "charge", "pass")
    answer(e, "main", f"play:{WATER}")
    d = finish(e)
    assert names(e, "bz", 0) == sorted(["dm20-013", WATER])   # 払って出した: 破壊されない


def test_morse_g_zero_requires_six_creatures(rules):
    e = setup(rules, {"hand": ["dm16-027"], "graveyard": [WATER] * 5})
    answer(e, "charge", "pass")
    d = e.advance()
    assert d["player"] == 1 or "play:dm16-027:free" not in keys(d)    # 5体ではコストなしでは出せない（マナも無い）
    e = setup(rules, {"hand": ["dm16-027"], "graveyard": [WATER] * 6})
    answer(e, "charge", "pass")
    d = e.advance()
    assert d["kind"] == "main" and "play:dm16-027:free" in keys(d)    # 6体でコストなしの選択肢が出る
    e.answer([keys(d).index("play:dm16-027:free")])
    answer(e, "yes_no", "yes")
    d = e.advance()
    assert d["kind"] == "choose_cards"
    e.answer([0])
    finish(e)
    assert "dm16-027" in names(e, "bz", 0) and names(e, "hand", 0).count(WATER) == 1 and not e.zlist("mana", 0)


def test_morse_with_magnum_destroys_own_creature(rules):
    """マグナムが場にいる時、G・ゼロで出すと（マナをタップしていないので）自分のクリーチャーを1体破壊する。"""
    e = setup(rules, {"bz": ["dm20-013"], "hand": ["dm16-027"], "graveyard": [WATER] * 6})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm16-027:free")
    seen = []
    while (d := e.advance()) and d["player"] == 0 and d["kind"] != "attack":
        seen.append((d["kind"], keys(d)))
        e.answer([0])
    destroyed = [x for x in ("dm20-013", "dm16-027") if x in names(e, "graveyard", 0)]
    assert len(destroyed) == 1, (destroyed, seen)      # 自分のクリーチャー（マグナムかモールス）が1体破壊された


def test_mildgarmus_mana_destruction_and_accel(rules):
    e = setup(rules, {"hand": ["dm20-018"], "mana": [NATURE] * 7}, {"mana": [WATER] * 3})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm20-018")
    finish(e)
    assert len(e.zlist("mana", 1)) == 2 and len(e.zlist("graveyard", 1)) == 1
    assert len(e.zlist("mana", 0)) == 8


def test_great_blessing_graveyard_to_mana(rules):
    e = setup(rules, {"hand": ["dm20-020"], "mana": [NATURE] * 4, "graveyard": [WATER] * 4})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm20-020")
    d = e.advance()
    assert d["kind"] == "choose_cards" and d["max"] == 3
    e.answer([0, 1, 2])
    finish(e)
    assert len(e.zlist("mana", 0)) == 7 and names(e, "graveyard", 0).count("dm20-020") == 1


def test_zapping_beans_swaps_opponents_board_and_mana(rules):
    e = setup(rules, {"hand": ["dm20-033"], "mana": [NATURE] * 5}, {"bz": [LIGHT], "mana": [WATER]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm20-033")
    finish(e)
    assert LIGHT in names(e, "mana", 1) and not e.bz_tops(1)        # 相手のクリーチャーはマナへ


def test_zapping_beans_destroyed_gives_opponent_mana_creature(rules):
    """破壊されると、相手は自分のマナから進化ではないクリーチャーを出す（進化は選べない）。"""
    e = setup(rules, {"bz": ["dm20-033"]}, {"mana": [WATER, "dm02-024"]})
    b = bz(e, 0, "dm20-033")
    e._push(e.ev_task({"ev": "move", "subject": e.s.ref(b), "to": "graveyard", "reason": "destroy"}))
    d = e.advance()
    assert d["kind"] == "yes_no" and d["player"] == 1       # 出たアクア・ハルカスの「引いてもよい」
    e.answer([1])
    e.advance()
    assert [e.s.cards[c].defn for c in e.bz_tops(1)] == [WATER] and "dm02-024" in names(e, "mana", 1)


def test_slowly_chain_goes_to_shield_and_trades_for_graveyard(rules):
    e = setup(rules, {"hand": ["dm20-008"], "mana": [LIGHT] * 4})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm20-008")
    d = e.advance()
    assert d["kind"] == "choose_cards"          # 自分のシールド（呪文自身を含む6枚）から1枚を墓地へ
    assert len(d["options"]) == 6
    e.answer([0])
    finish(e)
    assert len(e.zlist("shield", 0)) == 5 and len(e.zlist("graveyard", 0)) == 1


def test_grudge_assembly_cost_limited_by_graveyard(rules):
    e = setup(rules, {"hand": ["dm20-029"], "mana": [DARK] * 4, "graveyard": [WATER] * 3},
              {"bz": ["dm01-001", "dm01-080", "dm01-027"]})
    # 墓地の枚数と同じかそれ以下のコスト（3）: アクア・ハルカス(3)のみ。デーモン・ハンドは呪文なので場にいない
    e2 = setup(rules, {"hand": ["dm20-029"], "mana": [DARK] * 4, "graveyard": [WATER] * 3},
               {"bz": [LIGHT, WATER]})
    answer(e2, "charge", "pass")
    answer(e2, "main", "play:dm20-029")
    finish(e2)
    assert names(e2, "bz", 1) == [LIGHT] and WATER in names(e2, "graveyard", 1)


def test_clocktower_reorders_top3(rules):
    e = setup(rules, {"hand": ["dm20-043"], "mana": [WATER] * 2}, deck_left=[None, None])
    top3 = [e.s.cards[c].defn for c in e.zlist("deck", 0)[:3]]
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm20-043")
    n = len(e.zlist("deck", 0))
    finish(e)
    assert len(e.zlist("deck", 0)) == n - 1 and len(top3) == 3


def test_escort_bounces_own_creature(rules):
    e = setup(rules, {"bz": [LIGHT], "hand": ["dm20-042"], "mana": [WATER] * 4})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm20-042")
    d = e.advance()
    assert d["kind"] == "choose_cards"
    e.answer([keys(d).index(f"bz:{LIGHT}:0")])
    finish(e)
    assert LIGHT in names(e, "hand", 0) and "dm20-042" in names(e, "bz", 0)


def test_linlullaby_both_decks_to_mana_and_l_gate(rules):
    e = setup(rules, {"hand": ["dm23-035"], "mana": [NATURE] * 4}, {"mana": []})
    answer(e, "charge", "pass")
    answer(e, "main", "play:dm23-035")
    finish(e)
    assert len(e.zlist("mana", 0)) == 5 and len(e.zlist("mana", 1)) == 1
