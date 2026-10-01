import hmac
from datetime import UTC, datetime
from hashlib import sha256

BOT_TOKEN = "123456:test-token"
NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)


def signed_login(bot_token: str = BOT_TOKEN, **overrides: str) -> dict[str, str]:
    fields = {
        "id": "123456789",
        "first_name": "Nik",
        "auth_date": str(int(NOW.timestamp())),
    } | overrides
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    key = sha256(bot_token.encode()).digest()
    return fields | {"hash": hmac.new(key, check_string.encode(), sha256).hexdigest()}
