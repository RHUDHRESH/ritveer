# Local spatial clustering utilities for supplier-artisan matching

import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np
from math import radians, cos, sin, sqrt, atan2


@dataclass
class SpatialClustererConfig:
    num_clusters: int = 3
    eps: float = 0.5  # DBSCAN distance threshold in km
    min_samples: int = 5  # DBSCAN minimum samples


class SpatialClusterer:
    """
    Class for spatial clustering and querying of geolocated points.

    Provides K-means and DBSCAN clustering on latitude/longitude coordinates,
    nearest location search, and retrieval of spatial regions.

    Attributes:
        config (SpatialClustererConfig): Configuration parameters.
    """

    def __init__(self, config: SpatialClustererConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """
        Calculate the great-circle distance between two points on the Earth surface.

        Args:
            coord1 (tuple): (latitude, longitude) of point 1.
            coord2 (tuple): (latitude, longitude) of point 2.

        Returns:
            float: Distance in kilometers.
        """
        lat1, lon1 = coord1
        lat2, lon2 = coord2

        R = 6371.0  # Earth radius in kilometers
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)

        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c
        return distance

    def cluster_locations(self, locations: List[Tuple[float, float]], method: str = "kmeans") -> List[int]:
        """
        Cluster geographic locations using the specified method.

        Args:
            locations (List[Tuple[float, float]]): List of (lat, lon) points.
            method (str): Clustering method - 'kmeans' or 'dbscan'.

        Returns:
            List[int]: Cluster labels for each point.
        """
        if method == "kmeans":
            return self._kmeans_cluster(locations)
        elif method == "dbscan":
            return self._dbscan_cluster(locations)
        else:
            self.logger.error(f"Invalid clustering method {method}")
            raise ValueError(f"Invalid clustering method {method}")

    def _kmeans_cluster(self, locations: List[Tuple[float, float]]) -> List[int]:
        n = len(locations)
        k = self.config.num_clusters
        if n == 0:
            self.logger.warning("No locations provided for clustering.")
            return []

        coords = np.array(locations)

        # Initialize centroids - pick first k points
        centroids = coords[:k].copy()
        labels = np.zeros(n, dtype=int)

        for iteration in range(100):
            # Assign clusters
            for i in range(n):
                dists = np.array([self.haversine_distance(locations[i], tuple(cent)) for cent in centroids])
                labels[i] = np.argmin(dists)
            # Update centroids
            new_centroids = np.array([
                coords[labels == idx].mean(axis=0) if np.any(labels == idx) else centroids[idx]
                for idx in range(k)
            ])
            if np.allclose(centroids, new_centroids):
                self.logger.debug(f"Kmeans converged in {iteration} iterations.")
                break
            centroids = new_centroids

        return labels.tolist()

    def _dbscan_cluster(self, locations: List[Tuple[float, float]]) -> List[int]:
        n = len(locations)
        if n == 0:
            self.logger.warning("No locations provided for clustering.")
            return []

        labels = [-1] * n
        coords = np.array(locations)

        def region_query(point_idx):
            neighbors = []
            for i in range(n):
                if self.haversine_distance(locations[point_idx], locations[i]) <= self.config.eps:
                    neighbors.append(i)
            return neighbors

        cluster_id = 0
        visited = set()

        for i in range(n):
            if i in visited:
                continue
            visited.add(i)
            neighbors = region_query(i)
            if len(neighbors) < self.config.min_samples:
                labels[i] = -1  # noise
                continue

            labels[i] = cluster_id
            seeds = neighbors.copy()
            seeds.remove(i)

            while seeds:
                current_point = seeds.pop()
                if current_point not in visited:
                    visited.add(current_point)
                    current_neighbors = region_query(current_point)
                    if len(current_neighbors) >= self.config.min_samples:
                        seeds.extend([n for n in current_neighbors if n not in seeds])
                if labels[current_point] == -1:
                    labels[current_point] = cluster_id
            cluster_id += 1

        return labels

    def find_nearest(self, locations: List[Tuple[float, float]], point: Tuple[float, float]) -> Optional[int]:
        """
        Find the index of the nearest location in the list to the given point.

        Args:
            locations (List[Tuple[float, float]]): List of (lat, lon) points.
            point (Tuple[float, float]): Query (lat, lon).

        Returns:
            Optional[int]: Index of nearest location or None if empty.
        """
        if not locations:
            self.logger.warning("Empty locations list provided to find_nearest.")
            return None

        min_idx = None
        min_dist = float('inf')

        for i, loc in enumerate(locations):
            dist = self.haversine_distance(loc, point)
            if dist < min_dist:
                min_dist = dist
                min_idx = i

        return min_idx

    def get_regions(self, locations: List[Tuple[float, float]], labels: List[int]) -> List[List[Tuple[float, float]]]:
        """
        Group locations by cluster labels.

        Args:
            locations (List[Tuple[float, float]]): List of (lat, lon) points.
            labels (List[int]): Cluster labels corresponding to locations.

        Returns:
            List[List[Tuple[float, float]]]: Grouped locations by clusters.
        """
        clusters = {}
        for loc, label in zip(locations, labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(loc)

        return list(clusters.values())

    def silhouette_score(self, locations: List[Tuple[float, float]], labels: List[int]) -> Optional[float]:
        """
        Compute silhouette score for the clustering.

        Args:
            locations (List[Tuple[float, float]]): List of (lat, lon).
            labels (List[int]): Cluster labels.

        Returns:
            Optional[float]: Silhouette score or None if not computable.
        """
        n = len(locations)
        if n <= 1:
            return None

        unique_labels = set(labels)
        if len(unique_labels) == 1 or (-1 in unique_labels and len(unique_labels) == 2):
            return None

        coords = locations

        def a(i):  # Mean intra-cluster distance
            own_cluster = labels[i]
            same_cluster_points = [j for j in range(n) if labels[j] == own_cluster and j != i]
            if not same_cluster_points:
                return 0
            return np.mean([self.haversine_distance(coords[i], coords[j]) for j in same_cluster_points])

        def b(i):  # Mean nearest-cluster distance
            other_clusters = [l for l in unique_labels if l != labels[i] and l != -1]
            min_dist = float('inf')
            for oc in other_clusters:
                points = [j for j in range(n) if labels[j] == oc]
                if not points:
                    continue
                dist = np.mean([self.haversine_distance(coords[i], coords[j]) for j in points])
                if dist < min_dist:
                    min_dist = dist
            return min_dist

        s = []
        for i in range(n):
            ai = a(i)
            bi = b(i)
            denom = max(ai, bi)
            if denom == 0:
                s.append(0)
            else:
                s.append((bi - ai) / denom)

        score = np.mean(s)
        return score

    def inertia(self, locations: List[Tuple[float, float]], labels: List[int]) -> float:
        """
        Compute cluster inertia as sum of squared distances to cluster centers (for K-means).

        Args:
            locations (List[Tuple[float, float]]): Points.
            labels (List[int]): Cluster labels.

        Returns:
            float: Inertia value.
        """
        coords = np.array(locations)
        inertia = 0.0
        unique_labels = set(labels)

        for label in unique_labels:
            cluster_points = coords[np.array(labels) == label]
            if len(cluster_points) == 0 or label == -1:
                continue
            centroid = np.mean(cluster_points, axis=0)
            distances = np.array([self.haversine_distance(tuple(point), tuple(centroid)) for point in cluster_points])
            inertia += np.sum(distances ** 2)

        return inertia


# Basic logging setup
logging.basicConfig(level=logging.DEBUG)


# Tests for spatial_clustering.py
import pytest


@pytest.fixture
def sample_locations():
    return [
        (12.9715987, 77.594566),  # Bengaluru
        (13.0826802, 80.2707184),  # Chennai
        (17.385044, 78.486671),    # Hyderabad
        (19.0759837, 72.8776559),  # Mumbai
        (28.7040592, 77.1024902),  # Delhi
    ]


def test_haversine_distance(sample_locations):
    sc = SpatialClusterer(SpatialClustererConfig())
    dist = sc.haversine_distance(sample_locations[0], sample_locations[1])
    assert dist > 0


def test_kmeans_cluster(sample_locations):
    sc = SpatialClusterer(SpatialClustererConfig(num_clusters=2))
    labels = sc.cluster_locations(sample_locations, method="kmeans")
    assert len(labels) == len(sample_locations)


def test_dbscan_cluster(sample_locations):
    sc = SpatialClusterer(SpatialClustererConfig(eps=1500, min_samples=1))
    labels = sc.cluster_locations(sample_locations, method="dbscan")
    assert len(labels) == len(sample_locations)


def test_find_nearest(sample_locations):
    sc = SpatialClusterer(SpatialClustererConfig())
    nearest_idx = sc.find_nearest(sample_locations, (12.9716, 77.6))
    assert nearest_idx == 0


def test_get_regions_and_inertia(sample_locations):
    sc = SpatialClusterer(SpatialClustererConfig(num_clusters=2))
    labels = sc.cluster_locations(sample_locations, method="kmeans")
    regions = sc.get_regions(sample_locations, labels)
    inertia = sc.inertia(sample_locations, labels)
    assert isinstance(regions, list)
    assert inertia >= 0


def test_silhouette_score(sample_locations):
    sc = SpatialClusterer(SpatialClustererConfig(num_clusters=2))
    labels = sc.cluster_locations(sample_locations, method="kmeans")
    score = sc.silhouette_score(sample_locations, labels)
    assert score is not None
