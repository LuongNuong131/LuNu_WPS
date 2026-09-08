# OfficeFlow

OfficeFlow là dự án cộng đồng miễn phí, local/open-source-first, tập trung vào các workflow xử lý tài liệu chạy thật. Dự án không có pricing, paywall, billing hay tài khoản thương mại. Các file được xử lý theo job; lịch sử gần đây trong giao diện chỉ được lưu cục bộ trên thiết bị và chưa phải bộ nhớ đồng bộ lâu dài.

## Các workflow hiện có

Repository giữ các workflow PDF và Office hiện có: PDF → Excel, Merge PDF, Split PDF, Compress PDF, Rotate PDF, PDF → JPG, Extract pages, Delete pages, PDF → Word, Word → PDF, Excel → PDF, PowerPoint → PDF, Images → PDF và image conversion.

## PDF → Excel quality model

PDF → Excel sử dụng ba mode. **Adaptive** dùng canonical document pipeline, native extraction và OCR fallback theo từng trang. **Tables** ưu tiên các bảng phát hiện được và không thêm sheet text. **Text** giữ toàn bộ text đọc được theo trang/dòng. Khi tài liệu có text native tốt, native layer được ưu tiên; OCR chỉ chạy ở trang trống, image-heavy, sparse hoặc có tín hiệu chất lượng thấp.

Workbook có `Overview`, các sheet bảng, `Document Text` khi được bật và `Audit`. Audit giữ raw text, object ID, page, confidence, engine và evidence JSON. Giá trị số hoặc tiền tệ chỉ được chuyển thành kiểu Excel khi parse đủ rõ ràng; raw text không bị âm thầm ghi đè. Scan mờ, merged cells phức tạp, bảng nghiêng, biểu đồ và layout cực phức tạp có thể cần review thủ công; hệ thống ghi warning thay vì cam kết khôi phục hoàn hảo.

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

## Kiểm thử

Regression tests tạo fixture PDF native, bảng có đường kẻ, scan image-only và kiểm tra workbook mở được bằng `openpyxl`, sheet structure, typed money, provenance, OCR pass metadata, API options validation, result metadata và download.

```bash
PYTHONPATH=backend python3 -m compileall -q backend
PYTHONPATH=backend pytest -q
cd frontend && npm run build
cd .. && git diff --check
```

## Giới hạn và privacy

Giới hạn upload hiện tại là 25 MB mỗi file và tối đa 10 file theo tool. Input tạm được lưu trong job directory và dọn sau khi xử lý; output không bị xóa trước download. Chưa có persistence database hay cleanup TTL tự động cho output production. SHA-256 chỉ là fingerprint nội bộ, không phải cam kết bảo mật hoặc deduplication persistence. Không nên gửi tài liệu nhạy cảm vào môi trường chưa được harden theo chính sách triển khai của bạn.

OCR và table reconstruction là các quá trình xác suất/heuristic. OfficeFlow công khai confidence, warning và evidence để người dùng kiểm tra; không tuyên bố tái tạo 100% mọi PDF scan hoặc layout bất thường.

## Document Brain 4.0 contracts

Canonical documents expose a versioned `DocumentState` lifecycle: `uploaded`, `identified`, `profiled`, `understanding`, `extracted`, `validated`, `review_required`, `ready` và `failed`. Mỗi kết quả cũng lưu `PipelineVersion` để biết phiên bản pipeline, OCR, layout, table, semantic và export đã tạo ra artifact.

Quality không được suy đoán thành một con số duy nhất. `quality_dimensions` giữ các thành phần source confidence, OCR confidence, layout confidence, semantic confidence, consistency confidence, evidence coverage và overall score. Mỗi thành phần được tính từ metrics có trong canonical result và có thể kiểm tra trong diagnostics.

Validation deterministic kiểm tra evidence coverage, độ nhất quán số cột của table và tính hợp lý sơ bộ của các giá trị tiền tệ. Khi entity quan trọng có confidence thấp hoặc thiếu evidence, hệ thống tạo `ReviewTask` với field, raw value, priority, reason, confidence và evidence. Review task không sửa raw source value; nó chỉ đánh dấu phần cần người dùng kiểm tra.

Các layer như knowledge graph, multi-document aggregation, document comparison, RAG và workflow automation vẫn là extension points tương lai. Chúng không được giả lập trong giao diện khi backend chưa thực sự cung cấp capability tương ứng.
