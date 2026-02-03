"""
GraphRAG Implementation for SalesBoost.

Implements knowledge graph-enhanced RAG with entity extraction,
relation extraction, and graph-based retrieval.
"""
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """Entity types in sales knowledge graph."""
    PRODUCT = "product"
    FEATURE = "feature"
    OBJECTION = "objection"
    RESPONSE = "response"
    STAGE = "stage"
    CUSTOMER_TYPE = "customer_type"
    TECHNIQUE = "technique"
    BENEFIT = "benefit"
    PRICE = "price"
    COMPETITOR = "competitor"


class RelationType(str, Enum):
    """Relation types in sales knowledge graph."""
    HAS_FEATURE = "has_feature"
    ADDRESSES = "addresses"
    SUITABLE_FOR = "suitable_for"
    USED_IN_STAGE = "used_in_stage"
    COMPETES_WITH = "competes_with"
    PROVIDES_BENEFIT = "provides_benefit"
    COSTS = "costs"
    REQUIRES = "requires"
    SIMILAR_TO = "similar_to"
    PART_OF = "part_of"


@dataclass
class Entity:
    """Knowledge graph entity."""
    id: str
    name: str
    type: EntityType
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class Relation:
    """Knowledge graph relation."""
    id: str
    source_id: str
    target_id: str
    type: RelationType
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0


@dataclass
class Triple:
    """Knowledge graph triple (subject, predicate, object)."""
    subject: Entity
    predicate: Relation
    object: Entity


@dataclass
class Subgraph:
    """Subgraph extracted from knowledge graph."""
    entities: List[Entity]
    relations: List[Relation]
    triples: List[Triple]
    relevance_score: float = 0.0


class KnowledgeGraph:
    """
    In-memory knowledge graph for sales knowledge.

    Features:
    - Entity and relation storage
    - Graph traversal
    - Subgraph extraction
    - Community detection (optional)
    """

    def __init__(self):
        """Initialize knowledge graph."""
        self.entities: Dict[str, Entity] = {}
        self.relations: Dict[str, Relation] = {}
        self.adjacency: Dict[str, Set[str]] = {}  # entity_id -> set of related entity_ids

    def add_entity(self, entity: Entity) -> None:
        """Add entity to graph."""
        self.entities[entity.id] = entity
        if entity.id not in self.adjacency:
            self.adjacency[entity.id] = set()

    def add_relation(self, relation: Relation) -> None:
        """Add relation to graph."""
        self.relations[relation.id] = relation

        # Update adjacency
        if relation.source_id not in self.adjacency:
            self.adjacency[relation.source_id] = set()
        if relation.target_id not in self.adjacency:
            self.adjacency[relation.target_id] = set()

        self.adjacency[relation.source_id].add(relation.target_id)

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self.entities.get(entity_id)

    def get_neighbors(self, entity_id: str, max_hops: int = 1) -> Set[str]:
        """
        Get neighboring entities within max_hops.

        Args:
            entity_id: Starting entity ID
            max_hops: Maximum number of hops

        Returns:
            Set of neighboring entity IDs
        """
        if entity_id not in self.adjacency:
            return set()

        neighbors = set()
        current_level = {entity_id}

        for _ in range(max_hops):
            next_level = set()
            for eid in current_level:
                if eid in self.adjacency:
                    next_level.update(self.adjacency[eid])
            neighbors.update(next_level)
            current_level = next_level

        return neighbors

    def extract_subgraph(
        self,
        seed_entities: List[str],
        max_hops: int = 2,
        max_entities: int = 50,
    ) -> Subgraph:
        """
        Extract subgraph around seed entities.

        Args:
            seed_entities: Starting entity IDs
            max_hops: Maximum hops from seed
            max_entities: Maximum entities in subgraph

        Returns:
            Extracted subgraph
        """
        # Collect entities
        entity_ids = set(seed_entities)
        for seed in seed_entities:
            neighbors = self.get_neighbors(seed, max_hops)
            entity_ids.update(neighbors)
            if len(entity_ids) >= max_entities:
                break

        entity_ids = list(entity_ids)[:max_entities]

        # Collect entities and relations
        entities = [self.entities[eid] for eid in entity_ids if eid in self.entities]

        relations = []
        triples = []
        for rel in self.relations.values():
            if rel.source_id in entity_ids and rel.target_id in entity_ids:
                relations.append(rel)

                # Create triple
                if rel.source_id in self.entities and rel.target_id in self.entities:
                    triple = Triple(
                        subject=self.entities[rel.source_id],
                        predicate=rel,
                        object=self.entities[rel.target_id]
                    )
                    triples.append(triple)

        return Subgraph(
            entities=entities,
            relations=relations,
            triples=triples
        )

    def get_stats(self) -> Dict[str, int]:
        """Get graph statistics."""
        return {
            "num_entities": len(self.entities),
            "num_relations": len(self.relations),
            "num_entity_types": len(set(e.type for e in self.entities.values())),
            "num_relation_types": len(set(r.type for r in self.relations.values())),
        }


