from modules.skill_tree.domain.ports import SkillTreePort
from uuid import UUID

class GetSessionSkillTreeUseCase:
    def __init__(self, repository: SkillTreePort, chat_repo=None):
        self.repository = repository
        self.chat_repo = chat_repo

    async def execute(self, session_id: str, user_id: UUID) -> dict:
        # Step 1: Check if session has generated tree in context_data
        if self.chat_repo and session_id:
            try:
                session = await self.chat_repo.get_session(UUID(session_id))
                if session and session.context_data:
                    tree_nodes = session.context_data.get("tree_nodes")
                    if tree_nodes:
                        # Return tree from session context (generated via chat)
                        # Convert flat nodes list to tree format expected by frontend
                        return {
                            "id": session_id,
                            "name": "Generated Tree",
                            "nodes": [
                                {
                                    "id": node.get("id"),
                                    "label": node.get("name"),
                                    "type": node.get("type", "skill"),
                                    "level": node.get("level", 1),
                                    "data": {
                                        "description": node.get("description"),
                                        "status": "not_started"
                                    },
                                    "position": {"x": 0, "y": 0}
                                }
                                for node in tree_nodes
                            ],
                            "edges": self._build_edges(tree_nodes)
                        }
            except Exception as e:
                print(f"⚠️ Could not load session tree: {e}")
        
        # Step 2: Fallback to default template tree
        tree_data = await self.repository.get_user_tree(user_id)
        if not tree_data:
            return {}
            
        return tree_data

    def _build_edges(self, nodes: list) -> list:
        """Build edges from parentId relationships"""
        edges = []
        for node in nodes:
            parent_id = node.get("parentId")
            if parent_id:
                edges.append({
                    "id": f"e{parent_id}-{node['id']}",
                    "source": parent_id,
                    "target": node["id"],
                    "animated": True
                })
        return edges
