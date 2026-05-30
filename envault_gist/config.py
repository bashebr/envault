"""Project-local configuration for envault-gist.

Stores non-secret metadata (currently the Gist ID) in `.envault.json` in the
current working directory so users do not need to pass `--gist-id` on every
command. The Gist is private and still requires GitHub auth to read, so this
file is safe to commit if a team wants `pull` to work with just a passphrase.
"""

import json
from pathlib import Path
from typing import Optional

CONFIG_FILENAME = ".envault.json"


def _config_path() -> Path:
    return Path(CONFIG_FILENAME)


def load_config() -> dict:
    path = _config_path()
    if path.exists():
        try:
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def get_gist_id() -> Optional[str]:
    value = load_config().get("gist_id")
    return value if isinstance(value, str) and value else None


def set_gist_id(gist_id: str) -> None:
    config = load_config()
    config["gist_id"] = gist_id
    _config_path().write_text(json.dumps(config, indent=2) + "\n")
