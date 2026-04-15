# Contributing

Keep changes small, reviewable, and easy to run locally.

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
- Keep public docs and UI copy aligned with what the open-source repo actually ships.
- If you change seeded data in `mock_data/`, rerun `python manage.py init-db`.
- Do not commit local databases, cache files, logs, secrets, or private planning notes.

## Before Opening A PR

- Run `git status` and confirm only intended files are included.
- Call out any route, schema, or data-shape changes.
- Include brief manual verification steps when automated coverage is absent.
