# Shared Vector Store Adapter
# Implements VectorStorePort using ChromaDB

from typing import List
import chromadb

from modules.chat.domain.ports import VectorStorePort
from config.settings import settings


class ChromaAdapter(VectorStorePort):
    """ChromaDB adapter implementing VectorStorePort"""
    
    def __init__(self):
        # Load config from centralized settings
        db_path = settings.CHROMA_DB_PATH
        collection_name = settings.CHROMA_COLLECTION
        
        # Load embedding model
        self.embedder = self._load_embedder()
        
        # Connect to ChromaDB
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
    
    def _load_embedder(self):
        """Load SentenceTransformer embedding model"""
        import torch
        from sentence_transformers import SentenceTransformer
        
        model_name = settings.EMBEDDING_MODEL
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        print(f"Loading embedding model: {model_name} (device: {device})")
        model = SentenceTransformer(model_name, device=device)
        print("✅ Embedding model loaded")
        
        return model
    
    def search(self, query: str, n_results: int = 3) -> List[str]:
        """Search for similar documents using vector similarity"""
        try:
            # Encode query to vector
            query_vector = self.embedder.encode(query).tolist()
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=n_results
            )
            
            return results['documents'][0] if results['documents'] else []
        
        except Exception as e:
            print(f"Error searching: {e}")
            return []
    
    def search_with_metadata(self, query: str, n_results: int = 5) -> List[dict]:
        """
        Search for similar documents and return with IDs and metadata.
        Returns list of dicts with: id, document, distance
        """
        try:
            # Encode query to vector
            query_vector = self.embedder.encode(query).tolist()
            
            # Query ChromaDB with include
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results['ids'] or not results['ids'][0]:
                return []
            
            items = []
            for i, doc_id in enumerate(results['ids'][0]):
                items.append({
                    "id": doc_id,
                    "document": results['documents'][0][i] if results['documents'] else "",
                    "metadata": results['metadatas'][0][i] if results.get('metadatas') else {},
                    "distance": results['distances'][0][i] if results.get('distances') else 0
                })
            
            return items
        
        except Exception as e:
            print(f"Error searching with metadata: {e}")
            return []
    
    def add_documents(self, documents: List[str], ids: List[str]) -> None:
        """Add documents to vector store"""
        try:
            # Encode all documents
            embeddings = self.embedder.encode(documents).tolist()
            
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
