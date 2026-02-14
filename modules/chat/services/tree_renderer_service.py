# Chat Module - Tree Renderer Service
# Renders skill tree based on user intent and RAG results

import logging
from typing import List, Dict, Optional
from uuid import UUID
from modules.skill_tree.infrastructure.repository import SkillTreeRepository

logger = logging.getLogger(__name__)


class TreeRenderService:
    """
    Service to render skill tree structures based on user intent and documents
    
    - Loads skill tree templates from database
    - Filters nodes based on user intent
    - Attaches learning resources from RAG results
    - Builds tree structure for frontend
    """
    
    def __init__(self, repo: Optional[SkillTreeRepository] = None):
        """
        Initialize service with skill tree repository
        
        Args:
            repo: SkillTreeRepository instance (creates new if None)
        """
        self.repo = repo or SkillTreeRepository()
    
    async def render_tree(
        self,
        intent: str,
        documents: List[Dict],
        user_id: Optional[UUID] = None,
        max_nodes: int = 20
    ) -> Dict:
        """
        Render skill tree based on intent and documents
        
        Args:
            intent: User intent (learning_path, find_job, practice, resource, general)
            documents: RAG results with learning content
            user_id: User ID for personalization (optional)
            max_nodes: Maximum nodes to include in tree
        
        Returns:
            {
                "id": "root",
                "name": "Learning Path Title",
                "description": "Tree description",
                "nodes": [
                    {
                        "id": "node1",
                        "label": "Skill Name",
                        "type": "skill",
                        "level": 1,
                        "icon": "📚",
                        "status": "not_started",
                        "resources": [...],
                        "parentId": null,
                        "children": ["node2", "node3"]
                    },
                    ...
                ],
                "edges": []
            }
        """
        try:
            logger.info(f"🌳 Rendering tree for intent: {intent}")
            
            # Step 1: Get default template based on intent
            template_tree = await self._get_template_tree(intent)
            
            # Step 2: Filter nodes based on documents and intent
            filtered_nodes = self._filter_nodes(template_tree.get("nodes", []), documents, intent)
            
            # Step 3: Attach resources from RAG results
            enriched_nodes = self._attach_resources(filtered_nodes, documents)
            
            # Step 4: Build tree structure
            tree = self._build_tree_structure(enriched_nodes, intent)
            
            logger.info(f"✅ Tree rendered with {len(tree.get('nodes', []))} nodes")
            return tree
        
        except Exception as e:
            logger.error(f"❌ Tree rendering failed: {e}", exc_info=True)
            # Return default tree on error
            return self._default_tree(intent)
    
    async def _get_template_tree(self, intent: str) -> Dict:
        """Get template tree based on intent"""
        try:
            # Template mapping based on intent
            intent_templates = {
                "learning_path": "Python Learning Path",
                "find_job": "Job Search Roadmap",
                "practice": "Practice Exercises",
                "resource": "Learning Resources",
                "general": "General Skills"
            }
            
            template_name = intent_templates.get(intent, "General Skills")
            
            # Search for template (in real DB, would query by name/category)
            # For now, return default structure
            return self._default_tree(intent)
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to get template: {e}")
            return self._default_tree(intent)
    
    def _filter_nodes(self, nodes: List[Dict], documents: List[Dict], intent: str) -> List[Dict]:
        """
        Filter nodes based on documents and intent
        Keep only nodes relevant to the documents and intent
        """
        if not nodes:
            return []
        
        # Extract keywords from documents
        doc_keywords = self._extract_doc_keywords(documents)
        
        # Filter nodes that match keywords or intent
        filtered = []
        for node in nodes:
            node_text = f"{node.get('label', '')} {node.get('description', '')}".lower()
            
            # Keep if matches keywords or is foundational
            if any(kw.lower() in node_text for kw in doc_keywords) or node.get("level", 1) <= 2:
                filtered.append(node)
        
        # Limit to reasonable size
        return filtered[:20]
    
    def _attach_resources(self, nodes: List[Dict], documents: List[Dict]) -> List[Dict]:
        """Attach learning resources from RAG results to nodes"""
        enriched = []
        
        for i, node in enumerate(nodes):
            # Select documents for this node
            node_resources = []
            
            # For first few nodes, attach documents
            if i < len(documents) and documents:
                node_resources = [
                    {
                        "id": f"resource_{i}_{j}",
                        "title": doc.get("metadata", {}).get("title", f"Resource {j}"),
                        "url": doc.get("metadata", {}).get("url"),
                        "type": doc.get("metadata", {}).get("type", "article"),
                        "score": doc.get("score", 0.8)
                    }
                    for j, doc in enumerate(documents[max(0, i*2):(i+1)*2])
                ]
            
            # Attach resources to node
            node["resources"] = node_resources
            enriched.append(node)
        
        return enriched
    
    def _build_tree_structure(self, nodes: List[Dict], intent: str) -> Dict:
        """Build final tree structure for frontend"""
        if not nodes:
            return self._default_tree(intent)
        
        # Build edges based on hierarchy
        edges = []
        root_node = nodes[0] if nodes else None
        
        if root_node:
            # Build parent-child relationships
            for i in range(1, len(nodes)):
                parent_idx = max(0, i - 1)
                edges.append({
                    "id": f"e{parent_idx}_{i}",
                    "source": nodes[parent_idx].get("id"),
                    "target": nodes[i].get("id"),
                    "animated": True
                })
        
        # Build tree structure
        tree = {
            "id": "root",
            "name": self._get_tree_title(intent),
            "description": f"Skill tree for {intent} learning",
            "intent": intent,
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "generated_at": logging.getLogger().debug("tree generated"),
                "intent": intent
            }
        }
        
        return tree
    
    def _extract_doc_keywords(self, documents: List[Dict]) -> List[str]:
        """Extract keywords from documents"""
        keywords = set()
        
        for doc in documents:
            # Extract from content
            content = doc.get("content", "")
            # Simple word extraction
            words = content.split()[:10]  # First 10 words
            keywords.update(w.lower() for w in words if len(w) > 3)
        
        return list(keywords)[:10]
    
    def _get_tree_title(self, intent: str) -> str:
        """Get tree title based on intent"""
        titles = {
            "learning_path": "Learning Path",
            "find_job": "Career Roadmap",
            "practice": "Practice Exercises",
            "resource": "Learning Resources",
            "general": "Skill Development"
        }
        return titles.get(intent, "Learning Path")
    
    def _default_tree(self, intent: str = "general") -> Dict:
        """Return default tree structure"""
        return {
            "id": "root",
            "name": self._get_tree_title(intent),
            "description": f"Skill tree for {intent} learning",
            "intent": intent,
            "nodes": [
                {
                    "id": "node_1",
                    "label": "Foundations",
                    "type": "skill",
                    "level": 1,
                    "icon": "📚",
                    "status": "not_started",
                    "description": "Core fundamentals",
                    "resources": [],
                    "parentId": None,
                    "children": ["node_2", "node_3"]
                },
                {
                    "id": "node_2",
                    "label": "Intermediate Skills",
                    "type": "skill",
                    "level": 2,
                    "icon": "🎯",
                    "status": "not_started",
                    "description": "Build on foundations",
                    "resources": [],
                    "parentId": "node_1",
                    "children": []
                },
                {
                    "id": "node_3",
                    "label": "Advanced Topics",
                    "type": "skill",
                    "level": 2,
                    "icon": "🚀",
                    "status": "not_started",
                    "description": "Expert-level skills",
                    "resources": [],
                    "parentId": "node_1",
                    "children": []
                }
            ],
            "edges": [
                {
                    "id": "e1_2",
                    "source": "node_1",
                    "target": "node_2",
                    "animated": True
                },
                {
                    "id": "e1_3",
                    "source": "node_1",
                    "target": "node_3",
                    "animated": True
                }
            ],
            "metadata": {
                "total_nodes": 3,
                "intent": intent
            }
        }
