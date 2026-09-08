from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from main import app


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
    assert client.get(f"/api/v1/jobs/{job_id}/download").status_code == 200
