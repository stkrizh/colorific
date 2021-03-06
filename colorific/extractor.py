from abc import ABC, abstractmethod
from collections import Counter
from io import BytesIO
from itertools import combinations
from typing import Dict, List

import numpy as np
from PIL import Image
from skimage.color import rgb2lab
from sklearn.cluster import KMeans

from . import color_names
from .image_loader import open_image
from .types import Color


COLORS_DIFFERENCE_THRESHOLD = 20
IMAGE_THUMBNAIL_SIZE = (300, 300)
MAX_NUMBER_OF_CLUSTERS = 12


class ColorExtractor(ABC):
    """
    Base class that defines common interface for color extraction.
    """

    @abstractmethod
    def extract(self, image: Image) -> List[Color]:
        ...

    def extract_from_bytes(self, image_data: bytes) -> List[Color]:
        with BytesIO(image_data) as buffer:
            image = open_image(buffer)
            colors = self.extract(image)
            image.close()
            return colors


class KMeansExtractor(ColorExtractor):
    """
    Extract main colors with KMeans clustering algorithm.

    See also
    --------
    https://en.wikipedia.org/wiki/K-means_clustering
    """

    def extract(self, image: Image) -> List[Color]:
        """
        Entry point for color palette extraction.
        """
        lab_image_data = self.prepare_image_data(image)
        clustering = KMeans(n_clusters=MAX_NUMBER_OF_CLUSTERS)
        clustering.fit(lab_image_data)

        centroids = self.merge_similar_colors(
            clustering.cluster_centers_, clustering.labels_
        )
        names_with_dist = color_names.find(centroids[:, :-1])
        return [
            Color(
                L=centroid[0],
                a=centroid[1],
                b=centroid[2],
                percentage=centroid[3],
                name=name,
                name_distance=name_distance,
            )
            for centroid, (name, name_distance) in zip(centroids, names_with_dist)
        ]

    def prepare_image_data(self, image: Image) -> np.ndarray:
        """
        Prepare image and convert it to data for cluster analysis.
        """
        rgb_image = image.convert("RGB")
        rgb_image.thumbnail(IMAGE_THUMBNAIL_SIZE, resample=Image.LANCZOS)
        rgb_image_data = np.expand_dims(
            np.array(rgb_image.getdata(), dtype=np.uint8), axis=0
        )
        lab_image_data = rgb2lab(rgb_image_data)[0]
        return lab_image_data

    def merge_similar_colors(
        self, centroids: np.ndarray, labels: np.ndarray
    ) -> np.ndarray:
        """
        Merge similar colors and return new cluster centroids and their percentage.

        Parameters
        ----------
        centroids : np.ndarray, [N_clusters, 3] shape
            Cluster centroids, represent main colors in CIELAB color space.

        labels : np.ndarray, [1, N_pixels] shape
            Cluster label for each pixel.

        Returns
        -------
        np.ndarray, [N_new_clusters, 4] shape
            New cluster centroids and their percentage.
        """
        label_counter: Dict[int, int] = Counter(labels)
        current_centroids: Dict[int, np.ndarray] = {}
        current_counts: Dict[int, int] = {}

        # Filter out clusters with 0 frequency
        for ix, centroid in enumerate(centroids):
            if label_counter[ix] == 0:
                continue
            current_centroids[ix] = centroid
            current_counts[ix] = label_counter[ix]

        while True:
            for ix_1, ix_2 in combinations(current_centroids, 2):
                # CIE76 color difference
                # https://en.wikipedia.org/wiki/Color_difference#CIE76
                color_difference = np.linalg.norm(
                    current_centroids[ix_1] - current_centroids[ix_2]
                )

                if color_difference < COLORS_DIFFERENCE_THRESHOLD:
                    if current_counts[ix_1] >= current_counts[ix_2]:
                        current_counts[ix_1] += current_counts.pop(ix_2)
                        current_centroids.pop(ix_2)
                    else:
                        current_counts[ix_2] += current_counts.pop(ix_1)
                        current_centroids.pop(ix_1)
                    break
            else:
                break

        assert current_centroids.keys() == current_counts.keys()

        new_centroids: np.ndarray = np.zeros(
            (len(current_centroids), 3), dtype=np.float64
        )
        new_counts: np.ndarray = np.zeros(len(current_centroids), dtype=np.float64)

        for new_ix, (ix, centroid) in enumerate(current_centroids.items()):
            new_centroids[new_ix] = current_centroids[ix]
            new_counts[new_ix] = current_counts[ix]

        return np.hstack(
            (
                new_centroids,
                new_counts.reshape((len(current_centroids), 1)) / np.sum(new_counts),
            )
        )
