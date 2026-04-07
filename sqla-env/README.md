---
title: SQLAudit-Env
emoji: 🛡️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
tags:
  - openenv
  - sql
  - security
  - database
  - rl-environment
  - fastapi
pinned: false
---
# SQLAudit-Env 🔍

**An OpenEnv environment for training AI agents on enterprise SQL security auditing, performance optimization, and GDPR compliance.**

[![OpenEnv](https://img.shields.io/badge/OpenEnv-v1.0.0-00d4aa?style=flat-square)](https://openenv.dev)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-Space-yellow?style=flat-square)](https://huggingface.co/spaces)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)](https://python.org)

---

## 🎯 Motivation

Every production database accumulates dangerous SQL: injection vulnerabilities costing millions in breaches, cartesian joins silently degrading performance, PII columns exposed to downstream APIs in GDPR violation. Database engineers spend 20–40% of their time in code review catching these issues.

**SQLAudit-Env** trains AI agents to do this work — automatically, at scale, with expert-level precision. This is a real workflow engineers at AWS, Stripe, and Cloudflare perform daily. Agents trained here can be deployed in CI pipelines to catch issues before they reach production.

---

## 🏗️ Environment Architecture

```
SQLAudit-Env
├── app/
│   ├── models.py       # Typed Pydantic models (Observation, Action, Reward)
│   ├── environment.py  # Core env engine: step() / reset() / state()
│   ├── tasks.py        # Task definitions with ground-truth query sets
│   ├── graders.py      # Deterministic agent graders (0.0–1.0)
│   └── server.py       # FastAPI HTTP server (OpenEnv REST API)
├── tests/              # Pytest test suite (15 tests)
├── inference.py        # Baseline inference script (OpenAI client)
├── openenv.yaml        # OpenEnv spec metadata
├── Dockerfile          # Container for HF Spaces
└── requirements.txt
```

---

## 🗺️ Observation Space

```python
Observation(
    task_id:         str,           # "task_easy" | "task_medium" | "task_hard"
    step:            int,           # Current step (0-indexed)
    max_steps:       int,           # Episode step budget
    queries:         List[str],     # SQL queries to audit
    schema_info:     Dict[str, SchemaTable],  # Tables with columns, indexes, row estimates
    query_statuses:  List[QueryStatus],       # pending|scanned|rewritten|flagged|skipped
    findings_so_far: List[Finding], # Accumulated findings this episode
    remaining_steps: int,           # Steps left before forced termination
    phase:           str,           # scanning|optimizing|compliance|reporting
    score_so_far:    float,         # Running episode reward (shaped)
    hint:            str,           # Phase-appropriate guidance
)
```

---

## ⚡ Action Space

```python
Action(
    action_type:    Literal["scan_query","rewrite_query","flag_compliance","submit_report","skip"],
    query_index:    int,            # 0-based index into queries list
    finding:        str,            # Human-readable finding description
    severity:       Literal["critical","high","medium","low","info"],
    rewritten_sql:  str,            # Optimized/secure SQL (for rewrite_query)
    reasoning:      str,            # Agent's reasoning chain
    report_summary: str,            # Full report text (for submit_report only)
)
```

| Action | Use When |
|--------|----------|
| `scan_query` | Identifying security vulnerabilities (SQL injection, unsafe patterns) |
| `rewrite_query` | Providing an optimized or secure replacement query |
| `flag_compliance` | Flagging PII exposure, GDPR violations, password leakage |
| `submit_report` | Ending the episode with a structured audit report |
| `skip` | Intentionally skipping a query (costs -0.02 reward) |

---

## 🎮 Tasks

### Task 1: SQL Security Scan (Easy)
- **5 queries**, **20 step budget**
- **Goal:** Identify SQL injection vulnerabilities; avoid false positives on safe queries
- **Patterns:** String concatenation injection, UNION attacks, dynamic SQL execution
- **Grading:** True positive rate (45%) + Severity accuracy (30%) + Description quality (25%) − False positive penalty

**Expected difficulty:** A capable GPT-4o-mini should score 0.65–0.80

### Task 2: Query Performance Optimizer (Medium)
- **8 queries**, **30 step budget**
- **Goal:** Detect performance anti-patterns and provide rewritten SQL
- **Patterns:** Cartesian joins, N+1 subqueries, missing LIMIT, function-on-indexed-column, SELECT *
- **Grading:** Detection rate (35%) + Critical issue caught (20%) + Rewrite quality (25%) + Severity calibration (20%)

**Expected difficulty:** Requires domain knowledge; GPT-4o scores ~0.55–0.75

### Task 3: Full Audit Pipeline (Hard)
- **12 queries**, **50 step budget**, **4 phases**: scanning → optimizing → compliance → reporting
- **Goal:** Full audit: security + performance + GDPR compliance + structured report
- **Patterns:** All of above + PII over-exposure, UPDATE without WHERE, missing transactions, IP retention violations
- **Grading:** Security (30%) + Performance (20%) + Compliance (30%) + Report quality (20%)

**Expected difficulty:** Frontier models score 0.40–0.65; requires multi-phase reasoning

---

## 🏆 Reward Function

The reward reward is **shaped across the full trajectory** — not sparse end-of-episode only:

| Signal | Reward | Rationale |
|--------|--------|-----------|
| Correct vulnerability detection (with reasoning) | +0.8 | Core task |
| Correct detection (severity match) | +0.5 | Partial credit |
| Scan of safe query (no false alarm) | +0.05 | Calibration |
| False positive on safe query (critical) | -0.30 | Precision matters |
| Correct performance rewrite with reasoning | +0.90 | High-value skill |
| Correct compliance flag (mentions GDPR/PII) | +0.85 | Privacy-critical |
| Skip action | -0.02 | Mild discouragement |
| Step limit hit | Final grade computed | Forces completion |
| submit_report | Full grader score applied | Episode terminus |

**Partial progress:** Agents receive reward at each step, enabling RL training from non-terminal states.

---

## 📡 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/reset` | Start new episode: `{"task_id": "task_easy"}` |
| `POST` | `/step` | Execute action (Action JSON body) |
| `GET` | `/state` | Current environment state |
| `GET` | `/tasks` | List all tasks with metadata |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Interactive Swagger UI |

---

## 🚀 Setup & Usage

### Local Development

```bash
git clone <repo>
cd sqla-env
pip install -r requirements.txt
uvicorn app.server:app --host 0.0.0.0 --port 7860
```

### Docker

```bash
docker build -t sqla-env .
docker run -p 7860:7860 sqla-env
```

### Run Tests

```bash
pytest tests/ -v
# → 15 passed
```

### Run Inference Baseline

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="sk-..."
export ENV_BASE_URL="http://localhost:7860"

python inference.py
```

---

## 📊 Baseline Scores

Scores measured with `gpt-4o-mini` (temperature=0.2):

| Task | Score | Notes |
|------|-------|-------|
| task_easy | ~0.72 | Good injection detection, occasional false positive |
| task_medium | ~0.58 | Misses function-on-index pattern, good cartesian detection |
| task_hard | ~0.44 | Strong security, weak compliance section |
| **Mean** | **~0.58** | Leaves significant room for specialized fine-tuning |

---

## 🔧 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `API_BASE_URL` | LLM API endpoint (OpenAI-compatible) | Yes |
| `MODEL_NAME` | Model identifier (e.g. `gpt-4o-mini`) | Yes |
| `HF_TOKEN` | API key / HuggingFace token | Yes |
| `ENV_BASE_URL` | SQLAudit-Env server URL | No (default: localhost:7860) |
| `PORT` | Server port | No (default: 7860) |

---

## 🧪 OpenEnv Compliance

- ✅ `openenv.yaml` with full metadata
- ✅ Typed Pydantic `Observation`, `Action`, `Reward` models
- ✅ `step()` → `(observation, reward, done, info)`
- ✅ `reset()` → initial observation
- ✅ `state()` → current state snapshot
- ✅ 3 tasks with difficulty progression (easy → medium → hard)
- ✅ Deterministic graders (scores reproducible)
- ✅ Reward in `[0.0, 1.0]`
- ✅ Partial reward signals (shaped, not sparse)
- ✅ Docker + HuggingFace Spaces deployment

---

## 🏷️ Tags

`openenv` · `sql` · `security` · `database` · `enterprise` · `code-review` · `gdpr` · `rl-environment`
