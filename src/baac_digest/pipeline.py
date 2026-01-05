"""Read a BAAC file, validate each line against the data contract, aggregate the valid ones.

Nothing here writes to disk or knows about the CLI: `digest` returns a `Digest` or raises
`InputError` when the file cannot be used at all.
"""

import csv
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from baac_digest.errors import InputError
from baac_digest.model import REQUIRED_COLUMNS, Accident

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Rejection:
    """A line set aside: its number in the file (the header is line 1), Num_Acc, the reason."""

    line: int
    num_acc: str
    errors: str


@dataclass
class Digest:
    source: str
    rows: int = 0
    rejects: list[Rejection] = field(default_factory=list)
    by_month: Counter[str] = field(default_factory=Counter)
    by_hour: Counter[str] = field(default_factory=Counter)
    by_department: Counter[str] = field(default_factory=Counter)

    @property
    def rejected(self) -> int:
        return len(self.rejects)

    @property
    def valid(self) -> int:
        return self.rows - self.rejected

    @property
    def reject_rate(self) -> float:
        return self.rejected / self.rows if self.rows else 0.0


def describe(error: ValidationError) -> str:
    """`lum='7': Input should be less than or equal to 5; …`: the column, the value read (the
    rules on several columns quote their values in their message), one entry per broken rule."""
    parts = []
    for item in error.errors():
        where = ".".join(str(part) for part in item["loc"])
        message = item["msg"].removeprefix("Value error, ")
        parts.append(f"{where}={item['input']!r}: {message}" if where else message)
    return "; ".join(parts)


def digest(path: Path) -> Digest:
    """Validates every line of `path` and aggregates the valid ones (no duplicate rule: the
    contract leaves it to an extension)."""
    if not path.is_file():
        raise InputError(f"{path}: no such file")
    logger.info("reading %s", path)
    result = Digest(source=path.name)
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, delimiter=";")
            header = next(reader, None)
            if header is None:
                raise InputError(f"{path}: empty file, no header")
            missing = [column for column in REQUIRED_COLUMNS if column not in header]
            if missing:
                raise InputError(f"{path}: missing required column(s): {', '.join(missing)}")
            position = header.index("Num_Acc")
            for fields in reader:
                if not fields:
                    continue  # blank line: neither counted nor rejected
                result.rows += 1
                line = reader.line_num
                num_acc = fields[position].strip() if position < len(fields) else ""
                if len(fields) != len(header):
                    reason = f"expected {len(header)} fields, got {len(fields)}"
                    result.rejects.append(Rejection(line, num_acc, reason))
                    continue
                try:
                    accident = Accident.model_validate(dict(zip(header, fields, strict=True)))
                except ValidationError as error:
                    result.rejects.append(Rejection(line, num_acc, describe(error)))
                    continue
                result.by_month[f"{accident.mois:02d}"] += 1
                result.by_hour[accident.hrmn[:2]] += 1
                result.by_department[accident.dep] += 1
    except UnicodeDecodeError as error:
        raise InputError(f"{path}: not valid UTF-8 (byte {error.start}: {error.reason})") from error
    if result.rows == 0:
        raise InputError(f"{path}: no data line after the header")
    logger.info("%d lines read, %d valid, %d rejected", result.rows, result.valid, result.rejected)
    return result
