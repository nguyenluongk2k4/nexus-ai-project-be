# Skill Tree Query Service
# Orchestrates: User message → Intent extraction → ChromaDB search → Node selection

import json
import re
import uuid
from typing import List, Optional
from dataclasses import dataclass

from modules.chat.providers import get_llm
from shared.vector_store.chroma_search_util import get_chroma_search_util
from modules.skill_tree.infrastructure.repository import get_skill_tree_repository


@dataclass
class TreeNodeResult:
    """Node result for frontend tree visualization"""
    id: str
    name: str
    description: Optional[str] = None
    type: str = "skill"  # root, specialization, ability, skill, knowledge
    parent_id: Optional[str] = None
    level: int = 0
    metadata: Optional[dict] = None


class SkillTreeQueryService:
    """
    Service to extract learning intent from chat and query skill nodes from ChromaDB.
    
    Flow:
    1. Detect if message is a skill tree query (learning intent)
    2. Extract keywords from the message
    3. Search ChromaDB for related skill nodes
    4. Use LLM to select and organize best nodes
    5. Return formatted nodes for tree visualization
    """
    
    def __init__(self):
        self.llm = get_llm()
        self.chroma_util = get_chroma_search_util()
    
    async def is_skill_tree_query(self, message: str) -> bool:
        """Detect if message is asking about learning/skill tree using Gemini"""
        try:
            prompt = f"""Analyze if this message is asking about learning, skill development, career roadmap, or wants to explore a skill tree.

Message: "{message}"

Consider these as skill tree queries:
- Asking to learn something (e.g., "I want to learn Python")
- Career/roadmap questions (e.g., "How to become a backend developer")
- Skill exploration (e.g., "Show me cloud computing skills")
- Learning path requests (e.g., "What should I learn first")

Reply with ONLY "yes" or "no"."""
            
            response = await self.llm.generate(prompt)
            is_query = response.strip().lower().startswith("yes")
            
            if is_query:
                print(f"🎯 Detected skill tree query: {message[:50]}...")
            
            return is_query
        except Exception as e:
            print(f"Intent detection error: {e}")
            return False
    
    async def extract_keywords(self, message: str) -> List[str]:
        """Extract searchable keywords from user message"""
        prompt = f"""Extract 3-5 technical keywords from this learning request for searching a skill database.

Message: "{message}"

Return ONLY a JSON array of keywords, like: ["keyword1", "keyword2", "keyword3"]
Focus on technical terms, technologies, and skill areas."""

        try:
            response = await self.llm.generate(prompt)
            # Parse JSON from response
            match = re.search(r'\[.*?\]', response, re.DOTALL)
            if match:
                keywords = json.loads(match.group())
                return [str(k).strip() for k in keywords if k]
            return []
        except Exception as e:
            print(f"Keyword extraction error: {e}")
            # Fallback: simple word extraction
            words = message.lower().split()
            return [w for w in words if len(w) > 3][:5]
    
    async def search_nodes(self, keywords: List[str]) -> List[str]:
        """Search ChromaDB for skill nodes matching multiple keywords"""
        # Use shared ChromaSearchUtil
        return self.chroma_util.search_multiple(keywords, n_results_per_query=5, max_total=15)
    
    async def select_and_organize_nodes(
        self, 
        message: str, 
        search_results: List[str]
    ) -> List[TreeNodeResult]:
        """Use LLM to select and organize the most relevant nodes into a tree structure"""
        
        if not search_results:
            return []
        
        # Format search results for LLM
        results_text = "\n".join([f"- {doc}" for doc in search_results[:10]])
        
        prompt = f"""Based on this learning request and search results, create a skill tree structure.

USER REQUEST: "{message}"

AVAILABLE SKILLS:
{results_text}

Create a hierarchical skill tree with 5-8 nodes. Return ONLY valid JSON in this exact format:
{{
  "nodes": [
    {{"id": "1", "name": "Root Topic", "type": "root", "level": 0, "parent_id": null}},
    {{"id": "2", "name": "Subtopic 1", "type": "skill", "level": 1, "parent_id": "1"}},
    {{"id": "3", "name": "Subtopic 2", "type": "skill", "level": 1, "parent_id": "1"}}
  ]
}}

Types: root, specialization, skill, knowledge
Levels: 0=root, 1=main topics, 2=subtopics, 3=details"""

        try:
            response = await self.llm.generate(prompt)
            
            # Extract JSON from response
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                data = json.loads(match.group())
                nodes = data.get("nodes", [])
                
                return [
                    TreeNodeResult(
                        id=str(n.get("id", "")),
                        name=n.get("name", "Unknown"),
                        description=n.get("description"),
                        type=n.get("type", "skill"),
                        parent_id=n.get("parent_id"),
                        level=n.get("level", 0),
                        metadata=n.get("metadata")
                    )
                    for n in nodes
                ]
        except Exception as e:
            print(f"Node organization error: {e}")
        
        # Fallback: create simple structure from search results
        return self._create_fallback_tree(message, search_results)
    
    def _create_fallback_tree(self, message: str, results: List[str]) -> List[TreeNodeResult]:
        """Create a simple tree structure when LLM fails"""
        import hashlib
        
        nodes = [
            TreeNodeResult(
                id="root",
                name=message[:50],
                type="root",
                level=0
            )
        ]
        
        for i, doc in enumerate(results[:6]):
            node_id = hashlib.md5(doc.encode()).hexdigest()[:8]
            name = doc[:50] if len(doc) > 50 else doc
            
            nodes.append(TreeNodeResult(
                id=node_id,
                name=name,
                type="skill",
                parent_id="root",
                level=1
            ))
        
        return nodes
    async def process_question(self, message: str) -> Optional[dict]:
        """
        Step 1: Process question with Gemini to extract intent and keywords.
        Returns structured JSON with expanded keywords for vector search.
        """
        prompt = f"""Phân tích câu hỏi học tập của user và trả về JSON với format sau:

INPUT: "{message}"

OUTPUT FORMAT (JSON only, no markdown):
{{
  "intent": "learn",
  "main_topic": "chủ đề chính bằng tiếng Anh",
  "sub_topics": ["topic1", "topic2"],
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "difficulty_hint": "beginner" | "intermediate" | "advanced" | null,
  "is_valid_learning_query": true | false
}}

RULES:
- keywords: 5-8 từ khóa tiếng Anh để search vector database
- QUAN TRỌNG: Nếu user nói topic RỘNG (VD: "backend", "devops", "frontend"),
  hãy MỞ RỘNG thành các công nghệ/kỹ năng CỤ THỂ liên quan
  
EXAMPLES:
- "học backend" → keywords: ["backend", "API", "REST", "Node.js", "Express", "database", "SQL"]
- "học devops" → keywords: ["DevOps", "Docker", "Kubernetes", "CI/CD", "AWS", "Linux"]
- "học frontend" → keywords: ["frontend", "React", "JavaScript", "CSS", "HTML", "TypeScript"]
- "học Python" → keywords: ["Python", "Flask", "Django", "OOP", "scripting"]

Trả về JSON only, không có text khác."""

        try:
            response = await self.llm.generate(prompt)
            print(f"📝 [Step1] Gemini raw response: {response[:200]}...")
            
            # Parse JSON from response
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                parsed = json.loads(match.group())
                print(f"✅ [Step1] Parsed: intent={parsed.get('intent')}, keywords={parsed.get('keywords')}")
                return parsed
            return None
        except Exception as e:
            print(f"❌ [Step1] Error processing question: {e}")
            # Fallback for rate limits or other errors
            print("⚠️ [Step1] Using fallback parsing due to AI error")
            return {
                "intent": "learn",
                "main_topic": message,
                "sub_topics": [],
                "keywords": [message] + [w for w in message.split() if len(w) > 3],  # simple keyword extraction
                "difficulty_hint": "beginner",
                "is_valid_learning_query": True
            }

    async def search_chroma(self, keywords: List[str]) -> List[dict]:
        """
        Step 2: Search ChromaDB for candidate nodes using keywords.
        Returns list of dicts with keys: id, document, metadata, distance.
        """
        try:
            # Use search_with_metadata to get IDs
            results = self.chroma_util.search_with_metadata(keywords, n_results_per_query=5, max_total=15)
            print(f"🔍 [Step2] ChromaDB found {len(results)} candidates")
            return results
        except Exception as e:
            print(f"❌ [Step2] ChromaDB search error: {e}")
            return []

    def is_valid_uuid(self, val):
        try:
            uuid.UUID(str(val))
            return True
        except ValueError:
            return False

    async def select_nodes(self, message: str, main_topic: str, candidates: List[dict]) -> List[dict]:
        """
        Step 3: Use Gemini to select best nodes from candidates.
        Returns list of selected items (dict with id, name, metadata).
        """
        if not candidates:
            return []
        
        # Number candidates for easy selection (use 'document' as display name)
        # Handle cases where document might be long text
        display_candidates = []
        for i, c in enumerate(candidates[:15]):
            doc = c.get('document', 'Unknown')
            # Try to get short name from metadata if available
            meta = c.get('metadata', {}) or {}
            short_name = meta.get('name') or meta.get('title') or (doc[:100] + "..." if len(doc) > 100 else doc)
            display_candidates.append(f"{i+1}. {short_name}")
            
        numbered_candidates = "\n".join(display_candidates)
        
        prompt = f"""Từ danh sách skills dưới đây, chọn 5-8 skills phù hợp nhất để tạo skill tree cho user.

USER REQUEST: "{message}"
MAIN TOPIC: "{main_topic}"

AVAILABLE SKILLS (chọn từ đây):
{numbered_candidates}

CHỈ trả về các SỐ THỨ TỰ của skills đã chọn, format:
{{"selected": [1, 3, 5, 7, 8]}}

Chọn skills theo thứ tự logic từ cơ bản đến nâng cao.
JSON only, không text khác."""

        try:
            response = await self.llm.generate(prompt)
            print(f"🎯 [Step3] Gemini selection response: {response[:200]}...")
            
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                data = json.loads(match.group())
                selected_indices = data.get("selected", [])
                
                selected_items = []
                for idx in selected_indices:
                    if isinstance(idx, int) and 1 <= idx <= len(candidates):
                        item = candidates[idx - 1]
                        selected_items.append({
                            "id": item.get("id"),
                            "name": item.get("document"),
                            "metadata": item.get("metadata", {})
                        })
                
                print(f"✅ [Step3] Selected {len(selected_items)} nodes")
                return selected_items
            return [{"id": c.get("id"), "name": c.get("document"), "metadata": c.get("metadata", {})} for c in candidates[:5]]
        except Exception as e:
            print(f"❌ [Step3] Node selection error: {e}")
            return [{"id": c.get("id"), "name": c.get("document"), "metadata": c.get("metadata", {})} for c in candidates[:5]]

    async def build_tree_from_db(self, selected_items: List[dict], main_topic: str) -> List[TreeNodeResult]:
        """
        Step 4: Fetch real data from PostgreSQL using IDs first, then Names.
        """
        if not selected_items:
            return [
                TreeNodeResult(
                    id="root",
                    name=main_topic,
                    description=f"Lộ trình học {main_topic}",
                    type="root",
                    level=0,
                    parent_id=None
                )
            ]
        
        repo = get_skill_tree_repository()
        nodes = []
        
        # Create root node
        root_id = "root"
        nodes.append(TreeNodeResult(
            id=root_id,
            name=f"🎯 {main_topic}",
            description=f"Lộ trình học {main_topic}",
            type="root",
            level=0,
            parent_id=None
        ))
        
        for i, item in enumerate(selected_items[:8]):
            raw_id = item.get("id")
            raw_name = item.get("name", "Unknown")
            metadata = item.get("metadata") or {}
            
            # 1. Determine best ID to query
            target_ids = []
            if self.is_valid_uuid(raw_id):
                target_ids.append(raw_id)
            
            # Check metadata for alternate IDs
            if self.is_valid_uuid(metadata.get("id")):
                target_ids.append(metadata.get("id"))
            if self.is_valid_uuid(metadata.get("node_id")):
                target_ids.append(metadata.get("node_id"))
            if self.is_valid_uuid(metadata.get("skill_id")):
                target_ids.append(metadata.get("skill_id"))
                
            db_node = None
            try:
                # Try ID search
                if target_ids:
                    # Remove duplicates and query
                    target_ids = list(set(target_ids))
                    db_nodes_by_id = await repo.get_nodes_by_ids(target_ids)
                    if db_nodes_by_id:
                        db_node = db_nodes_by_id[0]
                
                # 2. Fallback to Name search
                if not db_node:
                    # Try to find a good name to search
                    search_name = metadata.get("name") or metadata.get("title")
                    if not search_name and raw_name and len(raw_name) < 150:
                        search_name = raw_name
                        
                    if search_name:
                        db_nodes_by_name = await repo.search_nodes_by_name(search_name, limit=1)
                        if db_nodes_by_name:
                            db_node = db_nodes_by_name[0]
                
                if db_node:
                    # Determine hierarchy: level 1 (2 abilities), level 2 (3 skills), level 3 (3 knowledge)
                    if i < 2:
                        level = 1
                        parent_id = root_id
                        node_type = "ability"
                    elif i < 5:
                        level = 2
                        # Map to one of the ability nodes (indices 1, 2 in nodes list)
                        parent_idx = (i % 2) + 1
                        if parent_idx < len(nodes):
                            parent_id = nodes[parent_idx].id
                        else:
                            parent_id = root_id
                        node_type = "skill"
                    else:
                        level = 3
                        # Map to one of the skill nodes (indices 3, 4, 5 in nodes list)
                        skill_idx = 3 + ((i - 5) % 3)
                        if skill_idx < len(nodes):
                            parent_id = nodes[skill_idx].id
                        else:
                            parent_id = root_id
                        node_type = "knowledge"
                    
                    # Use real DB data
                    nodes.append(TreeNodeResult(
                        id=str(db_node.id),
                        name=db_node.name,
                        description=db_node.description,
                        type=node_type,
                        level=level,
                        parent_id=parent_id,
                        metadata={
                            "difficultyLevel": db_node.difficulty_level or "beginner",
                            "estimatedHours": db_node.estimated_hours or 5
                        }
                    ))
                    print(f"  ✅ Found in DB: {db_node.name} ({db_node.id})")
                else:
                    # Fallback if not in DB - same level logic
                    if i < 2:
                        level = 1
                        parent_id = root_id
                        node_type = "ability"
                    elif i < 5:
                        level = 2
                        parent_idx = (i % 2) + 1
                        if parent_idx < len(nodes):
                            parent_id = nodes[parent_idx].id
                        else:
                            parent_id = root_id
                        node_type = "skill"
                    else:
                        level = 3
                        skill_idx = 3 + ((i - 5) % 3)
                        if skill_idx < len(nodes):
                            parent_id = nodes[skill_idx].id
                        else:
                            parent_id = root_id
                        node_type = "knowledge"
                    
                    # Use extracted name or truncate raw name
                    display_name = metadata.get("name") or (raw_name[:50] + "..." if len(raw_name) > 50 else raw_name)
                    
                    nodes.append(TreeNodeResult(
                        id=f"node-{i}",
                        name=display_name,
                        description=f"Skill: {display_name}",
                        type=node_type,
                        level=level,
                        parent_id=parent_id
                    ))
                    print(f"  ⚠️ Not in DB, using name: {display_name}")
                    
            except Exception as e:
                print(f"  ❌ Error fetching node '{str(raw_name)[:30]}...': {e}")
        
        print(f"🌳 [Step4] Built tree with {len(nodes)} nodes from PostgreSQL")
        return nodes

    async def query(
        self, 
        message: str,
        max_level: int = None  # None = all levels, 1 = lazy load (root + abilities)
    ) -> Optional[List[TreeNodeResult]]:
        """
        Main entry point: Full pipeline to process message and return tree nodes.
        
        Pipeline:
        1. Process question with Gemini (extract intent + keywords)
        2. Search ChromaDB for candidate nodes
        3. Use Gemini to select best nodes for tree
        4. Build tree structure
        
        Args:
            message: User's learning query
            max_level: Maximum level to return (None=all, 1=lazy load)
        """
        print(f"\n{'='*60}")
        print(f"🚀 [SkillTree] Processing query: '{message}' (max_level={max_level})")
        print(f"{'='*60}")
        
        # Step 1: Process question with Gemini
        parsed = await self.process_question(message)
        
        if not parsed:
            print("⚠️ [SkillTree] Could not parse question, skipping tree")
            return None
        
        if not parsed.get("is_valid_learning_query", False):
            print("⚠️ [SkillTree] Not a learning query, skipping tree")
            return None
        
        main_topic = parsed.get("main_topic", message[:30])
        keywords = parsed.get("keywords", [])
        
        if not keywords:
            keywords = [main_topic]
        
        # Step 2: Search ChromaDB
        candidates = await self.search_chroma(keywords)
        
        # Step 3: Select nodes with Gemini
        selected_nodes = await self.select_nodes(message, main_topic, candidates)
        
        # Step 4: Build tree
        tree_nodes = await self.build_tree_from_db(selected_nodes, main_topic)
        
        # Filter by max_level if specified
        if max_level is not None and tree_nodes:
            tree_nodes = [n for n in tree_nodes if n.level <= max_level]
            print(f"📊 [SkillTree] Filtered to {len(tree_nodes)} nodes (max_level={max_level})")
        
        print(f"\n✅ [SkillTree] Returning {len(tree_nodes)} tree nodes")
        return tree_nodes


# Singleton instance
_skill_tree_service: Optional[SkillTreeQueryService] = None

def get_skill_tree_query_service() -> SkillTreeQueryService:
    """Get or create singleton SkillTreeQueryService"""
    global _skill_tree_service
    if _skill_tree_service is None:
        _skill_tree_service = SkillTreeQueryService()
    return _skill_tree_service
