from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime
import httpx
from .config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://asylumcommand.netlify.app",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── HEALTH ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "env": settings.ENV,
        "asylum_base": settings.ASYLUM_API_BASE,
        "timestamp": datetime.utcnow().isoformat(),
    }

# ── ASYLUM RELAY ──────────────────────────────────────────────────────────────

def relay_to_asylum(method: str, path: str, payload: dict = None):
    with httpx.Client(base_url=settings.ASYLUM_API_BASE, timeout=15.0) as client:
        if method == "GET":
            resp = client.get(path)
        elif method == "POST":
            resp = client.post(path, json=payload)
        elif method == "PATCH":
            resp = client.patch(path, json=payload)
        elif method == "DELETE":
            resp = client.delete(path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported method")
        resp.raise_for_status()
        return resp.json()

# ── EXEC POST ─────────────────────────────────────────────────────────────────

class ExecPostRequest(BaseModel):
    platform: str
    content: str
    metadata: Optional[Dict[str, Any]] = None

class ExecTaskResponse(BaseModel):
    id: int
    status: str
    type: str
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None

class ExecTaskListResponse(BaseModel):
    tasks: List[ExecTaskResponse]

@app.post("/exec/post", response_model=ExecTaskResponse)
def exec_post(req: ExecPostRequest):
    payload = {
        "type": "POST_CONTENT",
        "payload": {
            "platform": req.platform,
            "content": req.content,
            "metadata": req.metadata or {},
        },
    }
    task = relay_to_asylum("POST", "/tasks", payload)
    return ExecTaskResponse(**task)

@app.get("/exec/tasks", response_model=ExecTaskListResponse)
def exec_list_tasks():
    tasks = relay_to_asylum("GET", "/tasks")
    return ExecTaskListResponse(tasks=tasks)

# ── WORKFLOW ENGINE ───────────────────────────────────────────────────────────

class WorkflowRequest(BaseModel):
    workflow_type: str
    target: str
    payload: Optional[Dict[str, Any]] = None
    priority: str = "normal"
    notes: Optional[str] = None

@app.post("/workflow/submit")
def submit_workflow(req: WorkflowRequest):
    task_payload = {
        "type": req.workflow_type,
        "payload": {
            "target": req.target,
            "priority": req.priority,
            "notes": req.notes or "",
            **(req.payload or {}),
        },
    }
    task = relay_to_asylum("POST", "/tasks", task_payload)
    return {
        "submitted": True,
        "workflow_type": req.workflow_type,
        "task_id": task.get("id"),
        "status": task.get("status"),
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/workflow/status")
def workflow_status():
    tasks = relay_to_asylum("GET", "/tasks")
    total = len(tasks)
    by_status = {}
    for t in tasks:
        s = t.get("status", "UNKNOWN")
        by_status[s] = by_status.get(s, 0) + 1
    return {
        "total_workflows": total,
        "by_status": by_status,
        "timestamp": datetime.utcnow().isoformat(),
    }

# ── ACCOUNT CREATION PROTOCOL ─────────────────────────────────────────────────

class AccountRequest(BaseModel):
    platform: str
    purpose: str
    roi_justification: str
    requested_by: str = "serene"
    content_category: Optional[str] = None
    estimated_monthly_value: Optional[str] = None

@app.post("/accounts/request")
def request_account_creation(req: AccountRequest):
    """
    Serene submits account creation request.
    Routes to Asylum Guardian for approval check.
    Founder (Erin) gives final approval.
    """
    task_payload = {
        "type": "ACCOUNT_CREATION_REQUEST",
        "payload": {
            "platform": req.platform,
            "purpose": req.purpose,
            "roi_justification": req.roi_justification,
            "requested_by": req.requested_by,
            "content_category": req.content_category or "general",
            "estimated_monthly_value": req.estimated_monthly_value or "TBD",
            "requires_founder_approval": True,
            "timestamp": datetime.utcnow().isoformat(),
        },
    }
    task = relay_to_asylum("POST", "/tasks/submit-for-approval", task_payload)
    return {
        "request_submitted": True,
        "platform": req.platform,
        "task_id": task.get("id"),
        "status": task.get("status"),
        "next_step": "Awaiting Asylum approval, then Founder final sign-off",
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/accounts/pending")
def get_pending_account_requests():
    tasks = relay_to_asylum("GET", "/tasks/awaiting")
    account_tasks = [
        t for t in tasks
        if t.get("type") == "ACCOUNT_CREATION_REQUEST"
        or (t.get("payload") or {}).get("platform")
    ]
    return {
        "pending_count": len(account_tasks),
        "requests": account_tasks,
        "timestamp": datetime.utcnow().isoformat(),
    }

# ── FILE ACCESS PROTOCOL ──────────────────────────────────────────────────────

class FileAccessRequest(BaseModel):
    operation: str
    file_path: str
    content: Optional[str] = None
    requested_by: str = "serene"
    reason: str = ""

ALLOWED_BASE_PATHS = [
    "EYoungWorks_System/Asylum",
    "EYoungWorks_System/Serene",
    "EYoungWorks_System/Shared",
]

def is_path_allowed(file_path: str) -> bool:
    normalized = file_path.replace("\\", "/")
    return any(base in normalized for base in ALLOWED_BASE_PATHS)

@app.post("/files/request")
def request_file_access(req: FileAccessRequest):
    if not is_path_allowed(req.file_path):
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: path is outside EYoungWorks company scope"
        )
    if req.operation not in ["READ", "WRITE", "CREATE", "LOG"]:
        raise HTTPException(
            status_code=400,
            detail="Operation must be READ, WRITE, CREATE, or LOG"
        )
    task_payload = {
        "type": "FILE_ACCESS",
        "payload": {
            "operation": req.operation,
            "file_path": req.file_path,
            "content": req.content or "",
            "requested_by": req.requested_by,
            "reason": req.reason,
            "timestamp": datetime.utcnow().isoformat(),
        },
    }
    task = relay_to_asylum("POST", "/tasks", task_payload)
    return {
        "access_granted": True,
        "operation": req.operation,
        "file_path": req.file_path,
        "task_id": task.get("id"),
        "status": task.get("status"),
        "timestamp": datetime.utcnow().isoformat(),
    }

# ── SERENE STATUS SUMMARY ─────────────────────────────────────────────────────

@app.get("/status")
def serene_status():
    try:
        tasks = relay_to_asylum("GET", "/tasks")
        awaiting = relay_to_asylum("GET", "/tasks/awaiting")
        memories = relay_to_asylum("GET", "/memory")
        asylum_health = relay_to_asylum("GET", "/health")
        asylum_online = asylum_health.get("status") == "ok"
    except Exception:
        tasks, awaiting, memories, asylum_online = [], [], [], False

    account_requests = [
        t for t in awaiting
        if t.get("type") == "ACCOUNT_CREATION_REQUEST"
    ]

    return {
        "serene": "online",
        "asylum_connected": asylum_online,
        "total_tasks": len(tasks),
        "awaiting_approval": len(awaiting),
        "pending_account_requests": len(account_requests),
        "total_memories": len(memories),
        "timestamp": datetime.utcnow().isoformat(),
    }