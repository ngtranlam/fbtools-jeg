"""Token encryption/decryption using Fernet symmetric encryption."""

from __future__ import annotations

import os
from pathlib import Path
from cryptography.fernet import Fernet

_KEY_FILE = Path(__file__).resolve().parent.parent.parent / "data" / ".secret_key"
_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet:
        return _fernet

    if _KEY_FILE.exists():
        key = _KEY_FILE.read_bytes().strip()
    else:
        key = Fernet.generate_key()
        _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _KEY_FILE.write_bytes(key)
    _fernet = Fernet(key)
    return _fernet


def encrypt_token(token: str) -> str:
    return _get_fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()
