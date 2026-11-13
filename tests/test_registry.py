"""登録簿（dmsim.base.registry）と登録前の検証（dmsim.eval.verify）。"""
import re
from pathlib import Path

import pytest

from dmsim.base import registry
from dmsim.base.registry import Candidate, Evidence, RegistryError
from dmsim.base.store import HoldoutWriteError
from dmsim.eval.verify import verify

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def full_rules():
    import os
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)   # 実カード（converted.yaml 側を含む）
    try:
        return load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old


def _cand(**kw):
    d = dict(id="x", name="X", split="tuning", types=["loop"], win="opp_deck_out",
             core=[{"id": "a", "name": "A", "role": "e"}, {"id": "b", "name": "B", "role": "w"}])
    d.update(kw)
    return Candidate(**d)


def _ev(c, passed=True, issuer=registry.ISSUER):
    return Evidence(c.digest(), passed, [{"name": "ruler", "ok": passed, "detail": ""}], {}, {}, issuer)


def test_record_and_query(tmp_path):
    p = tmp_path / "r.yaml"
    registry.record(_cand(), _ev(_cand()), path=p)
    h = _cand(id="h", split="holdout", types=["lock"], win="lock")
    registry.record(h, _ev(h), path=p)
    f = _cand(id="f", types=["resource"])
    registry.record(f, _ev(f, passed=False), path=p)
    assert [r["id"] for r in registry.query(path=p)] == ["h", "x"]
    assert [r["id"] for r in registry.query(for_tuning=True, path=p)] == ["x"]
    assert [r["id"] for r in registry.query(types="lock", path=p)] == ["h"]
    assert registry.load(p)["rejected"][0]["failed_at"] == "ruler"
    registry.record(_cand(), _ev(_cand(), passed=False), path=p)      # 同じ id は置き換え
    assert [r["id"] for r in registry.query(path=p)] == ["h"]


def test_only_verified_writes(tmp_path):
    p = tmp_path / "r.yaml"
    c = _cand()
    with pytest.raises(RegistryError):
        registry.record(c, _ev(c, issuer="hand"), path=p)
    with pytest.raises(RegistryError):
        registry.record(c, _ev(_cand(name="other")), path=p)
    h = _cand(split="holdout")
    with pytest.raises(HoldoutWriteError):
        registry.record(h, _ev(h), path=p, purpose="tuning")


def test_bad_fields():
    for kw in ({"split": "x"}, {"types": []}, {"types": ["combo"]}, {"win": "x"}, {"lock_mode": "x"}):
        with pytest.raises(RegistryError):
            _cand(**kw)


def test_novelty(tmp_path):
    p = tmp_path / "r.yaml"
    registry.record(_cand(), _ev(_cand()), path=p)
    rel = lambda ids: [n["relation"] for n in registry.novelty(_cand(id="y", core=[{"id": i} for i in ids]), path=p)]
    assert rel(["a", "b"]) == ["same"] and rel(["a", "b", "c"]) == ["superset"]
    assert rel(["a"]) == ["subset"] and rel(["a", "c"]) == ["overlap"] and rel(["z"]) == []


def test_record_called_only_from_verify():
    """登録簿へ書くのは S4 の検証役だけ。"""
    hits = [str(f.relative_to(ROOT)) for f in (ROOT / "dmsim").rglob("*.py")
            if re.search(r"registry\.record\(", f.read_text(encoding="utf-8"))]
    assert hits == ["dmsim/eval/verify.py"]


def test_verify_stops_at_first_failure(full_rules):
    rules = full_rules
    ev = verify(rules, _cand(core=[{"id": None, "name": "無い札"}]))
    assert not ev.passed and ev.failed_at() == "cards" and len(ev.checks) == 1
    ev = verify(rules, _cand(types=["resource"], core=[{"id": "dm25ex3-028"}]))
    assert ev.failed_at() == "type"
    ev = verify(rules, _cand(types=["lock"], lock_mode="active", core=[{"id": "dm25ex3-028"}]))
    assert ev.failed_at() == "entry"          # 能動ロックは setup と policy が要る
    ev = verify(rules, _cand(core=[{"id": "dm25ex3-028"}]))
    assert ev.failed_at() == "entry"


def test_verify_known_akashic_passes(full_rules):
    rules = full_rules
    """既知のアカシック（tuning）は入口局面から検証を通る（2シードに縮めた版）。"""
    c = _cand(id="akashic", entry="data/loops/entry/akashic.json", seeds=[1, 2],
              core=[{"id": "dm23ex2-009"}, {"id": "dm23bd7-035"}])
    ev = verify(rules, c)
    assert ev.passed, ev.checks
    assert [x["name"] for x in ev.checks] == ["cards", "type", "entry", "ruler", "replay"]
    assert ev.measured["stage2"] == "2/2" and ev.version["fingerprint"]


def test_registry_file_matches_candidates():
    """コミット済みの登録簿は候補と同じ指紋（候補を変えたら tools/registry.py で通し直す）。"""
    import yaml
    cands = {c["id"]: Candidate.from_dict(c).digest()
             for c in yaml.safe_load((ROOT / "data/registry/candidates.yaml").read_text(encoding="utf-8"))["candidates"]}
    reg = registry.load()
    rows = reg["entries"] + reg["rejected"]
    assert {r["id"]: r["digest"] for r in rows} == cands
    assert not [r for r in reg["entries"] if any(not c["ok"] for c in r["checks"])]


def test_active_lock_drill(full_rules):
    """能動ロック（ドリル・スコール＋ジョバンニ、holdout）: 与えた方針で相手の山札切れまで勝つ。方針を外すと勝てない。"""
    kw = dict(id="d", split="holdout", types=["lock"], win="lock", lock_mode="active", seeds=[1, 2],
              core=[{"id": "dm16-051"}, {"id": "dm36-015"}], setup="data/registry/setups/drill_lock.json")
    ev = verify(full_rules, _cand(**kw, policy=["charge:T001", "play:dm16-051", "mana:T001", "graveyard:dm16-051"]))
    assert ev.passed, ev.checks
    assert ev.measured["stage2"] == "2/2" and ev.measured["policy"][1] == "play:dm16-051"
    ev = verify(full_rules, _cand(**kw, policy=["charge:T001"]))
    assert ev.failed_at() == "lock"


def test_active_needs_lock_type():
    with pytest.raises(RegistryError):
        _cand(lock_mode="active")
