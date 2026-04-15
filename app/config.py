"""
ReliOps - Configuration.
Paths, runtime settings, and .env loader.

Author: Kris R. (UpliftPal)
"""

import os
from pathlib import Path

# Base directory is the repo root (parent of app/)
BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Load .env file (stdlib only, no python-dotenv dependency)
# ---------------------------------------------------------------------------
def _load_dotenv(env_path):
    """Load key=value pairs from a .env file into os.environ.
    Skips comments, blank lines, and already-set env vars."""
    if not os.path.isfile(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip()
            # Strip inline comments (e.g. "14400  # seconds")
            # but not inside quoted values
            if value and value[0] not in ('"', "'"):
                value = value.split('#')[0].strip()
            # Don't override vars already set in the real environment
            if key not in os.environ:
                os.environ[key] = value


_load_dotenv(BASE_DIR / '.env')
INSTANCE_DIR = BASE_DIR / 'instance'
LOGS_DIR = BASE_DIR / 'logs'
CACHE_DIR = LOGS_DIR / 'cache'
MOCK_DATA_DIR = BASE_DIR / 'mock_data'
DB_PATH = INSTANCE_DIR / 'reliops.db'
# ---------------------------------------------------------------------------
# Caching strategy
# ---------------------------------------------------------------------------
# Content-hash mode (default): cache invalidates when the DB changes,
# not on a timer. Best for low-traffic sites — every visitor gets instant
# load, AI only called when data actually changes.
#
# Set CACHE_MODE=ttl to switch to time-based expiry instead.
# CACHE_TTL only applies when CACHE_MODE=ttl.
# ---------------------------------------------------------------------------
CACHE_MODE = os.environ.get('CACHE_MODE', 'content-hash')        # content-hash | ttl
CACHE_TTL = int(os.environ.get('CACHE_TTL', '14400'))             # Seconds (only for ttl mode)
PORT = int(os.environ.get('PORT', 5000))

# ---------------------------------------------------------------------------
# Asset cache-busting & static file caching
# ---------------------------------------------------------------------------
# Bump ASSET_VERSION on each deploy to force browsers to re-fetch static assets.
# Uses semver (e.g. 1.0.0 → 1.1.0) so you can track what changed.
# In templates: <link href="/static/style.css?v={{ asset_v }}">
ASSET_VERSION = os.environ.get('ASSET_VERSION', '1.0.0')

# How long (seconds) browsers/CDN cache /static/ files. 604800 = 7 days.
# ASSET_VERSION query param busts cache on deploy regardless of this TTL.
STATIC_CACHE_TIMEOUT = int(os.environ.get('STATIC_CACHE_TIMEOUT', '604800'))

# Ensure directories exist
INSTANCE_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
