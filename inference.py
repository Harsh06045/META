"""
inference.py — SQLAudit-Env baseline inference script.

Uses OpenAI client to run an LLM agent against all 3 tasks.
Emits structured [START] / [STEP] / [END] logs to stdout.

Required env vars (HF submission):
  API_BASE_URL   LLM API endpoint (OpenAI-compatible)
  MODEL_NAME     Model identifier
  HF_TOKEN       Hugging Face / API key (OpenAI client api_key)
  ENV_BASE_URL   OpenEnv HTTP base URL (the Space serving step/reset/state)

Optional:
  INFERENCE_MAX_SECONDS  Wall-clock budget for entire run (default 1080, under 20min cap)
  LOCAL_IMAGE_NAME       If using from_docker_image() workflows
"""
from __future__ import annotations
import os
import json
import re
import sys
import time
from typing import Any, Dict, List, Optional

import requests
from openai import OpenAI

# ─── Config (defaults only where allowed: API_BASE_URL, MODEL_NAME) ───────────

API_BASE_URL = os.getenv("API_BASE_URL", "<your-active-endpoint>")
MODEL_NAME = os.getenv("MODEL_NAME", "<your-active-model>")
HF_TOKEN = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
ENV_BASE = os.getenv("ENV_BASE_URL") or os.getenv("OPENENV_BASE_URL")

INFERENCE_MAX_SECONDS = float(os.getenv("INFERENCE_MAX_SECONDS", "1080"))

client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)

TASKS = ["task_easy", "task_medium", "task_hard"]


# ─── Environment client helpers ───────────────────────────────────────────────

def env_reset(task_id: str) -> Dict:
    r = requests.post(f"{ENV_BASE}/reset", json={"task_id": task_id}, timeout=30)
    r.raise_for_status()
    return r.json()


def env_step(action: Dict) -> Dict:
    r = requests.post(f"{ENV_BASE}/step", json=action, timeout=30)
    r.raise_for_status()
    return r.json()


def env_state() -> Dict:
    r = requests.get(f"{ENV_BASE}/state", timeout=10)
    r.raise_for_status()
    return r.json()


# ─── Agent prompts ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert database reliability engineer and SQL security auditor.
You are working inside an OpenEnv SQL auditing environment.

