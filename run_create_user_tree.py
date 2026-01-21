"""
Tạo User Skill Tree đơn giản với 4 nodes mẫu
- 1 Ability node
- 1 Skill node  
- 2 Knowledge nodes
"""

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv
from datetime import date, timedelta
import uuid

load_dotenv()
import os
DATABASE_URL = os.getenv("DATABASE_URL")


async def create_simple_tree():
    print("🚀 Creating Simple User Skill Tree...")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        user_id = "39327209-e605-4af6-98b1-4cc6d70f2a8e"
        print(f"📌 User: {user_id}")
        
        # 1. Xóa tree cũ của user này (nếu có)
        print("🗑️  Deleting old tree if exists...")
        await conn.execute(
            text("DELETE FROM user_skill_trees WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        
        # 2. Tạo User Skill Tree mới
        tree_id = str(uuid.uuid4())
        print(f"📦 Creating new tree: {tree_id}")
        await conn.execute(
            text("""
                INSERT INTO user_skill_trees (id, user_id, name, description)
                VALUES (:id, :user_id, 'Python Developer', 'Cây kỹ năng mẫu để test Timeline')
            """),
            {"id": tree_id, "user_id": user_id}
        )
        
        # 3. Tạo 4 User Skill Nodes
        nodes = [
            {
                "id": str(uuid.uuid4()),
                "name": "Backend Development",
                "description": "Xây dựng backend hoàn chỉnh",
                "icon": "Server",
                "color": "#8B5CF6",
                "type": "ability",
                "status": "in_progress",
                "progress": 40,
                "x": 0, "y": 0
            },
            {
                "id": str(uuid.uuid4()),
                "name": "REST API Design",
                "description": "Thiết kế và xây dựng REST API",
                "icon": "Zap",
                "color": "#10B981",
                "type": "skill",
                "status": "in_progress",
                "progress": 60,
                "x": 1, "y": 0
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Python Basics",
                "description": "Nắm vững cú pháp Python cơ bản",
                "icon": "Code",
                "color": "#F59E0B",
                "type": "knowledge",
                "status": "completed",
                "progress": 100,
                "x": 2, "y": 0
            },
            {
                "id": str(uuid.uuid4()),
                "name": "FastAPI Framework",
                "description": "Học framework FastAPI để xây dựng API",
                "icon": "Layers",
                "color": "#EF4444",
                "type": "knowledge",
                "status": "not_started",
                "progress": 0,
                "x": 2, "y": 1
            }
        ]
        
        print("📦 Creating 4 skill nodes:")
        for node in nodes:
            await conn.execute(
                text("""
                    INSERT INTO user_skill_nodes 
                    (id, tree_id, name, description, icon, color, status, progress_percent, position_x, position_y)
                    VALUES (:id, :tree_id, :name, :desc, :icon, :color, :status, :progress, :x, :y)
                """),
                {
                    "id": node["id"],
                    "tree_id": tree_id,
                    "name": node["name"],
                    "desc": node["description"],
                    "icon": node["icon"],
                    "color": node["color"],
                    "status": node["status"],
                    "progress": node["progress"],
                    "x": node["x"],
                    "y": node["y"]
                }
            )
            print(f"   ✅ [{node['type'].upper()}] {node['name']} ({node['status']})")
        
        # 4. Tạo timeline items (chỉ nếu có learning_resources)
        print("📦 Checking for learning resources...")
        resources = await conn.execute(text("SELECT id, title FROM learning_resources LIMIT 3"))
        resources_list = resources.fetchall()
        
        if resources_list:
            print(f"📅 Creating {len(resources_list)} timeline items:")
            today = date.today()
            priorities = ['high', 'medium', 'low']
            
            for i, res in enumerate(resources_list):
                scheduled = today + timedelta(days=i + 1)
                deadline = today + timedelta(days=7)
                priority = priorities[i] if i < len(priorities) else 'medium'
                
                await conn.execute(
                    text("""
                        INSERT INTO timeline_items (user_id, resource_id, scheduled_date, deadline, priority)
                        VALUES (:user_id, :resource_id, :scheduled, :deadline, :priority)
                    """),
                    {
                        "user_id": user_id,
                        "resource_id": res.id,
                        "scheduled": scheduled,
                        "deadline": deadline,
                        "priority": priority
                    }
                )
                print(f"   📅 {scheduled}: {res.title[:40]}...")
        else:
            print("   ⚠️ Không có learning resources, bỏ qua timeline items")
    
    await engine.dispose()
    
    print("\n✅ Done!")
    print("📋 Summary:")
    print("   - 1 Ability: Backend Development")
    print("   - 1 Skill: REST API Design")
    print("   - 2 Knowledge: Python Basics, FastAPI Framework")


if __name__ == "__main__":
    asyncio.run(create_simple_tree())
