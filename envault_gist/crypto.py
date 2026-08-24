"""Authenticated encryption helpers for envault-gist payloads."""

import base64
import binascii
import gc
import os
from typing import Dict, Tuple

from argon2.low_level import Type, hash_secret_raw
from cryptography.fernet import Fernet, InvalidToken

ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65536  # 64 MiB
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32
ARGON2_SALT_LEN = 16
KDF_NAME = "argon2id"


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a URL-safe Fernet key from a passphrase and Argon2id salt."""
    passphrase_bytes = passphrase.encode("utf-8")
    try:
        raw_key = hash_secret_raw(
            secret=passphrase_bytes,
            salt=salt,
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
            hash_len=ARGON2_HASH_LEN,
            type=Type.ID,
        )
        return base64.urlsafe_b64encode(raw_key)
    finally:
        del passphrase_bytes
        gc.collect()


def encrypt(data: bytes, passphrase: str) -> Dict[str, str]:
    """Encrypt bytes into a JSON-serializable, authenticated payload."""
    salt = os.urandom(ARGON2_SALT_LEN)
    key = _derive_key(passphrase, salt)
    try:
        ciphertext = Fernet(key).encrypt(data)
        return {
            "salt": base64.urlsafe_b64encode(salt).decode("ascii"),
            "ciphertext": ciphertext.decode("ascii"),
            "kdf": KDF_NAME,
        }
    finally:
        del key
        gc.collect()


def _decode_payload(payload: Dict[str, str]) -> Tuple[bytes, bytes]:
    """Validate and decode the untrusted serialized encryption payload."""
    if not isinstance(payload, dict) or payload.get("kdf") != KDF_NAME:
        raise ValueError("Unsupported or invalid encrypted payload format.")

    salt_value = payload.get("salt")
    ciphertext_value = payload.get("ciphertext")
    if not isinstance(salt_value, str) or not isinstance(ciphertext_value, str):
        raise ValueError("Invalid encrypted payload format.")

    try:
        salt = base64.b64decode(salt_value.encode("ascii"), altchars=b"-_", validate=True)
        ciphertext = ciphertext_value.encode("ascii")
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise ValueError("Invalid encrypted payload encoding.") from exc

    if len(salt) != ARGON2_SALT_LEN:
        raise ValueError("Invalid encrypted payload salt.")
    return salt, ciphertext


def decrypt(payload: Dict[str, str], passphrase: str) -> bytes:
    """Decrypt a validated Argon2id/Fernet payload.

    Raises ValueError for malformed payloads or an incorrect passphrase.
    """
    salt, ciphertext = _decode_payload(payload)
    key = _derive_key(passphrase, salt)
    try:
        try:
            return Fernet(key).decrypt(ciphertext)
        except (InvalidToken, ValueError) as exc:
            raise ValueError("Unable to decrypt payload with the supplied passphrase.") from exc
    finally:
        del key
        gc.collect()
