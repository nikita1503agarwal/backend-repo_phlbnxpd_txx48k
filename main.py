import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson.objectid import ObjectId

from database import create_document, get_documents, db
from schemas import User, Workspace, Room, Meeting, Note, Task


app = FastAPI(title="Qik Office API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------
# Utility serializers
# ----------------------------

def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    d = doc.copy()
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Convert datetimes to isoformat strings
    for k, v in list(d.items()):
        try:
            import datetime as _dt
            if isinstance(v, (_dt.datetime, _dt.date)):
                d[k] = v.isoformat()
        except Exception:
            pass
    return d


def serialize_list(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [serialize_doc(i) for i in items]


# ----------------------------
# Health + Schema endpoints
# ----------------------------

@app.get("/")
def read_root():
    return {"app": "Qik Office API", "status": "ok"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


@app.get("/schema")
def get_schema():
    # Minimal schema description for viewer/tools
    return {
        "collections": [
            "user", "workspace", "room", "meeting", "note", "task", "fileasset"
        ]
    }


# ----------------------------
# Auth & Users (MVP simple signup)
# ----------------------------

class SignupRequest(BaseModel):
    name: str
    email: str
    company: Optional[str] = None


@app.post("/api/signup")
def signup(req: SignupRequest):
    # Generate a very simple API key for the MVP
    api_key = uuid4().hex
    user = User(name=req.name, email=req.email, company=req.company, api_key=api_key)
    user_id = create_document("user", user)
    return {"id": user_id, "api_key": api_key}


# ----------------------------
# Workspaces
# ----------------------------

class CreateWorkspaceRequest(BaseModel):
    name: str
    owner_user_id: str
    description: Optional[str] = None


@app.post("/api/workspaces")
def create_workspace(req: CreateWorkspaceRequest):
    ws = Workspace(name=req.name, owner_user_id=req.owner_user_id, description=req.description)
    ws_id = create_document("workspace", ws)
    return {"id": ws_id}


@app.get("/api/workspaces")
def list_workspaces(owner_user_id: Optional[str] = None):
    filter_q: Dict[str, Any] = {}
    if owner_user_id:
        filter_q["owner_user_id"] = owner_user_id
    items = get_documents("workspace", filter_q)
    return serialize_list(items)


# ----------------------------
# Rooms
# ----------------------------

class CreateRoomRequest(BaseModel):
    workspace_id: str
    name: str
    type: Optional[str] = "online"  # online | in-person | hybrid
    description: Optional[str] = None


@app.post("/api/rooms")
def create_room(req: CreateRoomRequest):
    room = Room(
        workspace_id=req.workspace_id,
        name=req.name,
        type=req.type or "online",
        description=req.description,
    )
    room_id = create_document("room", room)
    return {"id": room_id}


@app.get("/api/rooms")
def list_rooms(workspace_id: str):
    items = get_documents("room", {"workspace_id": workspace_id})
    return serialize_list(items)


# ----------------------------
# Meetings
# ----------------------------

class CreateMeetingRequest(BaseModel):
    room_id: str
    title: str
    scheduled_at: str  # ISO datetime string for simplicity in MVP
    duration_minutes: int = 60
    host_user_id: str
    participant_user_ids: List[str] = []


@app.post("/api/meetings")
def create_meeting(req: CreateMeetingRequest):
    from datetime import datetime
    scheduled_dt = datetime.fromisoformat(req.scheduled_at)
    mtg = Meeting(
        room_id=req.room_id,
        title=req.title,
        scheduled_at=scheduled_dt,
        duration_minutes=req.duration_minutes,
        host_user_id=req.host_user_id,
        participant_user_ids=req.participant_user_ids,
    )
    meeting_id = create_document("meeting", mtg)
    return {"id": meeting_id}


@app.get("/api/meetings")
def list_meetings(room_id: Optional[str] = None):
    q: Dict[str, Any] = {"room_id": room_id} if room_id else {}
    items = get_documents("meeting", q)
    return serialize_list(items)


# ----------------------------
# Notes
# ----------------------------

class CreateNoteRequest(BaseModel):
    meeting_id: str
    author_user_id: str
    content: str


@app.post("/api/notes")
def create_note(req: CreateNoteRequest):
    note = Note(meeting_id=req.meeting_id, author_user_id=req.author_user_id, content=req.content)
    note_id = create_document("note", note)
    return {"id": note_id}


@app.get("/api/notes")
def list_notes(meeting_id: str):
    items = get_documents("note", {"meeting_id": meeting_id})
    return serialize_list(items)


# ----------------------------
# Tasks (To-dos)
# ----------------------------

class CreateTaskRequest(BaseModel):
    meeting_id: str
    title: str
    assignee_user_id: Optional[str] = None
    due_date: Optional[str] = None  # ISO date


@app.post("/api/tasks")
def create_task(req: CreateTaskRequest):
    from datetime import datetime
    due_dt = datetime.fromisoformat(req.due_date) if req.due_date else None
    task = Task(meeting_id=req.meeting_id, title=req.title, assignee_user_id=req.assignee_user_id, due_date=due_dt)
    task_id = create_document("task", task)
    return {"id": task_id}


@app.get("/api/tasks")
def list_tasks(meeting_id: Optional[str] = None, assignee_user_id: Optional[str] = None):
    q: Dict[str, Any] = {}
    if meeting_id:
        q["meeting_id"] = meeting_id
    if assignee_user_id:
        q["assignee_user_id"] = assignee_user_id
    items = get_documents("task", q)
    return serialize_list(items)


# Simple update endpoint for task status
class UpdateTaskStatusRequest(BaseModel):
    status: str  # open | in_progress | done


@app.patch("/api/tasks/{task_id}/status")
def update_task_status(task_id: str, body: UpdateTaskStatusRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        oid = ObjectId(task_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid task id")
    res = db["task"].update_one({"_id": oid}, {"$set": {"status": body.status}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task_id, "status": body.status}


# ----------------------------
# Dashboard summary
# ----------------------------

@app.get("/api/dashboard/summary")
def dashboard_summary(workspace_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    # Rooms in workspace
    rooms = list(db["room"].find({"workspace_id": workspace_id}, {"_id": 1}))
    room_ids = [str(r["_id"]) for r in rooms]

    # Meetings in rooms
    meetings = []
    if room_ids:
        meetings = list(db["meeting"].find({"room_id": {"$in": room_ids}}, {"_id": 1}))
    meeting_ids = [str(m.get("_id")) for m in meetings]

    # Tasks and completion
    q_tasks: Dict[str, Any] = {}
    if meeting_ids:
        q_tasks["meeting_id"] = {"$in": meeting_ids}
    tasks = list(db["task"].find(q_tasks))
    total_tasks = len(tasks)
    done_tasks = sum(1 for t in tasks if t.get("status") == "done")

    return {
        "rooms": len(rooms),
        "meetings": len(meetings),
        "tasks": total_tasks,
        "tasks_done": done_tasks,
        "completion_rate": (done_tasks / total_tasks) if total_tasks else 0.0,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
