# ─────────────────────────────────────────────────────────────────────────────
# File    : shared/utils/document_encryption.py
# Purpose : JSP-FR-012 Encrypted storage & password/PIN protection utility
# ─────────────────────────────────────────────────────────────────────────────

import os
import hmac
import hashlib
import secrets
from typing import Optional, Tuple
from fastapi import HTTPException, status

MAGIC_HEADER = b"LV360ENC1"
DEFAULT_SYSTEM_KEY = os.getenv("DOCUMENT_ENCRYPTION_KEY", "LV360_SECURE_STORAGE_MASTER_KEY_2026_PROD")


def hash_archive_pin(pin: str) -> str:
    """
    Hashes an archive protection PIN/password using PBKDF2-HMAC-SHA256 with random salt.
    """
    clean_pin = (pin or "").strip()
    if not clean_pin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN or password cannot be empty.",
        )
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", clean_pin.encode("utf-8"), salt, 100_000)
    return f"pbkdf2_sha256$100000${salt.hex()}${key.hex()}"


def verify_archive_pin(pin: str, stored_hash: Optional[str]) -> bool:
    """
    Verifies a PIN against stored PBKDF2 hash using constant-time comparison.
    """
    if not stored_hash or not pin:
        return False
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_key = bytes.fromhex(parts[3])
        actual_key = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual_key, expected_key)
    except Exception:
        return False


def _derive_keys(master_key: str, salt: bytes, user_pin: Optional[str] = None) -> Tuple[bytes, bytes]:
    """
    Derives 32-byte cipher key and 32-byte authentication (HMAC) key.
    Combines system master key and optional user PIN.
    """
    combined_secret = master_key.encode("utf-8")
    if user_pin:
        combined_secret += b"|" + user_pin.strip().encode("utf-8")
    
    key_material = hashlib.pbkdf2_hmac("sha256", combined_secret, salt, 50_000, dklen=64)
    cipher_key = key_material[:32]
    mac_key = key_material[32:]
    return cipher_key, mac_key


def _generate_keystream(cipher_key: bytes, nonce: bytes, length: int) -> bytes:
    """
    Generates deterministic keystream using SHA-256 CTR mode.
    """
    blocks = []
    block_index = 0
    generated = 0
    while generated < length:
        h = hashlib.sha256()
        h.update(cipher_key)
        h.update(nonce)
        h.update(block_index.to_bytes(4, byteorder="big"))
        block = h.digest()
        blocks.append(block)
        generated += len(block)
        block_index += 1
    return b"".join(blocks)[:length]


def encrypt_document_data(data: bytes, user_pin: Optional[str] = None) -> bytes:
    """
    Encrypts raw document bytes using AES-strength authenticated stream cipher (PBKDF2-HMAC-SHA256 CTR).
    Payload format:
      [9 bytes MAGIC_HEADER]
      [16 bytes SALT]
      [16 bytes NONCE]
      [32 bytes HMAC_TAG]
      [N bytes CIPHERTEXT]
    """
    if not data:
        return b""

    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)
    cipher_key, mac_key = _derive_keys(DEFAULT_SYSTEM_KEY, salt, user_pin)

    keystream = _generate_keystream(cipher_key, nonce, len(data))
    # XOR cipher
    ciphertext = bytes(a ^ b for a, b in zip(data, keystream))

    # Authenticate header + salt + nonce + ciphertext
    h = hmac.new(mac_key, MAGIC_HEADER + salt + nonce + ciphertext, hashlib.sha256)
    mac_tag = h.digest()

    return MAGIC_HEADER + salt + nonce + mac_tag + ciphertext


def is_encrypted_document(data: bytes) -> bool:
    """Checks whether bytes begin with the encryption magic header."""
    return data.startswith(MAGIC_HEADER) and len(data) >= (len(MAGIC_HEADER) + 16 + 16 + 32)


def decrypt_document_data(encrypted_data: bytes, user_pin: Optional[str] = None) -> bytes:
    """
    Verifies authenticity tag and decrypts ciphertext back to original bytes.
    If data is not encrypted (legacy unencrypted document), returns data as-is.
    Supports documents encrypted with a user PIN or with the system master key.
    """
    if not encrypted_data:
        return b""

    if not is_encrypted_document(encrypted_data):
        # Legacy backward-compatibility: Return unencrypted data directly
        return encrypted_data

    header_len = len(MAGIC_HEADER)
    salt = encrypted_data[header_len:header_len + 16]
    nonce = encrypted_data[header_len + 16:header_len + 32]
    mac_tag = encrypted_data[header_len + 32:header_len + 64]
    ciphertext = encrypted_data[header_len + 64:]

    candidate_pins = [user_pin, None] if user_pin else [None]
    seen = set()
    for pin_cand in candidate_pins:
        if pin_cand in seen:
            continue
        seen.add(pin_cand)
        cipher_key, mac_key = _derive_keys(DEFAULT_SYSTEM_KEY, salt, pin_cand)
        h = hmac.new(mac_key, MAGIC_HEADER + salt + nonce + ciphertext, hashlib.sha256)
        if hmac.compare_digest(mac_tag, h.digest()):
            keystream = _generate_keystream(cipher_key, nonce, len(ciphertext))
            return bytes(a ^ b for a, b in zip(ciphertext, keystream))

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Document decryption failed. Invalid PIN or corrupted data.",
    )
