"""
Comprehensive tests for the embedding generator module.

Tests cover all functionality including embedding generation, similarity calculations,
clustering, and error handling scenarios.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock
import json
from artisan_agents.tools.embedding_generator import (
    EmbeddingGenerator,
    EmbeddingConfig,
    generate_text_embedding,
    generate_text_embeddings_batch
)


@pytest.fixture
def embedding_config():
    """Standard embedding configuration for testing."""
    return EmbeddingConfig(
        model="nomic-embed-text",
        base_url="http://localhost:11434",
        timeout=10.0,
        max_retries=2,
        batch_size=5
    )


@pytest.fixture
def sample_texts():
    """Sample texts for testing."""
    return [
        "handcrafted wooden furniture",
        "artisan made pottery",
        "traditional textile weaving",
        "modern ceramic design",
        "vintage furniture restoration",
        "ceramic pottery techniques",
        "wood carving craftsmanship",
        "textile art and design"
    ]


@pytest.fixture
def mock_embedding_response():
    """Mock embedding response from Ollama."""
    return {
        "embedding": [0.1, 0.2, 0.3, 0.4, 0.5] * 20  # 100-dimensional vector
    }


class TestEmbeddingConfig:
    """Test EmbeddingConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EmbeddingConfig()
        assert config.model == "nomic-embed-text"
        assert config.base_url == "http://localhost:11434"
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.batch_size == 10

    def test_custom_config(self):
        """Test custom configuration values."""
        config = EmbeddingConfig(
            model="custom-model",
            base_url="http://custom:8080",
            timeout=60.0,
            max_retries=5,
            batch_size=20
        )
        assert config.model == "custom-model"
        assert config.base_url == "http://custom:8080"
        assert config.timeout == 60.0
        assert config.max_retries == 5
        assert config.batch_size == 20


