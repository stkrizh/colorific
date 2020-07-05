from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from skimage.color import lab2rgb, rgb2lab


@dataclass
class Color:
    """
    Represents a color in CIELAB color space.

    See also
    --------
    https://en.wikipedia.org/wiki/CIELAB_color_space
    """

    L: float
    a: float
    b: float
    percentage: float

    @classmethod
    def from_rgb(cls, r: int, g: int, b: int, percentage: float = 1.0) -> "Color":
        lab: np.ndarray = rgb2lab(np.array([r, g, b], dtype=np.float64) / 255)
        return cls(L=lab[0], a=lab[1], b=lab[2], percentage=percentage)

    def __post_init__(self):
        rgb: np.ndarray = lab2rgb(np.array([self.L, self.a, self.b], dtype=np.float64))
        self.rgb: List[int] = [int(np.round(value * 255)) for value in rgb]


@dataclass
class Image:
    origin: str
    url_big: str
    url_thumb: str
    id: Optional[int] = None
