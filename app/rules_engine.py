"""
ReliOps - Rules Engine.
8-rule reliability scanner, risk scoring, blast radius calculation,
and deterministic insight generation.

Author: Kris R. (UpliftPal)
"""

from datetime import datetime, timedelta
from collections import defaultdict
import json
from app.models import (
    query_services, query_dependencies, query_incidents,
    insert_risk_finding, query_risk_findings, query_latest_snapshot
)


class RuleViolation:
    """Represents a detected reliability risk."""

    def __init__(self, rule_name, service, severity, description, blast_radius=0,
                 recurrence_score=0.0, condition_signature=None):
        self.rule_name = rule_name
        self.service = service
        self.severity = severity
        self.description = description
        self.blast_radius = blast_radius
        self.recurrence_score = recurrence_score
        self.condition_signature = condition_signature or rule_name
        self.detected_at = datetime.utcnow()

    def to_dict(self):
        return {
            'rule_name': self.rule_name,
            'service': self.service,
            'severity': self.severity,
            'description': self.description,
            'blast_radius': self.blast_radius,
            'recurrence_score': self.recurrence_score,
            'condition_signature': self.condition_signature,
            'detected_at': self.detected_at.isoformat(),
        }


class RulesEngine:
    """
    Core reliability risk detection engine.
    Evaluates services against production best practices and generates findings.
    """

    # Severity levels
    CRITICAL = 'CRITICAL'
    HIGH = 'HIGH'
    MEDIUM = 'MEDIUM'
    LOW = 'LOW'

    def __init__(self, services, dependencies, incidents):
        """
        Initialize rules engine with service and dependency catalog.

        Args:
            services: List of service dicts
            dependencies: List of dependency dicts
            incidents: List of incident dicts
        """
        self.services = {s['name']: s for s in services}
        self.dependencies = dependencies
        self.incidents = incidents

        # Build dependency graph for efficient traversal
        self._build_dependency_graph()

    def _build_dependency_graph(self):
        """Build adjacency lists for forward and reverse dependency traversal."""
        self.forward_deps = defaultdict(list)  # service -> [deps]
        self.reverse_deps = defaultdict(list)  # service -> [dependents]

        for dep in self.dependencies:
            source = dep['source_service']
            target = dep['target_service']
            is_critical = dep.get('is_critical', False)

            self.forward_deps[source].append({
                'target': target,
                'is_critical': is_critical
            })
            self.reverse_deps[target].append({
                'source': source,
                'is_critical': is_critical
            })

    def _calculate_blast_radius(self, service_name):
        """
        Calculate number of services affected if this service goes down.
        Uses BFS on reverse_deps (who depends on this service).
        """
        visited = set()
        queue = [service_name]
        visited.add(service_name)

        while queue:
            current = queue.pop(0)
            # Find services that DEPEND ON the current service
            for dep in self.reverse_deps.get(current, []):
                if dep['source'] not in visited:
                    visited.add(dep['source'])
                    queue.append(dep['source'])

        return len(visited) - 1  # Exclude the service itself

    def _calculate_recurrence_score(self, service_name, condition_signature):
        """
        Calculate likelihood of issue recurrence based on incident history.
        Returns 0-100 score, higher = more likely to recur.
        """
        matching_incidents = [
            i for i in self.incidents
            if (i['service'] == service_name and
                i['condition_signature'] == condition_signature)
        ]

        if not matching_incidents:
            return 0.0

        # Score based on frequency and recency
        recent_threshold = datetime.utcnow() - timedelta(days=90)
        recent_incidents = []

        for inc in matching_incidents:
            try:
                created_at = datetime.fromisoformat(inc['created_at'].replace('Z', '+00:00'))
                if created_at > recent_threshold:
                    recent_incidents.append(inc)
            except (ValueError, TypeError):
                pass

        base_score = min(len(matching_incidents) * 15, 100)

        # Boost score if recent incidents
        if recent_incidents:
            base_score = min(base_score + (len(recent_incidents) * 20), 100)

        # Boost score if last incident is very recent
        if matching_incidents:
            try:
                last_incident = max(
                    matching_incidents,
                    key=lambda x: datetime.fromisoformat(x['created_at'].replace('Z', '+00:00'))
                )
                last_created = datetime.fromisoformat(
                    last_incident['created_at'].replace('Z', '+00:00')
                )
                days_since = (datetime.utcnow() - last_created).days
                if days_since < 30:
                    base_score = min(base_score + 30, 100)
            except (ValueError, TypeError):
                pass

        return base_score

    def _get_incident_impact(self, service_name):
        """Get average impact estimate from past incidents."""
        incidents = [i for i in self.incidents if i['service'] == service_name]
        if not incidents:
            return 0.0

        total_impact = sum(i.get('impact_estimate_usd', 0.0) for i in incidents)
        return total_impact / len(incidents)

    def _get_service(self, name):
        """Get service dict by name."""
        return self.services.get(name)

    def rule_missing_cross_az_failover(self):
        """
        RULE: missing_cross_az_failover
        Critical services without cross-AZ redundancy face total outage risk.
        """
        violations = []

        for name, service in self.services.items():
            az_count = service.get('az_count', 1)
            has_failover = service.get('has_failover', False)
            tier = service.get('tier', '')

            # Tier-1 services in single AZ without failover
            if 'tier-1' in str(tier) and az_count < 2 and not has_failover:
                blast_radius = self._calculate_blast_radius(name)
                recurrence_score = self._calculate_recurrence_score(
                    name, 'single_az_failure'
                )

                violations.append(RuleViolation(
                    rule_name='missing_cross_az_failover',
                    service=name,
                    severity=self.CRITICAL,
                    description=f'{name} is deployed in single AZ with no failover. '
                               f'Blast radius: {blast_radius} downstream systems.',
                    blast_radius=blast_radius,
                    recurrence_score=recurrence_score,
                    condition_signature='single_az_failure'
                ))

        return violations

    def rule_no_slo_defined(self):
        """
        RULE: no_slo_defined
        Critical services must have explicit SLO targets.
        """
        violations = []

        for name, service in self.services.items():
            tier = service.get('tier', '')
            slo_target = service.get('slo_target')

            if 'tier-1' in str(tier) and (slo_target is None or slo_target == 0):
                violations.append(RuleViolation(
                    rule_name='no_slo_defined',
                    service=name,
                    severity=self.HIGH,
                    description=f'{name} (tier-1) lacks explicit SLO target. '
                               f'Cannot measure reliability or set proper alerting.',
                    blast_radius=1,
                    recurrence_score=0.0,
                    condition_signature='missing_slo'
                ))

        return violations

    def rule_missing_circuit_breaker(self):
        """
        RULE: missing_circuit_breaker
        Services with high fan-out (3+ dependencies) need circuit breakers.
        """
        violations = []

        for name, service in self.services.items():
            deps = self.forward_deps.get(name, [])
            has_circuit_breaker = service.get('has_circuit_breaker', False)

            if len(deps) >= 3 and not has_circuit_breaker:
                blast_radius = self._calculate_blast_radius(name)
                violations.append(RuleViolation(
                    rule_name='missing_circuit_breaker',
                    service=name,
                    severity=self.HIGH,
                    description=f'{name} has {len(deps)} downstream dependencies but no circuit breaker. '
                               f'Risk of cascading failures.',
                    blast_radius=blast_radius,
                    recurrence_score=self._calculate_recurrence_score(name, 'cascading_timeout'),
                    condition_signature='cascading_timeout'
                ))

        return violations

    def rule_retry_storm_risk(self):
        """
        RULE: retry_storm_risk
        Services with high fan-out and no rate limiting risk retry storms.
        """
        violations = []

        for name, service in self.services.items():
            deps = self.forward_deps.get(name, [])
            has_rate_limiting = service.get('has_rate_limiting', False)

            if len(deps) >= 3 and not has_rate_limiting:
                blast_radius = self._calculate_blast_radius(name)
                violations.append(RuleViolation(
                    rule_name='retry_storm_risk',
                    service=name,
                    severity=self.MEDIUM,
                    description=f'{name} calls {len(deps)} services without rate limiting. '
                               f'Retry storms could cascade across {blast_radius} downstream systems.',
                    blast_radius=blast_radius,
                    recurrence_score=self._calculate_recurrence_score(name, 'retry_storm'),
                    condition_signature='retry_storm'
                ))

        return violations

    def rule_single_point_of_failure(self):
        """
        RULE: single_point_of_failure
        Services that 3+ critical services depend on must have redundancy.
        """
        violations = []

        for name, service in self.services.items():
            reverse = self.reverse_deps.get(name, [])
            critical_dependents = [d for d in reverse if d['is_critical']]

            az_count = service.get('az_count', 1)
            has_failover = service.get('has_failover', False)

            if len(critical_dependents) >= 3 and (az_count < 2 or not has_failover):
                violations.append(RuleViolation(
                    rule_name='single_point_of_failure',
                    service=name,
                    severity=self.CRITICAL,
                    description=f'{name} is a critical dependency for {len(critical_dependents)} services '
                               f'but lacks redundancy (AZ count: {az_count}, failover: {has_failover}). '
                               f'High-impact outage risk.',
                    blast_radius=len(critical_dependents),
                    recurrence_score=self._calculate_recurrence_score(name, 'single_point_of_failure'),
                    condition_signature='single_point_of_failure'
                ))

        return violations

    def rule_slo_breach_trending(self):
        """
        RULE: slo_breach_trending
        Alert when actual SLO is tracking below target.
        """
        violations = []

        for name, service in self.services.items():
            slo_target = service.get('slo_target')
            slo_current = service.get('slo_current')

            if slo_target and slo_current and slo_current < slo_target:
                gap = slo_target - slo_current
                severity = self.CRITICAL if gap > 0.5 else self.HIGH if gap > 0.1 else self.MEDIUM

                violations.append(RuleViolation(
                    rule_name='slo_breach_trending',
                    service=name,
                    severity=severity,
                    description=f'{name} SLO trending below target. '
                               f'Target: {slo_target}%, Current: {slo_current}%. Gap: {gap:.2f}%',
                    blast_radius=self._calculate_blast_radius(name),
                    recurrence_score=0.0,
                    condition_signature='slo_breach'
                ))

        return violations

    def rule_dependency_complexity_high(self):
        """
        RULE: dependency_complexity_high
        Services with 5+ dependencies are high complexity, harder to maintain.
        """
        violations = []

        for name, service in self.services.items():
            deps = self.forward_deps.get(name, [])

            if len(deps) >= 5:
                violations.append(RuleViolation(
                    rule_name='dependency_complexity_high',
                    service=name,
                    severity=self.MEDIUM,
                    description=f'{name} has {len(deps)} dependencies. '
                               f'High complexity increases operational risk.',
                    blast_radius=self._calculate_blast_radius(name),
                    recurrence_score=0.0,
                    condition_signature='high_complexity'
                ))

        return violations

    def rule_missing_saturation_metrics(self):
        """
        RULE: missing_saturation_metrics
        Tier-1 services need comprehensive saturation monitoring.
        """
        violations = []

        for name, service in self.services.items():
            tier = service.get('tier', '')

            if 'tier-1' in str(tier):
                # Simplified check: if no circuit breaker or rate limiting, assume missing metrics
                has_circuit_breaker = service.get('has_circuit_breaker', False)
                has_rate_limiting = service.get('has_rate_limiting', False)

                if not has_circuit_breaker or not has_rate_limiting:
                    violations.append(RuleViolation(
                        rule_name='missing_saturation_metrics',
                        service=name,
                        severity=self.MEDIUM,
                        description=f'{name} (tier-1) may lack comprehensive saturation metrics. '
                                   f'Circuit breaker: {has_circuit_breaker}, Rate limiting: {has_rate_limiting}',
                        blast_radius=self._calculate_blast_radius(name),
                        recurrence_score=0.0,
                        condition_signature='missing_metrics'
                    ))

        return violations

    def scan_all_rules(self):
        """
        Execute all rules and return comprehensive violation list.

        Returns:
            List of RuleViolation objects
        """
        all_violations = []

        all_violations.extend(self.rule_missing_cross_az_failover())
        all_violations.extend(self.rule_no_slo_defined())
        all_violations.extend(self.rule_missing_circuit_breaker())
        all_violations.extend(self.rule_retry_storm_risk())
        all_violations.extend(self.rule_single_point_of_failure())
        all_violations.extend(self.rule_slo_breach_trending())
        all_violations.extend(self.rule_dependency_complexity_high())
        all_violations.extend(self.rule_missing_saturation_metrics())

        return all_violations

    def calculate_operational_reliability_risk_score(self, violations=None):
        """
        Calculate overall Operational Reliability Risk score (0-100).
        Higher score = more risk.

        Returns:
            dict with score (0-100), label, and breakdown
        """
        if violations is None:
            violations = self.scan_all_rules()

        score = 0.0

        # Count violations by severity
        critical_count = len([v for v in violations if v.severity == self.CRITICAL])
        high_count = len([v for v in violations if v.severity == self.HIGH])
        medium_count = len([v for v in violations if v.severity == self.MEDIUM])
        low_count = len([v for v in violations if v.severity == self.LOW])

        # Base score from violation counts (tuned for 10-15 service environments)
        total_services = max(len(self.services), 1)
        score += critical_count * 15
        score += high_count * 8
        score += medium_count * 3
        score += low_count * 1

        # Add weighted recurrence scores
        for violation in violations:
            weight = 0.08 if violation.severity == self.CRITICAL else \
                     0.05 if violation.severity == self.HIGH else \
                     0.02 if violation.severity == self.MEDIUM else 0.01
            score += violation.recurrence_score * weight

        # Add SLO breach penalties (SLO gaps are small decimals)
        for service in self.services.values():
            slo_target = service.get('slo_target')
            slo_current = service.get('slo_current')
            tier = service.get('tier', '')

            if slo_target and slo_current and slo_current < slo_target:
                gap = slo_target - slo_current
                if 'tier-1' in str(tier):
                    score += gap * 3  # Moderate penalty for tier-1
                else:
                    score += gap * 1

        # Cap at 100
        score = min(score, 100)

        # Determine risk label
        if score >= 80:
            label = 'CRITICAL'
        elif score >= 60:
            label = 'HIGH'
        elif score >= 40:
            label = 'MEDIUM'
        else:
            label = 'LOW'

        return {
            'score': round(score, 1),
            'label': label,
            'violation_counts': {
                'critical': critical_count,
                'high': high_count,
                'medium': medium_count,
                'low': low_count,
            }
        }

    def detect_drift_signals(self, prev_snapshot, curr_snapshot):
        """
        Compare two snapshots and identify drift signals.
        Detects increases in risk, changes in architecture, SLO degradation.

        Args:
            prev_snapshot: Previous snapshot state (dict)
            curr_snapshot: Current snapshot state (dict)

        Returns:
            List of drift signal dicts
        """
        signals = []

        prev_services = prev_snapshot.get('services', {})
        curr_services = curr_snapshot.get('services', {})

        # Detect SLO degradation
        for service_name in curr_services:
            if service_name not in prev_services:
                continue

            prev_slo = prev_services[service_name].get('slo_current', 100)
            curr_slo = curr_services[service_name].get('slo_current', 100)

            degradation = prev_slo - curr_slo
            if degradation > 0.1:  # More than 0.1% degradation
                signals.append({
                    'type': 'slo_degradation',
                    'service': service_name,
                    'prev_value': prev_slo,
                    'curr_value': curr_slo,
                    'change': round(degradation, 3),
                    'severity': 'HIGH' if degradation > 0.5 else 'MEDIUM',
                })

        # Detect dependency changes
        prev_dep_count = len(prev_snapshot.get('dependencies', []))
        curr_dep_count = len(curr_snapshot.get('dependencies', []))

        if curr_dep_count > prev_dep_count:
            new_deps = curr_dep_count - prev_dep_count
            signals.append({
                'type': 'dependency_increase',
                'new_dependencies': new_deps,
                'prev_count': prev_dep_count,
                'curr_count': curr_dep_count,
                'severity': 'MEDIUM' if new_deps > 2 else 'LOW',
            })

        # Detect architecture changes
        prev_tiers = set(s.get('tier') for s in prev_services.values())
        curr_tiers = set(s.get('tier') for s in curr_services.values())

        if prev_tiers != curr_tiers:
            signals.append({
                'type': 'tier_changes',
                'change': 'Service tier configuration changed',
                'severity': 'MEDIUM',
            })

        return signals


