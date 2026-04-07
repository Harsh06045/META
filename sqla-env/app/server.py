"""
SQLAudit-Env: FastAPI server exposing the OpenEnv HTTP API.
"""
from __future__ import annotations
import os
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

@app.get("/health")
def health():
    return {"status": "ok", "env": "sqla-env", "version": "1.0.0"}

@app.get("/tasks")
def list_tasks():
    return {tid: {"id": td["id"], "name": td["name"], "difficulty": td["difficulty"]} for tid, td in TASKS.items()}

@app.post("/reset", response_model=Observation)
def reset(req: ResetRequest):
    try:
        return _env.reset(task_id=req.task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/step", response_model=StepResult)
def step(action: Action):
    try:
        return _env.step(action)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/state", response_model=EnvironmentState)
def state():
    return _env.state()

@app.get("/", response_class=HTMLResponse)
def index():
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>SQLAudit-Env | Mission Control</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --g1: #7c3aed;
  --g2: #2563eb;
  --g3: #06b6d4;
  --g4: #10b981;
  --g5: #f59e0b;
  --g6: #ef4444;
  --bg-dark: #0a0a1a;
  --bg-card: rgba(255,255,255,0.04);
  --bg-glass: rgba(255,255,255,0.06);
  --border-glass: rgba(255,255,255,0.1);
  --text: #f0f4ff;
  --muted: #8892b0;
  --radius: 20px;
}

html, body {
  height: 100%;
  width: 100%;
}

body {
  background: var(--bg-dark);
  color: var(--text);
  font-family: 'Inter', sans-serif;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
}

