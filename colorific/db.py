import aiopg.sa
import sqlalchemy as sa
from aiohttp.web import Application

from .settings import config


METADATA = sa.MetaData()


image = sa.Table(
    "image",
    METADATA,
    sa.Column("id", sa.Integer(), primary_key=True),
    sa.Column("origin", sa.String(), nullable=False, unique=True),
    sa.Column("url_big", sa.String(), nullable=False),
    sa.Column("url_thumb", sa.String(), nullable=False),
    sa.Column(
        "indexed_at",
        sa.DateTime(),
        nullable=False,
        server_default=sa.text("(now() at time zone 'utc')"),
    ),
)


image_color = sa.Table(
    "image_color",
    METADATA,
    sa.Column("id", sa.Integer(), primary_key=True),
    sa.Column("image_id", sa.Integer(), sa.ForeignKey("image.id"), nullable=False),
    sa.Column("L", sa.Float(), nullable=False),
    sa.Column("a", sa.Float(), nullable=False),
    sa.Column("b", sa.Float(), nullable=False),
    sa.Column("percentage", sa.Float(), nullable=False),
    sa.Column("name", sa.String(), nullable=True),
    sa.Column("name_distance", sa.Float(), nullable=True),
)


async def setup(app: Application):
    engine = await aiopg.sa.create_engine(config.postgres.dsn, echo=True)
    app["db"] = engine
    yield
    app["db"].close()
    await app["db"].wait_closed()


def create_engine():
    """
    Create new (synchronous) connection to DB.
    If test is True, then create engine with the testing DB.
    """
    engine = sa.create_engine(config.postgres.dsn)
    return engine
