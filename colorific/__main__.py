import logging
from logging.config import dictConfig

from aiohttp import web

from . import application


dictConfig(
    {
        "version": 1,
        "formatters": {
            "f": {"format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s"}
        },
        "handlers": {
            "h": {
                "class": "logging.StreamHandler",
                "formatter": "f",
                "level": logging.DEBUG,
            }
        },
        "loggers": {
            "colorific": {"handlers": ["h"], "level": logging.INFO},
            "aiohttp": {"handlers": ["h"], "level": logging.INFO},
        },
    }
)

web.run_app(application.init())
