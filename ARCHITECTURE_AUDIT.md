# Architecture Audit

## Kết luận

LuNu WPS hiện là một ứng dụng FastAPI + Vue chạy theo mô hình xử lý job trong phiên backend. Năng lực **Document Brain cho PDF → Excel đã được triển khai thực tế** ở mức local-first, gồm native extraction, OCR fallback, canonical model, evidence, truth facts, validation và audit workbook. Tuy nhiên, hệ thống chưa phải một nền tảng document operating system production-ready vì job metadata và artifact ownership chưa được lưu bền vững.

Milestone hiện tại harden boundary của job lifecycle mà không thay đổi kiến trúc xử lý tài liệu. Upload được giới hạn theo extension, kích thước và file rỗng; các artifact download được kiểm tra path; lỗi xử lý không để lại output hỏng; upload trùng basename không ghi đè nguồn đã nhận.

## Current

| Area | Current implementation | Status |
|---|---|---|
| Frontend | Vue 3 + Vite, tool workspace, local history | Implemented |
| API | FastAPI multipart upload, status polling, download | Implemented |
| Job execution | FastAPI `BackgroundTasks`, in-memory `jobs_db` | Partial |
| Input storage | Per-job temporary directory, removed after processing | Implemented |
| Artifact storage | Local output directory, generated filename, no TTL cleanup | Partial |
| Document intelligence | Canonical PDF pipeline with native extraction and Tesseract adapter | Implemented |
| Truth and evidence | Facts, typed graph edges, validation and review tasks | Implemented for PDF → Excel |
| Authentication | None | Planned |
| Ownership and authorization | None; resources are addressed by job ID | Planned / security gap |
| Durable persistence | None | Planned |
| Queue and worker recovery | None; in-process background task | Planned |
| E2E deployment hardening | Not present | Planned |

## Target

The target architecture is incremental:

```text
Authenticated user
  → persistent document and job records
  → durable artifact metadata
  → queue and restartable worker
  → Document Brain pipeline
  → evidence-backed result and review state
  → authorized artifact download
  → document library and history
```

The core processing contract should remain the `CanonicalDocument`. Storage, queue and identity layers should wrap that contract rather than replace it.

## Gap

The highest-impact gaps are persistence, identity, authorization, durable job recovery, artifact retention policy and end-to-end security tests. The current in-memory job registry means a backend restart loses status records even when output files remain on disk. The current local download endpoint is safe against basic path traversal after this milestone, but it does not yet prove that the requester owns the job.

## Migration

1. **M01 — Audit and lifecycle hardening:** document the actual architecture, validate upload boundaries, protect artifact path resolution, clean failed outputs and add regression tests. Completed in this change.
2. **M02 — Identity foundation:** introduce explicit user/session identity only after selecting the deployment trust model. Do not infer ownership from an untrusted client field.
3. **M03 — Durable persistence:** add migrations and persistent records for users, documents, jobs, artifacts, pipeline versions and review tasks. Keep local filesystem storage behind an artifact service.
4. **M04 — Restartable execution:** move processing to a durable queue and worker with idempotency, leases and recovery semantics.
5. **M05 — Workspace and review:** expose persisted documents, evidence and review tasks in the frontend with authorization checks.

## Risks

The largest migration risk is coupling future database records directly to current in-memory response shapes. A second risk is claiming privacy before authentication and authorization exist. A third risk is deleting output files without a retention policy that is visible to users. All future milestones should preserve the existing PDF regression fixtures and canonical diagnostics.

## Verification baseline

The repository baseline is:

```bash
PYTHONPATH=backend python3 -m compileall -q backend
PYTHONPATH=backend pytest -q
cd frontend && npm run build
cd .. && git diff --check
```

The implementation status in this file is intentionally explicit. Items marked **Planned** are not represented as working UI or backend behavior.

## References

[1]: README.md "LuNu WPS implementation notes and limitations"
[2]: backend/app/api/v1/endpoints/jobs.py "Job upload, processing and download endpoint"
[3]: backend/app/document_ai/pipeline.py "Canonical document processing pipeline"

*Author: Manus AI*
