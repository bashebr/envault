# AGENTS.md

> **Inherits from `AGENTS.base.md`** (parent standards). The base file holds the
> project-agnostic engineering rules (core principles, code conventions, SDLC,
> testing, version control, security, documentation). This file adds the
> envault-specific details and states any explicit overrides. On conflict, this
> file wins; anything not restated here defers to the parent.

## Project Overview

envault-gist is a small Python CLI package for encrypting a local `.env` file and storing the encrypted payload in a private GitHub Gist. The current implementation is intentionally compact: one CLI module coordinates user interaction, one module handles cryptography, and one module handles GitHub Gist access.

The repository language is English in code comments, README text, and supporting docs. Keep new comments and documentation in English.

The PyPI distribution name is `envault-gist` (not `envault`, which is taken by an unrelated package). The current published metadata identifies version `0.1.0` in both `pyproject.toml` and `envault_gist/__init__.py`.

## Repository Layout

- `pyproject.toml`: package metadata, dependencies, script entry point, and Hatchling build backend.
- `uv.lock`: checked-in dependency lockfile.
- `README.md`: user-facing usage, security model, and authoritative product description.
- `.github/workflows/ci.yml`: pytest (with coverage) and Ruff on push/PR to `main`.
- `AGENTS.base.md`: parent/base engineering standards this file inherits from.
- `envault_gist/cli.py`: Typer application and command implementations.
- `envault_gist/crypto.py`: key derivation and encryption/decryption helpers.
- `envault_gist/gist.py`: GitHub authentication and Gist CRUD operations.
- `envault_gist/config.py`: project-local `.envault.json` storage for the saved Gist ID.
- `tests/test_cli.py`: command-level tests using Typer's `CliRunner` and mocks.
- `tests/test_crypto.py`: crypto round-trip and invalid-passphrase tests.
- `tests/test_config.py`: `.envault.json` config get/set and invalid-JSON handling.
- `tests/test_gist.py`: GitHub token parsing and Gist-layer tests.
- `.gitignore`: ignores `.env`, `.envault_token`, temporary files, virtualenvs, caches, and build artifacts.

There are no subpackages beyond `envault_gist/`, no Docker files, no Makefile, and no `mypy` or pre-commit configuration. Ruff is configured in `pyproject.toml` under `[tool.ruff]`.

## Technology Stack

- Python `>=3.14`
- Packaging: PEP 621 metadata in `pyproject.toml`
- Build backend: `hatchling`
- CLI framework: `typer`
- Terminal output: `rich`
- GitHub API client: `PyGithub`
- Retry/backoff: `tenacity`
- Cryptography: `cryptography.fernet.Fernet`
- Key derivation: `argon2-cffi` low-level Argon2id API

## Build, Install, and Run

The repository does not define wrapper scripts for development tasks. Use the package metadata directly.

- Preferred environment reproduction: use the checked-in `uv.lock` if you are working with `uv`.
- Standard install path: install the package from the project root so the `envault-gist` console script is created from `project.scripts`.
- Standard build path: use a PEP 517 frontend against the Hatchling backend declared in `pyproject.toml`.
- Dev dependency group (`dependency-groups.dev`): `pytest`, `pytest-cov`, and `ruff`.

Concrete commands that match the current project structure:

```bash
# install the package in editable mode
uv sync

# run the CLI after dependencies are installed
uv run envault-gist --help

# run tests (CI also runs coverage)
uv run pytest

# lint (matches CI)
uv run ruff check .
uv run ruff format --check .

# build distributable artifacts with a PEP 517 frontend
uv run python -m build
```

If you are using `uv`, sync from `uv.lock` first and run the same tasks inside that environment.

## Runtime Architecture

### CLI Layer

`envault_gist/cli.py` defines a single `typer.Typer` application with these commands:

- `init`: checks for `GITHUB_TOKEN` or `.envault_token`, optionally prompts for a token, ensures a local `.env` file exists, and reports any saved Gist ID.
- `push [--gist-id <id>] [--new]`: validates the local `.env`, reads a passphrase (with confirmation), encrypts the file bytes, serializes the payload to JSON, and either creates a new private Gist or updates an existing one. Resolution order for the target Gist: `--gist-id` flag, then saved `.envault.json`; `--new` forces creation. The resulting Gist ID is persisted to `.envault.json`.
- `pull [--gist-id <id>]`: prompts for a passphrase, fetches the encrypted JSON payload, decrypts it, writes to `.env.tmp`, atomically replaces `.env`, and saves the Gist ID.
- `rotate [--gist-id <id>]`: fetches and decrypts an existing payload with the current passphrase, then re-encrypts it with a new passphrase and updates the Gist.
- `diff [--gist-id <id>]`: decrypts the remote payload and compares it against the local `.env` line-by-line, printing only key names with redacted values.

