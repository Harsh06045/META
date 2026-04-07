"""
Agent graders for SQLAudit-Env.
Each grader produces deterministic scores in [0.0, 1.0] with partial credit.
"""
from __future__ import annotations
from typing import List, Dict, Any, Tuple
from app.models import Finding, Severity, Reward
from app.tasks import TASKS


# ─── UTILITY ──────────────────────────────────────────────────────────────────

INJECTION_KEYWORDS = [
    "sql_injection", "injection", "unsanitized", "string concat",
    "concatenat", "unparameterized", "dynamic sql", "exec ", "union attack",
    "union select", "sp_executesql", "user_input", "unsafe"
]
PERF_KEYWORDS = [
    "cartesian", "n+1", "missing index", "select *", "no limit",
    "full table scan", "function on index", "subquery", "nested", "join"
]
PII_KEYWORDS = [
    "pii", "ssn", "email", "password", "personal data", "sensitive",
    "gdpr", "private", "confidential"
]
COMPLIANCE_KEYWORDS = [
    "gdpr", "compliance", "retention", "data protection", "pii exposure",
    "password leakage", "ip address", "audit"
]


def _keyword_match(text: str, keywords: List[str]) -> bool:
    text_lower = (text or "").lower()
    return any(k in text_lower for k in keywords)


def _severity_score(severity: str) -> float:
    return {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.3, "info": 0.1}.get(severity or "info", 0.0)


# ─── GRADER: EASY ─────────────────────────────────────────────────────────────

class EasyGrader:
    """
    Grades the SQL Security Scan task.
    Full score requires: correctly flagging all 3 vulnerable queries,
    not false-flagging the 2 safe ones, and providing meaningful descriptions.
    """
    VULN_INDICES = {0, 2, 4}
    SAFE_INDICES = {1, 3}

    def grade(self, findings: List[Finding], query_statuses: List = None) -> Reward:
        scores: Dict[str, float] = {}

        # 1. True positives: did agent flag the vulnerable queries?
        flagged_vuln = {f.query_index for f in findings if _keyword_match(
            (f.description or "") + (f.finding_type or ""), INJECTION_KEYWORDS
        ) or f.severity in ("critical", "high")}

        tp = len(flagged_vuln & self.VULN_INDICES)
        tp_score = tp / len(self.VULN_INDICES) if self.VULN_INDICES else 1.0
        scores["true_positive_rate"] = tp_score

        # 2. False positives: did agent incorrectly flag safe queries?
        fp = len(flagged_vuln & self.SAFE_INDICES)
        fp_penalty = fp * 0.2
        scores["false_positive_penalty"] = -fp_penalty

        # 3. Severity accuracy: critical issues should be flagged critical
        severity_scores = []
        for f in findings:
            if f.query_index in self.VULN_INDICES:
                if f.severity in ("critical", "high"):
                    severity_scores.append(1.0)
                elif f.severity == "medium":
                    severity_scores.append(0.5)
                else:
                    severity_scores.append(0.1)
        scores["severity_accuracy"] = sum(severity_scores) / len(self.VULN_INDICES) if self.VULN_INDICES else 0.0

        # 4. Description quality: finding descriptions mention injection
        desc_scores = []
        for f in findings:
            if f.query_index in self.VULN_INDICES:
                if _keyword_match(f.description or "", INJECTION_KEYWORDS):
                    desc_scores.append(1.0)
                elif len(f.description or "") > 20:
                    desc_scores.append(0.4)
                else:
                    desc_scores.append(0.0)
        scores["description_quality"] = sum(desc_scores) / len(self.VULN_INDICES) if self.VULN_INDICES and desc_scores else 0.0

        # Weighted total
        total = max(0.0, min(1.0,
            scores["true_positive_rate"] * 0.45
            + scores["severity_accuracy"] * 0.30
            + scores["description_quality"] * 0.25
            - fp_penalty
        ))

        return Reward(
            value=round(total, 4),
            breakdown={k: round(v, 4) for k, v in scores.items()},
            message=f"Detected {tp}/{len(self.VULN_INDICES)} vulnerabilities, {fp} false positives"
        )


