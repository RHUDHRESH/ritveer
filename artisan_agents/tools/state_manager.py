# Agent state serialization and workflow persistence utilities

import os
import json
import pickle
import zlib
import base64
import hashlib
import asyncio
import logging
import uuid
from copy import deepcopy
from typing import Any, Dict, Optional, List, Type, Callable, Union
from datetime import datetime, timedelta
from functools import wraps

from pydantic import BaseModel, ValidationError, validator

# =====================
# Logging Configuration
# =====================

def configure_logger(name="artisan_agents.state_manager"):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s][%(levelname)s][%(correlation_id)s] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

logger = configure_logger()

def log_info(msg, cid=None): logger.info(msg, extra={'correlation_id': cid or ''})
def log_warn(msg, cid=None): logger.warning(msg, extra={'correlation_id': cid or ''})
def log_error(msg, cid=None): logger.error(msg, extra={'correlation_id': cid or ''})

# ============================
# Configuration, State Paths
# ============================

STATE_VERSION = "1.0"
STATE_DIR = os.getenv("ARTISAN_STATE_DIR", "./agent_state")
os.makedirs(STATE_DIR, exist_ok=True)
ENCRYPTION_KEY = os.getenv("AGENT_STATE_ENCRYPTION_KEY", "insecure-key")
DEFAULT_EXPIRY_DAYS = int(os.getenv("AGENT_STATE_DEFAULT_EXPIRE", "30"))

# =================
# Custom Exceptions
# =================

class StateManagerError(Exception): pass
class SerializationError(StateManagerError): pass
class DeserializationError(StateManagerError): pass
class StateValidationError(StateManagerError): pass
class StateExpiredError(StateManagerError): pass

# =================
# Serialization Utils
# =================

