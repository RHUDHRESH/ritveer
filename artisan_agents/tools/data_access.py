"""
Data Access Layer (DAL) for ArtisanHub database operations.

This module provides a comprehensive data access layer with CRUD operations
for all database tables, including artisans, suppliers, orders, and agent_state.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor, Json, execute_values
import json
from dataclasses import dataclass, asdict
from decimal import Decimal


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    host: str = "localhost"
    port: int = 5432
    database: str = "artisan_agents"
    user: str = "postgres"
    password: str = "password"
    connection_timeout: int = 30


class DatabaseConnection:
    """Database connection manager."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection = None

    def __enter__(self):
        self._connection = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.user,
            password=self.config.password,
            connect_timeout=self.config.connection_timeout,
            cursor_factory=RealDictCursor
        )
        return self._connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._connection:
            self._connection.close()


class DataAccessLayer:
    """
    Comprehensive Data Access Layer for ArtisanHub.

    Provides CRUD operations for all database entities with proper
    error handling, connection management, and data validation.
    """

    def __init__(self, config: DatabaseConfig = None):
        """Initialize DAL with database configuration."""
        self.config = config or DatabaseConfig()
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup."""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                connect_timeout=self.config.connection_timeout,
                cursor_factory=RealDictCursor
            )
            yield conn
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @contextmanager
    def get_cursor(self, connection=None):
        """Get database cursor with automatic cleanup."""
        if connection is None:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    yield cursor
        else:
            with connection.cursor() as cursor:
                yield cursor

    # ===== ARTISAN OPERATIONS =====

    def create_artisan(self, artisan_data: Dict[str, Any]) -> int:
        """Create a new artisan record."""
        required_fields = ['name']
        for field in required_fields:
            if field not in artisan_data:
                raise ValueError(f"Missing required field: {field}")

        query = """
            INSERT INTO artisans (
                name, email, phone, location, latitude, longitude,
                specialties, rating, is_active, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        with self.get_cursor() as cursor:
            cursor.execute(query, (
                artisan_data['name'],
                artisan_data.get('email'),
                artisan_data.get('phone'),
                artisan_data.get('location'),  # PostGIS point
                artisan_data.get('latitude'),
                artisan_data.get('longitude'),
                artisan_data.get('specialties', []),
                artisan_data.get('rating', 0),
                artisan_data.get('is_active', True),
                Json(artisan_data.get('metadata', {}))
            ))
            return cursor.fetchone()['id']

    def get_artisan(self, artisan_id: int) -> Optional[Dict[str, Any]]:
        """Get artisan by ID."""
        query = "SELECT * FROM artisans WHERE id = %s"

        with self.get_cursor() as cursor:
            cursor.execute(query, (artisan_id,))
            return cursor.fetchone()

    def get_artisan_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get artisan by email."""
        query = "SELECT * FROM artisans WHERE email = %s"

        with self.get_cursor() as cursor:
            cursor.execute(query, (email,))
            return cursor.fetchone()

    def update_artisan(self, artisan_id: int, artisan_data: Dict[str, Any]) -> bool:
        """Update artisan record."""
        allowed_fields = {
            'name', 'email', 'phone', 'location', 'latitude', 'longitude',
            'specialties', 'rating', 'is_active', 'metadata'
        }

        update_fields = []
        values = []

        for field, value in artisan_data.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = %s")
                values.append(value)

        if not update_fields:
            return False

        values.append(artisan_id)
        query = f"""
            UPDATE artisans
            SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """

        with self.get_cursor() as cursor:
            cursor.execute(query, values)
            return cursor.rowcount > 0

    def delete_artisan(self, artisan_id: int) -> bool:
        """Delete artisan record."""
        query = "DELETE FROM artisans WHERE id = %s"

        with self.get_cursor() as cursor:
            cursor.execute(query, (artisan_id,))
            return cursor.rowcount > 0

    def search_artisans(self, filters: Dict[str, Any] = None,
                       limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Search artisans with filters."""
        filters = filters or {}

        query = "SELECT * FROM artisans WHERE 1=1"
        params = []
        param_index = 1

        if 'specialty' in filters:
            query += f" AND %s = ANY(specialties)"
            params.append(filters['specialty'])
            param_index += 1

        if 'min_rating' in filters:
            query += f" AND rating >= %s"
            params.append(filters['min_rating'])
            param_index += 1

        if 'is_active' in filters:
            query += f" AND is_active = %s"
            params.append(filters['is_active'])
            param_index += 1

        if 'location' in filters:
            # Simple bounding box search - in production, use PostGIS functions
            lat, lon = filters['location']
            query += " AND latitude BETWEEN %s AND %s AND longitude BETWEEN %s AND %s"
            params.extend([lat - 0.1, lat + 0.1, lon - 0.1, lon + 0.1])
            param_index += 4

        query += " ORDER BY rating DESC, name"
        query += f" LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    # ===== SUPPLIER OPERATIONS =====

    def create_supplier(self, supplier_data: Dict[str, Any]) -> int:
        """Create a new supplier record."""
        required_fields = ['name']
        for field in required_fields:
            if field not in supplier_data:
                raise ValueError(f"Missing required field: {field}")

        query = """
            INSERT INTO suppliers (
                name, email, phone, location, latitude, longitude,
                product_categories, min_order_amount, max_order_amount,
                rating, is_active, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        with self.get_cursor() as cursor:
            cursor.execute(query, (
                supplier_data['name'],
                supplier_data.get('email'),
                supplier_data.get('phone'),
                supplier_data.get('location'),
                supplier_data.get('latitude'),
                supplier_data.get('longitude'),
                supplier_data.get('product_categories', []),
                supplier_data.get('min_order_amount'),
                supplier_data.get('max_order_amount'),
                supplier_data.get('rating', 0),
                supplier_data.get('is_active', True),
                Json(supplier_data.get('metadata', {}))
            ))
            return cursor.fetchone()['id']

    def get_supplier(self, supplier_id: int) -> Optional[Dict[str, Any]]:
        """Get supplier by ID."""
        query = "SELECT * FROM suppliers WHERE id = %s"

        with self.get_cursor() as cursor:
            cursor.execute(query, (supplier_id,))
            return cursor.fetchone()

    def update_supplier(self, supplier_id: int, supplier_data: Dict[str, Any]) -> bool:
        """Update supplier record."""
        allowed_fields = {
            'name', 'email', 'phone', 'location', 'latitude', 'longitude',
            'product_categories', 'min_order_amount', 'max_order_amount',
            'rating', 'is_active', 'metadata'
        }

        update_fields = []
        values = []

        for field, value in supplier_data.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = %s")
                values.append(value)

        if not update_fields:
            return False

        values.append(supplier_id)
        query = f"""
            UPDATE suppliers
            SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """

        with self.get_cursor() as cursor:
            cursor.execute(query, values)
            return cursor.rowcount > 0

    def search_suppliers(self, filters: Dict[str, Any] = None,
                        limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Search suppliers with filters."""
        filters = filters or {}

        query = "SELECT * FROM suppliers WHERE 1=1"
        params = []

        if 'category' in filters:
            query += " AND %s = ANY(product_categories)"
            params.append(filters['category'])

        if 'min_rating' in filters:
            query += " AND rating >= %s"
            params.append(filters['min_rating'])

        if 'is_active' in filters:
            query += " AND is_active = %s"
            params.append(filters['is_active'])

        query += " ORDER BY rating DESC, name"
        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    # ===== ORDER OPERATIONS =====

    def create_order(self, order_data: Dict[str, Any]) -> int:
        """Create a new order record."""
        required_fields = ['artisan_id', 'order_number', 'total_amount']
        for field in required_fields:
            if field not in order_data:
                raise ValueError(f"Missing required field: {field}")

        query = """
            INSERT INTO orders (
                artisan_id, supplier_id, order_number, status, total_amount,
                currency, order_items, shipping_address, billing_address,
                notes, estimated_delivery, actual_delivery, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        with self.get_cursor() as cursor:
            cursor.execute(query, (
                order_data['artisan_id'],
                order_data.get('supplier_id'),
                order_data['order_number'],
                order_data.get('status', 'pending'),
                order_data['total_amount'],
                order_data.get('currency', 'USD'),
                Json(order_data.get('order_items', [])),
                Json(order_data.get('shipping_address', {})),
                Json(order_data.get('billing_address', {})),
                order_data.get('notes'),
                order_data.get('estimated_delivery'),
                order_data.get('actual_delivery'),
                Json(order_data.get('metadata', {}))
            ))
            return cursor.fetchone()['id']

    def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Get order by ID."""
        query = "SELECT * FROM orders WHERE id = %s"

        with self.get_cursor() as cursor:
            cursor.execute(query, (order_id,))
            return cursor.fetchone()

    def get_order_by_number(self, order_number: str) -> Optional[Dict[str, Any]]:
        """Get order by order number."""
        query = "SELECT * FROM orders WHERE order_number = %s"

        with self.get_cursor() as cursor:
            cursor.execute(query, (order_number,))
            return cursor.fetchone()

    def update_order(self, order_id: int, order_data: Dict[str, Any]) -> bool:
        """Update order record."""
        allowed_fields = {
            'supplier_id', 'status', 'total_amount', 'currency',
            'order_items', 'shipping_address', 'billing_address',
            'notes', 'estimated_delivery', 'actual_delivery', 'metadata'
        }

        update_fields = []
        values = []

        for field, value in order_data.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = %s")
                values.append(value)

        if not update_fields:
            return False

        values.append(order_id)
        query = f"""
            UPDATE orders
            SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """

        with self.get_cursor() as cursor:
            cursor.execute(query, values)
            return cursor.rowcount > 0

    def get_orders_by_artisan(self, artisan_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get orders for a specific artisan."""
        query = """
            SELECT * FROM orders
            WHERE artisan_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """

        with self.get_cursor() as cursor:
            cursor.execute(query, (artisan_id, limit))
            return cursor.fetchall()

    def get_orders_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get orders by status."""
        query = """
            SELECT * FROM orders
            WHERE status = %s
            ORDER BY created_at DESC
            LIMIT %s
        """

        with self.get_cursor() as cursor:
            cursor.execute(query, (status, limit))
            return cursor.fetchall()

    # ===== AGENT STATE OPERATIONS =====

    def save_agent_state(self, agent_id: int, session_id: str,
                        state_data: Dict[str, Any], expires_at: datetime = None) -> bool:
        """Save or update agent state."""
        query = """
            INSERT INTO agent_state (agent_id, session_id, state_data, expires_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (agent_id, session_id)
            DO UPDATE SET
                state_data = EXCLUDED.state_data,
                expires_at = EXCLUDED.expires_at,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """

        with self.get_cursor() as cursor:
            cursor.execute(query, (
                agent_id,
                session_id,
                Json(state_data),
                expires_at
            ))
            return cursor.rowcount > 0

    def get_agent_state(self, agent_id: int, session_id: str) -> Optional[Dict[str, Any]]:
        """Get agent state."""
        query = """
            SELECT * FROM agent_state
            WHERE agent_id = %s AND session_id = %s AND is_active = true
        """

        with self.get_cursor() as cursor:
            cursor.execute(query, (agent_id, session_id))
            result = cursor.fetchone()
            if result:
                # Check if expired
                if result['expires_at'] and result['expires_at'] < datetime.now():
                    self.deactivate_agent_state(agent_id, session_id)
                    return None
                return result

        return None

    def deactivate_agent_state(self, agent_id: int, session_id: str) -> bool:
        """Deactivate agent state."""
        query = """
            UPDATE agent_state
            SET is_active = false, updated_at = CURRENT_TIMESTAMP
            WHERE agent_id = %s AND session_id = %s
        """

        with self.get_cursor() as cursor:
            cursor.execute(query, (agent_id, session_id))
            return cursor.rowcount > 0

    def cleanup_expired_states(self) -> int:
        """Clean up expired agent states."""
        query = """
            UPDATE agent_state
            SET is_active = false, updated_at = CURRENT_TIMESTAMP
            WHERE expires_at < CURRENT_TIMESTAMP AND is_active = true
        """

        with self.get_cursor() as cursor:
            cursor.execute(query)
            return cursor.rowcount

    # ===== UTILITY OPERATIONS =====

    def health_check(self) -> Dict[str, Any]:
        """Check database health and return status."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1 as health_check")
                result = cursor.fetchone()

            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "check_result": result['health_check'] if result else None
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

    def get_table_counts(self) -> Dict[str, int]:
        """Get row counts for all tables."""
        tables = ['agents', 'tools', 'artisans', 'suppliers', 'orders', 'agent_state']
        counts = {}

        for table in tables:
            try:
                with self.get_cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    result = cursor.fetchone()
                    counts[table] = result['count'] if result else 0
            except Exception as e:
                self.logger.error(f"Failed to get count for {table}: {e}")
                counts[table] = -1

        return counts

    def bulk_insert_artisans(self, artisans_data: List[Dict[str, Any]]) -> int:
        """Bulk insert multiple artisans."""
        if not artisans_data:
            return 0

        query = """
            INSERT INTO artisans (
                name, email, phone, latitude, longitude,
                specialties, rating, is_active, metadata
            ) VALUES %s
        """

        values = []
        for artisan in artisans_data:
            values.append((
                artisan['name'],
                artisan.get('email'),
                artisan.get('phone'),
                artisan.get('latitude'),
                artisan.get('longitude'),
                artisan.get('specialties', []),
                artisan.get('rating', 0),
                artisan.get('is_active', True),
                Json(artisan.get('metadata', {}))
            ))

        with self.get_cursor() as cursor:
            execute_values(cursor, query, values)
            return cursor.rowcount


# Convenience functions for common operations
def get_dal(config: DatabaseConfig = None) -> DataAccessLayer:
    """Get a DataAccessLayer instance."""
    return DataAccessLayer(config)


def create_artisan(artisan_data: Dict[str, Any], config: DatabaseConfig = None) -> int:
    """Convenience function to create an artisan."""
    dal = DataAccessLayer(config)
    return dal.create_artisan(artisan_data)


def get_artisan(artisan_id: int, config: DatabaseConfig = None) -> Optional[Dict[str, Any]]:
    """Convenience function to get an artisan."""
    dal = DataAccessLayer(config)
    return dal.get_artisan(artisan_id)


# Basic logging setup
logging.basicConfig(level=logging.INFO)
