import json
import os
import re
import shutil
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.api.v1.endpoints.auth import UserResponse, current_user
from app.models.job import JobResponse, JobStatus
from app.persistence.job_store import JobStore
from app.processors.factory import get_processor
from app.queue import enqueue_job
from app.tool_registry import get_tool

router = APIRouter()
logger = logging.getLogger("officeflow.jobs")
MAX_FILE_SIZE = 25 * 1024 * 1024
MAX_FILES = 10
_ALLOWED_OCR_CODES = {"eng", "vie", "chi_sim", "jpn", "kor", "tha", "ind", "fra", "deu", "spa", "por", "ita", "rus", "ara"}
job_store = JobStore(settings.JOB_DB_PATH)
job_store.recover_incomplete()


def _safe_filename(filename: str | None) -> str:
    name = os.path.basename(filename or "document")
    if not name or name.startswith(".") or name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ.")
    return name


def _cleanup(paths: List[str]) -> None:
    if paths:
        shutil.rmtree(os.path.dirname(paths[0]), ignore_errors=True)


def _output_path(filename: str | None) -> str:
    """Resolve an internally generated artifact without allowing path escape."""
    if not filename or os.path.basename(filename) != filename:
        raise HTTPException(status_code=404, detail="Artifact không hợp lệ.")
    output_dir = os.path.realpath(settings.OUTPUT_DIR)
    candidate = os.path.realpath(os.path.join(output_dir, filename))
    if os.path.dirname(candidate) != output_dir:
        raise HTTPException(status_code=404, detail="Artifact không hợp lệ.")
    return candidate


def _validate_options(tool_slug: str, raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="Options phải là một JSON object.")
    if tool_slug != "pdf-to-excel":
        return raw
    allowed = {"extraction", "include_text", "ocr_fallback", "ocr_language", "use_canonical"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise HTTPException(status_code=400, detail=f"Options không được hỗ trợ: {', '.join(unknown)}.")
    result = {
        "extraction": raw.get("extraction", "auto"),
        "include_text": raw.get("include_text", True),
        "ocr_fallback": raw.get("ocr_fallback", True),
        "ocr_language": raw.get("ocr_language", "auto"),
        "use_canonical": raw.get("use_canonical", True),
    }
    if result["extraction"] not in {"auto", "tables", "text"}:
        raise HTTPException(status_code=400, detail="extraction phải là auto, tables hoặc text.")
    for key in ("include_text", "ocr_fallback", "use_canonical"):
        if not isinstance(result[key], bool):
            raise HTTPException(status_code=400, detail=f"{key} phải là boolean.")
    language = result["ocr_language"]
    if not isinstance(language, str) or not language:
        raise HTTPException(status_code=400, detail="ocr_language phải là chuỗi hoặc auto.")
    if language != "auto":
        codes = language.split("+")
        if any(code not in _ALLOWED_OCR_CODES for code in codes):
            raise HTTPException(status_code=400, detail="ocr_language chứa language code chưa được hỗ trợ.")
    return result


def _public_error(exc: Exception) -> str:
    message = str(exc).replace("\\", "/")
    message = re.sub(r"(?:/[^\s:'\"]+)+", "[path]", message)
    return message[:500] or "Xử lý tài liệu thất bại."


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "value") and isinstance(value.value, (str, int, float, bool)):
        return value.value
    if hasattr(value, "__dict__"):
        return _json_safe(value.__dict__)
    return str(value)


