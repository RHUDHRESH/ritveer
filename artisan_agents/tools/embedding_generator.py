"""
Ollama-based embedding generator for semantic text analysis.

This module provides functionality to generate embeddings from text using Ollama's
embedding models for semantic matching and clustering applications.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Union
import httpx
from dataclasses import dataclass
import numpy as np


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    model: str = "nomic-embed-text"  # Default Ollama embedding model
    base_url: str = "http://localhost:11434"  # Default Ollama URL
    timeout: float = 30.0
    max_retries: int = 3
    batch_size: int = 10  # Process texts in batches


class EmbeddingGenerator:
    """
    Generate embeddings from text using Ollama's embedding models.

    This class provides both synchronous and asynchronous methods for generating
    embeddings from text content, with support for batch processing and error handling.
    """

    def __init__(self, config: EmbeddingConfig = None):
        """Initialize the embedding generator with configuration."""
        self.config = config or EmbeddingConfig()
        self.logger = logging.getLogger(__name__)
        self.client = httpx.Client(timeout=self.config.timeout)

    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, 'client'):
            self.client.close()

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text synchronously.

        Args:
            text (str): Input text to generate embedding for.

        Returns:
            Optional[List[float]]: Embedding vector or None if failed.
        """
        try:
            response = self.client.post(
                f"{self.config.base_url}/api/embeddings",
                json={
                    "model": self.config.model,
                    "prompt": text
                },
                timeout=self.config.timeout
            )
            response.raise_for_status()
            result = response.json()
            return result.get("embedding")
        except Exception as e:
            self.logger.error(f"Failed to generate embedding for text: {e}")
            return None

    async def generate_embedding_async(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text asynchronously.

        Args:
            text (str): Input text to generate embedding for.

        Returns:
            Optional[List[float]]: Embedding vector or None if failed.
        """
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            for attempt in range(self.config.max_retries):
                try:
                    response = await client.post(
                        f"{self.config.base_url}/api/embeddings",
                        json={
                            "model": self.config.model,
                            "prompt": text
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result.get("embedding")
                except Exception as e:
                    self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt == self.config.max_retries - 1:
                        self.logger.error(f"Failed to generate embedding after {self.config.max_retries} attempts")
                        return None
                    await asyncio.sleep(1)  # Wait before retry

    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts synchronously.

        Args:
            texts (List[str]): List of input texts.

        Returns:
            List[Optional[List[float]]]: List of embedding vectors.
        """
        embeddings = []
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            self.logger.info(f"Processing batch {i//self.config.batch_size + 1}/{(len(texts)-1)//self.config.batch_size + 1}")

            for text in batch:
                embedding = self.generate_embedding(text)
                embeddings.append(embedding)

        return embeddings

    async def generate_embeddings_batch_async(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts asynchronously.

        Args:
            texts (List[str]): List of input texts.

        Returns:
            List[Optional[List[float]]]: List of embedding vectors.
        """
        # Create tasks for all texts
        tasks = [self.generate_embedding_async(text) for text in texts]

        # Execute all tasks concurrently
        embeddings = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions that occurred
        processed_embeddings = []
        for i, result in enumerate(embeddings):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to generate embedding for text {i}: {result}")
                processed_embeddings.append(None)
            else:
                processed_embeddings.append(result)

        return processed_embeddings

    def cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1 (List[float]): First embedding vector.
            embedding2 (List[float]): Second embedding vector.

        Returns:
            float: Cosine similarity score between -1 and 1.
        """
        if not embedding1 or not embedding2:
            return 0.0

        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def find_similar_texts(self, query_embedding: List[float], text_embeddings: List[Dict[str, Any]],
                          top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find texts most similar to the query embedding.

        Args:
            query_embedding (List[float]): Query embedding vector.
            text_embeddings (List[Dict[str, Any]]): List of dicts with 'text' and 'embedding' keys.
            top_k (int): Number of similar texts to return.

        Returns:
            List[Dict[str, Any]]: Similar texts with similarity scores.
        """
        similarities = []

        for item in text_embeddings:
            embedding = item.get("embedding")
            if embedding:
                similarity = self.cosine_similarity(query_embedding, embedding)
                similarities.append({
                    "text": item.get("text", ""),
                    "similarity": similarity,
                    "metadata": item.get("metadata", {})
                })

        # Sort by similarity (descending) and return top k
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:top_k]

    def cluster_embeddings(self, embeddings: List[List[float]], threshold: float = 0.7) -> List[List[int]]:
        """
        Cluster embeddings based on similarity threshold.

        Args:
            embeddings (List[List[float]]): List of embedding vectors.
            threshold (float): Similarity threshold for clustering.

        Returns:
            List[List[int]]: List of clusters, where each cluster is a list of indices.
        """
        n = len(embeddings)
        if n == 0:
            return []

        # Initialize clusters - each point starts in its own cluster
        clusters = [[i] for i in range(n)]
        cluster_changed = True

        while cluster_changed:
            cluster_changed = False

            for i in range(n):
                for j in range(i + 1, n):
                    if (i in [idx for cluster in clusters for idx in cluster] and
                        j in [idx for cluster in clusters for idx in cluster]):

                        # Check if these points are in different clusters
                        cluster_i = None
                        cluster_j = None

                        for cluster in clusters:
                            if i in cluster:
                                cluster_i = cluster
                            if j in cluster:
                                cluster_j = cluster

                        if cluster_i != cluster_j:
                            # Check similarity
                            similarity = self.cosine_similarity(embeddings[i], embeddings[j])
                            if similarity >= threshold:
                                # Merge clusters
                                merged_cluster = cluster_i + cluster_j
                                clusters = [c for c in clusters if c != cluster_i and c != cluster_j]
                                clusters.append(merged_cluster)
                                cluster_changed = True

        return clusters

    def check_ollama_availability(self) -> bool:
        """
        Check if Ollama service is available and responding.

        Returns:
            bool: True if Ollama is available, False otherwise.
        """
        try:
            response = self.client.get(f"{self.config.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    def get_available_models(self) -> List[str]:
        """
        Get list of available models from Ollama.

        Returns:
            List[str]: List of available model names.
        """
        try:
            response = self.client.get(f"{self.config.base_url}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            return [model["name"] for model in models]
        except Exception as e:
            self.logger.error(f"Failed to get available models: {e}")
            return []


# Utility functions for common use cases
def generate_text_embedding(text: str, config: EmbeddingConfig = None) -> Optional[List[float]]:
    """Convenience function to generate embedding for a single text."""
    generator = EmbeddingGenerator(config)
    return generator.generate_embedding(text)


async def generate_text_embeddings_batch(texts: List[str], config: EmbeddingConfig = None) -> List[Optional[List[float]]]:
    """Convenience function to generate embeddings for multiple texts asynchronously."""
    generator = EmbeddingGenerator(config)
    return await generator.generate_embeddings_batch_async(texts)


# Basic logging setup
logging.basicConfig(level=logging.INFO)


# Tests for embedding_generator.py
import pytest


@pytest.fixture
def sample_texts():
    return [
        "handcrafted wooden furniture",
        "artisan made pottery",
        "traditional textile weaving",
        "modern ceramic design",
        "vintage furniture restoration"
    ]


@pytest.fixture
def embedding_config():
    return EmbeddingConfig(
        model="nomic-embed-text",
        base_url="http://localhost:11434"
    )


def test_embedding_generator_init():
    config = EmbeddingConfig()
    generator = EmbeddingGenerator(config)
    assert generator.config == config


def test_cosine_similarity():
    generator = EmbeddingGenerator()
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [0.0, 1.0, 0.0]
    vec3 = [1.0, 0.0, 0.0]

    # Orthogonal vectors should have similarity 0
    assert abs(generator.cosine_similarity(vec1, vec2)) < 1e-6
    # Identical vectors should have similarity 1
    assert abs(generator.cosine_similarity(vec1, vec3) - 1.0) < 1e-6


def test_find_similar_texts():
    generator = EmbeddingGenerator()

    # Mock embeddings for testing
    embeddings = [
        {"text": "wooden chair", "embedding": [1.0, 0.0, 0.0]},
        {"text": "metal table", "embedding": [0.0, 1.0, 0.0]},
        {"text": "wooden table", "embedding": [0.9, 0.1, 0.0]}
    ]

    query_embedding = [1.0, 0.0, 0.0]  # Similar to wooden chair
    similar = generator.find_similar_texts(query_embedding, embeddings, top_k=2)

    assert len(similar) == 2
    # Most similar should be wooden chair
    assert similar[0]["text"] == "wooden chair"


def test_cluster_embeddings():
    generator = EmbeddingGenerator()

    # Create embeddings that form two clear clusters
    cluster1 = [[1.0, 0.0], [0.9, 0.1], [0.8, 0.0]]
    cluster2 = [[0.0, 1.0], [0.1, 0.9], [0.0, 0.8]]
    embeddings = cluster1 + cluster2

    clusters = generator.cluster_embeddings(embeddings, threshold=0.8)

    # Should find 2 clusters
    assert len(clusters) == 2
    # Each cluster should have 3 points
    assert all(len(cluster) == 3 for cluster in clusters)


def test_check_ollama_availability(embedding_config):
    generator = EmbeddingGenerator(embedding_config)
    # This will likely return False since Ollama may not be running
    # but it should not raise an exception
    available = generator.check_ollama_availability()
    assert isinstance(available, bool)


def test_get_available_models(embedding_config):
    generator = EmbeddingGenerator(embedding_config)
    # This may return empty list if Ollama is not running
    # but it should not raise an exception
    models = generator.get_available_models()
    assert isinstance(models, list)
