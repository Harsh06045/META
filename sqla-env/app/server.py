"""SQLAudit-Env: FastAPI Server — Updated with advanced UI"""
from __future__ import annotations
import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
from app.models import Action, Observation, StepResult, EnvironmentState
from app.environment import SQLAuditEnvironment
from app.tasks import TASKS

app = FastAPI(title="SQLAudit-Env", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
_env = SQLAuditEnvironment()

class ResetRequest(BaseModel):
    task_id: str = "task_easy"

@app.post("/reset", response_model=Observation)
def reset(req: Optional[ResetRequest] = None):
    # Optional JSON body: harness may POST with no body (OpenEnv reset check).
    task_id = "task_easy"
    if req is not None:
        if hasattr(req, "task_id") and req.task_id:
            task_id = req.task_id
        elif isinstance(req, dict) and req.get("task_id"):
            task_id = req["task_id"]
    
    try:
        return _env.reset(task_id=task_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.get("/health")
def health(): return {"status": "ok", "version": "1.0.0"}

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
