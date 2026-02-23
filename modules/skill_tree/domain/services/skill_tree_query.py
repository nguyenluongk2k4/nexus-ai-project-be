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
    name: str  # Short name for visualization
    full_name: Optional[str] = None  # Full name for details/tooltips
    description: Optional[str] = None
    type: str = "skill"  # root, specialization, ability, skill, knowledge
    parent_id: Optional[str] = None
    level: int = 0
    icon: Optional[str] = None
    metadata: Optional[dict] = None
    original_node_id: Optional[str] = None  # Original DB/Chroma ID


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

Create a hierarchical skill tree with 5-8 nodes.
IMPORTANT: The ROOT NODE name must be the specific Job Title, Role, or Main Skill (e.g., "Data Scientist", "Backend Developer"), NOT generic terms like "Job Readiness" or "Root Topic".

Return ONLY valid JSON in this exact format:
{{
  "nodes": [
    {{"id": "1", "name": "<Specific Role/Skill Name>", "type": "root", "level": 0, "parent_id": null}},
    {{"id": "2", "name": "Subtopic 1", "type": "skill", "level": 1, "parent_id": "1"}}
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
  "main_topic": "Specific Job Title or Technology (e.g., 'Backend Engineer', 'Data Scientist'). NO generic terms.",
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
        Search separately by type to ensure diversity.
        Returns list of dicts with keys: id, document, metadata, distance.
        """
        try:
            all_results = []
            
            # Search for Abilities (level 1) - need 2, get 5 for selection
            print(f"  🔍 Searching abilities...")
            ability_results = self.chroma_util.search_with_metadata(
                keywords, 
                n_results_per_query=2,
                max_total=5,
                metadata_filter={"node_type": "ability"}
            )
            all_results.extend(ability_results)
            print(f"     Found {len(ability_results)} abilities")
            
            # Search for Skills (level 2) - need 4, get 8 for selection
            print(f"  🔍 Searching skills...")
            skill_results = self.chroma_util.search_with_metadata(
                keywords,
                n_results_per_query=3,
                max_total=8,
                metadata_filter={"node_type": "skill"}
            )
            all_results.extend(skill_results)
            print(f"     Found {len(skill_results)} skills")
            
            # Search for Knowledge (level 3) - need 8, get 12 for selection
            print(f"  🔍 Searching knowledge...")
            knowledge_results = self.chroma_util.search_with_metadata(
                keywords,
                n_results_per_query=4,
                max_total=12,
                metadata_filter={"node_type": "knowledge"}
            )
            all_results.extend(knowledge_results)
            print(f"     Found {len(knowledge_results)} knowledge")
            
            print(f"🔍 [Step2] ChromaDB found {len(all_results)} candidates total")
            return all_results
        except Exception as e:
            print(f"❌ [Step2] ChromaDB search error: {e}")
            import traceback
            traceback.print_exc()
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
        display_candidates = []
        for i, c in enumerate(candidates[:25]):
            doc = c.get('document', 'Unknown')
            # Try to get short name from metadata if available
            meta = c.get('metadata', {}) or {}
            short_name = meta.get('name') or meta.get('title') or (doc[:100] + "..." if len(doc) > 100 else doc)
            display_candidates.append(f"{i+1}. {short_name}")
            
        numbered_candidates = "\n".join(display_candidates)
        
        prompt = f"""Từ danh sách skills dưới đây, chọn 14 skills phù hợp nhất để tạo skill tree cho user.

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
        Step 4: Build balanced tree structure:
        - 2 Abilities (level 1)
        - 2 Skills per Ability (level 2) = 4 total
        - 2 Knowledge per Skill (level 3) = 8 total
        Total: 1 root + 2 + 4 + 8 = 15 nodes
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
        
        # Group items by level
        abilities = []
        skills = []
        knowledge = []
        
        for item in selected_items:
            metadata = item.get("metadata") or {}
            node_type = metadata.get("node_type", "knowledge")
            
            if node_type == "ability":
                abilities.append(item)
            elif node_type == "skill":
                skills.append(item)
            else:  # knowledge
                knowledge.append(item)
        
        print(f"  📊 Distribution: {len(abilities)} abilities, {len(skills)} skills, {len(knowledge)} knowledge")
        
        # If not enough abilities/skills, we need to pad with available nodes
        if len(abilities) < 2 or len(skills) < 4:
            print(f"  ⚠️ WARNING: Not enough abilities ({len(abilities)}/2) or skills ({len(skills)}/4)")
            print(f"     Consider improving ChromaDB search to return diverse node types")
        
        # Build tree with 2-2-2 structure
        # Take first 2 abilities
        for i, item in enumerate(abilities[:2]):
            await self._add_node_to_tree(item, i, root_id, nodes, repo, "ability", 1)
        
        # Take first 4 skills (2 per ability)
        for i, item in enumerate(skills[:4]):
            # Determine parent: skill 0,1 -> ability 0; skill 2,3 -> ability 1
            ability_idx = 1 + (i // 2)  # nodes[1] or nodes[2]
            parent_id = nodes[ability_idx].id if ability_idx < len(nodes) else root_id
            await self._add_node_to_tree(item, i, parent_id, nodes, repo, "skill", 2)
        
        # Take first 8 knowledge (2 per skill)
        for i, item in enumerate(knowledge[:8]):
            # Determine parent: knowledge 0,1 -> skill 0; knowledge 2,3 -> skill 1, etc.
            skill_idx = 3 + (i // 2)  # nodes[3], nodes[4], nodes[5], nodes[6]
            parent_id = nodes[skill_idx].id if skill_idx < len(nodes) else root_id
            await self._add_node_to_tree(item, i, parent_id, nodes, repo, "knowledge", 3)
        
        print(f"🌳 [Step4] Built tree with {len(nodes)} nodes from PostgreSQL")
        return nodes
    
    async def _add_node_to_tree(
        self,
        item: dict,
        index: int,
        parent_id: str,
        nodes: List[TreeNodeResult],
        repo,
        expected_type: str,
        expected_level: int
    ):
        """Helper to add a node to the tree"""
        raw_id = item.get("id")
        metadata = item.get("metadata") or {}
        raw_name = metadata.get("name", item.get("document", "Unknown"))
        
        db_node = None
        try:
            if self.is_valid_uuid(raw_id):
                db_nodes_by_id = await repo.get_nodes_by_ids([raw_id])
                if db_nodes_by_id:
                    db_node = db_nodes_by_id[0]
            
            if not db_node:
                search_name = metadata.get("name") or raw_name
                if search_name and len(search_name) < 150:
                    db_nodes_by_name_search = await repo.search_nodes_by_name(search_name, limit=1)
                    if db_nodes_by_name_search:
                        db_node = db_nodes_by_name_search[0]
            
            if db_node:
                display_name = db_node.name[:50] + "..." if len(db_node.name) > 50 else db_node.name
                
                node_result = TreeNodeResult(
                    id=str(db_node.id),
                    name=display_name,
                    full_name=db_node.name,
                    description=db_node.description,
                    type=expected_type,
                    level=expected_level,
                    icon=db_node.icon,
                    parent_id=parent_id,
                    metadata={
                        "difficultyLevel": db_node.difficulty_level or "beginner",
                        "estimatedHours": db_node.estimated_hours or 5
                    },
                    original_node_id=str(db_node.id)
                )
                nodes.append(node_result)
                print(f"  ✅ Added {expected_type}: {db_node.name[:40]}")
            else:
                # Fallback
                display_name = metadata.get("name") or (raw_name[:50] + "..." if len(raw_name) > 50 else raw_name)
                full_node_name = metadata.get("name") or raw_name
                
                node_result = TreeNodeResult(
                    id=f"node-{expected_type}-{index}",
                    name=display_name,
                    full_name=full_node_name,
                    description=metadata.get("description", f"{expected_type}: {full_node_name}"),
                    type=expected_type,
                    level=expected_level,
                    icon=metadata.get("icon"),
                    parent_id=parent_id,
                    original_node_id=raw_id if self.is_valid_uuid(raw_id) else None
                )
                nodes.append(node_result)
                print(f"  ⚠️ Added {expected_type} (no DB): {display_name[:40]}")
        except Exception as e:
            print(f"  ❌ Error adding {expected_type} '{str(raw_name)[:30]}...': {e}")

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

    async def find_alternatives(self, current_level: int, query_context: str, node_name: str = "", existing_node_ids: List[str] = None) -> List[dict]:
        """
        Find alternative nodes for a given node based on context and level.
        Search ChromaDB using query_context, filter by node type corresponding to level.
        Excludes nodes that are already in the tree (existing_node_ids).
        """
        search_query = query_context
        if node_name:
            search_query = f"{query_context} related to {node_name}"
            
        print(f"🔄 Finding alternatives for level {current_level} with query: '{search_query}'")
        
        # Determine strict type based on level
        target_type = "skill"
        if current_level == 1: 
            target_type = "ability"
        elif current_level == 2: 
            target_type = "skill"
        elif current_level >= 3: 
            target_type = "knowledge"
        
        # Search ChromaDB with MORE results to increase chance of finding matching type
        candidates = self.chroma_util.search_with_metadata(
            [search_query], 
            n_results_per_query=50, 
            max_total=50,
            metadata_filter={"node_type": target_type}  # Use metadata filter for efficiency!
        )
        print(f"📊 ChromaDB returned {len(candidates)} candidates for query '{search_query}' (level={current_level}, target_type='{target_type}')")
        
        alternatives = []
        seen_names = set()
        existing_ids_set = set(existing_node_ids or [])
        
        if node_name:
            seen_names.add(node_name) # Don't suggest itself
        
        # STEP 1: Pre-fetch icons from DB for all candidates to avoid nulls
        candidate_ids = [c.get("id") for c in candidates if self.is_valid_uuid(c.get("id"))]
        db_icon_map = {}
        if candidate_ids:
            try:
                repo = get_skill_tree_repository()
                db_nodes = await repo.get_nodes_by_ids(candidate_ids)
                db_icon_map = {str(n.id): n.icon for n in db_nodes if n.icon}
            except Exception as e:
                print(f"⚠️ Error pre-fetching icons for alternatives: {e}")

        for idx, c in enumerate(candidates):
            meta = c.get("metadata", {})
            c_type = meta.get("node_type", "").lower() 
            c_id = c.get("id")
            c_name = meta.get("name", "")
            
            # Fetch icon from DB map if not in metadata
            c_icon = meta.get("icon") or db_icon_map.get(str(c_id))
            
            # Skip if already in tree
            if c_id in existing_ids_set:
                continue
                
            # Skip if duplicate name in results
            if c_name in seen_names:
                continue

            # Double check type (though filter should handle it)
            if c_type == target_type:
                # Calculate similarity score (1 - distance)
                # ChromaDB distance is usually cosine distance [0, 2] or Euclidean
                # Assuming cosine distance for SentenceTransformers
                dist = c.get("distance", 0.5)
                sim_score = max(0, min(1, 1 - dist))
                
                # Filter by threshold
                from config.settings import settings
                if sim_score < settings.SKILL_MATCH_THRESHOLD:
                    continue
                
                # Create node object
                alt_node = {
                    "id": c_id,
                    "name": c_name,
                    "description": meta.get("description", ""),
                    "type": c_type,
                    "level": current_level,
                    "icon": c_icon,
                    "similarity_score": sim_score,
                    "metadata": {
                        "difficultyLevel": meta.get("difficulty", "beginner")
                    }
                }
                
                # Auto-populate children for preview
                # This avoids N+1 requests from frontend
                print(f"  generating children for alternative: {c_name}")
                alt_node["children"] = await self.generate_descendants(alt_node)
                
                alternatives.append(alt_node)
                seen_names.add(c_name)
                
            if len(alternatives) >= 5:  # Limit to 5 alternatives
                break
                
        print(f"✅ Found {len(alternatives)} alternatives (with children populated)")
        return alternatives


    async def generate_descendants(self, parent_node: dict) -> List[dict]:
        """
        Generate descendant nodes for a newly swapped parent node.
        Optimized to use BATCH SEARCH for sub-levels.
        """
        parent_level = parent_node.get("level", 3)
        parent_name = parent_node.get("name", "")
        parent_id = parent_node.get("id")
        
        descendants = []
        
        # Determine strict type based on level
        if parent_level == 1: # Ability -> Find Skills (Level 2)
            search_query = f"Skills for {parent_name}"
            print(f"  🔄 Generating skills for ability: '{parent_name}'")
            
            skills = self.chroma_util.search_with_metadata(
                [search_query], n_results_per_query=5, max_total=5, metadata_filter={"node_type": "skill"}
            )
            
            # STEP 2: Pre-fetch icons for descendants
            skill_ids = [s.get("id") for s in skills if self.is_valid_uuid(s.get("id"))]
            db_icon_map = {}
            if skill_ids:
                try:
                    repo = get_skill_tree_repository()
                    db_nodes = await repo.get_nodes_by_ids(skill_ids)
                    db_icon_map = {str(n.id): n.icon for n in db_nodes if n.icon}
                except Exception as e:
                    print(f"⚠️ Error pre-fetching icons for skills: {e}")

            # Select 2 distinct skills
            selected_skills = []
            seen = set()
            for s in skills:
                name = s.get("metadata", {}).get("name", "")
                if name and name not in seen:
                    seen.add(name)
                    s_id = s.get("id")
                    s_icon = s.get("metadata", {}).get("icon") or db_icon_map.get(str(s_id))
                    
                    # Convert to TreeNode format
                    skill_node = {
                        "id": s_id,
                        "name": name,
                        "description": s.get("metadata", {}).get("description", ""),
                        "type": "skill",
                        "level": 2,
                        "parentId": parent_id,
                        "filled": True,
                        "icon": s_icon,
                        "metadata": s.get("metadata", {})
                    }
                    selected_skills.append(skill_node)
                    descendants.append(skill_node)
                    if len(selected_skills) >= 2: break
            
            # BATCH Generated Knowledge for all selected skills
            if selected_skills:
                print(f"  ⚡ Batch generating knowledge for {len(selected_skills)} skills...")
                knowledge_queries = [f"Knowledge for {skill['name']}" for skill in selected_skills]
                
                batch_results = self.chroma_util.batch_search(
                    knowledge_queries, 
                    n_results_per_query=5, 
                    metadata_filter={"node_type": "knowledge"}
                )
                
                # STEP 3: Pre-fetch icons for knowledge
                all_knowledge_ids = []
                for res in batch_results:
                    for k in res:
                        if self.is_valid_uuid(k.get("id")):
                            all_knowledge_ids.append(k.get("id"))
                
                db_k_icon_map = {}
                if all_knowledge_ids:
                    try:
                        repo = get_skill_tree_repository()
                        db_k_nodes = await repo.get_nodes_by_ids(all_knowledge_ids)
                        db_k_icon_map = {str(n.id): n.icon for n in db_k_nodes if n.icon}
                    except Exception as e:
                        print(f"⚠️ Error pre-fetching icons for knowledge: {e}")

                # Process results for each skill
                for i, skill in enumerate(selected_skills):
                    knowledges = batch_results[i]
                    seen_k = set()
                    count_k = 0
                    
                    for k in knowledges:
                        k_name = k.get("metadata", {}).get("name", "")
                        if k_name and k_name not in seen_k:
                            seen_k.add(k_name)
                            k_id = k.get("id")
                            k_icon = k.get("metadata", {}).get("icon") or db_k_icon_map.get(str(k_id))
                            
                            k_node = {
                                "id": k_id,
                                "name": k_name,
                                "description": k.get("metadata", {}).get("description", ""),
                                "type": "knowledge",
                                "level": 3,
                                "parentId": skill["id"], # Parent is the Skill
                                "filled": True,
                                "icon": k_icon,
                                "metadata": k.get("metadata", {})
                            }
                            descendants.append(k_node)
                            count_k += 1
                            if count_k >= 2: break

        elif parent_level == 2: # Skill -> Find Knowledge (Level 3)
            # Find Knowledge for single skill (still use search, no batch needed for 1)
            search_query = f"Knowledge for {parent_name}"
            print(f"  🔄 Generating knowledge for skill: '{parent_name}'")
            
            knowledges = self.chroma_util.search_with_metadata(
                [search_query], n_results_per_query=5, max_total=5, metadata_filter={"node_type": "knowledge"}
            )
            
            # STEP 4: Pre-fetch icons for knowledge (single skill case)
            k_ids = [k.get("id") for k in knowledges if self.is_valid_uuid(k.get("id"))]
            db_k_icon_map = {}
            if k_ids:
                try:
                    repo = get_skill_tree_repository()
                    db_k_nodes = await repo.get_nodes_by_ids(k_ids)
                    db_k_icon_map = {str(n.id): n.icon for n in db_k_nodes if n.icon}
                except Exception as e:
                    print(f"⚠️ Error pre-fetching icons for knowledge (single): {e}")

            seen = set()
            count = 0
            for k in knowledges:
                name = k.get("metadata", {}).get("name", "")
                if name and name not in seen:
                    seen.add(name)
                    k_id = k.get("id")
                    k_icon = k.get("metadata", {}).get("icon") or db_k_icon_map.get(str(k_id))
                    
                    k_node = {
                        "id": k_id,
                        "name": name,
                        "description": k.get("metadata", {}).get("description", ""),
                        "type": "knowledge",
                        "level": 3,
                        "parentId": parent_id,
                        "filled": True,
                        "icon": k_icon,
                        "metadata": k.get("metadata", {})
                    }
                    descendants.append(k_node)
                    count += 1
                    if count >= 2: break
                    
        return descendants


# Singleton instance
_skill_tree_service: Optional[SkillTreeQueryService] = None


def get_skill_tree_query_service() -> SkillTreeQueryService:
    """Get or create singleton SkillTreeQueryService"""
    global _skill_tree_service
    if _skill_tree_service is None:
        _skill_tree_service = SkillTreeQueryService()
    return _skill_tree_service
