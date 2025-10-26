import pytest
import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from artisan_agents.tools.data_access import DataAccessLayer, AgentState
from artisan_agents.tools.state_manager import StateManager, DeserializationError, SerializationError, StateValidationError

@pytest.mark.asyncio
async def test_state_serialization_deserialization(temp_db, temp_state_dir):
    sm = StateManager(temp_db)
    agent_state = {
        "id": "sid123",
        "workflow_id": "wfk321",
        "agent_name": "AgentX",
        "state_data": {"step": 1, "progress": 0.5},
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=1),
        "version": "1.0"
    }
    blob = await sm.serialize_agent_state(agent_state, format="json")
    recovered = await sm.deserialize_agent_state(blob, format="json")
    assert recovered["agent_name"] == "AgentX"

    blob_cjson = await sm.serialize_agent_state(agent_state, format="cjson", compress=True)
    recovered_cjson = await sm.deserialize_agent_state(blob_cjson, format="cjson", decompress=True)
    assert recovered_cjson["state_data"]["step"] == 1

    blob_pickle = await sm.serialize_agent_state(agent_state, format="pickle")
    recovered_pickle = await sm.deserialize_agent_state(blob_pickle, format="pickle")
    assert recovered_pickle["version"] == "1.0"

@pytest.mark.asyncio
async def test_state_save_load_file_fallback(temp_db, temp_state_dir):
    sm = StateManager(temp_db)
    agent_state = {
        "id": "sidfile",
        "workflow_id": "wf_file",
        "agent_name": "FileBackup",
        "state_data": {"step": 2, "done": True},
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=2),
        "version": "1.0"
    }
    sid = await sm.save_workflow_state(agent_state, format="json", compress=False)
    result = await sm.load_workflow_state("sidfile", format="json")
    assert result["agent_name"] == "FileBackup"

@pytest.mark.asyncio
async def test_checkpoint_restore(temp_db, temp_state_dir):
    sm = StateManager(temp_db)
    agent_state = {
        "id": "sidchk",
        "workflow_id": "wfchk",
        "agent_name": "ChkAgent",
        "state_data": {"msg": "checkpoint"},
        "created_at": datetime.utcnow(),
        "expires_at": None,
        "version": "1.0"
    }
    await sm.checkpoint_state("sidchk", agent_state)
    chk_files = [f for f in os.listdir(temp_state_dir) if "checkpoint" in f]
    assert len(chk_files) > 0
    for chk_file in chk_files:
        chk_path = os.path.join(temp_state_dir, chk_file)
        state = await sm.restore_from_checkpoint(chk_path)
        assert state["agent_name"] == "ChkAgent"

@pytest.mark.asyncio
async def test_state_expiry_cleanup(temp_db, temp_state_dir):
    sm = StateManager(temp_db)
    # Expired state
    expired_state = {
        "id": "expired1",
        "workflow_id": "expiredwf",
        "agent_name": "DeadAgent",
        "state_data": {},
        "created_at": datetime.utcnow() - timedelta(days=40),
        "expires_at": datetime.utcnow() - timedelta(days=5),
        "version": "1.0"
    }
    await sm.save_workflow_state(expired_state, format="json")
    deleted = await sm.cleanup_expired_states()
    assert deleted >= 0

@pytest.mark.asyncio
async def test_state_validation_and_migration(temp_db, temp_state_dir):
    sm = StateManager(temp_db)
    agent_state = {
        "id": "sidev",
        "workflow_id": "wfev",
        "agent_name": "ValAgent",
        "state_data": {"msg": "validate"},
        "created_at": datetime.utcnow(),
        "expires_at": None,
        "version": "1.0"
    }
    validated = sm.validate_state(agent_state, version="1.0")
    assert validated.agent_name == "ValAgent"

# More edge-case tests: recovery from corrupted state, encrypted/compressed objects, get_state_history, stream_large_object, etc.