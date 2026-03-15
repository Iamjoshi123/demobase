"""Credential encryption service using Fernet symmetric encryption."""

from cryptography.fernet import Fernet, InvalidToken
from app.config import settings
import logging

logger = logging.getLogger(__name__)

_fernet = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.encryption_key
        if key == "placeholder-generate-a-real-key":
            # Auto-generate for dev; log warning
            logger.warning("Using auto-generated encryption key. Set ENCRYPTION_KEY in .env for production.")
            key = Fernet.generate_key().decode()
        try:
            _fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception:
            logger.warning("Invalid ENCRYPTION_KEY, generating ephemeral key.")
            _fernet = Fernet(Fernet.generate_key())
    return _fernet


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string and return base64-encoded ciphertext."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext string."""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt credential - invalid token or wrong key")
        raise ValueError("Decryption failed - check ENCRYPTION_KEY")
