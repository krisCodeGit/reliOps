# Contributing

This repository is still evolving, so keep changes small, reviewable, and easy to run locally.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py init-db
python manage.py run --debug
```

## Guidelines

- Prefer straightforward Python and standard-library solutions.
- Keep the dashboard copy aligned with what the app actually does.
- If you change seeded data in `mock_data/`, rerun `python manage.py init-db`.
- Do not commit local databases, cache files, or private notes from `docs/internal/`.

## Open-Source vs Enterprise Code

ReliOps has two tiers of code in the same repo:

**Open-source core** (committed to GitHub, public):
- `app/__init__.py`, `app/config.py`, `app/models.py`, `app/rules_engine.py`
- `app/templates/` (all HTML templates including `enterprise.html`)
- `mock_data/`, `manage.py`, `requirements.txt`

**Enterprise modules** (gitignored, never committed):
- `app/enterprise/` contains AI insights, pattern analysis, runbook generation, and data sanitization

### Rules for contributors

1. **Never import enterprise modules at the top level of open-source files.** Use lazy imports inside functions wrapped in `try/except ImportError`, or check `ENTERPRISE_AVAILABLE` before calling. See `app/__init__.py` for the pattern.

2. **The open-source core must work without `app/enterprise/`.** If you add a feature that depends on an enterprise module, the open-source path must gracefully degrade (return an empty result, a 403 response, or a "requires Enterprise" message).

3. **New proprietary features go in `app/enterprise/`.** If the feature is part of the paid enterprise offering (AI insights, advanced analytics, runbooks, continuous monitoring, dependency discovery APIs), it belongs in the enterprise package.

4. **Templates and marketing pages stay public.** `enterprise.html`, `help.html`, and other templates are intentionally public (sales and onboarding surfaces).

5. **Never hardcode secrets.** API keys, credentials, and internal IPs go in `.env` (gitignored). Use `app/config.py` to read them via `os.environ`.

6. **Check `.gitignore` before committing.** Run `git status` and verify nothing from `app/enterprise/`, `docs/internal/`, `instance/`, or `logs/` shows up as untracked-and-about-to-be-staged.

### How the enterprise import pattern works

```python
# In app/__init__.py
try:
    from app.enterprise.pattern_analyzer import detect_systemic_patterns
    from app.enterprise.runbook_generator import generate_runbook
    ENTERPRISE_AVAILABLE = True
except ImportError:
    detect_systemic_patterns = None
    generate_runbook = None
    ENTERPRISE_AVAILABLE = False

# Usage: always guard enterprise calls
patterns = detect_systemic_patterns(db) if detect_systemic_patterns else []

if not generate_runbook:
    return jsonify({'error': 'Requires ReliOps Enterprise'}), 403
```

## Pull Requests

- Summarize the user-visible change.
- Call out any schema, route, or data-shape changes.
- Note whether the change affects open-source core, enterprise, or both.
- Include manual verification steps when there is no automated test coverage.
