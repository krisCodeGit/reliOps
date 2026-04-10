# ReliOps MVP

Analyze reliability risks in distributed systems using dependency graphs, scoring models, and audit reports.

ReliOps is a small Flask prototype for exploring reliability risk reviews against a service catalog and dependency graph. It ships with seeded mock data, a lightweight SQLite store, a browser dashboard, and a configuration audit flow for trying scans against sample service definitions.

The current codebase is best described as a working MVP:

- It is easy to run locally.
- It is useful for demos, internal discussion, and product exploration.
- It is not packaged as a production-ready platform.

## What It Does

- Scans services against a fixed set of reliability rules.
- Scores aggregate operational risk across the environment.
- Highlights blast-radius hotspots and incident recurrence signals.
- Stores seeded mock services, dependencies, and incidents in SQLite.
- Exposes JSON endpoints for the dashboard and audit flow.

The bundled dataset is synthetic. Service names, incidents, and impact figures are sample data for local demos only.

## Stack

- Python 3
- Flask
- SQLite
- Vanilla HTML, CSS, and JavaScript

## Project Layout

```text
app/
  __init__.py          Flask app and routes
  config.py            Paths and runtime settings
  models.py            SQLite schema and query helpers
  rules_engine.py      Reliability scanning logic
  templates/           Dashboard and audit pages
mock_data/             Seed data used for local demos
docs/internal/         Local-only internal notes kept out of git
manage.py              CLI for database setup and dev server
```

## Getting Started

1. Create and activate a virtual environment.
2. Install dependencies.
3. Seed the local database.
4. Start the dev server.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py init-db
python manage.py run --host 127.0.0.1 --port 5000
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) for the dashboard or [http://127.0.0.1:5000/audit](http://127.0.0.1:5000/audit) for the configuration audit page.

## API Endpoints

- `GET /api/dashboard` returns the main dashboard payload.
- `GET /api/risks` returns rule violations from the current dataset.
- `GET /api/dependencies` returns the dependency graph for visualization.
- `GET /api/drift` returns snapshot drift signals.
- `GET /api/incidents` returns historical incidents.
- `GET /api/reliability-debt` returns open reliability debt items.
- `GET /api/blast-radius/<service_name>` returns dependent-service impact for one service.
- `POST /api/audit` evaluates an uploaded service configuration.

## Notes for a Public Repo

- Runtime artifacts live under `instance/` and should not be committed.
- `docs/internal/` is reserved for local internal notes; its contents are ignored by git except for a small placeholder README.
- The app currently allows open CORS and uses seeded demo data by default.
- There is no authentication, tenancy, or deployment hardening in this MVP.
- See [PUBLIC_RELEASE_CHECKLIST.md](/Users/kris/Documents/Documents - Kris’s MacBook Pro/UpliftPal/reliops_mvp/PUBLIC_RELEASE_CHECKLIST.md) before the first public push.

## Development

Common local commands:

```bash
python manage.py init-db
python manage.py run --debug
```

If you change the mock data, rerun `python manage.py init-db` to rebuild the local SQLite database.

## Contributing

See [CONTRIBUTING.md](/Users/kris/Documents/Documents - Kris’s MacBook Pro/UpliftPal/reliops_mvp/CONTRIBUTING.md) for development expectations and repo conventions.

## Security

See [SECURITY.md](/Users/kris/Documents/Documents - Kris’s MacBook Pro/UpliftPal/reliops_mvp/SECURITY.md) for reporting guidance.

## License

This project is released under the MIT License. See [LICENSE](/Users/kris/Documents/Documents - Kris’s MacBook Pro/UpliftPal/reliops_mvp/LICENSE).
