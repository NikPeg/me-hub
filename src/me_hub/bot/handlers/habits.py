from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from me_hub.bot import texts
from me_hub.bot.keyboards import HabitAction, HabitActionKind, confirm_archive_markup
from me_hub.bot.messaging import show_in_place
from me_hub.bot.views import View, habits_view
from me_hub.core.habits import (
    DuplicateHabitError,
    HabitNotFoundError,
    add_habit,
    archive_habit,
    get_active_habit,
    rename_habit,
)
from me_hub.core.models import HABIT_NAME_MAX_LENGTH, User

router = Router(name="habits")

PLAIN_TEXT = F.text & ~F.text.startswith("/")


class HabitForm(StatesGroup):
    adding = State()
    renaming = State()


BAD_HABIT_NAME = texts.BAD_HABIT_NAME.format(max_length=HABIT_NAME_MAX_LENGTH)


@router.message(Command("habits"))
async def list_habits(message: Message, session: AsyncSession, user: User) -> None:
    view = await habits_view(session, user)
    await message.answer(view.text, reply_markup=view.markup)


@router.message(Command("add"))
async def start_adding(
    message: Message, command: CommandObject, state: FSMContext, session: AsyncSession, user: User
) -> None:
    if command.args:
        await _add(message, command.args, state, session, user)
        return
    await state.set_state(HabitForm.adding)
    await message.answer(texts.ASK_HABIT_NAME)


@router.message(HabitForm.adding, PLAIN_TEXT)
async def finish_adding(
    message: Message, state: FSMContext, session: AsyncSession, user: User
) -> None:
    await _add(message, message.text or "", state, session, user)


async def _add(
    message: Message, name: str, state: FSMContext, session: AsyncSession, user: User
) -> None:
    try:
        habit = await add_habit(session, user, name)
    except DuplicateHabitError as error:
        await message.answer(texts.DUPLICATE_HABIT.format(name=escape(error.name)))
        return
    except ValueError:
        await message.answer(BAD_HABIT_NAME)
        return
    await session.commit()
    await state.clear()
    await message.answer(texts.HABIT_ADDED.format(name=escape(habit.name)))


@router.callback_query(HabitAction.filter(F.action == HabitActionKind.RENAME))
async def start_renaming(
    callback: CallbackQuery,
    callback_data: HabitAction,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    try:
        habit = await get_active_habit(session, user.id, callback_data.habit_id)
    except HabitNotFoundError:
        await _habit_gone(callback, session, user)
        return
    await state.set_state(HabitForm.renaming)
    await state.update_data(habit_id=habit.id)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(texts.ASK_NEW_HABIT_NAME.format(name=escape(habit.name)))


@router.message(HabitForm.renaming, PLAIN_TEXT)
async def finish_renaming(
    message: Message, state: FSMContext, session: AsyncSession, user: User
) -> None:
    habit_id = (await state.get_data()).get("habit_id")
    if not isinstance(habit_id, int):
        await state.clear()
        await message.answer(texts.HABIT_NOT_FOUND)
        return
    try:
        habit = await rename_habit(session, user.id, habit_id, message.text or "")
    except HabitNotFoundError:
        await state.clear()
        await message.answer(texts.HABIT_NOT_FOUND)
        return
    except DuplicateHabitError as error:
        await message.answer(texts.DUPLICATE_HABIT.format(name=escape(error.name)))
        return
    except ValueError:
        await message.answer(BAD_HABIT_NAME)
        return
    await session.commit()
    await state.clear()
    await message.answer(texts.HABIT_RENAMED.format(name=escape(habit.name)))


@router.callback_query(HabitAction.filter(F.action == HabitActionKind.ARCHIVE))
async def ask_archive(
    callback: CallbackQuery, callback_data: HabitAction, session: AsyncSession, user: User
) -> None:
    try:
        habit = await get_active_habit(session, user.id, callback_data.habit_id)
    except HabitNotFoundError:
        await _habit_gone(callback, session, user)
        return
    view = View(
        texts.CONFIRM_ARCHIVE.format(name=escape(habit.name)), confirm_archive_markup(habit.id)
    )
    await show_in_place(callback, view)
    await callback.answer()


@router.callback_query(HabitAction.filter(F.action == HabitActionKind.CONFIRM_ARCHIVE))
async def confirm_archive(
    callback: CallbackQuery, callback_data: HabitAction, session: AsyncSession, user: User
) -> None:
    try:
        habit = await archive_habit(session, user, callback_data.habit_id)
    except HabitNotFoundError:
        await _habit_gone(callback, session, user)
        return
    await session.commit()
    await callback.answer(texts.HABIT_ARCHIVED.format(name=habit.name))
    await show_in_place(callback, await habits_view(session, user))


@router.callback_query(HabitAction.filter(F.action == HabitActionKind.BACK))
async def back_to_list(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    await show_in_place(callback, await habits_view(session, user))
    await callback.answer()


async def _habit_gone(callback: CallbackQuery, session: AsyncSession, user: User) -> None:
    await callback.answer(texts.HABIT_NOT_FOUND, show_alert=True)
    await show_in_place(callback, await habits_view(session, user))
