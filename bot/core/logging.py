"""Logging setup. Replaces the scattered print() calls in the old monolith."""

import logging


def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # discord.py is chatty at INFO for gateway events; keep it at WARNING.
    logging.getLogger("discord").setLevel(logging.WARNING)
