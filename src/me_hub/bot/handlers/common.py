from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from me_hub.bot import texts
from me_hub.bot.keyboards import site_markup

router = Router(name="common")
fallback_router = Router(name="fallback")


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(texts.START)


@router.message(Command("help"))
async def show_help(message: Message) -> None:
    await message.answer(texts.HELP)


@router.message(Command("site"))
async def show_site(message: Message) -> None:
    await message.answer(texts.SITE_MESSAGE, reply_markup=site_markup())


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer(texts.NOTHING_TO_CANCEL)
        return
    await state.clear()
    await message.answer(texts.CANCELLED)


@fallback_router.message()
async def unknown_message(message: Message) -> None:
    await message.answer(texts.UNKNOWN_MESSAGE)
