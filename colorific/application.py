import pathlib

import aiojobs.aiohttp
from aiohttp import web

from . import routes, workers

HERE = pathlib.Path(__file__).parent


def init(setup_workers: bool = False) -> web.Application:
    application = web.Application()

    # Setup ------------------------------
    routes.setup(application)
    aiojobs.aiohttp.setup(application)

    if setup_workers:
        application.cleanup_ctx.append(workers.setup)

    return application
