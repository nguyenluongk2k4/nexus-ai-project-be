# Seed data from JSON files
# Import skill tree data from frontend JSON files into PostgreSQL + ChromaDB

import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime

sys.path.insert(0, '.')

from infrastructure.database.connection import async_session_maker
from infrastructure.database.models import (
    SkillTreeTemplateModel, TemplateSkillNodeModel, TemplateSkillPathModel,
    LearningResourceModel
)


# JSON data files
DATA_DIRS = [
    Path("../frontend/src/data"),
    Path("../frontend/src/domain/data"),
]

# Map difficulty levels
DIFFICULTY_MAP = {
    "Beginner": "beginner",
    "Intermediate": "intermediate", 
    "Advanced": "advanced",
    "Expert": "expert",
}


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
    all_nodes = []  # [(node_model, parent_id, depth)]
    node_count = 0
    resource_count = 0
    
    async def process_node(node_data: dict, parent_id: str | None, depth: int):
        nonlocal node_count, resource_count
        
        node_id = str(uuid4())
        
        # Parse difficulty level
        difficulty = node_data.get('difficultyLevel', 'beginner')
        if isinstance(difficulty, str):
            difficulty = DIFFICULTY_MAP.get(difficulty, difficulty.lower())
        
        # Parse estimated hours
        estimated_hours = None
        time_str = node_data.get('estimatedTimeToComplete', '')
        if time_str and isinstance(time_str, str):
            # Extract first number from "40-60 hours"
            import re
            match = re.search(r'(\d+)', time_str)
            if match:
                estimated_hours = int(match.group(1))
        
        # Create node
        node = TemplateSkillNodeModel(
            id=node_id,
            template_id=template_id,
            name=node_data.get('name', 'Unknown'),
            description=node_data.get('description'),
            node_type=node_data.get('type', 'knowledge'),
            difficulty_level=difficulty,
            estimated_hours=estimated_hours,
            keywords=node_data.get('keywords', []),
            created_at=datetime.now()
        )
        session.add(node)
        node_count += 1
        
        # Add self-reference path
        self_path = TemplateSkillPathModel(
            ancestor_id=node_id,
            descendant_id=node_id,
            depth=0
        )
        session.add(self_path)
        
        # Add path from parent (if exists)
        if parent_id:
            parent_path = TemplateSkillPathModel(
                ancestor_id=parent_id,
                descendant_id=node_id,
                depth=1
            )
            session.add(parent_path)
        
        all_nodes.append((node_id, parent_id, depth))
        
        # Add learning resources
        resources = node_data.get('learningResources', [])
        for idx, res in enumerate(resources):
            resource = LearningResourceModel(
                id=str(uuid4()),
                skill_node_id=node_id,
                title=res.get('name', res.get('title', 'Unknown')),
                url=res.get('url'),
                resource_type='documentation',
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
    
    # Process root and all children
    await process_node(root, None, 0)
    
    # Build full closure table paths (ancestors at all depths)
    # For each node, add paths from all ancestors
    for node_id, parent_id, depth in all_nodes:
        if parent_id:
            # Find all ancestors of parent and add paths to current node
            for ancestor_id, ancestor_parent_id, ancestor_depth in all_nodes:
                if ancestor_depth < depth:
                    # Check if ancestor is in the path to root
                    path_depth = depth - ancestor_depth
                    if path_depth > 1:
                        # Only add if not already a direct parent
                        try:
                            path = TemplateSkillPathModel(
                                ancestor_id=ancestor_id,
                                descendant_id=node_id,
                                depth=path_depth
                            )
                            session.add(path)
                        except:
                            pass  # Skip duplicates
    
    await session.flush()
    print(f"  📊 Nodes: {node_count}, Resources: {resource_count}")


async def main():
    """Import all JSON skill tree files"""
    print("🌱 Importing Skill Tree Data from JSON files...")
    print("=" * 50)
    
    # Collect all JSON files
    json_files = []
    for data_dir in DATA_DIRS:
        if data_dir.exists():
            for f in data_dir.glob("*.json"):
                if f not in json_files:
                    json_files.append(f)
    
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
        for json_file in json_files:
            try:
                await import_json_file(session, json_file)
            except Exception as e:
                print(f"  ❌ Error: {e}")
                continue
        
        await session.commit()
    
    print("\n" + "=" * 50)
    print("🎉 Import complete!")


if __name__ == "__main__":
    asyncio.run(main())
