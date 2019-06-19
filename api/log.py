import logging

from aiohttp import web

from api import settings


async def configure_logging(app: web.Application = None) -> None:
    basic_config = {
        "format": "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S",
        "level": logging.INFO
    }

    if settings["debug"]:
        basic_config["level"] = logging.DEBUG

    logging.basicConfig(**basic_config)