At each step you must output a JSON action with this schema:
{
  "action_type": one of ["scan_query","rewrite_query","flag_compliance","submit_report","skip"],
  "query_index": integer (0-based index of the query you're acting on),
  "finding": string (description of what you found),
  "severity": one of ["critical","high","medium","low","info"],
  "rewritten_sql": string (improved SQL, if rewriting),
  "reasoning": string (your reasoning),
  "report_summary": string (only for submit_report action)
}

Always output ONLY valid JSON. No markdown, no explanation outside the JSON.

For scan_query: analyze the SQL for injection vulnerabilities, unsafe patterns.
For rewrite_query: provide an optimized/secure version of the SQL.
For flag_compliance: flag PII exposure or GDPR violations.
For submit_report: include executive_summary, critical_findings, compliance_violations, recommendations in report_summary.
"""

def build_user_prompt(obs: Dict, step: int) -> str:
    queries = obs.get("queries", [])
    statuses = obs.get("query_statuses", [])
    findings = obs.get("findings_so_far", [])
    phase = obs.get("phase", "scanning")
    remaining = obs.get("remaining_steps", 10)
    hint = obs.get("hint", "")

    q_list = "\n".join(
        f"  [{i}] ({statuses[i] if i < len(statuses) else 'pending'}): {q[:200]}"
        for i, q in enumerate(queries)
    )
    f_list = json.dumps(findings[-5:], indent=2) if findings else "none"

    return f"""Step {step} | Phase: {phase} | Remaining steps: {remaining}
Hint: {hint}

QUERIES TO AUDIT:
{q_list}

FINDINGS SO FAR (last 5):
{f_list}

Choose your next action. If you've scanned all queries and remaining steps < 5, submit_report.
Output JSON action only."""


# ─── Agent loop ───────────────────────────────────────────────────────────────

def run_agent(task_id: str, deadline: Optional[float] = None) -> Dict[str, Any]:
    obs = env_reset(task_id)
    total_reward = 0.0
    steps_taken = 0
    actions_log: List[Dict[str, Any]] = []
    max_steps = obs.get("max_steps", 30)

    for step in range(1, max_steps + 1):
        if deadline is not None and time.monotonic() >= deadline:
            print(
                f"[STEP] task_id={task_id} step={step} error=TIME_BUDGET_EXCEEDED reward=0.0 done=false",
                flush=True,
            )
            break

        user_msg = build_user_prompt(obs, step)

        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0,
                max_tokens=800,
            )
            raw = response.choices[0].message.content.strip()
        except Exception as e:
            print(
                f"[STEP] task_id={task_id} step={step} error=LLM_CALL_FAILED detail={e} reward=0.0 done=false",
                flush=True,
            )
            break

        try:
            clean = raw.replace("```json", "").replace("```", "").strip()
            action_dict = json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    action_dict = json.loads(match.group())
                except Exception:
                    action_dict = {"action_type": "skip"}
            else:
                action_dict = {"action_type": "skip"}

        try:
            result = env_step(action_dict)
        except Exception as e:
            print(
                f"[STEP] task_id={task_id} step={step} error=ENV_STEP_FAILED detail={e} reward=0.0 done=false",
                flush=True,
            )
            break

        reward = result.get("reward", {}).get("value", 0.0)
        done = result.get("done", False)
        obs = result.get("observation", obs)
        steps_taken = step

        total_reward += reward
        actions_log.append({
            "step": step,
            "action_type": action_dict.get("action_type"),
            "query_index": action_dict.get("query_index"),
            "reward": reward,
        })

        print(
            f"[STEP] task_id={task_id} step={step} action_type={action_dict.get('action_type')} "
            f"reward={round(reward, 4)} done={done}",
            flush=True,
        )

        if done:
            break

    try:
        final_state = env_state()
        final_score = final_state.get("episode_reward", total_reward)
    except Exception:
        final_score = total_reward

    return {
        "task_id": task_id,
        "steps_taken": steps_taken,
        "final_score": round(final_score, 4),
        "total_reward": round(total_reward, 4),
        "actions": actions_log,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    if not HF_TOKEN:
        print("[FATAL] HF_TOKEN is required for the OpenAI client.", file=sys.stderr)
        return 1
    if not ENV_BASE:
        print(
            "[FATAL] Set ENV_BASE_URL (or OPENENV_BASE_URL) to the OpenEnv HTTP base URL.",
            file=sys.stderr,
        )
        return 1

    deadline = time.monotonic() + INFERENCE_MAX_SECONDS
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(
        f"[START] event=GLOBAL_START model={MODEL_NAME} api_base={API_BASE_URL} timestamp={timestamp}",
        flush=True,
    )

    results: Dict[str, Any] = {}
    for task_id in TASKS:
        if time.monotonic() >= deadline:
            print(f"[STEP] task_id={task_id} step=0 error=TIME_BUDGET_EXCEEDED reward=0.0 done=false", flush=True)
            results[task_id] = {
                "task_id": task_id,
                "steps_taken": 0,
                "final_score": 0.0,
                "total_reward": 0.0,
                "actions": [],
            }
            print(f"[END] task_id={task_id} score=0.0 steps=0 elapsed_seconds=0.0", flush=True)
            continue

        print(f"[START] event=TASK_START task_id={task_id}", flush=True)
        t0 = time.time()
        result = run_agent(task_id, deadline=deadline)
        elapsed = round(time.time() - t0, 2)
        results[task_id] = result

        print(
            f"[END] task_id={task_id} score={result['final_score']} steps={result['steps_taken']} "
            f"elapsed_seconds={elapsed}",
            flush=True,
        )

    scores = [r["final_score"] for r in results.values()]
    mean_score = round(sum(scores) / len(scores), 4) if scores else 0.0

    summary_str = " ".join([f"{tid}={res['final_score']}" for tid, res in results.items()])
    print(f"[END] event=SUMMARY mean_score={mean_score} {summary_str}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
