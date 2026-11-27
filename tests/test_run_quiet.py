import sys

from tools.run_quiet import main, summarize


def test_summarize_context_and_tail():
    lines = [f"l{i}" for i in range(100)]
    lines[50] = "Traceback (most recent call last):"
    s = summarize(lines, 5, 3)
    assert "l45" in s and "l55" in s and "l44" not in s and "l99" in s and "l96" not in s


def test_full_log_kept(tmp_path, capsys):
    log = tmp_path / "x.log"
    rc = main(["--log", str(log), "--", sys.executable, "-c", "print('a\\n'*500); raise SystemExit(3)"])
    assert rc == 3 and len(log.read_text().splitlines()) >= 500
    assert len(capsys.readouterr().out.splitlines()) < 40
