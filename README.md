# SQLAudit-Env (OpenEnv)

Real-world SQL security / performance / compliance auditing for agents. Implementation lives under `sqla-env/`; **`inference.py` is at the repository root** (submission requirement).

## Hugging Face Space

- **Docker (from repo root):** `docker build -t sqla-env .` then `docker run -p 7860:7860 sqla-env`
- Alternative: `cd sqla-env && docker build -t sqla-env .` (uses `sqla-env/inference.py`; keep it in sync with root `inference.py`)

Space must respond **200** on `/health` and accept **POST `/reset`** (empty or JSON body).

## Inference (baseline)

Set secrets / endpoints in the environment (HF Space **Settings → Variables**):

| Variable | Purpose |
|----------|---------|
| `API_BASE_URL` | OpenAI-compatible LLM base URL |
| `MODEL_NAME` | Model id |
| `HF_TOKEN` | API key passed to `OpenAI(api_key=...)` |
| `ENV_BASE_URL` | Base URL of this Space (or `OPENENV_BASE_URL`), e.g. `https://USER-space.hf.space` |

Optional: `INFERENCE_MAX_SECONDS` (default **1080**) to stay under the **20 minute** runtime cap.

```bash
export ENV_BASE_URL=http://localhost:7860
export API_BASE_URL=...
export MODEL_NAME=...
export HF_TOKEN=...
python inference.py
```

Logs use **`[START]`**, **`[STEP]`**, **`[END]`** on stdout only.

## Pre-submission validation

Install the OpenEnv CLI, then from `sqla-env/`:

```bash
pip install openenv
python -m openenv.cli validate .
python -m openenv.cli validate --url https://YOUR-SPACE.hf.space
```

The environment includes **`sqla-env/pyproject.toml`** and **`sqla-env/uv.lock`** so local validation reports **multi-mode deployment** readiness (Docker, `uv run server`, etc.).

## Resource notes

Image is **Python 3.11 slim** with modest dependencies; fits **2 vCPU / 8 GB** when the LLM is external (API calls only).
