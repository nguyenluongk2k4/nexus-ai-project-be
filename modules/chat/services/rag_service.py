# Chat Module - RAG Service
# Queries ChromaDB for relevant documents based on user message

import logging
from typing import List, Dict, Optional
from shared.vector_store.chroma_adapter import ChromaAdapter

logger = logging.getLogger(__name__)


class RAGService:
    """
    Service to query RAG system (ChromaDB) for relevant documents
    
    Searches vector store for documents relevant to user query
    and returns formatted results with metadata
    """
    
    def __init__(self, vector_store: Optional[ChromaAdapter] = None):
        """
        Initialize service with vector store adapter
        
        Args:
            vector_store: ChromaAdapter instance (creates new if None)
        """
        self.vector_store = vector_store or ChromaAdapter()
    
    async def query_documents(
        self,
        query: str,
        n_results: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Query documents from vector store
        
        Args:
            query: Search query string
            n_results: Number of results to return (default: 5)
            filters: Optional metadata filters
        
        Returns:
            List of document results, each containing:
            {
                "id": "doc_id",
                "content": "document content",
                "score": 0.92,  # Relevance score
                "metadata": {...}
            }
        """
        try:
            logger.info(f"📚 Querying RAG: {query[:100]}")
            
            # Query vector store
            results = self.vector_store.search_with_metadata(
                query=query,
                n_results=n_results,
                where=filters
            )
            
            # Format results
            formatted = self._format_results(results)
            
            logger.info(f"✅ Found {len(formatted)} documents")
            return formatted
        
        except Exception as e:
            logger.error(f"❌ RAG query failed: {e}", exc_info=True)
            return []
    
    async def batch_query_documents(
        self,
        queries: List[str],
        n_results: int = 5
    ) -> List[List[Dict]]:
        """
        Query multiple queries in batch
        
        Args:
            queries: List of query strings
            n_results: Results per query
        
        Returns:
            List of result lists, one for each query
        """
        try:
            logger.info(f"📚 Batch querying {len(queries)} queries")
            
            # Query vector store with batch
            batch_results = self.vector_store.batch_search_with_metadata(
                queries=queries,
                n_results=n_results
            )
            
            # Format each batch result
            formatted_batch = [self._format_results(r) for r in batch_results]
            
            logger.info(f"✅ Batch query complete")
            return formatted_batch
        
        except Exception as e:
            logger.error(f"❌ Batch query failed: {e}", exc_info=True)
            return [[] for _ in queries]
    
    def _format_results(self, raw_results: List[Dict]) -> List[Dict]:
        """Format raw ChromaDB results into standard format"""
        formatted = []
        
        for result in raw_results:
            formatted.append({
                "id": result.get("id", ""),
                "content": result.get("document", ""),
                "score": 1 - result.get("distance", 0),  # Convert distance to similarity score
                "metadata": result.get("metadata", {}),
                "source": result.get("metadata", {}).get("source", "unknown")
            })
        
        # Sort by relevance score (descending)
        formatted.sort(key=lambda x: x["score"], reverse=True)
        
        return formatted
    
    async def rank_results(
        self,
        results: List[Dict],
        query: str,
        top_k: int = 3
    ) -> List[Dict]:
        """
        Re-rank results by relevance
        
        Args:
            results: Initial search results
            query: Original query for re-ranking context
            top_k: Number of top results to keep
        
        Returns:
            Top K re-ranked results
        """
        # Sort by score and return top K
        ranked = sorted(results, key=lambda x: x["score"], reverse=True)
        return ranked[:top_k]
