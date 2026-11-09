from __future__ import annotations

import base64
import hashlib
import hmac
import os
import random
import re
import secrets
import unicodedata

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _key_bytes() -> bytes:
    hex_key = os.getenv("ENCRYPTION_KEY", "")
    if len(hex_key) != 64:
        raise RuntimeError("ENCRYPTION_KEY deve ter 64 caracteres hexadecimais.")
    return bytes.fromhex(hex_key)


def normalize_name(name: str) -> str:
    return " ".join(str(name or "").strip().split())


def name_key(name: str) -> str:
    return normalize_name(name).casefold()


def encrypt_name(plain_text: str) -> str:
    aesgcm = AESGCM(_key_bytes())
    iv = secrets.token_bytes(12)
    encrypted = aesgcm.encrypt(iv, str(plain_text).encode("utf-8"), None)
    return base64.b64encode(iv + encrypted).decode("ascii")


def decrypt_name(payload: str) -> str:
    raw = base64.b64decode(str(payload))
    iv, data = raw[:12], raw[12:]
    aesgcm = AESGCM(_key_bytes())
    return aesgcm.decrypt(iv, data, None).decode("utf-8")


def hash_name(name: str) -> str:
    return hmac.new(_key_bytes(), name_key(name).encode("utf-8"), hashlib.sha256).hexdigest()


def hash_token(token: str) -> str:
    return hmac.new(
        _key_bytes(),
        str(token).strip().casefold().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_password(plain_password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    digest = hash_token(plain_password)
    return hmac.compare_digest(digest, str(password_hash))


def generate_easy_password(name: str) -> str:
    """Gera senha fácil: primeiro nome sem acento + 2 dígitos. Ex.: ana47"""
    first = normalize_name(name).split(" ")[0]
    folded = unicodedata.normalize("NFKD", first).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z]", "", folded).lower() or "amigo"
    return f"{slug}{random.randint(10, 99)}"
