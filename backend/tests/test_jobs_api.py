from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from main import app
from app.api.v1.endpoints.jobs import _output_path
from app.models.job import JobResponse, JobStatus
from app.persistence.job_store import JobStore


def pdf_bytes() -> bytes:
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream)
    pdf.drawString(72, 720, "Invoice INV-API-001")
    pdf.drawString(72, 700, "Total 1.250.000 VNĐ")
    pdf.save()
    return stream.getvalue()


def test_pdf_to_excel_rejects_invalid_options() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/jobs/", data={"tool_slug": "pdf-to-excel", "options_json": '{"include_text":"yes"}'}, files={"files": ("invoice.pdf", pdf_bytes(), "application/pdf")})
    assert response.status_code == 400
    assert "boolean" in response.json()["detail"]


def test_pdf_to_excel_job_returns_metadata(tmp_path: Path) -> None:
    client = TestClient(app)
    response = client.post("/api/v1/jobs/", data={"tool_slug": "pdf-to-excel", "options_json": '{"extraction":"auto","include_text":true,"ocr_fallback":true,"ocr_language":"auto","use_canonical":true}'}, files={"files": ("invoice.pdf", pdf_bytes(), "application/pdf")})
    assert response.status_code == 200, response.text
    job_id = response.json()["id"]
    status = client.get(f"/api/v1/jobs/{job_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "SUCCESS"
    assert body["result_metadata"]["pages"] == 1
    assert body["result_metadata"]["audit_available"] is True
    assert body["result_metadata"]["document_state"] in {"ready", "review_required"}
    assert "quality_dimensions" in body["result_metadata"]
    assert "validation_results" in body["result_metadata"]
    assert "review_tasks" in body["result_metadata"]
    assert body["result_metadata"]["facts_count"] >= 1
    assert "truth_facts" in body["result_metadata"]
    assert "truth_graph_edges" in body["result_metadata"]
    assert client.get(f"/api/v1/jobs/{job_id}/download").status_code == 200


def test_upload_rejects_empty_file() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/jobs/",
        data={"tool_slug": "pdf-to-excel", "options_json": "{}"},
        files={"files": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "rỗng" in response.json()["detail"]


def test_download_path_must_stay_inside_output_directory() -> None:
    from fastapi import HTTPException

    try:
        _output_path("../outside.xlsx")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("path traversal was not rejected")


def test_job_store_survives_reopen_and_recovers_incomplete(tmp_path: Path) -> None:
    database = tmp_path / "jobs.sqlite3"
    job = JobResponse(
        id="restart-test",
        tool_slug="pdf-to-excel",
        status=JobStatus.PROCESSING,
        progress=42,
        original_filename="invoice.pdf",
        created_at=datetime.now(timezone.utc),
    )
    JobStore(str(database)).save(job)

    reopened = JobStore(str(database))
    restored = reopened.get("restart-test")
    assert restored is not None
    assert restored.status == JobStatus.PROCESSING
    assert restored.progress == 42
    assert reopened.recover_incomplete() == 1
    recovered = reopened.get("restart-test")
    assert recovered is not None
    assert recovered.status == JobStatus.FAILED
    assert "restarted" in (recovered.error_message or "")


def test_health_endpoints_report_runtime_state() -> None:
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    readiness = client.get("/health/ready")
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "ready"
    assert readiness.json()["database"]["backend"] == "sqlite"
