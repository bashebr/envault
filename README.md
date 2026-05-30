# envault-gist

[![CI](https://github.com/bashebr/envault/actions/workflows/ci.yml/badge.svg)](https://github.com/bashebr/envault/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/envault-gist)](https://pypi.org/project/envault-gist/)
[![Python](https://img.shields.io/pypi/pyversions/envault-gist)](https://pypi.org/project/envault-gist/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A secure, minimal CLI tool to sync encrypted `.env` files to private GitHub Gists.

> **Note:** The PyPI name `envault` belongs to an unrelated HashiCorp Vault wrapper. This project is published as **`envault-gist`**.

## Why?

It fills the gap between "send the `.env` over Slack" (insecure) and "stand up HashiCorp Vault" (overkill). Your secrets are encrypted **on your machine** with a passphrase, stored in a **private Gist**, and restored on any other machine with the same passphrase. GitHub only ever sees an encrypted blob.

## Install

```bash
# From PyPI (global CLI)
uv tool install envault-gist

# From a clone (editable while developing)
uv tool install -e .

# Straight from GitHub
uv tool install git+https://github.com/bashebr/envault.git
```

After install, the `envault-gist` command is on your PATH. Run `envault-gist --help` to see all commands.

## Mental model

envault-gist is a **sync tool**, not a runtime loader:

1. You keep secrets in a local `.env` (gitignored).
2. `push` encrypts that file and stores it in a private Gist.
3. `pull` restores `.env` on another machine.
4. Your app reads `.env` exactly as before (dotenv, Docker, `uv run`, etc.).

Two things unlock the vault: the **Gist ID** (saved automatically, see below) and the **passphrase** (you share this out of band, e.g. 1Password).

## Authentication

envault-gist needs a GitHub Personal Access Token with **Gist** permission to read/write Gists.

- **Classic PAT:** enable the `gist` scope.
- **Fine-grained PAT:** grant **Gists: Read and write** under Account permissions.

Create one at <https://github.com/settings/tokens>, then provide it via either:

```bash
# Option 1: environment variable (takes precedence)
export GITHUB_TOKEN=ghp_your_token_here

# Option 2: project-local file (raw token, one line)
echo "ghp_your_token_here" > .envault_token
```

> The token file accepts either a raw PAT (`ghp_...` / `github_pat_...`) or a `GITHUB_TOKEN=...` line. Keep the PAT **out of `.env`** — that file gets encrypted and pushed.

## Quickstart

```bash
# 1. In your project, set up auth + an empty .env
envault-gist init

# 2. Edit .env with your secrets, then push (creates a private Gist)
envault-gist push
# → Success! Created Gist: abc123def456
#   https://gist.github.com/abc123def456
#   Saved Gist ID to .envault.json

# 3. On another machine (after cloning the project)
envault-gist pull
# → Success! .env file restored.
```

The Gist ID is saved to **`.envault.json`** after the first push/pull, so subsequent commands don't need `--gist-id`.

## Commands

### `envault-gist init`
Interactive setup. Checks for `GITHUB_TOKEN` / `.envault_token` (prompting to save a token if missing), ensures a local `.env` exists, and reports the saved Gist ID if there is one.

### `envault-gist push`
Encrypts the local `.env` and syncs it to a private Gist.

- With no saved Gist and no flag → **creates** a new Gist and saves its ID to `.envault.json`.
- With a saved Gist ID (or `--gist-id`) → **updates** that Gist in place.

```bash
envault-gist push                      # create or update (auto)
envault-gist push --gist-id abc123     # update a specific Gist
envault-gist push --new                # force-create a new Gist
```

### `envault-gist pull`
Fetches the encrypted Gist, decrypts with your passphrase, and atomically restores `.env` (writes `.env.tmp`, then renames — no partial writes on crash).

```bash
envault-gist pull                      # uses saved Gist ID
envault-gist pull --gist-id abc123     # pull a specific Gist
```

### `envault-gist diff`
Compares your local `.env` with the remote encrypted Gist and prints only the **key names** that differ (values are redacted as `***`).

```bash
envault-gist diff
envault-gist diff --gist-id abc123
```

### `envault-gist rotate`
Re-encrypts an existing Gist under a new passphrase. Decrypts with the current passphrase, prompts for a new one, and updates the Gist.

```bash
envault-gist rotate
envault-gist rotate --gist-id abc123
```

## Using it in a project

### First-time setup (author)

```bash
cd my-app
envault-gist init          # auth + empty .env
# ...edit .env with real secrets...
envault-gist push          # creates Gist, writes .envault.json
```

Share the **passphrase** with teammates via a secure channel (1Password, Bitwarden, etc.).

### Teammates / new machines

Commit `.envault.json` (it only contains the non-secret Gist ID; the Gist is private and still needs auth to read). Then:

```bash
git clone .../my-app && cd my-app
echo "ghp_their_token" > .envault_token   # their own PAT with gist scope
envault-gist pull                          # restores .env from the saved Gist ID
uv run python app.py                       # app reads .env as usual
```

### When secrets change

```bash
# edit .env locally
envault-gist diff          # see which keys changed (names only)
envault-gist push          # updates the same Gist in place
```

## Non-interactive / CI use

Set `ENVAULT_PASSPHRASE` to skip the interactive passphrase prompt (and the confirmation step on push):

```bash
export GITHUB_TOKEN=ghp_...
export ENVAULT_PASSPHRASE='correct horse battery staple'

envault-gist pull --gist-id abc123
```

> Prefer your CI's secret store for both `GITHUB_TOKEN` and `ENVAULT_PASSPHRASE`. Avoid leaving the passphrase in shell history.

## Files at a glance

| File | Purpose | Commit it? |
|------|---------|------------|
| `.env` | Your app secrets (encrypted + synced) | No (gitignored) |
| `.envault_token` | Your GitHub PAT for auth | No (gitignored) |
| `.envault.json` | Saved Gist ID (non-secret metadata) | Optional — handy for teams |
| Gist `envault.json` | Encrypted copy of `.env` on GitHub | n/a (remote) |

## Security model

- **Client-side encryption:** Files are encrypted locally with Fernet (AES-128-CBC + HMAC-SHA256) before leaving your machine.
- **Key derivation:** Keys are derived from your passphrase using Argon2id with a random per-file salt.
- **Zero knowledge:** Passphrases and keys are never stored; GitHub only sees the encrypted payload.
- **Redacted diffs:** `diff` reveals changed key names only, never values.
- **Atomic restores:** `pull` writes to a temp file and renames, so a crash can't corrupt `.env`.
- **Transport security:** All GitHub communication is over HTTPS.

## Development

```bash
git clone https://github.com/bashebr/envault.git
cd envault
uv sync
uv run envault-gist --help
uv run pytest
uv run ruff check .
```

## Non-Goals

- Not a full secrets management platform (like HashiCorp Vault).
- Not a password manager (like 1Password).
- No team management or ACLs (relies on Gist permissions).
- No background daemons or agents.

## License

MIT
