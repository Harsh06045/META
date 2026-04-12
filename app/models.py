"""
SQLAudit-Env: Typed Pydantic models for OpenEnv spec compliance.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


class ActionType(str, Enum):
    SCAN_QUERY = "scan_query"
    REWRITE_QUERY = "rewrite_query"
    FLAG_COMPLIANCE = "flag_compliance"
    SUBMIT_REPORT = "submit_report"
    SKIP = "skip"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class QueryStatus(str, Enum):
    PENDING = "pending"
    SCANNED = "scanned"
    REWRITTEN = "rewritten"
    FLAGGED = "flagged"
    SKIPPED = "skipped"


class Finding(BaseModel):
    query_index: int
    finding_type: str  # "injection", "performance", "compliance", "style"
    severity: Severity
    description: str
    rewritten_sql: Optional[str] = None
    reasoning: Optional[str] = None


class SchemaTable(BaseModel):
    name: str
    columns: List[Dict[str, str]]  # [{name, type, nullable, pii}]
    indexes: List[str] = []
    row_estimate: int = 1000


class Observation(BaseModel):
    task_id: str
    step: int
    max_steps: int
    queries: List[str]
    sql_schema: Dict[str, SchemaTable] = Field(..., alias="schema")
    schema_info: Optional[Dict[str, SchemaTable]] = None
    query_statuses: List[QueryStatus]
    findings_so_far: List[Finding]
    remaining_steps: int
    phase: str
    score_so_far: float = 0.0

    model_config = ConfigDict(use_enum_values=True, populate_by_name=True)


class Action(BaseModel):
    action_type: ActionType
    query_index: Optional[int] = None
    finding: Optional[str] = None
    severity: Optional[Severity] = None
    rewritten_sql: Optional[str] = None
    reasoning: Optional[str] = None
    report_summary: Optional[str] = None

    model_config = {"use_enum_values": True}


class Reward(BaseModel):
    value: float = Field(ge=0.0, le=1.0)
    breakdown: Dict[str, float] = {}
    message: str = ""


class StepResult(BaseModel):
    observation: Observation
    reward: float  # Simplified to float for strict OpenEnv compatibility
    done: bool
    info: Dict[str, Any] = {}


class EnvironmentState(BaseModel):
    task_id: str
    step: int
    done: bool
    episode_reward: float
    findings: List[Finding]
    query_statuses: List[QueryStatus]
    phase: str
