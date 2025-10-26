"""
Comprehensive tests for the Data Access Layer (DAL) module.

Tests cover all CRUD operations, error handling, connection management,
and integration scenarios for the database layer.
"""

import pytest
import psycopg2
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
import json
from decimal import Decimal

from artisan_agents.tools.data_access import (
    DataAccessLayer,
    DatabaseConfig,
    DatabaseConnection,
    get_dal,
    create_artisan,
    get_artisan
)


@pytest.fixture
def db_config():
    """Standard database configuration for testing."""
    return DatabaseConfig(
        host="localhost",
        port=5432,
        database="test_artisan_agents",
        user="test_user",
        password="test_password",
        connection_timeout=10
    )


@pytest.fixture
def sample_artisan_data():
    """Sample artisan data for testing."""
    return {
        'name': 'Test Artisan',
        'email': 'test@artisan.com',
        'phone': '+1-555-0123',
        'latitude': 40.7128,
        'longitude': -74.0060,
        'specialties': ['woodworking', 'furniture'],
        'rating': 4.5,
        'is_active': True,
        'metadata': {
            'experience_years': 10,
            'certifications': ['Certified Artisan']
        }
    }


@pytest.fixture
def sample_supplier_data():
    """Sample supplier data for testing."""
    return {
        'name': 'Test Supplier',
        'email': 'test@supplier.com',
        'phone': '+1-555-0456',
        'latitude': 34.0522,
        'longitude': -118.2437,
        'product_categories': ['wood', 'tools'],
        'min_order_amount': 100.0,
        'max_order_amount': 10000.0,
        'rating': 4.2,
        'is_active': True,
        'metadata': {
            'business_type': 'wholesale',
            'established': 2010
        }
    }


@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        'artisan_id': 1,
        'supplier_id': 1,
        'order_number': 'ORD-2025-001',
        'status': 'pending',
        'total_amount': 1500.0,
        'currency': 'USD',
        'order_items': [
            {'product': 'Oak Wood', 'quantity': 10, 'price': 150.0}
        ],
        'shipping_address': {
            'street': '123 Main St',
            'city': 'Anytown',
            'state': 'CA',
            'zip': '12345'
        },
        'notes': 'Handle with care',
        'estimated_delivery': date(2025, 2, 15)
    }


