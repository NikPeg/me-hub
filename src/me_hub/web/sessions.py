import hmac
from datetime import datetime, timedelta
from hashlib import sha256

SESSION_COOKIE = "me_hub_session"


def _sign(payload: str, secret: bytes) -> str:
    return hmac.new(secret, payload.encode(), sha256).hexdigest()


def issue_session(user_id: int, secret: bytes, now: datetime, ttl: timedelta) -> str:
    payload = f"{user_id}.{int((now + ttl).timestamp())}"
    return f"{payload}.{_sign(payload, secret)}"


def read_session(token: str, secret: bytes, now: datetime) -> int | None:
    """Returns the user id of a genuine, unexpired session token, otherwise None."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    user_id, expires_at, signature = parts
    expected = _sign(f"{user_id}.{expires_at}", secret)
    if not hmac.compare_digest(signature.encode(), expected.encode()):
        return None
    try:
        if now.timestamp() >= int(expires_at):
            return None
        return int(user_id)
    except ValueError:
        return None
