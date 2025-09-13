import redis
import json
from typing import Dict, Any
from config.settings import settings

# Initialize Redis client
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True
    )
    redis_client.ping()
    print("RedisUtils: Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    print(f"RedisUtils: Could not connect to Redis: {e}")
    redis_client = None

REDIS_RETRY_STREAM = "ritveer_retry_stream"

def add_to_retry_stream(task_details: Dict[str, Any]) -> bool:
    """
    Adds a failed task to a Redis Stream for later retry.

    Args:
        task_details: A dictionary containing details of the failed task,
                      e.g., {'agent': 'commit_agent', 'tool': 'create_payment_order', 'args': {...}}

    Returns:
        True if the task was added to the stream, False otherwise.
    """
    if not redis_client:
        print("RedisUtils: Not connected to Redis. Cannot add task to retry stream.")
        return False

    try:
        # Add the task details as a JSON string to the Redis Stream
        redis_client.xadd(REDIS_RETRY_STREAM, {"task": json.dumps(task_details)})
        print(f"RedisUtils: Added task to retry stream: {task_details.get('tool', 'unknown')}")
        return True
    except Exception as e:
        print(f"RedisUtils: Error adding task to retry stream: {e}")
        return False
