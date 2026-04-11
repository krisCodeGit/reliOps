# ReliOps

Proactive reliability risk intelligence for service architectures.

ReliOps scans your service configs for the operational risks that actually cause outages: single-AZ deployments without failover, missing circuit breakers on high-fan-out services, SLOs silently eroding week over week. It maps your dependency graph, scores blast radius, and tells you what to fix first.

Built for SRE and platform engineering teams running 10-50 service environments where reliability gaps turn into production incidents.

---

## What It Does

**8 reliability rules** scan your service architecture and produce an Operational Reliability Risk score (0-100):

- **Blast radius simulation** uses BFS traversal of your dependency graph to show which services cascade when one goes down
- **Incident recurrence scoring** pattern-matches current architecture gaps against past incident signatures and flags recurrence probability
- **SLO breach detection** surfaces services trending below target before they breach, weighted by tier criticality
- **Configuration audit** lets you upload any YAML/JSON service definition and get a risk assessment against the same engine that powers the dashboard
- **Natural language insights** produce targeted recommendations written like an SRE analyst briefing, not generic advice
- **AI-enhanced insights (opt-in)** connect an LLM for contextual recommendations. Supports Anthropic Claude, OpenAI, or a self-hosted local LLM where nothing leaves your network. All data is anonymized before sending. Falls back to pattern-based insights if AI is unavailable.

## AI Insights

Optional, off by default. The platform works without it.

| Provider | Data leaves your network? | Requires API key? |
|----------|--------------------------|-------------------|
| `local` | **No** (runs on your infrastructure) | No (unless your endpoint requires one) |
| `anthropic` | Yes (anonymized data only) | Yes |
| `openai` | Yes (anonymized data only) | Yes |

For compliance-sensitive environments, use `AI_PROVIDER=local` with any OpenAI-compatible self-hosted model (Ollama, vLLM, llama.cpp, LocalAI, LM Studio).

```bash
cp .env.example .env
# Edit .env:
AI_INSIGHTS_ENABLED=true
AI_PROVIDER=local
AI_BASE_URL=http://localhost:11434
```

All service names and internal identifiers are stripped before the LLM sees anything. The model receives anonymized risk patterns only (e.g., "Service-A: CRITICAL, single AZ, blast radius 7").

## Scoring Model

| Score | Label | Meaning |
|-------|-------|---------|
| 80-100 | CRITICAL | Active risk of cascading production failure |
| 60-79 | HIGH | Significant gaps requiring near-term remediation |
| 40-59 | MEDIUM | Architectural debt accumulating |
| 0-39 | LOW | Strong operational posture |

The composite score weights severity, recurrence likelihood, SLO gap penalties, and tier-1 criticality multipliers.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # configure settings (AI insights are optional)
python manage.py init-db
python manage.py run --host 127.0.0.1 --port 5000
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) for the dashboard.
Open [http://127.0.0.1:5000/audit](http://127.0.0.1:5000/audit) to audit your own service config.

## Stack

- **Python 3 + Flask** with no ORM, no Redis, no queue. Runs anywhere.
- **SQLite** for portable single-file storage. No infrastructure required.
- **Vanilla HTML/CSS/JS + D3.js** for the interactive dependency graph with drag, zoom, and blast radius highlighting.
- **Responsive design** with full mobile, tablet, and desktop support.

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard` | GET | Full dashboard payload: risk score, findings, insights, debt |
| `/api/risks` | GET | All rule violations from current scan |
| `/api/dependencies` | GET | D3-compatible dependency graph with per-node risk levels |
| `/api/drift` | GET | Snapshot-to-snapshot drift signals |
| `/api/incidents` | GET | Historical incident data |
| `/api/reliability-debt` | GET | Open reliability debt items with effort estimates |
| `/api/blast-radius/<service>` | GET | Cascading failure impact for a single service |
| `/api/audit` | POST | Evaluate custom service config against the rules engine |
| `/api/runbook/<service>` | POST | Generate incident response runbook (enterprise) |

## Project Layout

```
app/
  __init__.py          Flask app, routes, caching, dashboard builders
  config.py            Paths and runtime settings
  models.py            SQLite schema and query layer
  rules_engine.py      8-rule reliability scanner + scoring model
  templates/           Dashboard, audit, enterprise, and help UI
  enterprise/          (optional) Proprietary modules, not in open-source distro
mock_data/             13 services, 20 dependencies, 8+ incidents
manage.py              CLI for database setup and dev server
```

The `app/enterprise/` directory contains paid features (AI insights, pattern analysis, runbook generation). The open-source core works without it. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## How It Compares

| Capability | ReliOps | Backstage | Rootly | Sleuth | PagerDuty |
|-----------|---------|-----------|--------|--------|-----------|
| Dependency-aware risk scoring | Yes | -- | -- | -- | -- |
| Blast radius simulation | Yes | -- | -- | -- | -- |
| Incident recurrence analysis | Yes | -- | Partial | -- | -- |
| Configuration audit | Yes | -- | -- | -- | -- |
| SLO breach trending | Yes | -- | -- | Yes | Partial |
| Self-hosted / no vendor lock-in | Yes | Yes | -- | -- | -- |
| Zero infrastructure required | Yes | -- | -- | -- | -- |

## Rules Engine

| Rule | Severity | What It Catches |
|------|----------|-----------------|
| `missing_cross_az_failover` | CRITICAL | Tier-1 services in single AZ without failover |
| `single_point_of_failure` | CRITICAL | Services that 3+ critical dependents rely on without redundancy |
| `missing_circuit_breaker` | HIGH | High fan-out services (3+ deps) with no circuit breaker |
| `no_slo_defined` | HIGH | Tier-1 services without explicit SLO targets |
| `slo_breach_trending` | VARIES | Actual SLO tracking below target, severity scaled by gap size |
| `retry_storm_risk` | MEDIUM | High fan-out without rate limiting |
| `dependency_complexity_high` | MEDIUM | Services with 5+ dependencies |
| `missing_saturation_metrics` | MEDIUM | Tier-1 services lacking circuit breaker or rate limiting coverage |

## Sample Data

The bundled dataset models a trading/fintech microservices environment with 13 services across 3 tiers, 20 dependency edges, and 8+ historical incidents. All names, incidents, and figures are synthetic.

## Development

```bash
python manage.py init-db     # rebuild database from mock data
python manage.py run --debug  # start dev server with auto-reload
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## License

MIT License. See [LICENSE](LICENSE).

---

**Built by Kris R. at [UpliftPal](https://upliftpal.com)**
