"""
ReliOps - Flask application.
Routes, caching, dashboard builders, and API endpoints.

Author: Kris R. (UpliftPal)
"""

import json
import os
import hashlib
import logging
import logging.config
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from app.config import BASE_DIR, INSTANCE_DIR, CACHE_DIR, MOCK_DATA_DIR, DB_PATH, CACHE_TTL, PORT
from app.models import (
    init_db, seed_from_mock_data,
    query_services, query_dependencies, query_incidents,
    query_risk_findings, query_reliability_debt, query_latest_snapshot,
    insert_risk_finding, insert_snapshot
)
from app.rules_engine import (
    run_scan, calculate_risk_score, detect_drift,
    generate_insights, calculate_blast_radius
)
# Enterprise modules (proprietary; gracefully degrade when absent)
try:
    from app.enterprise.pattern_analyzer import detect_systemic_patterns
    from app.enterprise.runbook_generator import generate_runbook
    ENTERPRISE_AVAILABLE = True
except ImportError:
    detect_systemic_patterns = None
    generate_runbook = None
    ENTERPRISE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Fix-hint mapping (one-liner remediation per rule)
# ---------------------------------------------------------------------------
RULE_FIX_HINTS = {
    'missing_cross_az_failover': 'Deploy to second AZ with automatic failover',
    'no_slo_defined': 'Define explicit SLO targets with monitoring',
    'missing_circuit_breaker': 'Add circuit breaker for fault isolation',
    'retry_storm_risk': 'Cap retries at 3 with exponential backoff + jitter',
    'single_point_of_failure': 'Add redundancy or active-passive failover',
    'slo_breach_trending': 'Investigate degradation; consider capacity increase',
    'dependency_complexity_high': 'Reduce coupling; add circuit breakers at boundaries',
    'missing_saturation_metrics': 'Add CPU/memory/queue-depth monitoring and alerts',
}


app = Flask(__name__)
logger = logging.getLogger("reliops")


def _configure_logging(app):
    flag = os.getenv("APP_LOG_LEVEL", "").strip().lower()
    level_map = {
        "debug": "DEBUG",
        "info": "INFO",
        "warning": "WARNING",
        "error": "ERROR",
        "critical": "CRITICAL",
        "true": "INFO",
        "1": "INFO",
        "yes": "INFO",
        "on": "INFO",
        "warn": "WARNING",
    }
    log_level = level_map.get(flag)
    if not log_level:
        logging.getLogger("reliops").handlers.clear()
        logging.getLogger("reliops.ai").handlers.clear()
        logging.getLogger("reliops.runbook").handlers.clear()
        return

    project_root = Path(app.root_path).parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / "app.log"

    logging.config.dictConfig(
        {
            "version": 1,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                }
            },
            "handlers": {
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": str(log_file),
                    "mode": "a",
                    "encoding": "utf-8",
                    "formatter": "default",
                    "level": log_level,
                    "maxBytes": 5 * 1024 * 1024,
                    "backupCount": 3,
                }
            },
            "loggers": {
                "reliops": {"handlers": ["file"], "level": log_level, "propagate": False},
                "reliops.ai": {"handlers": ["file"], "level": log_level, "propagate": False},
                "reliops.runbook": {"handlers": ["file"], "level": log_level, "propagate": False},
            },
        }
    )
    logging.getLogger("reliops").info("ReliOps logging enabled (level=%s). Writing to %s", log_level, log_file)


_configure_logging(app)


@app.context_processor
def inject_globals():
    """Variables available in every Jinja template."""
    return {"asset_v": config.ASSET_VERSION}


@app.after_request
def add_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    if response.content_type and 'text/html' in response.content_type:
        if app.debug:
            # Dev: always fetch fresh templates
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        else:
            # Prod: short cache for HTML, revalidate periodically
            response.headers['Cache-Control'] = 'public, max-age=300, must-revalidate'
    elif request.path.startswith('/static/') and not app.debug:
        # Prod: long cache for static assets (busted by ?v=ASSET_VERSION)
        timeout = config.STATIC_CACHE_TIMEOUT
        response.headers['Cache-Control'] = f'public, max-age={timeout}, immutable'
    return response


# ---------------------------------------------------------------------------
# Caching helpers
# ---------------------------------------------------------------------------

def get_cache_path(key):
    hash_key = hashlib.md5(key.encode()).hexdigest()
    return os.path.join(str(CACHE_DIR), f'{hash_key}.json')


