"""The command line: exit codes, files written, messages on stderr."""

import json
from pathlib import Path

from conftest import REAL_LINE, WriteCsv
from typer.testing import CliRunner

from baac_digest import __version__
from baac_digest.cli import app

runner = CliRunner()


def lines(count: int, invalid: int) -> list[dict[str, str]]:
    return [
        REAL_LINE | {"Num_Acc": f"2023{n:08d}", "lum": "7" if n <= invalid else "1"}
        for n in range(1, count + 1)
    ]


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout == f"baac-digest {__version__}\n"


def test_help_lists_the_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "summarize" in result.stdout
    assert "download" in result.stdout


def test_summarize_writes_both_files(tmp_path: Path, write_csv: WriteCsv) -> None:
    out = tmp_path / "out" / "2023"
    result = runner.invoke(app, ["summarize", str(write_csv(lines(4, 0))), "--out", str(out)])
    assert result.exit_code == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["valid"] == 4
    assert summary["by_month"]["05"] == 4
    assert len(summary["by_hour"]) == 24
    assert (out / "rejects.csv").read_bytes() == b"line,num_acc,errors\r\n"


def test_unusable_input_exits_2_without_files(tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = runner.invoke(app, ["summarize", str(tmp_path / "absent.csv"), "--out", str(out)])
    assert result.exit_code == 2
    assert "unusable input" in result.stderr
    assert not out.exists()


def test_max_reject_rate_out_of_range(tmp_path: Path, write_csv: WriteCsv) -> None:
    path = write_csv(lines(1, 0))
    result = runner.invoke(app, ["summarize", str(path), "--max-reject-rate", "1.5"])
    assert result.exit_code == 2


def test_unwritable_out_folder_exits_2(tmp_path: Path, write_csv: WriteCsv) -> None:
    path = write_csv(lines(1, 0))
    blocker = tmp_path / "file"
    blocker.write_text("not a folder", encoding="utf-8")
    result = runner.invoke(app, ["summarize", str(path), "--out", str(blocker)])
    assert result.exit_code == 2
