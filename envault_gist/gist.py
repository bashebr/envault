import os
import sys
from pathlib import Path
from typing import Optional

from github import Auth, Github, InputFileContent
from github.GithubException import GithubException
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

GIST_FILENAME = "envault.json"
GIST_DESCRIPTION = "envault-gist secrets"


def gist_url(gist_id: str) -> str:
    return f"https://gist.github.com/{gist_id}"


def _parse_github_token_value(raw: str) -> str:
    """Accept a raw PAT or a single KEY=VALUE line from a token file."""
    token = raw.strip().strip('"').strip("'")
    if "=" in token and not token.startswith(("ghp_", "github_pat_")):
        _, _, value = token.partition("=")
        if value.strip():
            return value.strip().strip('"').strip("'")
    return token


def _load_github_token() -> Optional[str]:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return _parse_github_token_value(token)

    token_path = Path(".envault_token")
    if token_path.exists():
        raw = token_path.read_text()
        if raw.strip():
            return _parse_github_token_value(raw)

    return None


def get_github_client() -> Github:
    token = _load_github_token()

    if not token:
        print(
            "Error: GITHUB_TOKEN not set and .envault_token file not found.",
            file=sys.stderr,
        )
        sys.exit(1)
    auth = Auth.Token(token)
    return Github(auth=auth)


def _is_retryable_github_error(exc: BaseException) -> bool:
    if isinstance(exc, GithubException):
        if exc.status is None:
            return True
        return exc.status >= 500 or exc.status == 429
    return isinstance(exc, (ConnectionError, TimeoutError))


def _format_github_error(exc: GithubException, action: str) -> str:
    if exc.status == 403:
        return (
            f"GitHub returned 403 Forbidden when trying to {action}. "
            "Your token likely lacks Gist permission. "
            "Classic PAT: enable the 'gist' scope. "
            "Fine-grained PAT: grant Gists read/write under Account permissions. "
            "Then update GITHUB_TOKEN or .envault_token. "
            "https://github.com/settings/tokens"
        )
    if exc.status == 401:
        return (
            f"GitHub authentication failed (401) when trying to {action}. "
            "Check that your token is valid and not expired. "
            ".envault_token should contain the raw PAT (ghp_... or github_pat_...), "
            "not a GITHUB_TOKEN= line unless exported as an environment variable."
        )
    return f"GitHub error when trying to {action}: {exc}"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_is_retryable_github_error),
    reraise=True,
)
def create_gist(content: str) -> str:
    """Create a new secret Gist and return its ID."""
    gh = get_github_client()
    user = gh.get_user()

    try:
        gist = user.create_gist(
            public=False,
            files={GIST_FILENAME: InputFileContent(content)},
            description=GIST_DESCRIPTION,
        )
        return gist.id
    except GithubException as exc:
        raise RuntimeError(_format_github_error(exc, "create a Gist")) from exc


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_is_retryable_github_error),
    reraise=True,
)
def update_gist(gist_id: str, content: str) -> None:
    """Update an existing Gist with new content."""
    gh = get_github_client()
    try:
        gist = gh.get_gist(gist_id)
        gist.edit(
            description=GIST_DESCRIPTION,
            files={GIST_FILENAME: InputFileContent(content)},
        )
    except GithubException as exc:
        raise RuntimeError(_format_github_error(exc, f"update Gist {gist_id}")) from exc


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_is_retryable_github_error),
    reraise=True,
)
def get_gist_content(gist_id: str) -> str:
    """Fetch content from a Gist."""
    gh = get_github_client()
    try:
        gist = gh.get_gist(gist_id)
        if GIST_FILENAME not in gist.files:
            print(f"Error: Gist {gist_id} does not contain {GIST_FILENAME}", file=sys.stderr)
            sys.exit(1)

        return gist.files[GIST_FILENAME].content
    except GithubException as exc:
        print(_format_github_error(exc, f"fetch Gist {gist_id}"), file=sys.stderr)
        sys.exit(1)
