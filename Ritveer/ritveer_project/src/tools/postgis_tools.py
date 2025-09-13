import psycopg2
from psycopg2 import extras
from typing import List, Dict, Any, Optional
from config.settings import settings

def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database.
    """
    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD
    )
    return conn

def find_artisan_clusters(
    target_location: Dict[str, float],  # e.g., {"latitude": 12.9716, "longitude": 77.5946}
    k_clusters: int = 3,
    craft_type: str = None
) -> List[Dict[str, Any]]:
    """
    Finds clusters of artisans near a target location using ST_ClusterKMeans.

    Args:
        target_location: A dictionary with 'latitude' and 'longitude' of the target.
        k_clusters: The number of clusters to form.
        craft_type: Optional. Filter artisans by craft type.

    Returns:
        A list of dictionaries, where each dictionary represents an artisan
        and includes their cluster ID.
    """
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)

        query = f"""
        SELECT
            id,
            name,
            craft_type,
            ST_X(location) AS longitude,
            ST_Y(location) AS latitude,
            ST_ClusterKMeans(location, %s) OVER () AS cluster_id
        FROM
            artisans
        WHERE
            ST_DWithin(
                location,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                100000 -- Search within 100 km radius (in meters)
            )
        """
        params = [k_clusters, target_location["longitude"], target_location["latitude"]]

        if craft_type:
            query += " AND craft_type ILIKE %s"
            params.append(f"%{craft_type}%")

        cur.execute(query, params)
        clusters = cur.fetchall()
        return clusters
    except Exception as e:
        print(f"Error finding artisan clusters: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def record_transaction(
    transaction_id: str,
    amount: float,
    currency: str,
    transaction_type: str,
    status: str,
    order_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Records a financial transaction in the ledger table.

    Args:
        transaction_id: A unique ID for the transaction (e.g., Razorpay payment ID).
        amount: The amount of the transaction.
        currency: The currency of the transaction.
        transaction_type: Type of transaction (e.g., 'payment_in', 'payment_out').
        status: Status of the transaction (e.g., 'approved', 'pending_approval').
        order_id: Optional. The associated order ID.

    Returns:
        A dictionary with the recorded transaction details, or an error message.
    """
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
        INSERT INTO ledger (transaction_id, order_id, amount, currency, transaction_type, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, timestamp;
        """
        cur.execute(query, (transaction_id, order_id, amount, currency, transaction_type, status))
        
        result = cur.fetchone()
        conn.commit()
        
        return {
            "id": result[0],
            "transaction_id": transaction_id,
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "transaction_type": transaction_type,
            "status": status,
            "timestamp": result[1]
        }
    except Exception as e:
        print(f"LEDGER TOOL: Error recording transaction: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def update_supplier_reliability(supplier_name: str, score_change: float) -> Dict[str, Any]:
    """
    Updates the reliability score for a given supplier.

    Args:
        supplier_name: The name of the supplier.
        score_change: The amount to add to the current reliability score.
                      Can be positive (improvement) or negative (degradation).

    Returns:
        A dictionary with the updated supplier details, or an error message.
    """
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        
        # Ensure supplier exists, or insert with default score
        cur.execute("""
            INSERT INTO suppliers (name, reliability_score)
            VALUES (%s, 0.0)
            ON CONFLICT (name) DO NOTHING;
        """, (supplier_name,))
        
        cur.execute("""
            UPDATE suppliers
            SET reliability_score = reliability_score + %s
            WHERE name = %s
            RETURNING id, name, reliability_score;
        """, (score_change, supplier_name))
        
        updated_supplier = cur.fetchone()
        conn.commit()
        
        if updated_supplier:
            return updated_supplier
        else:
            return {"error": f"Supplier {supplier_name} not found or not updated."}
            
    except Exception as e:
        print(f"LEARN TOOL: Error updating supplier reliability: {e}")
        if conn:
            conn.rollback()
        return {"error": str(e)}
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