def get_cached(key):
    cache_path = get_cache_path(key)
    if os.path.exists(cache_path):
        try:
            stat = os.stat(cache_path)
            age = datetime.utcnow().timestamp() - stat.st_mtime
            if age < CACHE_TTL:
                with open(cache_path, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            pass
    return None


def set_cache(key, value):
    cache_path = get_cache_path(key)
    try:
        with open(cache_path, 'w') as f:
            json.dump(value, f)
    except IOError:
        pass


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def serialize_incident(incident):
    return {
        'id': incident.get('id'),
        'title': incident.get('title'),
        'service': incident.get('service'),
        'root_cause': incident.get('root_cause'),
        'condition_signature': incident.get('condition_signature'),
        'severity': incident.get('severity'),
        'remediation': incident.get('remediation'),
        'impact_estimate_usd': incident.get('impact_estimate_usd'),
        'created_at': incident.get('created_at'),
    }


def serialize_debt(debt):
    return {
        'id': debt.get('id'),
        'service': debt.get('service'),
        'debt_type': debt.get('debt_type'),
        'severity': debt.get('severity'),
        'description': debt.get('description'),
        'estimated_effort': debt.get('estimated_effort'),
        'created_at': debt.get('created_at'),
        'resolved_at': debt.get('resolved_at'),
    }


# ---------------------------------------------------------------------------
# Dashboard builders
# ---------------------------------------------------------------------------

def build_dependency_graph_d3(services, dependencies, violations=None):
    nodes = []
    node_ids = {}

    # Build per-service risk level from violations
    service_risk = {}
    if violations:
        for v in violations:
            svc = v.service if hasattr(v, 'service') else v.get('service', '')
            sev = v.severity if hasattr(v, 'severity') else v.get('severity', '')
            current = service_risk.get(svc, 'none')
            rank = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'none': 0}
            if rank.get(sev, 0) > rank.get(current, 0):
                service_risk[svc] = sev

    for i, service in enumerate(services):
        node_ids[service['name']] = i
        tier_num = int(service.get('tier', '0').replace('tier-', '')) if service.get('tier') else 0
        risk_level = service_risk.get(service['name'], 'none').lower()
        nodes.append({
            'id': service['name'],
            'name': service['name'],
            'tier': tier_num,
            'tier_label': f"Tier {tier_num}",
            'owner': service.get('owner'),
            'slo_target': service.get('slo_target'),
            'slo_current': service.get('slo_current'),
            'risk': risk_level,
            'index': i,
        })

    links = []
    for dep in dependencies:
        if dep['source_service'] in node_ids and dep['target_service'] in node_ids:
            links.append({
                'source': dep['source_service'],
                'target': dep['target_service'],
                'type': dep.get('dep_type', 'sync'),
                'critical': bool(dep.get('is_critical', 0)),
            })

    return {'nodes': nodes, 'links': links}


def get_risk_color(label):
    return {
        'CRITICAL': '#d32f2f',
        'HIGH': '#f57c00',
        'MEDIUM': '#f5a623',
        'LOW': '#388e3c',
    }.get(label, '#757575')


def build_dashboard_json():
    db_path = str(DB_PATH)
    cached = get_cached('dashboard')
    if cached:
        return cached

    services = query_services(db_path)
    dependencies = query_dependencies(db_path)
    debt_items = query_reliability_debt(db_path)

    violations = run_scan(db_path)
    risk_result = calculate_risk_score(db_path, violations)
    drift_signals = detect_drift(db_path)
    insights = generate_insights(db_path, violations, risk_result)

    # Track which insight source was used (set as side-effect in generate_insights)
    from app.rules_engine import _last_insights_source
    insights_source = _last_insights_source

    tier1_services = [s for s in services if 'tier-1' in str(s.get('tier', ''))]
    at_risk_services = list({v.service for v in violations if v.severity in ['CRITICAL', 'HIGH']})

    debt_by_severity = {
        'critical': len([d for d in debt_items if d.get('severity') == 'CRITICAL']),
        'high': len([d for d in debt_items if d.get('severity') == 'HIGH']),
        'medium': len([d for d in debt_items if d.get('severity') == 'MEDIUM']),
    }
    total_effort = sum(
        {'s': 1, 'm': 3, 'l': 5, 'xl': 8}.get(d.get('estimated_effort', 'm'), 3)
        for d in debt_items
    )

    critical_issues = [
        {
            'service': v.service,
            'rule': v.rule_name,
            'severity': v.severity,
            'description': v.description,
            'blast_radius': v.blast_radius,
            'fix_hint': RULE_FIX_HINTS.get(v.rule_name, 'Review architecture'),
        }
        for v in violations if v.severity in ['CRITICAL', 'HIGH']
    ][:10]

    recurrence_alerts = [
        {
            'service': v.service,
            'rule': v.rule_name,
            'recurrence_score': v.recurrence_score,
            'description': f"{v.service}: {v.rule_name} has {v.recurrence_score:.0f}% recurrence likelihood",
        }
        for v in violations if v.recurrence_score > 30
    ][:5]

    hotspots = sorted(
        [{'service': v.service, 'blast_radius': v.blast_radius, 'affected_count': v.blast_radius}
         for v in violations if v.blast_radius > 2],
        key=lambda x: x['blast_radius'],
        reverse=True
    )[:5]

    dashboard = {
        'overall_risk_score': risk_result['score'],
        'risk_label': risk_result['label'],
        'risk_color': get_risk_color(risk_result['label']),
        'material_exposures': len(critical_issues),
        'critical_issues': critical_issues,
        'risk_findings': [v.to_dict() for v in violations[:20]],
        'recurrence_alerts': recurrence_alerts,
        'drift_signals': drift_signals[:5],
        'ai_insights': insights[:5],
        'insights_source': insights_source,
        'reliability_debt': {
            'critical': debt_by_severity['critical'],
            'high': debt_by_severity['high'],
            'medium': debt_by_severity['medium'],
            'total_effort_days': total_effort,
        },
        'blast_radius_hotspots': hotspots,
        'services_summary': {
            'total': len(services),
            'tier1': len(tier1_services),
            'at_risk': len(at_risk_services),
        },
        'incident_patterns': detect_systemic_patterns(db_path) if detect_systemic_patterns else [],
    }

    set_cache('dashboard', dashboard)
    return dashboard


