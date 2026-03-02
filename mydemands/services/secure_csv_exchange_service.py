from __future__ import annotations

import base64
import csv
import io
import logging
import os
import secrets
import string
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger(__name__)
CRYPTO_IMPORT_ERROR: str | None = None

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTO_AVAILABLE = True
except Exception as exc:  # pragma: no cover - exercised by simulated fallback tests
    AESGCM = None  # type: ignore[assignment]
    PBKDF2HMAC = None  # type: ignore[assignment]
    hashes = None  # type: ignore[assignment]
    CRYPTO_AVAILABLE = False
    CRYPTO_IMPORT_ERROR = repr(exc)

try:
    import win32crypt  # type: ignore
except Exception:  # pragma: no cover - platform fallback
    win32crypt = None

from csv_store import DISPLAY_COLUMNS
from mydemands.infra.secrets.secret_store import ISecretStore

ENC_HEADER = "MYDEMANDS_ENCRYPTED_V1"
DPAPI_HEADER = "MYDEMANDS_DPAPI_V1"
MASTER_KEY_SECRET = "csv_exchange_master_key"
CRYPTO_LOG_FILE = "mydemands_crypto.log"


def _log_crypto_import_error(detail: str) -> None:
    try:
        with Path(CRYPTO_LOG_FILE).open("a", encoding="utf-8") as fp:
            fp.write(f"CRYPTO_IMPORT_ERROR: {detail}\n")
    except Exception:
        pass


class CsvExchangeError(Exception):
    pass


@dataclass
class ImportResult:
    csv_text: str
    encrypted: bool


