# ReliOps

ReliOps is a reliability analysis platform for distributed systems, built around dependency graphs, scoring models, and audit reports.

This public codebase captures the core workflow: seeded mock data, a database-backed model, a browser dashboard, and a configuration audit flow for evaluating service definitions against operational risk rules. It is designed to be easy to run locally while still communicating the platform direction clearly.

## What It Does

- Scans services against a fixed set of reliability rules.
- Scores aggregate operational risk across the environment.
- Highlights blast-radius hotspots and incident recurrence signals.
- Stores seeded mock services, dependencies, and incidents in a local database.
- Exposes JSON endpoints for the dashboard and audit flow.

The bundled dataset is synthetic. Service names, incidents, and impact figures are sample data for local demos only.

## Stack

- Python 3
- Flask
- Database-backed persistence
- Vanilla HTML, CSS, and JavaScript

## Project Layout

```text
app/
  __init__.py          Flask app and routes
  config.py            Paths and runtime settings
  models.py            Database schema and query helpers
  rules_engine.py      Reliability scanning logic
  templates/           Dashboard and audit pages
mock_data/             Seed data used for local demos
docs/internal/         Local-only notes ignored in normal public commits
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
- `docs/internal/` exists so private working notes can stay local without being published.
- The public repo focuses on the scoring engine, graph analysis, and audit workflow.
- See [PUBLIC_RELEASE_CHECKLIST.md](PUBLIC_RELEASE_CHECKLIST.md) before a public push.

## Development

Common local commands:

```bash
python manage.py init-db
python manage.py run --debug
```

If you change the mock data, rerun `python manage.py init-db` to rebuild the local database.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development expectations and repo conventions.

## Security

See [SECURITY.md](SECURITY.md) for reporting guidance.

## License

This project is released under the MIT License. See [LICENSE](LICENSE).
