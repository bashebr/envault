import os
from contextlib import contextmanager
from tempfile import TemporaryDirectory

from typer.testing import CliRunner

if not hasattr(CliRunner, "isolated_filesystem"):

    @contextmanager
    def isolated_filesystem(self):
        cwd = os.getcwd()
        with TemporaryDirectory() as path:
            os.chdir(path)
            try:
                yield path
            finally:
                os.chdir(cwd)

    CliRunner.isolated_filesystem = isolated_filesystem
