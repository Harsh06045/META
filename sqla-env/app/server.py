"""SQLAudit-Env: FastAPI Server"""
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
def health(): return {"status": "ok", "version": "1.0.0"}

@app.get("/tasks")
def list_tasks(): return {tid: {"id": td["id"], "name": td["name"], "difficulty": td["difficulty"]} for tid, td in TASKS.items()}

@app.post("/reset", response_model=Observation)
def reset(req: ResetRequest):
    try: return _env.reset(task_id=req.task_id)
    except ValueError as e: raise HTTPException(400, str(e))

@app.post("/step", response_model=StepResult)
def step(action: Action):
    try: return _env.step(action)
    except RuntimeError as e: raise HTTPException(400, str(e))

@app.get("/state", response_model=EnvironmentState)
def state(): return _env.state()

@app.get("/", response_class=HTMLResponse)
def index():
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SQLAudit — Mission Control</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --sidebar-w:220px;
  --topbar-h:52px;
  --statusbar-h:28px;
  --bg:#0f1117;
  --bg2:#161b27;
  --bg3:#1c2333;
  --bg4:#232b3e;
  --border:#2a3349;
  --accent:#5b6af0;
  --accent2:#38bdf8;
  --green:#22c55e;
  --red:#f43f5e;
  --amber:#f59e0b;
  --text:#e2e8f0;
  --text2:#94a3b8;
  --text3:#475569;
}
html,body{height:100%;background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;font-size:13px;overflow:hidden}

/* ── APP SHELL ── */
.app{display:grid;grid-template-rows:var(--topbar-h) 1fr var(--statusbar-h);height:100vh}