def run_scan(db_path):
    """Run the full rules engine scan and return findings."""
    services = query_services(db_path)
    dependencies = query_dependencies(db_path)
    incidents = query_incidents(db_path)

    engine = RulesEngine(services, dependencies, incidents)
    violations = engine.scan_all_rules()

    return violations


def calculate_risk_score(db_path, violations=None):
    """Calculate overall risk score."""
    if violations is None:
        violations = run_scan(db_path)

    services = query_services(db_path)
    dependencies = query_dependencies(db_path)
    incidents = query_incidents(db_path)

    engine = RulesEngine(services, dependencies, incidents)
    return engine.calculate_operational_reliability_risk_score(violations)


def detect_drift(db_path):
    """Detect drift signals by comparing snapshots."""
    snapshot = query_latest_snapshot(db_path)

    if not snapshot:
        return []

    curr_snapshot = {
        'services': {s['name']: s for s in query_services(db_path)},
        'dependencies': query_dependencies(db_path),
    }

    services = query_services(db_path)
    dependencies = query_dependencies(db_path)
    incidents = query_incidents(db_path)

    engine = RulesEngine(services, dependencies, incidents)
    return engine.detect_drift_signals(snapshot['data'], curr_snapshot)


# ---------------------------------------------------------------------------
# Insight generation: hybrid AI + deterministic
# ---------------------------------------------------------------------------