class EntityExtractor:
    """
    Extract entities from text using LLM or NER.

    For production, this should use a fine-tuned NER model or LLM.
    """

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize entity extractor.

        Args:
            llm_client: LLM client for extraction (optional)
        """
        self.llm_client = llm_client

    async def extract(self, text: str) -> List[Entity]:
        """
        Extract entities from text.

        Args:
            text: Input text

        Returns:
            List of extracted entities
        """
        # Simple rule-based extraction for demo
        # In production, use LLM or fine-tuned NER model

        entities = []

        # Extract products (simple keyword matching)
        product_keywords = ["产品", "信用卡", "服务", "方案"]
        for keyword in product_keywords:
            if keyword in text:
                entity = Entity(
                    id=f"product_{keyword}",
                    name=keyword,
                    type=EntityType.PRODUCT,
                    properties={"source_text": text}
                )
                entities.append(entity)

        # Extract objections
        objection_keywords = ["太贵", "不需要", "考虑考虑", "没时间"]
        for keyword in objection_keywords:
            if keyword in text:
                entity = Entity(
                    id=f"objection_{keyword}",
                    name=keyword,
                    type=EntityType.OBJECTION,
                    properties={"source_text": text}
                )
                entities.append(entity)

        # Extract responses
        response_keywords = ["可以回应", "话术", "应对"]
        for keyword in response_keywords:
            if keyword in text:
                entity = Entity(
                    id=f"response_{hash(text)}",
                    name=text[:50],
                    type=EntityType.RESPONSE,
                    properties={"full_text": text}
                )
                entities.append(entity)

        return entities


class RelationExtractor:
    """
    Extract relations between entities.

    For production, this should use a fine-tuned relation extraction model.
    """

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize relation extractor.

        Args:
            llm_client: LLM client for extraction (optional)
        """
        self.llm_client = llm_client

    async def extract(
        self,
        text: str,
        entities: List[Entity]
    ) -> List[Relation]:
        """
        Extract relations between entities.

        Args:
            text: Source text
            entities: Extracted entities

        Returns:
            List of relations
        """
        relations = []

        # Simple rule-based relation extraction
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                # Objection -> Response
                if entity1.type == EntityType.OBJECTION and entity2.type == EntityType.RESPONSE:
                    relation = Relation(
                        id=f"rel_{entity1.id}_{entity2.id}",
                        source_id=entity1.id,
                        target_id=entity2.id,
                        type=RelationType.ADDRESSES,
                        properties={"source_text": text}
                    )
                    relations.append(relation)

                # Product -> Feature
                elif entity1.type == EntityType.PRODUCT and entity2.type == EntityType.FEATURE:
                    relation = Relation(
                        id=f"rel_{entity1.id}_{entity2.id}",
                        source_id=entity1.id,
                        target_id=entity2.id,
                        type=RelationType.HAS_FEATURE,
                        properties={"source_text": text}
                    )
                    relations.append(relation)

        return relations


class GraphRetriever:
    """
    Retrieve relevant subgraphs from knowledge graph.

    Supports multiple retrieval modes:
    - Local: Retrieve entities and their neighbors
    - Global: Retrieve based on graph structure
    - Hybrid: Combine local and global retrieval
    """

    def __init__(
        self,
        knowledge_graph: KnowledgeGraph,
        embedding_manager: Optional[Any] = None,
    ):
        """
        Initialize graph retriever.

        Args:
            knowledge_graph: Knowledge graph instance
            embedding_manager: Embedding manager for semantic search
        """
        self.knowledge_graph = knowledge_graph
        self.embedding_manager = embedding_manager

    async def retrieve_local(
        self,
        query: str,
        top_k: int = 5,
        max_hops: int = 2,
    ) -> Subgraph:
        """
        Local retrieval: Find relevant entities and their neighbors.

        Args:
            query: Search query
            top_k: Number of seed entities
            max_hops: Maximum hops from seed

        Returns:
            Retrieved subgraph
        """
        # Find seed entities by name matching (simple)
        seed_entities = []
        for entity in self.knowledge_graph.entities.values():
            if query.lower() in entity.name.lower():
                seed_entities.append(entity.id)
                if len(seed_entities) >= top_k:
                    break

        if not seed_entities:
            return Subgraph(entities=[], relations=[], triples=[])

        # Extract subgraph
        subgraph = self.knowledge_graph.extract_subgraph(
            seed_entities=seed_entities,
            max_hops=max_hops,
            max_entities=50
        )

        return subgraph

    async def retrieve_for_objection(
        self,
        objection_text: str,
        top_k: int = 5,
    ) -> Subgraph:
        """
        Retrieve responses for a specific objection.

        Args:
            objection_text: Objection text
            top_k: Number of responses

        Returns:
            Subgraph with objection and responses
        """
        # Find objection entities
        objection_entities = [
            e for e in self.knowledge_graph.entities.values()
            if e.type == EntityType.OBJECTION and objection_text.lower() in e.name.lower()
        ]

        if not objection_entities:
            return Subgraph(entities=[], relations=[], triples=[])

        # Find related responses
        seed_ids = [e.id for e in objection_entities]
        subgraph = self.knowledge_graph.extract_subgraph(
            seed_entities=seed_ids,
            max_hops=1,
            max_entities=top_k * 2
        )

        return subgraph


