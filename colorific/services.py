from typing import List, Optional

import sqlalchemy as sa
from aiopg.sa import SAConnection

from .types import Color, Image


async def get_images_by_color(
    connection: SAConnection,
    color: Color,
    image_count: int = 36,
    offset: int = 0,
    percentage_weight: float = 0.2,
) -> List[Image]:
    """
    Return images from DB ordered by color similarity.
    """

    query = sa.text(
        """
        SELECT
            image.id,
            image.origin,
            image.url_big,
            image.url_thumb,
            MIN(
                SQRT(
                    (c."L" / 100 - :L)^2 +
                    ((c.a + 128) / 256 - :a)^2 +
                    ((c.b + 128) / 256 - :b)^2 +
                    :percentage_weight * (c.percentage - 1)^2
                )
            ) as distance
        FROM image_color AS c JOIN image ON c.image_id = image.id
        GROUP BY image.id
        ORDER BY distance
        LIMIT :image_count
        OFFSET :offset;
        """
    )

    images: List[Image] = []
    async for row in await connection.execute(
        query,
        {
            "L": color.L / 100,
            "a": (color.a + 128) / 256,
            "b": (color.b + 128) / 256,
            "percentage_weight": percentage_weight,
            "image_count": image_count,
            "offset": offset,
        },
    ):
        images.append(
            Image(
                origin=row["origin"],
                url_big=row["url_big"],
                url_thumb=row["url_thumb"],
                id=row["id"],
            )
        )

    return images


async def get_image(connection: SAConnection, image_id: int) -> Optional[Image]:
    """
    Retrieve one image from DB. Return `None` if there is no
    image with `image_id` primary key.
    """
    sql = sa.text(
        """
        SELECT * FROM image WHERE id = :image_id;
        """
    )
    cursor = await connection.execute(sql, {"image_id": image_id})
    row = await cursor.fetchone()

    if row is None:
        return None

    return Image(
        id=row["id"],
        origin=row["origin"],
        url_big=row["url_big"],
        url_thumb=row["url_thumb"],
    )


async def get_image_colors(connection: SAConnection, image_id: int) -> List[Color]:
    """
    Retrieve a list of image colors from DB.
    """
    sql = sa.text(
        """
        SELECT * FROM image_color WHERE image_id = :image_id;
        """
    )
    colors: List[Color] = []
    async for row in connection.execute(sql, {"image_id": image_id}):
        color = Color(
            L=row["L"],
            a=row["a"],
            b=row["b"],
            percentage=row["percentage"],
            name=row["name"],
        )
        colors.append(color)

    return colors
