# Seed Forum Data to COPY Tables
# Populate forum_categories_copy, forum_posts_copy, forum_comments_copy, post_likes_copy
# with sample data matching frontend mock

import asyncio
import sys
from datetime import datetime, timedelta
from uuid import uuid4, UUID
import random

sys.path.insert(0, '.')

from sqlalchemy import select, text
from shared.database.connection import async_session_maker
from modules.auth.infrastructure.models import UserModel


# =====================================================
# User ID Mapping (from provided user data)
# =====================================================

# Map author names to user IDs (from the users table)
USER_NAME_TO_ID = {
    "Nguyễn Văn A": "34a49f8d",  # Will be matched by prefix
    "Trần Thị B": "13e9a5cf",
    "Lê Văn C": "41fa46a0",
    "Phạm Thị D": "d5527ff4",
    "Hoàng Văn E": "44625e1c",
    "Vũ Thị F": "6158749d",
    "Đặng Văn G": "0859cc4d",
}

# Category data matching frontend mock
CATEGORIES = [
    {
        "name": "Trí tuệ Nhân tạo (AI)",
        "slug": "ai",
        "description": "Machine Learning, Deep Learning, NLP",
        "icon": "Bot",
        "sort_order": 1
    },
    {
        "name": "Phát triển Phần mềm",
        "slug": "software",
        "description": "Web, Mobile, Desktop Development",
        "icon": "Code",
        "sort_order": 2
    },
    {
        "name": "Phân tích Dữ liệu",
        "slug": "data",
        "description": "Data Science, Analytics, Visualization",
        "icon": "Database",
        "sort_order": 3
    }
]

