# Envault

[![CI](https://github.com/bashebr/envault/actions/workflows/ci.yml/badge.svg)](https://github.com/bashebr/envault/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/envault)](https://pypi.org/project/envault/)
[![Python](https://img.shields.io/pypi/pyversions/envault)](https://pypi.org/project/envault/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A secure, minimal CLI tool to sync encrypted `.env` files to private GitHub Gists.

## Quickstart

```bash
pip install envault

# Option 1: Env Var
export GITHUB_TOKEN=your_token_here

# Option 2: Local File (Project-scoped)
echo "your_token_here" > .envault_token

envault push
envault pull --gist-id <id>
```

## Commands

### `envault push`
Reads `.env` from the current directory, prompts for a passphrase, encrypts the file, and syncs it to a private GitHub Gist.

### `envault pull`
Fetches an encrypted Gist by ID, decrypts it with your passphrase, and restores the `.env` file locally.

### `envault rotate`
Rotates the passphrase for an existing Gist. Decrypts with the old passphrase and re-encrypts with a new one.

### `envault diff`
Compares your local `.env` with the remote encrypted Gist and shows which keys differ.

### `envault init`
Initializes envault configuration, walking through token setup and `.env` creation.

## Security Model

- **Client-side Encryption**: Files are encrypted locally using Fernet (AES-128-CBC + HMAC-SHA256) before leaving your machine.
- **Key Derivation**: Keys are derived from your passphrase using Argon2id with a random salt.
- **Zero Knowledge**: Passphrases and keys are never stored. GitHub only sees the encrypted payload.
- **Transport Security**: All communication with GitHub is over HTTPS.

## Development

```bash
git clone https://github.com/bashebr/envault.git
cd envault
uv sync
uv run pytest
```

## Non-Goals

- Not a full secrets management platform (like HashiCorp Vault).
- Not a password manager (like 1Password).
- No team management or ACLs (relies on Gist permissions).
- No background daemons or agents.

## License

MIT
