import asyncio
import sys
import os
from pathlib import Path
from uuid import uuid4

# Add backend directory to python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, func, and_
from shared.database.connection import async_session_maker
from modules.skill_tree.infrastructure.models import (
    TemplateSkillNodeModel, 
    TemplateSkillPathModel,
    SkillTreeTemplateModel
)

import chromadb
from chromadb.config import Settings

# ChromaDB Config
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))
COLLECTION_NAME = "ksa_project"

async def main():
    print(f"🚀 Starting ChromaDB Sync...")
    print(f"   Target: {CHROMA_HOST}:{CHROMA_PORT} (Collection: {COLLECTION_NAME})")
    
    # 1. Connect to ChromaDB
    try:
        from chromadb.utils import embedding_functions
        
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        
        # Delete existing collection to start fresh (ensure no stale data)
        try:
            client.delete_collection(name=COLLECTION_NAME)
            print(f"   🗑️  Deleted existing collection '{COLLECTION_NAME}'")
        except:
            pass
        
        # Create embedding function matching backend's model
        sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        )
            
        collection = client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=sentence_transformer_ef
        )
        print(f"   ✅ Created fresh collection '{COLLECTION_NAME}' with dimension 768")
        
    except Exception as e:
        print(f"   ❌ Failed to connect to ChromaDB: {e}")
        return

    # 2. Connect to PostgreSQL and fetch data
    async with async_session_maker() as session:
        print(f"\n📥 Fetching nodes from PostgreSQL...")
        
        # Get all templates
        templates_result = await session.execute(select(SkillTreeTemplateModel))
        templates = templates_result.scalars().all()
        template_map = {t.id: t.name for t in templates}
        print(f"   Found {len(templates)} templates")

        # Get all nodes with their depth/level from root
        # We assume Root is depth=0 or depth=1 depending on implementation
        # Let's query: Node + Template Name + Max Depth
        
        query = select(TemplateSkillNodeModel)
        result = await session.execute(query)
        nodes = result.scalars().all()
        
        print(f"   Found {len(nodes)} nodes total")
        
        # Batch-fetch all parent IDs in one query (much faster!)
        print(f"   Fetching parent relationships...")
        all_node_ids = [node.id for node in nodes]
        
        parent_query = (
            select(
                TemplateSkillPathModel.descendant_id,
                TemplateSkillPathModel.ancestor_id
            )
            .where(
                TemplateSkillPathModel.descendant_id.in_(all_node_ids),
                TemplateSkillPathModel.depth == 1
            )
        )
        parent_results = await session.execute(parent_query)
        parent_map = {row.descendant_id: str(row.ancestor_id) for row in parent_results.all()}
        
        print(f"   Building ChromaDB documents...")

        documents = []
        metadatas = []
        ids = []
        
        count_by_type = {"ability": 0, "skill": 0, "knowledge": 0, "unknown": 0}
        total_indexed = 0
        
        for node in nodes:
            # Calculate Level/Type
            depth_query = select(func.max(TemplateSkillPathModel.depth)).where(
                TemplateSkillPathModel.descendant_id == node.id
            )
            depth_result = await session.execute(depth_query)
            max_depth = depth_result.scalar()
            
            if max_depth is None:
                max_depth = 0
                
            # Determine Node Type based on Depth
            node_type = "unknown"
            if max_depth == 1:
                node_type = "ability"
            elif max_depth == 2:
                node_type = "skill"
            elif max_depth >= 3:
                node_type = "knowledge"
            else:
                if max_depth == 0:
                     node_type = "specialization" 
            
            if node_type == "specialization":
                pass
                
            if node_type in count_by_type:
                count_by_type[node_type] += 1
            else:
                 count_by_type["unknown"] += 1

            # Prepare Data
            text_content = f"{node.name}. {node.description or ''}"
            
            # Get parent ID
            parent_id = parent_map.get(node.id)
            
            documents.append(text_content)
            ids.append(str(node.id))
            metadatas.append({
                "node_type": node_type,
                "name": node.name,
                "description": node.description or "",
                "difficulty": node.difficulty_level or "beginner",
                "template_name": template_map.get(node.template_id, "Unknown"),
                "level": max_depth,
                "parent_id": parent_id or ""  # Add parent_id
            })
            total_indexed += 1
            
            if len(documents) >= 100:
                collection.add(documents=documents, metadatas=metadatas, ids=ids)
                print(f" [{total_indexed} nodes]", end="", flush=True)
                documents = []
                metadatas = []
                ids = []

        # Add remaining
        if documents:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
            
        print(f"\n\n✅ Sync Complete!")
        print(f"   Total indexed: {total_indexed}/{len(nodes)} nodes")
        print(f"   Type Distribution: {count_by_type}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

