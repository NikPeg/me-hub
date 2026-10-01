import hmac
from datetime import timedelta
from hashlib import sha256

import pytest
from web_helpers import BOT_TOKEN, NOW, signed_login

from me_hub.web.sessions import issue_session, read_session
from me_hub.web.telegram_auth import TelegramAuthError, verify_login

SECRET = b"s" * 32


class TestVerifyLogin:
    def test_returns_user_id_of_genuine_login(self) -> None:
        assert verify_login(signed_login(), BOT_TOKEN, NOW) == 123456789

    def test_rejects_missing_hash(self) -> None:
        login = signed_login()
        del login["hash"]
        with pytest.raises(TelegramAuthError):
            verify_login(login, BOT_TOKEN, NOW)

    def test_rejects_tampered_field(self) -> None:
        login = signed_login() | {"id": "42"}
        with pytest.raises(TelegramAuthError):
            verify_login(login, BOT_TOKEN, NOW)

    def test_rejects_login_signed_with_another_token(self) -> None:
        with pytest.raises(TelegramAuthError):
            verify_login(signed_login(bot_token="other:token"), BOT_TOKEN, NOW)

    def test_rejects_non_ascii_hash(self) -> None:
        with pytest.raises(TelegramAuthError):
            verify_login(signed_login() | {"hash": "é" * 64}, BOT_TOKEN, NOW)

    def test_rejects_stale_login(self) -> None:
        with pytest.raises(TelegramAuthError):
            verify_login(signed_login(), BOT_TOKEN, NOW + timedelta(minutes=6))

    def test_tolerates_small_clock_skew(self) -> None:
        assert verify_login(signed_login(), BOT_TOKEN, NOW - timedelta(seconds=5)) == 123456789

    def test_rejects_login_from_the_far_future(self) -> None:
        with pytest.raises(TelegramAuthError):
            verify_login(signed_login(), BOT_TOKEN, NOW - timedelta(minutes=5))

    @pytest.mark.parametrize("overrides", [{"id": "abc"}, {"auth_date": "yesterday"}])
    def test_rejects_malformed_signed_fields(self, overrides: dict[str, str]) -> None:
        with pytest.raises(TelegramAuthError):
            verify_login(signed_login(**overrides), BOT_TOKEN, NOW)


class TestSessions:
    def test_round_trip(self) -> None:
        token = issue_session(42, SECRET, NOW, timedelta(days=1))
        assert read_session(token, SECRET, NOW + timedelta(hours=23)) == 42

    def test_expires(self) -> None:
        token = issue_session(42, SECRET, NOW, timedelta(days=1))
        assert read_session(token, SECRET, NOW + timedelta(days=1)) is None

    def test_rejects_wrong_secret(self) -> None:
        token = issue_session(42, SECRET, NOW, timedelta(days=1))
        assert read_session(token, b"x" * 32, NOW) is None

    def test_rejects_tampered_user(self) -> None:
        _, expires, signature = issue_session(42, SECRET, NOW, timedelta(days=1)).split(".")
        assert read_session(f"7.{expires}.{signature}", SECRET, NOW) is None

    @pytest.mark.parametrize("token", ["", "garbage", "1.2", "a.b.c.d", "é.é.é"])
    def test_rejects_malformed_tokens(self, token: str) -> None:
        assert read_session(token, SECRET, NOW) is None

    def test_rejects_signed_non_numeric_payload(self) -> None:
        payload = "abc.def"
        signature = hmac.new(SECRET, payload.encode(), sha256).hexdigest()
        assert read_session(f"{payload}.{signature}", SECRET, NOW) is None
