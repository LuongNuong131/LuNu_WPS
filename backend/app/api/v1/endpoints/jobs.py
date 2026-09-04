from datetime import datetime
import json
import os
import shutil
import uuid
from typing import List

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.models.job import JobResponse, JobStatus, jobs_db
from app.processors.factory import get_processor
from app.tool_registry import get_tool

router = APIRouter()
MAX_FILE_SIZE = 25 * 1024 * 1024
MAX_FILES = 10


def _safe_filename(filename: str | None) -> str:
    name = os.path.basename(filename or "document")
    if not name or name.startswith("."):
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ.")
    return name


def _cleanup(paths: List[str]) -> None:
    if paths:
        shutil.rmtree(os.path.dirname(paths[0]), ignore_errors=True)


def process_job_task(job_id: str, input_paths: List[str], tool_slug: str, options: dict) -> None:
    job = jobs_db.get(job_id)
    if not job:
        _cleanup(input_paths)
        return
    job.status = JobStatus.PROCESSING
    job.progress = 20
    processor = get_processor(tool_slug)
    tool = get_tool(tool_slug)
    if not processor or not tool:
        job.status = JobStatus.FAILED
        job.error_message = "Công cụ chưa được hỗ trợ trong phiên bản hiện tại."
        _cleanup(input_paths)
        return
    output_filename = f"OfficeFlow_{tool_slug}_{job_id}{tool.output_extension}"
    output_path = os.path.join(settings.OUTPUT_DIR, output_filename)
    try:
        job.progress = 55
        if processor.process(input_paths, output_path, options):
            job.status = JobStatus.SUCCESS
            job.progress = 100
            job.output_filename = output_filename
    except Exception as exc:
        job.status = JobStatus.FAILED
        job.error_message = str(exc)
    finally:
        _cleanup(input_paths)


@router.post("/", response_model=JobResponse)
async def create_job(
    background_tasks: BackgroundTasks,
    tool_slug: str = Form(...),
    options_json: str = Form("{}"),
    files: List[UploadFile] = File(...),
):
    tool = get_tool(tool_slug)
    if not tool or not tool.enabled:
        raise HTTPException(status_code=400, detail="Công cụ này chưa được bật.")
    if not files or len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Vui lòng chọn từ 1 đến {MAX_FILES} file.")
    if not tool.multiple_files and len(files) > 1:
        raise HTTPException(status_code=400, detail="Công cụ này chỉ nhận một file.")
    try:
        options = json.loads(options_json or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Options không hợp lệ.") from exc

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(settings.UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    input_paths: List[str] = []
    original_names: List[str] = []
    try:
        for upload in files:
            safe_name = _safe_filename(upload.filename)
            extension = os.path.splitext(safe_name)[1].lower()
            if extension not in tool.input_extensions:
                allowed = ", ".join(tool.input_extensions)
                raise HTTPException(status_code=400, detail=f"Định dạng {extension or 'file'} không hợp lệ. Chấp nhận: {allowed}.")
            destination = os.path.join(job_dir, safe_name)
            size = 0
            with open(destination, "wb") as buffer:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_FILE_SIZE:
                        raise HTTPException(status_code=413, detail=f"{safe_name} vượt quá giới hạn 25 MB.")
                    buffer.write(chunk)
            input_paths.append(destination)
            original_names.append(safe_name)
    except HTTPException:
        _cleanup(input_paths or [os.path.join(job_dir, "placeholder")])
        raise
    except Exception as exc:
        _cleanup(input_paths or [os.path.join(job_dir, "placeholder")])
        raise HTTPException(status_code=500, detail=f"Không thể lưu file: {exc}") from exc

    job = JobResponse(id=job_id, tool_slug=tool_slug, status=JobStatus.QUEUED, progress=0, original_filename=", ".join(original_names), created_at=datetime.utcnow())
    jobs_db[job_id] = job
    background_tasks.add_task(process_job_task, job_id, input_paths, tool_slug, options)
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
    file_path = os.path.join(settings.OUTPUT_DIR, job.output_filename or "")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File không tồn tại.")
    return FileResponse(path=file_path, filename=job.output_filename, media_type="application/octet-stream")
