from typing import List

import sqlalchemy as sa
from aiopg.sa import SAConnection

from .types import Color, Image


async def get_images_by_color(
    connection: SAConnection,
    color: Color,
    image_count: int = 30,
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
