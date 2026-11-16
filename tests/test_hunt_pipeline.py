"""部品探索の端から端まで（dmsim/discovery/hunt_pipeline.py）: 陽性対照の自己診断が通り、途中再開で済んだ段を飛ばすこと。"""
import os


def _rules():
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        return load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old


def test_controls_built_from_registry_core(tmp_path):
    from dmsim.discovery import hunt_pipeline as H
    R = H.Run(_rules(), tmp_path, H.Config(), log=lambda m: None)
    cb = dict(R.control_bases())
    assert cb["saga"] is not None and cb["akashic"] is not None
    assert len(cb["akashic"].cards) == 4          # ループ部品2種＋最初の勝ち手段の組（入口と同じ最小の形）


def test_resume_skips_done_stage(tmp_path):
    import json
    from dmsim.discovery import hunt_pipeline as H
    (tmp_path / "check.json").write_text(json.dumps({"controls": [], "ok": True}), encoding="utf-8")
    logs = []
    r = H.run(_rules(), tmp_path, H.Config(stages=("check",)), log=logs.append)
    assert r["ok"] and any("済み" in x for x in logs)


def test_since_limits_pool_to_changed_cards(tmp_path):
    """差分実行: 前回の指紋から変わった札を含む組だけが試し打ちの対象になる。"""
    import json
    from dmsim.discovery import hunt_pipeline as H
    rules = _rules()
    prev, cur = tmp_path / "prev", tmp_path / "cur"
    R0 = H.Run(rules, prev, H.Config(), log=lambda m: None)
    hs = R0.card_hashes()
    ids = sorted(hs)[:4]
    a, b, c, d = ids
    hs[a] = "changed"
    (prev / "card_hashes.json").write_text(json.dumps(hs), encoding="utf-8")
    base = lambda cs: {"cards": cs, "names": cs, "gains": {}, "has_win": False, "unknown": 0, "turn": 4}  # noqa: E731
    cur.mkdir()
    (cur / "collect2.json").write_text(json.dumps({"bases": [base([a, b]), base([c, d])]}), encoding="utf-8")
    R = H.Run(rules, cur, H.Config(since=str(prev)), log=lambda m: None)
    assert R.changed_cards() == {a}
    assert [x.cards for x in R._pool()] == [[a, b]]
    assert H.latest_run(tmp_path, exclude=cur) == str(prev)


def test_fast_heavy_pairs_reads_free_if():
    from dmsim.discovery import triples as X, loop_screen as F
    rules = _rules()
    ids, _ = F.usable_ids(rules)
    r = X.fast_heavy_pairs(rules, X.by_card_of(rules), ids)
    assert "free_if" in set(r["self"].values())
    assert all(rules.cards[h].cost >= 5 and rules.cards[e].cost <= 4 for h, e, _ in r["pairs"][:200])
