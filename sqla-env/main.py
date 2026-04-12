from fastapi import Body, FastAPI
from pydantic import BaseModel, ConfigDict
from app.env import SQLAEnv
from app.models import Action

class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    task_id: str = "task_easy"

app = FastAPI(title="SQLAudit-Env API")
env = SQLAEnv()

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/reset")
def reset(body: ResetRequest = Body(default_factory=ResetRequest)):
    task_id = body.task_id if body.task_id else "task_easy"
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
