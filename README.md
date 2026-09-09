# OfficeFlow

OfficeFlow là dự án cộng đồng miễn phí, local/open-source-first, tập trung vào các workflow xử lý tài liệu chạy thật. Dự án không có pricing, paywall, billing hay tài khoản thương mại. Các file được xử lý theo job; lịch sử gần đây trong giao diện chỉ được lưu cục bộ trên thiết bị và chưa phải bộ nhớ đồng bộ lâu dài.

## Trạng thái triển khai

| Capability | Status | Ghi chú |
|---|---|---|
| PDF/Office conversion workflows | Implemented | Chạy qua API và processor hiện có. |
| PDF → Excel Document Brain | Implemented | Có native extraction, OCR fallback, evidence, truth, validation và audit. |
| Multi-page table continuation | Partial | Merge bảo thủ khi các bảng ở trang liền kề có repeated header tương đương; merged cells phức tạp vẫn cần review. |
| Upload and artifact boundary hardening | Implemented | Kiểm tra extension, giới hạn kích thước, file rỗng, path artifact và lỗi output. |
| Job persistence and restart recovery | Partial | Metadata job đã lưu SQLite; job đang chạy khi restart được đánh dấu cần retry. Durable worker recovery vẫn chưa có. |
| Authentication, ownership and authorization | Implemented | JWT session, password hashing và tenant-scoped job status/download. Bật `AUTH_REQUIRED=true` khi deploy production. |
| Durable queue and workers | Implemented (configurable) | Celery/Redis với late acknowledgement, bounded retry và prefetch=1; local fallback giữ cho development/test. |
| Document library and synchronized history | Planned | Frontend history hiện chỉ lưu trên thiết bị. |

Chi tiết gap, rủi ro và migration plan nằm trong [ARCHITECTURE_AUDIT.md](ARCHITECTURE_AUDIT.md) và [TECHNICAL_DEBT.md](TECHNICAL_DEBT.md).

Gap matrix định lượng riêng cho flagship PDF → Excel nằm trong [PDF_EXCEL_GAP_MATRIX.md](PDF_EXCEL_GAP_MATRIX.md). Điểm số trong ma trận là đánh giá engineering hiện trạng, không phải accuracy benchmark trên corpus bên ngoài.

## Các workflow hiện có

Repository giữ các workflow PDF và Office hiện có: PDF → Excel, Merge PDF, Split PDF, Compress PDF, Rotate PDF, PDF → JPG, Extract pages, Delete pages, PDF → Word, Word → PDF, Excel → PDF, PowerPoint → PDF, Images → PDF và image conversion.

## Production hardening additions

Set `JWT_SECRET_KEY` to a unique secret of at least 32 bytes and `AUTH_REQUIRED=true` in production. Users can register and log in through `/api/v1/auth/register` and `/api/v1/auth/login`; every job carries `user_id`, and status/download queries require the same owner. PostgreSQL deployment foundations are defined in `backend/app/persistence/sqlalchemy_models.py` and the async engine factory in `backend/app/persistence/database.py`; local SQLite compatibility remains available for regression tests.

For durable processing, set `REDIS_URL=redis://...` and run `PYTHONPATH=backend celery -A app.queue:celery_app worker --loglevel=INFO`. The table engine includes conservative merged-cell span inference, parent/child header hierarchy metadata and deterministic x-axis clustering for borderless layouts. Run the golden evaluator with `PYTHONPATH=backend python3 backend/tests/benchmark/evaluate.py backend/tests/benchmark/sample.json`; the score combines cell accuracy, merged-cell recall and header accuracy. The frontend sends bearer tokens and presents low-confidence review tasks while preserving raw extracted values.

## PDF → Excel quality model

PDF → Excel sử dụng ba mode. **Adaptive** dùng canonical document pipeline, native extraction và OCR fallback theo từng trang. **Tables** ưu tiên các bảng phát hiện được và không thêm sheet text. **Text** giữ toàn bộ text đọc được theo trang/dòng. Khi tài liệu có text native tốt, native layer được ưu tiên; OCR chỉ chạy ở trang trống, image-heavy, sparse hoặc có tín hiệu chất lượng thấp.

Workbook có `Overview`, các sheet bảng, `Document Text` khi được bật và `Audit`. Audit giữ raw text, object ID, page, confidence, engine và evidence JSON. Giá trị số hoặc tiền tệ chỉ được chuyển thành kiểu Excel khi parse đủ rõ ràng; raw text không bị âm thầm ghi đè. Các bảng ở trang liền kề có repeated header tương đương được merge vào một worksheet và diagnostics giữ `source_pages`, `merged_table_count` và `multi_page_tables`. Scan mờ, merged cells phức tạp, bảng nghiêng, biểu đồ và layout cực phức tạp có thể cần review thủ công; hệ thống ghi warning thay vì cam kết khôi phục hoàn hảo.

## Kiến trúc Document Intelligence

Pipeline chính là:

```text
Upload
  → validation + SHA-256 fingerprint
  → page-level profile
  → processing plan
  → native text/table extraction
  → OCR fallback theo trang
  → OCR tokens, bbox, confidence và pass diagnostics
  → canonical document model
  → semantic entities
  → provenance/evidence
  → workbook + audit metadata
```

`CanonicalDocument` là lớp trung tâm kết nối `DocumentSource`, `DocumentProfile`, `DocumentQuality`, `DocumentPage`, `DocumentBlock`, `DocumentTable`, `DocumentEntity`, `Evidence` và `ProcessingEvent`. OCR engine được trừu tượng hóa qua adapter; Tesseract là adapter local mặc định. Có thể bổ sung PaddleOCR, EasyOCR hoặc engine khác mà không đổi processor/export contract.