def with_correlation_id(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cid = kwargs.get("correlation_id", None)
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log_error(f"Exception in {func.__name__}: {e}", cid)
            raise
    return wrapper

def serialize_json(payload: Any) -> bytes:
    return json.dumps(payload, default=str).encode()

def deserialize_json(blob: bytes) -> Any:
    return json.loads(blob.decode())

def serialize_pickle(payload: Any) -> bytes:
    return pickle.dumps(payload)

def deserialize_pickle(blob: bytes) -> Any:
    return pickle.loads(blob)

def compress_data(data: bytes) -> bytes:
    return zlib.compress(data, 9)

def decompress_data(blob: bytes) -> bytes:
    return zlib.decompress(blob)

def encrypt_data(blob: bytes, key: str) -> bytes:
    k = hashlib.sha256(key.encode()).digest()
    return bytes([b ^ k[i % len(k)] for i, b in enumerate(blob)])

def decrypt_data(blob: bytes, key: str) -> bytes:
    return encrypt_data(blob, key)  # Symmetric

def state_file_path(state_id: str, format: str):
    ts = datetime.utcnow().strftime('%Y%m%d')
    return os.path.join(STATE_DIR, f"{state_id}.{format.lower()}.{ts}")

def generate_correlation_id() -> str:
    return str(uuid.uuid4())[:12]

# ===========================
# Pydantic AgentState Model
# ===========================

class AgentStateData(BaseModel):
    id: str
    workflow_id: str
    agent_name: str
    state_data: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime]
    version: str

    @validator('version')
    def check_version(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Missing version!")
        return v

    @validator('created_at', pre=True, always=True)
    def ensure_datetime_created_at(cls, v):
        if isinstance(v, str): return datetime.fromisoformat(v)
        return v

    @validator('expires_at', pre=True, always=True)
    def ensure_datetime_expires_at(cls, v):
        if v is None: return None
        if isinstance(v, str): return datetime.fromisoformat(v)
        return v

# ===========================
# StateManager Implementation
# ===========================

class StateManager:
    SUPPORTED_FORMATS = ["json", "pickle", "cjson"]
    
    def __init__(self, data_access_layer):
        self.dal = data_access_layer

    # ----------- SERIALIZATION -----------
    def _serialize_obj(self, obj: Dict[str, Any], format: str = "json", compress: bool = False, encrypt: bool = False) -> bytes:
        try:
            if format == "json":
                blob = serialize_json(obj)
            elif format == "pickle":
                blob = serialize_pickle(obj)
            elif format == "cjson":
                buf = serialize_json(obj)
                blob = compress_data(buf)
            else:
                raise SerializationError(f"Unsupported format {format}")
            if encrypt:
                blob = encrypt_data(blob, ENCRYPTION_KEY)
            return blob
        except Exception as e:
            raise SerializationError(f"Serialization failed: {e}")

    def _deserialize_obj(self, blob: bytes, format: str = "json", decompress: bool = False, decrypt: bool = False) -> dict:
        try:
            if decrypt:
                blob = decrypt_data(blob, ENCRYPTION_KEY)
            if format == "json":
                return deserialize_json(blob)
            elif format == "pickle":
                return deserialize_pickle(blob)
            elif format == "cjson":
                raw = decompress_data(blob)
                return deserialize_json(raw)
            else:
                raise DeserializationError(f"Unsupported format {format}")
        except Exception as e:
            raise DeserializationError(f"Deserialization failed: {e}")
        
    # ----------- VERSIONING, MIGRATION -----------
    def _migrate_state(self, state: Dict[str, Any], target_version: str) -> Dict[str, Any]:
        # Migration logic placeholder
        state = deepcopy(state)
        orig_ver = state.get('version', "1.0")
        # example: migrate "old_key" -> "new_key"
        if orig_ver == "1.0" and target_version == "2.0":
            state['version'] = "2.0"
            # Example: state['new_field'] = state.pop('old_field')
        # ... Actual migrations developed as state schema evolves
        return state

    # ----------- VALIDATION -----------

    def validate_state(self, agent_state: Dict[str, Any], version: Optional[str]=None) -> AgentStateData:
        try:
            state = deepcopy(agent_state)
            if version:
                state = self._migrate_state(state, version)
            return AgentStateData(**state)
        except ValidationError as e:
            raise StateValidationError(str(e))

    # ----------- SAVE/LOAD MAIN APIS -----------

    async def save_workflow_state(self, agent_state: Dict[str, Any], format: str = "json", compress: bool = False,
                                  encrypt: bool = False, metadata: Optional[dict]=None) -> str:
        obj = deepcopy(agent_state)
        obj["version"] = STATE_VERSION
        blob = self._serialize_obj(obj, format=format, compress=compress, encrypt=encrypt)
        state_id = obj.get("id", str(uuid.uuid4()))
        try:
            await self.dal.agent_states.save_agent_state(
                state_id, obj["workflow_id"], obj["agent_name"], blob, datetime.utcnow(),
                obj.get("expires_at", datetime.utcnow() + timedelta(days=DEFAULT_EXPIRY_DAYS)), STATE_VERSION,
            )
            # Save to file as well for fallback
            with open(state_file_path(state_id, format), "wb") as f:
                f.write(blob)
            log_info(f"Saved state {state_id} to DB and file", state_id)
        except Exception as exc:
            log_error(f"Primary DB write error for state {state_id}: {exc}", state_id)
            with open(state_file_path(state_id, format), "wb") as f:
                f.write(blob)
            log_warn(f"State written to file after DB write failed: {state_id}", state_id)
        return state_id

    async def load_workflow_state(self, state_id: str, format: str = "json", decompress: bool = False,
                                 decrypt: bool = False, target_version: Optional[str]=None) -> dict:
        # Try DB first, fallback to file
        try:
            blob = await self.dal.agent_states.load_agent_state(state_id)
            state = self._deserialize_obj(blob, format=format, decompress=decompress, decrypt=decrypt)
            self.validate_state(state, version=target_version)
            log_info(f"Loaded state {state_id} from DB", state_id)
            return state
        except Exception as e:
            log_warn(f"State {state_id} load DB failed: {e}", state_id)
            # Fallback to file
            try:
                with open(state_file_path(state_id, format), "rb") as f:
                    blob = f.read()
                state = self._deserialize_obj(blob, format=format, decompress=decompress, decrypt=decrypt)
                self.validate_state(state, version=target_version)
                log_info(f"Loaded state {state_id} from file fallback", state_id)
                return state
            except Exception as err2:
                log_error(f"State {state_id} load failed from both DB and file: {err2}", state_id)
                raise DeserializationError("Could not load state from DB or file.")

    async def serialize_agent_state(self, obj: Dict[str, Any], format: str="json", compress:bool=False, encrypt:bool=False):
        """Just serialization, no persistence (for network transmission, etc.)"""
        try:
            blob = self._serialize_obj(obj, format=format, compress=compress, encrypt=encrypt)
            log_info(f"Serialized agent state obj {obj.get('id', '')}", obj.get('id',''))
            return blob
        except Exception as e:
            log_error(f"Serialization failed: {e}", obj.get('id',''))
            raise

    async def deserialize_agent_state(self, blob: bytes, format: str="json", decompress:bool=False, decrypt:bool=False):
        """Just deserialization, no DB interaction."""
        try:
            obj = self._deserialize_obj(blob, format=format, decompress=decompress, decrypt=decrypt)
            log_info("Deserialized agent state blob", obj.get('id',''))
            self.validate_state(obj)
            return obj
        except Exception as e:
            log_error(f"Deserialization failed: {e}", None)
            raise

    # ----------- CHECKPOINTS, RECOVERY -----------

    async def checkpoint_state(self, state_id: str, agent_state: Dict[str, Any], format: str = "json"):
        """Point-in-time snapshot."""
        ts = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
        fname = state_file_path(f"{state_id}_checkpoint_{ts}", format)
        blob = self._serialize_obj(agent_state, format)
        with open(fname, "wb") as f:
            f.write(blob)
        log_info(f"Checkpointed state {state_id} at {fname}", state_id)

    async def restore_from_checkpoint(self, checkpoint_file: str, format: str = "json", decompress:bool=False, decrypt:bool=False):
        """Load from checkpoint file on disk."""
        with open(checkpoint_file, "rb") as f:
            blob = f.read()
        state = self._deserialize_obj(blob, format=format, decompress=decompress, decrypt=decrypt)
        self.validate_state(state)
        log_info(f"Restored state from checkpoint {checkpoint_file}", state.get('id',''))
        return state

    # ----------- CLEANUP, STATE HISTORY -----------

    async def cleanup_expired_states(self) -> int:
        """Remove expired states from DB and disk."""
        now = datetime.utcnow()
        deleted = 0
        # Clean DB
        try:
            await self.dal.agent_states.cleanup_expired_states()
            log_info("Expired states cleaned up in DB", None)
        except Exception as e:
            log_warn(f"DB cleanup failed: {e}", None)
        # Clean disk
        files = os.listdir(STATE_DIR)
        for f in files:
            path = os.path.join(STATE_DIR, f)
            if not f.endswith(('.json', '.pickle', '.cjson')): continue
            try:
                ctime = datetime.fromtimestamp(os.path.getctime(path))
                if (now - ctime).days > DEFAULT_EXPIRY_DAYS:
                    os.remove(path)
                    deleted += 1
            except Exception:
                continue
        log_info(f"Expired states cleaned up on disk: {deleted} files", None)
        return deleted

    async def get_state_history(self, workflow_id: str) -> List[Dict[str, Any]]:
        try:
            states = await self.dal.agent_states.get_by_workflow(workflow_id)
            history = []
            for s in states:
                d = s.dict()
                # Don't return big blobs or sensitive content
                d.pop('state_data', None)
                history.append(d)
            return history
        except Exception as e:
            log_warn(f"State history fetch failed: {e}", workflow_id)
            return []

# ============================
# Memory-Efficient State Tools
# ============================

def stream_large_state_file(path: str, chunk_size=65536):
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk: break
            yield chunk

def process_large_state(blob: bytes, func: Callable[[bytes],Any], chunk_size=65536):
    # In-memory chunked processing for huge blobs
    for offset in range(0, len(blob), chunk_size):
        yield func(blob[offset:offset+chunk_size])

# ============================
# END OF MODULE
# ===========================
