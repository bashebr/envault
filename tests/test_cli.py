import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from envault.cli import app
from envault import gist

runner = CliRunner()

@patch("envault.gist.create_gist")
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

@patch("envault.gist.get_gist_content")
def test_pull_command(mock_get_content):
    # Mock return from Gist
    from envault import crypto
    payload = crypto.encrypt(b"FOO=BAR", "mypassword")
    mock_get_content.return_value = json.dumps(payload)
    
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["pull", "--gist-id", "12345"], input="mypassword\n")
        
        assert result.exit_code == 0
        assert "Success!" in result.stdout
        
        # Verify .env was written
        assert Path(".env").read_text() == "FOO=BAR"

@patch("envault.gist.get_gist_content")
def test_diff_command(mock_get_content):
    from envault import crypto
    payload = crypto.encrypt(b"FOO=REMOTE_VAL\nBAR=BAZ", "mypassword")
    mock_get_content.return_value = json.dumps(payload)
    
    with runner.isolated_filesystem():
        Path(".env").write_text("FOO=LOCAL_VAL\nBAR=BAZ")
        
        result = runner.invoke(app, ["diff", "--gist-id", "12345"], input="mypassword\n")
        
        assert result.exit_code == 0
        # Check output contains diff info
        assert "Differences Found" in result.stdout
        assert "+ FOO=***" in result.stdout # Local different
        assert "- FOO=***" in result.stdout # Remote different
        # BAR shouldn't appear because it's same
        assert "BAR" not in result.stdout

def test_init_command():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["init"], input="my_token\n")
        assert result.exit_code == 0
        assert ".envault_token found locally" in result.stdout or "Saved to .envault_token" in result.stdout