# Module-level flag set by generate_insights() to track which path was used.
def generate_insights(db_path, violations, risk_score):
    """Generate natural language insights from violations and score.

    Args:
        db_path: str, path to SQLite database
        violations: list[RuleViolation]
        risk_score: dict with 'score', 'label', 'violation_counts'

    Returns:
        list[str], up to 5 insight strings
    """
    return _generate_deterministic_insights(db_path, violations, risk_score)


def _generate_deterministic_insights(db_path, violations, risk_score):
    """Original pattern-based insight generation.

    Produces insights that sound like a senior SRE analyst briefing,
    referencing specific services, numbers, and patterns.
    """
    insights = []
    incidents = query_incidents(db_path)

    score = risk_score.get('score', 0)
    label = risk_score.get('label', 'UNKNOWN')

    # --- Insight 1: Blast radius + specific services ---
    critical_violations = [v for v in violations if v.severity == 'CRITICAL']
    high_blast = [v for v in violations if v.blast_radius >= 4]
    if high_blast:
        worst = max(high_blast, key=lambda v: v.blast_radius)
        insights.append(
            f"{worst.service} failure would cascade to {worst.blast_radius} downstream services. "
            f"Combined blast radius across all high-risk services: "
            f"{sum(v.blast_radius for v in high_blast)} systems exposed."
        )

    # --- Insight 2: Recurrence pattern with incident history ---
    recurrence_violations = [v for v in violations if v.recurrence_score > 30]
    if recurrence_violations:
        for v in recurrence_violations[:2]:
            matching = [i for i in incidents
                       if i.get('condition_signature') == v.condition_signature
                       and i.get('service') == v.service]
            if matching:
                last = matching[-1]
                days_ago = 'recently'
                if last.get('date') or last.get('created_at'):
                    from datetime import datetime
                    try:
                        d = last.get('date') or last.get('created_at', '')
                        incident_date = datetime.strptime(str(d)[:10], '%Y-%m-%d')
                        delta = (datetime.now() - incident_date).days
                        days_ago = f"{delta} days ago"
                    except Exception:
                        pass
                insights.append(
                    f"Recurrence risk: {v.rule_name.replace('_', ' ')} pattern detected on "
                    f"{v.service} — last incident was {days_ago}. "
                    f"Recurrence probability: {v.recurrence_score:.0f}%."
                )

    # --- Insight 3: Missing SLOs / SLO breaches ---
    slo_violations = [v for v in violations if 'slo' in v.rule_name.lower()]
    if slo_violations:
        slo_services = list(set(v.service for v in slo_violations))
        tier1_slo = [s for s in slo_services if any(
            v.service == s and 'tier-1' in str(query_services(db_path)[0].get('tier', ''))
            for v in slo_violations
        )]
        insights.append(
            f"{len(slo_violations)} services have SLO issues — "
            f"{len([v for v in slo_violations if 'no_slo' in v.rule_name])} lack defined SLOs entirely, "
            f"{len([v for v in slo_violations if 'breach' in v.rule_name])} are trending below target. "
            f"SLO gaps erode reliability posture silently."
        )

    # --- Insight 4: Architecture weakness ---
    single_az = [v for v in violations if 'cross_az' in v.rule_name or 'single_point' in v.rule_name]
    if single_az:
        services = list(set(v.service for v in single_az))
        insights.append(
            f"{len(services)} Tier-1 service(s) lack cross-AZ failover or are single points of failure: "
            f"{', '.join(services)}. An AZ outage would impact the critical service path."
        )

    # --- Insight 5: Complexity / dependency growth ---
    complexity = [v for v in violations if 'complexity' in v.rule_name or 'retry' in v.rule_name]
    if complexity:
        insights.append(
            f"Dependency complexity increasing: {len(complexity)} services flagged for high fan-out "
            f"or retry storm risk. Recommend circuit breakers and rate limiting on the critical path."
        )

    # If we got fewer than 3, add a summary
    if len(insights) < 3:
        insights.append(
            f"Overall reliability risk: {score}/100 ({label}). "
            f"{len(violations)} issues detected across {len(set(v.service for v in violations))} services."
        )

    return insights[:5]  # Cap at 5 insights


def calculate_blast_radius(db_path, service_name):
    """Calculate the blast radius for a service failure."""
    services = query_services(db_path)
    dependencies = query_dependencies(db_path)
    incidents = query_incidents(db_path)

    engine = RulesEngine(services, dependencies, incidents)
    radius = engine._calculate_blast_radius(service_name)

    # Find all affected services (who depends on this service)
    visited = set()
    queue = [service_name]
    visited.add(service_name)

    while queue:
        current = queue.pop(0)
        for dep in engine.reverse_deps.get(current, []):
            if dep['source'] not in visited:
                visited.add(dep['source'])
                queue.append(dep['source'])

    affected_services = [s for s in visited if s != service_name]

    return {
        'service': service_name,
        'blast_radius': radius,
        'affected_services': affected_services
    }
