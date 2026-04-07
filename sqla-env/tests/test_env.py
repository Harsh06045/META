"""
Tests for SQLAudit-Env — validates OpenEnv spec compliance.
Run with: pytest tests/ -v
"""
import pytest
from app.environment import SQLAuditEnvironment
from app.models import Action, ActionType, Severity, QueryStatus


@pytest.fixture
def env():
    return SQLAuditEnvironment()


# ─── reset() ─────────────────────────────────────────────────────────────────

def test_reset_easy(env):
    obs = env.reset("task_easy")
    assert obs.task_id == "task_easy"
    assert obs.step == 0
    assert len(obs.queries) == 5
    assert all(s == QueryStatus.PENDING for s in obs.query_statuses)
    assert obs.findings_so_far == []


def test_reset_medium(env):
    obs = env.reset("task_medium")
    assert obs.task_id == "task_medium"
    assert len(obs.queries) == 8


def test_reset_hard(env):
    obs = env.reset("task_hard")
    assert obs.task_id == "task_hard"
    assert len(obs.queries) == 12


def test_reset_invalid_task(env):
    with pytest.raises(ValueError):
        env.reset("nonexistent_task")


def test_reset_clears_state(env):
    env.reset("task_easy")
    env.step(Action(action_type=ActionType.SCAN_QUERY, query_index=0,
                    finding="injection", severity=Severity.CRITICAL))
    obs = env.reset("task_easy")
    assert obs.step == 0
    assert obs.findings_so_far == []


# ─── step() ──────────────────────────────────────────────────────────────────

def test_step_scan_vulnerable(env):
    env.reset("task_easy")
    result = env.step(Action(
        action_type=ActionType.SCAN_QUERY,
        query_index=0,
        finding="SQL injection via string concatenation — user_input unsanitized",
        severity=Severity.CRITICAL,
        reasoning="Classic injection pattern"
    ))
    assert 0.0 <= result.reward.value <= 1.0
    assert result.reward.value > 0  # should get positive reward
    assert result.observation.step == 1
    assert result.observation.query_statuses[0] == QueryStatus.SCANNED


def test_step_false_positive_penalty(env):
    env.reset("task_easy")
    # Query 1 is safe — flagging it critical should get penalty
    result = env.step(Action(
        action_type=ActionType.SCAN_QUERY,
        query_index=1,
        finding="SQL injection",
        severity=Severity.CRITICAL,
    ))
    assert result.reward.value <= 0.1  # should be penalized or near zero


def test_step_rewrite(env):
    env.reset("task_medium")
    result = env.step(Action(
        action_type=ActionType.REWRITE_QUERY,
        query_index=3,
        finding="Cartesian join detected",
        severity=Severity.CRITICAL,
        rewritten_sql="SELECT u.email, o.total_amount FROM users u JOIN orders o ON u.id = o.user_id WHERE o.total_amount > 500",
        reasoning="Added explicit JOIN condition to eliminate cartesian product"
    ))
    assert result.reward.value > 0.5


def test_step_compliance_flag(env):
    env.reset("task_hard")
    result = env.step(Action(
        action_type=ActionType.FLAG_COMPLIANCE,
        query_index=1,
        finding="GDPR violation: exposing ssn, password_hash PII columns without business justification",
        severity=Severity.HIGH,
    ))
    assert result.reward.value > 0.3


def test_step_submit_report_ends_episode(env):
    env.reset("task_easy")
    env.step(Action(action_type=ActionType.SCAN_QUERY, query_index=0,
                    finding="injection", severity=Severity.CRITICAL))
    result = env.step(Action(
        action_type=ActionType.SUBMIT_REPORT,
        report_summary="executive_summary: Found 3 critical SQL injections. critical_findings: queries 0,2,4. compliance_violations: none. recommendations: use parameterized queries."
    ))
    assert result.done is True
    assert 0.0 <= result.reward.value <= 1.0


def test_step_after_done_raises(env):
    env.reset("task_easy")
    env.step(Action(action_type=ActionType.SUBMIT_REPORT, report_summary="done"))
    with pytest.raises(RuntimeError):
        env.step(Action(action_type=ActionType.SKIP))


# ─── state() ─────────────────────────────────────────────────────────────────

def test_state_initial(env):
    env.reset("task_easy")
    s = env.state()
    assert s.task_id == "task_easy"
    assert s.step == 0
    assert s.done is False


def test_state_after_steps(env):
    env.reset("task_medium")
    env.step(Action(action_type=ActionType.SCAN_QUERY, query_index=0,
                    finding="test", severity=Severity.HIGH))
    s = env.state()
    assert s.step == 1
    assert len(s.findings) == 1


# ─── reward bounds ───────────────────────────────────────────────────────────

def test_reward_always_in_bounds(env):
    """Reward must always be in [0, 1]."""
    for task_id in ["task_easy", "task_medium", "task_hard"]:
        env.reset(task_id)
        for i in range(5):
            result = env.step(Action(
                action_type=ActionType.SCAN_QUERY,
                query_index=i % 3,
                finding="injection vulnerability",
                severity=Severity.CRITICAL,
            ))
            assert 0.0 <= result.reward.value <= 1.0, f"Reward out of bounds: {result.reward.value}"


# ─── grader determinism ──────────────────────────────────────────────────────

def test_grader_deterministic(env):
    """Same actions must produce same final score."""
    def run():
        env.reset("task_easy")
        env.step(Action(action_type=ActionType.SCAN_QUERY, query_index=0,
                        finding="sql injection string concat", severity=Severity.CRITICAL))
        env.step(Action(action_type=ActionType.SCAN_QUERY, query_index=2,
                        finding="union attack injection", severity=Severity.CRITICAL))
        result = env.step(Action(action_type=ActionType.SUBMIT_REPORT,
                                 report_summary="critical_findings: 2 injections"))
        return result.reward.value

    score1 = run()
    score2 = run()
    assert score1 == score2, f"Grader not deterministic: {score1} vs {score2}"
