"""ReliOps configuration."""

import os
from pathlib import Path

# Base directory is the repo root (parent of app/)
BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / 'instance'
CACHE_DIR = INSTANCE_DIR / 'cache'
MOCK_DATA_DIR = BASE_DIR / 'mock_data'
DB_PATH = INSTANCE_DIR / 'reliops.db'
CACHE_TTL = 600  # 10 minutes in seconds
PORT = int(os.environ.get('PORT', 5000))

# Ensure directories exist
INSTANCE_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
