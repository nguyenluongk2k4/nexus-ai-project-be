# Nexus AI - Docker Build Cheatsheet 🚀

Dự án đã được tách nhỏ để anh có thể build/chạy riêng lẻ từng phần mà không gây ảnh hưởng lẫn nhau.

---

## 1. Hệ thống Backend & Database (Core)
Anh chạy các lệnh này đầu tiên vì nó khởi tạo Network và các Database chung.

**Di chuyển vào thư mục:** `cd backend`

### Build & Chạy Backend (FastAPI + Postgres + Redis + Chroma):
```bash
docker compose up -d --build
```

### Chỉ Build lại Backend (Khi sửa code BE):
```bash
docker compose build backend
```

---

## 2. Notification Service (Websocket)
Service này chạy độc lập hoàn toàn khỏi BE chính.

**Di chuyển vào thư mục:** `cd backend`

### Build & Chạy Notification:
```bash
docker compose -f docker-compose.notification.yml up -d --build
```

---

## 3. Frontend Service (React)
Service này chỉ phục vụ file tĩnh, rất nhẹ.

**Di chuyển vào thư mục:** `cd frontend`

### Build & Chạy Frontend:
```bash
docker compose up -d --build
```

---

## 💡 Lưu ý quan trọng:
- **Thứ tự:** Luôn chạy `backend` trước để tạo Network chung (`nexusai-network`).
- ** aaPanel (Host Nginx):** Toàn quyền kiểm soát Proxy. Anh chỉ cần trỏ vào các cổng:
  - Frontend: `3000`
  - Backend: `8000`
  - Notification: `8002`
- **Tối ưu:** Đừng quên em đã cài **Cache Mounts**, các lần build sau sẽ cực nhanh!

---

## 🛠 Lệnh kiểm tra Log:
- BE: `cd backend && docker compose logs -f backend`
- Noti: `cd backend && docker compose -f docker-compose.notification.yml logs -f`
- FE: `cd frontend && docker compose logs -f`

---

## 💡 Lưu ý về Tối ưu Build:
- Em đã cấu hình **BuildKit Cache Mounts** trong `backend/Dockerfile`.
- Khi build lại BE hoặc Notification, Docker sẽ tái sử dụng folder `.cache` bên ngoài image.
- **Tốc độ:** Lần build thứ 2 sẽ nhanh hơn rất nhiều vì không phải tải lại thư viện `pip` và model AI.

---

## 🛠 Lệnh hữu ích khác:
- **Xem log riêng từng cái:**
  - BE: `docker compose logs -f backend`
  - Notification: `docker compose -f backend/docker-compose.notification.yml logs -f`
  - FE: `docker compose logs -f frontend`
- **Dừng tất cả:** `docker compose down` (chỉ dừng các service trong file `docker-compose.yml` chính).
