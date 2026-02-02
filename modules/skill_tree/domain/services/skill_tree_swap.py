from uuid import UUID
from typing import List, Dict, Any, Optional
from modules.chat.domain.ports import ChatRepositoryPort
from modules.chat.infrastructure.repository import ChatRepositoryImpl

class SkillTreeSwapService:
    def __init__(self, chat_repo: ChatRepositoryPort):
        self.chat_repo = chat_repo

    async def swap_node(self, session_id: UUID, old_node_id: str, new_node_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Swap a node in the skill tree stored in chat session context.
        Returns the updated tree nodes or None if failure.
        """
        session = await self.chat_repo.get_session(session_id)
        if not session or not session.context_data:
            print(f"❌ Session {session_id} not found or no context data")
            return None
            
        context = session.context_data
        # Expecting structure: {"skill_tree": [...]} or just [...]
        nodes = []
        is_dict_wrapper = False
        
        if isinstance(context, dict):
            # Check for 'tree_nodes' (used by generate) first, then 'skill_tree'
            nodes = context.get("tree_nodes") or context.get("skill_tree", [])
            # Track which key to update
            target_key = "tree_nodes" if "tree_nodes" in context else "skill_tree"
            if not nodes and "tree_nodes" not in context and "skill_tree" not in context:
                 # Empty context but dict type, default to tree_nodes
                 target_key = "tree_nodes"
            is_dict_wrapper = True
        elif isinstance(context, list):
            nodes = context
        
        if not nodes:
            print(f"⚠️ No nodes found in session context")
            return None

        # Find target node index
        target_idx = -1
        old_node = None
        for i, n in enumerate(nodes):
            if str(n.get("id")) == str(old_node_id):
                target_idx = i
                old_node = n
                break
        
        if target_idx == -1:
            print(f"⚠️ Old node {old_node_id} not found in tree")
            return None
            
        print(f"🔄 Swapping node: {old_node.get('name')} -> {new_node_data.get('name')}")

        # Construct Swapped Node
        # Keep structural info from old_node (parent_id, level) to maintain tree structure
        # Note: parentId vs parent_id differences
        parent_id_key = "parentId" if "parentId" in old_node else "parent_id"
        
        swapped_node = old_node.copy()
        swapped_node["id"] = new_node_data.get("id")
        swapped_node["name"] = new_node_data.get("name")
        swapped_node["full_name"] = new_node_data.get("name") 
        swapped_node["description"] = new_node_data.get("description")
        swapped_node["icon"] = new_node_data.get("icon", old_node.get("icon"))
        
        # Respect new type if provided
        swapped_node["type"] = new_node_data.get("type", old_node.get("type"))
        
        # Metadata merge
        new_meta = new_node_data.get("metadata", {}) or {}
        old_meta = old_node.get("metadata", {}) or {}
        merged_meta = {**old_meta, **new_meta}
        swapped_node["metadata"] = merged_meta
        
        # Ensure parent linkage is preserved under the correct key
        swapped_node[parent_id_key] = old_node.get(parent_id_key)

        # Replace in list
        nodes[target_idx] = swapped_node
        
        # Handle Children: Remove invalid descendants
        descendants = self._get_descendants(nodes, old_node_id)
        if descendants:
            print(f"✂️ Removing {len(descendants)} invalid descendants")
            remove_ids = set(n["id"] for n in descendants)
            nodes = [n for n in nodes if n["id"] not in remove_ids]
        
        # Auto-generate sub-tree for Ability/Skill nodes using ChromaDB search
        if swapped_node.get("level", 0) < 3:
            try:
                from modules.skill_tree.domain.services.skill_tree_query import get_skill_tree_query_service
                query_service = get_skill_tree_query_service()
                
                print(f"🤖 Auto-generating sub-tree for {swapped_node['name']} (level {swapped_node.get('level')})...")
                
                # Use the new generate_descendants method
                new_children = await query_service.generate_descendants(swapped_node)
                
                if new_children:
                    # Safety check: Ensure no ID collisions
                    existing_ids = set(n["id"] for n in nodes)
                    
                    for child in new_children:
                        # If ID collision, generate new UUID
                        if child["id"] in existing_ids:
                            from uuid import uuid4
                            new_id = str(uuid4())
                            # Update parent pointers of its children if any?
                            # Our generate_descendants is recursive but returns flat list.
                            # So if we change child ID, we must update its children's parentId.
                            
                            original_id = child["id"]
                            child["id"] = new_id
                            
                            # Update descendants pointing to this child
                            for sub_child in new_children:
                                if sub_child["parentId"] == original_id:
                                    sub_child["parentId"] = new_id
                                    
                            print(f"⚠️ Collision fix: {original_id} -> {new_id}")
                            
                        existing_ids.add(child["id"])
                    
                    nodes.extend(new_children)
                    print(f"✅ Added {len(new_children)} new descendants")
                    
            except Exception as e:
                print(f"⚠️ Failed to auto-generate children: {e}")
                import traceback
                traceback.print_exc()
        
        
        # Prepare update payload
        if is_dict_wrapper:
            context[target_key] = nodes
            update_payload = context
        else:
            update_payload = {"tree_nodes": nodes} # Standardize
            
        success = await self.chat_repo.update_session_context(session_id, update_payload)
        
        if success:
            return nodes
        return None

    def _get_descendants(self, nodes: List[Dict], parent_id: str) -> List[Dict]:
        """Recursively find all descendants of a node"""
        direct_children = []
        for n in nodes:
            # Check both keys commonly used
            pid = n.get("parentId") or n.get("parent_id")
            if pid and str(pid) == str(parent_id):
                direct_children.append(n)
                
        descendants = []
        for child in direct_children:
            descendants.append(child)
            descendants.extend(self._get_descendants(nodes, child.get("id")))
        return descendants

# Singleton Factory
_swap_service: Optional[SkillTreeSwapService] = None

def get_skill_tree_swap_service() -> SkillTreeSwapService:
    global _swap_service
    if _swap_service is None:
        repo = ChatRepositoryImpl()
        _swap_service = SkillTreeSwapService(repo)
    return _swap_service