def process_job_task(job_id: str, input_paths: List[str], tool_slug: str, options: dict, user_id: str = "local-dev") -> None:
    job = job_store.get_for_user(job_id, user_id)
    if not job:
        _cleanup(input_paths)
        return
    job.status = JobStatus.PROCESSING
    logger.info("job_processing", extra={"job_id": job_id, "document_id": job_id, "tool_slug": tool_slug})
    job.progress = 10
    job_store.save(job)
    processor = get_processor(tool_slug)
    tool = get_tool(tool_slug)
    if not processor or not tool:
        job.status = JobStatus.FAILED
        job.error_message = "Công cụ chưa được hỗ trợ trong phiên bản hiện tại."
        job_store.save(job)
        _cleanup(input_paths)
        return
    output_filename = f"OfficeFlow_{tool_slug}_{job_id}{tool.output_extension}"
    output_path = os.path.join(settings.OUTPUT_DIR, output_filename)
    try:
        job.progress = 25
        if processor.process(input_paths, output_path, options):
            job.progress = 90
            diagnostics = _json_safe(getattr(processor, "last_diagnostics", {}))
            job.status = JobStatus.SUCCESS
            job.progress = 100
            job.output_filename = output_filename
            job.completed_at = datetime.now(timezone.utc)
            job.result_metadata = _json_safe({
                "output_bytes": os.path.getsize(output_path) if os.path.exists(output_path) else 0,
                "output_extension": tool.output_extension,
                "tool": tool.name,
                "options": options,
                "source_fingerprint": diagnostics.get("fingerprint"),
                "pages": diagnostics.get("pages", 0),
                "tables": diagnostics.get("tables", 0),
                "ocr_pages": diagnostics.get("ocr_pages", 0),
                "low_confidence_count": diagnostics.get("low_confidence_cells", 0),
                "warnings": diagnostics.get("warnings", []),
                "document_state": diagnostics.get("document_state", "unknown"),
                "quality_dimensions": diagnostics.get("quality_dimensions", {}),
                "validation_results": diagnostics.get("validation_results", []),
                "review_tasks": diagnostics.get("review_tasks", []),
                "facts_count": diagnostics.get("facts_count", diagnostics.get("facts", 0)),
                "graph_edges_count": diagnostics.get("graph_edges_count", diagnostics.get("graph_edges", 0)),
                "truth_facts": diagnostics.get("truth_facts", []),
                "truth_graph_edges": diagnostics.get("truth_graph_edges", []),
                "review_required": bool(diagnostics.get("review_tasks")),
                "audit_available": bool(diagnostics),
                "diagnostics": diagnostics,
            })
            job_store.save(job)
    except Exception as exc:
        logger.exception("job_processing_failed", extra={"job_id": job_id, "document_id": job_id, "tool_slug": tool_slug})
        job.status = JobStatus.FAILED
        job.error_message = _public_error(exc)
        job.completed_at = datetime.now(timezone.utc)
        job_store.save(job)
        if os.path.exists(output_path):
            os.remove(output_path)
    finally:
        _cleanup(input_paths)


@router.post("/", response_model=JobResponse)
async def create_job(
    background_tasks: BackgroundTasks,
    tool_slug: str = Form(...),
    options_json: str = Form("{}"),
    files: List[UploadFile] = File(...),
    user: UserResponse = Depends(current_user),
):
    tool = get_tool(tool_slug)
    if not tool or not tool.enabled:
        raise HTTPException(status_code=400, detail="Công cụ này chưa được bật.")
    if not files or len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Vui lòng chọn từ 1 đến {MAX_FILES} file.")
    if not tool.multiple_files and len(files) > 1:
        raise HTTPException(status_code=400, detail="Công cụ này chỉ nhận một file.")
    try:
        options = _validate_options(tool_slug, json.loads(options_json or "{}"))
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
            # Multiple uploads may contain the same basename. Never overwrite a
            # previously accepted input because that changes the user's source.
            destination = os.path.join(job_dir, safe_name)
            if os.path.exists(destination):
                stem, suffix = os.path.splitext(safe_name)
                counter = 2
                while os.path.exists(destination):
                    destination = os.path.join(job_dir, f"{stem}_{counter}{suffix}")
                    counter += 1
            size = 0
            with open(destination, "wb") as buffer:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_FILE_SIZE:
                        raise HTTPException(status_code=413, detail=f"{safe_name} vượt quá giới hạn 25 MB.")
                    buffer.write(chunk)
            if size == 0:
                raise HTTPException(status_code=400, detail=f"{safe_name} là file rỗng.")
            input_paths.append(destination)
            original_names.append(safe_name)
    except HTTPException:
        _cleanup(input_paths or [os.path.join(job_dir, "placeholder")])
        raise
    except Exception as exc:
        _cleanup(input_paths or [os.path.join(job_dir, "placeholder")])
        raise HTTPException(status_code=500, detail=f"Không thể lưu file: {_public_error(exc)}") from exc

    job = JobResponse(id=job_id, user_id=user.id, tool_slug=tool_slug, status=JobStatus.QUEUED, progress=0, original_filename=", ".join(original_names), created_at=datetime.now(timezone.utc))
    job_store.save(job)
    if enqueue_job(job_id, input_paths, tool_slug, options, user.id) is None:
        background_tasks.add_task(process_job_task, job_id, input_paths, tool_slug, options, user.id)
    return job


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str, user: UserResponse = Depends(current_user)):
    job = job_store.get_for_user(job_id, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy Job")
    return job


@router.get("/{job_id}/download")
async def download_job(job_id: str, user: UserResponse = Depends(current_user)):
    job = job_store.get_for_user(job_id, user.id)
    if not job or job.status != JobStatus.SUCCESS:
        raise HTTPException(status_code=400, detail="File chưa sẵn sàng hoặc đã bị lỗi.")
    file_path = _output_path(job.output_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File không tồn tại.")
    return FileResponse(path=file_path, filename=job.output_filename, media_type="application/octet-stream")