Mỗi trang có profile riêng gồm kích thước, rotation, native character count, images, table/vector signals, blank/image-heavy status, quality warnings và cờ `ocr_recommended`. Tesseract thử hai layout pass (`PSM 6` và `PSM 11`) rồi chọn pass theo confidence, tỷ lệ ký tự hợp lệ và số token có nghĩa. Kết quả lưu language, preprocessing profile, raster size, pass scores và selected pass.

## Cài đặt

Backend yêu cầu Python 3.11+ và các package trong `backend/requirements.txt`. OCR local yêu cầu Tesseract cùng language packs. Trên Ubuntu, cài tối thiểu:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-vie
```

Các language code được API cho phép gồm `eng`, `vie`, `chi_sim`, `jpn`, `kor`, `tha`, `ind`, `fra`, `deu`, `spa`, `por`, `ita`, `rus` và `ara`, nhưng code chỉ được dùng đầy đủ khi language pack tương ứng đã cài. `auto` mặc định chọn `eng+vie` khi có sẵn và fallback an toàn nếu thiếu pack.

Cài dependency và chạy backend:

```bash
sudo pip3 install -r backend/requirements.txt
PYTHONPATH=backend uvicorn main:app --reload --port 8000
```

Chạy frontend:

```bash
cd frontend
npm ci
npm run dev
```

SQLite JobStore mặc định được tạo tại `backend/storage/jobs.sqlite3` và bị loại khỏi Git. Có thể đổi đường dẫn bằng biến cấu hình `JOB_DB_PATH`. Hai endpoint vận hành là `/health` cho liveness và `/health/ready` cho readiness, bao gồm kiểm tra thư mục storage và SQLite.

## Kiểm thử

Regression tests tạo fixture PDF native, bảng có đường kẻ, scan image-only và kiểm tra workbook mở được bằng `openpyxl`, sheet structure, typed money, provenance, OCR pass metadata, API options validation, result metadata và download.

```bash
PYTHONPATH=backend python3 -m compileall -q backend
PYTHONPATH=backend pytest -q
cd frontend && npm run build
cd .. && git diff --check
```

## Giới hạn và privacy

Giới hạn upload hiện tại là 25 MB mỗi file và tối đa 10 file theo tool. File rỗng bị từ chối. Nếu một request có cùng basename nhiều lần, backend đổi tên bản lưu nội bộ để không ghi đè nguồn đã nhận. Input tạm được lưu trong job directory và dọn sau khi xử lý; output lỗi bị xóa, còn output thành công chưa có cleanup TTL tự động. Download chỉ chấp nhận artifact filename do backend sinh và kiểm tra artifact nằm trong output directory. Job metadata hiện có persistence SQLite cho local/test, nhưng chưa có PostgreSQL, authentication hoặc ownership authorization; vì vậy không nên gửi tài liệu nhạy cảm vào môi trường chưa được harden theo chính sách triển khai của bạn. SHA-256 chỉ là fingerprint nội bộ, không phải cam kết bảo mật hoặc deduplication persistence.

OCR và table reconstruction là các quá trình xác suất/heuristic. OfficeFlow công khai confidence, warning và evidence để người dùng kiểm tra; không tuyên bố tái tạo 100% mọi PDF scan hoặc layout bất thường.

## Document Brain 4.0 contracts

Canonical documents expose a versioned `DocumentState` lifecycle: `uploaded`, `identified`, `profiled`, `understanding`, `extracted`, `validated`, `review_required`, `ready` và `failed`. Mỗi kết quả cũng lưu `PipelineVersion` để biết phiên bản pipeline, OCR, layout, table, semantic và export đã tạo ra artifact.

Quality không được suy đoán thành một con số duy nhất. `quality_dimensions` giữ các thành phần source confidence, OCR confidence, layout confidence, semantic confidence, consistency confidence, evidence coverage và overall score. Mỗi thành phần được tính từ metrics có trong canonical result và có thể kiểm tra trong diagnostics.

Validation deterministic kiểm tra evidence coverage, độ nhất quán số cột của table và tính hợp lý sơ bộ của các giá trị tiền tệ. Khi entity quan trọng có confidence thấp hoặc thiếu evidence, hệ thống tạo `ReviewTask` với field, raw value, priority, reason, confidence và evidence. Review task không sửa raw source value; nó chỉ đánh dấu phần cần người dùng kiểm tra.

Các layer như knowledge graph, multi-document aggregation, document comparison, RAG và workflow automation vẫn là extension points tương lai. Chúng không được giả lập trong giao diện khi backend chưa thực sự cung cấp capability tương ứng.

## Document Truth Model 5.0

Document Brain phân biệt raw observation, extracted value, normalized value, inferred value và verified value. Các trạng thái `unknown`, `not_found`, `unsupported`, `uncertain` và `conflicting` không bị chuyển thành dữ liệu chắc chắn. `DocumentFact` giữ raw value, normalized value, truth status, confidence, explanation và evidence.

Canonical result cũng có graph edges typed. Ví dụ một invoice fact có thể liên kết với money fact bằng quan hệ `has_amount`; đây là quan hệ được suy ra từ các entity đã có evidence, không phải dữ liệu được bịa thêm. PDF → Excel đưa facts, graph edges, validation và review tasks vào Audit sheet cũng như job metadata để có thể kiểm tra hai chiều từ semantic result về source evidence.
