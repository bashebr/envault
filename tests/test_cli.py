import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from envault_gist import config, crypto
from envault_gist.cli import app

runner = CliRunner()


@patch("envault_gist.gist.create_gist")
def test_push_command(mock_create_gist, tmp_path):
    mock_create_gist.return_value = "1234567890"

    # We use isolated_filesystem provided by runner
    with runner.isolated_filesystem():
        # Setup env
        Path(".env").write_text("FOO=BAR")

        # Test
        result = runner.invoke(app, ["push"], input="mypassword\nmypassword\n")

        assert result.exit_code == 0
        assert "Success!" in result.stdout
        assert "1234567890" in result.stdout

        # Verify create_gist was called with some JSON content
        mock_create_gist.assert_called_once()
        args, _ = mock_create_gist.call_args
        payload = json.loads(args[0])
        assert "salt" in payload
        assert "ciphertext" in payload
        assert "kdf" in payload

        # The new Gist ID is persisted for later commands
        assert config.get_gist_id() == "1234567890"


@patch("envault_gist.gist.update_gist")
@patch("envault_gist.gist.create_gist")
def test_push_uses_saved_gist_id(mock_create_gist, mock_update_gist):
    with runner.isolated_filesystem():
        Path(".env").write_text("FOO=BAR")
        config.set_gist_id("saved123")

        result = runner.invoke(app, ["push"], input="mypassword\nmypassword\n")

        assert result.exit_code == 0
        assert "Updated Gist" in result.stdout
        assert "saved123" in result.stdout
        mock_update_gist.assert_called_once()
        mock_create_gist.assert_not_called()


@patch("envault_gist.gist.update_gist")
def test_push_gist_id_flag(mock_update_gist):
    with runner.isolated_filesystem():
        Path(".env").write_text("FOO=BAR")

        result = runner.invoke(
            app, ["push", "--gist-id", "flag456"], input="mypassword\nmypassword\n"
        )

        assert result.exit_code == 0
        assert "flag456" in result.stdout
        mock_update_gist.assert_called_once()
        assert config.get_gist_id() == "flag456"


@patch("envault_gist.gist.create_gist")
def test_push_new_forces_create(mock_create_gist):
    mock_create_gist.return_value = "fresh789"
    with runner.isolated_filesystem():
        Path(".env").write_text("FOO=BAR")
        config.set_gist_id("saved123")

        result = runner.invoke(app, ["push", "--new"], input="mypassword\nmypassword\n")

        assert result.exit_code == 0
        assert "fresh789" in result.stdout
        mock_create_gist.assert_called_once()
        assert config.get_gist_id() == "fresh789"


@patch("envault_gist.gist.create_gist")
def test_push_passphrase_from_env(mock_create_gist, monkeypatch):
    mock_create_gist.return_value = "envpass1"
    monkeypatch.setenv("ENVAULT_PASSPHRASE", "from-env")
    with runner.isolated_filesystem():
        Path(".env").write_text("FOO=BAR")

        # No interactive input provided; passphrase comes from the env var
        result = runner.invoke(app, ["push"])

        assert result.exit_code == 0
        mock_create_gist.assert_called_once()


def test_pull_requires_gist_id():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["pull"], input="mypassword\n")
        assert result.exit_code == 1
        assert "No Gist ID" in result.stdout


@patch("envault_gist.gist.get_gist_content")
def test_pull_command(mock_get_content):
    # Mock return from Gist
    payload = crypto.encrypt(b"FOO=BAR", "mypassword")
    mock_get_content.return_value = json.dumps(payload)

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["pull", "--gist-id", "12345"], input="mypassword\n")

        assert result.exit_code == 0
        assert "Success!" in result.stdout

        # Verify .env was written
        assert Path(".env").read_text() == "FOO=BAR"


@patch("envault_gist.gist.get_gist_content")
def test_pull_removes_temp_file_when_restore_fails(mock_get_content, tmp_path, monkeypatch):
    payload = crypto.encrypt(b"SECRET=value", "mypassword")
    mock_get_content.return_value = json.dumps(payload)

    monkeypatch.chdir(tmp_path)
    Path(".env").mkdir()

    result = runner.invoke(app, ["pull", "--gist-id", "12345"], input="mypassword\n")

    assert result.exit_code == 1
    assert not Path(".env.tmp").exists()


@patch("envault_gist.gist.get_gist_content")
def test_diff_command(mock_get_content):
    payload = crypto.encrypt(b"FOO=REMOTE_VAL\nBAR=BAZ", "mypassword")
    mock_get_content.return_value = json.dumps(payload)

    with runner.isolated_filesystem():
        Path(".env").write_text("FOO=LOCAL_VAL\nBAR=BAZ")

        result = runner.invoke(app, ["diff", "--gist-id", "12345"], input="mypassword\n")

        assert result.exit_code == 0
        # Check output contains diff info
        assert "Differences Found" in result.stdout
        assert "+ FOO=***" in result.stdout  # Local different
        assert "- FOO=***" in result.stdout  # Remote different
        # BAR shouldn't appear because it's same
        assert "BAR" not in result.stdout


def test_init_command():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["init"], input="my_token\n")
        assert result.exit_code == 0
        assert (
            ".envault_token found locally" in result.stdout
            or "Saved to .envault_token" in result.stdout
        )
