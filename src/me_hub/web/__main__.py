import asyncio
import logging

import uvicorn

from me_hub.core.db import create_engine, create_session_factory
from me_hub.web.app import create_app
from me_hub.web.config import WebSettings

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


async def run(settings: WebSettings) -> None:
    engine = create_engine(settings.database_url)
    app = create_app(settings, create_session_factory(engine))
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=settings.web_host,
            port=settings.web_port,
            proxy_headers=True,
            forwarded_allow_ips="127.0.0.1",
            log_config=None,
        )
    )
    try:
        await server.serve()
    finally:
        await engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    asyncio.run(run(WebSettings()))  # type: ignore[call-arg]


if __name__ == "__main__":
    main()
