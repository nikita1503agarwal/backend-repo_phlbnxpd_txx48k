"""
Database Schemas for Qik Office MVP

Each Pydantic model maps to a MongoDB collection (lowercased class name).
Use these schemas for validation and for the auto database viewer via GET /schema.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Unique email address")
    company: Optional[str] = Field(None, description="Company name (optional)")
    role: Optional[str] = Field(None, description="User role or title")
    avatar_url: Optional[str] = Field(None, description="Profile image URL")
    api_key: Optional[str] = Field(None, description="Simple API key for MVP auth")
    is_active: bool = Field(True, description="Whether user is active")


class Workspace(BaseModel):
    name: str = Field(..., description="Workspace name, e.g., Bright Media")
    owner_user_id: str = Field(..., description="Owner user ID")
    member_user_ids: List[str] = Field(default_factory=list, description="Members in workspace")
    description: Optional[str] = Field(None, description="Workspace description")


class Room(BaseModel):
    workspace_id: str = Field(..., description="Workspace ID")
    name: str = Field(..., description="Room name")
    type: str = Field("online", description="online | in-person | hybrid")
    description: Optional[str] = Field(None, description="Room purpose/notes")


class Meeting(BaseModel):
    room_id: str = Field(..., description="Room ID")
    title: str = Field(..., description="Meeting title")
    scheduled_at: datetime = Field(..., description="Scheduled date/time (ISO)")
    duration_minutes: int = Field(60, ge=0, description="Estimated duration")
    host_user_id: str = Field(..., description="Host user ID")
    participant_user_ids: List[str] = Field(default_factory=list, description="Participants")
    status: str = Field("scheduled", description="scheduled | live | completed | cancelled")
    recording_url: Optional[str] = Field(None, description="Recording URL if available")


class Note(BaseModel):
    meeting_id: str = Field(..., description="Meeting ID")
    author_user_id: str = Field(..., description="Author user ID")
    content: str = Field(..., description="Note content")


class Task(BaseModel):
    meeting_id: str = Field(..., description="Meeting ID")
    title: str = Field(..., description="Task title")
    assignee_user_id: Optional[str] = Field(None, description="Assignee user ID")
    due_date: Optional[datetime] = Field(None, description="Due date (optional)")
    status: str = Field("open", description="open | in_progress | done")


class FileAsset(BaseModel):
    meeting_id: str = Field(..., description="Meeting ID")
    uploaded_by_user_id: str = Field(..., description="Uploader ID")
    name: str = Field(..., description="File name")
    url: str = Field(..., description="File URL (MVP stores URL only)")
    type: Optional[str] = Field(None, description="mime/type or category")
