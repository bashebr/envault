import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from typer.testing import CliRunner


@contextmanager
def isolated_filesystem():
    cwd = Path.cwd()
    with TemporaryDirectory() as tmp_dir:
        os.chdir(tmp_dir)
        try:
            yield tmp_dir
        finally:
            os.chdir(cwd)


if not hasattr(CliRunner, "isolated_filesystem"):
    CliRunner.isolated_filesystem = staticmethod(isolated_filesystem)
