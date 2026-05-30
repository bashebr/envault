from typer.testing import CliRunner

from envault_gist import config

runner = CliRunner()


def test_get_gist_id_missing():
    with runner.isolated_filesystem():
        assert config.get_gist_id() is None


def test_set_and_get_gist_id():
    with runner.isolated_filesystem():
        config.set_gist_id("abc123")
        assert config.get_gist_id() == "abc123"


def test_load_config_ignores_invalid_json():
    with runner.isolated_filesystem():
        from pathlib import Path

        Path(config.CONFIG_FILENAME).write_text("{ not valid json")
        assert config.load_config() == {}
        assert config.get_gist_id() is None
