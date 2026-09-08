# Technical Debt Register

| Problem | Impact | Priority | Recommendation | Status |
|---|---|---:|---|---|
| Job metadata chỉ nằm trong `jobs_db` của process | Restart backend làm mất trạng thái và lịch sử job | P0 | Thêm persistence có migration và contract versioning | Open |
| Artifact lưu local, chưa có TTL hoặc lifecycle policy | Có thể tích tụ dữ liệu và khó vận hành production | P0 | Tạo artifact service, retention policy, cleanup job và audit log | Open |
| Chưa có authentication/authorization/ownership | Không thể chứng minh người tải artifact là chủ tài nguyên | P0 | Chọn identity model, gắn owner vào document/job/artifact, test isolation | Open |
| BackgroundTasks không phải durable queue | Crash giữa chừng không có recovery hoặc retry có kiểm soát | P0 | Queue + worker có lease, idempotency key và retry policy | Open |
| Table reconstruction và OCR vẫn heuristic | Scan khó, merged cells và layout bất thường có thể cần review | P1 | Xây benchmark corpus, đo precision/recall và tăng review UI | Partial |
| Frontend history chỉ lưu localStorage | Lịch sử không đồng bộ và link có thể hết hạn | P1 | Hiển thị persisted document library sau khi có identity/persistence | Open |
| Chưa có metrics/tracing production | Khó theo dõi latency, lỗi và chất lượng pipeline | P1 | Thêm structured logs, metrics và correlation ID | Open |
| Chưa có E2E security/deployment test | Rủi ro hồi quy ở boundary và cấu hình triển khai | P1 | Thêm test matrix cho auth, ownership, restart và artifact expiry | Open |

## Nguyên tắc xử lý

Không giải quyết technical debt bằng cách giả lập database, queue, authentication hoặc confidence. Mỗi mục chỉ được chuyển sang **Implemented** khi có code tích hợp, regression tests và tài liệu vận hành tương ứng.

## References

[1]: ARCHITECTURE_AUDIT.md "LuNu WPS architecture audit"
[2]: README.md "LuNu WPS implementation notes and limitations"

*Author: Manus AI*
