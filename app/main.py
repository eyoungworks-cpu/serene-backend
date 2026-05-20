from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import httpx
from .config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://asylumcommand.netlify.app",
        "http://localhost:5174",
        "http://localhost:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/health")
def health():
    return {"status": "ok", "env": settings.ENV}

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
    with httpx.Client(base_url=settings.ASYLUM_API_BASE, timeout=10.0) as client:
        resp = client.post("/tasks", json=payload)
        resp.raise_for_status()
        task = resp.json()
    return ExecTaskResponse(**task)

@app.get("/exec/tasks", response_model=ExecTaskListResponse)
def exec_list_tasks():
    with httpx.Client(base_url=settings.ASYLUM_API_BASE, timeout=10.0) as client:
        resp = client.get("/tasks")
        resp.raise_for_status()
        tasks = resp.json()
    return ExecTaskListResponse(tasks=tasks)
from services.account_service import create_account

request = {
    "platform": "Metricool",
    "purpose": "Analytics for TikTok performance",
    "justification": "Needed for content optimization",
    "expected_roi": "10-20% increase in engagement",
    "integration_plan": "Connect to Asylum dashboard",
    "owner": "Asylum"
}

response = create_account(request)
print(response)
