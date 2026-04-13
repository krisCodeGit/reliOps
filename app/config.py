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
            # Don't override vars already set in the real environment
            if key not in os.environ:
                os.environ[key] = value


_load_dotenv(BASE_DIR / '.env')
INSTANCE_DIR = BASE_DIR / 'instance'
CACHE_DIR = INSTANCE_DIR / 'cache'
MOCK_DATA_DIR = BASE_DIR / 'mock_data'
DB_PATH = INSTANCE_DIR / 'reliops.db'
CACHE_TTL = 600  # 10 minutes in seconds
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

# ---------------------------------------------------------------------------
# AI-Enhanced Insights (opt-in)
# ---------------------------------------------------------------------------
# Set AI_INSIGHTS_ENABLED=true to use an LLM for richer reliability insights.
# All service names and identifiers are anonymized before sending to the LLM.
# If the AI provider is unavailable, ReliOps falls back to pattern-based insights.

AI_INSIGHTS_ENABLED = os.environ.get('AI_INSIGHTS_ENABLED', 'false').lower() == 'true'
AI_PROVIDER = os.environ.get('AI_PROVIDER', 'none')          # anthropic | openai | local | none
AI_API_KEY = os.environ.get('AI_API_KEY', '')
AI_MODEL = os.environ.get('AI_MODEL', '')                     # e.g. claude-sonnet-4-20250514, gpt-4o
AI_BASE_URL = os.environ.get('AI_BASE_URL', '')               # For local/self-hosted models
AI_TIMEOUT = int(os.environ.get('AI_TIMEOUT', '5'))           # Seconds before fallback

# Ensure directories exist
INSTANCE_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
