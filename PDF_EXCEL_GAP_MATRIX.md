# PDF → Excel Gap Matrix

## Phạm vi

Ma trận này phản ánh implementation thực tế trong repository sau milestone M03-A. Điểm số dùng thang 0–10: **0–3 thiếu**, **4–5 yếu**, **6–7 dùng được**, **8 mạnh**, **9 production-grade**, **10 exceptional**. Điểm không phải benchmark độ chính xác trên corpus bên ngoài.

| Subsystem | Current implementation | Score | Current problems | Root cause | Impact | Target | Priority |
|---|---|---:|---|---|---|---|---:|
| PDF → Excel | Canonical pipeline, tables, text sheet, audit sheet, typed values | 7 | Chưa có corpus benchmark thực tế và chưa xuất cell geometry đầy đủ | Chưa có benchmark harness và schema layout ổn định cho export | Khó đo regression chất lượng | 8 | P0 |
| OCR | Tesseract adapter, page routing, preprocessing, two-pass selection | 7 | Chất lượng phụ thuộc language packs và scan quality | Chưa có benchmark theo ngôn ngữ/quality bucket | 8 | P0 |
| Table detection | Native pdfplumber line/text strategies | 6 | Layout không kẻ dòng, merged header và bảng nghiêng còn heuristic | Detection strategy chưa dùng geometry hợp nhất | 8 | P0 |
| Table reconstruction | Normalize rows, repeated-header filtering, conservative adjacent-page merge | 6 | Chưa xử lý merged cells/hierarchical headers | Canonical table model chưa lưu span/header hierarchy | 8 | P0 |
| Multi-page tables | Merge khi trang kế tiếp có header tương đương | 6 | Không merge qua trang thiếu header hoặc header biến thể có kiểm chứng | Chưa có header similarity/provenance model | 8 | P0 |
| Merged cells | Giữ text trong cell nhưng chưa khôi phục span | 4 | Có thể làm phẳng cấu trúc header | Chưa có cell span inference | 7 | P1 |
| Cell typing | Conservative number, currency, date/text handling | 7 | Một số locale ambiguity cần review | Parser chưa có currency/locale contract đầy đủ | 8 | P1 |
| Validation | Evidence coverage, table width, financial consistency, review tasks | 6 | Chưa kiểm tra tổng theo từng table/export cell | Validation rules còn ở document level | 8 | P1 |
| Evidence | Page/block/table/cell evidence và Audit sheet | 7 | Exported merged rows chưa có provenance row-level riêng | Merge metadata hiện ở table diagnostics/source pages | 8 | P1 |
| Quality | Multi-dimensional quality dimensions và table quality metrics | 6 | Chưa calibrated trên labeled corpus | Chưa có benchmark data | 8 | P1 |
| Review | ReviewTask backend và warning metadata | 5 | Chưa có review workspace/UI chỉnh sửa có traceability | Frontend chưa expose review contract | 8 | P1 |
| Storage | Local artifact boundary, SQLite job metadata | 6 | Chưa có retention TTL production/object storage | Chưa có artifact repository và cleanup scheduler | 8 | P1 |
| Jobs | SQLite metadata, state recovery on restart, health/readiness | 6 | Chưa có durable queue/worker retry | FastAPI BackgroundTasks | 8 | P1 |
| Security | Upload/path hardening and no paid AI dependency | 4 | Chưa có auth, ownership, authorization | Identity layer chưa triển khai | 8 | P0 |
| Testing | 12 regression tests including OCR, API, persistence and table merge | 6 | Chưa có corpus-based benchmark/performance suite | Chưa có labeled fixtures | 8 | P0 |
| Performance | Early native extraction and page-aware routing | 5 | Chưa có latency/memory baseline | Chưa có benchmark harness | 7 | P1 |

## Milestone M03-A

Milestone này nâng **Multi-page tables** từ mức chỉ tách bảng theo từng trang lên mức **merge bảo thủ theo trang liền kề và repeated header tương đương**. Hệ thống giữ source pages, số lượt merge và số multi-page tables trong diagnostics. Bảng khác header hoặc không liền trang không được merge.

## Giới hạn được công khai

Đây là heuristic deterministic, không phải cam kết khôi phục mọi bảng nhiều trang. Các trường hợp header biến thể, merged cells, hierarchical headers, bảng thiếu header ở trang tiếp theo và bảng bị cắt bởi layout phức tạp vẫn cần benchmark và review.

## References

[1]: README.md "LuNu WPS implementation notes and limitations"
[2]: backend/app/processors/pdf_to_excel.py "PDF to Excel extraction and table merge implementation"
[3]: backend/tests/test_pdf_to_excel.py "PDF to Excel regression and table merge tests"

*Author: Manus AI*
