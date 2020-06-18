from aiohttp.web import Application

from . import views


def setup(app: Application):
    app.router.add_view("/", views.IndexView)