When `--gist-id` is omitted, `pull`/`diff`/`rotate` fall back to the ID saved in `.envault.json` and error out if none is available. The `ENVAULT_PASSPHRASE` environment variable, when set, supplies the passphrase non-interactively and skips the push confirmation prompt.

`validate_env_file()` is only used by `push`. It currently enforces a 1 MB maximum file size and rejects non-UTF-8 input.

### Crypto Layer

`envault_gist/crypto.py` is responsible for all encryption and decryption logic.

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

`envault_gist/gist.py` owns authentication and remote storage details.

- Authentication order: `GITHUB_TOKEN` environment variable first, then project-local `.envault_token`.
- Gist filename is always `envault.json` (legacy name kept for backward compatibility).
- Gist description is `envault-gist secrets`.
- `update_gist()` and `get_gist_content()` use Tenacity retry decorators with exponential backoff. `create_gist()` is intentionally not retried because creating a Gist is not idempotent.

Token loading (`_load_github_token`/`_parse_github_token_value`) accepts a raw PAT or a `KEY=VALUE` line. Retries use a custom `retry_if_exception` predicate so only transient errors (5xx, 429, connection/timeout) are retried; `create_gist` and `update_gist` raise `RuntimeError` with a friendly message (via `_format_github_error`) on `GithubException`. `get_github_client` and `get_gist_content` still `sys.exit(1)` on missing auth / missing file.

## Code Organization and Development Conventions

The generic engineering standards (core principles, code conventions, SDLC, testing, version control, security, documentation) live in `AGENTS.base.md`. This section records only envault-specific conventions, explicit overrides, and how the parent rules are concretely enforced here.

The codebase is flat and module-oriented. There is no service layer, dependency injection, or internal plugin system.

Project-specific conventions:

- Use `pathlib.Path` for filesystem work.
- Use Typer prompts for secrets and required CLI input.
- Use Rich console output for user-visible status and errors.
- Keep GitHub-specific concerns inside `envault_gist/gist.py` rather than mixing them into the crypto module.
- **Overrides parent ("handle errors explicitly / catch narrowly"):** the CLI layer intentionally uses broad `except Exception` blocks to convert any failure into a user-facing message and `typer.Exit(code=1)`. Lower layers (`crypto.py`, `gist.py`) should still catch narrowly.

How parent rules are enforced/instantiated in this repo:

- The parent "no inline imports" rule is machine-enforced by Ruff `PLC0415` (`import-outside-top-level`) and fails CI lint.
- The parent SDLC "verify" step here means running `uv run pytest`, `uv run ruff check .`, and `uv run ruff format --check .`.

What is not currently enforced in-repo:

- No `mypy` config or type-check job in CI
- No `black` config (formatting is Ruff)
- No pre-commit hooks
- No Dependabot or automated security scanning config in-repo

## Testing Instructions

The test suite is minimal and uses `pytest`.

Current test coverage is limited to:

- Crypto round-trip behavior
- Crypto failure on wrong passphrase
- CLI `push` (create, update via saved ID, `--gist-id`, `--new`, `ENVAULT_PASSPHRASE`), `pull`, `diff`, and `init`
- `pull` requiring a Gist ID when none is saved
- `config` get/set/invalid-JSON handling
- GitHub token parsing (`_parse_github_token_value`)

Testing style in the current repo:

- `tests/test_cli.py` uses `typer.testing.CliRunner`
- CLI tests use `runner.isolated_filesystem()` to avoid touching the real working directory
- GitHub operations are mocked with `unittest.mock.patch`
- There are no real network tests and no live GitHub integration tests

Run tests with:

```bash
uv run pytest
```

Be aware of the current gaps before relying on the suite:

- No integration tests against a real GitHub Gist
- No property-based tests
- No property-based or fuzz testing around malformed payloads

Note: `.envault.json` is project-local metadata (the saved Gist ID). It is not secret (the Gist is private and requires auth), so it is intentionally not gitignored and may be committed to let teammates `pull` with only a passphrase.

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

There is no runtime deployment (no server or container). The package is intended for PyPI as `envault-gist` (`uv tool install envault-gist`).

What exists today:

- Python package metadata at v0.1.0
- A console-script entry point (`envault-gist`)
- An MIT license
- A lockfile for reproducible dependencies
- GitHub Actions CI: multi-version pytest with coverage, plus Ruff check and format check

What does not exist today:

- Automated release or publish workflows in this repo
- Signed release artifacts
- Homebrew tap
- Container images

If you add release automation or distribution channels, update this section and the README.
