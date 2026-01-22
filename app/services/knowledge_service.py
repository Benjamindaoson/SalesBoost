import chromadb
from chromadb.utils import embedding_functions
import uuid
import logging
from typing import List, Dict, Any, Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class KnowledgeService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KnowledgeService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        settings = get_settings()
        # Persist data to disk
        try:
            import chromadb
            self.client = chromadb.PersistentClient(path="./knowledge_db")
        except ImportError:
            logger.warning("ChromaDB not installed, using mock")
            self.client = None
        except Exception as e:
            logger.warning(f"ChromaDB initialization failed: {e}, using mock")
            self.client = None
        
        # Use default embedding function (all-MiniLM-L6-v2)
        try:
            from chromadb.utils import embedding_functions
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
        except Exception as e:
            logger.warning(f"Embedding function init failed: {e}, using mock")
            self.embedding_fn = None
        
        if self.client:
            try:
                self.collection = self.client.get_or_create_collection(
                    name="sales_knowledge",
                    embedding_function=self.embedding_fn
                )
            except Exception as e:
                logger.warning(f"Collection init failed: {e}")
                self.collection = None
        else:
            self.collection = None
        self._initialized = True
        logger.info("KnowledgeService initialized with ChromaDB")

    def add_document(self, content: str, meta: Dict[str, Any], doc_id: Optional[str] = None) -> str:
        """
        Add a document to the knowledge base.
        """
        if not doc_id:
            doc_id = str(uuid.uuid4())
            
        self.collection.add(
            documents=[content],
            metadatas=[meta],
            ids=[doc_id]
        )
        logger.info(f"Document added: {doc_id}")
        return doc_id

    def query(self, text: str, top_k: int = 3, filter_meta: Optional[Dict] = None, min_relevance: float = 0.0) -> List[Dict]:
        """
        Query the knowledge base.
        """
        if not self.collection:
            return []
            
        results = self.collection.query(
            query_texts=[text],
            n_results=top_k,
            where=filter_meta
        )
        
        # Format results
        formatted_results = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i]
                doc_id = results["ids"][0][i]
                distance = results["distances"][0][i] if results["distances"] else 0
                
                # Simple relevance filtering (distance is dissimilarity)
                # Lower distance means higher relevance
                if min_relevance > 0 and distance > (1 - min_relevance):
                    continue

                formatted_results.append({
                    "id": doc_id,
                    "content": doc,
                    "metadata": meta,
                    "distance": distance,
                    "evidence_id": doc_id # Alias for V3 contract
                })
                
        return formatted_results

    def count_documents(self) -> int:
        return self.collection.count()
