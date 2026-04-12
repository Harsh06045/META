"""SQLAudit-Env: FastAPI Server — Updated with advanced UI"""
from __future__ import annotations
import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette.requests import Request
import uvicorn
from app.models import Action, Observation, StepResult, EnvironmentState
from app.environment import SQLAuditEnvironment
from app.tasks import TASKS

app = FastAPI(title="SQLAudit-Env", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
_env = SQLAuditEnvironment()

# Public string so you can confirm the running image from GET /health (avoids stale HF deploys).
RESET_HANDLER_ID = "request-async-no-body-param-v2"


@app.post("/reset", response_model=Observation)
@app.post("/reset/", response_model=Observation, include_in_schema=False)
async def reset(request: Request):
    """
    No Pydantic *body* parameter — avoids 422 'body Field required' when clients POST with
    empty/missing body (OpenEnv automated checks). JSON body is optional: {"task_id": "..."}.
    """
    task_id = "task_easy"
    raw = await request.body()
    if raw:
        try:
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
            data = None
        if isinstance(data, dict):
            tid = data.get("task_id")
            if tid is not None and str(tid).strip():
                task_id = str(tid).strip()
    try:
        return _env.reset(task_id=task_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "reset_handler": RESET_HANDLER_ID,
    }

@app.get("/tasks")
def list_tasks(): return {tid: {"id": td["id"], "name": td["name"], "difficulty": td["difficulty"]} for tid, td in TASKS.items()}

    
@app.post("/step", response_model=StepResult)
def step(action: Action):
    try: return _env.step(action)
    except RuntimeError as e: raise HTTPException(400, str(e))

@app.get("/state", response_model=EnvironmentState)
def state(): return _env.state()

@app.get("/", response_class=HTMLResponse)
def index():
    # Read from embedded HTML or file
    html_path = os.path.join(os.path.dirname(__file__), "sqlaudit_ui.html")
    try:
        with open(html_path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        pass
    # Fallback inline minimal UI
    return _INLINE_UI

_INLINE_UI = """<!DOCTYPE html>
<html><head><title>SQLAudit-Env</title>
<style>body{font-family:monospace;background:#080b12;color:#e8edf7;padding:40px}</style>
</head><body>
<h1>SQLAudit-Env v1.0.0</h1>
<p>API is running. Visit <a href="/docs" style="color:#3b82f6">/docs</a> for the Swagger UI.</p>
</body></html>"""

def main() -> None:
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("app.server:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