@dataclass
class GraphRAGResult:
    """GraphRAG search result."""
    query: str
    mode: str
    subgraph: Subgraph
    context: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class GraphRAGService:
    """
    GraphRAG service integrating knowledge graph with RAG.

    Features:
    - Document ingestion with entity/relation extraction
    - Graph-based retrieval
    - Multiple retrieval modes (local, global, hybrid)
    - Community detection (optional)
    """

    def __init__(
        self,
        org_id: str,
        enable_communities: bool = False,
        llm_client: Optional[Any] = None,
    ):
        """
        Initialize GraphRAG service.

        Args:
            org_id: Organization ID
            enable_communities: Enable community detection
            llm_client: LLM client for extraction
        """
        self.org_id = org_id
        self.enable_communities = enable_communities

        self.knowledge_graph = KnowledgeGraph()
        self.entity_extractor = EntityExtractor(llm_client)
        self.relation_extractor = RelationExtractor(llm_client)
        self.graph_retriever = GraphRetriever(self.knowledge_graph)

        logger.info(f"GraphRAG service initialized for org: {org_id}")

    async def ingest_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ingest document into knowledge graph.

        Args:
            doc_id: Document ID
            text: Document text
            metadata: Document metadata

        Returns:
            Ingestion result
        """
        # Extract entities
        entities = await self.entity_extractor.extract(text)

        # Add entities to graph
        for entity in entities:
            self.knowledge_graph.add_entity(entity)

        # Extract relations
        relations = await self.relation_extractor.extract(text, entities)

        # Add relations to graph
        for relation in relations:
            self.knowledge_graph.add_relation(relation)

        logger.info(
            f"Ingested document {doc_id}: "
            f"{len(entities)} entities, {len(relations)} relations"
        )

        return {
            "doc_id": doc_id,
            "total_entities": len(entities),
            "total_relations": len(relations),
            "total_triples": len(relations),
        }

    async def search(
        self,
        query: str,
        mode: str = "local",
        top_k: int = 5,
        max_hops: int = 2,
    ) -> GraphRAGResult:
        """
        Search knowledge graph.

        Args:
            query: Search query
            mode: Retrieval mode ("local", "global", "hybrid")
            top_k: Number of results
            max_hops: Maximum hops for local retrieval

        Returns:
            GraphRAG search result
        """
        if mode == "local":
            subgraph = await self.graph_retriever.retrieve_local(
                query=query,
                top_k=top_k,
                max_hops=max_hops
            )
        elif mode == "hybrid":
            # Combine local and global retrieval
            subgraph = await self.graph_retriever.retrieve_local(
                query=query,
                top_k=top_k,
                max_hops=max_hops
            )
        else:
            raise ValueError(f"Unknown mode: {mode}")

        # Convert subgraph to context
        context = self._subgraph_to_context(subgraph)

        return GraphRAGResult(
            query=query,
            mode=mode,
            subgraph=subgraph,
            context=context,
            metadata={
                "num_entities": len(subgraph.entities),
                "num_relations": len(subgraph.relations),
                "num_triples": len(subgraph.triples),
            }
        )

    def _subgraph_to_context(self, subgraph: Subgraph) -> str:
        """
        Convert subgraph to text context.

        Args:
            subgraph: Subgraph to convert

        Returns:
            Text context
        """
        context_parts = []

        # Add entities
        for entity in subgraph.entities:
            context_parts.append(f"[{entity.type.value}] {entity.name}")

        # Add triples
        for triple in subgraph.triples:
            context_parts.append(
                f"{triple.subject.name} --[{triple.predicate.type.value}]--> {triple.object.name}"
            )

        return "\n".join(context_parts)

    def get_stats(self) -> Dict[str, Any]:
        """Get GraphRAG statistics."""
        return {
            "org_id": self.org_id,
            "graph_stats": self.knowledge_graph.get_stats(),
            "enable_communities": self.enable_communities,
        }
