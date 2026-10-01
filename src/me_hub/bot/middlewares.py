import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Chat, TelegramObject
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from me_hub.bot.config import BotSettings
from me_hub.core.habits import ensure_user

logger = logging.getLogger(__name__)

type Handler = Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]


class OwnerOnlyMiddleware(BaseMiddleware):
    """Silently drops every update that is not from the owner in a private chat."""

    def __init__(self, owner_id: int) -> None:
        self._owner_id = owner_id

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        sender: TelegramUser | None = data.get("event_from_user")
        chat: Chat | None = data.get("event_chat")
        if sender is None or sender.id != self._owner_id:
            logger.info("Ignored update from user %s", sender.id if sender else None)
            return None
        if chat is not None and chat.type != ChatType.PRIVATE:
            logger.info("Ignored update from non-private chat %s", chat.id)
            return None
        return await handler(event, data)


class DatabaseMiddleware(BaseMiddleware):
    """Provides a session and the owner's `User` row to handlers.

    Handlers commit their own writes so that replies are sent only after data is saved."""

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], settings: BotSettings
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        async with self._session_factory() as session:
            user = await ensure_user(
                session,
                self._settings.telegram_owner_id,
                self._settings.default_timezone,
                self._settings.default_reminder_time,
            )
            await session.commit()
            data["session"] = session
            data["user"] = user
            return await handler(event, data)
