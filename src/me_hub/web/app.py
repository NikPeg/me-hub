import functools
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from me_hub.core.models import User, utcnow
from me_hub.web.config import WebSettings
from me_hub.web.dashboard import build_dashboard
from me_hub.web.sessions import SESSION_COOKIE, issue_session, read_session
from me_hub.web.telegram_auth import TelegramAuthError, verify_login

NO_STORE = {"Cache-Control": "no-store"}
LOGIN_FAILED_URL = "/?error=login"

Handler = Callable[[Request], Awaitable[Response]]


def json_response(content: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(content, status_code=status_code, headers=NO_STORE)


def is_owner_session(request: Request) -> bool:
    settings: WebSettings = request.app.state.settings
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        return False
    user_id = read_session(token, settings.session_key, utcnow())
    return user_id == settings.telegram_owner_id


def owner_only(handler: Handler) -> Handler:
    @functools.wraps(handler)
    async def wrapper(request: Request) -> Response:
        if not is_owner_session(request):
            return json_response({"detail": "Not authenticated"}, status_code=401)
        return await handler(request)

    return wrapper


async def config(request: Request) -> Response:
    settings: WebSettings = request.app.state.settings
    return json_response({"bot_username": settings.telegram_bot_username})


async def telegram_login(request: Request) -> Response:
    settings: WebSettings = request.app.state.settings
    now = utcnow()
    try:
        user_id = verify_login(
            dict(request.query_params), settings.telegram_bot_token.get_secret_value(), now
        )
    except TelegramAuthError:
        return RedirectResponse(LOGIN_FAILED_URL, status_code=303, headers=NO_STORE)
    if user_id != settings.telegram_owner_id:
        return RedirectResponse(LOGIN_FAILED_URL, status_code=303, headers=NO_STORE)
    token = issue_session(user_id, settings.session_key, now, settings.session_ttl)
    response = RedirectResponse("/", status_code=303, headers=NO_STORE)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(settings.session_ttl.total_seconds()),
        httponly=True,
        secure=True,
        samesite="strict",
    )
    return response


async def logout(_request: Request) -> Response:
    response = json_response({})
    response.delete_cookie(SESSION_COOKIE, httponly=True, secure=True, samesite="strict")
    return response


@owner_only
async def me(_request: Request) -> Response:
    return json_response({})


@owner_only
async def dashboard(request: Request) -> Response:
    settings: WebSettings = request.app.state.settings
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        user = await session.get(User, settings.telegram_owner_id)
        if user is None:
            return json_response({"detail": "Owner has not started the bot yet"}, status_code=503)
        return json_response((await build_dashboard(session, user)).model_dump(mode="json"))


def create_app(
    settings: WebSettings, session_factory: async_sessionmaker[AsyncSession]
) -> Starlette:
    app = Starlette(
        routes=[
            Route("/api/config", config),
            Route("/api/auth/telegram", telegram_login),
            Route("/api/auth/logout", logout, methods=["POST"]),
            Route("/api/me", me),
            Route("/api/dashboard", dashboard),
        ]
    )
    app.state.settings = settings
    app.state.session_factory = session_factory
    return app
