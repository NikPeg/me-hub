import hmac
from collections.abc import Mapping
from datetime import datetime, timedelta
from hashlib import sha256

LOGIN_MAX_AGE = timedelta(minutes=5)
CLOCK_SKEW = timedelta(seconds=30)


class TelegramAuthError(Exception):
    """The Telegram Login Widget payload is malformed, forged or stale."""


def verify_login(
    params: Mapping[str, str], bot_token: str, now: datetime, max_age: timedelta = LOGIN_MAX_AGE
) -> int:
    """Validates a Telegram Login Widget payload and returns the Telegram user id.

    https://core.telegram.org/widgets/login#checking-authorization
    """
    received_hash = params.get("hash")
    if received_hash is None:
        raise TelegramAuthError("Missing hash")
    fields = {key: value for key, value in params.items() if key != "hash"}
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = sha256(bot_token.encode()).digest()
    expected_hash = hmac.new(secret_key, check_string.encode(), sha256).hexdigest()
    if not hmac.compare_digest(received_hash.encode(), expected_hash.encode()):
        raise TelegramAuthError("Invalid hash")
    try:
        auth_age = now.timestamp() - int(fields["auth_date"])
        user_id = int(fields["id"])
    except (KeyError, ValueError) as error:
        raise TelegramAuthError("Missing or malformed id or auth_date") from error
    if not -CLOCK_SKEW.total_seconds() <= auth_age <= max_age.total_seconds():
        raise TelegramAuthError("Login is stale")
    return user_id