/* ═══════════════════════════════════
   ANIMATED BACKGROUND
═══════════════════════════════════ */
.aurora {
  position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
}
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.35;
  animation: drift 12s ease-in-out infinite;
}
.orb-1 { width: 600px; height: 600px; background: radial-gradient(circle, #7c3aed, transparent 70%); top: -200px; left: -150px; animation-delay: 0s; }
.orb-2 { width: 500px; height: 500px; background: radial-gradient(circle, #2563eb, transparent 70%); top: -100px; right: -100px; animation-delay: -4s; }
.orb-3 { width: 450px; height: 450px; background: radial-gradient(circle, #06b6d4, transparent 70%); bottom: -150px; left: 30%; animation-delay: -8s; }
.orb-4 { width: 350px; height: 350px; background: radial-gradient(circle, #10b981, transparent 70%); bottom: -100px; right: 10%; animation-delay: -2s; }
@keyframes drift {
  0%,100% { transform: translate(0,0) scale(1); }
  33%      { transform: translate(30px,-30px) scale(1.05); }
  66%      { transform: translate(-20px,20px) scale(0.97); }
}

.noise {
  position: fixed; inset: 0; z-index: 1; pointer-events: none; opacity: 0.04;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
}

.grid-overlay {
  position: fixed; inset: 0; z-index: 1; pointer-events: none;
  background-image: linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 50px 50px;
}

/* ═══════════════════════════════════
   GRADIENT UTILITIES
═══════════════════════════════════ */
.grad-text-purple { background: linear-gradient(135deg, #a78bfa, #60a5fa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.grad-text-cyan   { background: linear-gradient(135deg, #67e8f9, #34d399); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.grad-text-amber  { background: linear-gradient(135deg, #fbbf24, #f87171); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.grad-text-main   { background: linear-gradient(135deg, #e879f9, #818cf8, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }

/* ═══════════════════════════════════
   GLASS CARDS
═══════════════════════════════════ */
.glass {
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-glass);
  border-radius: var(--radius);
}
.glass-dark {
  background: rgba(10,10,30,0.6);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: var(--radius);
}

/* ═══════════════════════════════════
   HEADER
═══════════════════════════════════ */
header {
  position: relative; z-index: 100;
  padding: 0 32px;
  height: 72px;
  display: flex; justify-content: space-between; align-items: center;
  background: rgba(10,10,26,0.7);
  backdrop-filter: blur(24px);
  border-bottom: 1px solid rgba(255,255,255,0.07);
  flex-shrink: 0;
}

.logo-area { display: flex; align-items: center; gap: 14px; }
.logo-badge {
  width: 44px; height: 44px; border-radius: 14px;
  background: linear-gradient(135deg, #7c3aed, #2563eb, #06b6d4);
  display: grid; place-items: center; font-size: 1.3rem;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.15), 0 8px 32px rgba(124,58,237,0.5);
  animation: logoPulse 3s ease-in-out infinite;
}
@keyframes logoPulse {
  0%,100% { box-shadow: 0 0 0 1px rgba(255,255,255,0.15), 0 8px 32px rgba(124,58,237,0.5); }
  50%      { box-shadow: 0 0 0 1px rgba(255,255,255,0.25), 0 8px 48px rgba(124,58,237,0.8); }
}
.logo-name { font-size: 1.5rem; font-weight: 800; letter-spacing: -1px; }
.logo-sub { font-size: 0.6rem; color: var(--muted); font-family: 'JetBrains Mono', monospace; letter-spacing: 3px; text-transform: uppercase; margin-top: 2px; }

.header-center { display: flex; align-items: center; gap: 10px; }
.task-pill {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px; padding: 8px 4px 8px 14px;
  display: flex; align-items: center; gap: 8px;
  position: relative;
}
.task-pill select {
  background: transparent; border: none; color: var(--text);
  font-family: 'Inter', sans-serif; font-size: 0.85rem; font-weight: 600;
  cursor: pointer; outline: none; padding-right: 10px;
}
.task-pill select option { background: #1a1a3a; }

.btn-reset {
  padding: 10px 22px; border-radius: 12px; border: none; cursor: pointer;
  background: linear-gradient(135deg, #7c3aed, #2563eb);
  color: #fff; font-weight: 700; font-size: 0.85rem;
  box-shadow: 0 4px 20px rgba(124,58,237,0.4);
  transition: all 0.2s;
  white-space: nowrap;
}
.btn-reset:hover { transform: translateY(-1px); box-shadow: 0 8px 30px rgba(124,58,237,0.6); }

.status-badge {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 16px; border-radius: 12px;
  background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.25);
  font-size: 0.72rem; font-weight: 700; color: #34d399;
  font-family: 'JetBrains Mono', monospace; letter-spacing: 1px;
}
.dot { width: 8px; height: 8px; border-radius: 50%; background: #10b981; animation: breathe 2s ease-in-out infinite; }
@keyframes breathe { 0%,100% { opacity:1; transform:scale(1); } 50% { opacity:0.5; transform:scale(0.85); } }

/* ═══════════════════════════════════
   MAIN LAYOUT
═══════════════════════════════════ */
main {
  flex: 1; display: grid;
  grid-template-columns: 290px 1fr 370px;
  gap: 1px;
  overflow: hidden;
  position: relative; z-index: 10;
  background: rgba(255,255,255,0.03);
}

.panel {
  display: flex; flex-direction: column;
  overflow: hidden;
  background: rgba(10,10,26,0.65);
  backdrop-filter: blur(12px);
}

.panel-head {
  padding: 18px 24px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  display: flex; justify-content: space-between; align-items: center;
  flex-shrink: 0;
  background: rgba(255,255,255,0.02);
}
.panel-head-label {
  font-size: 0.62rem; font-weight: 800; letter-spacing: 3px; text-transform: uppercase;
  display: flex; align-items: center; gap: 10px;
}
.panel-head-label .indicator {
  width: 3px; height: 16px; border-radius: 2px;
  background: linear-gradient(180deg, #7c3aed, #06b6d4);
  display: inline-block;
}
.panel-scroll { flex: 1; overflow-y: auto; padding: 20px; }
.panel-scroll::-webkit-scrollbar { width: 3px; }
.panel-scroll::-webkit-scrollbar-thumb { background: linear-gradient(180deg, #7c3aed44, #06b6d444); border-radius: 2px; }

/* ═══════════════════════════════════
   STAT CARDS
═══════════════════════════════════ */
.stat-grid { display: grid; gap: 12px; margin-bottom: 16px; }
.stat-col-2 { grid-template-columns: 1fr 1fr; }
.stat-col-1 { grid-template-columns: 1fr; }

.stat-card {
  border-radius: 16px; padding: 16px; position: relative; overflow: hidden;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07);
  transition: transform 0.2s, box-shadow 0.2s;
}
.stat-card:hover { transform: translateY(-2px); }
.stat-card-glow {
  position: absolute; inset: 0; border-radius: 16px; opacity: 0;
  transition: opacity 0.3s;
}
.stat-card:hover .stat-card-glow { opacity: 1; }

.stat-card.purple { border-color: rgba(124,58,237,0.25); }
.stat-card.purple:hover { box-shadow: 0 8px 32px rgba(124,58,237,0.25); }
.stat-card.purple .stat-card-glow { background: radial-gradient(circle at 50% 0%, rgba(124,58,237,0.1), transparent 70%); }

.stat-card.cyan { border-color: rgba(6,182,212,0.25); }
.stat-card.cyan:hover { box-shadow: 0 8px 32px rgba(6,182,212,0.25); }
.stat-card.cyan .stat-card-glow { background: radial-gradient(circle at 50% 0%, rgba(6,182,212,0.1), transparent 70%); }

.stat-card.green { border-color: rgba(16,185,129,0.25); }
.stat-card.green:hover { box-shadow: 0 8px 32px rgba(16,185,129,0.2); }
.stat-card.green .stat-card-glow { background: radial-gradient(circle at 50% 0%, rgba(16,185,129,0.1), transparent 70%); }

.stat-card.amber { border-color: rgba(245,158,11,0.25); }
.stat-card.amber:hover { box-shadow: 0 8px 32px rgba(245,158,11,0.2); }
.stat-card.amber .stat-card-glow { background: radial-gradient(circle at 50% 0%, rgba(245,158,11,0.1), transparent 70%); }

.stat-label { font-size: 0.6rem; letter-spacing: 2px; text-transform: uppercase; color: var(--muted); margin-bottom: 6px; font-weight: 600; }
.stat-value { font-family: 'JetBrains Mono', monospace; font-weight: 800; line-height: 1; }
.stat-value.xl { font-size: 2rem; }
.stat-value.lg { font-size: 1.3rem; }
.stat-icon { position: absolute; right: 12px; top: 12px; font-size: 1.4rem; opacity: 0.2; }

/* ═══════════════════════════════════
   CHART
═══════════════════════════════════ */
.chart-card {
  border-radius: 16px; padding: 18px; margin-bottom: 14px;
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
  position: relative; overflow: hidden;
}
.chart-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(124,58,237,0.6), rgba(6,182,212,0.6), transparent);
}
.chart-label { font-size: 0.6rem; letter-spacing: 2px; text-transform: uppercase; color: var(--muted); margin-bottom: 14px; font-weight: 600; }
.chart-canvas-wrap { height: 110px; position: relative; }

/* ═══════════════════════════════════
   SCHEMA
═══════════════════════════════════ */
.schema-card {
  border-radius: 16px; padding: 16px; margin-bottom: 14px;
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
}
.schema-header { font-size: 0.6rem; letter-spacing: 2px; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; font-weight: 600; }
.schema-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 9px 0; border-bottom: 1px solid rgba(255,255,255,0.04);
  font-size: 0.8rem;
}
.schema-row:last-child { border: none; }
.schema-name { font-family: 'JetBrains Mono', monospace; font-weight: 600; font-size: 0.75rem; }
.badges { display: flex; gap: 5px; }
.badge {
  font-size: 0.55rem; padding: 3px 8px; border-radius: 6px; font-weight: 800;
  letter-spacing: 0.8px; text-transform: uppercase;
}
.badge-pii   { background: linear-gradient(135deg, rgba(239,68,68,0.2), rgba(245,158,11,0.2)); color: #fca5a5; border: 1px solid rgba(239,68,68,0.3); }
.badge-rows  { background: rgba(255,255,255,0.05); color: var(--muted); border: 1px solid rgba(255,255,255,0.08); }
.badge-done  { background: linear-gradient(135deg, rgba(16,185,129,0.15), rgba(6,182,212,0.15)); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.3); }
.badge-pend  { background: rgba(255,255,255,0.04); color: #64748b; border: 1px solid rgba(255,255,255,0.06); }

/* ═══════════════════════════════════
   PHASE BAR
═══════════════════════════════════ */
.phase-track { display: flex; gap: 6px; }
.phase-pip {
  flex: 1; text-align: center; padding: 5px 4px; border-radius: 8px;
  font-size: 0.55rem; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase;
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
  color: #475569; transition: all 0.3s;
}
.phase-pip.active {
  background: linear-gradient(135deg, rgba(124,58,237,0.3), rgba(6,182,212,0.3));
  border-color: rgba(124,58,237,0.5); color: #a78bfa;
  box-shadow: 0 0 12px rgba(124,58,237,0.3);
}
.phase-pip.done {
  background: rgba(16,185,129,0.07); border-color: rgba(16,185,129,0.2); color: #4ade80;
}

/* ═══════════════════════════════════
   QUERY CARDS
═══════════════════════════════════ */
.query-card {
  border-radius: 16px; margin-bottom: 12px; overflow: hidden;
  cursor: pointer; transition: all 0.25s;
  border: 1px solid rgba(255,255,255,0.07);
  background: rgba(255,255,255,0.03);
}
.query-card:hover {
  transform: translateY(-2px);
  border-color: rgba(99,102,241,0.4);
  box-shadow: 0 8px 32px rgba(99,102,241,0.15);
}
.query-card.active {
  border-color: transparent;
  background: linear-gradient(rgba(10,10,26,0.9), rgba(10,10,26,0.9)) padding-box,
              linear-gradient(135deg, #7c3aed, #2563eb, #06b6d4) border-box;
  box-shadow: 0 0 0 1px rgba(124,58,237,0.1), 0 12px 40px rgba(124,58,237,0.25);
}
.query-card.done {
  border-color: rgba(16,185,129,0.2);
  background: rgba(16,185,129,0.03);
}
.query-card-top {
  padding: 11px 16px; border-bottom: 1px solid rgba(255,255,255,0.05);
  display: flex; justify-content: space-between; align-items: center;
}
.query-id { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; font-weight: 700; color: var(--muted); }
.query-body { padding: 14px 16px; font-family: 'JetBrains Mono', monospace; font-size: 0.76rem; color: #94a3b8; line-height: 1.65; }

/* ═══════════════════════════════════
   CONTROLLER FORM
═══════════════════════════════════ */
.ctrl-section { margin-bottom: 16px; }
.ctrl-label {
  display: block; font-size: 0.6rem; font-weight: 800; letter-spacing: 2px;
  text-transform: uppercase; color: var(--muted); margin-bottom: 8px;
}
.ctrl-input {
  width: 100%; padding: 12px 14px; border-radius: 12px; font-size: 0.88rem;
  font-family: 'Inter', sans-serif;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.09);
  color: var(--text);
  transition: all 0.2s;
}
.ctrl-input:focus {
  outline: none;
  border-color: transparent;
  box-shadow: 0 0 0 2px #7c3aed;
  background: rgba(124,58,237,0.08);
}
.ctrl-input.mono { font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #67e8f9; }
.ctrl-input option { background: #1a1a3a; }
textarea.ctrl-input { resize: none; height: 80px; line-height: 1.55; }

.exec-wrap { position: relative; margin-top: 4px; }
.exec-btn {
  width: 100%; padding: 17px; border: none; border-radius: 14px; cursor: pointer;
  font-size: 0.95rem; font-weight: 800; letter-spacing: 0.5px; color: #fff;
  background: linear-gradient(135deg, #7c3aed 0%, #2563eb 50%, #06b6d4 100%);
  background-size: 200% 200%;
  animation: gradShift 4s ease infinite;
  box-shadow: 0 6px 30px rgba(124,58,237,0.5), inset 0 1px 0 rgba(255,255,255,0.15);
  display: flex; align-items: center; justify-content: center; gap: 10px;
  transition: transform 0.2s, box-shadow 0.2s;
}
.exec-btn:hover { transform: translateY(-2px); box-shadow: 0 12px 40px rgba(124,58,237,0.7); }
.exec-btn:active { transform: translateY(0); }
@keyframes gradShift {
  0%   { background-position: 0% 50%; }
  50%  { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.divider { height: 1px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent); margin: 16px 0; }

.response-card {
  border-radius: 14px; padding: 14px;
  background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
}
.response-label { font-size: 0.58rem; letter-spacing: 2px; color: var(--muted); text-transform: uppercase; font-weight: 700; margin-bottom: 10px; }
.response-val { font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #64748b; line-height: 1.5; }

/* ═══════════════════════════════════
   TERMINAL
═══════════════════════════════════ */
.terminal {
  flex-shrink: 0; height: 175px; display: flex; flex-direction: column;
  background: rgba(5,5,15,0.9);
  border-top: 1px solid rgba(255,255,255,0.05);
}
.terminal-bar {
  padding: 8px 16px; border-bottom: 1px solid rgba(255,255,255,0.04);
  display: flex; align-items: center; gap: 8px; flex-shrink: 0;
  background: linear-gradient(90deg, rgba(124,58,237,0.05), rgba(6,182,212,0.05));
}
.term-dots { display: flex; gap: 5px; }
.term-dot { width: 9px; height: 9px; border-radius: 50%; }
.term-title { font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; color: #475569; letter-spacing: 2px; margin-left: 6px; }
.terminal-stream { flex: 1; overflow-y: auto; padding: 10px 16px; }
.terminal-stream::-webkit-scrollbar { width: 2px; }
.terminal-stream::-webkit-scrollbar-thumb { background: rgba(124,58,237,0.3); }
.log-row { display: flex; gap: 12px; margin-bottom: 3px; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; line-height: 1.5; }
.log-ts   { color: #1e293b; flex-shrink: 0; width: 80px; }
.log-tag  { flex-shrink: 0; width: 52px; font-weight: 700; }
.log-tag.sys  { color: #818cf8; }
.log-tag.step { color: #34d399; }
.log-tag.warn { color: #fbbf24; }
.log-tag.err  { color: #f87171; }
.log-text { color: #334155; }

/* ═══════════════════════════════════
   TOAST
═══════════════════════════════════ */
#toast {
  position: fixed; bottom: 30px; left: 50%;
  transform: translateX(-50%) translateY(100px);
  padding: 13px 28px; border-radius: 14px; z-index: 9999;
  font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; font-weight: 600;
  background: linear-gradient(135deg, rgba(124,58,237,0.9), rgba(37,99,235,0.9));
  border: 1px solid rgba(255,255,255,0.15);
  color: #fff; backdrop-filter: blur(20px);
  box-shadow: 0 16px 48px rgba(124,58,237,0.5);
  transition: transform 0.45s cubic-bezier(0.34,1.56,0.64,1);
}
#toast.show { transform: translateX(-50%) translateY(0); }
</style>
</head>
<body>

<div class="aurora">
  <div class="orb orb-1"></div>
  <div class="orb orb-2"></div>
  <div class="orb orb-3"></div>
  <div class="orb orb-4"></div>
</div>
<div class="noise"></div>
<div class="grid-overlay"></div>

<!-- ═══ HEADER ═══ -->
<header>
  <div class="logo-area">
    <div class="logo-badge">🛡️</div>
    <div>
      <div class="logo-name"><span class="grad-text-main">SQLAudit</span><span style="color:rgba(255,255,255,0.3);font-weight:300;">.env</span></div>
      <div class="logo-sub">OpenEnv · Mission Control · v1.0.0</div>
    </div>
  </div>

  <div class="header-center">
    <div class="task-pill">
      <select id="taskSelect" onchange="resetEnv()">
        <option value="task_easy">⚡ LVL 1 — Security Scan</option>
        <option value="task_medium">🔧 LVL 2 — Performance Audit</option>
        <option value="task_hard">🔥 LVL 3 — Enterprise Pipeline</option>
      </select>
    </div>
    <button class="btn-reset" onclick="resetEnv()">↺ Reset Episode</button>
  </div>

  <div class="status-badge">
    <div class="dot"></div>
    <span>ENV_ACTIVE</span>
    <span style="opacity:0.4;margin:0 4px;">·</span>
    <span id="epLabel" style="color:#475569;">EP_001</span>
  </div>
</header>

<!-- ═══ MAIN ═══ -->
<main>

  <!-- ── COL 1: ANALYTICS ── -->
  <div class="panel">
    <div class="panel-head">
      <div class="panel-head-label">
        <span class="indicator"></span>
        <span class="grad-text-purple">Analytics</span>
      </div>
      <span style="font-size:0.6rem;color:#334155;font-family:monospace;">LIVE</span>
    </div>
    <div class="panel-scroll">

      <div class="stat-grid stat-col-2">
        <div class="stat-card cyan">
          <div class="stat-card-glow"></div>
          <div class="stat-label">Reward</div>
          <div id="rewardVal" class="stat-value xl grad-text-cyan">0.000</div>
          <div class="stat-icon">📈</div>
        </div>
        <div class="stat-card purple">
          <div class="stat-card-glow"></div>
          <div class="stat-label">Steps</div>
          <div id="stepVal" class="stat-value xl grad-text-purple">0/20</div>
          <div class="stat-icon">⏱</div>
        </div>
      </div>

      <div class="stat-grid stat-col-1">
        <div class="stat-card amber">
          <div class="stat-card-glow"></div>
          <div class="stat-label">Active Phase</div>
          <div id="phaseVal" class="stat-value lg grad-text-amber" style="letter-spacing:3px;">INIT</div>
          <div class="stat-icon">🔄</div>
        </div>
      </div>

      <div class="chart-card">
        <div class="chart-label">Reward Trajectory</div>
        <div class="chart-canvas-wrap">
          <canvas id="rewardChart"></canvas>
        </div>
      </div>

      <div class="schema-card">
        <div class="schema-header">Database Schema</div>
        <div id="schemaRows"></div>
      </div>

    </div>
  </div>

  <!-- ── COL 2: WORKLOAD ── -->
  <div class="panel">
    <div class="panel-head">
      <div class="panel-head-label">
        <span class="indicator" style="background:linear-gradient(180deg,#06b6d4,#10b981);"></span>
        <span class="grad-text-cyan">Audit Workload Explorer</span>
      </div>
      <div id="phaseTrack" class="phase-track" style="gap:5px;"></div>
    </div>
    <div id="queryGrid" class="panel-scroll"></div>
    <div class="terminal">
      <div class="terminal-bar">
        <div class="term-dots">
          <div class="term-dot" style="background:#ef4444;"></div>
          <div class="term-dot" style="background:#f59e0b;"></div>
          <div class="term-dot" style="background:#10b981;"></div>
        </div>
        <div class="term-title">KERNEL_TRACE · OENV_LOG_STREAM</div>
      </div>
      <div class="terminal-stream" id="logStream"></div>
    </div>
  </div>

  <!-- ── COL 3: CONTROLLER ── -->
  <div class="panel">
    <div class="panel-head">
      <div class="panel-head-label">
        <span class="indicator" style="background:linear-gradient(180deg,#f59e0b,#ef4444);"></span>
        <span class="grad-text-amber">Operator Controller</span>
      </div>
      <span style="font-size:0.6rem;font-family:monospace;background:linear-gradient(135deg,#34d399,#67e8f9);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">READY</span>
    </div>
    <div class="panel-scroll">

      <div class="ctrl-section">
        <label class="ctrl-label">Audit Action</label>
        <select id="actionType" class="ctrl-input" onchange="onActionChange()">
          <option value="scan_query">🔍  SCAN_QUERY — Detect Vulnerability</option>
          <option value="rewrite_query">✏️  REWRITE_QUERY — Optimize SQL</option>
          <option value="flag_compliance">🔒  FLAG_COMPLIANCE — Privacy Check</option>
          <option value="submit_report">📋  SUBMIT_REPORT — Finalize Audit</option>
        </select>
      </div>

      <div id="idxBox" class="ctrl-section">
        <label class="ctrl-label">Target Query Index</label>
        <input type="number" id="queryIdx" class="ctrl-input" value="0" min="0"/>
      </div>

      <div class="ctrl-section">
        <label class="ctrl-label">Severity</label>
        <select id="severity" class="ctrl-input">
          <option value="info">ℹ️  INFO</option>
          <option value="low">🟡  LOW</option>
          <option value="medium">🟠  MEDIUM</option>
          <option value="high">🔴  HIGH</option>
          <option value="critical" selected>💀  CRITICAL</option>
        </select>
      </div>

      <div class="ctrl-section">
        <label class="ctrl-label">Technical Finding</label>
        <textarea id="findingTxt" class="ctrl-input" placeholder="Describe the vulnerability, performance issue, or PII exposure…"></textarea>
      </div>

      <div id="rewriteBox" class="ctrl-section" style="display:none;">
        <label class="ctrl-label">Rewritten SQL</label>
        <textarea id="sqlTxt" class="ctrl-input mono" placeholder="SELECT id, name FROM users WHERE id = $1"></textarea>
      </div>

      <div class="divider"></div>

      <div class="exec-wrap">
        <button class="exec-btn" id="execBtn" onclick="stepEnv()">
          <span>⚡</span><span>EXECUTE AUDIT STEP</span>
        </button>
      </div>

      <div class="divider"></div>

      <div class="response-card">
        <div class="response-label">Last Step Response</div>
        <div id="lastResp" class="response-val">awaiting first step…</div>
      </div>

    </div>
  </div>

</main>

<div id="toast">✅ Episode Initialized</div>

<script>
let chart, rHist = [0], sLabels = ['0'], ep = 0;
const PHASES = ['scanning','optimizing','compliance','reporting'];

// ── Chart ──────────────────────────────────────────
function initChart() {
  const ctx = document.getElementById('rewardChart').getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 0, 110);
  grad.addColorStop(0, 'rgba(124,58,237,0.5)');
  grad.addColorStop(0.5, 'rgba(6,182,212,0.2)');
  grad.addColorStop(1, 'rgba(16,185,129,0)');
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: sLabels,
      datasets: [{
        data: rHist,
        borderColor: 'rgba(124,58,237,1)',
        backgroundColor: grad,
        borderWidth: 2.5, tension: 0.5, fill: true,
        pointRadius: 3, pointBackgroundColor: '#7c3aed',
        pointBorderColor: '#0a0a1a', pointHoverRadius: 6,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(10,10,26,0.95)',
          borderColor: 'rgba(124,58,237,0.4)', borderWidth: 1,
          titleColor: '#a78bfa', bodyColor: '#94a3b8',
          callbacks: { label: c => ` Reward: ${c.raw.toFixed(4)}` }
        }
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#334155', font: { family:'JetBrains Mono', size:9 } } },
        y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#334155', font: { family:'JetBrains Mono', size:9 } }, min: 0 }
      }
    }
  });
}

// ── Reset ──────────────────────────────────────────
async function resetEnv() {
  const tid = document.getElementById('taskSelect').value;
  try {
    const res = await fetch('/reset', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({task_id:tid}) });
    const d = await res.json();
    ep++;
    document.getElementById('epLabel').textContent = `EP_${String(ep).padStart(3,'0')}`;
    document.getElementById('rewardVal').textContent = '0.000';
    document.getElementById('stepVal').textContent   = `0/${d.max_steps}`;
    document.getElementById('phaseVal').textContent  = d.phase.toUpperCase();
    rHist = [0]; sLabels = ['0'];
    chart.data.labels = sLabels;
    chart.data.datasets[0].data = rHist;
    chart.update('none');
    renderPhase(d.phase);
    renderQueries(d);
    renderSchema(d.schema_info);
    log('SYS', `Episode ${ep} initialized · task=${tid}`);
    toast('✅ Episode Reset');
  } catch(e) { log('ERR', e.message, 'err'); }
}

// ── Step ──────────────────────────────────────────
async function stepEnv() {
  const type = document.getElementById('actionType').value;
  const btn  = document.getElementById('execBtn');
  btn.style.opacity = '0.6';
  btn.innerHTML = '<span>⏳</span><span>Executing…</span>';
  try {
    const payload = {
      action_type: type,
      query_index: parseInt(document.getElementById('queryIdx').value) || 0,
      severity:    document.getElementById('severity').value,
      finding:     document.getElementById('findingTxt').value,
      rewritten_sql: document.getElementById('sqlTxt').value,
      reasoning:   'Manual audit',
      report_summary: type === 'submit_report' ? document.getElementById('findingTxt').value : null
    };
    const res = await fetch('/step', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload) });
    const d   = await res.json();
    const obs = d.observation;
    rHist.push(obs.score_so_far);
    sLabels.push(obs.step.toString());
    chart.data.labels = sLabels;
    chart.data.datasets[0].data = rHist;
    chart.update();
    document.getElementById('rewardVal').textContent = obs.score_so_far.toFixed(3);
    document.getElementById('stepVal').textContent   = `${obs.step}/${obs.max_steps}`;
    document.getElementById('phaseVal').textContent  = obs.phase.toUpperCase();
    const pos = d.reward.value >= 0;
    document.getElementById('lastResp').innerHTML =
      `<span style="color:${pos?'#34d399':'#f87171'};font-size:1rem;font-weight:800;">${pos?'+':''}${d.reward.value.toFixed(4)}</span>&nbsp;&nbsp;<span style="color:#334155">step ${obs.step} · ${d.done?'<span style="color:#f87171">DONE</span>':'running…'}</span>`;
    renderPhase(obs.phase);
    renderQueries(obs);
    log('STEP', `[${type}] idx=${payload.query_index} → ${d.reward.value >= 0 ? '+':''}${d.reward.value.toFixed(4)}`, pos?'step':'warn');
    if (d.done) log('HALT', 'Episode terminal — grader finalized.', 'err');
  } catch(e) { log('ERR', e.message, 'err'); }
  finally {
    btn.style.opacity = '1';
    btn.innerHTML = '<span>⚡</span><span>EXECUTE AUDIT STEP</span>';
  }
}

// ── Renders ──────────────────────────────────────
function renderPhase(cur) {
  document.getElementById('phaseVal').textContent = cur.toUpperCase();
  const done = PHASES.slice(0, PHASES.indexOf(cur));
  document.getElementById('phaseTrack').innerHTML = PHASES.map(p =>
    `<div class="phase-pip ${p===cur?'active':done.includes(p)?'done':''}">${p.substring(0,4).toUpperCase()}</div>`
  ).join('');
}

function renderQueries(obs) {
  const sel = parseInt(document.getElementById('queryIdx').value) || 0;
  document.getElementById('queryGrid').innerHTML = obs.queries.map((q,i) => {
    const st = obs.query_statuses[i];
    return `<div class="query-card ${i===sel?'active':''} ${st!=='pending'?'done':''}" onclick="pickQuery(${i})">
      <div class="query-card-top">
        <span class="query-id">UNIT_${String(i).padStart(2,'0')}</span>
        <span class="badge ${st!=='pending'?'badge-done':'badge-pend'}">${st.toUpperCase()}</span>
      </div>
      <div class="query-body">${escHtml(q)}</div>
    </div>`;
  }).join('');
}

function renderSchema(schema) {
  if (!schema) return;
  document.getElementById('schemaRows').innerHTML = Object.entries(schema).map(([name, tbl]) => {
    const pii = tbl.columns && tbl.columns.some(c => c.pii==='YES');
    return `<div class="schema-row">
      <span class="schema-name">${name}</span>
      <div class="badges">
        ${pii ? '<span class="badge badge-pii">PII</span>' : ''}
        <span class="badge badge-rows">${tbl.row_estimate ?? '—'} rows</span>
      </div>
    </div>`;
  }).join('');
}

function pickQuery(i) {
  document.getElementById('queryIdx').value = i;
  document.querySelectorAll('.query-card').forEach((c,idx) => {
    c.classList.toggle('active', idx === i);
  });
}

function onActionChange() {
  const v = document.getElementById('actionType').value;
  document.getElementById('rewriteBox').style.display = v==='rewrite_query' ? 'block' : 'none';
  document.getElementById('idxBox').style.display     = v==='submit_report'  ? 'none'  : 'block';
}

function log(tag, msg, cls='sys') {
  const el = document.getElementById('logStream');
  const ts  = new Date().toLocaleTimeString('en-GB');
  el.innerHTML += `<div class="log-row"><span class="log-ts">[${ts}]</span><span class="log-tag ${cls}">${tag}</span><span class="log-text">${msg}</span></div>`;
  el.scrollTop = el.scrollHeight;
}

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}

function escHtml(s) {
  return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

window.onload = () => { initChart(); resetEnv(); };
</script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("app.server:app", host="0.0.0.0", port=port, reload=False)
