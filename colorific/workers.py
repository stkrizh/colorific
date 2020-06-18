import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import Coroutine, List

from aiohttp.web import Application

from .settings import config


async def setup(app: Application):
    await on_startup(app)
    yield
    await on_cleanup(app)


async def on_startup(app: Application):
    """
    Warm up workers.
    """
    n_workers: int = config.colorific.pool_exec_size
    app["executor"] = ProcessPoolExecutor(max_workers=n_workers)

    loop = asyncio.get_running_loop()
    futures: List[Coroutine] = [
        loop.run_in_executor(app["executor"], warm_up) for _ in range(n_workers)
    ]
    await asyncio.wait(futures)


async def on_cleanup(app: Application):
    executor = app["executor"]
    executor.shutdown(wait=True)


def warm_up():
    ...
