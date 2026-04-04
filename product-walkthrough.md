# Envault Product Walkthrough

**Envault** is a secure, developer-friendly CLI tool designed to solve the common headache of sharing `.env` files within small teams or across machines without committing secrets to git.

It leverages strong cryptography (Argon2id + AES) and your existing GitHub Gists infrastructure to serve as a designated encrypted store.

## Key Features

### 1. Robust Security
- **Argon2id Key Derivation**: Uses the winner of the Password Hashing Competition (Argon2) to resist GPU/ASIC brute-force attacks.
- **Client-Side Encryption**: Secrets leave your machine *only* as encrypted blobs.
- **Zero Knowledge**: Passphrases and keys are ephemeral; they exist only in memory during execution.

### 2. Reliability
- **Atomic Writes**: `pull` operations write to a temporary file first, ensuring your `.env` is never corrupted if the process crashes mid-download.
- **Network Resilience**: Built-in retries with exponential backoff handle flaky network connections gracefully.

### 3. Developer UX
- **`envault init`**: Interactive setup wizard to get you started in seconds.
- **`envault diff`**: Safely compare your local environment with the encrypted remote version without exposing values (shows changed keys only).
- **Project-Scoped Config**: Supports `.envault_token` for project-specific GitHub PATs.

## Workflow

1.  **Setup**:
    ```bash
    envault init
    ```
2.  **Push** your secrets:
    ```bash
    envault push
    # Output: Encrypted .env pushed to Gist ID: <gist_id>
    ```
3.  **Share** the `<gist_id>` and passphrase with your team (via a secure channel like 1Password).
4.  **Pull** on another machine:
    ```bash
    envault pull --gist-id <gist_id>
    ```
5.  **Check for Drift**:
    ```bash
    envault diff --gist-id <gist_id>
    ```

## Why Envault?
It fills the gap between "sending .env over Slack" (insecure) and "setting up HashiCorp Vault" (overkill). It's designed to be **boring**—using standard crypto and standard infrastructure (Gists)—so you can trust it.
