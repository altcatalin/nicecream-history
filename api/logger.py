import logging

from aiohttp import web

from api import settings


def setup_logging(app: web.Application = None) -> None:
    basic_config = {
        "format": "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S %z",
        "level": logging.INFO
    }

    if settings["debug"]:
        basic_config["level"] = logging.DEBUG

    logging.basicConfig(**basic_config)


def get_logger(name: str = None):
    return logging.getLogger(name)
