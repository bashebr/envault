import os
import sys
from pathlib import Path

from github import Auth, Github
from github.GithubException import GithubException
from tenacity import retry, stop_after_attempt, wait_exponential

GIST_FILENAME = "envault.json"
GIST_DESCRIPTION = "envault secrets"


def get_github_client() -> Github:
    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        # Check for local token file
        token_path = Path(".envault_token")
        if token_path.exists():
            token = token_path.read_text().strip()

    if not token:
        print(
            "Error: GITHUB_TOKEN not set and .envault_token file not found.",
            file=sys.stderr,
        )
        sys.exit(1)
    auth = Auth.Token(token)
    return Github(auth=auth)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def sensitive_request(func, *args, **kwargs):
    """Wrapper to apply retry logic"""
    return func(*args, **kwargs)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def create_gist(content: str) -> str:
    """Create a new secret Gist and return its ID."""
    gh = get_github_client()
    user = gh.get_user()

    gist = user.create_gist(
        public=False,
        files={GIST_FILENAME: {"content": content}},
        description=GIST_DESCRIPTION,
    )
    return gist.id


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def update_gist(gist_id: str, content: str) -> None:
    """Update an existing Gist with new content."""
    gh = get_github_client()
    try:
        gist = gh.get_gist(gist_id)
        gist.edit(
            description=GIST_DESCRIPTION,
            files={GIST_FILENAME: {"content": content}},
        )
    except GithubException as e:
        print(f"Error updating Gist: {e}", file=sys.stderr)
        sys.exit(1)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def get_gist_content(gist_id: str) -> str:
    """Fetch content from a Gist."""
    gh = get_github_client()
    try:
        gist = gh.get_gist(gist_id)
        if GIST_FILENAME not in gist.files:
            print(f"Error: Gist {gist_id} does not contain {GIST_FILENAME}", file=sys.stderr)
            sys.exit(1)

        return gist.files[GIST_FILENAME].content
    except GithubException as e:
        print(f"Error fetching Gist: {e}", file=sys.stderr)
        sys.exit(1)
