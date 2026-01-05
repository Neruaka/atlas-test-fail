"""Shared fixtures: a real line of the 2023 file, and small CSV files written on demand."""

import csv
from collections.abc import Callable
from pathlib import Path

import pytest

from baac_digest.model import REQUIRED_COLUMNS

# Line 2 of caract-2023.csv, strings included (quotes removed by the csv module).
REAL_LINE = {
    "Num_Acc": "202300000001",
    "jour": "7",
    "mois": "05",
    "an": "2023",
    "hrmn": "06:00",
    "lum": "1",
    "dep": "75",
    "com": "75101",
    "agg": "2",
    "int": "4",
    "atm": "2",
    "col": "7",
    "adr": "RUE DE RIVOLI",
    "lat": "48,86638600",
    "long": "2,32347100",
}

WriteCsv = Callable[..., Path]


@pytest.fixture
def real_line() -> dict[str, str]:
    return dict(REAL_LINE)


@pytest.fixture
def write_csv(tmp_path: Path) -> WriteCsv:
    """write_csv(rows, name=..., header=...) -> path of a `;` CSV, every field quoted."""

    def write(
        rows: list[dict[str, str]] | list[list[str]],
        name: str = "caract.csv",
        header: tuple[str, ...] = REQUIRED_COLUMNS,
    ) -> Path:
        path = tmp_path / name
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\n")
            writer.writerow(header)
            for row in rows:
                writer.writerow([row[c] for c in header] if isinstance(row, dict) else row)
        return path

    return write
