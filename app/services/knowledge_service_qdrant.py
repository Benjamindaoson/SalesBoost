"""
知识服务 - 使用 Qdrant 向量数据库（2026年推荐）

Qdrant优势：
- Python原生，无DLL依赖
- 高性能，支持大规模数据
- 丰富的过滤和查询功能
- 生产级稳定性
"""
import uuid
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError
from openai import OpenAI
from app.services.document_parser import DocumentProcessor

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
    )
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False

logger = logging.getLogger(__name__)


class QdrantKnowledgeService:
    """
    基于Qdrant的知识服务
    
    2026年技术选型：
    - Qdrant: 高性能向量数据库（Python原生）
    - OpenAI Embeddings: text-embedding-3-small/large
    - 支持元数据过滤、混合检索
    """
    _instances: Dict[str, "QdrantKnowledgeService"] = {}
    
    def __new__(cls, org_id: Optional[str] = None):
        key = org_id or "public"
        if key not in cls._instances:
            cls._instances[key] = super(QdrantKnowledgeService, cls).__new__(cls)
            cls._instances[key]._initialized = False
        return cls._instances[key]
    
    def __init__(self, org_id: Optional[str] = None):
        if getattr(self, "_initialized", False):
            return
        
        if not HAS_QDRANT:
            raise ConfigurationError(
                "Qdrant client is required. Install with: pip install qdrant-client",
                error_code="MISSING_QDRANT",
            )
        
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise ConfigurationError(
                "OPENAI_API_KEY is required for embeddings.",
                error_code="MISSING_OPENAI_API_KEY",
            )
        
        self.org_id = org_id or "public"
        
        # 初始化Qdrant客户端（本地模式）
        qdrant_path = Path("./qdrant_db") / self.org_id
        qdrant_path.mkdir(parents=True, exist_ok=True)
        
        self.client = QdrantClient(path=str(qdrant_path))
        
        # 初始化OpenAI客户端
        self.openai_client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        
        # Embedding模型
        self.embedding_model = getattr(
            settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        )
        
        # 向量维度（根据模型自动获取）
        self.vector_size = self._get_embedding_dimension()
        
        # 集合名称
        self.collection_name = f"sales_knowledge_{self.org_id}"
        
        # 创建集合（如果不存在）
        self._ensure_collection()
        
        # 初始化文档处理器
        self.document_processor = DocumentProcessor(llm_client=self.openai_client)
        
        self._initialized = True
        logger.info(f"QdrantKnowledgeService initialized (Collection: {self.collection_name})")
    
    def _get_embedding_dimension(self) -> int:
        """获取embedding维度"""
        # text-embedding-3-small: 1536
        # text-embedding-3-large: 3072
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return model_dimensions.get(self.embedding_model, 1536)
    
    def _ensure_collection(self):
        """确保集合存在"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Created collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise
    
    def _get_embedding(self, text: str) -> List[float]:
        """获取文本的embedding"""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=[text],
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            raise
    
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取embeddings"""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Failed to get embeddings: {e}")
            raise
    
    def add_document(self, content: str, meta: Dict[str, Any], doc_id: Optional[str] = None) -> str:
        """添加文档到知识库"""
        if not doc_id:
            doc_id = str(uuid.uuid4())
        
        # 获取embedding
        embedding = self._get_embedding(content)
        
        # 添加到Qdrant
        point = PointStruct(
            id=doc_id,
            vector=embedding,
            payload={
                "content": content,
                **meta,
            },
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point],
        )
        
        logger.info(f"Document added to Qdrant: {doc_id}")
        return doc_id
    
    async def add_document_with_processing(
        self,
        content: bytes,
        filename: str,
        content_type: Optional[str],
        meta: Dict[str, Any],
        doc_type: str = "knowledge",
    ) -> Dict[str, Any]:
        """
        添加文档并进行结构化处理
        
        Returns:
            {
                "doc_id": str,
                "chunks_added": int,
                "entities": List[str],
                "tags": List[str],
                "summary": str,
            }
        """
        # 处理文档
        processed = await self.document_processor.process_document(
            content=content,
            filename=filename,
            content_type=content_type,
            doc_type=doc_type,
        )
        
        # 合并元数据
        enhanced_meta = {
            **meta,
            **processed["metadata"],
            "entities": processed["entities"],
            "tags": processed["tags"],
            "summary": processed["summary"],
            "topics": processed.get("topics", []),
        }
        
        # 批量获取embeddings
        chunk_contents = [chunk["content"] for chunk in processed["chunks"]]
        if not chunk_contents:
            return {
                "doc_id": enhanced_meta.get("doc_id", str(uuid.uuid4())),
                "chunks_added": 0,
                "entities": processed["entities"],
                "tags": processed["tags"],
                "summary": processed["summary"],
            }
        
        embeddings = self._get_embeddings(chunk_contents)
        
        # 批量添加到Qdrant
        points = []
        parent_doc_id = enhanced_meta.get("doc_id", str(uuid.uuid4()))
        
        for i, (chunk, embedding) in enumerate(zip(processed["chunks"], embeddings)):
            chunk_id = f"{parent_doc_id}_{i}"
            chunk_meta = {
                **enhanced_meta,
                "chunk_index": i,
                "parent_doc_id": parent_doc_id,
                "is_chunk": True,
            }
            
            point = PointStruct(
                id=chunk_id,
                vector=embedding,
                payload={
                    "content": chunk["content"],
                    **chunk_meta,
                },
            )
            points.append(point)
        
        # 批量插入
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        
        logger.info(
            f"Document processed and added to Qdrant: {len(points)} chunks, "
            f"{len(processed['entities'])} entities"
        )
        
        return {
            "doc_id": parent_doc_id,
            "chunks_added": len(points),
            "entities": processed["entities"],
            "tags": processed["tags"],
            "summary": processed["summary"],
            "key_points": processed.get("key_points", []),
        }
    
    def query(
        self,
        text: str,
        top_k: int = 3,
        filter_meta: Optional[Dict] = None,
        min_relevance: float = 0.5,
        rerank: bool = True,
    ) -> List[Dict]:
        """
        查询知识库
        
        Args:
            text: 查询文本
            top_k: 返回数量
            filter_meta: 元数据过滤条件
            min_relevance: 最小相关性阈值
            rerank: 是否重排序
        """
        # 获取查询embedding
        query_embedding = self._get_embedding(text)
        
        # 构建过滤条件
        query_filter = None
        if filter_meta:
            conditions = []
            for key, value in filter_meta.items():
                conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
            if conditions:
                query_filter = Filter(must=conditions)
        
        # 检索更多候选（用于重排序）
        retrieve_k = top_k * 3 if rerank else top_k
        
        # 执行搜索
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=retrieve_k,
            query_filter=query_filter,
        )
        
        # 格式化结果
        formatted_results = []
        query_lower = text.lower()
        query_words = set(query_lower.split())
        
        for result in search_results:
            payload = result.payload
            content = payload.get("content", "")
            
            # 计算相关性分数（Qdrant返回的是相似度分数，0-1之间）
            relevance_score = result.score
            
            # 关键词匹配加分
            doc_lower = content.lower()
            doc_words = set(doc_lower.split())
            keyword_overlap = len(query_words & doc_words) / max(len(query_words), 1)
            
            # 综合分数
            final_score = relevance_score * 0.7 + keyword_overlap * 0.3
            
            formatted_results.append({
                "content": content,
                "metadata": {k: v for k, v in payload.items() if k != "content"},
                "distance": 1.0 - relevance_score,  # 转换为距离
                "relevance_score": final_score,
                "keyword_overlap": keyword_overlap,
            })
        
        # 按相关性排序
        formatted_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # 过滤低相关性结果
        filtered = [r for r in formatted_results if r["relevance_score"] >= min_relevance]
        
        return filtered[:top_k]
    
    def count_documents(self) -> int:
        """统计文档数量"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return collection_info.points_count
        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            return 0
    
    def list_documents(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """列出文档"""
        try:
            # 获取所有点（限制数量）
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            
            docs = []
            for point in scroll_result[0]:
                payload = point.payload
                docs.append({
                    "id": str(point.id),
                    "content": payload.get("content", ""),
                    "metadata": {k: v for k, v in payload.items() if k != "content"},
                })
            
            return docs
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []
    
    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        try:
            # 删除主文档和所有chunks
            # 先查找所有相关的点
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="parent_doc_id",
                            match=MatchValue(value=doc_id)
                        )
                    ]
                ),
                limit=1000,
                with_payload=False,
            )
            
            ids_to_delete = [str(point.id) for point in scroll_result[0]]
            ids_to_delete.append(doc_id)  # 也删除主文档
            
            if ids_to_delete:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=ids_to_delete,
                )
            
            logger.info(f"Document deleted from Qdrant: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False

