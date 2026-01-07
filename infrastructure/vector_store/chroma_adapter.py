# Infrastructure - Vector Store Adapter
# Implements VectorStorePort using ChromaDB

from typing import List
import chromadb
from chromadb.config import Settings

from domain.ports import VectorStorePort, EmbeddingPort


class ChromaAdapter(VectorStorePort):
    """
    ChromaDB adapter implementing VectorStorePort
    """
    
    def __init__(
        self, 
        db_path: str, 
        collection_name: str,
        embedder: EmbeddingPort
    ):
        self.embedder = embedder
        self.client = chromadb.PersistentClient(path=db_path)
        
        try:
            self.collection = self.client.get_collection(name=collection_name)
            print(f"✅ Connected to collection: '{collection_name}' ({self.collection.count()} documents)")
        except Exception as e:
            print(f"❌ Collection '{collection_name}' not found. Creating new one.")
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
    
    def search(self, query: str, n_results: int = 3) -> List[str]:
        """Search for similar documents using vector similarity"""
        try:
            # Encode query to vector
            query_vector = self.embedder.encode(query)
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=n_results
            )
            
            return results['documents'][0] if results['documents'] else []
        
        except Exception as e:
            print(f"Error searching: {e}")
            return []
    
    def add_documents(self, documents: List[str], ids: List[str]) -> None:
        """Add documents to vector store"""
        try:
            # Encode all documents
            embeddings = self.embedder.encode_batch(documents)
            
            # Add to collection
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                ids=ids
            )
            print(f"✅ Added {len(documents)} documents")
        
        except Exception as e:
            print(f"Error adding documents: {e}")
            raise
