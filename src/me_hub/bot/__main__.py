import asyncio
import logging

from me_hub.bot.app import run
from me_hub.bot.config import BotSettings

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    asyncio.run(run(BotSettings()))  # type: ignore[call-arg]


if __name__ == "__main__":
    main()
