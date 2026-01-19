import chromadb
from collections import Counter

# Kết nối
client = chromadb.HttpClient(host="localhost", port=8001)
collection = client.get_collection(name="ksa_project")

total_docs = collection.count()
print(f"🔍 Đang kiểm tra toàn bộ {total_docs} documents...\n")

# Lấy TOÀN BỘ dữ liệu
results = collection.get(limit=total_docs, include=["metadatas", "documents"])

# Cấu hình các trường bắt buộc phải có
REQUIRED_FIELDS = ['ability', 'name', 'node_type', 'skill', 'source_id', 'specialization']
errors = []
stats = {"node_types": Counter(), "specializations": Counter()}

for i in range(total_docs):
    metadata = results['metadatas'][i]
    doc_id = results['ids'][i]
    
    # 1. Kiểm tra thiếu trường (Missing fields)
    missing = [field for field in REQUIRED_FIELDS if field not in metadata]
    if missing:
        errors.append(f"❌ ID {doc_id}: Thiếu trường {missing}")
    
    # 2. Kiểm tra giá trị rỗng/N/A (Empty values)
    if metadata:
        for key, value in metadata.items():
            if value is None or str(value).strip() == "":
                errors.append(f"⚠️ ID {doc_id}: Trường '{key}' bị để trống")
        
        # Thống kê để tìm lỗi gõ sai (Typo)
        stats["node_types"][metadata.get('node_type')] += 1
        stats["specializations"][metadata.get('specialization')] += 1

# --- XUẤT BÁO CÁO ---
print("=" * 70)
print("📊 BÁO CÁO KIỂM TRA DỮ LIỆU")
print("=" * 70)

if not errors:
    print("✅ Tuyệt vời! Không phát hiện lỗi cấu trúc hoặc thiếu dữ liệu.")
else:
    print(f"❗ Tìm thấy {len(errors)} vấn đề cần lưu ý:")
    for err in errors[:10]: # Chỉ hiện 10 lỗi đầu tiên nếu quá nhiều
        print(err)
    if len(errors) > 10:
        print(f"... và {len(errors) - 10} lỗi khác.")

print("\n" + "-" * 30)
print("📂 THỐNG KÊ PHÂN LOẠI (Kiểm tra xem có bị gõ sai tên không):")
print(f"Loại Node: {dict(stats['node_types'])}")
print(f"Chuyên ngành: {dict(stats['specializations'])}")
print("=" * 70)