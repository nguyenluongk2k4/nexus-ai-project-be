# ChromaDB Search Utility
# Shared utility for searching ChromaDB, can be used by any service

from typing import List, Optional
from modules.chat.providers import get_vector_store


class ChromaSearchUtil:
    """
    Utility class for ChromaDB searches.
    Singleton pattern - reuses the already loaded vector store.
    """
    
    _instance: Optional['ChromaSearchUtil'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.vector_store = get_vector_store()
        self._initialized = True
        print("✅ ChromaSearchUtil initialized")
    
    def search(self, query: str, n_results: int = 5) -> List[str]:
        """
        Search ChromaDB for documents matching query.
        
        Args:
            query: Search query string
            n_results: Number of results to return (default 5)
            
        Returns:
            List of matching document strings
        """
        try:
            documents = self.vector_store.search(query, n_results=n_results)
            return documents if documents else []
        except Exception as e:
            print(f"ChromaDB search error for '{query}': {e}")
            return []
    
    def search_with_metadata(self, queries: List[str], n_results_per_query: int = 5, max_total: int = 15) -> List[dict]:
        """
        Search with multiple queries and return documents with metadata (IDs).
        """
        all_items = []
        for query in queries:
            # Call adapter's search_with_metadata
            items = self.vector_store.search_with_metadata(query, n_results=n_results_per_query)
            all_items.extend(items)
            
        # Deduplicate
        seen = set()
        unique_items = []
        for item in all_items:
            doc_id = item.get('id')
            if doc_id and doc_id not in seen:
                seen.add(doc_id)
                unique_items.append(item)
                
        return unique_items[:max_total]


# Singleton getter
_chroma_util: Optional[ChromaSearchUtil] = None

def get_chroma_search_util() -> ChromaSearchUtil:
    """Get or create singleton ChromaSearchUtil"""
    global _chroma_util
    if _chroma_util is None:
        _chroma_util = ChromaSearchUtil()
    return _chroma_util
