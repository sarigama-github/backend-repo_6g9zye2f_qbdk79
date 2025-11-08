from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

# Each Pydantic model corresponds to a MongoDB collection named after the lowercased class name

class Task(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    focus: Literal["low", "medium", "high", "critical"] = "medium"
    status: Literal["pending", "postponed", "cancelled", "done"] = "pending"
    due_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if isinstance(v, datetime) else v,
        }
