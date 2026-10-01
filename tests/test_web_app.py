from collections.abc import AsyncIterator

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from web_helpers import BOT_TOKEN, NOW, signed_login

from me_hub.core.habits import add_habit
from me_hub.core.models import User
from me_hub.web.app import create_app
from me_hub.web.config import WebSettings
from me_hub.web.sessions import SESSION_COOKIE

OWNER_ID = 123456789


@pytest.fixture
def settings(database_url: str) -> WebSettings:
    return WebSettings(
        database_url=database_url,
        telegram_bot_token=SecretStr(BOT_TOKEN),
        telegram_bot_username="me_hub_bot",
        telegram_owner_id=OWNER_ID,
        session_secret=SecretStr("s" * 32),
    )


@pytest.fixture
async def client(
    settings: WebSettings, session_factory: async_sessionmaker[AsyncSession]
) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=create_app(settings, session_factory))
    async with httpx.AsyncClient(transport=transport, base_url="https://testserver") as client:
        yield client


@pytest.fixture
def fresh_login(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("me_hub.web.app.utcnow", lambda: NOW)


async def log_in(client: httpx.AsyncClient, **overrides: str) -> httpx.Response:
    return await client.get("/api/auth/telegram", params=signed_login(**overrides))


async def test_config_exposes_bot_username(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/config")

    assert response.json() == {"bot_username": "me_hub_bot"}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("path", ["/api/me", "/api/dashboard"])
async def test_protected_routes_require_a_session(client: httpx.AsyncClient, path: str) -> None:
    assert (await client.get(path)).status_code == 401


async def test_login_sets_a_session_that_opens_protected_routes(
    client: httpx.AsyncClient, fresh_login: None
) -> None:
    response = await log_in(client)

    assert (response.status_code, response.headers["location"]) == (303, "/")
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=strict" in cookie
    assert (await client.get("/api/me")).status_code == 200


async def test_login_rejects_forged_payload(client: httpx.AsyncClient, fresh_login: None) -> None:
    response = await client.get("/api/auth/telegram", params=signed_login() | {"hash": "0" * 64})

    assert (response.status_code, response.headers["location"]) == (303, "/?error=login")
    assert SESSION_COOKIE not in client.cookies


async def test_login_rejects_other_telegram_users(
    client: httpx.AsyncClient, fresh_login: None
) -> None:
    response = await log_in(client, id="42")

    assert response.headers["location"] == "/?error=login"
    assert (await client.get("/api/me")).status_code == 401


async def test_logout_ends_the_session(client: httpx.AsyncClient, fresh_login: None) -> None:
    await log_in(client)

    assert (await client.post("/api/auth/logout")).status_code == 200
    assert (await client.get("/api/me")).status_code == 401


async def test_dashboard_returns_grids(
    client: httpx.AsyncClient, fresh_login: None, session: AsyncSession, owner: User
) -> None:
    await add_habit(session, owner, "Run")
    await session.commit()
    await log_in(client)

    response = await client.get("/api/dashboard")

    body = response.json()
    assert response.status_code == 200
    assert [habit["name"] for habit in body["habits"]] == ["Run"]
    assert len(body["overall"]) == len(body["habits"][0]["days"])


async def test_dashboard_is_unavailable_until_the_owner_started_the_bot(
    client: httpx.AsyncClient, fresh_login: None
) -> None:
    await log_in(client)

    assert (await client.get("/api/dashboard")).status_code == 503
