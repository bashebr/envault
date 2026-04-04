# AGENTS.md

## Project Overview

Envault is a small Python CLI package for encrypting a local `.env` file and storing the encrypted payload in a private GitHub Gist. The current implementation is intentionally compact: one CLI module coordinates user interaction, one module handles cryptography, and one module handles GitHub Gist access.

The repository language is English in code comments, README text, and supporting docs. Keep new comments and documentation in English.

The current published metadata identifies version `0.1.0` in both `pyproject.toml` and `envault/__init__.py`.

## Repository Layout

- `pyproject.toml`: package metadata, dependencies, script entry point, and Hatchling build backend.
- `uv.lock`: checked-in dependency lockfile.
- `README.md`: user-facing usage and security model summary.
- `PRODUCTION_ROADMAP.md`: future work and hardening ideas. Treat this as roadmap, not as implemented behavior.
- `product-walkthrough.md`: product positioning and workflow description. Also descriptive, not authoritative for implementation details.
- `envault/cli.py`: Typer application and command implementations.
- `envault/crypto.py`: key derivation and encryption/decryption helpers.
- `envault/gist.py`: GitHub authentication and Gist CRUD operations.
- `tests/test_cli.py`: command-level tests using Typer's `CliRunner` and mocks.
- `tests/test_crypto.py`: crypto round-trip and invalid-passphrase tests.
- `.gitignore`: ignores `.env`, `.envault_token`, temporary files, virtualenvs, caches, and build artifacts.

There are no subpackages beyond `envault/`, no Docker files, no GitHub Actions workflow files, no Makefile, and no dedicated lint/type-check config files in the current repository.

## Technology Stack

- Python `>=3.8`
- Packaging: PEP 621 metadata in `pyproject.toml`
- Build backend: `hatchling`
- CLI framework: `typer`
- Terminal output: `rich`
- GitHub API client: `PyGithub`
- Retry/backoff: `tenacity`
- Cryptography: `cryptography.fernet.Fernet`
- Key derivation: `argon2-cffi` low-level Argon2id API

Dependency note: `PyNaCl==1.5.0` is declared in `pyproject.toml`, but the current code does not import or use it.

## Build, Install, and Run

The repository does not define wrapper scripts for development tasks. Use the package metadata directly.

- Preferred environment reproduction: use the checked-in `uv.lock` if you are working with `uv`.
- Standard install path: install the package from the project root so the `envault` console script is created from `project.scripts`.
- Standard build path: use a PEP 517 frontend against the Hatchling backend declared in `pyproject.toml`.
- Standard test runner: `pytest` is the only declared dev dependency.

Concrete commands that match the current project structure:

```bash
# install the package in editable mode
python3 -m pip install -e .

# run the CLI after dependencies are installed
envault --help

# run tests after pytest is installed
python3 -m pytest

# build distributable artifacts with a PEP 517 frontend
python3 -m build
```

If you are using `uv`, sync from `uv.lock` first and run the same tasks inside that environment.

## Runtime Architecture

### CLI Layer

`envault/cli.py` defines a single `typer.Typer` application with these commands:

- `init`: checks for `GITHUB_TOKEN` or `.envault_token`, optionally prompts for a token, and ensures a local `.env` file exists.
- `push`: validates the local `.env`, prompts for a passphrase twice, encrypts the file bytes, serializes the payload to JSON, and creates a private Gist.
- `pull --gist-id <id>`: prompts for a passphrase, fetches the encrypted JSON payload, decrypts it, writes to `.env.tmp`, and atomically replaces `.env`.
- `rotate --gist-id <id>`: fetches and decrypts an existing payload with the current passphrase, then re-encrypts it with a new passphrase and updates the Gist.
- `diff --gist-id <id>`: decrypts the remote payload and compares it against the local `.env` line-by-line, printing only key names with redacted values.

`validate_env_file()` is only used by `push`. It currently enforces a 1 MB maximum file size and rejects non-UTF-8 input.

### Crypto Layer

`envault/crypto.py` is responsible for all encryption and decryption logic.

