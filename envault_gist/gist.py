"""GitHub Gist storage operations."""

import os
from pathlib import Path
from typing import Callable, Optional, TypeVar

from github import Auth, Github, InputFileContent
from github.GithubException import GithubException
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

GIST_FILENAME = "envault.json"
GIST_DESCRIPTION = "envault-gist secrets"
_T = TypeVar("_T")


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
        raw = token_path.read_text(encoding="utf-8")
        if raw.strip():
            return _parse_github_token_value(raw)
    return None


def get_github_client() -> Github:
    token = _load_github_token()
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set and .envault_token was not found.")
    return Github(auth=Auth.Token(token))


def _is_retryable_github_error(exc: BaseException) -> bool:
    if isinstance(exc, GithubException):
        return exc.status is None or exc.status >= 500 or exc.status == 429
    return isinstance(exc, (ConnectionError, TimeoutError))


def _format_github_error(exc: GithubException, action: str) -> str:
    if exc.status == 403:
        return (
            f"GitHub returned 403 Forbidden when trying to {action}. "
            "Your token likely lacks Gist permission. Classic PATs need the 'gist' scope; "
            "fine-grained PATs need Gists read/write Account permission. "
            "https://github.com/settings/tokens"
        )
    if exc.status == 401:
        return f"GitHub authentication failed (401) when trying to {action}. Check your token."
    return f"GitHub error when trying to {action}: {exc}"


def _with_github_error(action: str, operation: Callable[[], _T]) -> _T:
    try:
        return operation()
    except GithubException as exc:
        raise RuntimeError(_format_github_error(exc, action)) from exc


def create_gist(content: str) -> str:
    """Create a new secret Gist and return its ID; creation is never retried."""

    def operation() -> str:
        gist = (
            get_github_client()
            .get_user()
            .create_gist(
                public=False,
                files={GIST_FILENAME: InputFileContent(content)},
                description=GIST_DESCRIPTION,
            )
        )
        return gist.id

    return _with_github_error("create a Gist", operation)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_is_retryable_github_error),
    reraise=True,
)
def _update_gist_with_retry(gist_id: str, content: str) -> None:
    gist = get_github_client().get_gist(gist_id)
    gist.edit(description=GIST_DESCRIPTION, files={GIST_FILENAME: InputFileContent(content)})


def update_gist(gist_id: str, content: str) -> None:
    """Update an existing Gist, retrying only transient failures."""
    _with_github_error(f"update Gist {gist_id}", lambda: _update_gist_with_retry(gist_id, content))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_is_retryable_github_error),
    reraise=True,
)
def _get_gist_content_with_retry(gist_id: str) -> str:
    gist = get_github_client().get_gist(gist_id)
    file = gist.files.get(GIST_FILENAME)
    if file is None:
        raise RuntimeError(f"Gist {gist_id} does not contain {GIST_FILENAME}.")
    content = file.content
    if not isinstance(content, str):
        raise RuntimeError(f"Gist {gist_id} contains unreadable {GIST_FILENAME} content.")
    return content


def get_gist_content(gist_id: str) -> str:
    """Fetch Gist content, retrying only transient failures."""
    return _with_github_error(
        f"fetch Gist {gist_id}", lambda: _get_gist_content_with_retry(gist_id)
    )