# Post data matching frontend mock
POSTS = [
    {
        "title": "Thảo luận về mô hình GPT-4 và ứng dụng trong thực tế",
        "content": """GPT-4 đã mang lại nhiều cải tiến đáng kể so với các phiên bản trước. Chúng ta hãy cùng thảo luận về các ứng dụng thực tế của mô hình này.

Một số điểm nổi bật của GPT-4:
- Khả năng xử lý đa phương thức (text + image)
- Cải thiện đáng kể về reasoning
- Context window lớn hơn nhiều (128k tokens)

Các bạn đã ứng dụng GPT-4 vào dự án nào chưa? Hãy chia sẻ kinh nghiệm nhé!""",
        "author_name": "Nguyễn Văn A",
        "category_slug": "ai",
        "view_count": 2500,
        "is_pinned": True,
        "hours_ago": 2
    },
    {
        "title": "Hướng dẫn tối ưu React Performance với useMemo và useCallback",
        "content": """Trong bài viết này, tôi sẽ chia sẻ các kỹ thuật tối ưu performance cho React application bằng cách sử dụng hooks useMemo và useCallback.

## Khi nào dùng useMemo?
useMemo được dùng để cache kết quả của một computation tốn kém. Chỉ nên dùng khi:
- Computation thực sự tốn thời gian
- Dependencies không thay đổi thường xuyên

## Khi nào dùng useCallback?
useCallback được dùng để cache function reference. Hữu ích khi:
- Truyền callback xuống child component được wrap với React.memo
- Function được dùng trong dependency array của useEffect

Các bạn có tips nào khác không?""",
        "author_name": "Trần Thị B",
        "category_slug": "software",
        "view_count": 3200,
        "is_pinned": False,
        "hours_ago": 4
    },
    {
        "title": "Phân tích dữ liệu lớn với Apache Spark và Python",
        "content": """Apache Spark là framework mạnh mẽ cho xử lý dữ liệu lớn. Hãy cùng tìm hiểu cách tích hợp với Python thông qua PySpark.

## Setup PySpark
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("MyApp").getOrCreate()
df = spark.read.csv("data.csv", header=True, inferSchema=True)
```

## Ưu điểm của Spark
- Xử lý song song trên cluster
- Lazy evaluation giúp tối ưu query plan
- Tích hợp tốt với ecosystem (Hadoop, Hive, etc.)

Ai đang dùng Spark trong production? Chia sẻ kinh nghiệm nhé!""",
        "author_name": "Lê Văn C",
        "category_slug": "data",
        "view_count": 1800,
        "is_pinned": False,
        "hours_ago": 5
    },
    {
        "title": "Machine Learning Deployment Best Practices 2024",
        "content": """Triển khai ML models vào production đòi hỏi nhiều kỹ thuật và best practices. Tôi muốn chia sẻ kinh nghiệm sau nhiều dự án thực tế.

## 1. Model Versioning
Dùng MLflow hoặc DVC để track experiments và versions.

## 2. Containerization
Docker + Kubernetes là combo phổ biến nhất. FastAPI làm serving layer rất hiệu quả.

## 3. Monitoring
- Track model drift
- Monitor latency và throughput
- Set up alerts cho anomalies

## 4. A/B Testing
Rollout từ từ với canary deployment. So sánh metrics giữa old và new model.

Các bạn còn practices nào khác không?""",
        "author_name": "Phạm Thị D",
        "category_slug": "ai",
        "view_count": 4100,
        "is_pinned": False,
        "hours_ago": 6
    },
    {
        "title": "TypeScript 5.0 - Những tính năng mới đáng chú ý",
        "content": """TypeScript 5.0 đã được release với nhiều cải tiến về performance và developer experience. Đây là những điểm nổi bật:

## 1. Decorators (ECMAScript Standard)
Cuối cùng decorators cũng được chuẩn hóa! Syntax tương tự nhưng behavior khác với legacy decorators.

## 2. const Type Parameters
```typescript
function foo<const T>(x: T) { return x; }
const a = foo([1, 2, 3]); // readonly [1, 2, 3]
```

## 3. Multiple Config Extends
```json
{
  "extends": ["./tsconfig.base.json", "./tsconfig.strict.json"]
}
```

## 4. Better Performance
Build time giảm 10-25% so với 4.9!

Các bạn đã upgrade lên TS 5.0 chưa?""",
        "author_name": "Hoàng Văn E",
        "category_slug": "software",
        "view_count": 2900,
        "is_pinned": False,
        "hours_ago": 8
    },
    {
        "title": "Data Visualization với D3.js và React",
        "content": """Tạo các biểu đồ tương tác đẹp mắt bằng D3.js trong React application của bạn.

## Tích hợp D3 với React
Có 2 approaches chính:
1. **D3 quản lý DOM**: Dùng useRef và để D3 render
2. **React quản lý DOM**: Dùng D3 cho calculations, React cho rendering

## Ví dụ với React quản lý DOM
```jsx
const data = [10, 20, 30, 40, 50];
const scale = d3.scaleLinear()
  .domain([0, d3.max(data)])
  .range([0, 300]);

return (
  <svg>
    {data.map((d, i) => (
      <rect key={i} x={i * 40} y={300 - scale(d)} 
            width={30} height={scale(d)} fill="steelblue" />
    ))}
  </svg>
);
```

Các bạn thích approach nào hơn?""",
        "author_name": "Vũ Thị F",
        "category_slug": "data",
        "view_count": 1500,
        "is_pinned": False,
        "hours_ago": 24
    },
    {
        "title": "Neural Networks từ cơ bản đến nâng cao",
        "content": """Cùng tìm hiểu chi tiết về cách neural networks hoạt động, từ perceptron đơn giản đến deep learning.

## 1. Perceptron - Đơn vị cơ bản
Perceptron là một neuron đơn lẻ:
- Input: x1, x2, ..., xn
- Weights: w1, w2, ..., wn
- Output: f(Σ wi*xi + bias)

## 2. Activation Functions
- ReLU: max(0, x) - Phổ biến nhất hiện nay
- Sigmoid: 1/(1+e^-x) - Dùng cho binary classification
- Tanh: (e^x - e^-x)/(e^x + e^-x) - Output range [-1, 1]

## 3. Backpropagation
Thuật toán để tính gradient và update weights. Chain rule là core concept.

## 4. Deep Learning
Khi stack nhiều layers → Deep Neural Network. Các variants:
- CNN cho images
- RNN/LSTM cho sequences
- Transformer cho NLP

Các bạn muốn tìm hiểu sâu về topic nào?""",
        "author_name": "Đặng Văn G",
        "category_slug": "ai",
        "view_count": 5300,
        "is_pinned": False,
        "hours_ago": 24
    }
]