# ─── GRADER: MEDIUM ───────────────────────────────────────────────────────────

class MediumGrader:
    """
    Grades the Query Performance Optimizer task.
    Awards points for: identifying issues, rewriting queries, and accuracy
    of the performance reasoning.
    """
    PERF_ISSUES = {0, 1, 2, 3, 5, 6, 7}
    CLEAN = {4}
    CRITICAL_ISSUES = {3}  # cartesian join

    def grade(self, findings: List[Finding], query_statuses: List = None) -> Reward:
        scores: Dict[str, float] = {}
        perf_findings = {f.query_index: f for f in findings if _keyword_match(
            (f.description or "") + (f.finding_type or ""), PERF_KEYWORDS
        ) or f.finding_type in ("performance", "optimization")}

        # 1. Issue detection rate
        detected = set(perf_findings.keys()) & self.PERF_ISSUES
        detection_rate = len(detected) / len(self.PERF_ISSUES) if self.PERF_ISSUES else 1.0
        scores["detection_rate"] = detection_rate

        # 2. Critical issue caught (cartesian join)?
        scores["critical_detected"] = 1.0 if 3 in perf_findings else 0.0

        # 3. Rewrite quality: did agent provide rewritten SQL for flagged issues?
        rewrite_scores = []
        for qi, f in perf_findings.items():
            if qi in self.PERF_ISSUES:
                if f.rewritten_sql and len(f.rewritten_sql) > 10:
                    rewrite_scores.append(1.0)
                elif f.reasoning and len(f.reasoning) > 20:
                    rewrite_scores.append(0.5)
                else:
                    rewrite_scores.append(0.1)
        scores["rewrite_quality"] = sum(rewrite_scores) / len(self.PERF_ISSUES) if self.PERF_ISSUES and rewrite_scores else 0.0

        # 4. False positive penalty (flagging clean query 4)
        fp_penalty = 0.15 if 4 in perf_findings else 0.0
        scores["false_positive_penalty"] = -fp_penalty

        # 5. Severity calibration
        sev_scores = []
        for qi, f in perf_findings.items():
            if qi == 3:  # cartesian — must be critical/high
                sev_scores.append(1.0 if f.severity in ("critical", "high") else 0.3)
            elif qi in self.PERF_ISSUES:
                sev_scores.append(_severity_score(f.severity))
        scores["severity_calibration"] = sum(sev_scores) / len(self.PERF_ISSUES) if self.PERF_ISSUES and sev_scores else 0.0

        total = max(0.0, min(1.0,
            detection_rate * 0.35
            + scores["critical_detected"] * 0.20
            + scores["rewrite_quality"] * 0.25
            + scores["severity_calibration"] * 0.20
            - fp_penalty
        ))

        return Reward(
            value=round(total, 4),
            breakdown={k: round(v, 4) for k, v in scores.items()},
            message=f"Detected {len(detected)}/{len(self.PERF_ISSUES)} perf issues, {len(rewrite_scores)} rewrites"
        )


# ─── GRADER: HARD ─────────────────────────────────────────────────────────────

