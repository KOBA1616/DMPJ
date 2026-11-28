"""証明書化して登録へ渡す窓口。部品A（ジャシン帝＋マグナム＋ジャビビルブラッド＋ジャブラッド、墓地ゴルギーニ＋オア:ナテハ）。"""
import pytest

from dmsim.cards.defs import load_rules
from dmsim.discovery import certify as Z

CORE = [{"id": i, "role": "部品", "part": "loop"} for i in ("dm25sd1-001", "dm20-013", "dm26ex1-018", "dm25sd1-003", "dm26ex2-pr004", "dm25rp4-066")]
BOARD = dict(bz=["dm25sd1-001", "dm20-013", "dm26ex1-018", "dm25sd1-003"], graveyard=["dm26ex2-pr004", "dm25rp4-066"])


def test_part_a_certificate(tmp_path, monkeypatch):
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)
    rules = load_rules(only_approved=False)
    monkeypatch.chdir(tmp_path)   # 入口局面のデッキは相対パスで読まれる
    entry, _ = Z.S.build_entry(rules, id="t_cert", name="部品A", core=CORE, root=tmp_path, **BOARD)
    cert = Z.make_certificate(rules, origin="dm25sd1-001", entry_json=entry, root=tmp_path, laps_max=2, max_nodes=800, tries=2, **BOARD)
    print(cert)
    assert cert["kind"] in ("none", "finite", "infinite")
    assert cert["M"]["graveyard"] == sorted(BOARD["graveyard"])


def test_part_a_registers_through_submit(tmp_path, monkeypatch):
    """回帰が見つかれば submit_board 経由で verify.register へ渡り、登録簿（一時の場所）に行が残る。"""
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)
    rules = load_rules(only_approved=False)
    monkeypatch.chdir(tmp_path)
    from dmsim.base import registry
    reg = tmp_path / "registry"
    cert, ev, row = Z.certify_and_submit(rules, id="t_cert2", name="部品A", core=CORE, origin="dm25sd1-001", root=tmp_path,
                                         path=reg, seeds=range(1, 3), **BOARD)
    assert cert["kind"] in ("finite", "infinite")
    assert ev is not None and row is not None and "証明書" in row.get("note", "") + str(row)


def test_certificate_replays_as_stage1_evidence(tmp_path, monkeypatch):
    """証明書の選択列を再生すると、段1の証拠（measured['stage1_cert']）として受け付けられる。壊すと落ちる。"""
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)
    rules = load_rules(only_approved=False)
    monkeypatch.chdir(tmp_path)
    from dmsim.base.loopspec import LoopSpec
    from dmsim.eval.verify import _check_cert
    entry, _ = Z.S.build_entry(rules, id="t_cert3", name="部品A", core=CORE, root=tmp_path, **BOARD)
    cert = Z.make_certificate(rules, origin="dm25sd1-001", entry_json=entry, root=tmp_path, laps_max=2, max_nodes=800, tries=2, **BOARD)
    ls = LoopSpec.from_json((tmp_path / entry).read_text(encoding="utf-8"))
    m: dict = {}
    assert cert["moves"] and _check_cert(rules, ls, cert, m) and m["stage1_cert"]["laps"] == len(cert["moves"])
    bad = dict(cert, moves=[[("attack", ["no-such-key"])]])
    assert not _check_cert(rules, ls, bad, {})
