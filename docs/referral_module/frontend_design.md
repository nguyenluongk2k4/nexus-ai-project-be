# Frontend Architecture Design: Referral Module (DDD-lite)

Module Referral trên Frontend (React + Vite) sẽ được xây dựng thành các thành phần độc lập (DDD-lite), đảm bảo UI "Dumb" (chỉ lo render) và Use Cases lo điều phối logic.

## 1. Cấu trúc thư mục (`frontend/src/modules/referral/`)

```text
src/modules/referral/
├── domain/
│   ├── entities/
│   │   ├── Referral.ts        # Interface mô tả Referral data
│   │   └── ReferralStats.ts
│   ├── ports/
│   │   └── ReferralGateway.ts # Interface call API
│   └── services/
│       └── ReferralService.ts # Chứa business rules ở FE (Validate độ dài mã, regex...)
├── infrastructure/
│   └── ReferralHttpGateway.ts # Implement gọi Axios tới backend
├── usecases/
│   ├── ApplyReferralUseCase.ts
│   └── GetReferralStatsUseCase.ts
└── ui/
    ├── components/
    │   ├── ReferralInput.tsx  # Ô nhập mã code
    │   ├── ReferralStatsBox.tsx # Xem thống kê
    │   └── ReferralList.tsx   # Danh sách bạn đã mời
    ├── pages/
    │   └── ReferralPage.tsx   # Trang tổng
    └── hooks/
        └── useReferral.ts     # Hook cầu nối giữa UI và UseCases
```

## 2. Chi tiết các Layer

### 2.1. Domain Layer (`domain/`)
- **Gateway (Port):**
```typescript
export interface ReferralGateway {
  applyCode(code: string): Promise<{ success: boolean; message: string; coinsAwarded?: number }>;
  getStats(): Promise<ReferralStats>;
}
```
- **Service:** Xác thực mã ở client-side (VD: Mã không được để trống, mã phải từ 6 ký tự trở lên, format chữ hoa số).

### 2.2. Application Layer (`usecases/`)
- **`ApplyReferralUseCase.ts`:**
  - Inject `ReferralService` và `ReferralGateway`.
  - Validate mã qua Service.
  - Xử lý loading state, try-catch lỗi, map các Error Code (nhập mã của chính mình, nhập mã sai, đã nhập rồi) ra string thân thiện với người dùng (Tiếng Việt).

### 2.3. Infrastructure Layer (`infrastructure/`)
- **`ReferralHttpGateway.ts`:** 
  - Gọi Rest API (từ `apiConfig`).
  - POST `/api/referral/apply`. Hứng response chuẩn hoá trả về cho UseCase.

### 2.4. Presentation Layer (`ui/`)
- **`useReferral.ts` Custom Hook:**
  - Quản lý State React (`isLoading`, `error`, `successMsg`, trạng thái form).
  - Cung cấp hàm `handleApplyCode(code)` cho UI.
- **UI Components:**
  - `ReferralInput`: Giao diện bắt mắt (Shiny badge như yêu cầu tổng thể) để người dùng kích thích nhập mã.
  - Nếu áp dụng mã thành công: Bắn Lottie animation Tung Hoa (Confetti) hoặc chớp nháy số Coin để tăng trải nghiệm WOW.

## 3. Workflow nhập mã code
1. User gõ `NEXUS2026` vào `ReferralInput.tsx` và bấm "Xác nhận".
2. Khởi động hàm từ `useReferral` -> gọi `ApplyReferralUseCase`.
3. UseCase validate (Ok) -> gọi qua `ReferralHttpGateway`.
4. Gateway bắn HTTP POST xuống Backend.
5. Backend phản hồi `{"success": true, "coins": 50}`.
6. Alert Component (Toaster) hiện ra: "Áp dụng thành công! Cả hai được tặng 50 Xu 🎉".
7. Giao diện (Header Navbar) tự động update số Balance (nếu có sử dụng Zustand store / Context chung).