class HardGrader:
    """
    Grades the Full Audit Pipeline.
    Four sub-scores: security (30%), performance (20%), compliance (30%), report (20%).
    """
    SECURITY_CRITICAL = {0, 4, 10}
    PII_QUERIES = {0, 1, 2, 6, 7}
    PERF_ISSUES = {2, 3, 7, 9, 11}
    COMPLIANCE_QUERIES = {1, 5, 6, 7}
    CLEAN = {8}
    REQUIRED_REPORT_SECTIONS = {"executive_summary", "critical_findings", "compliance_violations", "recommendations"}

    def grade(self, findings: List[Finding], query_statuses: List = None, report_summary: str = "") -> Reward:
        scores: Dict[str, float] = {}

        # ── Sub-score 1: Security (30%) ──
        security_findings = {
            f.query_index: f for f in findings
            if _keyword_match((f.description or "") + (f.finding_type or ""), INJECTION_KEYWORDS)
            or f.finding_type in ("injection", "security")
            or (f.severity == "critical" and f.query_index in self.SECURITY_CRITICAL)
        }
        sec_detected = set(security_findings.keys()) & self.SECURITY_CRITICAL
        sec_rate = len(sec_detected) / len(self.SECURITY_CRITICAL) if self.SECURITY_CRITICAL else 1.0
        scores["security_detection"] = sec_rate

        # ── Sub-score 2: Performance (20%) ──
        perf_findings = {
            f.query_index: f for f in findings
            if _keyword_match((f.description or "") + (f.finding_type or ""), PERF_KEYWORDS)
            or f.finding_type in ("performance", "optimization")
        }
        perf_detected = set(perf_findings.keys()) & self.PERF_ISSUES
        perf_rate = len(perf_detected) / len(self.PERF_ISSUES) if self.PERF_ISSUES else 1.0
        scores["performance_detection"] = perf_rate

        # ── Sub-score 3: Compliance / PII (30%) ──
        compliance_findings = {
            f.query_index: f for f in findings
            if _keyword_match((f.description or "") + (f.finding_type or ""), PII_KEYWORDS + COMPLIANCE_KEYWORDS)
            or f.finding_type in ("compliance", "gdpr", "pii")
        }
        pii_detected = set(compliance_findings.keys()) & self.PII_QUERIES
        comp_rate = len(pii_detected) / len(self.PII_QUERIES) if self.PII_QUERIES else 1.0
        scores["compliance_detection"] = comp_rate

        # Bonus: detected the no-WHERE UPDATE (query 10 — catastrophic)
        if 10 in security_findings or any(
            "update" in (f.description or "").lower() and f.query_index == 10
            for f in findings
        ):
            scores["catastrophic_bonus"] = 0.1
        else:
            scores["catastrophic_bonus"] = 0.0

        # ── Sub-score 4: Report quality (20%) ──
        if report_summary:
            report_lower = report_summary.lower()
            section_hits = sum(1 for s in self.REQUIRED_REPORT_SECTIONS if s.replace("_", " ") in report_lower or s in report_lower)
            report_score = section_hits / len(self.REQUIRED_REPORT_SECTIONS)
            # Must mention at least 3 critical findings
            critical_count = sum(1 for f in findings if f.severity == "critical")
            if critical_count >= 3:
                report_score = min(1.0, report_score + 0.2)
        else:
            report_score = 0.0
        scores["report_quality"] = report_score

        # False positives
        fp_count = sum(1 for f in findings if f.query_index in self.CLEAN)
        fp_penalty = fp_count * 0.05
        scores["false_positive_penalty"] = -fp_penalty

        total = max(0.0, min(1.0,
            scores["security_detection"] * 0.30
            + scores["performance_detection"] * 0.20
            + scores["compliance_detection"] * 0.30
            + scores["report_quality"] * 0.20
            + scores["catastrophic_bonus"]
            - fp_penalty
        ))

        return Reward(
            value=round(total, 4),
            breakdown={k: round(v, 4) for k, v in scores.items()},
            message=(
                f"Security: {len(sec_detected)}/{len(self.SECURITY_CRITICAL)}, "
                f"Perf: {len(perf_detected)}/{len(self.PERF_ISSUES)}, "
                f"Compliance: {len(pii_detected)}/{len(self.PII_QUERIES)}, "
                f"Report: {report_score:.2f}"
            )
        )


GRADERS = {
    "task_easy": EasyGrader(),
    "task_medium": MediumGrader(),
    "task_hard": HardGrader(),
}
