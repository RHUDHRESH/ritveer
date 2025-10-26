# ArtisanHub - Artisan Marketplace Platform

A comprehensive platform for connecting artisans with suppliers, featuring intelligent matching, automated workflows, and robust data management.

## 🚀 Project Overview

ArtisanHub is a sophisticated marketplace platform designed to streamline the connection between skilled artisans and quality suppliers. The platform leverages advanced AI/ML techniques for intelligent matching, automated order processing, and comprehensive data management.

## 📋 Project Status

### ✅ Phase 1: Local Environment Setup - **COMPLETE**
- Python 3.12 environment configured
- Virtual environment established
- All required dependencies installed (FastAPI, SQLAlchemy, PostgreSQL, Redis, etc.)
- Docker Compose setup for local development
- Database initialization scripts created

### ✅ Phase 2: Utility Tool Development - **COMPLETE**

#### A. Text & Data Extraction Tools ✅
- **File**: `tools/extraction_tool.py`
- **Features**:
  - Ollama-based text extraction from documents
  - Regex-based pattern extraction
  - Multi-format support (PDF, DOCX, TXT)
  - Comprehensive test coverage
- **Status**: Fully implemented and tested

#### B. Validation & Policy Tools ✅
- **Files**: `tools/policy_loader.py`, `tools/validation_engine.py`
- **Features**:
  - Dynamic policy loading from YAML configurations
  - Comprehensive validation engine
  - Support for commission rates, order limits, and refund policies
  - Regional policy variations
- **Status**: Fully implemented with populated policy files

#### C. Clustering & Embedding Tools ✅
- **Files**: `tools/spatial_clustering.py`, `tools/embedding_generator.py`
- **Features**:
  - Geographic clustering (K-means, DBSCAN) for location-based matching
  - **NEW**: Ollama-based semantic embedding generation
  - Text similarity calculations and clustering
  - Batch processing capabilities
  - Async/sync processing modes
- **Status**: Fully implemented with comprehensive testing

#### D. Supplier & Scoring Tools ✅
- **Files**: `tools/web_scraper.py`, `tools/quote_aggregator.py`, `tools/supplier_scoring.py`
- **Features**:
  - Web scraping for supplier data collection
  - Quote aggregation and comparison
  - Multi-criteria supplier scoring system
  - Comprehensive test coverage
- **Status**: Fully implemented and tested

#### E. Persistence & State Tools ✅
- **Files**: `tools/state_manager.py`, `tools/data_access.py`
- **Features**:
  - Advanced state management with serialization, compression, encryption
  - **NEW**: Complete Data Access Layer (DAL) with full CRUD operations
  - Database schema for all entities (artisans, suppliers, orders, agent_state)
  - Connection pooling and error handling
  - Bulk operations and search capabilities
- **Status**: Fully implemented with comprehensive testing

#### F. Notification & Messaging Tools ✅
- **Files**: `tools/messaging_stubs.py`, `tools/notification_stubs.py`
- **Features**:
  - Local stubs for Telegram, WhatsApp, email, SMS
  - Message queuing and delivery simulation
  - Template-based message formatting
  - Comprehensive test coverage
- **Status**: Fully implemented and tested

## 🗄️ Database Schema

The platform uses PostgreSQL with the following main entities:

### Core Tables
- **agents**: System agents and their configurations
- **tools**: Available tools and their states

### Business Domain Tables
- **artisans**: Artisan profiles with specialties, ratings, and location data
- **suppliers**: Supplier information with product categories and ratings
- **orders**: Order management with status tracking and relationships
- **agent_state**: Session management for agent conversations

### Key Features
- PostGIS integration for geographic queries
- JSONB fields for flexible metadata storage
- Comprehensive indexing for performance
- Foreign key relationships and constraints

## 🔧 Key Components

### 1. Embedding Generator (`tools/embedding_generator.py`)
```python
from artisan_agents.tools.embedding_generator import EmbeddingGenerator, EmbeddingConfig

# Generate semantic embeddings for text
config = EmbeddingConfig(model="nomic-embed-text")
generator = EmbeddingGenerator(config)
embedding = generator.generate_embedding("handcrafted wooden furniture")

# Find similar texts
similar_texts = generator.find_similar_texts(query_embedding, text_embeddings)
```

