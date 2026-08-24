import pytest

from envault_gist import crypto


def test_encrypt_decrypt_roundtrip():
    passphrase = "secure_passcode"
    data = b"SECRET_API_KEY=12345"

    payload = crypto.encrypt(data, passphrase)

    assert "salt" in payload
    assert "ciphertext" in payload
    assert payload.get("kdf") == "argon2id"

    decrypted = crypto.decrypt(payload, passphrase)

    assert decrypted == data


def test_decrypt_invalid_passphrase():
    passphrase = "correct_passphrase"
    data = b"secret"
    payload = crypto.encrypt(data, passphrase)

    # Argon2 verification fails
    with pytest.raises(Exception):
        crypto.decrypt(payload, "wrong_passphrase")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"kdf": "pbkdf2", "salt": "a" * 24, "ciphertext": "invalid"},
        {"kdf": "argon2id", "salt": "not base64!", "ciphertext": "invalid"},
        {"kdf": "argon2id", "salt": "YQ==", "ciphertext": "invalid"},
    ],
)
def test_decrypt_rejects_malformed_payload(payload):
    with pytest.raises(ValueError):
        crypto.decrypt(payload, "passphrase")
