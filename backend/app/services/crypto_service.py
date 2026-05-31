import base64
import json
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_KEY = os.environ.get("ENCRYPTION_KEY", "data-asset-platform-default-key-2026").encode()
_SALT = b"dap-salt-v1"


def _derive_key() -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=_SALT, iterations=100000)
    return kdf.derive(_KEY)


def encrypt_config(config: dict) -> str:
    """Encrypt a config dict into a base64 string."""
    key = _derive_key()
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
    encryptor = cipher.encryptor()
    plaintext = json.dumps(config, ensure_ascii=False).encode("utf-8")
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    result = iv + encryptor.tag + ciphertext
    return base64.b64encode(result).decode("utf-8")


def decrypt_config(encrypted: str) -> dict:
    """Decrypt a base64 string back to a config dict."""
    key = _derive_key()
    data = base64.b64decode(encrypted)
    iv, tag, ciphertext = data[:16], data[16:32], data[32:]
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag))
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    return json.loads(plaintext.decode("utf-8"))
