"""Write `summary.json` and `rejects.csv` from a `Digest` already computed."""

import csv
import json
import logging
from pathlib import Path

from baac_digest.pipeline import Digest

logger = logging.getLogger(__name__)

SUMMARY_FILE = "summary.json"
REJECTS_FILE = "rejects.csv"


def summary(result: Digest) -> dict[str, object]:
    """The content of summary.json: every month and every hour present, even at 0."""
    return {
        "source": result.source,
        "rows": result.rows,
        "valid": result.valid,
        "rejected": result.rejected,
        "reject_rate": result.reject_rate,
        "by_month": {f"{month:02d}": result.by_month[f"{month:02d}"] for month in range(1, 13)},
        "by_hour": {f"{hour:02d}": result.by_hour[f"{hour:02d}"] for hour in range(24)},
        "by_department": dict(sorted(result.by_department.items())),
    }


def write(result: Digest, out_dir: Path) -> None:
    """Creates `out_dir` (parents included) and writes the two files; nothing else is touched."""
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / SUMMARY_FILE
    content = json.dumps(summary(result), ensure_ascii=False, indent=2)
    summary_path.write_text(content + "\n", encoding="utf-8")
    logger.info("wrote %s", summary_path)
    rejects_path = out_dir / REJECTS_FILE
    with rejects_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["line", "num_acc", "errors"])
        for rejection in result.rejects:
            writer.writerow([rejection.line, rejection.num_acc, rejection.errors])
    logger.info("wrote %s (%d rejected lines)", rejects_path, result.rejected)