### 2. Data Access Layer (`tools/data_access.py`)
```python
from artisan_agents.tools.data_access import DataAccessLayer, DatabaseConfig

# Database operations
dal = DataAccessLayer(DatabaseConfig(database="artisan_agents"))
artisan_id = dal.create_artisan({
    'name': 'John Woodworker',
    'email': 'john@example.com',
    'specialties': ['woodworking', 'furniture']
})

artisan = dal.get_artisan(artisan_id)
```

### 3. Spatial Clustering (`tools/spatial_clustering.py`)
```python
from artisan_agents.tools.spatial_clustering import SpatialClusterer, SpatialClustererConfig

# Geographic clustering
config = SpatialClustererConfig(num_clusters=5)
clusterer = SpatialClusterer(config)
labels = clusterer.cluster_locations(locations, method="kmeans")
```

## 🧪 Testing

Comprehensive test suites are included for all components:

- **Unit Tests**: Individual function and method testing
- **Integration Tests**: Cross-component workflow testing
- **Performance Tests**: Batch processing and scalability validation
- **Mock Tests**: External service simulation for reliable CI/CD

Run tests:
```bash
# Run all tests
pytest artisan_agents/tools/tests/

# Run specific test file
pytest artisan_agents/tools/tests/test_embedding_generator.py -v

# Run with coverage
pytest --cov=artisan_agents/tools/ artisan_agents/tools/tests/
```

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- PostgreSQL 13+
- Redis 6+
- Ollama (for embedding generation)

### Installation

1. **Clone and setup environment**:
```bash
git clone <repository-url>
cd artisan_agents
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```

2. **Database setup**:
```bash
# Initialize database
python init_db.py

# Verify setup
python verify_setup.py
```

3. **Start services**:
```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Or manually start Ollama for embeddings
ollama serve
```

### Usage Examples

#### Basic Operations
```python
# Text extraction
from artisan_agents.extraction_tool import extract_text_from_file
text = extract_text_from_file("document.pdf")

# Policy validation
from artisan_agents.tools.policy_loader import load_policy
policy = load_policy("commission_rates")
is_valid = validate_order(order_data, policy)

# Semantic search
from artisan_agents.tools.embedding_generator import generate_text_embedding
embedding = generate_text_embedding("artisan furniture")
similar_artisans = find_similar_artisans(embedding)

# Database operations
from artisan_agents.tools.data_access import get_dal
dal = get_dal()
artisans = dal.search_artisans(filters={'specialty': 'woodworking'})
```

## 📁 Project Structure

```
artisan_agents/
├── agents_system.py          # Main agent system
├── api.py                    # FastAPI endpoints
├── config.py                 # Configuration management
├── schema.sql               # Database schema
├── requirements.txt         # Python dependencies
├── init_db.py              # Database initialization
├── verify_setup.py         # Setup verification
├── extraction_tool.py      # Text extraction utilities
├── policies/               # Policy configuration files
│   ├── commission_rates.yaml
│   ├── order_limits.yaml
│   ├── refund_policies.yaml
│   └── refund_policy.yaml
├── tools/                  # Core utility modules
│   ├── data_access.py      # Database access layer
│   ├── embedding_generator.py  # Semantic embeddings
│   ├── messaging_stubs.py  # Message system stubs
│   ├── notification_stubs.py   # Notification stubs
│   ├── policy_loader.py    # Policy management
│   ├── quote_aggregator.py # Quote processing
│   ├── spatial_clustering.py   # Geographic clustering
│   ├── state_manager.py    # State management
│   ├── supplier_scoring.py # Supplier evaluation
│   ├── validation_engine.py    # Data validation
│   ├── web_scraper.py      # Web scraping utilities
│   └── tests/              # Test suites
│       ├── test_data_access.py
│       ├── test_embedding_generator.py
│       └── test_state_manager.py
└── static/                 # Static web assets
    └── index.html
```

## 🔮 Future Enhancements

While Phase 2 is complete, potential future improvements include:

- **Real-time WebSocket APIs** for live updates
- **Advanced ML models** for better matching algorithms
- **Mobile application** for artisan/supplier access
- **Payment processing integration**
- **Advanced analytics dashboard**
- **Multi-language support**
- **API rate limiting and caching**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add comprehensive tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Email: support@artisanhub.com
- Documentation: [Link to docs]
- Issue Tracker: [Link to issues]

---

**Project Status**: ✅ **COMPLETE** - All Phase 1 and Phase 2 components implemented and tested.

**Last Updated**: January 2025
**Version**: 1.0.0
