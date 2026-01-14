# Seed data from JSON files
# Import skill tree data from frontend JSON files into PostgreSQL + ChromaDB

import asyncio
import json
import sys
import re
from pathlib import Path
from uuid import uuid4
from datetime import datetime

sys.path.insert(0, '.')

from shared.database.connection import async_session_maker
from modules.skill_tree.infrastructure.models import (
    SkillTreeTemplateModel, TemplateSkillNodeModel, TemplateSkillPathModel,
    LearningResourceModel
)


# JSON data files
DATA_DIRS = [
    Path("../frontend/src/data"),
    Path("../frontend/src/domain/data"),
]

# Map difficulty levels (Vietnamese and English variants)
DIFFICULTY_MAP = {
    "Beginner": "beginner",
    "Intermediate": "intermediate", 
    "Advanced": "advanced",
    "Expert": "expert",
    # Vietnamese variants
    "nâng cao": "advanced",
    "trung bình": "intermediate",
    "cơ bản": "beginner",
    "nâng cao trung cấp": "intermediate",
    "trung bình đến nâng cao": "intermediate",
}

# Valid difficulty values per database constraint
VALID_DIFFICULTIES = {'beginner', 'intermediate', 'advanced', 'expert'}


async def import_json_file(session, file_path: Path):
    """Import a single JSON skill tree file"""
    print(f"\n📂 Importing: {file_path.name}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not data:
        print(f"  ⚠️ Empty file, skipping")
        return
    
    # Get root node (first item in array)
    root = data[0] if isinstance(data, list) else data
    
    # Create template from root
    template_id = str(uuid4())
    template_name = root.get('name', file_path.stem.replace('_', ' ').title())
    
    template = SkillTreeTemplateModel(
        id=template_id,
        name=template_name,
        description=f"Skill tree for {template_name}",
        category=root.get('type', 'specialization'),
        icon="🌳",
        color="#3B82F6",
        is_active=True,
        created_at=datetime.now()
    )
    session.add(template)
    await session.flush()
    print(f"  ✅ Created template: {template_name}")
    
    # Track all nodes for closure table
    all_nodes = []  # [(node_id, parent_id, depth)]
    node_count = 0
    resource_count = 0
    
    async def process_node(node_data, parent_id: str | None, depth: int):
        nonlocal node_count, resource_count
        
        # Skip if node_data is not a dict (might be string or other type)
        if not isinstance(node_data, dict):
            return
        
        node_id = str(uuid4())
        
        # Parse and validate difficulty level
        difficulty = node_data.get('difficultyLevel', 'beginner')
        if isinstance(difficulty, str):
            difficulty = DIFFICULTY_MAP.get(difficulty, difficulty.lower())
        # Validate against DB constraint - fallback to 'beginner' if invalid
        if difficulty not in VALID_DIFFICULTIES:
            difficulty = 'beginner'
        
        # Parse estimated hours
        estimated_hours = None
        time_str = node_data.get('estimatedTimeToComplete', '')
        if time_str and isinstance(time_str, str):
            # Extract first number from "40-60 hours"
            match = re.search(r'(\d+)', time_str)
            if match:
                estimated_hours = int(match.group(1))
        
        # Create node (note: DB schema doesn't have node_type or keywords columns)
        node = TemplateSkillNodeModel(
            id=node_id,
            template_id=template_id,
            name=node_data.get('name', 'Unknown'),
            description=node_data.get('description'),
            difficulty_level=difficulty,
            estimated_hours=estimated_hours,
            created_at=datetime.now()
        )
        session.add(node)
        node_count += 1
        
        all_nodes.append((node_id, parent_id, depth))
        
        # Add learning resources
        resources = node_data.get('learningResources', [])
        for idx, res in enumerate(resources):
            if isinstance(res, str):
                title = res
                url = None
                res_type = 'General'
            elif isinstance(res, dict):
                title = res.get('name', res.get('title', 'Unknown'))
                url = res.get('url')
                res_type = 'documentation'
            else:
                continue
                
            resource = LearningResourceModel(
                id=str(uuid4()),
                skill_node_id=node_id,
                title=title[:255],
                url=url,
                resource_type=res_type,
                platform=None,
                is_free=True,
                sort_order=idx
            )
            session.add(resource)
            resource_count += 1
        
        # Process children recursively
        children = node_data.get('children', [])
        for child in children:
            await process_node(child, node_id, depth + 1)
    
    # Process root and all children - collect all nodes first
    await process_node(root, None, 0)
    
    # Flush all nodes to DB first (before inserting paths)
    await session.flush()
    print(f"  📊 Nodes: {node_count}, Resources: {resource_count}")
    
    # Now insert closure table paths
    path_count = 0
    for node_id, parent_id, depth in all_nodes:
        # Add self-reference path (depth=0)
        self_path = TemplateSkillPathModel(
            ancestor_id=node_id,
            descendant_id=node_id,
            depth=0
        )
        session.add(self_path)
        path_count += 1
        
        # Add direct parent path (depth=1)
        if parent_id:
            parent_path = TemplateSkillPathModel(
                ancestor_id=parent_id,
                descendant_id=node_id,
                depth=1
            )
            session.add(parent_path)
            path_count += 1
    
    # Build full closure table paths (ancestors at all depths)
    # For efficiency, build a parent lookup
    parent_map = {node_id: parent_id for node_id, parent_id, depth in all_nodes}
    
    for node_id, parent_id, depth in all_nodes:
        if depth > 1 and parent_id:
            # Walk up the tree and add paths for all ancestors
            current_parent = parent_map.get(parent_id)
            current_depth = 2
            while current_parent:
                path = TemplateSkillPathModel(
                    ancestor_id=current_parent,
                    descendant_id=node_id,
                    depth=current_depth
                )
                session.add(path)
                path_count += 1
                current_parent = parent_map.get(current_parent)
                current_depth += 1
    
    await session.flush()
    print(f"  🔗 Paths: {path_count}")


async def main():
    """Import all JSON skill tree files"""
    print("🌱 Importing Skill Tree Data from JSON files...")
    print("=" * 50)
    
    # Collect all JSON files
    json_files = []
    seen_names = set()
    for data_dir in DATA_DIRS:
        if data_dir.exists():
            for f in data_dir.glob("*.json"):
                if f.name not in seen_names:
                    json_files.append(f)
                    seen_names.add(f.name)
    
    print(f"Found {len(json_files)} JSON files")
    
    async with async_session_maker() as session:
        # Check if already imported
        from sqlalchemy import select, func
        count = await session.execute(
            select(func.count()).select_from(SkillTreeTemplateModel)
        )
        existing = count.scalar()
        
        if existing > 0:
            print(f"\n⚠️ Database already has {existing} templates.")
            print("   Run with --force to reimport, or delete existing data first.")
            
            if len(sys.argv) > 1 and sys.argv[1] == "--force":
                print("   --force detected, deleting existing data...")
                await session.execute(TemplateSkillPathModel.__table__.delete())
                await session.execute(LearningResourceModel.__table__.delete())
                await session.execute(TemplateSkillNodeModel.__table__.delete())
                await session.execute(SkillTreeTemplateModel.__table__.delete())
                await session.commit()
                print("   ✅ Deleted existing data")
            else:
                return
        
        # Import each file
        success_count = 0
        for json_file in json_files:
            try:
                await import_json_file(session, json_file)
                success_count += 1
            except Exception as e:
                print(f"  ❌ Error: {e}")
                await session.rollback()  # Rollback on error to continue with next file
                continue
        
        if success_count > 0:
            await session.commit()
            print(f"\n✅ Successfully imported {success_count}/{len(json_files)} files")
        else:
            print("\n❌ No files were imported successfully")
    
    print("\n" + "=" * 50)
    print("🎉 Import complete!")


if __name__ == "__main__":
    asyncio.run(main())