class TestDatabaseConfig:
    """Test DatabaseConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DatabaseConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "artisan_agents"
        assert config.user == "postgres"
        assert config.password == "password"
        assert config.connection_timeout == 30

    def test_custom_config(self):
        """Test custom configuration values."""
        config = DatabaseConfig(
            host="custom.host",
            port=5433,
            database="custom_db",
            user="custom_user",
            password="custom_pass",
            connection_timeout=60
        )
        assert config.host == "custom.host"
        assert config.port == 5433
        assert config.database == "custom_db"
        assert config.user == "custom_user"
        assert config.password == "custom_pass"
        assert config.connection_timeout == 60


class TestDatabaseConnection:
    """Test DatabaseConnection context manager."""

    @patch('psycopg2.connect')
    def test_connection_context_manager(self, mock_connect, db_config):
        """Test database connection context manager."""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        with DatabaseConnection(db_config) as conn:
            assert conn == mock_connection

        mock_connect.assert_called_once()
        mock_connection.close.assert_called_once()


class TestDataAccessLayer:
    """Test DataAccessLayer class."""

    def test_initialization(self, db_config):
        """Test DAL initialization."""
        dal = DataAccessLayer(db_config)
        assert dal.config == db_config

    def test_initialization_default_config(self):
        """Test DAL initialization with default config."""
        dal = DataAccessLayer()
        assert dal.config.database == "artisan_agents"

    @patch('psycopg2.connect')
    def test_get_connection_success(self, mock_connect, db_config):
        """Test successful database connection."""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        with dal.get_connection() as conn:
            assert conn == mock_connection

        mock_connection.close.assert_called_once()

    @patch('psycopg2.connect')
    def test_get_connection_failure(self, mock_connect, db_config):
        """Test database connection failure."""
        mock_connect.side_effect = Exception("Connection failed")

        dal = DataAccessLayer(db_config)
        with pytest.raises(Exception, match="Connection failed"):
            with dal.get_connection():
                pass

    def test_get_cursor_with_connection(self, db_config):
        """Test cursor creation with existing connection."""
        dal = DataAccessLayer(db_config)

        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = Mock(return_value=None)

        with dal.get_cursor(mock_connection) as cursor:
            assert cursor == mock_cursor

    def test_get_cursor_without_connection(self, db_config):
        """Test cursor creation without existing connection."""
        dal = DataAccessLayer(db_config)

        with patch.object(dal, 'get_connection') as mock_get_conn:
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_get_conn.return_value.__enter__ = Mock(return_value=mock_connection)
            mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_connection.cursor.return_value.__exit__ = Mock(return_value=None)

            with dal.get_cursor() as cursor:
                assert cursor == mock_cursor


class TestArtisanOperations:
    """Test artisan CRUD operations."""

    @patch('psycopg2.connect')
    def test_create_artisan_success(self, mock_connect, db_config, sample_artisan_data):
        """Test successful artisan creation."""
        # Mock database response
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {'id': 1}

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        artisan_id = dal.create_artisan(sample_artisan_data)

        assert artisan_id == 1
        mock_cursor.execute.assert_called_once()

    @patch('psycopg2.connect')
    def test_create_artisan_missing_required_field(self, mock_connect, db_config):
        """Test artisan creation with missing required field."""
        dal = DataAccessLayer(db_config)
        incomplete_data = {'email': 'test@example.com'}  # Missing 'name'

        with pytest.raises(ValueError, match="Missing required field: name"):
            dal.create_artisan(incomplete_data)

    @patch('psycopg2.connect')
    def test_get_artisan_success(self, mock_connect, db_config):
        """Test successful artisan retrieval."""
        mock_artisan = {
            'id': 1,
            'name': 'Test Artisan',
            'email': 'test@artisan.com',
            'rating': 4.5
        }

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = mock_artisan

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        result = dal.get_artisan(1)

        assert result == mock_artisan
        mock_cursor.execute.assert_called_once_with("SELECT * FROM artisans WHERE id = %s", (1,))

    @patch('psycopg2.connect')
    def test_get_artisan_not_found(self, mock_connect, db_config):
        """Test artisan retrieval when not found."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        result = dal.get_artisan(999)

        assert result is None

    @patch('psycopg2.connect')
    def test_get_artisan_by_email(self, mock_connect, db_config):
        """Test artisan retrieval by email."""
        mock_artisan = {'id': 1, 'name': 'Test Artisan', 'email': 'test@artisan.com'}

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = mock_artisan

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        result = dal.get_artisan_by_email('test@artisan.com')

        assert result == mock_artisan

    @patch('psycopg2.connect')
    def test_update_artisan_success(self, mock_connect, db_config):
        """Test successful artisan update."""
        mock_cursor = Mock()
        mock_cursor.rowcount = 1

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        success = dal.update_artisan(1, {'name': 'Updated Name', 'rating': 5.0})

        assert success is True
        assert mock_cursor.execute.call_count == 1

    @patch('psycopg2.connect')
    def test_update_artisan_no_valid_fields(self, mock_connect, db_config):
        """Test artisan update with no valid fields."""
        dal = DataAccessLayer(db_config)
        success = dal.update_artisan(1, {'invalid_field': 'value'})

        assert success is False

    @patch('psycopg2.connect')
    def test_delete_artisan_success(self, mock_connect, db_config):
        """Test successful artisan deletion."""
        mock_cursor = Mock()
        mock_cursor.rowcount = 1

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        success = dal.delete_artisan(1)

        assert success is True

    @patch('psycopg2.connect')
    def test_search_artisans_with_filters(self, mock_connect, db_config):
        """Test artisan search with filters."""
        mock_artisans = [
            {'id': 1, 'name': 'Woodworker', 'rating': 4.5},
            {'id': 2, 'name': 'Potter', 'rating': 4.2}
        ]

        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = mock_artisans

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        results = dal.search_artisans(
            filters={'specialty': 'woodworking', 'min_rating': 4.0},
            limit=10,
            offset=0
        )

        assert results == mock_artisans
        # Verify the query was constructed correctly
        call_args = mock_cursor.execute.call_args[0]
        assert 'specialty' in call_args[0]
        assert 'min_rating' in call_args[0]


