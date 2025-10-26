# Pytest configuration and shared fixtures for artisan marketplace system

import os
import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime

from artisan_agents.tools.data_access import DataAccessLayer, DB_PATH

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def temp_db(tmp_path):
    db_file = tmp_path / "test_artisan.db"
    dal = DataAccessLayer(str(db_file))
    await dal.initialize()
    yield dal
    await dal.close()
    if os.path.exists(db_file):
        os.remove(db_file)

@pytest.fixture(scope="function")
def temp_state_dir(tmp_path):
    state_dir = tmp_path / "state_test"
    os.makedirs(state_dir, exist_ok=True)
    yield str(state_dir)
    shutil.rmtree(state_dir)