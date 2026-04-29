import base64
import hashlib
import hmac
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta


@dataclass(slots=True)
class AuthTokenPayload:
    sub: str
    role: str
    exp: int


class TokenService:
    def __init__(self, secret_key: str, expire_minutes: int) -> None:
        self._secret_key = secret_key.encode("utf-8")
        self._expire_minutes = expire_minutes

    def create_token(self, subject: str, role: str) -> str:
        expires_at = datetime.now(UTC) + timedelta(minutes=self._expire_minutes)
        payload = AuthTokenPayload(sub=subject, role=role, exp=int(expires_at.timestamp()))
        payload_bytes = json.dumps(
            asdict(payload),
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        payload_encoded = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
        signature = hmac.new(
            self._secret_key,
            payload_encoded.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{payload_encoded}.{signature}"

    def decode_token(self, token: str) -> AuthTokenPayload:
        try:
            payload_encoded, signature = token.split(".", maxsplit=1)
        except ValueError as exc:
            raise ValueError("Token invalido.") from exc

        expected_signature = hmac.new(
            self._secret_key,
            payload_encoded.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Token invalido.")

        padding = "=" * (-len(payload_encoded) % 4)
        payload_raw = base64.urlsafe_b64decode(f"{payload_encoded}{padding}".encode())
        payload_data = json.loads(payload_raw.decode("utf-8"))
        payload = AuthTokenPayload(**payload_data)

        if payload.exp < int(datetime.now(UTC).timestamp()):
            raise ValueError("Token expirado.")

        return payload
