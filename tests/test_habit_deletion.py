from datetime import time, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from aiogram.types import CallbackQuery
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from me_hub.bot import texts
from me_hub.bot.app import COMMANDS
from me_hub.bot.handlers.habits import (
    ask_delete,
    back_to_list,
    confirm_delete,
)
from me_hub.bot.keyboards import HabitAction, HabitActionKind, habits_markup
from me_hub.core.habits import (
    HabitNotFoundError,
    add_habit,
    archive_habit,
    delete_habit,
    ensure_user,
    local_today,
    toggle_check,
)
from me_hub.core.models import Habit, HabitCheck, User


@pytest.mark.parametrize("archived", [False, True])
async def test_delete_removes_habit_and_all_checks_only(
    session: AsyncSession, owner: User, archived: bool
) -> None:
    habit = await add_habit(session, owner, "Read")
    other = await add_habit(session, owner, "Run")
    today = local_today(owner)
    for day in (today, today - timedelta(days=5)):
        await toggle_check(session, owner, habit.id, day)
    await toggle_check(session, owner, other.id, today)
    habit_id, other_id, owner_id = habit.id, other.id, owner.id
    if archived:
        await archive_habit(session, owner, habit_id)
    await session.commit()
    session.expunge_all()

    await delete_habit(session, owner_id, habit_id)
    await session.commit()
    session.expunge_all()

    assert await session.get(Habit, habit_id) is None
    assert (
        await session.scalar(
            select(func.count()).select_from(HabitCheck).where(HabitCheck.habit_id == habit_id)
        )
        == 0
    )
    assert await session.get(Habit, other_id) is not None
    assert await session.get(HabitCheck, (other_id, today)) is not None
    with pytest.raises(HabitNotFoundError):
        await delete_habit(session, owner_id, habit_id)


async def test_delete_rejects_foreign_habit(session: AsyncSession, owner: User) -> None:
    stranger = await ensure_user(session, 7, "UTC", time(21))
    habit = await add_habit(session, stranger, "Secret")

    with pytest.raises(HabitNotFoundError):
        await delete_habit(session, owner.id, habit.id)
    assert await session.get(Habit, habit.id) is habit


async def test_delete_requires_confirmation_and_can_be_cancelled(
    session: AsyncSession, owner: User
) -> None:
    habit = await add_habit(session, owner, "Read <books>")
    await session.commit()
    callback = AsyncMock(spec=CallbackQuery)
    callback.answer = AsyncMock()
    action = HabitAction(action=HabitActionKind.DELETE, habit_id=habit.id)

    buttons = habits_markup([habit]).inline_keyboard[0]
    assert buttons[-2].callback_data is not None
    assert HabitAction.unpack(buttons[-2].callback_data).action == HabitActionKind.ARCHIVE
    assert buttons[-1].callback_data == action.pack()
    assert {"del", "delete"}.isdisjoint(command.command for command in COMMANDS)

    with patch("me_hub.bot.handlers.habits.show_in_place", new_callable=AsyncMock) as show:
        await ask_delete(callback, action, session, owner)
        assert show.await_args is not None
        view = show.await_args.args[1]
        assert "Read &lt;books&gt;" in view.text
        assert view.markup is not None
        confirm_button, cancel_button = [row[0] for row in view.markup.inline_keyboard]
        assert confirm_button.callback_data is not None
        confirm_action = HabitAction.unpack(confirm_button.callback_data)
        assert confirm_action.action == HabitActionKind.CONFIRM_DELETE
        assert cancel_button.callback_data is not None
        assert HabitAction.unpack(cancel_button.callback_data).action == HabitActionKind.BACK
        await back_to_list(callback, session, owner)
        assert await session.get(Habit, habit.id) is habit

        await confirm_delete(callback, confirm_action, session, owner)
        assert await session.get(Habit, habit.id) is None
        callback.answer.assert_awaited_with(texts.HABIT_DELETED.format(name=habit.name))

        await confirm_delete(callback, confirm_action, session, owner)
        callback.answer.assert_awaited_with(texts.HABIT_NOT_FOUND, show_alert=True)
