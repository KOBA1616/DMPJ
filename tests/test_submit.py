"""dmsim.discovery.submit（盤面を指定した検証依頼の窓口）。入口局面とデッキの組み立てだけを確かめる（検証そのものは重い）。"""
from dmsim.base.loopspec import LoopSpec
from dmsim.discovery.submit import build_entry
from dmsim.eval import loop_entry


def test_build_entry_writes_loadable_spec(rules, tmp_path):
    core = [{"id": "dm20-013", "role": "破壊", "part": "loop", "copies": 2}, {"id": "dm20-027", "role": "部品"}]
    ep, dp = build_entry(rules, id="t_submit", name="試験", core=core, bz=["dm20-013"], graveyard=["dm20-013"], hand=["dm20-027"], root=tmp_path)
    ls = LoopSpec.from_json((tmp_path / ep).read_text(encoding="utf-8"))
    b = ls.source["board"]["p0"]
    assert b["bz"] == ["dm20-013"] and b["graveyard"] == ["dm20-013"] and "dm20-027" in b["hand"]
    assert len(b["hand"]) == 5 and len(b["shield"]) == 5 and len(b["mana"]) == 5
    assert {p.match["name"] for p in ls.minimal} == {"dm20-013", "dm20-027"}
    assert (tmp_path / dp).exists()
