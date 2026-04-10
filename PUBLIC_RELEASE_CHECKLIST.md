# Public Release Checklist

Use this before any public GitHub push.

## Repo Hygiene

- Confirm the repo root contains only files you intend to publish.
- Keep `.venv/`, `__pycache__/`, `instance/reliops.db`, and `instance/cache/` out of the commit.
- Keep private planning notes under `docs/internal/`; that folder is configured to stay local.

## Content Review

- Read the public [README.md](README.md) once as an external reader.
- Confirm the mock data is acceptable to publish and still clearly synthetic.
- Remove any references to customers, deals, internal roadmaps, or private product plans from public files.

## Before `git add .`

- Check that no local databases or cache files are sitting in the staging set.
- Check that no editor settings or OS artifacts were picked up.
- If this repo was previously private, confirm old tracked runtime files are removed from version control before pushing.

## Quick Smoke Test

```bash
source .venv/bin/activate
python manage.py init-db
python manage.py run --host 127.0.0.1 --port 5000
```

Then verify:

- `/`
- `/audit`
- `/api/dashboard`
- `/api/dependencies`

## GitHub Setup

- Add a short repo description.
- Choose a small set of topics.
- Pin the MIT license.
- Decide whether issues and discussions should be enabled on day one.

## Nice-to-Have

- Add one or two screenshots to the repo.
- Tag the first public commit or release.
- Add CI once the project has a stable test path.
