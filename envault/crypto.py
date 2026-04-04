import base64
import os
import gc
from typing import Dict, Optional

from cryptography.fernet import Fernet
from argon2.low_level import hash_secret_raw, Type

# Constants for Argon2id
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65536  # 64 MiB
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32
ARGON2_SALT_LEN = 16

def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a URL-safe base64-encoded 32-byte key using Argon2id."""
    # Convert passphrase to bytes
    pass_bytes = passphrase.encode('utf-8')
    
    try:
        raw_key = hash_secret_raw(
            secret=pass_bytes,
            salt=salt,
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
            hash_len=ARGON2_HASH_LEN,
            type=Type.ID
        )
        return base64.urlsafe_b64encode(raw_key)
    finally:
        # Best effort memory cleanup for the passphrase bytes
        del pass_bytes
        # Since Python strings are immutable and interned/cached, 
        # true clearing is hard, but we do what we can.
        gc.collect()

def encrypt(data: bytes, passphrase: str) -> Dict[str, str]:
    """
    Encrypts data using a derived key from the passphrase (Argon2id).
    Returns a dictionary containing the base64 encoded salt and ciphertext.
    """
    salt = os.urandom(ARGON2_SALT_LEN)
    key = _derive_key(passphrase, salt)
    
    try:
        f = Fernet(key)
        ciphertext = f.encrypt(data)

        return {
            "salt": base64.urlsafe_b64encode(salt).decode("utf-8"),
            "ciphertext": ciphertext.decode("utf-8"),
            "kdf": "argon2id" # Identify KDF for future compatibility
        }
    finally:
        del key
        gc.collect()


def decrypt(payload: Dict[str, str], passphrase: str) -> bytes:
    """
    Decrypts the payload using the provided passphrase.
    Payload must contain 'salt' and 'ciphertext' fields.
    """
    try:
        salt = base64.urlsafe_b64decode(payload["salt"])
    except Exception:
        raise ValueError("Invalid salt format")

    # Check Key Derivation Function if present, default to PBKDF2 if missing (legacy)
    # But as per roadmap, we are breaking change, so we assume Argon2id or fail if strict.
    # However, to be robust, we could check. For this strict iteration: we enforce Argon2id logic.
    # If the user tries to decrypt old data, it will fail (crypto.InvalidToken or similar)
    # which satisfies the "breaking change" notice.
    
    key = _derive_key(passphrase, salt)
    
    try:
        ciphertext = payload["ciphertext"].encode("utf-8")
        f = Fernet(key)
        return f.decrypt(ciphertext)
    finally:
        del key
        gc.collect()