class SecureCsvExchangeService:
    def __init__(self, secret_store: ISecretStore):
        self.secret_store = secret_store

    @staticmethod
    def crypto_unavailable_message() -> str:
        return "Criptografia indisponível nesta build (dependência ausente). Contate o administrador."

    @classmethod
    def crypto_ready(cls) -> bool:
        available = cls.self_check()
        if not available and CRYPTO_IMPORT_ERROR:
            logger.error("Cryptography indisponível no runtime: %s", CRYPTO_IMPORT_ERROR)
            _log_crypto_import_error(CRYPTO_IMPORT_ERROR)
        return available

    @classmethod
    def crypto_available(cls) -> bool:
        return cls.crypto_ready()

    @classmethod
    def self_check(cls) -> bool:
        if not CRYPTO_AVAILABLE or AESGCM is None:
            return False
        try:
            key = b"0" * 32
            nonce = b"1" * 12
            plain = b"mydemands-crypto-check"
            cipher = AESGCM(key).encrypt(nonce, plain, None)
            return AESGCM(key).decrypt(nonce, cipher, None) == plain
        except Exception:
            return False

    def _get_or_create_master_key(self) -> bytes:
        key = self.secret_store.get(MASTER_KEY_SECRET)
        if key and len(key) >= 32:
            return key[:32]
        key = os.urandom(32)
        self.secret_store.set(MASTER_KEY_SECRET, key)
        return key

    def _derive_key(self, passphrase: str, salt: bytes) -> bytes:
        if not self.crypto_ready():
            raise CsvExchangeError(self.crypto_unavailable_message())
        if not passphrase:
            raise CsvExchangeError("Informe uma palavra-passe válida para exportar.")
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390000)
        return kdf.derive(passphrase.encode("utf-8"))

    def _export_dpapi_payload(self, csv_text: str, passphrase: str, is_master: bool) -> str:
        if passphrase:
            raise CsvExchangeError(self.crypto_unavailable_message())
        if not is_master:
            raise CsvExchangeError(self.crypto_unavailable_message())
        if win32crypt is None:
            raise CsvExchangeError("Criptografia indisponível nesta build. Contate o administrador.")
        cipher = win32crypt.CryptProtectData(csv_text.encode("utf-8-sig"), "MyDemandsCSV", None, None, None, 0)
        return "\n".join([DPAPI_HEADER, f"data:{base64.b64encode(cipher).decode('ascii')}"])

    def _import_dpapi_payload(self, raw_text: str, is_master: bool) -> ImportResult:
        if win32crypt is None:
            raise CsvExchangeError("Criptografia indisponível nesta build. Contate o administrador.")
        values: dict[str, bytes] = {}
        for line in raw_text.splitlines()[1:]:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            values[key.strip()] = base64.b64decode(value.strip() or "")
        cipher = values.get("data", b"")
        if not cipher:
            raise CsvExchangeError("Arquivo criptografado inválido ou corrompido.")
        if not is_master:
            raise CsvExchangeError(self.crypto_unavailable_message())
        plain = win32crypt.CryptUnprotectData(cipher, None, None, None, 0)[1]
        return ImportResult(csv_text=plain.decode("utf-8-sig"), encrypted=True)

    def render_csv_text(self, rows: List[Dict[str, Any]], delimiter: str = ",") -> str:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=DISPLAY_COLUMNS, delimiter=delimiter)
        writer.writeheader()
        for row in rows:
            payload = {k: row.get(k, "") for k in DISPLAY_COLUMNS}
            writer.writerow(payload)
        return buf.getvalue()

    @staticmethod
    def generate_passphrase(length: int = 12) -> str:
        size = max(8, length)
        letters = string.ascii_letters
        digits = string.digits
        alphabet = letters + digits
        token = [secrets.choice(letters), secrets.choice(digits)]
        token.extend(secrets.choice(alphabet) for _ in range(size - 2))
        secrets.SystemRandom().shuffle(token)
        return "".join(token)

    def export_payload(self, csv_text: str, passphrase: str, is_master: bool) -> str:
        if not self.crypto_ready():
            return self._export_dpapi_payload(csv_text, passphrase=passphrase, is_master=is_master)

        data_key = os.urandom(32)
        salt = os.urandom(16)
        data_nonce = os.urandom(12)

        data_cipher = AESGCM(data_key).encrypt(data_nonce, csv_text.encode("utf-8-sig"), None)

        master_key = self._get_or_create_master_key()
        wrap_nonce_master = os.urandom(12)
        wrapped_key_master = AESGCM(master_key).encrypt(wrap_nonce_master, data_key, None)

        wrapped_key_user = b""
        wrap_nonce_user = b""
        if passphrase:
            user_key = self._derive_key(passphrase, salt)
            wrap_nonce_user = os.urandom(12)
            wrapped_key_user = AESGCM(user_key).encrypt(wrap_nonce_user, data_key, None)
        elif not is_master:
            raise CsvExchangeError("Informe uma palavra-passe válida para exportar.")

        lines = [
            ENC_HEADER,
            f"salt:{base64.b64encode(salt).decode('ascii')}",
            f"nonce:{base64.b64encode(data_nonce).decode('ascii')}",
            f"wrap_nonce_user:{base64.b64encode(wrap_nonce_user).decode('ascii')}",
            f"wrapped_key_user:{base64.b64encode(wrapped_key_user).decode('ascii')}",
            f"wrap_nonce_master:{base64.b64encode(wrap_nonce_master).decode('ascii')}",
            f"wrapped_key_master:{base64.b64encode(wrapped_key_master).decode('ascii')}",
            f"data:{base64.b64encode(data_cipher).decode('ascii')}",
        ]
        return "\n".join(lines)

    def import_payload(self, raw_text: str, passphrase: str, is_master: bool, allow_master_key: bool = True) -> ImportResult:
        if raw_text.startswith(DPAPI_HEADER):
            return self._import_dpapi_payload(raw_text, is_master=is_master)

        if not self.crypto_ready() and raw_text.startswith(ENC_HEADER):
            raise CsvExchangeError(self.crypto_unavailable_message())

        if not raw_text.startswith(ENC_HEADER):
            return ImportResult(csv_text=raw_text, encrypted=False)

        values: dict[str, bytes] = {}
        for line in raw_text.splitlines()[1:]:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            values[key.strip()] = base64.b64decode(value.strip() or "")

        salt = values.get("salt", b"")
        data_nonce = values.get("nonce", b"")
        data_cipher = values.get("data", b"")
        wrapped_key_user = values.get("wrapped_key_user", b"")
        wrap_nonce_user = values.get("wrap_nonce_user", b"")
        wrapped_key_master = values.get("wrapped_key_master", b"")
        wrap_nonce_master = values.get("wrap_nonce_master", b"")

        data_key: bytes | None = None
        if is_master and allow_master_key:
            try:
                data_key = AESGCM(self._get_or_create_master_key()).decrypt(wrap_nonce_master, wrapped_key_master, None)
            except Exception:
                data_key = None

        if data_key is None:
            if not passphrase:
                raise CsvExchangeError("Palavra-passe inválida ou ausente para descriptografar o arquivo.")
            try:
                user_key = self._derive_key(passphrase, salt)
                data_key = AESGCM(user_key).decrypt(wrap_nonce_user, wrapped_key_user, None)
            except Exception as exc:
                raise CsvExchangeError("Não foi possível descriptografar o arquivo. Verifique a palavra-passe.") from exc

        try:
            plain = AESGCM(data_key).decrypt(data_nonce, data_cipher, None)
        except Exception as exc:
            raise CsvExchangeError("Arquivo criptografado inválido ou corrompido.") from exc

        return ImportResult(csv_text=plain.decode("utf-8-sig"), encrypted=True)