class TestSupplierOperations:
    """Test supplier CRUD operations."""

    @patch('psycopg2.connect')
    def test_create_supplier_success(self, mock_connect, db_config, sample_supplier_data):
        """Test successful supplier creation."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {'id': 1}

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        supplier_id = dal.create_supplier(sample_supplier_data)

        assert supplier_id == 1

    @patch('psycopg2.connect')
    def test_get_supplier_success(self, mock_connect, db_config):
        """Test successful supplier retrieval."""
        mock_supplier = {'id': 1, 'name': 'Test Supplier', 'rating': 4.2}

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = mock_supplier

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        result = dal.get_supplier(1)

        assert result == mock_supplier

    @patch('psycopg2.connect')
    def test_search_suppliers_with_category_filter(self, mock_connect, db_config):
        """Test supplier search with category filter."""
        mock_suppliers = [
            {'id': 1, 'name': 'Wood Supplier', 'product_categories': ['wood']},
            {'id': 2, 'name': 'Tool Supplier', 'product_categories': ['tools']}
        ]

        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = mock_suppliers

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        results = dal.search_suppliers(
            filters={'category': 'wood'},
            limit=10
        )

        assert results == mock_suppliers


class TestOrderOperations:
    """Test order CRUD operations."""

    @patch('psycopg2.connect')
    def test_create_order_success(self, mock_connect, db_config, sample_order_data):
        """Test successful order creation."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {'id': 1}

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        order_id = dal.create_order(sample_order_data)

        assert order_id == 1

    @patch('psycopg2.connect')
    def test_create_order_missing_required_field(self, mock_connect, db_config):
        """Test order creation with missing required field."""
        dal = DataAccessLayer(db_config)
        incomplete_data = {'supplier_id': 1}  # Missing artisan_id, order_number, total_amount

        with pytest.raises(ValueError, match="Missing required field: artisan_id"):
            dal.create_order(incomplete_data)

    @patch('psycopg2.connect')
    def test_get_order_by_number(self, mock_connect, db_config):
        """Test order retrieval by order number."""
        mock_order = {
            'id': 1,
            'order_number': 'ORD-2025-001',
            'status': 'pending',
            'total_amount': 1500.0
        }

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = mock_order

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        result = dal.get_order_by_number('ORD-2025-001')

        assert result == mock_order

    @patch('psycopg2.connect')
    def test_get_orders_by_artisan(self, mock_connect, db_config):
        """Test retrieving orders by artisan."""
        mock_orders = [
            {'id': 1, 'order_number': 'ORD-001', 'status': 'pending'},
            {'id': 2, 'order_number': 'ORD-002', 'status': 'shipped'}
        ]

        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = mock_orders

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        results = dal.get_orders_by_artisan(1, limit=10)

        assert results == mock_orders

    @patch('psycopg2.connect')
    def test_get_orders_by_status(self, mock_connect, db_config):
        """Test retrieving orders by status."""
        mock_orders = [
            {'id': 1, 'order_number': 'ORD-001', 'status': 'pending'},
            {'id': 2, 'order_number': 'ORD-002', 'status': 'pending'}
        ]

        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = mock_orders

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        results = dal.get_orders_by_status('pending', limit=10)

        assert results == mock_orders


