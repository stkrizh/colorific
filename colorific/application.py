import asyncio
import pathlib

import aiojobs.aiohttp
from aiohttp import ClientSession, TCPConnector, web

from . import db, routes, workers
from .extractor import KMeansExtractor
from .indexer import UnsplashIndexer
from .middlewares import cors_middleware
from .settings import config


HERE = pathlib.Path(__file__).parent


def init(setup_workers: bool = True) -> web.Application:
    application = web.Application(middlewares=[cors_middleware])

    routes.setup(application)
    aiojobs.aiohttp.setup(application)

    if setup_workers:
        application.cleanup_ctx.append(workers.setup)

    application.cleanup_ctx.append(db.setup)
    application.cleanup_ctx.append(setup_http_client)

    if config.colorific.image_indexing:
        application.cleanup_ctx.append(setup_image_indexing)

    return application


async def setup_http_client(app):
    app["http_client"] = ClientSession(
        connector=TCPConnector(force_close=True, enable_cleanup_closed=True)
    )
    yield
    await app["http_client"].close()


async def setup_image_indexing(app):
    color_extractor = KMeansExtractor()
    indexer = UnsplashIndexer(
        color_extractor=color_extractor,
        executor=app["executor"],
        http_client=app["http_client"],
        db_pool=app["db"],
    )
    asyncio.create_task(indexer.run())
    yield
