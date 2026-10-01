"""All user-facing bot copy. The bot speaks Russian, so Cyrillic is expected only here."""

MONTHS_GENITIVE = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)
WEEKDAYS_SHORT = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")
TODAY_LABEL = "сегодня, {label}"
YESTERDAY_LABEL = "вчера, {label}"
TODAY_BUTTON = "Сегодня"
YESTERDAY_BUTTON = "Вчера"
ARCHIVE_BUTTON = "В архив"
BACK_BUTTON = "Назад"

COMMAND_DESCRIPTIONS = {
    "today": "Отметить сегодня",
    "mark": "Отметить другой день",
    "habits": "Список привычек",
    "add": "Добавить привычку",
    "settings": "Часовой пояс и напоминания",
    "help": "Помощь",
}

HELP = (
    "Я каждый вечер спрашиваю, какие привычки ты сделал за день.\n\n"
    "/today — отметить сегодня\n"
    "/mark — отметить другой день (например, <code>/mark 28.09</code>)\n"
    "/habits — список привычек: переименовать, архивировать\n"
    "/add — добавить привычку (например, <code>/add Читать</code>)\n"
    "/settings — часовой пояс и время напоминаний\n"
    "/timezone — сменить часовой пояс (например, <code>/timezone Asia/Dubai</code>)\n"
    "/reminder — сменить время вечернего опроса (например, <code>/reminder 23:00</code>)\n"
    "/cancel — отменить текущее действие"
)
UNKNOWN_MESSAGE = "Не понял. Список команд: /help"
SOMETHING_WENT_WRONG = "Что-то пошло не так. Попробуй ещё раз чуть позже."

NOTHING_TO_CANCEL = "Нечего отменять."
CANCELLED = "Отменено."

NO_HABITS = "Привычек пока нет. Добавь первую: <code>/add Название</code>"
CHECKIN_TITLE = "Привычки за <b>{day}</b>\nВыполнено {done} из {total}"
EVENING_INTRO = "Как прошёл день? Отметь, что удалось сделать."
MORNING_INTRO = "Вчера ничего не отмечено. Ещё не поздно заполнить."
PICK_DAY = "За какой день отметить? Можно и любую дату: <code>/mark 28.09</code>"
BAD_DATE = (
    "Не понял дату. Примеры: <code>28.09</code>, <code>28.09.2026</code>, <code>2026-09-28</code>"
)
DAY_NOT_MARKABLE = "Этот день отметить нельзя: только прошлые дни за последний год и сегодня."
HABIT_NOT_FOUND = "Привычка не найдена: возможно, она уже в архиве."

HABITS_TITLE = "Твои привычки. ✏️ — переименовать, 🗄 — в архив."
ASK_HABIT_NAME = "Как назовём привычку? /cancel — отменить."
ASK_NEW_HABIT_NAME = "Новое название для «{name}»? /cancel — отменить."
BAD_HABIT_NAME = "Название должно быть непустым и не длиннее {max_length} символов."
DUPLICATE_HABIT = "Привычка «{name}» уже есть."
HABIT_ADDED = "Добавил «{name}». Отметить сегодня: /today"
HABIT_RENAMED = "Переименовал в «{name}»."
CONFIRM_ARCHIVE = "Убрать «{name}» в архив? Перестану о ней спрашивать, история сохранится."
HABIT_ARCHIVED = "«{name}» в архиве."

SETTINGS = (
    "Часовой пояс: <b>{timezone}</b>\n"
    "Вечерний опрос: <b>{reminder_time}</b>\n"
    "Утреннее напоминание, если вчера ничего не отмечено: <b>{morning_time}</b>\n\n"
    "Изменить: <code>/timezone Asia/Dubai</code>, <code>/reminder 23:00</code>"
)
TIMEZONE_USAGE = "Укажи часовой пояс в формате IANA, например: <code>/timezone Asia/Dubai</code>"
UNKNOWN_TIMEZONE = (
    "Не знаю такой часовой пояс. Пример: <code>Asia/Dubai</code>, <code>Europe/London</code>"
)
TIMEZONE_UPDATED = "Часовой пояс: <b>{timezone}</b>. Вечерний опрос в {reminder_time} по нему."
REMINDER_USAGE = "Укажи время в формате ЧЧ:ММ, например: <code>/reminder 23:00</code>"
REMINDER_UPDATED = "Теперь спрашиваю каждый день в <b>{reminder_time}</b> ({timezone})."
