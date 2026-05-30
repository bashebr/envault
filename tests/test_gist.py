from envault_gist.gist import _parse_github_token_value


def test_parse_github_token_value_raw():
    assert _parse_github_token_value("ghp_abc123") == "ghp_abc123"
    assert _parse_github_token_value("github_pat_abc123") == "github_pat_abc123"


def test_parse_github_token_value_env_line():
    assert _parse_github_token_value("GITHUB_TOKEN=ghp_abc123") == "ghp_abc123"
    assert _parse_github_token_value('GITHUB_TOKEN="ghp_abc123"') == "ghp_abc123"
