"""
Message content encryption utilities using Fernet (AES-128)
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class MessageEncryption:
    """
    Encrypt and decrypt message content using Fernet (symmetric encryption)
    """

    _cipher = None

    @classmethod
    def _get_cipher(cls):
        """Get or create Fernet cipher instance"""
        if cls._cipher is None:
            # Get encryption key from settings
            encryption_key = getattr(settings, 'MESSAGE_ENCRYPTION_KEY', None)

            if not encryption_key:
                # Generate a key from SECRET_KEY if MESSAGE_ENCRYPTION_KEY not set
                logger.warning("MESSAGE_ENCRYPTION_KEY not set, deriving from SECRET_KEY")
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'real_estate_young_salt',  # Static salt for consistency
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(
                    kdf.derive(settings.SECRET_KEY.encode())
                )
            else:
                # Use provided key
                key = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key

            cls._cipher = Fernet(key)

        return cls._cipher

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """
        Encrypt plaintext message content

        Args:
            plaintext: Original message content

        Returns:
            Encrypted content (base64 encoded)
        """
        if not plaintext:
            return plaintext

        try:
            cipher = cls._get_cipher()
            encrypted_bytes = cipher.encrypt(plaintext.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        """
        Decrypt encrypted message content

        Args:
            encrypted_text: Encrypted content (base64 encoded)

        Returns:
            Decrypted plaintext content
        """
        if not encrypted_text:
            return encrypted_text

        try:
            cipher = cls._get_cipher()
            decrypted_bytes = cipher.decrypt(encrypted_text.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            # If decryption fails, might be unencrypted legacy data
            logger.warning("Failed to decrypt, returning original text (might be legacy unencrypted data)")
            return encrypted_text
