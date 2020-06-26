import pathlib

import aiojobs.aiohttp
from aiohttp import ClientSession, web

from . import db, routes, workers

HERE = pathlib.Path(__file__).parent


def init(setup_workers: bool = True) -> web.Application:
    application = web.Application()

    # Setup ------------------------------
    routes.setup(application)
    aiojobs.aiohttp.setup(application)

    if setup_workers:
        application.cleanup_ctx.append(workers.setup)

    application.cleanup_ctx.append(db.setup)
    application.cleanup_ctx.append(setup_http_client)

    return application


async def setup_http_client(app):
    app["http_client"] = ClientSession()
    yield
    await app["http_client"].close()
