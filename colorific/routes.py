from aiohttp.web import Application

from . import views


def setup(app: Application):
    app.router.add_view(r"/image", views.ColorExtractionView)
    app.router.add_view(r"/images", views.ImageListView)
    app.router.add_view(r"/images/{image_id:\d+}", views.ImageDetailView)
