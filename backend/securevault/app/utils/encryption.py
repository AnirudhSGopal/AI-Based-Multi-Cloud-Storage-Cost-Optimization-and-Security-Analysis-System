"""
Encryption utility for cloud provider credentials.

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the `cryptography` package
for symmetric encryption of API keys, secrets, and service-account JSON
before they are stored in the database.

The encryption key is loaded from the CLOUD_ENCRYPTION_KEY env var.
If missing or invalid, a RuntimeError is raised at import time — this
is intentional so the application fails loudly on startup rather than
silently storing credentials in plaintext.
"""
import os
import logging

from cryptography.fernet import Fernet, MultiFernet, InvalidToken

logger = logging.getLogger(__name__)

# ── Load key at module level — fail loud if missing ──────────────────────────

_raw_key = os.getenv("ENCRYPTION_KEY") or os.getenv("CLOUD_ENCRYPTION_KEY")

if not _raw_key:
    raise RuntimeError(
        "ENCRYPTION_KEY environment variable is not set. "
        "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
        "and add it to your .env file."
    )

try:
    _key_list = [k.strip() for k in _raw_key.split(",") if k.strip()]
    if not _key_list:
        raise ValueError("No keys provided in ENCRYPTION_KEY")
    _fernet = MultiFernet([Fernet(k.encode()) for k in _key_list])
except Exception as exc:
    raise RuntimeError(
        "ENCRYPTION_KEY does not contain valid Fernet key(s)"
    ) from exc


# ── Public API ───────────────────────────────────────────────────────────────

def encrypt_credential(plaintext: str) -> str:
    """
    Encrypt a plaintext string (e.g. JSON-serialized credentials) with the primary key.

    Returns a URL-safe base64-encoded ciphertext string suitable for
    storing in a TEXT database column.
    """
    if not plaintext:
        raise ValueError("Cannot encrypt empty string")
    token = _fernet.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_credential(ciphertext: str) -> str:
    """
    Decrypt a ciphertext string produced by encrypt_credential().
    MultiFernet automatically tests against all keys in order.

    Raises cryptography.fernet.InvalidToken if no key matches
    or the data has been tampered with.
    """
    if not ciphertext:
        raise ValueError("Cannot decrypt empty string")
    try:
        plaintext = _fernet.decrypt(ciphertext.encode("utf-8"))
        return plaintext.decode("utf-8")
    except InvalidToken:
        logger.error("Failed to decrypt credential — invalid token or wrong key")
        raise


def rotate_credential(ciphertext: str) -> str:
    """
    Re-encrypt ciphertext with the primary (first) key in MultiFernet while verifying
    with the older key(s). Enables zero-downtime key rotation.
    """
    if not ciphertext:
        raise ValueError("Cannot rotate empty string")
    try:
        rotated = _fernet.rotate(ciphertext.encode("utf-8"))
        return rotated.decode("utf-8")
    except InvalidToken:
        logger.error("Failed to rotate credential — token cannot be decrypted with known keys")
        raise
