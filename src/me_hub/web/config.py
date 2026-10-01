from datetime import timedelta

from pydantic import Field, SecretStr

from me_hub.core.config import Settings

MIN_SESSION_SECRET_LENGTH = 32


class WebSettings(Settings):
    telegram_bot_token: SecretStr
    telegram_bot_username: str
    telegram_owner_id: int
    session_secret: SecretStr = Field(min_length=MIN_SESSION_SECRET_LENGTH)
    session_ttl_days: int = Field(default=30, gt=0)
    web_host: str = "127.0.0.1"
    web_port: int = Field(default=8000, gt=0, lt=65536)

    @property
    def session_ttl(self) -> timedelta:
        return timedelta(days=self.session_ttl_days)

    @property
    def session_key(self) -> bytes:
        return self.session_secret.get_secret_value().encode()
