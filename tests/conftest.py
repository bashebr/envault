import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from typer.testing import CliRunner


@contextmanager
def _isolated_filesystem(self, temp_dir=None):
    cwd = os.getcwd()

    try:
        if temp_dir is None:
            with tempfile.TemporaryDirectory() as tmp_dir:
                os.chdir(tmp_dir)
                yield tmp_dir
        else:
            path = Path(temp_dir)
            path.mkdir(parents=True, exist_ok=True)
            os.chdir(path)
            yield str(path)
    finally:
        os.chdir(cwd)


if not hasattr(CliRunner, "isolated_filesystem"):
    CliRunner.isolated_filesystem = _isolated_filesystem
