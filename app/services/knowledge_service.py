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
        self.client = chromadb.PersistentClient(path="./knowledge_db")
        
        # Use default embedding function (all-MiniLM-L6-v2)
        # This will download the model on first use
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        self.collection = self.client.get_or_create_collection(
            name="sales_knowledge",
            embedding_function=self.embedding_fn
        )
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

    def query(self, text: str, top_k: int = 3, filter_meta: Optional[Dict] = None) -> List[Dict]:
        """
        Query the knowledge base.
        """
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
                formatted_results.append({
                    "content": doc,
                    "metadata": meta,
                    "distance": results["distances"][0][i] if results["distances"] else 0
                })
                
        return formatted_results

    def count_documents(self) -> int:
        return self.collection.count()
