---
title: "sqla-env"
emoji: "💼"
colorFrom: "blue"
colorTo: "indigo"
sdk: "docker"
app_port: 7860
sdk_version: "3.11"
app_file: "app/server.py"
pinned: false
---
# SQLAudit-Env 🔍

**An OpenEnv environment for training AI agents on enterprise SQL security auditing, performance optimization, and GDPR compliance.**

---

## 🚀 Mission Control Dashboard
Once running, visit the main URL to access the interactive dashboard.

### API Layer
- **POST `/reset`**: Start new episode
- **POST `/step`**: Execute audit action
- **GET `/state`**: Current environment state
- **GET `/health`**: Health check

---

## Motivation

Database engineers routinely audit production SQL for injection risk, performance anti-patterns, and compliance (e.g. PII exposure). This environment encodes that workflow as a structured RL-style API so agents can learn from **step-level feedback** and final **0.0–1.0** grader scores.

## Observation and action spaces

- **Observation:** `task_id`, `step`, `max_steps`, `queries[]`, `schema` (table metadata), `query_statuses`, `findings_so_far`, `remaining_steps`, `phase`, rewards aliases, optional `hint`.
- **Action:** `action_type` ∈ `scan_query` | `rewrite_query` | `flag_compliance` | `submit_report` | `skip`, plus `query_index`, `finding`, `severity`, `rewritten_sql`, `reasoning`, `report_summary` as needed.

See `openenv.yaml` and `app/models.py` for the full schema.

## Tasks (easy → hard)

| Task | Focus |
|------|--------|
| `task_easy` | SQL injection / unsafe patterns in 5 queries |
| `task_medium` | Performance issues (N+1, joins, indexes) across 8 queries |
| `task_hard` | Security + performance + GDPR-style compliance + audit report |

Each task has a deterministic grader in `app/graders.py`; episode rewards stay in **[0.0, 1.0]**.

## Setup and run

**Docker**

```bash
docker build -t sqla-env .
docker run -p 7860:7860 sqla-env
```

**uv (OpenEnv tooling)**

```bash
uv sync
uv run server
```

**Validate (before submit)**

```bash
pip install openenv
python -m openenv.cli validate .
python -m openenv.cli validate --url https://YOUR-SPACE.hf.space
```

## Baseline inference

The competition **`inference.py`** lives at the **repository root** (copy is also under this folder for Docker `COPY`). Configure `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`, and `ENV_BASE_URL`, then run `python inference.py`. Reported **mean_score** and per-task scores depend on the model; re-run for your baseline table.

## Troubleshooting `POST /reset` (422 “body Field required”)

Production server uses **`Request` only** for `/reset` (no Pydantic body field), so empty bodies are valid. Confirm deploy with:

`GET /health` → JSON must include `"reset_handler": "request-async-no-body-param-v2"`. If missing, **rebuild the Hugging Face Space** from the latest Git push (try **rebuild without cache**).

From repo root: `python scripts/verify_hackathon_endpoints.py https://YOUR-SPACE.hf.space`

## OpenEnv compliance

Typed Pydantic models, `step` / `reset` / `state`, `openenv.yaml`, and **`pyproject.toml` + `uv.lock`** for `openenv validate` multi-mode readiness.
