# OfficeFlow

> **Local-first document intelligence for real-world PDF → Excel workflows.**

OfficeFlow là nền tảng xử lý PDF/Office miễn phí và open-source-first, được xây dựng cho các tài liệu không hoàn hảo: PDF scan, trang bị nghiêng, bảng không có đường kẻ, bảng kéo dài qua nhiều trang và dữ liệu tài chính cần kiểm tra trước khi tin cậy. Hệ thống giữ lại **raw value, evidence, confidence, validation result và review task** thay vì âm thầm biến một suy đoán thành dữ liệu chắc chắn.

[![Backend](https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi&logoColor=white)](backend/) [![Frontend](https://img.shields.io/badge/frontend-Vue%203-42b883?logo=vue.js&logoColor=white)](frontend/) [![OCR](https://img.shields.io/badge/OCR-Tesseract-blue)](backend/app/document_ai/ocr/) [![License](https://img.shields.io/badge/license-open--source-lightgrey)](#license)

## Vì sao OfficeFlow khác biệt?

| Năng lực | Trạng thái | Giá trị vận hành |
|---|---:|---|
| PDF/Office conversion workflows | ✅ Implemented | Merge, split, compress, rotate, convert và các workflow tài liệu phổ biến. |
| PDF → Excel Document Brain | ✅ Implemented | Native extraction, OCR fallback, semantic entities, evidence, truth model và audit workbook. |
| Deskew và noise resilience | ✅ Implemented | Tự phát hiện góc nghiêng nhỏ trước OCR, ghi lại góc xoay trong diagnostics. |
| Borderless table inference | ✅ Implemented | Density clustering cho alignment thay vì yêu cầu bounding box hoàn hảo. |
| Headerless multi-page continuation | ✅ Implemented | Dùng column-width similarity và data-type matching khi trang sau không lặp header. |
| Financial truth checks | ✅ Implemented | Kiểm tra `Quantity × Unit Price ≈ Line Total` và `Subtotal + Tax ≈ Grand Total`. |
| Enterprise invoice extraction | ✅ Implemented | Gom mô tả nhiều dòng, trích xuất Invoice Number/Date/MST/VAT/Subtotal/Grand Total và xuất workbook theo nghiệp vụ hóa đơn. |
| Vietnamese financial localization | ✅ Implemented | Hiểu `1.000.000 VNĐ`, `1,000,000.00`, `1.234,56 €` và suy luận VAT khi thiếu rate. |
| Human conflict review | ✅ Implemented | Conflict gắn với cell, ưu tiên cao và hiển thị nổi bật trong Confidence Review Panel. |
| Durable queue | ✅ Configurable | Celery + Redis, late acknowledgement, bounded retry và prefetch thấp. |
| Production stack | ✅ Implemented | Docker Compose gồm FastAPI, Vue/Nginx, PostgreSQL, Redis và Celery. |
| Structured observability | ✅ Implemented | JSON logs có job ID, document ID, tool, retry count và exception stack trace. |

## Kiến trúc xử lý

```text
Upload
  → validation + fingerprint
  → page profile + quality signals
  → native text/table extraction
  → OCR fallback theo trang
  → deskew + preprocessing
  → canonical document model
  → layout/table inference
  → semantic entities + provenance
  → truth model
  → arithmetic validation
  → review tasks / ready state
  → Overview + Line Items + Audit workbook
```

`CanonicalDocument` là hợp đồng trung tâm giữa ingestion, OCR, layout, semantics, validation và export. Mỗi object quan trọng có thể truy ngược về page, bbox, table/cell ID, quote, engine và confidence. Pipeline không quảng cáo accuracy tuyệt đối; nó công khai uncertainty để người dùng có thể kiểm tra.

## Tính năng nổi bật

### 1. OCR chịu được tài liệu thực tế

Preprocessing local-first dùng OpenCV, NumPy và Pillow. Deskew chỉ được áp dụng khi tín hiệu hình học đủ mạnh và góc nằm trong phạm vi an toàn; các trường hợp thiếu tín hiệu được ghi warning thay vì xoay bừa. OCR diagnostics lưu `deskew_angle`, `deskew_applied`, raster size, selected pass, confidence và preprocessing profile.

Layout inference hỗ trợ merged-cell span bảo thủ, header hierarchy và clustering một chiều cho các cột borderless có sai lệch nhỏ do scan/OCR. Các bảng nối tiếp được merge khi thỏa đồng thời điều kiện trang liền kề, số cột, similarity của vector độ rộng và tương thích kiểu dữ liệu.

### 2. Financial truth thay vì chỉ type-checking

Validation engine nhận diện các cột phổ biến như `Quantity`, `Unit Price`, `Line Total`, `Subtotal`, `Tax`, `Grand Total` và áp dụng tolerance 1% hoặc ngưỡng tuyệt đối nhỏ. Khi phép tính thất bại, hệ thống:

1. Tạo `ValidationResult` trạng thái `invalid`.
2. Tạo `ReviewTask` trạng thái `arithmetic_conflict` ở cấp cell.
3. Gắn priority `high` và evidence của cell.
4. Đưa conflict vào review panel của frontend.
5. Đánh dấu truth facts là `conflicting` mà không sửa raw source value.

### 3. Enterprise invoice moat

Invoice extraction xử lý mô tả sản phẩm bị wrap thành nhiều visual lines bằng Y-axis clustering và continuation-row inference. Một dòng logic được giữ trong một Excel row, dùng newline trong description và `wrap_text=True` thay vì vertical cell merge gây mất dữ liệu.

Các key-value pairs ngoài bảng được trích xuất bằng regex deterministic kết hợp block-level spatial provenance. Những trường được hỗ trợ gồm `Invoice_Number`, `Date`, `Tax_Code`, `VAT_Rate`, `Subtotal` và `Grand_Total`. Mỗi entity giữ normalized value, confidence và evidence bbox.

Financial parsing hiểu cả convention Việt Nam và quốc tế. Khi invoice có subtotal và grand total nhưng thiếu VAT rate, engine suy luận rate từ `Grand Total / Subtotal - 1` trong khoảng hợp lý, lưu kết quả vào diagnostics và kiểm tra lại quan hệ VAT. Workbook invoice có ba vùng nghiệp vụ chính: `Overview` cho metadata, `Line Items` cho bảng chính và `Audit` cho provenance/conflict.

### 4. Production-ready nhưng vẫn dễ chạy local

Docker Compose cung cấp một stack hoàn chỉnh. Backend và Celery dùng cùng image để tránh lệch dependency; frontend được build multi-stage và phục vụ qua Nginx; Postgres và Redis có volume riêng cùng healthcheck. Worker có retry backoff cho lỗi kết nối tạm thời và JSON logs để điều tra job hỏng ở bất kỳ trang nào.

## Cài đặt local

### Yêu cầu

- Python 3.11+
- Node.js 22+
- Tesseract OCR và language packs cần thiết
- PostgreSQL/Redis chỉ bắt buộc khi bật durable queue hoặc production deployment

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-vie
sudo pip3 install -r backend/requirements.txt
```

### Chạy backend

```bash
PYTHONPATH=backend uvicorn main:app --app-dir backend --reload --port 8000
```

### Chạy frontend

```bash
cd frontend
npm ci
npm run dev
```

API docs có tại `http://localhost:8000/docs`. Liveness là `/health`; readiness là `/health/ready`.

## Chạy production bằng Docker Compose

```bash
cp .env.example .env
# Đặt JWT_SECRET_KEY thành secret ngẫu nhiên tối thiểu 32 bytes.
docker compose up --build -d
docker compose ps
```

Sau khi khởi động:

| Service | URL / vai trò |
|---|---|
| Frontend | `http://localhost/` |
| Backend API | `http://localhost:8000/docs` |
| PostgreSQL | Internal `postgres:5432` |
| Redis | Internal `redis:6379` |
| Celery worker | Durable document processing |

Production nên bật `AUTH_REQUIRED=true`, đặt `JWT_SECRET_KEY` riêng cho từng môi trường và đưa secrets vào secret manager thay vì commit vào repository. `DATABASE_URL` và `REDIS_URL` có thể trỏ đến managed services khi triển khai ngoài Compose.

## Kiểm thử và quality gates

```bash
PYTHONPATH=backend python3 -m compileall -q backend
PYTHONPATH=backend python3 -m pytest -q
cd frontend && npm run build
cd .. && git diff --check
docker compose config
```

Các regression tests hiện bao phủ native PDF, image-only scan, OCR fallback, deskew, density clustering, headerless continuation, typed Excel values, provenance, arithmetic conflict, API validation và workbook audit.

## Data contract và privacy

OfficeFlow lưu raw extraction và evidence để audit. Review task chỉ lưu verified value tách biệt, không ghi đè observation ban đầu. File input tạm nằm trong job directory và được dọn sau xử lý; output thành công vẫn cần policy cleanup/TTL riêng khi deploy lâu dài. Upload mặc định giới hạn 25 MB mỗi file và tối đa 10 file.

OCR và table reconstruction là heuristic. Scan mờ, chữ viết tay, merged cells phức tạp, biểu đồ và layout bất thường có thể cần người kiểm tra. Không nên đưa tài liệu nhạy cảm vào môi trường chưa bật authentication, access control và storage policy phù hợp.

## Cấu trúc repository

```text
backend/
  app/document_ai/       # canonical model, OCR, layout, semantics, truth, validation
  app/processors/        # PDF/Office processors và PDF → Excel exporter
  app/api/                # FastAPI routes và job lifecycle
  app/worker.py           # Celery task với retry/backoff và structured logs
  tests/                  # regression và benchmark fixtures
frontend/
  src/components/review/ # confidence và financial conflict review
  src/views/              # workflow UI
backend/Dockerfile
frontend/Dockerfile
docker-compose.yml
```

## Roadmap

Các hướng mở rộng hợp lý gồm PaddleOCR adapter local, learned table boundary proposal, distributed rate limiting, durable PostgreSQL job store hoàn chỉnh, object storage với TTL và benchmark corpus được gắn nhãn ngoài sample fixture. Những capability chưa triển khai sẽ không được giả lập trong UI.

## License

Dự án được phát triển theo hướng cộng đồng và local/open-source-first. Hãy bổ sung file license chính thức khi chọn điều khoản phân phối cho repository.
