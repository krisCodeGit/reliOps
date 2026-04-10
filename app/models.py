"""
ReliOps MVP - Data Models Layer
SQLite3-based models for incident tracking, service registry, dependency mapping,
and reliability risk findings.
Uses only Python standard library (sqlite3).
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path


def init_db(db_path='reliops.db'):
    """
    Initialize SQLite database and create all tables.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Connection object
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            tier TEXT,
            owner TEXT,
            team TEXT,
            slo_target REAL DEFAULT 99.9,
            slo_current REAL DEFAULT 99.9,
            az_count INTEGER DEFAULT 1,
            has_failover BOOLEAN DEFAULT 0,
            has_circuit_breaker BOOLEAN DEFAULT 0,
            has_rate_limiting BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dependencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_service TEXT NOT NULL,
            target_service TEXT NOT NULL,
            dep_type TEXT,
            is_critical BOOLEAN DEFAULT 0,
            FOREIGN KEY (source_service) REFERENCES services(name),
            FOREIGN KEY (target_service) REFERENCES services(name)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            service TEXT NOT NULL,
            root_cause TEXT,
            condition_signature TEXT,
            severity TEXT,
            remediation TEXT,
            impact_estimate_usd REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS risk_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            risk_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT,
            blast_radius INTEGER DEFAULT 0,
            recurrence_score REAL DEFAULT 0.0,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            condition_signature TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reliability_debt (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            debt_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT,
            estimated_effort TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_json TEXT
        )
    ''')

    conn.commit()
    return conn


def seed_from_mock_data(db_path, mock_data_dir='./mock_data'):
    """
    Seed database with mock data from JSON files.

    Args:
        db_path: Path to SQLite database file
        mock_data_dir: Directory containing mock JSON files
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute('DELETE FROM incidents')
    cursor.execute('DELETE FROM risk_findings')
    cursor.execute('DELETE FROM dependencies')
    cursor.execute('DELETE FROM reliability_debt')
    cursor.execute('DELETE FROM services')
    conn.commit()

    # Load mock services
    mock_dir = Path(mock_data_dir)

    if (mock_dir / 'mock_services.json').exists():
        with open(mock_dir / 'mock_services.json', 'r') as f:
            services = json.load(f)

        for svc in services:
            cursor.execute('''
                INSERT INTO services
                (name, tier, owner, team, slo_target, slo_current, az_count,
                 has_failover, has_circuit_breaker, has_rate_limiting)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                svc.get('name'),
                f"tier-{svc.get('tier', 1)}" if isinstance(svc.get('tier'), int) else svc.get('tier'),
                svc.get('owner'),
                svc.get('team'),
                svc.get('slo_target', 99.9) * 100,  # Convert decimal to percentage
                svc.get('slo_current', 99.9) * 100 if svc.get('slo_current') else None,
                svc.get('az_count', 1),
                1 if svc.get('has_failover') else 0,
                1 if svc.get('has_circuit_breaker') else 0,
                1 if svc.get('has_rate_limiting') else 0,
            ))
        conn.commit()

    # Load mock dependencies
    if (mock_dir / 'mock_dependencies.json').exists():
        with open(mock_dir / 'mock_dependencies.json', 'r') as f:
            dependencies = json.load(f)

        for dep in dependencies:
            cursor.execute('''
                INSERT INTO dependencies
                (source_service, target_service, dep_type, is_critical)
                VALUES (?, ?, ?, ?)
            ''', (
                dep.get('source_service'),
                dep.get('target_service'),
                dep.get('dep_type', 'sync'),
                1 if dep.get('is_critical', False) else 0,
            ))
        conn.commit()

    # Load mock incidents
    if (mock_dir / 'mock_incidents.json').exists():
        with open(mock_dir / 'mock_incidents.json', 'r') as f:
            incidents = json.load(f)

        for inc in incidents:
            cursor.execute('''
                INSERT INTO incidents
                (title, service, root_cause, condition_signature, severity,
                 remediation, impact_estimate_usd, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inc.get('title'),
                inc.get('service'),
                inc.get('root_cause'),
                inc.get('condition_signature'),
                inc.get('severity'),
                inc.get('remediation'),
                inc.get('impact_estimate_usd', 0.0),
                inc.get('created_at', datetime.utcnow().isoformat()),
            ))
        conn.commit()

    conn.close()


def get_db(db_path='reliops.db'):
    """
    Get a database connection.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Connection object with row_factory set
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# Query helper functions

def query_services(db_path):
    """Get all services as list of dicts."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM services')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def query_service_by_name(db_path, name):
    """Get a specific service by name."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM services WHERE name = ?', (name,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def query_dependencies(db_path):
    """Get all dependencies as list of dicts."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM dependencies')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def query_incidents(db_path):
    """Get all incidents as list of dicts."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM incidents ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def query_incidents_for_service(db_path, service_name):
    """Get incidents for a specific service."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM incidents WHERE service = ? ORDER BY created_at DESC',
        (service_name,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def query_risk_findings(db_path):
    """Get all risk findings as list of dicts."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM risk_findings ORDER BY detected_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def query_reliability_debt(db_path):
    """Get all reliability debt items as list of dicts."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM reliability_debt WHERE resolved_at IS NULL ORDER BY created_at DESC'
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def insert_risk_finding(db_path, service, risk_type, severity, description,
                       blast_radius=0, recurrence_score=0.0, condition_signature=None):
    """Insert a risk finding into the database."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO risk_findings
        (service, risk_type, severity, description, blast_radius, recurrence_score, condition_signature)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        service, risk_type, severity, description, blast_radius,
        recurrence_score, condition_signature or risk_type
    ))
    conn.commit()
    conn.close()


def insert_snapshot(db_path, data_dict):
    """Insert a snapshot of current state."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO snapshots (data_json)
        VALUES (?)
    ''', (json.dumps(data_dict),))
    conn.commit()
    conn.close()


def query_latest_snapshot(db_path):
    """Get the most recent snapshot."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM snapshots ORDER BY snapshot_time DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()

    if row:
        data = json.loads(row['data_json'])
        return {
            'id': row['id'],
            'snapshot_time': row['snapshot_time'],
            'data': data
        }
    return None


if __name__ == '__main__':
    # Initialize and seed database when run directly
    init_db('reliops.db')
    seed_from_mock_data('reliops.db')
    print("Database initialized and seeded with mock data")
