import pytest

from dmsim.autofix import Knobs, autofix, diagnose


def fake(k: Knobs, n=30):
    """coef が大きいほど board 到達、budget が大きいほど kill が増える疑似測定。"""
    board = [2 if i < min(n, int(k.coef * 0.75)) else None for i in range(n)]
    kill = [3 if (b is not None and i < min(n, k.budget // 10)) else None for i, b in enumerate(board)]
    return {"kill": kill, "board": board, "cards": [1] * n}


def test_diagnose_stages():
    n = 10
    assert diagnose({"kill": [None] * n, "board": [None] * n, "cards": [None] * n}, 4).stage == "cards"
    assert diagnose({"kill": [None] * n, "board": [None] * n, "cards": [1] * n}, 4).stage == "board"
    assert diagnose({"kill": [None] * n, "board": [2] * n, "cards": [1] * n}, 4).stage == "finish"
    assert diagnose({"kill": [3] * n, "board": [2] * n, "cards": [1] * n}, 4).stage == "ok"


def test_autofix_improves_and_logs(tmp_path):
    led = tmp_path / "l.jsonl"
    k, hist = autofix(fake, Knobs(coef=10, budget=100), rounds=6, ledger=str(led))
    assert k.coef > 10 or k.budget > 100
    assert any(t["verdict"] == "accept" for h in hist for t in h.get("tries", []))
    assert led.read_text().count("\n") == len(hist)


def test_guards():
    with pytest.raises(ValueError):
        autofix(fake, Knobs(), combo={"split": "holdout"})
    _, hist = autofix(fake, Knobs(coef=10), unverified_deck=True)
    assert all(t["verdict"] != "accept" for h in hist for t in h.get("tries", []))
    cards_only = lambda k: {"kill": [None] * 10, "board": [None] * 10, "cards": [None] * 10}
    k, hist = autofix(cards_only, Knobs())
    assert k == Knobs() and "deck_hint" in hist[0]


def test_add_parts_proposer():
    import random

    from dmsim import deckplan as D
    from dmsim.deckplan import change as C
    p = D.load("data/deckplans/mono_red_beatdown_v0.yaml")
    chs = C.PROPOSERS["add_parts"](p, random.Random(0), ["PARTX"], n=2)
    assert chs and all(c.ops[1] == ("PARTX", 1) for c in chs)
    assert C.apply(p, chs[0]).size() == 40


def test_finish_stage_proposes_finish_bundle_first():
    from dmsim.autofix.loop import propose
    c = propose("finish", Knobs())
    assert c[0][0].finish_mult == 1.0 and "締めの束" in c[0][1]
    assert propose("finish", Knobs(finish_mult=1.0))[0][0].finish_mult == 2.0
    assert all(k.finish_mult <= 8 for k, _ in propose("finish", Knobs(finish_mult=8.0)))


def test_batch_skips_holdout_and_unknown():
    from dmsim.autofix import run_targets
    combos = {"a": {"split": "tuning"}, "h": {"split": "holdout"}}
    r = run_targets([{"combo": "a"}, {"combo": "h"}, {"combo": "zz"}], combos, lambda t: fake, rounds=2)
    assert r[0]["stage"] and "skipped" in r[1] and "skipped" in r[2]


def test_finish_proposes_n_det():
    from dmsim.autofix.loop import propose
    assert any(c.n_det == 8 for c, _ in propose("finish", Knobs()))


def test_store_resumes_and_lookahead(tmp_path):
    from dmsim.autofix import run_targets
    st = tmp_path / "k.yaml"
    run_targets([{"combo": "a"}], {"a": {"split": "tuning"}}, lambda t: fake, rounds=4, store=str(st))
    assert st.exists()
    from dmsim.autofix.loop import propose
    assert any(c.lookahead == 1 for c, _ in propose("finish", Knobs()))


def test_default_board_uses_all_heavy_parts():
    import yaml

    from dmsim.autofix.batch import default_board
    c = {x["id"]: x for x in yaml.safe_load(open("data/known_combos/combos.yaml", encoding="utf-8"))["combos"]}["saga"]
    b = default_board(c)
    assert b["graveyard"] == {"dm22ex2-021": 1, "dmrp03-s03": 1} and b["hand"] == {"dm22ex2-021": 1, "dm22ex1-007": 1}


def test_prep_unused_hint_and_candidate():
    from dmsim.autofix import propose
    n = 10
    m = {"kill": [None] * n, "board": [2] * n, "cards": [1] * n, "prep": [0] * 8 + [1, 1]}
    d = diagnose(m, 4)
    assert d.stage == "finish" and d.hints == ("prep_unused",)
    assert diagnose({**m, "prep": [1] * n}, 4).hints == ()
    assert diagnose({k: v for k, v in m.items() if k != "prep"}, 4).hints == ()      # 測っていなければ出さない
    cands = propose(d.stage, Knobs(), hints=d.hints)
    assert cands[0][0].prep_bonus == 10.0
    assert propose(d.stage, cands[0][0], hints=d.hints)[0][0].prep_bonus == 20.0
    assert all(c.prep_bonus == 0.0 for c, _ in propose(d.stage, Knobs()))


def test_prep_bonus_value(rules):
    from dmsim.engine import scenario
    from dmsim.search.prep import prep_used, with_prep_bonus
    e = scenario.build(rules, {"p0": {"graveyard": ["dmd08-015", "dmd08-015", "dmd08-015", "T001"]}, "p1": {}, "filler": "T001",
                               "seed": 1, "deck_size": 10, "deck_left": None})
    e.advance()
    assert prep_used(e, 0, ["dmd08-015"]) == 3 and prep_used(e, 0, []) == 0
    assert with_prep_bonus(lambda _e, _m: 1.0, ["dmd08-015"], 5.0)(e, 0) == 11.0       # 上限2枚


def test_merge_parts_order():
    from dmsim.autofix.loop import _merge
    assert _merge([{"kill": [1, 2], "board": [3]}, {"kill": [4], "board": [5, 6]}]) == {"kill": [1, 2, 4], "board": [3, 5, 6]}


def test_cards_stage_tries_prep_bonus_and_default_need():
    import yaml

    from dmsim.autofix.batch import default_need
    c = {x["id"]: x for x in yaml.safe_load(open("data/known_combos/combos.yaml", encoding="utf-8"))["combos"]}
    assert set(default_need(c["saga"])) == {"dm22ex2-021", "dmrp03-s03", "dm22ex1-007"}
    assert len(default_need(c["tenmon"])) >= 5                    # leaf_parts が無いコンボは core 全部

    def m(k):
        n = 20
        got = [2 if i < (10 if k.prep_bonus else 2) else None for i in range(n)]
        return {"kill": [None] * n, "board": [None] * n, "cards": got, "prep": [0] * n}
    k, hist = autofix(m, Knobs(), rounds=1)
    assert hist[0]["stage"] == "cards" and hist[0]["tries"][0]["verdict"] == "accept" and k.prep_bonus > 0


def test_ledger_has_combo_for_deck_fix(tmp_path):
    import json

    from dmsim.autofix import Knobs, autofix
    led = tmp_path / "l.jsonl"
    cards_only = lambda k: {"kill": [None] * 10, "board": [None] * 10, "cards": [None] * 10}
    autofix(cards_only, Knobs(), {"id": "saga", "split": "tuning"}, ledger=str(led))
    e = json.loads(led.read_text().splitlines()[0])
    assert e["combo"] == "saga" and e["stage"] == "cards" and e["deck_hint"]
    import sys
    sys.path.insert(0, "tools")
    import deck_fix
    assert deck_fix.cards_stage_decks(str(led)) == {"saga"}


def test_alias_makes_akashic_parts_match_deck():
    import yaml

    from dmsim.autofix.batch import default_need
    from dmsim.eval.measure import load_deck
    c = {x["id"]: x for x in yaml.safe_load(open("data/known_combos/combos.yaml", encoding="utf-8"))["combos"]}["akashic"]
    need = default_need(c)
    assert "dm23ex2-cho005" not in need and "dm23ex2-009" in need
    deck = load_deck("data/decks/akashic.yaml")
    assert all(deck.count(i) >= 1 for i in need)               # 重い部品がデッキに入っている（0枚なら cards が常に未達になる）


def test_stage_value_is_continuous_and_monotone():
    from dmsim.eval.deckeval import stage_value
    assert stage_value(None, None, None, 4) == 0.0
    a = stage_value(None, None, 3, 4)
    b = stage_value(None, None, 1, 4)
    c = stage_value(None, 2, 1, 4)
    d = stage_value(3, 2, 1, 4)
    assert 0 < a < b < c < d <= 3.0                        # 早い・段階が進むほど大きい


def test_budget_allocation_and_order(tmp_path):
    from dmsim.deckplan import budget as B
    hist = {"a": {"sec": 3000, "cands": 40, "coarse_seeds": 30, "complete": False, "last_run": 100.0},
            "b": {"sec": 400, "cands": 40, "coarse_seeds": 30, "complete": True, "last_run": 50.0},
            "c": {"sec": 400, "cands": 40, "coarse_seeds": 30, "complete": True, "last_run": 10.0}}
    assert B.order_targets(["b", "c", "a", "new"], hist) == ["new", "a", "c", "b"]      # 未実行→途中→古い順
    # 重いデッキ(a: 2.5秒/候補/局)は同じ枠なら軽いデッキ(b: 0.33)より小さく配分される
    ca = B.allocate(hist["a"], 1200, 5, 30)
    cb = B.allocate(hist["b"], 1200, 5, 30)
    assert ca[0] * ca[1] <= cb[0] * cb[1] and ca[1] >= 8 and ca[0] >= 3
    assert B.allocate(None, 1e9, 5, 30, probe=0.01) == (5, 30, 40, 2)                                      # 枠が十分なら上限のまま
    heavy = B.allocate(None, 1200, 6, 30, probe=8.5)                                        # 履歴なしでも実測が重ければ予算(深さ)から縮める
    light = B.allocate(None, 1200, 6, 30, probe=0.3)
    assert heavy[0] * heavy[1] < light[0] * light[1] and heavy[2] == light[2] == 40 and heavy[0] >= 3 and heavy[1] >= 8     # 重いほど局数・候補を縮める（予算は据え置き）
    ex = B.allocate(None, 500, 6, 8, probe=5.4, seeds=8, top_k=2)                           # knight_dmc 実測: 再比較（通常予算）が支配的
    assert ex[3] <= 2 and ex[1] == 8 and ex[0] == 3
    h = {}
    B.update(h, "x", {"sec": 100.0, "evaluated": 20, "complete": False}, 5, 12, 1.0)
    assert h["x"]["complete"] is False and h["x"]["cands"] == 20
    B.save_history(tmp_path / "h.yaml", h)
    assert B.load_history(tmp_path / "h.yaml") == h


def test_analytic_p_cards_monotone_and_crn():
    from dmsim.deckplan.analytic import p_cards
    deck = ["A"] * 2 + ["F"] * 38
    more = ["A"] * 4 + ["F"] * 36
    need = {"A": 1}
    assert p_cards(more, need) > p_cards(deck, need) > 0                    # 部品が多いほど揃いやすい
    assert p_cards(deck, need) == p_cards(deck, need)                        # 同じ乱数なので再現する
    assert p_cards(deck, {}) == 0.0
    assert abs(p_cards(deck, need, trials=20000) - (1 - (38 / 40) * (37 / 39) * (36 / 38) * (35 / 37) * (34 / 36) * (33 / 35) * (32 / 34) * (31 / 33) * (30 / 32))) < 0.02


def test_deck_fix_resolve_setup():
    import sys
    sys.path.insert(0, "tools")
    import deck_fix
    from dmsim.cards.defs import load_rules
    r = load_rules()
    sp, o = deck_fix.resolve_setup(r, {"combo": "saga", "deck_setup": "tests/saga_prep_setup.yaml"})
    assert o == "tests/saga_prep_setup.yaml" and "p0" in sp
    sp, o = deck_fix.resolve_setup(r, {"combo": "tenmon"})
    assert o == "LoopSpec自動" and "deck_exact" not in sp
    assert deck_fix.resolve_setup(r, {"combo": "nonexistent_combo"}) == (None, "冷たい開幕")


def test_parts_setup_from_combo_table(rules):
    from dmsim.deckplan.setup import parts_setup
    ids = [i for i in rules.cards if i != "T001" and rules.cards[i].civs][:12]
    key, others = ids[0], ids[1:]
    combo = {"parts": [{"id": key, "role": "core"}]}
    deck = [key] * 4 + others * 3
    sp = parts_setup(rules, combo, deck)
    assert sp["p0"]["hand"][0] == key and len(sp["p0"]["mana"]) == 5 and key not in sp["p0"]["mana"]
    assert parts_setup(rules, combo, ["T001"] * 40) is None


def test_split_remaining():
    from dmsim.deckplan import budget as B
    fix, tune = B.split_remaining(6000, 600)
    assert fix > tune > 0 and fix + tune <= 6000 * B.SAFETY - 600
    assert B.split_remaining(6000, 6000) == (0, 0)
    assert B.split_remaining(6000, 600, want_deck_fix=False)[0] == 0


def test_selfheal_phases(tmp_path):
    from dmsim.autofix import selfheal as S
    h = tmp_path / "health.yaml"
    ok, v = S.run_phase("a", lambda: 5, h, "2026-11-09")
    assert ok and v == 5 and S.render_issue(S.load(h)) is None

    def boom():
        raise ValueError("x")
    for i in range(S.QUARANTINE_AFTER):
        assert S.run_phase("b", boom, h, f"2026-11-1{i}")[0] is False
    st = S.load(h)
    assert st["b"]["consecutive_failures"] == S.QUARANTINE_AFTER and S.quarantined(st, "b") and "ValueError" in S.render_issue(st)
    ran = []
    assert S.run_phase("b", lambda: ran.append(1), h)[0] is False and not ran         # 隔離中は実行しない
    st = S.load(h); st.pop("b"); S.save(h, st)                                          # 直したら消して再開
    assert S.run_phase("b", lambda: 1, h)[0] and S.load(h)["b"]["consecutive_failures"] == 0


def test_run_targets_isolates_failure(tmp_path):
    from dmsim.autofix import Rule, run_targets, selfheal
    combos = {"c1": {"id": "c1", "parts": []}, "c2": {"id": "c2", "parts": []}}

    def mk(t):
        if t["combo"] == "c1":
            raise RuntimeError("boom")
        return lambda k, n=30: {"kill": [None] * n, "board": [None] * n, "cards": [1] * n}
    out = run_targets([{"combo": "c1"}, {"combo": "c2"}], combos, mk, Rule(), 1, None, None, health=str(tmp_path / "h.yaml"))
    assert "selfheal" in out[0]["skipped"] and "final" in out[1]
    assert selfheal.load(tmp_path / "h.yaml")["diagnose:c1"]["consecutive_failures"] == 1


def test_deck_fix_gate_includes_deck_bottleneck(tmp_path):
    import json
    import sys
    sys.path.insert(0, "tools")
    import deck_fix
    led = tmp_path / "l.jsonl"
    rows = [{"combo": "a", "stage": "ok", "bottleneck": "deck", "est_kill": 0.06},
            {"combo": "b", "stage": "ok", "bottleneck": "deck", "est_kill": 0.9},
            {"combo": "c", "stage": "board", "bottleneck": "ai", "est_kill": 0.01}]
    led.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    assert deck_fix.cards_stage_decks(str(led)) == {"a"}


def test_win_stats_records_8_turn_rate_and_fastest(tmp_path, monkeypatch):
    import sys
    sys.path.insert(0, "tools")
    import auto_fix
    from types import SimpleNamespace
    kills = [3, 5, None, 8, 9, None]          # 9 は8ターン超（max_turn=8 では出ないが念のため除外されること）
    mk = lambda t, turns=None: (lambda k: {"kill": kills})
    a = SimpleNamespace(store=str(tmp_path / "none.yaml"))
    out = auto_fix._win_stats(a, [{"combo": "x", "deck": "d"}, {"combo": "h", "deck": "d"}], {"x": {}, "h": {"split": "holdout"}}, mk)
    assert set(out) == {"x"} and out["x"]["win_8t"] == round(3 / 6, 3) and out["x"]["win_4t"] == round(1 / 6, 3) and out["x"]["fastest_turn"] == 3
