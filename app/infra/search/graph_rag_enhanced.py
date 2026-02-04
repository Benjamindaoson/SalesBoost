"""
Enhanced GraphRAG Implementation with LLM-based Extraction and Multi-hop Reasoning.

This module provides advanced knowledge graph capabilities for sales training:
- LLM-based entity and relation extraction
- Multi-hop reasoning for complex queries
- Path finding for sales strategy discovery
- Integration with existing RAG system

Architecture:
    Sales Conversation → LLM Extractor → Knowledge Graph → Multi-hop Reasoner → Sales Insights
"""

import logging
import json
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass

from app.infra.search.graph_rag import (
    Entity, Relation, Subgraph, KnowledgeGraph,
    EntityType, RelationType
)

logger = logging.getLogger(__name__)


# ==================== LLM-based Knowledge Extraction ====================

class LLMKnowledgeExtractor:
    """
    Extract entities and relations from sales conversations using LLM.

    This replaces simple keyword matching with intelligent extraction that
    understands context, implicit relationships, and sales domain knowledge.
    """

    def __init__(self, llm_client: Any):
        """
        Initialize LLM knowledge extractor.

        Args:
            llm_client: LLM client (e.g., ModelGateway)
        """
        self.llm_client = llm_client

        # Extraction prompts
        self.entity_extraction_prompt = """你是一个销售知识图谱构建专家。请从以下销售对话中提取关键实体。

销售对话：
{text}

请提取以下类型的实体：
1. 产品 (product): 信用卡、服务、方案等
2. 特性 (feature): 产品的功能、权益、优势
3. 异议 (objection): 客户的顾虑、拒绝理由
4. 应对 (response): 销售的回应话术、策略
5. 阶段 (stage): 销售流程的阶段（开场、需求挖掘、异议处理等）
6. 客户类型 (customer_type): 客户的分类（价格敏感型、品质追求型等）
7. 技巧 (technique): 销售技巧、方法论
8. 利益 (benefit): 客户能获得的好处
9. 价格 (price): 价格信息、费用
10. 竞品 (competitor): 竞争对手产品

输出格式（JSON）：
{
  "entities": [
    {
      "name": "实体名称",
      "type": "实体类型",
      "properties": {
        "description": "实体描述",
        "context": "出现的上下文"
      }
    }
  ]
}

只输出JSON，不要其他内容。"""

        self.relation_extraction_prompt = """你是一个销售知识图谱构建专家。请从以下销售对话和已提取的实体中，识别实体之间的关系。

销售对话：
{text}

已提取的实体：
{entities}

请识别以下类型的关系：
1. has_feature: 产品具有某个特性
2. addresses: 应对话术解决某个异议
3. suitable_for: 产品适合某类客户
4. used_in_stage: 技巧用于某个销售阶段
5. competes_with: 与竞品竞争
6. provides_benefit: 产品提供某个利益
7. costs: 产品的价格
8. requires: 需要某个前置条件
9. similar_to: 与某个实体相似
10. part_of: 是某个实体的一部分

输出格式（JSON）：
{
  "relations": [
    {
      "source": "源实体名称",
      "target": "目标实体名称",
      "type": "关系类型",
      "properties": {
        "confidence": 0.95,
        "evidence": "支持该关系的证据文本"
      }
    }
  ]
}

只输出JSON，不要其他内容。"""

    async def extract_entities(self, text: str) -> List[Entity]:
        """
        Extract entities from text using LLM.

        Args:
            text: Sales conversation text

        Returns:
            List of extracted entities
        """
        try:
            # Call LLM
            prompt = self.entity_extraction_prompt.format(text=text)
            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=2000,
            )

            # Parse JSON response
            result = json.loads(response)

            # Convert to Entity objects
            entities = []
            for entity_data in result.get("entities", []):
                entity = Entity(
                    id=f"{entity_data['type']}_{hash(entity_data['name'])}",
                    name=entity_data["name"],
                    type=EntityType(entity_data["type"]),
                    properties=entity_data.get("properties", {})
                )
                entities.append(entity)

            logger.info(f"Extracted {len(entities)} entities using LLM")
            return entities

        except Exception as e:
            logger.error(f"LLM entity extraction failed: {e}")
            return []

    async def extract_relations(
        self,
        text: str,
        entities: List[Entity]
    ) -> List[Relation]:
        """
        Extract relations between entities using LLM.

        Args:
            text: Sales conversation text
            entities: Previously extracted entities

        Returns:
            List of extracted relations
        """
        try:
            # Format entities for prompt
            entities_str = "\n".join([
                f"- {e.name} ({e.type.value})"
                for e in entities
            ])

            # Call LLM
            prompt = self.relation_extraction_prompt.format(
                text=text,
                entities=entities_str
            )
            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=2000,
            )

            # Parse JSON response
            result = json.loads(response)

            # Convert to Relation objects
            relations = []
            entity_map = {e.name: e for e in entities}

            for rel_data in result.get("relations", []):
                source_name = rel_data["source"]
                target_name = rel_data["target"]

                if source_name in entity_map and target_name in entity_map:
                    source_entity = entity_map[source_name]
                    target_entity = entity_map[target_name]

                    relation = Relation(
                        id=f"rel_{source_entity.id}_{target_entity.id}",
                        source_id=source_entity.id,
                        target_id=target_entity.id,
                        type=RelationType(rel_data["type"]),
                        properties=rel_data.get("properties", {}),
                        weight=rel_data.get("properties", {}).get("confidence", 1.0)
                    )
                    relations.append(relation)

            logger.info(f"Extracted {len(relations)} relations using LLM")
            return relations

        except Exception as e:
            logger.error(f"LLM relation extraction failed: {e}")
            return []


