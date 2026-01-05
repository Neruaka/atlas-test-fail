"""Business errors, raised deep in the code and turned into exit codes by the CLI only."""


class BaacError(Exception):
    """Base class of the errors baac-digest reports to its user."""


class InputError(BaacError):
    """The input file cannot be used at all (exit code 2)."""


class DownloadError(BaacError):
    """A download was refused: HTTP or network error, or wrong sha256 (exit code 1)."""
