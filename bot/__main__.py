"""Entry point: ``python -m bot``."""

from bot.core import config
from bot.core.bot import MiniGamesBot
from bot.core.logging import setup_logging


def main():
    setup_logging()
    token = config.require_token()
    bot = MiniGamesBot()
    # log_handler=None: we configure logging ourselves in setup_logging().
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
