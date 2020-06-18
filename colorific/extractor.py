from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from PIL import Image
from skimage.color import lab2rgb


@dataclass
class Color:
    """
    Represents a color in CIELAB color space.

    See also:
    ---------
    https://en.wikipedia.org/wiki/CIELAB_color_space
    """

    L: float
    a: float
    b: float
    percentage: float

    def __post_init__(self):
        _rgb: np.ndarray = lab2rgb(np.array([self.L, self.a, self.b], dtype=np.float32))
        self.rgb: List[int] = [int(np.round(value * 255)) for value in _rgb]


class ColorExtractor(ABC):
    """
    Base class that defines common interface for color exctraction.
    """

    @abstractmethod
    def extract(self, image: Image) -> List[Color]:
        ...