def build_audit_dashboard(services_config):
    db_path = str(DB_PATH)
    services = []
    dependencies = []

    for svc in services_config:
        services.append({
            'name': svc.get('name'),
            'tier': f"tier-{svc.get('tier', 1)}" if isinstance(svc.get('tier'), int) else svc.get('tier'),
            'owner': svc.get('owner'),
            'team': svc.get('team'),
            'slo_target': svc.get('slo_target', 99.9),
            'slo_current': svc.get('slo_current', 99.9),
            'az_count': svc.get('az_count', 1),
            'has_failover': svc.get('has_failover', False),
            'has_circuit_breaker': svc.get('has_circuit_breaker', False),
            'has_rate_limiting': svc.get('has_rate_limiting', False),
        })
        for target in svc.get('dependencies', []):
            dependencies.append({
                'source_service': svc.get('name'),
                'target_service': target.get('name'),
                'dep_type': target.get('type', 'sync'),
                'is_critical': target.get('critical', False),
            })

    from app.rules_engine import RulesEngine
    engine = RulesEngine(services, dependencies, [])
    violations = engine.scan_all_rules()
    risk_result = engine.calculate_operational_reliability_risk_score(violations)

    tier1_services = [s for s in services if 'tier-1' in str(s.get('tier', ''))]
    at_risk_services = list({v.service for v in violations if v.severity in ['CRITICAL', 'HIGH']})

    critical_issues = [
        {
            'service': v.service,
            'rule': v.rule_name,
            'severity': v.severity,
            'description': v.description,
            'blast_radius': v.blast_radius,
            'fix_hint': RULE_FIX_HINTS.get(v.rule_name, 'Review architecture'),
        }
        for v in violations if v.severity in ['CRITICAL', 'HIGH']
    ][:10]

    hotspots = sorted(
        [{'service': v.service, 'blast_radius': v.blast_radius, 'affected_count': v.blast_radius}
         for v in violations if v.blast_radius > 2],
        key=lambda x: x['blast_radius'],
        reverse=True
    )[:5]

    return {
        'overall_risk_score': risk_result['score'],
        'risk_label': risk_result['label'],
        'risk_color': get_risk_color(risk_result['label']),
        'material_exposures': len(critical_issues),
        'critical_issues': critical_issues,
        'risk_findings': [v.to_dict() for v in violations[:20]],
        'recurrence_alerts': [],
        'drift_signals': [],
        'ai_insights': generate_insights(db_path, violations, risk_result)[:5],
        'reliability_debt': {'critical': 0, 'high': 0, 'medium': 0, 'total_effort_days': 0},
        'blast_radius_hotspots': hotspots,
        'services_summary': {
            'total': len(services),
            'tier1': len(tier1_services),
            'at_risk': len(at_risk_services),
        },
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/audit')
def audit():
    return render_template('audit.html')


@app.route('/help')
def help_page():
    return render_template('help.html')


@app.route('/enterprise')
def enterprise_page():
    return render_template('enterprise.html')


@app.route('/api/dashboard')
def api_dashboard():
    data = build_dashboard_json()
    # If a browser is viewing this directly, wrap JSON in a navigable HTML page
    accept = request.headers.get('Accept', '')
    if 'text/html' in accept and 'application/json' not in accept:
        pretty = json.dumps(data, indent=2)
        return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ReliOps API | /api/dashboard</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0a0f;color:#c8ccd4;font-family:'Courier New',monospace;font-size:13px}}
.bar{{display:flex;justify-content:space-between;align-items:center;padding:12px 24px;
background:rgba(18,19,26,0.95);border-bottom:1px solid #1e2028;position:sticky;top:0;z-index:10}}
.bar a{{color:#f5a623;text-decoration:none;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
font-size:14px;font-weight:600}}
.bar a:hover{{text-decoration:underline}}
.bar .title{{color:#8a8f98;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:13px}}
.bar .endpoint{{color:#f5a623;font-family:'Courier New',monospace;margin-left:8px}}
pre{{padding:24px;white-space:pre-wrap;word-break:break-word;line-height:1.6}}
</style></head><body>
<div class="bar">
<div><span class="title">API Response</span><span class="endpoint">/api/dashboard</span></div>
<div style="display:flex;gap:16px"><a href="/">← Dashboard</a><a href="/audit">Audit</a></div>
</div>
<pre>{pretty}</pre>
</body></html>''', 200, {{'Content-Type': 'text/html'}}
    return jsonify(data)


@app.route('/api/risks')
def api_risks():
    violations = run_scan(str(DB_PATH))
    return jsonify({'risks': [v.to_dict() for v in violations]})


@app.route('/api/dependencies')
def api_dependencies():
    services = query_services(str(DB_PATH))
    deps = query_dependencies(str(DB_PATH))
    violations = run_scan(str(DB_PATH))
    graph = build_dependency_graph_d3(services, deps, violations)
    logger.info(
        "Dependency graph requested: nodes=%s links=%s violations=%s",
        len(graph.get('nodes', [])),
        len(graph.get('links', [])),
        len(violations),
    )
    return jsonify(graph)


@app.route('/api/drift')
def api_drift():
    return jsonify({'drift_signals': detect_drift(str(DB_PATH))})


@app.route('/api/incidents')
def api_incidents():
    incidents = query_incidents(str(DB_PATH))
    return jsonify({'incidents': [serialize_incident(i) for i in incidents]})


@app.route('/api/reliability-debt')
def api_reliability_debt():
    debt_items = query_reliability_debt(str(DB_PATH))
    return jsonify({'debt': [serialize_debt(d) for d in debt_items]})


@app.route('/api/blast-radius/<service_name>')
def api_blast_radius(service_name):
    return jsonify(calculate_blast_radius(str(DB_PATH), service_name))


@app.route('/api/runbook/<service_name>', methods=['POST', 'OPTIONS'])
def api_runbook(service_name):
    """Generate an on-demand incident response runbook for a service."""
    if request.method == 'OPTIONS':
        return '', 200

    # Check cache first (5-minute TTL, same as dashboard)
    cache_key = f'runbook:{service_name}'
    cached = get_cached(cache_key)
    if cached:
        return jsonify(cached)

    if not generate_runbook:
        return jsonify({'error': 'Runbook generation requires ReliOps Enterprise'}), 403

    try:
        result = generate_runbook(str(DB_PATH), service_name)
        if result is None:
            return jsonify({'error': f'Service "{service_name}" not found'}), 404

        set_cache(cache_key, result)
        return jsonify(result)
    except Exception as e:
        import logging
        logging.getLogger('reliops.runbook').warning("Runbook generation failed: %s", e)
        return jsonify({'error': 'Failed to generate runbook'}), 500


@app.route('/api/audit', methods=['POST', 'OPTIONS'])
def api_audit():
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    return jsonify(build_audit_dashboard(data.get('services', [])))


# ---------------------------------------------------------------------------
# Dev server runner (not used by gunicorn)
# ---------------------------------------------------------------------------

def run_server(host='localhost', port=None, ssl_cert=None, ssl_key=None, debug=False):
    """Start the Flask dev server. In production, use gunicorn instead."""
    port = port or PORT
    db_path = str(DB_PATH)

    if not os.path.exists(db_path):
        init_db(db_path)
        seed_from_mock_data(db_path, str(MOCK_DATA_DIR))

    ssl_context = (ssl_cert, ssl_key) if ssl_cert and ssl_key else None
    protocol = 'https' if ssl_context else 'http'

    print(f"\n  ReliOps running at {protocol}://{host}:{port}")
    print(f"  Dashboard : {protocol}://{host}:{port}/")
    print(f"  Audit     : {protocol}://{host}:{port}/audit")
    print(f"  DB        : {db_path}")
    if ssl_context:
        print(f"  SSL cert  : {ssl_cert}")
    print(f"\n  Press Ctrl+C to stop\n")

    app.run(host=host, port=port, debug=debug, ssl_context=ssl_context)
