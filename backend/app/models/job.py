from enum import Enum
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class JobBase(BaseModel):
    tool_slug: str

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: str
    status: JobStatus
    progress: int = 0
    original_filename: str
    output_filename: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    
# In-memory DB cho MVP
jobs_db = {}