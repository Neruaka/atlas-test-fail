"""Reading a whole file: counts, file-level rules, unusable inputs."""

from pathlib import Path

import pytest
from conftest import REAL_LINE, WriteCsv

from baac_digest.errors import InputError
from baac_digest.pipeline import digest


def line(number: int, **changes: str) -> dict[str, str]:
    return REAL_LINE | {"Num_Acc": f"2023{number:08d}"} | changes


def test_counts_and_aggregates(write_csv: WriteCsv) -> None:
    path = write_csv([line(1), line(2, hrmn="23:10", dep="94", com="94080"), line(3, lum="7")])
    result = digest(path)
    assert (result.rows, result.valid, result.rejected) == (3, 2, 1)
    assert result.rejects[0].line == 4
    assert result.rejects[0].num_acc == "202300000003"
    assert result.rejects[0].errors == "lum='7': Input should be less than or equal to 5"
    assert result.by_month == {"05": 2}
    assert result.by_hour == {"06": 1, "23": 1}
    assert result.by_department == {"75": 1, "94": 1}


def test_same_num_acc_twice_is_not_a_rule(write_csv: WriteCsv) -> None:
    result = digest(write_csv([line(1), line(1)]))
    assert result.valid == 2


def test_wrong_number_of_fields(write_csv: WriteCsv) -> None:
    short = list(line(1).values())[:-1]
    long = [*line(2).values(), "extra"]
    result = digest(write_csv([short, long, line(3)]))
    assert [rejection.line for rejection in result.rejects] == [2, 3]
    assert result.valid == 1


def test_blank_lines_are_ignored(tmp_path: Path, write_csv: WriteCsv) -> None:
    path = write_csv([line(1)])
    path.write_text(path.read_text(encoding="utf-8") + "\n\n", encoding="utf-8")
    assert digest(path).rows == 1


def test_bom_and_column_order(tmp_path: Path) -> None:
    columns = list(reversed(REAL_LINE))
    text = ";".join(columns) + "\n" + ";".join(REAL_LINE[c] for c in columns) + "\n"
    path = tmp_path / "bom.csv"
    path.write_text("﻿" + text, encoding="utf-8")
    assert digest(path).valid == 1


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"", "empty file"),
        (b"Num_Acc;jour\n", "missing required column"),
        (b"Num_Acc;jour;mois;an;hrmn;lum;dep;com;agg;int;atm;col;adr;lat;long\n", "no data"),
        ("Num_Acc;adr\n1;Église\n".encode("latin-1"), "UTF-8"),
    ],
)
def test_unusable_input(tmp_path: Path, content: bytes, message: str) -> None:
    path = tmp_path / "input.csv"
    path.write_bytes(content)
    with pytest.raises(InputError, match=message):
        digest(path)


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(InputError, match="no such file"):
        digest(tmp_path / "absent.csv")
