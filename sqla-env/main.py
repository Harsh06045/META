import json
from fastapi import FastAPI, Request
from app.env import SQLAEnv
from app.models import Action

app = FastAPI(title="SQLAudit-Env API")
env = SQLAEnv()

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/reset")
async def reset(request: Request):
    task_id = "task_easy"
    raw = await request.body()
    if raw:
        try:
            data = json.loads(raw.decode("utf-8"))
            if isinstance(data, dict) and data.get("task_id"):
                task_id = str(data["task_id"])
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
            pass
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