# Sample comments
SAMPLE_COMMENTS = [
    "Bài viết rất hay và chi tiết! Cảm ơn tác giả đã chia sẻ.",
    "Mình đã áp dụng và thấy hiệu quả rõ rệt. Thanks!",
    "Có thể giải thích thêm phần này được không ạ?",
    "Đây chính xác là những gì mình đang tìm kiếm.",
    "Rất hữu ích cho dự án hiện tại của mình.",
    "Concept hay quá, mình sẽ thử implement xem sao.",
    "Bổ sung thêm: có thể dùng thêm kỹ thuật X để optimize hơn nữa.",
    "Mình gặp issue khi implement, có ai giúp được không?",
]


async def get_user_id_by_prefix(session, prefix: str) -> UUID:
    """Find user ID that starts with the given prefix"""
    stmt = text(f"SELECT id FROM users WHERE id::text LIKE '{prefix}%' LIMIT 1")
    result = await session.execute(stmt)
    row = result.fetchone()
    if row:
        return row[0]
    return None


async def get_all_user_ids(session) -> list:
    """Get all active user IDs"""
    stmt = select(UserModel.id).where(UserModel.is_active == True)
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def seed_data():
    """Main seeding function"""
    print("🌱 Seeding Forum Data to COPY Tables...")
    print("=" * 50)
    
    async with async_session_maker() as session:
        # Check if COPY tables exist
        try:
            await session.execute(text("SELECT 1 FROM forum_categories_copy LIMIT 1"))
        except Exception as e:
            print("❌ COPY tables don't exist! Run create_forum_copy_tables.sql first.")
            print(f"   Error: {e}")
            return
        
        # Check if already seeded
        count_result = await session.execute(text("SELECT COUNT(*) FROM forum_categories_copy"))
        existing_count = count_result.scalar()
        if existing_count > 0:
            print(f"⚠️ COPY tables already have data ({existing_count} categories).")
            if len(sys.argv) <= 1 or sys.argv[1] != "--force":
                print("   Use --force to re-seed (will delete existing data).")
                return
            else:
                print("   --force detected, deleting existing data...")
                await session.execute(text("DELETE FROM post_likes_copy"))
                await session.execute(text("DELETE FROM forum_comments_copy"))
                await session.execute(text("DELETE FROM forum_posts_copy"))
                await session.execute(text("DELETE FROM forum_categories_copy"))
                await session.commit()
                print("   ✅ Deleted existing data")
        
        # Get all user IDs for mapping
        all_user_ids = await get_all_user_ids(session)
        if not all_user_ids:
            print("❌ No users found in database! Seed users first.")
            return
        print(f"📝 Found {len(all_user_ids)} users in database")
        
        # Map author names to user IDs
        author_to_user_id = {}
        for name, prefix in USER_NAME_TO_ID.items():
            user_id = await get_user_id_by_prefix(session, prefix)
            if user_id:
                author_to_user_id[name] = user_id
                print(f"   {name} -> {user_id}")
            else:
                print(f"   ⚠️ User not found for {name} (prefix: {prefix})")
        
        # 1. Seed Categories
        print("\n📁 Seeding categories...")
        category_id_map = {}  # slug -> UUID
        for cat in CATEGORIES:
            cat_id = uuid4()
            category_id_map[cat["slug"]] = cat_id
            
            await session.execute(text("""
                INSERT INTO forum_categories_copy (id, name, slug, description, icon, sort_order)
                VALUES (:id, :name, :slug, :description, :icon, :sort_order)
            """), {
                "id": cat_id,
                "name": cat["name"],
                "slug": cat["slug"],
                "description": cat["description"],
                "icon": cat["icon"],
                "sort_order": cat["sort_order"]
            })
        print(f"   ✅ Created {len(CATEGORIES)} categories")
        
        # 2. Seed Posts
        print("\n📝 Seeding posts...")
        post_ids = []  # Store for comments and likes
        for post in POSTS:
            post_id = uuid4()
            post_ids.append(post_id)
            
            # Get user ID for author
            user_id = author_to_user_id.get(post["author_name"])
            if not user_id:
                # Use random user if author not found
                user_id = random.choice(all_user_ids)
            
            # Calculate timestamps
            created_at = datetime.now() - timedelta(hours=post["hours_ago"])
            
            await session.execute(text("""
                INSERT INTO forum_posts_copy 
                (id, category_id, user_id, title, content, view_count, is_pinned, is_locked, created_at, updated_at)
                VALUES (:id, :category_id, :user_id, :title, :content, :view_count, :is_pinned, :is_locked, :created_at, :updated_at)
            """), {
                "id": post_id,
                "category_id": category_id_map[post["category_slug"]],
                "user_id": user_id,
                "title": post["title"],
                "content": post["content"],
                "view_count": post["view_count"],
                "is_pinned": post["is_pinned"],
                "is_locked": False,
                "created_at": created_at,
                "updated_at": created_at
            })
        print(f"   ✅ Created {len(POSTS)} posts")
        
        # 3. Seed Comments
        print("\n💬 Seeding comments...")
        comment_count = 0
        for post_id in post_ids:
            # Add 2-5 random comments per post
            num_comments = random.randint(2, 5)
            for i in range(num_comments):
                comment_id = uuid4()
                user_id = random.choice(all_user_ids)
                content = random.choice(SAMPLE_COMMENTS)
                created_at = datetime.now() - timedelta(hours=random.randint(1, 20))
                
                await session.execute(text("""
                    INSERT INTO forum_comments_copy 
                    (id, post_id, user_id, parent_id, content, created_at, updated_at)
                    VALUES (:id, :post_id, :user_id, NULL, :content, :created_at, :updated_at)
                """), {
                    "id": comment_id,
                    "post_id": post_id,
                    "user_id": user_id,
                    "content": content,
                    "created_at": created_at,
                    "updated_at": created_at
                })
                comment_count += 1
        print(f"   ✅ Created {comment_count} comments")
        
        # 4. Seed Likes
        print("\n❤️ Seeding likes...")
        like_count = 0
        for post_id in post_ids:
            # Add 5-15 random likes per post (unique users)
            num_likes = random.randint(5, min(15, len(all_user_ids)))
            likers = random.sample(all_user_ids, num_likes)
            
            for user_id in likers:
                try:
                    await session.execute(text("""
                        INSERT INTO post_likes_copy (user_id, post_id, created_at)
                        VALUES (:user_id, :post_id, :created_at)
                    """), {
                        "user_id": user_id,
                        "post_id": post_id,
                        "created_at": datetime.now() - timedelta(hours=random.randint(1, 48))
                    })
                    like_count += 1
                except Exception:
                    pass  # Skip duplicate likes
        print(f"   ✅ Created {like_count} likes")
        
        # Commit all changes
        await session.commit()
        
        print("\n" + "=" * 50)
        print("🎉 Seeding complete!")
        print("\nVerify with:")
        print("  SELECT COUNT(*) FROM forum_categories_copy;")
        print("  SELECT COUNT(*) FROM forum_posts_copy;")
        print("  SELECT COUNT(*) FROM forum_comments_copy;")
        print("  SELECT COUNT(*) FROM post_likes_copy;")


if __name__ == "__main__":
    asyncio.run(seed_data())
