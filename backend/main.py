from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database import create_document, get_documents, update_document, delete_document
from schemas import Task

app = FastAPI(title="Ultimate Task Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    focus: Task.model_fields["focus"].annotation  # reuse union type
    status: Task.model_fields["status"].annotation
    due_date: Optional[datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    focus: Optional[Task.model_fields["focus"].annotation] = None
    status: Optional[Task.model_fields["status"].annotation] = None
    due_date: Optional[datetime] = None

@app.get("/", tags=["health"])
async def root():
    return {"message": "Task Manager API running"}

@app.get("/tasks", response_model=List[Task])
async def list_tasks(status: Optional[str] = None, focus: Optional[str] = None, q: Optional[str] = None):
    filter_dict = {}
    if status:
        filter_dict["status"] = status
    if focus:
        filter_dict["focus"] = focus
    if q:
        # basic text search on title/description
        filter_dict["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    items = await get_documents("task", filter_dict)
    # coerce timestamps to isoformat strings for JSON
    for it in items:
        for k in ("created_at", "updated_at", "due_date"):
            if isinstance(it.get(k), datetime):
                it[k] = it[k].isoformat()
    return items

@app.post("/tasks", response_model=Task)
async def create_task(payload: TaskCreate):
    data = payload.model_dump(exclude_none=True)
    created = await create_document("task", data)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create task")
    return created

@app.patch("/tasks/{task_id}", response_model=Task)
async def patch_task(task_id: str, payload: TaskUpdate):
    updates = payload.model_dump(exclude_none=True)
    updated = await update_document("task", task_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated

@app.delete("/tasks/{task_id}")
async def remove_task(task_id: str):
    ok = await delete_document("task", task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True}

# Simple AI suggestion endpoint (rule-based for now, can be swapped with LLM)
class AISuggestRequest(BaseModel):
    tasks: List[Task]

class AISuggestResponse(BaseModel):
    suggestions: List[str]

@app.post("/ai/suggest", response_model=AISuggestResponse)
async def ai_suggest(req: AISuggestRequest):
    suggestions: List[str] = []
    now = datetime.utcnow()
    high_urgent = [t for t in req.tasks if t.focus in ("high", "critical") and t.status == "pending"]
    overdue = [t for t in req.tasks if t.due_date and datetime.fromisoformat(str(t.due_date)) < now and t.status == "pending"]

    if overdue:
        suggestions.append(f"You have {len(overdue)} overdue task(s). Consider tackling the earliest due first.")
    if high_urgent:
        suggestions.append("Focus on high/critical tasks next. Batch similar ones for momentum.")

    # quick workload balance tip
    pending = [t for t in req.tasks if t.status == "pending"]
    if len(pending) > 7:
        suggestions.append("Your pending list is long; mark low-focus items as postponed or cancelled to reduce clutter.")

    if not suggestions:
        suggestions = ["Great job staying on top of things! Pick any pending item and move it forward."]

    return AISuggestResponse(suggestions=suggestions)
