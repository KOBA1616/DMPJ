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
