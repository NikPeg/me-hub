from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from me_hub.bot.views import View


async def show_in_place(callback: CallbackQuery, view: View) -> None:
    """Replaces the message the callback came from, or sends a new one if it is unavailable."""
    message = callback.message
    if not isinstance(message, Message):
        if callback.bot is not None:
            await callback.bot.send_message(
                callback.from_user.id, view.text, reply_markup=view.markup
            )
        return
    try:
        await message.edit_text(view.text, reply_markup=view.markup)
    except TelegramBadRequest as error:
        if "message is not modified" not in error.message:
            raise