class TestAgentStateOperations:
    """Test agent state operations."""

    @patch('psycopg2.connect')
    def test_save_agent_state_success(self, mock_connect, db_config):
        """Test successful agent state save."""
        mock_cursor = Mock()
        mock_cursor.rowcount = 1

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        state_data = {'conversation': 'test', 'step': 1}
        success = dal.save_agent_state(1, 'session_123', state_data)

        assert success is True

    @patch('psycopg2.connect')
    def test_get_agent_state_success(self, mock_connect, db_config):
        """Test successful agent state retrieval."""
        future_time = datetime.now().replace(year=2026)  # Future expiry
        mock_state = {
            'id': 1,
            'agent_id': 1,
            'session_id': 'session_123',
            'state_data': {'conversation': 'test'},
            'expires_at': future_time,
            'is_active': True
        }

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = mock_state

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        result = dal.get_agent_state(1, 'session_123')

        assert result == mock_state

    @patch('psycopg2.connect')
    def test_get_agent_state_expired(self, mock_connect, db_config):
        """Test agent state retrieval when expired."""
        past_time = datetime.now().replace(year=2020)  # Past expiry
        mock_state = {
            'id': 1,
            'agent_id': 1,
            'session_id': 'session_123',
            'state_data': {'conversation': 'test'},
            'expires_at': past_time,
            'is_active': True
        }

        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = mock_state

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        result = dal.get_agent_state(1, 'session_123')

        assert result is None

    @patch('psycopg2.connect')
    def test_cleanup_expired_states(self, mock_connect, db_config):
        """Test cleanup of expired agent states."""
        mock_cursor = Mock()
        mock_cursor.rowcount = 5  # 5 expired states cleaned up

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        cleaned_count = dal.cleanup_expired_states()

        assert cleaned_count == 5


