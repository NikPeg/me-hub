from datetime import time

from pydantic import SecretStr, field_validator

from me_hub.core.config import Settings
from me_hub.core.models import validate_timezone


class BotSettings(Settings):
    telegram_bot_token: SecretStr
    telegram_owner_id: int
    default_timezone: str = "Asia/Dubai"
    default_reminder_time: time = time(23, 0)
    morning_reminder_time: time = time(9, 0)

    @field_validator("default_timezone")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        return validate_timezone(value)
