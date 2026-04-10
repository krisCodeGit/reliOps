# Contributing

This repository is still an MVP, so keep changes small, reviewable, and easy to run locally.

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
- Keep the dashboard copy aligned with what the product actually does.
- If you change seeded data in `mock_data/`, rerun `python manage.py init-db`.
- Do not commit local databases, cache files, or private notes from `docs/internal/`.

## Pull Requests

- Summarize the user-visible change.
- Call out any schema, route, or data-shape changes.
- Include manual verification steps when there is no automated test coverage.