class TestUtilityOperations:
    """Test utility operations."""

    @patch('psycopg2.connect')
    def test_health_check_success(self, mock_connect, db_config):
        """Test successful health check."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {'health_check': 1}

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        health = dal.health_check()

        assert health['status'] == 'healthy'
        assert 'timestamp' in health
        assert health['check_result'] == 1

    @patch('psycopg2.connect')
    def test_health_check_failure(self, mock_connect, db_config):
        """Test health check failure."""
        mock_connect.side_effect = Exception("Database unavailable")

        dal = DataAccessLayer(db_config)
        health = dal.health_check()

        assert health['status'] == 'unhealthy'
        assert 'error' in health

    @patch('psycopg2.connect')
    def test_get_table_counts(self, mock_connect, db_config):
        """Test getting table row counts."""
        mock_results = [
            {'count': 10},  # agents
            {'count': 5},   # tools
            {'count': 25},  # artisans
            {'count': 15},  # suppliers
            {'count': 100}, # orders
            {'count': 8}    # agent_state
        ]

        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = mock_results

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        counts = dal.get_table_counts()

        expected_counts = {
            'agents': 10,
            'tools': 5,
            'artisans': 25,
            'suppliers': 15,
            'orders': 100,
            'agent_state': 8
        }

        assert counts == expected_counts

    @patch('psycopg2.connect')
    def test_bulk_insert_artisans(self, mock_connect, db_config):
        """Test bulk artisan insertion."""
        mock_cursor = Mock()
        mock_cursor.rowcount = 3

        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection

        dal = DataAccessLayer(db_config)
        artisans_data = [
            {'name': 'Artisan 1', 'email': 'artisan1@test.com'},
            {'name': 'Artisan 2', 'email': 'artisan2@test.com'},
            {'name': 'Artisan 3', 'email': 'artisan3@test.com'}
        ]

        inserted_count = dal.bulk_insert_artisans(artisans_data)

        assert inserted_count == 3


class TestConvenienceFunctions:
    """Test convenience functions."""

    @patch('artisan_agents.tools.data_access.DataAccessLayer')
    def test_get_dal(self, mock_dal_class):
        """Test get_dal convenience function."""
        mock_dal = Mock()
        mock_dal_class.return_value = mock_dal

        result = get_dal()

        assert result == mock_dal
        mock_dal_class.assert_called_once()

    @patch('artisan_agents.tools.data_access.DataAccessLayer')
    def test_create_artisan_convenience(self, mock_dal_class, sample_artisan_data):
        """Test create_artisan convenience function."""
        mock_dal = Mock()
        mock_dal.create_artisan.return_value = 1
        mock_dal_class.return_value = mock_dal

        result = create_artisan(sample_artisan_data)

        assert result == 1
        mock_dal.create_artisan.assert_called_once_with(sample_artisan_data)

    @patch('artisan_agents.tools.data_access.DataAccessLayer')
    def test_get_artisan_convenience(self, mock_dal_class):
        """Test get_artisan convenience function."""
        mock_dal = Mock()
        mock_dal.get_artisan.return_value = {'id': 1, 'name': 'Test'}
        mock_dal_class.return_value = mock_dal

        result = get_artisan(1)

        assert result == {'id': 1, 'name': 'Test'}
        mock_dal.get_artisan.assert_called_once_with(1)


class TestErrorHandling:
    """Test error handling scenarios."""

    @patch('psycopg2.connect')
    def test_database_error_handling(self, mock_connect, db_config):
        """Test handling of database errors."""
        mock_connect.side_effect = psycopg2.OperationalError("Connection failed")

        dal = DataAccessLayer(db_config)

        with pytest.raises(psycopg2.OperationalError):
            dal.get_artisan(1)

    @patch('psycopg2.connect')
    def test_transaction_rollback_simulation(self, mock_connect, db_config):
        """Test that connections are properly closed on errors."""
        mock_connection = Mock()
        mock_connection.close = Mock()

        # Simulate an error during connection
        mock_connect.side_effect = Exception("Connection error")

        dal = DataAccessLayer(db_config)

        with pytest.raises(Exception):
            with dal.get_connection():
                raise Exception("Test error")

        # Connection should still be closed
        mock_connection.close.assert_called_once()


class TestIntegrationScenarios:
    """Integration test scenarios."""

    def test_complete_artisan_lifecycle(self, db_config, sample_artisan_data):
        """Test complete artisan lifecycle: create, read, update, delete."""
        with patch('psycopg2.connect') as mock_connect:
            # Mock successful operations
            mock_cursor = Mock()
            mock_cursor.rowcount = 1
            mock_cursor.fetchone.side_effect = [
                {'id': 1},  # create
                sample_artisan_data,  # get
                None  # delete
            ]

            mock_connection = Mock()
            mock_connection.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_connection

            dal = DataAccessLayer(db_config)

            # Create
            artisan_id = dal.create_artisan(sample_artisan_data)
            assert artisan_id == 1

            # Read
            artisan = dal.get_artisan(artisan_id)
            assert artisan == sample_artisan_data

            # Update
            updated = dal.update_artisan(artisan_id, {'rating': 5.0})
            assert updated is True

            # Delete
            deleted = dal.delete_artisan(artisan_id)
            assert deleted is True

    def test_order_management_workflow(self, db_config, sample_order_data):
        """Test order management workflow."""
        with patch('psycopg2.connect') as mock_connect:
            mock_cursor = Mock()
            mock_cursor.fetchone.side_effect = [
                {'id': 1},  # create order
                sample_order_data,  # get by number
                [sample_order_data],  # get by artisan
                [sample_order_data]   # get by status
            ]

            mock_connection = Mock()
            mock_connection.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_connection

            dal = DataAccessLayer(db_config)

            # Create order
            order_id = dal.create_order(sample_order_data)
            assert order_id == 1

            # Get by order number
            order = dal.get_order_by_number('ORD-2025-001')
            assert order == sample_order_data

            # Get by artisan
            orders = dal.get_orders_by_artisan(1)
            assert len(orders) == 1

            # Get by status
            pending_orders = dal.get_orders_by_status('pending')
            assert len(pending_orders) == 1

    def test_agent_state_management(self, db_config):
        """Test agent state management workflow."""
        with patch('psycopg2.connect') as mock_connect:
            future_time = datetime.now().replace(year=2026)

            mock_cursor = Mock()
            mock_cursor.rowcount = 1
            mock_cursor.fetchone.return_value = {
                'id': 1,
                'agent_id': 1,
                'session_id': 'session_123',
                'state_data': {'step': 1},
                'expires_at': future_time,
                'is_active': True
            }

            mock_connection = Mock()
            mock_connection.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_connection

            dal = DataAccessLayer(db_config)

            # Save state
            state_data = {'conversation': 'test', 'step': 1}
            saved = dal.save_agent_state(1, 'session_123', state_data)
            assert saved is True

            # Get state
            state = dal.get_agent_state(1, 'session_123')
            assert state is not None
            assert state['state_data']['step'] == 1

            # Cleanup expired (should find none in this case)
            cleaned = dal.cleanup_expired_states()
            assert cleaned == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
