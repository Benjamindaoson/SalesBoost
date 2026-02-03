"""
GraphRAG 集成测试

测试知识图谱增强的 RAG 系统的基本功能。
"""
import pytest
import asyncio
from cognitive.skills.study.graph_rag_service import GraphRAGService
from cognitive.skills.study.graph_rag.graph_schema import EntityType, RelationType


@pytest.mark.asyncio
async def test_graph_rag_service_initialization():
    """测试 GraphRAG 服务初始化"""
    service = GraphRAGService(
        org_id="test",
        enable_communities=True,
    )
    
    assert service is not None
    assert service.knowledge_graph is not None
    assert service.relation_extractor is not None
    assert service.graph_retriever is not None


@pytest.mark.asyncio
async def test_document_ingestion():
    """测试文档摄入"""
    service = GraphRAGService(org_id="test")
    
    # 测试文档
    test_doc = """
    当客户说"年费太贵"时，可以回应"首年免年费，之后每年消费满6次即可免年费"。
    信用卡产品具有积分兑换功能，可以帮助客户省钱。
    这个话术适用于促单成交阶段。
    """
    
    result = await service.ingest_document(
        doc_id="test_doc_1",
        text=test_doc,
    )
    
    assert result is not None
    assert "total_entities" in result
    assert "total_triples" in result
    assert result["total_entities"] > 0


@pytest.mark.asyncio
async def test_graph_search_local():
    """测试局部图检索"""
    service = GraphRAGService(org_id="test")
    
    # 先摄入一些测试数据
    test_doc = """
    当客户说"年费太贵"时，可以回应"首年免年费"。
    """
    await service.ingest_document(doc_id="test_doc_2", text=test_doc)
    
    # 执行局部检索
    result = await service.search(
        query="年费太贵",
        mode="local",
        top_k=5,
    )
    
    assert result is not None
    assert result.mode == "local"


@pytest.mark.asyncio
async def test_graph_search_hybrid():
    """测试混合检索"""
    service = GraphRAGService(org_id="test")
    
    result = await service.search(
        query="如何处理价格异议",
        mode="hybrid",
        top_k=5,
    )
    
    assert result is not None
    assert result.mode == "hybrid"


@pytest.mark.asyncio
async def test_objection_retrieval():
    """测试异议检索"""
    service = GraphRAGService(org_id="test")
    
    # 先摄入异议相关数据
    test_doc = """
    当客户说"价格太贵"时，可以回应"我们的产品性价比很高，而且首年免年费"。
    """
    await service.ingest_document(doc_id="test_doc_3", text=test_doc)
    
    # 检索异议应对
    subgraph = await service.graph_retriever.retrieve_for_objection(
        objection_text="价格太贵",
        top_k=5,
    )
    
    assert subgraph is not None


def test_graph_schema():
    """测试图 Schema"""
    from cognitive.skills.study.graph_rag.graph_schema import (
        Entity,
        EntityType,
        Relation,
        RelationType,
        Triple,
    )
    
    # 测试实体创建
    entity = Entity(
        id="test_entity_1",
        name="测试产品",
        type=EntityType.PRODUCT,
    )
    assert entity.type == EntityType.PRODUCT
    
    # 测试关系创建
    relation = Relation(
        id="test_rel_1",
        source_id="entity_1",
        target_id="entity_2",
        type=RelationType.HAS_FEATURE,
    )
    assert relation.type == RelationType.HAS_FEATURE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


