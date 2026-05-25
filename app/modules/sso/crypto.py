import base64
import hashlib

from cryptography.fernet import Fernet

from app.settings import Config


def _fernet():
    """
    Build a stable Fernet key from configured SSO secret encryption key.

    For production, set [sso] secret_encryption_key in incidentrelay.conf.
    If this value changes, existing encrypted provider secrets cannot be decrypted.
    """
    raw_key = Config.SSO_SECRET_ENCRYPTION_KEY or Config.SECRET_KEY
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(value: str | None) -> str | None:
    """Encrypt a secret string for database storage."""
    if value in (None, ""):
        return None
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str | None:
    """Decrypt a secret string from database storage."""
    if not value:
        return None
    return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
