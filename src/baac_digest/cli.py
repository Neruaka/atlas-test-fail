"""The `baac-digest` command: the only module that knows about exit codes.

0 success; 1 quality gate closed (too many rejected lines) or download refused; 2 unusable input
or invalid usage. Every message goes to stderr, through `logging`.
"""

import logging
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

import typer

from baac_digest import __version__, pipeline, report
from baac_digest import download as downloads
from baac_digest.errors import DownloadError, InputError

logger = logging.getLogger("baac_digest")

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    help="Download, validate and summarise the yearly BAAC road accident file (ONISR).",
)


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"baac-digest {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_print_version,
            is_eager=True,
            help="Print the version and exit.",
        ),
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Log debug details.")] = False,
) -> None:
    """Configures logging once, on stderr, before any command runs."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        force=True,
    )


@app.command()
def summarize(
    csv_path: Annotated[Path, typer.Argument(help="The BAAC « caractéristiques » CSV file.")],
    out: Annotated[
        Path, typer.Option("--out", help="Folder of summary.json and rejects.csv.")
    ] = Path("out"),
    max_reject_rate: Annotated[
        float,
        typer.Option(
            "--max-reject-rate", min=0.0, max=1.0, help="Quality gate: highest rejection rate."
        ),
    ] = 0.01,
) -> None:
    """Validate every line, write summary.json and rejects.csv, close the quality gate."""
    try:
        result = pipeline.digest(csv_path)
    except InputError as error:
        logger.error("unusable input: %s", error)
        raise typer.Exit(code=2) from error
    try:
        report.write(result, out)
    except OSError as error:
        logger.error("cannot write to %s: %s", out, error)
        raise typer.Exit(code=2) from error


@app.command()
def download(
    out: Annotated[Path, typer.Option("--out", help="Where to write the file.")] = Path(
        "data/caract.csv"
    ),
    year: Annotated[int, typer.Option("--year", help="A year of the registry.")] = 2024,
    url: Annotated[str | None, typer.Option("--url", help="Download from this URL.")] = None,
    sha256: Annotated[
        str | None, typer.Option("--sha256", help="Expected sha256 of --url.")
    ] = None,
) -> None:
    """Download the file of a year (or of --url) and check its sha256."""
    if (url is None) != (sha256 is None):
        raise typer.BadParameter("--url and --sha256 go together", param_hint="--url/--sha256")
    if url is not None and sha256 is not None:
        if urlparse(url).scheme not in {"http", "https"}:
            raise typer.BadParameter("only http and https URLs", param_hint="--url")
        source = downloads.Source(url, sha256)
    elif year in downloads.REGISTRY:
        source = downloads.REGISTRY[year]
    else:
        known = ", ".join(str(known) for known in sorted(downloads.REGISTRY))
        raise typer.BadParameter(f"{year} is not in the registry ({known})", param_hint="--year")
    try:
        downloads.fetch(source, out)
    except DownloadError as error:
        logger.error("download refused: %s", error)
        raise typer.Exit(code=1) from error