- `_derive_key()` derives a 32-byte key with Argon2id and base64-url-encodes it for Fernet.
- `encrypt()` generates a random 16-byte salt, derives a key from the passphrase, encrypts the plaintext with Fernet, and returns a JSON-serializable payload with `salt`, `ciphertext`, and `kdf`.
- `decrypt()` expects the same payload shape, re-derives the key, and decrypts the ciphertext.

Current crypto constants:

- Argon2 time cost: `3`
- Argon2 memory cost: `65536` KiB
- Argon2 parallelism: `4`
- Derived key length: `32`
- Salt length: `16`

The implementation makes a best-effort attempt to reduce secret lifetime with `del` and `gc.collect()`, but there is no true secure memory wiping.

### GitHub/Gist Layer

`envault/gist.py` owns authentication and remote storage details.

- Authentication order: `GITHUB_TOKEN` environment variable first, then project-local `.envault_token`.
- Gist filename is always `envault.json`.
- Gist description is always `envault secrets`.
- `create_gist()`, `update_gist()`, and `get_gist_content()` all use Tenacity retry decorators with exponential backoff.

Important behavior detail: this module exits the process with `sys.exit(1)` on missing auth and some GitHub API failures instead of raising domain-specific exceptions.

There is also a `sensitive_request()` helper with a retry decorator that is currently unused.

## Code Organization and Development Conventions

The codebase is flat and module-oriented. There is no service layer, dependency injection, or internal plugin system.

Observed conventions from the current code:

- Keep modules small and purpose-specific.
- Use `pathlib.Path` for filesystem work.
- Use Typer prompts for secrets and required CLI input.
- Use Rich console output for user-visible status and errors.
- Keep docstrings brief and practical.
- Use broad `except Exception` blocks in the CLI layer to convert failures into user-facing messages and `typer.Exit(code=1)`.
- Keep GitHub-specific concerns inside `envault/gist.py` rather than mixing them into the crypto module.

What is not currently enforced in-repo:

- No `ruff` config
- No `black` config
- No `mypy` config
- No pre-commit config
- No CI workflow

The roadmap mentions those tools, but they are not part of the current repository contract.

## Testing Instructions

The test suite is minimal and uses `pytest`.

Current test coverage is limited to:

- Crypto round-trip behavior
- Crypto failure on wrong passphrase
- CLI `push`, `pull`, `diff`, and `init` happy-path behavior

Testing style in the current repo:

- `tests/test_cli.py` uses `typer.testing.CliRunner`
- CLI tests use `runner.isolated_filesystem()` to avoid touching the real working directory
- GitHub operations are mocked with `unittest.mock.patch`
- There are no real network tests and no live GitHub integration tests

Run tests with:

```bash
python3 -m pytest
```

Be aware of the current gaps before relying on the suite:

- No test coverage for `rotate`
- No integration tests against a real GitHub Gist
- No property-based tests
- No regression tests around malformed payloads beyond invalid passphrase handling

## Security Considerations

This project handles secrets directly. Preserve the current threat model when editing it.

- Never log `.env` contents, passphrases, decrypted payloads, or GitHub tokens.
- `.env` and `.envault_token` are intentionally gitignored. Do not remove those ignores.
- `diff` is designed to reveal key names only, not values. Preserve that behavior unless requirements explicitly change.
- `pull` overwrites `.env` in the current working directory. Keep the atomic temp-file replacement behavior intact if you modify that flow.
- `push` currently validates UTF-8 text and rejects files larger than 1 MB before encryption.
- The payload format is a JSON object with `salt`, `ciphertext`, and `kdf`.
- `decrypt()` is written for the current Argon2id payload format. The code comments mention legacy compatibility considerations, but no backward-compatibility path is implemented.

## Deployment and Release Status

There is no deployment pipeline in this repository.

What exists today:

- Python package metadata
- A console-script entry point
- An MIT license
- A lockfile for reproducible dependencies

What does not exist today:

- Release automation
- Artifact signing
- Homebrew packaging
- CI/CD workflows
- Container images

If you need to add release or deployment machinery, treat it as new work. Do not describe it as existing project behavior.