class TestEmbeddingGenerator:
    """Test EmbeddingGenerator class."""

    def test_initialization(self, embedding_config):
        """Test generator initialization."""
        generator = EmbeddingGenerator(embedding_config)
        assert generator.config == embedding_config
        assert generator.client is not None

    def test_initialization_default_config(self):
        """Test generator initialization with default config."""
        generator = EmbeddingGenerator()
        assert generator.config.model == "nomic-embed-text"
        assert generator.client is not None

    @patch('httpx.Client.post')
    def test_generate_embedding_success(self, mock_post, embedding_config, mock_embedding_response):
        """Test successful embedding generation."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_embedding_response

        generator = EmbeddingGenerator(embedding_config)
        result = generator.generate_embedding("test text")

        assert result is not None
        assert len(result) == 100  # Based on our mock response
        mock_post.assert_called_once()

    @patch('httpx.Client.post')
    def test_generate_embedding_failure(self, mock_post, embedding_config):
        """Test embedding generation failure."""
        mock_post.return_value.status_code = 500
        mock_post.return_value.raise_for_status.side_effect = Exception("Server error")

        generator = EmbeddingGenerator(embedding_config)
        result = generator.generate_embedding("test text")

        assert result is None

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_generate_embedding_async_success(self, mock_post, embedding_config, mock_embedding_response):
        """Test successful async embedding generation."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_embedding_response

        generator = EmbeddingGenerator(embedding_config)
        result = await generator.generate_embedding_async("test text")

        assert result is not None
        assert len(result) == 100

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_generate_embedding_async_retry(self, mock_post, embedding_config, mock_embedding_response):
        """Test async embedding generation with retries."""
        # First two calls fail, third succeeds
        mock_post.side_effect = [
            Mock(status_code=500, raise_for_status=Mock(side_effect=Exception("Error"))),
            Mock(status_code=500, raise_for_status=Mock(side_effect=Exception("Error"))),
            Mock(status_code=200, json=Mock(return_value=mock_embedding_response))
        ]

        generator = EmbeddingGenerator(embedding_config)
        result = await generator.generate_embedding_async("test text")

        assert result is not None
        assert mock_post.call_count == 3

    def test_generate_embeddings_batch(self, embedding_config, sample_texts, mock_embedding_response):
        """Test batch embedding generation."""
        with patch.object(EmbeddingGenerator, 'generate_embedding', return_value=mock_embedding_response['embedding']):
            generator = EmbeddingGenerator(embedding_config)
            results = generator.generate_embeddings_batch(sample_texts[:3])

            assert len(results) == 3
            assert all(result is not None for result in results)

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_async(self, embedding_config, sample_texts, mock_embedding_response):
        """Test async batch embedding generation."""
        with patch.object(EmbeddingGenerator, 'generate_embedding_async', return_value=mock_embedding_response['embedding']):
            generator = EmbeddingGenerator(embedding_config)
            results = await generator.generate_embeddings_batch_async(sample_texts[:3])

            assert len(results) == 3
            assert all(result is not None for result in results)

    def test_cosine_similarity(self, embedding_config):
        """Test cosine similarity calculation."""
        generator = EmbeddingGenerator(embedding_config)

        # Identical vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = generator.cosine_similarity(vec1, vec2)
        assert abs(similarity - 1.0) < 1e-6

        # Orthogonal vectors
        vec3 = [0.0, 1.0, 0.0]
        similarity = generator.cosine_similarity(vec1, vec3)
        assert abs(similarity) < 1e-6

        # Opposite vectors
        vec4 = [-1.0, 0.0, 0.0]
        similarity = generator.cosine_similarity(vec1, vec4)
        assert abs(similarity - (-1.0)) < 1e-6

    def test_cosine_similarity_empty_vectors(self, embedding_config):
        """Test cosine similarity with empty vectors."""
        generator = EmbeddingGenerator(embedding_config)

        similarity = generator.cosine_similarity([], [])
        assert similarity == 0.0

        similarity = generator.cosine_similarity([1.0, 0.0], [])
        assert similarity == 0.0

    def test_find_similar_texts(self, embedding_config):
        """Test finding similar texts."""
        generator = EmbeddingGenerator(embedding_config)

        # Mock embeddings with known similarities
        text_embeddings = [
            {"text": "wooden chair", "embedding": [1.0, 0.0, 0.0]},
            {"text": "metal table", "embedding": [0.0, 1.0, 0.0]},
            {"text": "wooden table", "embedding": [0.9, 0.1, 0.0]}
        ]

        query_embedding = [1.0, 0.0, 0.0]  # Most similar to wooden chair
        similar = generator.find_similar_texts(query_embedding, text_embeddings, top_k=2)

        assert len(similar) == 2
        assert similar[0]["text"] == "wooden chair"
        assert similar[0]["similarity"] == 1.0
        assert similar[1]["text"] == "wooden table"
        assert similar[1]["similarity"] < 1.0

    def test_cluster_embeddings(self, embedding_config):
        """Test embedding clustering."""
        generator = EmbeddingGenerator(embedding_config)

        # Create two distinct clusters
        cluster1 = [[1.0, 0.0], [0.9, 0.1], [0.8, 0.0]]
        cluster2 = [[0.0, 1.0], [0.1, 0.9], [0.0, 0.8]]
        embeddings = cluster1 + cluster2

        clusters = generator.cluster_embeddings(embeddings, threshold=0.8)

        # Should find 2 clusters
        assert len(clusters) == 2
        # Each cluster should have 3 points
        assert all(len(cluster) == 3 for cluster in clusters)

    def test_cluster_embeddings_empty(self, embedding_config):
        """Test clustering with empty embeddings."""
        generator = EmbeddingGenerator(embedding_config)
        clusters = generator.cluster_embeddings([])
        assert clusters == []

    @patch('httpx.Client.get')
    def test_check_ollama_availability_success(self, mock_get, embedding_config):
        """Test Ollama availability check success."""
        mock_get.return_value.status_code = 200

        generator = EmbeddingGenerator(embedding_config)
        available = generator.check_ollama_availability()

        assert available is True
        mock_get.assert_called_once()

    @patch('httpx.Client.get')
    def test_check_ollama_availability_failure(self, mock_get, embedding_config):
        """Test Ollama availability check failure."""
        mock_get.return_value.status_code = 500

        generator = EmbeddingGenerator(embedding_config)
        available = generator.check_ollama_availability()

        assert available is False

    @patch('httpx.Client.get')
    def test_get_available_models_success(self, mock_get, embedding_config):
        """Test getting available models success."""
        mock_response = {
            "models": [
                {"name": "model1"},
                {"name": "model2"}
            ]
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        generator = EmbeddingGenerator(embedding_config)
        models = generator.get_available_models()

        assert models == ["model1", "model2"]

    @patch('httpx.Client.get')
    def test_get_available_models_failure(self, mock_get, embedding_config):
        """Test getting available models failure."""
        mock_get.return_value.status_code = 500

        generator = EmbeddingGenerator(embedding_config)
        models = generator.get_available_models()

        assert models == []


class TestUtilityFunctions:
    """Test utility functions."""

    @patch('artisan_agents.tools.embedding_generator.EmbeddingGenerator.generate_embedding')
    def test_generate_text_embedding(self, mock_generate):
        """Test convenience function for single embedding."""
        mock_generate.return_value = [0.1, 0.2, 0.3]

        result = generate_text_embedding("test text")

        assert result == [0.1, 0.2, 0.3]
        mock_generate.assert_called_once()

    @pytest.mark.asyncio
    @patch('artisan_agents.tools.embedding_generator.EmbeddingGenerator.generate_embeddings_batch_async')
    async def test_generate_text_embeddings_batch(self, mock_generate_batch):
        """Test convenience function for batch embeddings."""
        mock_generate_batch.return_value = [[0.1, 0.2], [0.3, 0.4]]

        texts = ["text1", "text2"]
        result = await generate_text_embeddings_batch(texts)

        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_generate_batch.assert_called_once_with(texts)


class TestIntegrationScenarios:
    """Integration tests for realistic scenarios."""

    def test_artisan_product_matching(self, embedding_config, sample_texts):
        """Test scenario: matching artisan products by description."""
        generator = EmbeddingGenerator(embedding_config)

        # Simulate product embeddings
        product_embeddings = []
        for text in sample_texts:
            # In real scenario, this would call the actual embedding generation
            mock_embedding = [hash(text) % 100 for _ in range(10)]  # Mock embedding
            product_embeddings.append({
                "text": text,
                "embedding": mock_embedding,
                "metadata": {"category": "artisan"}
            })

        # Query for similar products
        query_text = "handmade wooden items"
        query_embedding = [hash(query_text) % 100 for _ in range(10)]  # Mock embedding

        similar_products = generator.find_similar_texts(
            query_embedding, product_embeddings, top_k=3
        )

        assert len(similar_products) == 3
        assert all("similarity" in product for product in similar_products)

    def test_semantic_clustering_scenario(self, embedding_config):
        """Test scenario: clustering artisan descriptions semantically."""
        generator = EmbeddingGenerator(embedding_config)

        # Sample artisan descriptions
        descriptions = [
            "Handcrafted wooden furniture with traditional techniques",
            "Modern minimalist furniture design",
            "Rustic farmhouse style wooden pieces",
            "Contemporary ceramic pottery",
            "Traditional pottery with ancient methods",
            "Modern ceramic sculptures"
        ]

        # Generate mock embeddings (in real scenario, use actual embeddings)
        embeddings = []
        for desc in descriptions:
            mock_embedding = [hash(desc) % 1000 / 1000 for _ in range(50)]
            embeddings.append(mock_embedding)

        # Cluster by semantic similarity
        clusters = generator.cluster_embeddings(embeddings, threshold=0.7)

        # Should find meaningful clusters (wooden furniture vs ceramic)
        assert len(clusters) >= 2

    @pytest.mark.performance
    def test_batch_processing_performance(self, embedding_config):
        """Test performance of batch processing."""
        generator = EmbeddingGenerator(embedding_config)

        # Create larger dataset
        large_texts = [f"Sample text number {i}" for i in range(100)]

        start_time = time.time()

        # Mock the embedding generation for performance testing
        with patch.object(generator, 'generate_embedding', return_value=[0.1] * 100):
            results = generator.generate_embeddings_batch(large_texts)

        end_time = time.time()
        processing_time = end_time - start_time

        assert len(results) == 100
        assert processing_time < 5.0  # Should complete within 5 seconds
        assert all(result is not None for result in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
