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
                        # OPTIMIZATION: If icons are null but we have original_node_id, try to fetch icons
                        # This 'heals' old session data that was generated without icons
                        nodes_with_orig = [n for n in tree_nodes if not n.get("icon") and n.get("original_node_id")]
                        icon_map = {}
                        if nodes_with_orig:
                            try:
                                from modules.skill_tree.infrastructure.repository import get_skill_tree_repository
                                repo = get_skill_tree_repository()
                                orig_ids = [n.get("original_node_id") for n in nodes_with_orig]
                                db_nodes = await repo.get_nodes_by_ids(orig_ids)
                                icon_map = {str(db_n.id): db_n.icon for db_n in db_nodes if db_n.icon}
                            except Exception as e:
                                print(f"⚠️ Error auto-healing icons: {e}")

                        return {
                            "id": session_id,
                            "name": "Generated Tree",
                            "nodes": [
                                {
                                    "id": node.get("id"),
                                    "label": node.get("name"),
                                    "type": node.get("type", "skill"),
                                    "level": node.get("level", 1),
                                    "icon": node.get("icon") or icon_map.get(str(node.get("original_node_id"))),
                                    "original_node_id": node.get("original_node_id"),
                                    "data": {
                                        "description": node.get("description"),
                                        "status": "not_started",
                                        "metadata": node.get("metadata", {})
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
