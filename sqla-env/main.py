from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, Body, Request
from app.env import SQLAEnv
from app.models import Action

class ResetRequest(BaseModel):
    task_id: str = "task_easy"

app = FastAPI(title="SQLAudit-Env API")
env = SQLAEnv()

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/reset")
def reset(req: Optional[ResetRequest] = Body(None)):
    task_id = "task_easy"
    if req is not None:
        task_id = req.task_id if req.task_id else "task_easy"
    return env.reset(task_id)

@app.post("/step")
def step(action: Action):
    return env.step(action)

@app.get("/state")
def state():
    return env._get_observation()

@app.get("/tasks")
def list_tasks():
    return [
        {"id": "task_easy", "name": "SQL Security Scan"},
        {"id": "task_medium", "name": "Query Performance Optimizer"},
        {"id": "task_hard", "name": "Full Audit Pipeline"}
    ]
