"""Field-level encryption service using AES-256-GCM."""

import base64
import hashlib
import secrets
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from app.config import settings


class EncryptionError(Exception):
    """Encryption/decryption error."""
    pass


class EncryptionService:
    """
    Field-level encryption using AES-256-GCM with HKDF key derivation.

    Each field gets a unique derived key based on the field name and key version,
    allowing for key rotation without re-encrypting all data.
    """

    # Key derivation info for different field types
    FIELD_KEY_INFO = {
        "email": b"employee-tracker-email-v1",
        "phone": b"employee-tracker-phone-v1",
        "name": b"employee-tracker-name-v1",
        "address": b"employee-tracker-address-v1",
        "description": b"employee-tracker-description-v1",
        "notes": b"employee-tracker-notes-v1",
        "reason": b"employee-tracker-reason-v1",
        "default": b"employee-tracker-default-v1",
    }

    def __init__(self, master_key: Optional[bytes] = None) -> None:
        """
        Initialize encryption service.

        Args:
            master_key: 32-byte master key. If None, uses settings.ENCRYPTION_MASTER_KEY
        """
        if master_key is None:
            master_key = base64.b64decode(settings.ENCRYPTION_MASTER_KEY)
        if len(master_key) != 32:
            raise ValueError("Master key must be 32 bytes")
        self._master_key = master_key
        self._key_cache: dict[str, bytes] = {}

    def _derive_key(self, field_type: str, version: int = 1) -> bytes:
        """
        Derive a field-specific key using HKDF.

        Args:
            field_type: Type of field (email, phone, name, etc.)
            version: Key version for rotation

        Returns:
            32-byte derived key
        """
        cache_key = f"{field_type}:v{version}"
        if cache_key in self._key_cache:
            return self._key_cache[cache_key]

        info = self.FIELD_KEY_INFO.get(field_type, self.FIELD_KEY_INFO["default"])
        versioned_info = info + f":v{version}".encode()

        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=versioned_info,
        )
        derived_key = hkdf.derive(self._master_key)
        self._key_cache[cache_key] = derived_key
        return derived_key

    def encrypt(self, plaintext: str, field_type: str = "default") -> bytes:
        """
        Encrypt a string value.

        Args:
            plaintext: Text to encrypt
            field_type: Field type for key derivation

        Returns:
            Encrypted data as bytes (nonce + ciphertext + tag)
        """
        if not plaintext:
            return b""

        key = self._derive_key(field_type, settings.ENCRYPTION_KEY_VERSION)
        aesgcm = AESGCM(key)

        # Generate random 12-byte nonce
        nonce = secrets.token_bytes(12)

        # Encrypt with associated data (field type for integrity)
        associated_data = field_type.encode()
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), associated_data)

        # Return nonce + ciphertext (tag is appended by AESGCM)
        return nonce + ciphertext

    def decrypt(self, encrypted_data: bytes, field_type: str = "default") -> str:
        """
        Decrypt an encrypted value.

        Args:
            encrypted_data: Encrypted bytes (nonce + ciphertext + tag)
            field_type: Field type for key derivation

        Returns:
            Decrypted plaintext string
        """
        if not encrypted_data:
            return ""

        if len(encrypted_data) < 13:  # Minimum: 12 byte nonce + 1 byte ciphertext
            raise EncryptionError("Invalid encrypted data: too short")

        key = self._derive_key(field_type, settings.ENCRYPTION_KEY_VERSION)
        aesgcm = AESGCM(key)

        # Extract nonce (first 12 bytes) and ciphertext (rest)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

        associated_data = field_type.encode()

        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)
            return plaintext.decode("utf-8")
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")

    def encrypt_bytes(self, data: bytes, field_type: str = "default") -> bytes:
        """Encrypt raw bytes."""
        if not data:
            return b""
        key = self._derive_key(field_type, settings.ENCRYPTION_KEY_VERSION)
        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)
        associated_data = field_type.encode()
        ciphertext = aesgcm.encrypt(nonce, data, associated_data)
        return nonce + ciphertext

    def decrypt_bytes(self, encrypted_data: bytes, field_type: str = "default") -> bytes:
        """Decrypt to raw bytes."""
        if not encrypted_data:
            return b""
        if len(encrypted_data) < 13:
            raise EncryptionError("Invalid encrypted data: too short")
        key = self._derive_key(field_type, settings.ENCRYPTION_KEY_VERSION)
        aesgcm = AESGCM(key)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        associated_data = field_type.encode()
        try:
            return aesgcm.decrypt(nonce, ciphertext, associated_data)
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")

    def rotate_key(self, encrypted_data: bytes, field_type: str, from_version: int, to_version: int) -> bytes:
        """
        Rotate encryption key for a field.

        Args:
            encrypted_data: Currently encrypted data
            field_type: Field type
            from_version: Current key version
            to_version: Target key version

        Returns:
            Re-encrypted data with new key version
        """
        plaintext = self.decrypt(encrypted_data, field_type)
        # Temporarily set version for re-encryption
        old_version = settings.ENCRYPTION_KEY_VERSION
        try:
            settings.ENCRYPTION_KEY_VERSION = to_version
            return self.encrypt(plaintext, field_type)
        finally:
            settings.ENCRYPTION_KEY_VERSION = old_version


# Global encryption service instance
encryption_service = EncryptionService()


def get_encryption_service() -> EncryptionService:
    """Get the global encryption service instance."""
    return encryption_service