# me-hub

A private personal hub, for me only.

- **Telegram bot** — every evening asks which habits were done today; habits can be added, renamed, archived and backfilled.
- **Web dashboard** (`me.nikpeg.me`) — GitHub-style contribution grid: an overall grid plus one per habit, with streaks and completion stats.

## Stack

Python 3.14 · uv · aiogram 3 · APScheduler 3 · SQLAlchemy 2 (async) + aiosqlite · Alembic · pydantic-settings · pytest · ruff · mypy · Docker.

## Layout

```
src/me_hub/core/   models, database setup, settings, habit service, streak/completion stats
src/me_hub/bot/    Telegram bot: handlers, keyboards, reminder scheduling
src/me_hub/web/    dashboard API: Telegram login, sessions, grid data
web/               static dashboard (served by nginx from `/var/www/me-hub`)
migrations/        Alembic migrations
scripts/           maintenance scripts
tests/             pytest suite
```

## Development

```bash
uv sync                 # then create .env with the variables from "Configuration" below
uv run alembic upgrade head
uv run python -m me_hub.bot
uv run python -m me_hub.web   # dashboard API on 127.0.0.1:8000
```

Checks:

```bash
uv run ruff format && uv run ruff check && uv run mypy && uv run pytest
```

Migrations are applied only via `alembic upgrade head` (the Docker image's default command);
services never migrate on startup.

## Bot

Only the owner (`TELEGRAM_OWNER_ID`) can use the bot, in a private chat; other updates are ignored.

| Command | Action |
|---|---|
| `/today` | mark today's habits |
| `/mark [date]` | mark another day: picker for the last week, or `28.09`, `28.09.2026`, `2026-09-28` |
| `/habits` | list habits, rename or archive them |
| `/add [name]` | add a habit |
| `/settings` | show timezone and reminder times |
| `/timezone <IANA>` | change timezone |
| `/reminder <HH:MM>` | change the evening check-in time |
| `/cancel` | cancel the current action |

Reminders run in-process with APScheduler, in the owner's timezone:

- **evening check-in** at the configured time with a toggle button per habit;
- **morning reminder** if nothing was marked for yesterday.

Days can be marked up to a year back; future days cannot.

## Web dashboard

Static files from `web/` are served by nginx (`nginx/me-hub.conf`), which proxies `/api/` to
`python -m me_hub.web`. Sign-in uses the Telegram Login Widget: the bot's domain must be set
with @BotFather `/setdomain`. Only the owner (`TELEGRAM_OWNER_ID`) gets a session; it is an
HMAC-signed `HttpOnly`, `Secure`, `SameSite=Strict` cookie valid for `SESSION_TTL_DAYS`.

`/api/dashboard` returns the last 53 weeks: one overall grid (share of habits done per day)
and one grid per active habit with streaks and completion rate.

## Configuration

Read from environment variables or `.env`:

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///data/me_hub.db` | |
| `TELEGRAM_BOT_TOKEN` | — | secret, from @BotFather |
| `TELEGRAM_OWNER_ID` | — | your Telegram user id |
| `DEFAULT_TIMEZONE` | `Asia/Dubai` | initial timezone; then changed with `/timezone` |
| `DEFAULT_REMINDER_TIME` | `23:00` | initial check-in time; then changed with `/reminder` |
| `MORNING_REMINDER_TIME` | `09:00` | |
| `TELEGRAM_BOT_USERNAME` | — | web only: bot used for the login widget, without `@` |
| `SESSION_SECRET` | — | web only: at least 32 characters, e.g. `openssl rand -hex 32` |
| `SESSION_TTL_DAYS` | `30` | web only |
| `WEB_HOST` / `WEB_PORT` | `127.0.0.1` / `8000` | web only |

## GitHub Actions

`.github/workflows/ci.yml` runs lint, type checks and tests on every push and pull request,
then checks that the Docker image builds. Nothing is published.

`scripts/setup-github.sh [owner/repo]` interactively sets the repository's Actions
variables and secrets with `gh` (requires admin access). Secrets are kept to the minimum:

| Secrets | Variables |
|---|---|
| `TELEGRAM_BOT_TOKEN`, `SESSION_SECRET` (generated), `DEPLOY_SSH_KEY` (optional) | `TELEGRAM_OWNER_ID`, `TELEGRAM_BOT_USERNAME`, `DEFAULT_TIMEZONE`, `DEFAULT_REMINDER_TIME`, `MORNING_REMINDER_TIME`, `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PATH`, `SSH_KNOWN_HOSTS` |
