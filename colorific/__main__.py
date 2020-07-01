import logging

from aiohttp import web

from . import application


logging.basicConfig(level=logging.INFO)
web.run_app(application.init())
