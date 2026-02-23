# Backend Architecture Design: Referral Module (DDD-lite)

Module Referral (Giới thiệu người dùng mới) sẽ được xây dựng tuân thủ kiến trúc DDD-lite hiện tại của dự án (FastAPI + SQLAlchemy).

## 1. Mục tiêu (Goals)
- Cho phép người dùng sinh mã giới thiệu (Referral Code) của riêng họ.
- Cho phép người dùng mới nhập mã giới thiệu của người khác.
- Ghi nhận lịch sử giới thiệu vào bảng `referrals`.
- Tích hợp với `CoinsService` để cộng xu thưởng cho cả 2 bên (Người giới thiệu và Người nhập mã) khi thao tác thành công.

## 2. Cấu trúc thư mục (`backend/modules/referral/`)

```text
modules/referral/
├── __init__.py
├── api/
│   ├── dependencies.py
│   ├── routes.py          # HTTP Endpoints
│   └── schemas.py         # Pydantic models (Request/Response)
├── domain/
│   ├── entities.py        # Entity `Referral`
│   ├── ports.py           # `ReferralRepositoryPort`
│   └── services/
│       └── referral_service.py # Core Business Logic
├── infrastructure/
│   ├── models.py          # SQLAlchemy `ReferralModel`
│   └── repository.py      # Implement của `ReferralRepositoryPort`
└── usecases/
    ├── apply_referral_usecase.py
    └── get_referral_stats_usecase.py
```

## 3. Chi tiết các Layer

### 3.1. Domain Layer (`domain/`)
**Entities (`entities.py`):**
- `Referral`: Data class đại diện cho 1 bản ghi referral (chứa id, referrer_id, referee_id, referral_code, status, coins_awarded, created_at, completed_at).

**Ports (`ports.py`):**
- `ReferralRepositoryPort`:
  - `save(referral: Referral) -> Referral`
  - `get_by_referee_id(user_id: UUID) -> Optional[Referral]`
  - `get_referrals_by_referrer(user_id: UUID) -> list[Referral]`

**Domain Service (`services/referral_service.py`):**
- Đảm nhiệm logic nghiệp vụ (ví dụ: Kiểm tra một user có thể nhập mã không? Mã giới thiệu này của ai? Trạng thái mã hợp lệ không?).
- Giao tiếp với `CoinsService` (để cộng xu) thông qua Dependency Injection.

### 3.2. Infrastructure Layer (`infrastructure/`)
**Models (`models.py`):**
- Ánh xạ bảng `referrals` từ CSDL PostgreSQL (phù hợp với Supabase) sang SQLAlchemy ORM.

**Repository (`repository.py`):**
- `SQLAlchemyReferralRepository` implement các hàm của DB: insert, select bằng `AsyncSession`.

### 3.3. Application Layer (`usecases/`)
- `ApplyReferralUseCase`: Nhận request từ API (user A nhập mã của user B). Gọi `ReferralService` kiểm tra nghiệp vụ hợp lệ. Gọi `CoinsRepository` để cộng tiền, và `ReferralRepository` để lưu vào DB (kèm Transaction an toàn).
- `GetReferralStatsUseCase`: Lấy danh sách bạn bè đã mời và tổng số tiền kiếm được.

### 3.4. Framework Layer (`api/`)
- `POST /api/referral/apply`: API để client gọi khi bấm nút "Áp dụng mã".
- `GET /api/referral/stats`: (Tuỳ chọn) Lấy thống kê referral.
## 4. Quy tắc Sinh Mã Giới thiệu (Referral Code Generation)
Để đảm bảo mã **Độc nhất (Unique)** và **Ngắn gọn dễ nhớ**, ta áp dụng các quy tắc sau:
1. **Bảng `users`**: Đã được bổ sung thêm cột `referral_code VARCHAR UNIQUE`. Việc kiểm tra Unique được giao phó toàn bộ cho Database để tránh Race Condition (Nhiều người cày lúc cùng tạo 1 mã).
2. **Quy tắc sinh mã**: 
   - Dùng chuỗi ngẫu nhiên dài **6-8 ký tự** (bao gồm Chữ hoa và Số) để dễ nhìn, dễ đọc. Ví dụ: `NEX8VXQK` hoặc `A1B2C3D4`.
3. **Quy trình sinh lười (Lazy Generation)**:
   - Khi frontend gọi API `/api/referral/my-code`:
     - Nếu user đã có mã trong cột `referral_code` -> Trả về luôn.
     - Nếu chưa có -> Backend sẽ dùng vòng lặp `while` sinh ra 1 chuỗi ngẫu nhiên 8 ký tự.
     - Chèn vào DB. Nếu chèn bị lỗi `UNIQUE Violation` (cực hiếm vì $36^8$ là rất lớn số), backend tự động bắt lỗi và thử sinh lại mã khác (Retry).

## 5. Tương tác với Domain khác
Module này sẽ chọc chéo qua:
- **Modules Auth (`users`):** Cập nhật mã referral_code, phân tích user giới thiệu.
- **Modules Coins (`coins`):** Cộng tiền thưởng (Thường là 500 Coin cho cả người mời và người được mời) sau khi nhập hiệu lực thành công.