/* ── TOPBAR ── */
.topbar{
  display:flex;align-items:center;gap:0;
  background:var(--bg2);border-bottom:1px solid var(--border);
  padding:0 20px;z-index:100;
}
.topbar-brand{display:flex;align-items:center;gap:8px;margin-right:24px}
.brand-icon{width:26px;height:26px;border-radius:7px;background:linear-gradient(135deg,#5b6af0,#38bdf8);display:grid;place-items:center;font-size:.85rem}
.brand-name{font-weight:700;font-size:.9rem;letter-spacing:-.3px}
.topbar-tabs{display:flex;align-items:stretch;height:100%}
.tab{
  display:flex;align-items:center;gap:6px;padding:0 16px;
  border-bottom:2px solid transparent;cursor:pointer;
  color:var(--text2);font-weight:500;transition:all .15s;white-space:nowrap;
}
.tab:hover{color:var(--text);background:rgba(255,255,255,.03)}
.tab.active{color:var(--accent);border-bottom-color:var(--accent);background:rgba(91,106,240,.06)}
.tab-ico{font-size:.9rem}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:8px}
.task-select{
  background:var(--bg3);border:1px solid var(--border);
  color:var(--text);padding:5px 10px;border-radius:7px;
  font-family:'Inter',sans-serif;font-size:.78rem;cursor:pointer;outline:none;
}
.task-select option{background:var(--bg2)}
.btn{
  display:flex;align-items:center;gap:6px;padding:7px 16px;
  border-radius:9px;border:none;cursor:pointer;font-family:'Inter',sans-serif;
  font-size:.78rem;font-weight:600;
  transition:all .18s cubic-bezier(.34,1,.64,1);
  position:relative;overflow:hidden;user-select:none;
}
.btn:active{transform:scale(.96)!important}
.btn-primary{
  background:linear-gradient(135deg,var(--accent),#4338ca);
  color:#fff;box-shadow:0 2px 12px rgba(91,106,240,.45);
}
.btn-primary:hover{background:linear-gradient(135deg,#6b7af5,#5046e5);box-shadow:0 6px 20px rgba(91,106,240,.6);transform:translateY(-2px)}
.btn-danger{background:linear-gradient(135deg,#ef4444,#b91c1c);color:#fff;box-shadow:0 2px 12px rgba(239,68,68,.35)}
.btn-danger:hover{box-shadow:0 6px 20px rgba(239,68,68,.5);transform:translateY(-2px)}
.btn-success{background:linear-gradient(135deg,#22c55e,#15803d);color:#fff;box-shadow:0 2px 12px rgba(34,197,94,.35)}
.btn-success:hover{box-shadow:0 6px 20px rgba(34,197,94,.5);transform:translateY(-2px)}
.btn-ghost{
  background:rgba(255,255,255,.05);color:var(--text2);
  border:1px solid var(--border);backdrop-filter:blur(4px);
}
.btn-ghost:hover{background:rgba(255,255,255,.1);color:var(--text);border-color:rgba(255,255,255,.15);transform:translateY(-1px)}
/* ripple */
.ripple{position:absolute;border-radius:50%;transform:scale(0);background:rgba(255,255,255,.25);animation:rippleAnim .5s linear;pointer-events:none}
@keyframes rippleAnim{to{transform:scale(4);opacity:0}}
.badge-live{
  display:flex;align-items:center;gap:6px;padding:5px 12px;border-radius:20px;
  background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.2);
  color:#4ade80;font-size:.7rem;font-weight:700;letter-spacing:.5px;
  cursor:default;
}
.live-dot{width:7px;height:7px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 0 rgba(34,197,94,.5);animation:livePulse 2s ease infinite}
@keyframes livePulse{0%,100%{box-shadow:0 0 0 0 rgba(34,197,94,.5)}70%{box-shadow:0 0 0 6px rgba(34,197,94,0)}}

/* ── BODY ── */
.app-body{display:grid;grid-template-columns:var(--sidebar-w) 1fr 340px;overflow:hidden;background:var(--border);gap:1px}

/* ── SIDEBAR ── */
.sidebar{background:var(--bg2);display:flex;flex-direction:column;overflow:hidden}
.sidebar-section{padding:16px 12px 8px}
.sidebar-label{font-size:.6rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--text3);padding:0 8px;margin-bottom:6px}
.nav-item{
  display:flex;align-items:center;gap:10px;padding:8px 12px;
  border-radius:9px;cursor:pointer;color:var(--text2);
  font-weight:500;margin-bottom:2px;
  transition:all .2s cubic-bezier(.34,1,.64,1);
  position:relative;overflow:hidden;
}
.nav-item::before{
  content:'';position:absolute;left:0;top:0;bottom:0;width:3px;
  background:var(--accent);border-radius:0 2px 2px 0;
  transform:scaleY(0);transition:transform .2s cubic-bezier(.34,1.56,.64,1);
}
.nav-item:hover{background:rgba(255,255,255,.05);color:var(--text);transform:translateX(2px)}
.nav-item.active{
  background:rgba(91,106,240,.12);color:var(--accent);font-weight:600;
  box-shadow:inset 0 0 0 1px rgba(91,106,240,.15);
}
.nav-item.active::before{transform:scaleY(1)}
.nav-ico{font-size:1rem;width:22px;text-align:center;transition:transform .2s}
.nav-item:hover .nav-ico{transform:scale(1.15)}
.sidebar-divider{height:1px;background:var(--border);margin:10px 12px}
.sidebar-footer{margin-top:auto;padding:12px}
.episode-card{
  background:var(--bg3);border:1px solid var(--border);border-radius:12px;padding:14px;
  transition:border-color .2s;
}
.episode-card:hover{border-color:rgba(91,106,240,.3)}
.ep-label{font-size:.6rem;color:var(--text3);letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;font-weight:700}
.ep-stats{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px}
.ep-stat{text-align:center;background:rgba(255,255,255,.03);border-radius:8px;padding:8px 4px;border:1px solid rgba(255,255,255,.05)}
.ep-stat-val{font-family:'JetBrains Mono',monospace;font-size:1.15rem;font-weight:800}
.ep-stat-key{font-size:.58rem;color:var(--text3);margin-top:3px;letter-spacing:.5px;text-transform:uppercase}
.reward-val{color:#34d399}
.steps-val{color:#a78bfa}
.phase-pill{
  text-align:center;padding:5px;
  border-radius:7px;font-size:.6rem;font-weight:800;letter-spacing:2px;text-transform:uppercase;
  background:rgba(91,106,240,.1);color:var(--accent);border:1px solid rgba(91,106,240,.2);
  transition:all .3s;
}

/* ── MAIN CONTENT ── */
.main{background:var(--bg);display:flex;flex-direction:column;overflow:hidden}
.main-toolbar{
  display:flex;align-items:center;gap:8px;padding:10px 16px;
  border-bottom:1px solid var(--border);background:var(--bg2);flex-shrink:0;
}
.breadcrumb{display:flex;align-items:center;gap:6px;color:var(--text3);font-size:.8rem}
.breadcrumb span{color:var(--text2);font-weight:500}
.phase-track{display:flex;gap:6px;margin-left:auto}
.pip{
  padding:3px 10px;border-radius:6px;font-size:.6rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;
  background:rgba(255,255,255,.04);border:1px solid var(--border);color:var(--text3);transition:all .3s;
}
.pip.active{background:rgba(91,106,240,.15);border-color:rgba(91,106,240,.4);color:var(--accent)}
.pip.done{background:rgba(34,197,94,.08);border-color:rgba(34,197,94,.25);color:#4ade80}
.queries-scroll{flex:1;overflow-y:auto;padding:16px}
.queries-scroll::-webkit-scrollbar{width:4px}
.queries-scroll::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
.query-card{
  background:var(--bg2);border:1px solid var(--border);border-radius:12px;
  margin-bottom:10px;overflow:hidden;cursor:pointer;
  transition:all .25s cubic-bezier(.34,1,.64,1);
  position:relative;
}
.query-card::after{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;border-radius:0;background:linear-gradient(180deg,var(--accent),#4338ca);opacity:0;transition:opacity .2s}
.query-card:hover{border-color:rgba(91,106,240,.35);box-shadow:0 6px 20px rgba(91,106,240,.12);transform:translateY(-2px)}
.query-card:hover::after{opacity:1}
.query-card.active{border-color:var(--accent);background:rgba(91,106,240,.07);box-shadow:0 0 0 1px rgba(91,106,240,.2),0 6px 24px rgba(91,106,240,.18)}
.query-card.active::after{opacity:1}
.query-card.done{border-color:rgba(34,197,94,.2);background:rgba(34,197,94,.02)}
.query-card.done::after{background:linear-gradient(180deg,#22c55e,#15803d);opacity:.6}
.qc-head{padding:10px 14px 10px 18px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.qc-id{font-family:'JetBrains Mono',monospace;font-size:.68rem;font-weight:700;color:var(--text3)}
.badge{font-size:.58rem;padding:2px 8px;border-radius:5px;font-weight:700;letter-spacing:.5px;text-transform:uppercase}
.b-pend{background:rgba(255,255,255,.05);color:var(--text3);border:1px solid var(--border)}
.b-done{background:rgba(34,197,94,.1);color:#4ade80;border:1px solid rgba(34,197,94,.3)}
.b-pii{background:rgba(244,63,94,.1);color:#fca5a5;border:1px solid rgba(244,63,94,.3)}
.qc-body{padding:12px 14px 12px 18px;font-family:'JetBrains Mono',monospace;font-size:.76rem;color:#64748b;line-height:1.65}

/* ── RIGHT PANEL ── */
.right-panel{background:var(--bg2);display:flex;flex-direction:column;overflow:hidden}
.rp-head{padding:14px 16px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;flex-shrink:0}
.rp-title{font-weight:700;font-size:.82rem;display:flex;align-items:center;gap:8px}
.rp-title-ico{font-size:1rem}
.rp-scroll{flex:1;overflow-y:auto;padding:16px}
.rp-scroll::-webkit-scrollbar{width:3px}
.rp-scroll::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
.field{margin-bottom:14px}
.field-label{font-size:.62rem;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--text3);display:block;margin-bottom:6px}
.field-in{
  width:100%;padding:9px 11px;border-radius:9px;
  background:var(--bg3);border:1px solid var(--border);
  color:var(--text);font-family:'Inter',sans-serif;font-size:.84rem;
  transition:all .15s;outline:none;
}
.field-in:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(91,106,240,.12)}
.field-in.mono{font-family:'JetBrains Mono',monospace;font-size:.74rem;color:var(--accent2)}
.field-in option{background:var(--bg2)}
textarea.field-in{resize:none;height:72px;line-height:1.5}
.sep{height:1px;background:linear-gradient(90deg,transparent,var(--border),transparent);margin:14px 0}
.exec-btn{
  width:100%;padding:14px;border:none;border-radius:11px;cursor:pointer;
  background:linear-gradient(135deg,var(--accent),#4338ca);
  color:#fff;font-weight:800;font-size:.9rem;letter-spacing:.3px;
  display:flex;align-items:center;justify-content:center;gap:9px;
  box-shadow:0 4px 20px rgba(91,106,240,.45),inset 0 1px 0 rgba(255,255,255,.12);
  transition:all .2s cubic-bezier(.34,1,.64,1);
  position:relative;overflow:hidden;user-select:none;
}
.exec-btn::before{content:'';position:absolute;inset:0;background:linear-gradient(135deg,rgba(255,255,255,.1),transparent);pointer-events:none}
.exec-btn::after{content:'';position:absolute;top:0;left:-80%;width:40%;height:100%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.18),transparent);animation:sweep 2.8s ease-in-out infinite}
@keyframes sweep{0%,100%{left:-80%}50%{left:130%}}
.exec-btn:hover{transform:translateY(-2px);box-shadow:0 10px 30px rgba(91,106,240,.6),inset 0 1px 0 rgba(255,255,255,.15)}
.exec-btn:active{transform:scale(.97);box-shadow:0 2px 8px rgba(91,106,240,.4)}
.resp-box{
  background:var(--bg3);border:1px solid var(--border);border-radius:11px;
  padding:12px 14px;margin-top:14px;transition:border-color .2s;
}
.resp-box:hover{border-color:rgba(91,106,240,.25)}
.resp-lbl{font-size:.58rem;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:var(--text3);margin-bottom:8px}
.resp-val{font-family:'JetBrains Mono',monospace;font-size:.76rem;color:var(--text3);line-height:1.65}

/* chart panel */
.chart-panel{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:12px;margin-bottom:14px}
.chart-lbl{font-size:.6rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--text3);margin-bottom:10px}
.chart-wrap{height:90px;position:relative}

/* ── TERMINAL / STATUS ── */
.terminal{height:0;flex-shrink:0;background:var(--bg);border-top:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;transition:height .3s ease}
.terminal.open{height:180px}
.term-bar{padding:6px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px;flex-shrink:0;background:var(--bg2)}
.term-dots{display:flex;gap:4px}
.tdot{width:9px;height:9px;border-radius:50%}
.term-title{font-family:'JetBrains Mono',monospace;font-size:.62rem;color:var(--text3);margin-left:6px}
.term-stream{flex:1;overflow-y:auto;padding:8px 14px;font-family:'JetBrains Mono',monospace;font-size:.68rem}
.term-stream::-webkit-scrollbar{width:2px}
.log{display:flex;gap:10px;margin-bottom:2px;line-height:1.5}
.log-ts{color:#1e293b;width:72px;flex-shrink:0}
.log-tag{width:46px;flex-shrink:0;font-weight:700}
.SYS{color:#818cf8}.STEP{color:#34d399}.WARN{color:#fbbf24}.ERR{color:#f87171}
.log-msg{color:#334155}

/* ── STATUSBAR ── */
.statusbar{
  background:var(--accent);display:flex;align-items:center;
  padding:0 16px;gap:16px;color:rgba(255,255,255,.85);font-size:.65rem;font-weight:500;
}
.sb-item{display:flex;align-items:center;gap:4px}
.sb-sep{opacity:.3}
.sb-right{margin-left:auto;display:flex;gap:12px;align-items:center}
.sb-kbd{background:rgba(255,255,255,.15);padding:1px 5px;border-radius:3px;font-family:'JetBrains Mono',monospace;font-size:.6rem}

/* ── SCHEMA PANEL ── */
.schema-panel{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:12px;margin-bottom:14px}
.schema-head{font-size:.6rem;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--text3);margin-bottom:8px}
.schema-row{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:.76rem}
.schema-row:last-child{border:none}
.schema-name{font-family:'JetBrains Mono',monospace;font-size:.7rem;font-weight:600}
.badges{display:flex;gap:4px}
/* view panels */
.view-panel{animation:fadeSlide .22s cubic-bezier(.34,1,.64,1) both}
@keyframes fadeSlide{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
/* info cards */
.info-card{
  background:var(--bg3);border:1px solid var(--border);border-radius:12px;
  padding:16px;margin-bottom:0;transition:all .2s;
}
.info-card:hover{border-color:rgba(255,255,255,.12);box-shadow:0 4px 16px rgba(0,0,0,.3)}
.ic-label{font-size:.58rem;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:var(--text3);margin-bottom:8px}
.ic-val{font-family:'JetBrains Mono',monospace;font-size:1.25rem;font-weight:900;color:var(--text);line-height:1.2;margin-bottom:4px}
.ic-sub{font-size:.72rem;color:var(--text3);line-height:1.4}
/* field improvements */
.field-in:hover{border-color:rgba(255,255,255,.15)}
.field-in:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(91,106,240,.15),0 1px 4px rgba(0,0,0,.3)}
/* phase pips clickable */
.pip{cursor:pointer}
.pip:hover{background:rgba(91,106,240,.1);border-color:rgba(91,106,240,.3);color:var(--accent);transform:scale(1.05)}

/* ── MODAL ── */
#modal{position:fixed;inset:0;z-index:999;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,.6);backdrop-filter:blur(4px)}
#modal.open{display:flex;animation:fadeIn .2s ease}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.modal-box{background:var(--bg2);border:1px solid var(--border);border-radius:16px;width:480px;overflow:hidden;box-shadow:0 32px 64px rgba(0,0,0,.5);animation:scaleIn .2s cubic-bezier(.34,1.56,.64,1)}
@keyframes scaleIn{from{transform:scale(.95);opacity:0}to{transform:scale(1);opacity:1}}
.modal-head{padding:18px 20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.modal-title{font-weight:700;font-size:.95rem}
.modal-close{background:none;border:none;color:var(--text3);cursor:pointer;font-size:1.2rem;padding:4px;border-radius:6px;transition:all .15s}
.modal-close:hover{background:rgba(255,255,255,.06);color:var(--text)}
.modal-body{padding:20px}
.modal-footer{padding:14px 20px;border-top:1px solid var(--border);display:flex;justify-content:flex-end;gap:8px}

/* ── TOAST ── */
#toasts{position:fixed;bottom:40px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;align-items:flex-end}
.toast{
  padding:11px 18px;border-radius:11px;max-width:320px;
  background:var(--bg3);border:1px solid var(--border);
  box-shadow:0 8px 24px rgba(0,0,0,.4);
  font-size:.8rem;font-weight:500;
  transition:all .3s cubic-bezier(.34,1.56,.64,1);
  display:flex;align-items:center;gap:10px;
  animation:toastIn .3s ease;
}
@keyframes toastIn{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}
.toast.out{transform:translateX(110%);opacity:0}
.toast-ico{font-size:1.1rem}

/* ── SCAN OVERLAY ── */
#scanOverlay{position:fixed;inset:0;z-index:1000;background:rgba(0,0,0,.85);backdrop-filter:blur(8px);display:none;align-items:center;justify-content:center;flex-direction:column;gap:20px}
#scanOverlay.open{display:flex;animation:fadeIn .4s ease}
.scan-spinner{width:60px;height:60px;border:4px solid rgba(255,255,255,.1);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite}
.scan-msg{font-family:'JetBrains Mono',monospace;font-size:1rem;color:var(--text);letter-spacing:1px}
.scan-progress{width:300px;height:4px;background:rgba(255,255,255,.1);border-radius:2px;overflow:hidden}
.scan-bar{height:100%;width:0%;background:var(--accent);transition:width .1s}
@keyframes spin{to{transform:rotate(360deg)}}

.grid-header{
  padding:14px 20px;background:rgba(255,255,255,.02);border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;gap:12px;
}
.grid-title{font-size:.85rem;font-weight:700;display:flex;align-items:center;gap:8px}
.grid-title i{color:var(--text3);font-style:normal;font-weight:500;font-size:.75rem}

/* Kbd shortcut hint */
.kbd{display:inline-block;background:rgba(255,255,255,.06);border:1px solid var(--border);border-radius:4px;padding:1px 5px;font-family:'JetBrains Mono',monospace;font-size:.62rem;color:var(--text3)}
</style>
</head>
<body>
<div class="app">

<!-- ══ TOP BAR ══ -->
<div class="topbar">
  <div class="topbar-brand">
    <div class="brand-icon">🛡️</div>
    <span class="brand-name">SQLAudit</span>
  </div>
  <div class="topbar-tabs">
    <div class="tab active" data-tab="workload" onclick="switchTab(this)"><span class="tab-ico">🗃️</span> Workload</div>
    <div class="tab" data-tab="schema" onclick="navToId('settings')"><span class="tab-ico">🗄️</span> Schema</div>
    <div class="tab" data-tab="analytics" onclick="switchTab(this)"><span class="tab-ico">📊</span> Analytics</div>
    <div class="tab" onclick="toggleTerminal()"><span class="tab-ico">🖥️</span> Terminal</div>
  </div>
  <div class="topbar-right">
    <select id="taskSelect" class="task-select" onchange="resetEnv()">
      <option value="task_easy">⚡ LVL 1 — Security Scan</option>
      <option value="task_medium">🔧 LVL 2 — Performance</option>
      <option value="task_hard">🔥 LVL 3 — Enterprise</option>
    </select>
    <button class="btn btn-ghost" onclick="openModal()">＋ New Action</button>
    <button class="btn btn-primary" onclick="resetEnv()">↺ Reset</button>
    <div class="badge-live"><div class="live-dot"></div>LIVE</div>
  </div>
</div>

<!-- ══ BODY ══ -->
<div class="app-body">

  <!-- SIDEBAR -->
  <div class="sidebar">
    <div class="sidebar-section">
      <div class="sidebar-label">Navigation</div>
      <div class="nav-item active" data-view="dashboard" onclick="navTo(this)"><span class="nav-ico">🏠</span> Dashboard</div>
      <div class="nav-item" data-view="queries" onclick="navTo(this)"><span class="nav-ico">🔍</span> Audit Queries</div>
      <div class="nav-item" data-view="security" onclick="navTo(this)"><span class="nav-ico">🛡️</span> Security Scan</div>
      <div class="nav-item" data-view="performance" onclick="navTo(this)"><span class="nav-ico">⚡</span> Performance</div>
      <div class="nav-item" data-view="compliance" onclick="navTo(this)"><span class="nav-ico">🔒</span> Compliance</div>
    </div>
    <div class="sidebar-divider"></div>
    <div class="sidebar-section">
      <div class="sidebar-label">Tools</div>
      <div class="nav-item" data-view="reports" onclick="navTo(this)"><span class="nav-ico">📋</span> Reports</div>
      <div class="nav-item" data-view="metrics" onclick="navTo(this)"><span class="nav-ico">📈</span> Metrics</div>
      <div class="nav-item" data-view="settings" onclick="navTo(this)"><span class="nav-ico">⚙️</span> Settings</div>
    </div>
    <div class="sidebar-footer">
      <div class="episode-card">
        <div class="ep-label">Current Episode</div>
        <div class="ep-stats">
          <div class="ep-stat">
            <div id="sReward" class="ep-stat-val reward-val">0.000</div>
            <div class="ep-stat-key">Reward</div>
          </div>
          <div class="ep-stat">
            <div id="sSteps" class="ep-stat-val steps-val">0/20</div>
            <div class="ep-stat-key">Steps</div>
          </div>
        </div>
        <div id="sPhasePill" class="phase-pill">SCANNING</div>
      </div>
    </div>
  </div>

  <!-- MAIN CONTENT -->
  <div class="main">
    <div class="main-toolbar">
      <div class="breadcrumb">📁 SQLAudit <span style="color:var(--border)">›</span> <span id="crumbSection">Dashboard</span></div>
      <div class="phase-track" id="phaseTrack"></div>
    </div>

    <!-- VIEW: dashboard -->
    <div id="view-dashboard" class="view-panel queries-scroll">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
        <div class="info-card" style="border-left:3px solid var(--accent)">
          <div class="ic-label">Environment</div>
          <div class="ic-val">SQLAudit-Env v1.0.0</div>
          <div class="ic-sub">OpenEnv Compliant · FastAPI backend</div>
        </div>
        <div class="info-card" style="border-left:3px solid var(--green)">
          <div class="ic-label">Status</div>
          <div class="ic-val" style="color:var(--green)">● LIVE</div>
          <div class="ic-sub" id="dbEpId">Episode EP_001 active</div>
        </div>
        <div class="info-card" style="border-left:3px solid #f59e0b">
          <div class="ic-label">Cumulative Reward</div>
          <div id="dbReward" class="ic-val" style="color:#f59e0b">0.000</div>
          <div class="ic-sub">Agent performance score</div>
        </div>
        <div class="info-card" style="border-left:3px solid #a78bfa">
          <div class="ic-label">Steps Taken</div>
          <div id="dbSteps" class="ic-val" style="color:#a78bfa">0 / 20</div>
          <div class="ic-sub">Budget remaining</div>
        </div>
      </div>
      <div class="info-card" style="margin-bottom:12px">
        <div class="ic-label" style="margin-bottom:10px">What is SQLAudit-Env?</div>
        <p style="color:var(--text2);line-height:1.7;font-size:.84rem">SQLAudit-Env is an <strong style="color:var(--text)">OpenEnv-compliant</strong> AI training environment for SQL security auditing. Use the <strong style="color:var(--text)">Audit Queries</strong> view to inspect queries, the <strong style="color:var(--text)">Action Panel</strong> to execute audit steps, and track your agent's performance in <strong style="color:var(--text)">Metrics</strong>.</p>
      </div>
      <div class="info-card">
        <div class="ic-label" style="margin-bottom:10px">Quick Actions</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn btn-primary" onclick="navToId('queries')">🔍 Go to Audit Queries</button>
          <button class="btn btn-ghost" onclick="navToId('metrics')">📊 View Metrics</button>
          <button class="btn btn-ghost" onclick="resetEnv()">↺ Reset Episode</button>
          <button class="btn btn-ghost" onclick="toggleTerminal()">🖥️ Open Terminal</button>
        </div>
      </div>
    </div>

    <!-- VIEW: queries / security / performance / compliance (all show query grid) -->
    <div id="view-queries" class="view-panel" style="display:none;flex:1;overflow:hidden;flex-direction:column">
      <div id="gridHeader" class="grid-header"></div>
      <div id="queryGrid" class="queries-scroll" style="flex:1"></div>
    </div>

    <!-- VIEW: reports -->
    <div id="view-reports" class="view-panel queries-scroll" style="display:none">
      <div class="info-card" style="margin-bottom:12px">
        <div class="ic-label" style="margin-bottom:8px">Audit Report Summary</div>
        <div id="reportContent" style="color:var(--text2);font-size:.85rem;line-height:1.7">No report submitted yet. Use <strong style="color:var(--text)">SUBMIT_REPORT</strong> action to generate one.</div>
      </div>
      <div class="info-card">
        <div class="ic-label" style="margin-bottom:10px">Step History</div>
        <div id="reportLog" style="font-family:monospace;font-size:.75rem;color:var(--text3);max-height:300px;overflow-y:auto">No steps recorded yet.</div>
      </div>
    </div>

    <!-- VIEW: metrics -->
    <div id="view-metrics" class="view-panel queries-scroll" style="display:none">
      <div class="info-card" style="margin-bottom:12px">
        <div class="ic-label" style="margin-bottom:10px">Reward Trajectory (Full View)</div>
        <div style="height:200px;position:relative"><canvas id="bigChart"></canvas></div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
        <div class="info-card"><div class="ic-label">Peak Reward</div><div id="mPeak" class="ic-val" style="color:#34d399">—</div></div>
        <div class="info-card"><div class="ic-label">Total Steps</div><div id="mSteps" class="ic-val" style="color:#818cf8">0</div></div>
        <div class="info-card"><div class="ic-label">Findings</div><div id="mFindings" class="ic-val" style="color:#f59e0b">0</div></div>
      </div>
    </div>

    <!-- VIEW: settings -->
    <div id="view-settings" class="view-panel queries-scroll" style="display:none">
      <div class="info-card" style="margin-bottom:12px">
        <div class="ic-label" style="margin-bottom:12px">Task Configuration</div>
        <div class="field"><label class="field-label">Active Task</label>
          <select class="field-in" onchange="document.getElementById('taskSelect').value=this.value;resetEnv()">
            <option value="task_easy">⚡ LVL 1 — Security Scan</option>
            <option value="task_medium">🔧 LVL 2 — Performance Audit</option>
            <option value="task_hard">🔥 LVL 3 — Enterprise Pipeline</option>
          </select>
        </div>
      </div>
      <div class="info-card" style="margin-bottom:12px">
        <div class="ic-label" style="margin-bottom:12px">Keyboard Shortcuts</div>
        <div style="display:grid;gap:8px;font-size:.82rem;color:var(--text2)">
          <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)"><span>Reset Episode</span><span class="kbd">Ctrl+R</span></div>
          <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)"><span>Execute Step</span><span class="kbd">Ctrl+Enter</span></div>
          <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)"><span>Toggle Terminal</span><span class="kbd">Ctrl+T</span></div>
          <div style="display:flex;justify-content:space-between;padding:6px 0"><span>Quick Action Modal</span><span class="kbd">Ctrl+K</span></div>
        </div>
      </div>
      <div class="info-card">
        <div class="ic-label" style="margin-bottom:8px">About</div>
        <p style="color:var(--text3);font-size:.8rem;line-height:1.6">SQLAudit-Env · OpenEnv v1.0.0<br>Designed for AI agent training on SQL security, optimization, and GDPR compliance tasks.</p>
      </div>
    </div>

    <div class="terminal" id="terminal">
      <div class="term-bar">
        <div class="term-title">▸ KERNEL TRACE — sqlaudit@env:~</div>
        <button onclick="toggleTerminal()" style="margin-left:auto;background:none;border:none;color:var(--text3);cursor:pointer;font-size:.9rem">✕</button>
      </div>
      <div class="term-stream" id="logStream"></div>
    </div>
  </div>

  <!-- RIGHT PANEL -->
  <div class="right-panel">
    <div class="rp-head">
      <div class="rp-title"><span class="rp-title-ico">⚡</span> Action Panel</div>
      <span style="font-size:.65rem;color:var(--green);font-weight:700">READY</span>
    </div>
    <div class="rp-scroll">

      <div class="chart-panel">
        <div class="chart-lbl">Reward Trajectory</div>
        <div class="chart-wrap"><canvas id="rewardChart"></canvas></div>
      </div>

      <div class="field">
        <label class="field-label">Action Type</label>
        <select id="actionType" class="field-in" onchange="onACT()">
          <option value="scan_query">🔍 SCAN_QUERY</option>
          <option value="rewrite_query">✏️ REWRITE_QUERY</option>
          <option value="flag_compliance">🔒 FLAG_COMPLIANCE</option>
          <option value="submit_report">📋 SUBMIT_REPORT</option>
        </select>
      </div>
      <div id="idxF" class="field">
        <label class="field-label">Query Index</label>
        <input type="number" id="queryIdx" class="field-in" value="0" min="0"/>
      </div>
      <div class="field">
        <label class="field-label">Severity</label>
        <select id="severity" class="field-in">
          <option value="info">ℹ️ INFO</option>
          <option value="low">🟡 LOW</option>
          <option value="medium">🟠 MEDIUM</option>
          <option value="high">🔴 HIGH</option>
          <option value="critical" selected>💀 CRITICAL</option>
        </select>
      </div>
      <div class="field">
        <label class="field-label">Finding Detail</label>
        <textarea id="findingTxt" class="field-in" placeholder="Describe the vulnerability…"></textarea>
      </div>
      <div id="sqlF" class="field" style="display:none">
        <label class="field-label">Rewritten SQL</label>
        <textarea id="sqlTxt" class="field-in mono" placeholder="SELECT …"></textarea>
      </div>
      <div class="sep"></div>
      <button class="exec-btn" id="execBtn" onclick="stepEnv()">⚡ Execute Step <span class="kbd">↵</span></button>
      <div class="resp-box">
        <div class="resp-lbl">Last Response</div>
        <div id="lastResp" class="resp-val">awaiting first step…</div>
      </div>
      <div class="sep"></div>
      <div id="schemaBox" class="schema-panel">
        <div class="schema-head">Database Schema</div>
      </div>
    </div>
  </div>

</div>

<!-- ══ STATUS BAR ══ -->
<div class="statusbar">
  <div class="sb-item">🛡️ SQLAudit-Env v1.0.0</div>
  <span class="sb-sep">·</span>
  <div class="sb-item">OpenEnv Compliant</div>
  <span class="sb-sep">·</span>
  <div class="sb-item" id="sbEp">EP_001</div>
  <span class="sb-sep">·</span>
  <div class="sb-item" id="sbPhase">Phase: scanning</div>
  <div class="sb-right">
    <div class="sb-item"><span class="sb-kbd">⌘R</span> Reset</div>
    <div class="sb-item"><span class="sb-kbd">↵</span> Execute</div>
    <div class="sb-item"><span class="sb-kbd">⌘T</span> Terminal</div>
  </div>
</div>

</div><!-- .app -->

<div id="scanOverlay">
  <div class="scan-spinner"></div>
  <div class="scan-msg">AUDITING SQL STREAM...</div>
  <div class="scan-progress"><div id="scanBar" class="scan-bar"></div></div>
  <div id="scanTarget" style="font-size:.7rem;color:var(--text3);font-family:monospace">Initializing Engine...</div>
</div>

<div id="toasts"></div>

<!-- ══ MODAL ══ -->
<div id="modal">
  <div class="modal-box">
    <div class="modal-head">
      <div class="modal-title">Quick Action</div>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <p style="color:var(--text2);font-size:.84rem;margin-bottom:14px">Configure and execute a rapid audit action on any query in the workload.</p>
      <div class="field"><label class="field-label">Action</label><select id="mAction" class="field-in"><option value="scan_query">🔍 Scan Query</option><option value="flag_compliance">🔒 Flag Compliance</option></select></div>
      <div class="field"><label class="field-label">Query Index</label><input type="number" id="mIdx" class="field-in" value="0"/></div>
      <div class="field"><label class="field-label">Note</label><textarea id="mNote" class="field-in" placeholder="Brief finding…" style="height:60px"></textarea></div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="modalExec()">Execute</button>
    </div>
  </div>
</div>

<script>
let chart, rH=[0], sL=['0'], epN=0, termOpen=false, curObs=null, curV='dashboard';
const PHASES=['scanning','optimizing','compliance','reporting'];
const NAV_LABELS={task_easy:'Security Scan',task_medium:'Performance Audit',task_hard:'Enterprise Pipeline'};

/* ── chart ── */
function initChart(){
  const c=document.getElementById('rewardChart').getContext('2d');
  const g=c.createLinearGradient(0,0,0,90);
  g.addColorStop(0,'rgba(91,106,240,.5)');g.addColorStop(1,'rgba(91,106,240,0)');
  chart=new Chart(c,{
    type:'line',
    data:{labels:sL,datasets:[{data:rH,borderColor:'#5b6af0',backgroundColor:g,borderWidth:2,tension:.45,fill:true,pointRadius:2,pointBackgroundColor:'#5b6af0'}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{backgroundColor:'#1c2333',borderColor:'#2a3349',borderWidth:1,titleColor:'#818cf8',bodyColor:'#94a3b8'}},scales:{x:{display:false},y:{display:false,min:0}},animation:{duration:400}}
  });
}

/* ── env ── */
async function resetEnv(){
  const tid=document.getElementById('taskSelect').value;
  try{
    const d=await api('/reset',{task_id:tid});
    epN++;
    document.getElementById('sReward').textContent='0.000';
    document.getElementById('sSteps').textContent=`0/${d.max_steps}`;
    document.getElementById('sPhasePill').textContent=d.phase.toUpperCase();
    document.getElementById('sbEp').textContent=`EP_${String(epN).padStart(3,'0')}`;
    document.getElementById('sbPhase').textContent=`Phase: ${d.phase}`;
    rH=[0];sL=['0'];chart.data.labels=sL;chart.data.datasets[0].data=rH;chart.update('none');
    renderPhase(d.phase);renderQueries(d);renderSchema(d.schema_info);
    curObs=d;
    log('SYS',`Episode ${epN} initialized · ${tid}`);
    toast('✅ Episode initialized','#22c55e');
  }catch(e){log('ERR',e.message,'ERR');toast('❌ Reset failed','#ef4444');}
}

async function stepEnv(){
  const type=document.getElementById('actionType').value;
  const btn=document.getElementById('execBtn');
  btn.disabled=true;btn.textContent='⏳ Running…';
  try{
    const p={action_type:type,query_index:parseInt(document.getElementById('queryIdx').value)||0,severity:document.getElementById('severity').value,finding:document.getElementById('findingTxt').value,rewritten_sql:document.getElementById('sqlTxt').value,reasoning:'Manual',report_summary:type==='submit_report'?document.getElementById('findingTxt').value:null};
    const d=await api('/step',p);const obs=d.observation;
    curObs=obs;
    rH.push(obs.score_so_far);sL.push(obs.step.toString());chart.data.labels=sL;chart.data.datasets[0].data=rH;chart.update();
    const rv=obs.score_so_far.toFixed(3);
    document.getElementById('sReward').textContent=rv;
    document.getElementById('sSteps').textContent=`${obs.step}/${obs.max_steps}`;
    document.getElementById('sPhasePill').textContent=obs.phase.toUpperCase();
    document.getElementById('sbPhase').textContent=`Phase: ${obs.phase}`;
    const pos=d.reward.value>=0;
    if(pos) findingsCount++;
    document.getElementById('lastResp').innerHTML=`<span style="color:${pos?'#34d399':'#f43f5e'};font-size:1rem;font-weight:800">${pos?'+':''}${d.reward.value.toFixed(4)}</span>  <span style="color:var(--text3)">step ${obs.step}${d.done?' · <span style="color:#f43f5e">DONE</span>':''}</span>`;
    renderPhase(obs.phase);renderQueries(obs);
    const rl=document.getElementById('reportLog');
    if(rl){rl.innerHTML+=`<div style="padding:4px 0;border-bottom:1px solid var(--border)">[${new Date().toLocaleTimeString()}] ${type} idx=${p.query_index} → ${pos?'+':''}${d.reward.value.toFixed(4)}</div>`;}
    if(type==='submit_report'){const rc=document.getElementById('reportContent');if(rc)rc.innerHTML=`<strong style="color:var(--text)">Report submitted at step ${obs.step}</strong><br><br>${esc(p.finding||'No summary provided.')}<br><br><span style="color:var(--green)">✅ Final score: ${rv}</span>`;}
    log('STEP',`[${type}] idx=${p.query_index} → ${pos?'+':''}${d.reward.value.toFixed(4)}`,pos?'STEP':'WARN');
    toast(pos?`✅ +${d.reward.value.toFixed(4)} reward`:`⚠️ ${d.reward.value.toFixed(4)} reward`,pos?'#22c55e':'#f59e0b');
    if(d.done){log('ERR','Episode terminal state reached.','ERR');toast('🏁 Episode complete!','#5b6af0');}
  }catch(e){log('ERR',e.message,'ERR');toast('❌ Step failed','#ef4444');}
  finally{btn.disabled=false;btn.innerHTML='⚡ Execute Step <span class="kbd">↵</span>';}
}

/* ── renders ── */
function renderPhase(cur){
  const done=PHASES.slice(0,PHASES.indexOf(cur));
  document.getElementById('phaseTrack').innerHTML=PHASES.map(p=>`<div class="pip ${p===cur?'active':done.includes(p)?'done':''}">${p.substring(0,4).toUpperCase()}</div>`).join('');
  document.getElementById('sPhasePill').textContent=cur.toUpperCase();
}
function renderQueries(obs){
  const sel=parseInt(document.getElementById('queryIdx').value)||0;
  document.getElementById('queryGrid').innerHTML=obs.queries.map((q,i)=>{
    const st=obs.query_statuses[i];
    return `<div class="query-card ${i===sel?'active':''} ${st!=='pending'?'done':''}" onclick="pickQ(${i})">
      <div class="qc-head">
        <span class="qc-id">QUERY·${String(i).padStart(2,'0')}</span>
        <span class="badge ${st!=='pending'?'b-done':'b-pend'}">${st.toUpperCase()}</span>
      </div>
      <div class="qc-body">${esc(q)}</div>
    </div>`;
  }).join('');
}
function renderSchema(s){
  if(!s)return;
  const rows=Object.entries(s).map(([n,t])=>{
    const pii=t.columns&&t.columns.some(c=>c.pii==='YES');
    return `<div class="schema-row"><span class="schema-name">${n}</span><div class="badges">${pii?'<span class="badge b-pii">PII</span>':''}<span class="badge b-pend">${t.row_estimate??'—'}r</span></div></div>`;
  }).join('');
  document.getElementById('schemaBox').innerHTML=`<div class="schema-head">Database Schema</div>${rows}`;
}

/* ── helpers ── */
async function api(path,body){
  const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
function pickQ(i){document.getElementById('queryIdx').value=i;document.querySelectorAll('.query-card').forEach((c,idx)=>c.classList.toggle('active',idx===i));}
function onACT(){
  const v=document.getElementById('actionType').value;
  document.getElementById('sqlF').style.display=v==='rewrite_query'?'block':'none';
  document.getElementById('idxF').style.display=v==='submit_report'?'none':'block';
}
/* ── view router ── */
const VIEW_MAP={dashboard:'Dashboard',queries:'Audit Queries',security:'Security Scan',performance:'Performance',compliance:'Compliance',reports:'Reports',metrics:'Metrics',settings:'Settings'};
const QUERY_VIEWS=new Set(['queries','security','performance','compliance']);
let bigChart=null, findingsCount=0;

function navTo(el){
  const view=el.dataset.view;
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  el.classList.add('active');
  showView(view);
}
function navToId(view){
  const el=document.querySelector(`[data-view="${view}"]`);
  if(el) navTo(el);
}
function showView(view){
  curV=view;
  document.querySelectorAll('.view-panel').forEach(p=>p.style.display='none');
  const panel=document.getElementById('view-'+view);
  if(panel) panel.style.display=QUERY_VIEWS.has(view)?'flex':'block';
  document.getElementById('crumbSection').textContent=VIEW_MAP[view]||view;
  
  // sync tabs
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  const tabMap={queries:'workload',security:'workload',performance:'workload',compliance:'workload',metrics:'analytics'};
  const tabName=tabMap[view];
  if(tabName){const t=document.querySelector(`.tab[data-tab="${tabName}"]`);if(t)t.classList.add('active');}
  
  // filter & header
  if(QUERY_VIEWS.has(view)) filterQueries(view);
  const gh = document.getElementById('gridHeader');
  if(gh){
    if(view==='security'){
      gh.innerHTML = `<div class="grid-title">🛡️ Security Scan <i>— Vulnerability Audit</i></div>
                     <button class="btn btn-primary" onclick="runSecurityScan()"><span style="font-size:1.1rem">📡</span> Start Automated Scan</button>`;
    } else if(view==='performance'){
      gh.innerHTML = `<div class="grid-title">⚡ Performance Optimize <i>— Bottleneck Detection</i></div>
                     <button class="btn btn-primary" onclick="toast('ℹ️ Performance Auto-Optimizer ready.')">🚀 Optimize All</button>`;
    } else if(view==='compliance'){
      gh.innerHTML = `<div class="grid-title">🔒 Compliance Guard <i>— PII & GDPR Audit</i></div>
                     <button class="btn btn-primary" onclick="toast('🔒 Compliance scanner active.')">🛡️ Check Privacy</button>`;
    } else {
      gh.innerHTML = `<div class="grid-title">🔍 Audit Queries <i>— Live Workload Filter</i></div>`;
    }
    wireRipples();
  }
  
  if(view==='metrics') refreshMetrics();
  if(view==='dashboard') refreshDashboard();
}

async function runSecurityScan(){
  const s = document.getElementById('scanOverlay');
  const b = document.getElementById('scanBar');
  const t = document.getElementById('scanTarget');
  s.classList.add('open');
  
  const qs = curObs?.queries || [];
  for(let i=0; i<qs.length; i++){
    const p = ((i+1)/qs.length)*100;
    b.style.width = p+'%';
    t.textContent = `AUDITING BLOB [0x${i.toString(16).toUpperCase()}]: ${qs[i].substring(0,35)}...`;
    
    const sql = qs[i].toLowerCase();
    if(sql.includes('\' or \'1\'=\'1') || sql.includes('drop table') || sql.includes('union select')){
      log('WARN', `Vulnerability detected at index ${i}`, 'WARN');
      toast(`⚠️ RISK: SQL Injection at ID ${i}`, '#f87171');
    }
    await new Promise(r=>setTimeout(r, 150 + Math.random()*200));
  }
  
  setTimeout(()=>{
    s.classList.remove('open');
    toast('✅ Automated security scan complete!', '#34d399');
    log('SYS', 'Global Security Scan finished. All vulnerabilities flagged.', 'STEP');
    showView('queries');
  }, 500);
}
function filterQueries(view){
  const cards=document.querySelectorAll('#queryGrid .query-card');
  const KEYWORDS={security:['injection','xss','sql','union','exec','drop','delete','truncate'],performance:['select *','join','cartesian','full scan','missing index','n+1'],compliance:['email','phone','ssn','pii','gdpr','address','password','secret']};
  const kw=KEYWORDS[view]||null;
  cards.forEach(c=>{
    if(!kw){c.style.display='';return;}
    const txt=c.querySelector('.qc-body')?.textContent.toLowerCase()||'';
    c.style.display=kw.some(k=>txt.includes(k))?'':'none';
  });
  // show message if none match
  const visible=[...cards].filter(c=>c.style.display!=='none').length;
  let msg=document.getElementById('filterMsg');
  if(!msg){msg=document.createElement('div');msg.id='filterMsg';msg.style.cssText='padding:20px 16px;color:var(--text3);font-size:.82rem;text-align:center';document.getElementById('queryGrid').appendChild(msg);}
  msg.textContent=visible===0?`No ${view}-related queries found in current workload.`:'';
}
function refreshMetrics(){
  const peak=rH.length>1?Math.max(...rH.slice(1)).toFixed(4):'—';
  document.getElementById('mPeak').textContent=peak;
  document.getElementById('mSteps').textContent=sL.length-1;
  document.getElementById('mFindings').textContent=findingsCount;
  // big chart
  setTimeout(()=>{
    const c2=document.getElementById('bigChart');
    if(!c2)return;
    if(bigChart)bigChart.destroy();
    const ctx=c2.getContext('2d');
    const g=ctx.createLinearGradient(0,0,0,200);
    g.addColorStop(0,'rgba(91,106,240,.4)');g.addColorStop(1,'rgba(91,106,240,0)');
    bigChart=new Chart(ctx,{type:'line',data:{labels:sL,datasets:[{label:'Reward',data:rH,borderColor:'#5b6af0',backgroundColor:g,borderWidth:2.5,tension:.45,fill:true,pointRadius:4,pointBackgroundColor:'#5b6af0'}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{backgroundColor:'#1c2333',borderColor:'#2a3349',borderWidth:1}},scales:{x:{grid:{color:'rgba(255,255,255,.04)'},ticks:{color:'#475569',font:{size:10}}},y:{grid:{color:'rgba(255,255,255,.04)'},ticks:{color:'#475569',font:{size:10}},min:0}}}});
  },50);
}
function refreshDashboard(){
  document.getElementById('dbReward').textContent=rH[rH.length-1]?.toFixed(3)||'0.000';
  document.getElementById('dbSteps').textContent=`${sL.length-1} / 20`;
  document.getElementById('dbEpId').textContent=`Episode EP_${String(epN).padStart(3,'0')} active`;
}
function switchTab(el){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  const viewMap={workload:'queries',analytics:'metrics'};
  const v=viewMap[el.dataset.tab];
  if(v) navToId(v);
}
function toggleTerminal(){termOpen=!termOpen;document.getElementById('terminal').classList.toggle('open',termOpen);}
function openModal(){document.getElementById('modal').classList.add('open');}
function closeModal(){document.getElementById('modal').classList.remove('open');}
function closeApp(){if(confirm('Close SQLAudit?'))window.close();}
async function modalExec(){
  document.getElementById('actionType').value=document.getElementById('mAction').value;
  document.getElementById('queryIdx').value=document.getElementById('mIdx').value;
  document.getElementById('findingTxt').value=document.getElementById('mNote').value;
  closeModal();await stepEnv();
}
function log(tag,msg,cls='SYS'){
  const el=document.getElementById('logStream');
  const ts=new Date().toLocaleTimeString('en-GB');
  el.innerHTML+=`<div class="log"><span class="log-ts">[${ts}]</span><span class="log-tag ${cls}">${tag}</span><span class="log-msg">${msg}</span></div>`;
  el.scrollTop=el.scrollHeight;
}
function toast(msg,color='#5b6af0'){
  const t=document.createElement('div');
  t.className='toast';
  t.innerHTML=`<span class="toast-ico">${msg.substring(0,2)}</span><span>${msg.substring(2).trim()}</span>`;
  t.style.borderLeft=`3px solid ${color}`;
  document.getElementById('toasts').appendChild(t);
  setTimeout(()=>{t.classList.add('out');setTimeout(()=>t.remove(),300)},2800);
}
function esc(s){return(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}

/* ── ripple effect ── */
function addRipple(e){
  const btn=e.currentTarget;
  const rect=btn.getBoundingClientRect();
  const r=document.createElement('span');
  const size=Math.max(rect.width,rect.height);
  r.className='ripple';
  r.style.cssText=`width:${size}px;height:${size}px;left:${e.clientX-rect.left-size/2}px;top:${e.clientY-rect.top-size/2}px`;
  btn.appendChild(r);
  r.addEventListener('animationend',()=>r.remove());
}
function wireRipples(){document.querySelectorAll('.btn,.exec-btn,.modal-close').forEach(b=>b.addEventListener('click',addRipple));}

/* ── keyboard shortcuts ── */
document.addEventListener('keydown',e=>{
  if((e.metaKey||e.ctrlKey)&&e.key==='r'){e.preventDefault();resetEnv();}
  if((e.metaKey||e.ctrlKey)&&e.key==='t'){e.preventDefault();toggleTerminal();}
  if((e.metaKey||e.ctrlKey)&&e.key==='k'){e.preventDefault();openModal();}
  if(e.key==='Enter'&&(e.metaKey||e.ctrlKey)){stepEnv();}
});

/* ── boot ── */
window.onload=()=>{initChart();resetEnv().then(()=>{showView('dashboard');wireRipples();});};
</script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("app.server:app", host="0.0.0.0", port=port, reload=False)
