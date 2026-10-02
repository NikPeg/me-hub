"""All user-facing copy for the bot and web dashboard."""

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
CHANGE_COLOR_BUTTON = "🎨"

COMMAND_DESCRIPTIONS = {
    "today": "Отметить сегодня",
    "mark": "Отметить другой день",
    "site": "Открыть сайт",
    "habits": "Список привычек",
    "add": "Добавить привычку",
    "settings": "Часовой пояс и напоминания",
    "help": "Помощь",
}

HELP = (
    "Помогаю отслеживать привычки: отмечай, что удалось сделать за день, "
    "а я напомню об этом вечером. Прогресс можно посмотреть на сайте.\n\n"
    "/today — отметить сегодня\n"
    "/mark — отметить другой день (например, <code>/mark 28.09</code>)\n"
    "/site — открыть сайт\n"
    "/habits — список привычек: переименовать, сменить цвет, архивировать\n"
    "/add — добавить привычку (например, <code>/add Читать</code>)\n"
    "/settings — часовой пояс и время напоминаний\n"
    "/timezone — сменить часовой пояс (например, <code>/timezone Asia/Dubai</code>)\n"
    "/reminder — сменить время вечернего опроса (например, <code>/reminder 23:00</code>)\n"
    "/cancel — отменить текущее действие"
)
SITE_URL = "https://me.nikpeg.me/"
START = SITE_URL + "\n\n" + HELP
SITE_MESSAGE = "Сайт"
SITE_BUTTON = "🌐 Открыть сайт me.nikpeg.me"
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

HABITS_TITLE = "Твои привычки. ✏️ — переименовать, 🎨 — сменить цвет, 🗄 — в архив."
ASK_HABIT_NAME = "Как назовём привычку? /cancel — отменить."
ASK_NEW_HABIT_NAME = "Новое название для «{name}»? /cancel — отменить."
BAD_HABIT_NAME = "Название должно быть непустым и не длиннее {max_length} символов."
DUPLICATE_HABIT = "Привычка «{name}» уже есть."
HABIT_ADDED = "Добавил «{name}». Отметить сегодня: /today"
HABIT_RENAMED = "Переименовал в «{name}»."
HABIT_COLOR_CHANGED = "Новый цвет для «{name}» сохранён. Смотри на сайте."
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

WEB_TEXTS = {
    "months": ("янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"),
    "weekdays": ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"),
    "logout": "Выйти",
    "overall": "Все привычки",
    "login_failed": "Не удалось войти. Попробуйте ещё раз.",
    "data_failed": "Не удалось загрузить данные.",
    "service_failed": "Сервис недоступен. Попробуйте позже.",
    "year": "Весь год",
    "no_habits": "нет привычек",
    "done": "выполнено",
    "missed": "пропущено",
    "untracked": "не отслеживалось",
    "streak": "Серия",
    "record": "Рекорд",
    "total": "Всего",
    "completion": "Выполнение",
    "today": "Сегодня",
    "of": "из",
}
