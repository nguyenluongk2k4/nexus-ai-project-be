# Infrastructure - Embedding Adapter
# Implements EmbeddingPort using SentenceTransformer

from typing import List
import torch
from sentence_transformers import SentenceTransformer

from domain.ports import EmbeddingPort


class SentenceTransformerAdapter(EmbeddingPort):
    """
    SentenceTransformer adapter implementing EmbeddingPort
    """
    
    DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    
    def __init__(self, model_name: str = None):
        model_name = model_name or self.DEFAULT_MODEL
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        print(f"Loading embedding model: {model_name} (device: {device})")
        self.model = SentenceTransformer(model_name, device=device)
        print("✅ Embedding model loaded")
    
    def encode(self, text: str) -> List[float]:
        """Encode single text to vector"""
        return self.model.encode(text).tolist()
    
    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """Encode multiple texts to vectors"""
        embeddings = self.model.encode(texts)
        return [emb.tolist() for emb in embeddings]
