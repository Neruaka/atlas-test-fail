"""`python -m baac_digest`: the same application as the `baac-digest` command."""

from baac_digest.cli import app

if __name__ == "__main__":
    app(prog_name="baac-digest")
