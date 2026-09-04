from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List
import uuid
import shutil
import os
from datetime import datetime
from app.models.job import JobResponse, JobStatus, jobs_db
from app.core.config import settings
from app.processors.factory import get_processor

router = APIRouter()

def process_job_task(job_id: str, input_paths: List[str], tool_slug: str):
    job = jobs_db.get(job_id)
    if not job: return
    
    job.status = JobStatus.PROCESSING
    job.progress = 20
    
    processor = get_processor(tool_slug)
    if not processor:
        job.status = JobStatus.FAILED
        job.error_message = f"Công cụ {tool_slug} chưa được hỗ trợ."
        return
        
    ext = ".zip" if tool_slug == "split-pdf" else (".pdf" if tool_slug == "merge-pdf" else ".xlsx")
    output_filename = f"OfficeFlow_{tool_slug}_{job_id}{ext}"
    output_path = os.path.join(settings.OUTPUT_DIR, output_filename)
    
    try:
        job.progress = 60
        success = processor.process(input_paths, output_path)
        if success:
            job.status = JobStatus.SUCCESS
            job.progress = 100
            job.output_filename = output_filename
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_message = str(e)

@router.post("/", response_model=JobResponse)
async def create_job(
    background_tasks: BackgroundTasks,
    tool_slug: str = Form(...),
    files: List[UploadFile] = File(...)
):
    job_id = str(uuid.uuid4())
    
    # Tạo thư mục tạm riêng cho job này để chứa nhiều file
    job_dir = os.path.join(settings.UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    input_paths = []
    original_names = []
    
    try:
        for file in files:
            file_path = os.path.join(job_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            input_paths.append(file_path)
            original_names.append(file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể lưu file: {str(e)}")
        
    job = JobResponse(
        id=job_id,
        tool_slug=tool_slug,
        status=JobStatus.QUEUED,
        progress=0,
        original_filename=", ".join(original_names),
        created_at=datetime.utcnow()
    )
    
    jobs_db[job_id] = job
    background_tasks.add_task(process_job_task, job_id, input_paths, tool_slug)
    
    return job

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    job = jobs_db.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy Job")
    return job

@router.get("/{job_id}/download")
async def download_job(job_id: str):
    job = jobs_db.get(job_id)
    if not job or job.status != JobStatus.SUCCESS:
        raise HTTPException(status_code=400, detail="File chưa sẵn sàng hoặc đã bị lỗi.")
    
    file_path = os.path.join(settings.OUTPUT_DIR, job.output_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File không tồn tại (đã bị dọn dẹp).")
        
    return FileResponse(
        path=file_path, 
        filename=job.output_filename,
        media_type="application/octet-stream"
    )