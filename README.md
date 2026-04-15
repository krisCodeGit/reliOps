# ReliOps

ReliOps is an open-source reliability audit tool for service architectures.

It scans service configuration and dependency data to highlight resilience gaps,
surface likely failure hotspots, and prioritize what to fix first.

The public repository is intentionally kept lightweight. It includes a
self-hostable core for running audits, exploring dependency blast radius, and
reviewing ranked findings against a synthetic sample environment.

## What The Public Edition Includes

- Configuration audit for YAML and JSON service definitions
- Dependency graph and blast-radius analysis
- Ranked reliability findings and remediation hints
- Sample data for local evaluation

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py init-db
python manage.py run --host 127.0.0.1 --port 5000
```

Open `http://127.0.0.1:5000` for the dashboard.
Open `http://127.0.0.1:5000/audit` to run an audit against your own config.

## API

- `GET /api/dashboard`
- `GET /api/risks`
- `GET /api/dependencies`
- `GET /api/drift`
- `GET /api/incidents`
- `GET /api/reliability-debt`
- `GET /api/blast-radius/<service>`
- `POST /api/audit`

## Project Layout

```text
app/
  __init__.py
  config.py
  models.py
  rules_engine.py
  templates/
mock_data/
manage.py
requirements.txt
```

## Sample Data

The bundled dataset is synthetic and exists only to demonstrate the workflow
locally.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## License

MIT License. See [LICENSE](LICENSE).