# ==================== Multi-hop Reasoning ====================

@dataclass
class ReasoningPath:
    """A reasoning path through the knowledge graph."""
    entities: List[Entity]
    relations: List[Relation]
    path_score: float
    reasoning: str  # Natural language explanation of the path


class MultiHopReasoner:
    """
    Multi-hop reasoning engine for complex sales queries.

    This enables the system to answer questions like:
    "客户说年费太贵，销冠通常怎么应对？"

    The reasoner will find paths like:
    [异议: 年费贵] --addresses--> [应对: 权益话术] --part_of--> [技巧: 价值转化]
    """

    def __init__(
        self,
        knowledge_graph: KnowledgeGraph,
        llm_client: Any,
        max_hops: int = 3,
        max_paths: int = 5,
    ):
        """
        Initialize multi-hop reasoner.

        Args:
            knowledge_graph: Knowledge graph instance
            llm_client: LLM client for path ranking
            max_hops: Maximum reasoning hops
            max_paths: Maximum paths to return
        """
        self.knowledge_graph = knowledge_graph
        self.llm_client = llm_client
        self.max_hops = max_hops
        self.max_paths = max_paths

    async def reason(
        self,
        query: str,
        start_entities: List[str],
        target_type: Optional[EntityType] = None,
    ) -> List[ReasoningPath]:
        """
        Perform multi-hop reasoning to answer a query.

        Args:
            query: Natural language query
            start_entities: Starting entity IDs
            target_type: Target entity type (optional)

        Returns:
            List of reasoning paths
        """
        # Find all paths from start entities
        all_paths = []

        for start_id in start_entities:
            paths = self._find_paths(
                start_id=start_id,
                target_type=target_type,
                current_path=[],
                visited=set(),
                depth=0
            )
            all_paths.extend(paths)

        # Rank paths by relevance
        ranked_paths = await self._rank_paths(query, all_paths)

        # Return top paths
        return ranked_paths[:self.max_paths]

    def _find_paths(
        self,
        start_id: str,
        target_type: Optional[EntityType],
        current_path: List[Tuple[Entity, Relation]],
        visited: Set[str],
        depth: int,
    ) -> List[List[Tuple[Entity, Relation]]]:
        """
        Recursively find paths through the graph.

        Args:
            start_id: Current entity ID
            target_type: Target entity type
            current_path: Current path
            visited: Visited entity IDs
            depth: Current depth

        Returns:
            List of paths
        """
        if depth >= self.max_hops:
            return [current_path] if current_path else []

        if start_id in visited:
            return []

        visited.add(start_id)
        paths = []

        # Get current entity
        current_entity = self.knowledge_graph.get_entity(start_id)
        if not current_entity:
            return []

        # Check if we reached target type
        if target_type and current_entity.type == target_type and current_path:
            paths.append(current_path)

        # Explore neighbors
        for relation in self.knowledge_graph.relations.values():
            if relation.source_id == start_id:
                next_id = relation.target_id
                next_entity = self.knowledge_graph.get_entity(next_id)

                if next_entity and next_id not in visited:
                    new_path = current_path + [(next_entity, relation)]
                    sub_paths = self._find_paths(
                        start_id=next_id,
                        target_type=target_type,
                        current_path=new_path,
                        visited=visited.copy(),
                        depth=depth + 1
                    )
                    paths.extend(sub_paths)

        return paths

    async def _rank_paths(
        self,
        query: str,
        paths: List[List[Tuple[Entity, Relation]]]
    ) -> List[ReasoningPath]:
        """
        Rank paths by relevance to query using LLM.

        Args:
            query: User query
            paths: List of paths

        Returns:
            Ranked reasoning paths
        """
        if not paths:
            return []

        # Convert paths to reasoning paths
        reasoning_paths = []

        for path in paths:
            # Extract entities and relations
            entities = [item[0] for item in path]
            relations = [item[1] for item in path]

            # Generate natural language explanation
            reasoning = self._path_to_reasoning(entities, relations)

            # Calculate path score (simple heuristic)
            path_score = sum(r.weight for r in relations) / len(relations) if relations else 0

            reasoning_path = ReasoningPath(
                entities=entities,
                relations=relations,
                path_score=path_score,
                reasoning=reasoning
            )
            reasoning_paths.append(reasoning_path)

        # Sort by score
        reasoning_paths.sort(key=lambda p: p.path_score, reverse=True)

        return reasoning_paths

    def _path_to_reasoning(
        self,
        entities: List[Entity],
        relations: List[Relation]
    ) -> str:
        """
        Convert path to natural language reasoning.

        Args:
            entities: Path entities
            relations: Path relations

        Returns:
            Natural language explanation
        """
        if not entities or not relations:
            return ""

        # Build reasoning chain
        reasoning_parts = []

        for i, (entity, relation) in enumerate(zip(entities[:-1], relations)):
            next_entity = entities[i + 1]
            reasoning_parts.append(
                f"{entity.name} --[{relation.type.value}]--> {next_entity.name}"
            )

        return " → ".join(reasoning_parts)


