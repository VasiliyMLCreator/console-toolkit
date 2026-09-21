import os
import subprocess
import sys


def _run(args):
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-m", "toolkit"] + args,
        capture_output=True,
        text=True,
        cwd=".",
        env=env,
    )


def test_help():
    result = _run(["--help"])
    assert result.returncode == 0
    assert "usage" in result.stdout.lower() or "calc" in result.stdout.lower()


def test_calc_ok():
    result = _run(["calc", "2+3*4"])
    assert result.returncode == 0
    assert "14" in result.stdout


def test_calc_error():
    result = _run(["calc", "1/0"])
    assert result.returncode == 2
    assert len(result.stderr.strip()) > 0


def test_convert_ok():
    result = _run(["convert", "1000", "--from", "mm", "--to", "m"])
    assert result.returncode == 0
    assert "1" in result.stdout
