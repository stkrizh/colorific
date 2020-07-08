import json
from pathlib import Path
from typing import List, Tuple, Union

import numpy as np
from skimage.color import rgb2lab
from sklearn.neighbors import KDTree


BASE_DIR = Path(__file__).parent.parent
COLOR_NAMES: List[str]
COLOR_TREE: KDTree


def init_color_data() -> Tuple[List[str], KDTree]:
    """
    Read color names from `color_names.json` file and prepare data
    structures for color names search.
    """
    color_data = json.loads((BASE_DIR / "color_names.json").read_text())
    names: List[str] = []
    colors_rgb: List[List[int]] = []

    for color in color_data:
        name = color["name"]
        names.append(name)
        hex_code = color["hex"]
        rgb: List[int] = [
            int(hex_code[1:3], 16),
            int(hex_code[3:5], 16),
            int(hex_code[5:], 16),
        ]
        colors_rgb.append(rgb)

    tree = KDTree(rgb2lab(np.array(colors_rgb, dtype=np.float32) / 255), leaf_size=10)
    return names, tree


def find(X: np.ndarray) -> List[Tuple[str, float]]:
    """
    Find closest color names.

    Parameters
    ----------
    X: array-like of shape (n_colors, 3)
        Represents N colors in CIELAB color space.

    Returns
    ------
        List of tuples (color name, distance)
    """
    distances, indexes = COLOR_TREE.query(X)
    return [(COLOR_NAMES[ix[0]], d[0]) for (d, ix) in zip(distances, indexes)]


def find_by_hex(hex_codes: Union[str, List[str]]) -> List[Tuple[str, float]]:
    """
    Find closest color names by RGB hex codes.

    Parameters
    ----------
    hex_codes:
        List of RGB hex codes (e.g. ["aaff00", "ff0000"])

    Returns
    ------
        List of tuples (color name, distance)
    """
    hex_codes = [hex_codes] if isinstance(hex_codes, str) else hex_codes

    rgb: List[List[int]] = []
    for hex_code in hex_codes:
        rgb.append(
            [int(hex_code[:2], 16), int(hex_code[2:4], 16), int(hex_code[4:], 16)]
        )

    return find(rgb2lab(np.array(rgb, dtype=np.float32) / 255))


COLOR_NAMES, COLOR_TREE = init_color_data()