# ==================== Enhanced GraphRAG Service ====================

class EnhancedGraphRAGService:
    """
    Enhanced GraphRAG service with LLM-based extraction and multi-hop reasoning.

    This service provides:
    1. Intelligent entity/relation extraction from sales conversations
    2. Multi-hop reasoning for complex queries
    3. Path-based insights for sales strategy discovery
    4. Integration with existing RAG system
    """

    def __init__(
        self,
        org_id: str,
        llm_client: Any,
        enable_multi_hop: bool = True,
        max_reasoning_hops: int = 3,
    ):
        """
        Initialize enhanced GraphRAG service.

        Args:
            org_id: Organization ID
            llm_client: LLM client
            enable_multi_hop: Enable multi-hop reasoning
            max_reasoning_hops: Maximum reasoning hops
        """
        self.org_id = org_id
        self.llm_client = llm_client
        self.enable_multi_hop = enable_multi_hop

        # Initialize components
        self.knowledge_graph = KnowledgeGraph()
        self.llm_extractor = LLMKnowledgeExtractor(llm_client)

        if enable_multi_hop:
            self.multi_hop_reasoner = MultiHopReasoner(
                knowledge_graph=self.knowledge_graph,
                llm_client=llm_client,
                max_hops=max_reasoning_hops,
            )
        else:
            self.multi_hop_reasoner = None

        logger.info(
            f"Enhanced GraphRAG service initialized for org: {org_id}, "
            f"multi-hop: {enable_multi_hop}"
        )

    async def ingest_sales_conversation(
        self,
        conversation_id: str,
        conversation_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ingest sales conversation into knowledge graph.

        Args:
            conversation_id: Conversation ID
            conversation_text: Conversation text
            metadata: Conversation metadata

        Returns:
            Ingestion result
        """
        # Extract entities using LLM
        entities = await self.llm_extractor.extract_entities(conversation_text)

        # Add entities to graph
        for entity in entities:
            self.knowledge_graph.add_entity(entity)

        # Extract relations using LLM
        relations = await self.llm_extractor.extract_relations(
            conversation_text,
            entities
        )

        # Add relations to graph
        for relation in relations:
            self.knowledge_graph.add_relation(relation)

        logger.info(
            f"Ingested conversation {conversation_id}: "
            f"{len(entities)} entities, {len(relations)} relations"
        )

        return {
            "conversation_id": conversation_id,
            "total_entities": len(entities),
            "total_relations": len(relations),
            "entity_types": list(set(e.type.value for e in entities)),
            "relation_types": list(set(r.type.value for r in relations)),
        }

    async def answer_complex_query(
        self,
        query: str,
        use_multi_hop: bool = True,
    ) -> Dict[str, Any]:
        """
        Answer complex sales query using multi-hop reasoning.

        Example queries:
        - "客户说年费太贵，销冠通常怎么应对？"
        - "如何处理客户的价格异议？"
        - "什么话术适合价格敏感型客户？"

        Args:
            query: Natural language query
            use_multi_hop: Use multi-hop reasoning

        Returns:
            Answer with reasoning paths
        """
        # Find relevant starting entities
        start_entities = self._find_query_entities(query)

        if not start_entities:
            return {
                "query": query,
                "answer": "未找到相关知识",
                "reasoning_paths": [],
                "confidence": 0.0,
            }

        # Perform multi-hop reasoning
        if use_multi_hop and self.multi_hop_reasoner:
            # Determine target type from query
            target_type = self._infer_target_type(query)

            reasoning_paths = await self.multi_hop_reasoner.reason(
                query=query,
                start_entities=[e.id for e in start_entities],
                target_type=target_type,
            )

            # Generate answer from paths
            answer = self._generate_answer_from_paths(query, reasoning_paths)

            return {
                "query": query,
                "answer": answer,
                "reasoning_paths": [
                    {
                        "entities": [e.name for e in path.entities],
                        "reasoning": path.reasoning,
                        "score": path.path_score,
                    }
                    for path in reasoning_paths
                ],
                "confidence": reasoning_paths[0].path_score if reasoning_paths else 0.0,
            }
        else:
            # Simple retrieval without multi-hop
            subgraph = self.knowledge_graph.extract_subgraph(
                seed_entities=[e.id for e in start_entities],
                max_hops=1,
                max_entities=10,
            )

            answer = self._generate_answer_from_subgraph(query, subgraph)

            return {
                "query": query,
                "answer": answer,
                "reasoning_paths": [],
                "confidence": 0.5,
            }

    def _find_query_entities(self, query: str) -> List[Entity]:
        """Find entities relevant to query."""
        relevant_entities = []

        for entity in self.knowledge_graph.entities.values():
            # Simple keyword matching
            if entity.name.lower() in query.lower() or query.lower() in entity.name.lower():
                relevant_entities.append(entity)

        return relevant_entities

    def _infer_target_type(self, query: str) -> Optional[EntityType]:
        """Infer target entity type from query."""
        if "应对" in query or "话术" in query or "回应" in query:
            return EntityType.RESPONSE
        elif "技巧" in query or "方法" in query:
            return EntityType.TECHNIQUE
        elif "客户" in query:
            return EntityType.CUSTOMER_TYPE
        else:
            return None

    def _generate_answer_from_paths(
        self,
        query: str,
        paths: List[ReasoningPath]
    ) -> str:
        """Generate answer from reasoning paths."""
        if not paths:
            return "未找到相关的销售策略"

        # Use top path
        top_path = paths[0]

        # Extract final entity (usually the answer)
        if top_path.entities:
            final_entity = top_path.entities[-1]
            answer_parts = [f"根据销冠经验，{final_entity.name}"]

            # Add reasoning
            if top_path.reasoning:
                answer_parts.append(f"\n\n推理路径：{top_path.reasoning}")

            # Add properties if available
            if final_entity.properties:
                desc = final_entity.properties.get("description")
                if desc:
                    answer_parts.append(f"\n\n详细说明：{desc}")

            return "".join(answer_parts)

        return "未找到具体的应对策略"

    def _generate_answer_from_subgraph(
        self,
        query: str,
        subgraph: Subgraph
    ) -> str:
        """Generate answer from subgraph."""
        if not subgraph.entities:
            return "未找到相关知识"

        # Collect relevant entities
        relevant_entities = [
            e for e in subgraph.entities
            if e.type in [EntityType.RESPONSE, EntityType.TECHNIQUE]
        ]

        if relevant_entities:
            entity_names = [e.name for e in relevant_entities[:3]]
            return f"相关策略：{', '.join(entity_names)}"

        return "未找到具体的应对策略"

    def get_stats(self) -> Dict[str, Any]:
        """Get enhanced GraphRAG statistics."""
        return {
            "org_id": self.org_id,
            "graph_stats": self.knowledge_graph.get_stats(),
            "enable_multi_hop": self.enable_multi_hop,
            "total_entities": len(self.knowledge_graph.entities),
            "total_relations": len(self.knowledge_graph.relations),
        }


# ==================== Factory Function ====================

_enhanced_graph_rag_services: Dict[str, EnhancedGraphRAGService] = {}


def get_enhanced_graph_rag_service(
    org_id: str,
    llm_client: Any,
    force_new: bool = False,
) -> EnhancedGraphRAGService:
    """
    Get or create enhanced GraphRAG service (singleton per org).

    Args:
        org_id: Organization ID
        llm_client: LLM client
        force_new: Force create new instance

    Returns:
        EnhancedGraphRAGService instance
    """
    global _enhanced_graph_rag_services

    if org_id not in _enhanced_graph_rag_services or force_new:
        _enhanced_graph_rag_services[org_id] = EnhancedGraphRAGService(
            org_id=org_id,
            llm_client=llm_client,
            enable_multi_hop=True,
            max_reasoning_hops=3,
        )

    return _enhanced_graph_rag_services[org_id]
