from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from envault_gist.gist import _parse_github_token_value, create_gist, update_gist


def test_parse_github_token_value_raw():
    assert _parse_github_token_value("ghp_abc123") == "ghp_abc123"
    assert _parse_github_token_value("github_pat_abc123") == "github_pat_abc123"


def test_parse_github_token_value_env_line():
    assert _parse_github_token_value("GITHUB_TOKEN=ghp_abc123") == "ghp_abc123"
    assert _parse_github_token_value('GITHUB_TOKEN="ghp_abc123"') == "ghp_abc123"


@patch("envault_gist.gist.get_github_client")
def test_create_gist_does_not_retry_after_lost_create_response(mock_get_github_client):
    user = MagicMock()
    user.create_gist.side_effect = [
        ConnectionError("lost response after create"),
        SimpleNamespace(id="duplicate"),
    ]
    mock_get_github_client.return_value.get_user.return_value = user

    with pytest.raises(ConnectionError, match="lost response after create"):
        create_gist("payload")

    user.create_gist.assert_called_once()


@patch("envault_gist.gist.get_github_client")
def test_update_gist_retries_transient_errors(mock_get_github_client):
    gist = MagicMock()
    gist.edit.side_effect = [ConnectionError("temporary failure"), None]
    mock_get_github_client.return_value.get_gist.return_value = gist

    update_gist("abc123", "payload")

    assert gist.edit.call_count == 2
