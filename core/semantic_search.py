"""
Vector database and semantic search engine for AgentricAI.
Provides embedding-based retrieval for conversations and documents.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import numpy as np
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import faiss
except ImportError:
    faiss = None

from core.config import get_config


class EmbeddingService:
    """Service for generating and managing embeddings."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize embedding service."""
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers not installed")
        
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
    
    def embed_text(self, text: str) -> np.ndarray:
        """Convert text to embedding vector."""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Convert multiple texts to embeddings."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.astype(np.float32)


class VectorStore:
    """FAISS-based vector store for similarity search."""
    
    def __init__(self, embedding_dim: int = 384, db_path: Optional[str] = None):
        """Initialize vector store."""
        if faiss is None:
            raise RuntimeError("faiss not installed")
        
        self.embedding_dim = embedding_dim
        self.db_path = db_path or Path(__file__).parent.parent / "vector_store.db"
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.metadata: List[Dict[str, Any]] = []
        
        self._load()
    
    def add_vector(self, vector: np.ndarray, metadata: Dict[str, Any]) -> int:
        """Add a single vector with metadata."""
        vector = vector.reshape(1, -1).astype(np.float32)
        self.index.add(vector)
        
        item_id = len(self.metadata)
        metadata["id"] = item_id
        metadata["added_at"] = datetime.utcnow().isoformat()
        self.metadata.append(metadata)
        
        self._save()
        return item_id
    
    def add_vectors(self, vectors: np.ndarray, metadatas: List[Dict[str, Any]]) -> List[int]:
        """Add multiple vectors with metadata."""
        vectors = vectors.astype(np.float32)
        self.index.add(vectors)
        
        ids = []
        for i, metadata in enumerate(metadatas):
            item_id = len(self.metadata)
            metadata["id"] = item_id
            metadata["added_at"] = datetime.utcnow().isoformat()
            self.metadata.append(metadata)
            ids.append(item_id)
        
        self._save()
        return ids
    
    def search(self, query_vector: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        query_vector = query_vector.reshape(1, -1).astype(np.float32)
        distances, indices = self.index.search(query_vector, min(k, len(self.metadata)))
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx >= 0 and idx < len(self.metadata):
                result = self.metadata[idx].copy()
                result["distance"] = float(distance)
                results.append(result)
        
        return results
    
    def _save(self):
        """Save vector store to disk."""
        faiss.write_index(self.index, str(self.db_path) + ".index")
        
        with open(str(self.db_path) + ".json", "w") as f:
            json.dump(self.metadata, f)
    
    def _load(self):
        """Load vector store from disk if exists."""
        index_path = str(self.db_path) + ".index"
        metadata_path = str(self.db_path) + ".json"
        
        if Path(index_path).exists():
            self.index = faiss.read_index(index_path)
        
        if Path(metadata_path).exists():
            with open(metadata_path, "r") as f:
                self.metadata = json.load(f)


class SemanticSearchEngine:
    """High-level semantic search engine."""
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        """Initialize semantic search engine."""
        self.embeddings = EmbeddingService(embedding_model)
        self.vector_store = VectorStore(self.embeddings.embedding_dim)
    
    async def index_conversation(
        self,
        resource: str,
        thread: str,
        messages: List[Dict[str, str]]
    ) -> int:
        """Index conversation messages for semantic search."""
        vectors = []
        metadatas = []
        
        for i, message in enumerate(messages):
            if message.get("content"):
                vector = self.embeddings.embed_text(message["content"])
                vectors.append(vector)
                
                metadatas.append({
                    "resource": resource,
                    "thread": thread,
                    "message_index": i,
                    "role": message.get("role", "unknown"),
                    "content_preview": message["content"][:100],
                    "content": message["content"],
                    "timestamp": message.get("timestamp", datetime.utcnow().isoformat())
                })
        
        if vectors:
            vectors_array = np.array(vectors)
            self.vector_store.add_vectors(vectors_array, metadatas)
        
        return len(metadatas)
    
    async def semantic_search(
        self,
        query: str,
        resource: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for semantically similar content."""
        query_vector = self.embeddings.embed_text(query)
        results = self.vector_store.search(query_vector, k=top_k * 2)  # Get more for filtering
        
        # Filter by resource if specified
        if resource:
            results = [r for r in results if r.get("resource") == resource][:top_k]
        else:
            results = results[:top_k]
        
        return results
    
    async def get_context_for_query(
        self,
        query: str,
        resource: Optional[str] = None,
        context_size: int = 3
    ) -> str:
        """Get contextual information for a query."""
        results = await self.semantic_search(query, resource, context_size)
        
        context_parts = []
        for result in results:
            context_parts.append(f"[{result['role']}]: {result['content']}")
        
        return "\n".join(context_parts)


# Global semantic search engine
semantic_search = SemanticSearchEngine()
