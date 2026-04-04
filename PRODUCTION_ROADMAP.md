# Production Roadmap for Envault

This document outlines the steps to take `envault` from an MVP to a robust, production-grade tool.

## 1. Security Hardening

- **Upgrade KDF**: Switch from `PBKDF2HMAC` to **Argon2id**. Argon2 is memory-hard and provides better resistance against GPU/ASIC cracking.
- **Memory Hygiene**: While Python makes true memory scrubbing difficult, we can minimize exposure by explicitly deleting variables containing secrets and calling `gc.collect()`, or using `ctypes` to overwrite buffers where possible.
- **Key Rotation**: Implement a formal `rotate-keys` command that doesn't just change the passphrase but also rotates the underlying encryption keys if we move to a master-key architecture.
- **Audit Logs**: Optionally log push/pull actions (without secrets) to a local secure log for auditability.

## 2. Robustness & Reliability

- **Atomic File Writes**: specificly for `pull`. Write to `.env.tmp` first, fsync, and then rename to `.env`. This prevents corruption if the process crashes during a write.
- **Network Retries**: Use a library like `tenacity` or `urllib3`'s implementation to handle transient network errors (5xx, timeouts) when talking to GitHub.
- **Input Validation**: stricter validation on the `.env` content (e.g., ensuring it looks like a valid env file) before encrypting.

## 3. Feature Enhancements

- **Multiple Environments**: Support scanning for keys like `envault.prod.json` or `envault.staging.json` in the Gist to allow managing multiple environments from one Gist, or support tagging Gists.
- **Interactive Init**: `envault init` to guide the user through setting up the `.envault_token` and initial push.
- **Diffing**: `envault diff` to download the remote secret, decrypt it in memory, and show a diff against the local `.env` (redacted values, just showing keys changed).

## 4. Development & CI/CD

- **Type Checking**: Enforce `mypy --strict` in CI.
- **Linting**: Add `ruff` and `black` to pre-commit hooks.
- **Testing**:
    - **Integration Tests**: A test suite that actually hits a real Gist (using a test user/token) to verify API contract changes.
    - **Property-based Testing**: Use `hypothesis` to test the crypto roundtrip with random byte inputs.
- **Distribution**:
    - Create a Homebrew tap.
    - Sign releases.

## 5. Dependency Management

- **Pinning**: We currently pin `PyNaCl` due to installation issues. For production, we should resolve this by finding the correct compatible set or moving to a pure-python alternative if performance permits (though `nacl` is preferred for security).
- **Vulnerability Scanning**: Automated dependabot or `bandit` scans.
