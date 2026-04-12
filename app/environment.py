"""
SQLAudit-Env: Core environment engine.
Implements the OpenEnv step() / reset() / state() interface.
"""
from __future__ import annotations
import copy
from typing import Any, Dict, Optional, List
from app.models import (
    Observation, Action, Reward, StepResult, EnvironmentState,
    Finding, ActionType, QueryStatus, Severity
)
from app.tasks import TASKS, SHARED_SCHEMA
from app.graders import GRADERS


class SQLAuditEnvironment:
    """
    OpenEnv-compliant environment for SQL auditing tasks.
    Thread-safe per-instance; create one per episode.
    """

    def __init__(self):
        self._task_id: Optional[str] = None
        self._task_def: Optional[Dict] = None
        self._step_count: int = 0
        self._done: bool = False
        self._findings: List[Finding] = []
        self._query_statuses: List[QueryStatus] = []
        self._episode_reward: float = 0.0
        self._phase_index: int = 0
        self._report_summary: str = ""
        self._actions_log: List[Dict] = []

    # ─── OpenEnv API ─────────────────────────────────────────────────────────

    def reset(self, task_id: str = "task_easy") -> Observation:
        """Reset environment to initial state for the given task."""
        if task_id not in TASKS:
            raise ValueError(f"Unknown task: {task_id}. Choose from {list(TASKS.keys())}")

        self._task_id = task_id
        self._task_def = TASKS[task_id]
        self._step_count = 0
        self._done = False
        self._findings = []
        self._query_statuses = [QueryStatus.PENDING for _ in self._task_def["queries"]]
        self._episode_reward = 0.0
        self._phase_index = 0
        self._report_summary = ""
        self._actions_log = []

        return self._build_observation(hint=f"You are auditing {len(self._task_def['queries'])} SQL queries. Start by scanning each query for security vulnerabilities.")

    def step(self, action: Action) -> StepResult:
        """Execute one agent action and return (observation, reward, done, info)."""
        if self._done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        self._step_count += 1
        reward_value = 0.0
        info: Dict[str, Any] = {}

        action_type = action.action_type if isinstance(action.action_type, str) else action.action_type.value

        # ── Process action ────────────────────────────────────────────────────
        if action_type == ActionType.SCAN_QUERY or action_type == "scan_query":
            reward_value, info = self._handle_scan(action)

        elif action_type == ActionType.REWRITE_QUERY or action_type == "rewrite_query":
            reward_value, info = self._handle_rewrite(action)

        elif action_type == ActionType.FLAG_COMPLIANCE or action_type == "flag_compliance":
            reward_value, info = self._handle_compliance(action)

        elif action_type == ActionType.SUBMIT_REPORT or action_type == "submit_report":
            reward_value, info = self._handle_report(action)
            self._done = True

        elif action_type == ActionType.SKIP or action_type == "skip":
            reward_value = -0.02  # small penalty for skipping
            if action.query_index is not None and action.query_index < len(self._query_statuses):
                self._query_statuses[action.query_index] = QueryStatus.SKIPPED
            info["message"] = "Query skipped"

        # ── Step limit check ──────────────────────────────────────────────────
        max_steps = self._task_def["max_steps"]
        if self._step_count >= max_steps and not self._done:
            self._done = True
            # Final grade at step limit
            final_reward = self._compute_final_reward()
            reward_value = final_reward.value
            info["reason"] = "step_limit_reached"
            info["final_grade"] = final_reward.breakdown

        # ── Cumulative reward (shaped) ─────────────────────────────────────
        self._episode_reward = min(1.0, self._episode_reward + max(0.0, reward_value * 0.1))

        reward = Reward(
            value=max(0.0, min(1.0, reward_value)),
            breakdown=info.get("breakdown", {}),
            message=info.get("message", "")
        )

        obs = self._build_observation()
        self._actions_log.append({"step": self._step_count, "action": action.model_dump(), "reward": reward_value})

        info["reward_details"] = reward.model_dump()
        return StepResult(
            observation=obs,
            reward=reward.value,
            done=self._done,
            info=info
        )

    def state(self) -> EnvironmentState:
        """Return current environment state snapshot."""
        return EnvironmentState(
            task_id=self._task_id or "",
            step=self._step_count,
            done=self._done,
            episode_reward=round(self._episode_reward, 4),
            findings=self._findings,
            query_statuses=self._query_statuses,
            phase=self._current_phase()
        )

    # ─── Internal helpers ─────────────────────────────────────────────────────

    def _current_phase(self) -> str:
        phases = self._task_def.get("phase_sequence", ["scanning"]) if self._task_def else ["scanning"]
        idx = min(self._phase_index, len(phases) - 1)
        return phases[idx]

    def _advance_phase(self):
        phases = self._task_def.get("phase_sequence", ["scanning"])
        if self._phase_index < len(phases) - 1:
            self._phase_index += 1

    def _build_observation(self, hint: str = "") -> Observation:
        td = self._task_def
        return Observation(
            task_id=self._task_id,
            step=self._step_count,
            max_steps=td["max_steps"],
            queries=td["queries"],
            sql_schema=SHARED_SCHEMA,
            schema_info=SHARED_SCHEMA,
            query_statuses=self._query_statuses,
            findings_so_far=self._findings,
            remaining_steps=td["max_steps"] - self._step_count,
            phase=self._current_phase(),
            score_so_far=round(self._episode_reward, 4)
        )

    def _phase_hint(self) -> str:
        phase = self._current_phase()
        hints = {
            "scanning": "Scan each query for SQL injection and security vulnerabilities.",
            "optimizing": "Identify performance issues: missing indexes, cartesian joins, N+1 patterns.",
            "compliance": "Flag PII exposure and GDPR violations in query results.",
            "reporting": "Submit a comprehensive audit report covering all findings.",
        }
        return hints.get(phase, "")

    def _handle_scan(self, action: Action):
        qi = action.query_index
        if qi is None or qi >= len(self._task_def["queries"]):
            return -0.05, {"message": "Invalid query index"}

        finding = Finding(
            query_index=qi,
            finding_type=action.finding or "security",
            severity=action.severity or Severity.INFO,
            description=action.finding or "",
            reasoning=action.reasoning,
        )
        self._findings.append(finding)
        self._query_statuses[qi] = QueryStatus.SCANNED

        # Partial reward: ground truth check for immediate feedback
        gt = self._task_def.get("ground_truth", {})
        reward = 0.0
        vuln = gt.get("vulnerable_indices", gt.get("security_issues", {}))
        is_vuln_query = (qi in vuln) if isinstance(vuln, (set, list)) else (qi in vuln)

        desc_lower = (action.finding or "").lower()
        mentions_injection = any(k in desc_lower for k in ["inject", "concat", "unsafe", "union", "dynamic", "exec"])

        if is_vuln_query:
            if mentions_injection and action.severity in ("critical", "high"):
                reward = 0.8
            elif mentions_injection:
                reward = 0.5
            elif action.severity in ("critical", "high"):
                reward = 0.3
            else:
                reward = 0.1
        else:
            # Penalize false positives on safe queries
            safe = gt.get("safe_indices", gt.get("clean_queries", []))
            if qi in safe and action.severity in ("critical", "high"):
                reward = -0.3
            else:
                reward = 0.05  # minor reward for scanning

        self._advance_phase_if_needed()
        return reward, {"message": f"Scanned query {qi}", "is_vulnerable": is_vuln_query}

    def _handle_rewrite(self, action: Action):
        qi = action.query_index
        if qi is None or qi >= len(self._task_def["queries"]):
            return -0.05, {"message": "Invalid query index"}

        # Find existing finding to enrich
        existing = [f for f in self._findings if f.query_index == qi]
        if existing:
            existing[-1].rewritten_sql = action.rewritten_sql
            existing[-1].reasoning = action.reasoning
        else:
            self._findings.append(Finding(
                query_index=qi,
                finding_type="performance",
                severity=action.severity or Severity.MEDIUM,
                description=action.finding or "Performance rewrite",
                rewritten_sql=action.rewritten_sql,
                reasoning=action.reasoning,
            ))
        self._query_statuses[qi] = QueryStatus.REWRITTEN

        reward = 0.0
        gt = self._task_def.get("ground_truth", {})
        perf_issues = gt.get("performance_issues", {})

        if qi in perf_issues:
            rewrite = action.rewritten_sql or ""
            if len(rewrite) > 20:
                reward = 0.7
                if action.reasoning and len(action.reasoning) > 30:
                    reward = 0.9
            else:
                reward = 0.2
        else:
            reward = -0.1  # penalize rewriting a clean query

        return reward, {"message": f"Rewrote query {qi}", "rewrite_length": len(action.rewritten_sql or "")}

    def _handle_compliance(self, action: Action):
        qi = action.query_index
        if qi is None or qi >= len(self._task_def["queries"]):
            return -0.05, {"message": "Invalid query index"}

        finding = Finding(
            query_index=qi,
            finding_type="compliance",
            severity=action.severity or Severity.HIGH,
            description=action.finding or "",
            reasoning=action.reasoning,
        )
        self._findings.append(finding)
        self._query_statuses[qi] = QueryStatus.FLAGGED

        gt = self._task_def.get("ground_truth", {})
        compliance_flags = gt.get("compliance_flags", {})
        pii_queries = gt.get("pii_exposure", {})

        reward = 0.0
        desc_lower = (action.finding or "").lower()
        mentions_pii = any(k in desc_lower for k in ["pii", "gdpr", "personal", "ssn", "password", "email", "compliance"])

        if qi in compliance_flags or qi in pii_queries:
            if mentions_pii:
                reward = 0.85
            else:
                reward = 0.4
        else:
            reward = -0.15  # false compliance flag

        self._advance_phase_if_needed()
        return reward, {"message": f"Flagged compliance issue on query {qi}"}

    def _handle_report(self, action: Action):
        self._report_summary = action.report_summary or action.reasoning or action.finding or ""
        final_reward = self._compute_final_reward()
        self._episode_reward = final_reward.value
        return final_reward.value, {
            "message": "Report submitted. Episode complete.",
            "breakdown": final_reward.breakdown,
            "final_score": final_reward.value
        }

    def _compute_final_reward(self) -> Reward:
        grader = GRADERS.get(self._task_id)
        if not grader:
            return Reward(value=0.0, message="No grader found")

        if self._task_id == "task_hard":
            return grader.grade(self._findings, self._query_statuses, self._report_summary)
        return grader.grade(self._findings, self._query_statuses)

    def _advance_phase_if_needed(self):
        """Auto-advance phase when enough queries in current phase are processed."""
        pending = sum(1 for s in self._query_statuses if s == QueryStatus.PENDING)
        total = len(self._query_statuses)
        processed = total - pending
        if processed > 0 and processed % max(1, total // len(self._task_def.get("phase_sequence", ["scanning"]))) == 0:
            self._advance_phase()
