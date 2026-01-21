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
        collection_name = settings.CHROMA_COLLECTION
        
        # Load embedding model
        self.embedder = self._load_embedder()
        
        # Connect to ChromaDB based on mode
        if settings.CHROMA_MODE == "server":
            print(f"🔗 Connecting to ChromaDB server at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
            self.client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT
            )
            print(f"✅ Connected to ChromaDB server")
        else:
            # Embedded mode (default)
            db_path = settings.CHROMA_DB_PATH
            print(f"💾 Using ChromaDB embedded mode at {db_path}")
            self.client = chromadb.PersistentClient(path=db_path)
            print(f"✅ ChromaDB embedded client ready")
        
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
    
    def search_with_metadata(self, query: str, n_results: int = 5, where: dict = None) -> List[dict]:
        """
        Search for similar documents and return with IDs and metadata.
        Returns list of dicts with: id, document, distance, metadata
        """
        try:
            # Encode query to vector
            query_vector = self.embedder.encode(query).tolist()
            
            # Query ChromaDB with include and optional where filter
            query_params = {
                "query_embeddings": [query_vector],
                "n_results": n_results,
                "include": ["documents", "metadatas", "distances"]
            }
            
            if where:
                query_params["where"] = where
            
            results = self.collection.query(**query_params)
            
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
    
    def batch_search_with_metadata(
        self, 
        queries: List[str], 
        n_results: int = 5, 
        where: dict = None
    ) -> List[List[dict]]:
        """
        Batch search for multiple queries.
        Returns a list of result lists, corresponding to each query.
        """
        try:
            if not queries:
                return []
                
            # Encode all queries at once
            query_vectors = self.embedder.encode(queries).tolist()
            
            # Query ChromaDB
            query_params = {
                "query_embeddings": query_vectors,
                "n_results": n_results,
                "include": ["documents", "metadatas", "distances"]
            }
            if where:
                query_params["where"] = where
                
            results = self.collection.query(**query_params)
            
            # Parse results
            # results['ids'] is List[List[str]]
            batch_output = []
            
            for q_idx in range(len(queries)):
                query_items = []
                if results['ids'] and len(results['ids']) > q_idx:
                    ids = results['ids'][q_idx]
                    # 'embeddings' is not included in the 'include' list, so it won't be in results.
                    # embeddings = results['embeddings'][q_idx] if 'embeddings' in results and results['embeddings'] else []
                    documents = results['documents'][q_idx] if 'documents' in results and results['documents'] else []
                    metadatas = results['metadatas'][q_idx] if 'metadatas' in results and results['metadatas'] else []
                    distances = results['distances'][q_idx] if 'distances' in results and results['distances'] else []
                    
                    for i, doc_id in enumerate(ids):
                        query_items.append({
                            "id": doc_id,
                            "document": documents[i] if i < len(documents) else "",
                            "metadata": metadatas[i] if i < len(metadatas) else {},
                            "distance": distances[i] if i < len(distances) else 0
                        })
                batch_output.append(query_items)
                
            return batch_output
            
        except Exception as e:
            print(f"Error in batch search: {e}")
            import traceback
            traceback.print_exc()
            return [[] for _ in queries]
    
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
