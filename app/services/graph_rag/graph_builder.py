"""
知识图谱构建器 - 销售知识图谱的构建与管理

使用 NetworkX 作为图存储（MVP），支持后续迁移到 Neo4j。
"""
import logging
import pickle
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
import hashlib

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

from app.services.graph_rag.graph_schema import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    Triple,
    SubGraph,
    PREDEFINED_SALES_STAGES,
    PREDEFINED_CUSTOMER_TYPES,
)

logger = logging.getLogger(__name__)


class SalesKnowledgeGraph:
    """
    销售知识图谱
    
    核心功能：
    - 图的构建和管理（添加实体、关系）
    - 图的持久化（保存/加载）
    - 基础图查询（邻居、路径）
    - 与向量存储的集成（实体嵌入）
    """
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        org_id: Optional[str] = None,
    ):
        """
        初始化知识图谱
        
        Args:
            storage_path: 图存储路径
            org_id: 组织ID（支持多租户）
        """
        if not HAS_NETWORKX:
            raise ImportError("NetworkX is required. Install with: pip install networkx")
        
        self.org_id = org_id or "public"
        self.storage_path = Path(storage_path or "./graph_db")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 图文件路径
        self.graph_file = self.storage_path / f"sales_kg_{self.org_id}.gpickle"
        self.metadata_file = self.storage_path / f"sales_kg_{self.org_id}_meta.json"
        
        # 初始化图
        self.graph: nx.DiGraph = nx.DiGraph()
        
        # 实体索引（按类型）
        self.entity_index: Dict[EntityType, Set[str]] = defaultdict(set)
        
        # 实体名称到ID的映射
        self.name_to_id: Dict[str, str] = {}
        
        # 加载或初始化
        if self.graph_file.exists():
            self._load_graph()
        else:
            self._initialize_predefined_entities()
        
        logger.info(f"SalesKnowledgeGraph initialized: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
    
    def _initialize_predefined_entities(self):
        """初始化预定义实体"""
        # 添加销售阶段
        for stage in PREDEFINED_SALES_STAGES:
            self.add_entity(stage)
        
        # 添加客户类型
        for customer_type in PREDEFINED_CUSTOMER_TYPES:
            self.add_entity(customer_type)
        
        # 添加阶段顺序关系
        for i in range(len(PREDEFINED_SALES_STAGES) - 1):
            self.add_relation(Relation(
                id=f"stage_order_{i}",
                source_id=PREDEFINED_SALES_STAGES[i].id,
                target_id=PREDEFINED_SALES_STAGES[i + 1].id,
                type=RelationType.FOLLOWS,
                weight=1.0,
                confidence=1.0,
            ))
        
        logger.info("Predefined entities initialized")
    
    def add_entity(self, entity: Entity) -> bool:
        """
        添加实体到图中
        
        Args:
            entity: 实体对象
            
        Returns:
            是否成功添加（已存在返回 False）
        """
        if self.graph.has_node(entity.id):
            # 更新现有实体的属性
            existing_data = self.graph.nodes[entity.id]
            existing_doc_ids = set(existing_data.get("source_doc_ids", []))
            existing_doc_ids.update(entity.source_doc_ids)
            
            self.graph.nodes[entity.id].update({
                "properties": {**existing_data.get("properties", {}), **entity.properties},
                "source_doc_ids": list(existing_doc_ids),
            })
            return False
        
        # 添加新节点
        self.graph.add_node(
            entity.id,
            name=entity.name,
            type=entity.type.value if isinstance(entity.type, EntityType) else entity.type,
            properties=entity.properties,
            embedding=entity.embedding,
            source_doc_ids=entity.source_doc_ids,
            created_at=entity.created_at.isoformat() if entity.created_at else None,
        )
        
        # 更新索引
        entity_type = entity.type if isinstance(entity.type, EntityType) else EntityType(entity.type)
        self.entity_index[entity_type].add(entity.id)
        self.name_to_id[entity.name] = entity.id
        
        return True
    
    def add_relation(self, relation: Relation) -> bool:
        """
        添加关系到图中
        
        Args:
            relation: 关系对象
            
        Returns:
            是否成功添加
        """
        # 确保源和目标节点存在
        if not self.graph.has_node(relation.source_id):
            logger.warning(f"Source node not found: {relation.source_id}")
            return False
        if not self.graph.has_node(relation.target_id):
            logger.warning(f"Target node not found: {relation.target_id}")
            return False
        
        # 检查是否已存在相同关系
        if self.graph.has_edge(relation.source_id, relation.target_id):
            existing_data = self.graph.edges[relation.source_id, relation.target_id]
            # 如果关系类型相同，更新权重和置信度
            if existing_data.get("type") == (relation.type.value if isinstance(relation.type, RelationType) else relation.type):
                # 取更高的置信度
                new_confidence = max(existing_data.get("confidence", 0), relation.confidence)
                self.graph.edges[relation.source_id, relation.target_id]["confidence"] = new_confidence
                return False
        
        # 添加边
        self.graph.add_edge(
            relation.source_id,
            relation.target_id,
            id=relation.id,
            type=relation.type.value if isinstance(relation.type, RelationType) else relation.type,
            properties=relation.properties,
            weight=relation.weight,
            confidence=relation.confidence,
            source_doc_ids=relation.source_doc_ids,
        )
        
        return True
    
    def add_triple(self, triple: Triple, doc_id: Optional[str] = None) -> Tuple[bool, bool]:
        """
        添加三元组到图中
        
        Args:
            triple: 三元组对象
            doc_id: 文档ID
            
        Returns:
            (实体是否新增, 关系是否新增)
        """
        # 添加主体实体
        entity_added = self.add_entity(triple.subject)
        
        # 添加客体实体
        entity_added = self.add_entity(triple.object) or entity_added
        
        # 创建关系
        relation_id = hashlib.md5(
            f"{triple.subject.id}:{triple.relation}:{triple.object.id}".encode()
        ).hexdigest()[:16]
        
        relation = triple.to_relation(relation_id, doc_id)
        relation_added = self.add_relation(relation)
        
        return entity_added, relation_added
    
    def add_document_to_graph(
        self,
        doc_id: str,
        entities: List[Entity],
        triples: List[Triple],
    ) -> Dict[str, int]:
        """
        将文档的实体和关系添加到图中
        
        Args:
            doc_id: 文档ID
            entities: 实体列表
            triples: 三元组列表
            
        Returns:
            添加统计 {"entities_added": int, "relations_added": int}
        """
        entities_added = 0
        relations_added = 0
        
        # 添加实体
        for entity in entities:
            if doc_id not in entity.source_doc_ids:
                entity.source_doc_ids.append(doc_id)
            if self.add_entity(entity):
                entities_added += 1
        
        # 添加三元组
        for triple in triples:
            _, rel_added = self.add_triple(triple, doc_id)
            if rel_added:
                relations_added += 1
        
        # 添加文档实体
        doc_entity = Entity(
            id=f"doc_{doc_id}",
            name=f"Document {doc_id}",
            type=EntityType.DOCUMENT,
            properties={"doc_id": doc_id},
        )
        self.add_entity(doc_entity)
        
        # 添加实体到文档的关系
        for entity in entities:
            self.add_relation(Relation(
                id=f"extracted_{entity.id}_{doc_id}",
                source_id=entity.id,
                target_id=doc_entity.id,
                type=RelationType.EXTRACTED_FROM,
                confidence=1.0,
            ))
        
        logger.info(f"Document {doc_id} added to graph: {entities_added} entities, {relations_added} relations")
        return {"entities_added": entities_added, "relations_added": relations_added}
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        if not self.graph.has_node(entity_id):
            return None
        
        data = self.graph.nodes[entity_id]
        return Entity(
            id=entity_id,
            name=data.get("name", ""),
            type=EntityType(data.get("type", "Keyword")),
            properties=data.get("properties", {}),
            embedding=data.get("embedding"),
            source_doc_ids=data.get("source_doc_ids", []),
        )
    
    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """根据名称获取实体"""
        entity_id = self.name_to_id.get(name)
        if entity_id:
            return self.get_entity(entity_id)
        return None
    
    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """获取指定类型的所有实体"""
        entity_ids = self.entity_index.get(entity_type, set())
        return [self.get_entity(eid) for eid in entity_ids if self.get_entity(eid)]
    
    def get_neighbors(
        self,
        entity_id: str,
        relation_types: Optional[List[RelationType]] = None,
        direction: str = "both",  # "in", "out", "both"
    ) -> List[Tuple[Entity, Relation]]:
        """
        获取实体的邻居
        
        Args:
            entity_id: 实体ID
            relation_types: 过滤的关系类型
            direction: 方向（入边、出边、双向）
            
        Returns:
            [(邻居实体, 关系)] 列表
        """
        if not self.graph.has_node(entity_id):
            return []
        
        neighbors = []
        
        # 出边邻居
        if direction in ["out", "both"]:
            for _, target_id, edge_data in self.graph.out_edges(entity_id, data=True):
                if relation_types:
                    edge_type = edge_data.get("type", "")
                    if edge_type not in [rt.value for rt in relation_types]:
                        continue
                
                target_entity = self.get_entity(target_id)
                if target_entity:
                    relation = Relation(
                        id=edge_data.get("id", ""),
                        source_id=entity_id,
                        target_id=target_id,
                        type=RelationType(edge_data.get("type", "SIMILAR_TO")),
                        properties=edge_data.get("properties", {}),
                        weight=edge_data.get("weight", 1.0),
                        confidence=edge_data.get("confidence", 1.0),
                    )
                    neighbors.append((target_entity, relation))
        
        # 入边邻居
        if direction in ["in", "both"]:
            for source_id, _, edge_data in self.graph.in_edges(entity_id, data=True):
                if relation_types:
                    edge_type = edge_data.get("type", "")
                    if edge_type not in [rt.value for rt in relation_types]:
                        continue
                
                source_entity = self.get_entity(source_id)
                if source_entity:
                    relation = Relation(
                        id=edge_data.get("id", ""),
                        source_id=source_id,
                        target_id=entity_id,
                        type=RelationType(edge_data.get("type", "SIMILAR_TO")),
                        properties=edge_data.get("properties", {}),
                        weight=edge_data.get("weight", 1.0),
                        confidence=edge_data.get("confidence", 1.0),
                    )
                    neighbors.append((source_entity, relation))
        
        return neighbors
    
    def get_subgraph(
        self,
        center_entity_ids: List[str],
        max_hops: int = 2,
        max_nodes: int = 50,
        relation_types: Optional[List[RelationType]] = None,
    ) -> SubGraph:
        """
        获取以指定实体为中心的子图
        
        Args:
            center_entity_ids: 中心实体ID列表
            max_hops: 最大跳数
            max_nodes: 最大节点数
            relation_types: 过滤的关系类型
            
        Returns:
            子图对象
        """
        visited_nodes: Set[str] = set()
        visited_edges: Set[Tuple[str, str]] = set()
        
        # BFS 遍历
        current_level = set(center_entity_ids)
        
        for hop in range(max_hops + 1):
            if len(visited_nodes) >= max_nodes:
                break
            
            next_level = set()
            
            for node_id in current_level:
                if node_id in visited_nodes:
                    continue
                if not self.graph.has_node(node_id):
                    continue
                
                visited_nodes.add(node_id)
                
                if len(visited_nodes) >= max_nodes:
                    break
                
                # 获取邻居
                neighbors = self.get_neighbors(node_id, relation_types, "both")
                for neighbor_entity, relation in neighbors:
                    if neighbor_entity.id not in visited_nodes:
                        next_level.add(neighbor_entity.id)
                    
                    # 记录边
                    edge_key = (relation.source_id, relation.target_id)
                    if edge_key not in visited_edges:
                        visited_edges.add(edge_key)
            
            current_level = next_level
        
        # 构建子图
        entities = [self.get_entity(nid) for nid in visited_nodes if self.get_entity(nid)]
        relations = []
        
        for source_id, target_id in visited_edges:
            if self.graph.has_edge(source_id, target_id):
                edge_data = self.graph.edges[source_id, target_id]
                relations.append(Relation(
                    id=edge_data.get("id", f"{source_id}_{target_id}"),
                    source_id=source_id,
                    target_id=target_id,
                    type=RelationType(edge_data.get("type", "SIMILAR_TO")),
                    properties=edge_data.get("properties", {}),
                    weight=edge_data.get("weight", 1.0),
                    confidence=edge_data.get("confidence", 1.0),
                ))
        
        return SubGraph(
            entities=entities,
            relations=relations,
            center_entity_id=center_entity_ids[0] if center_entity_ids else None,
            hop_count=max_hops,
        )
    
    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 4,
    ) -> List[List[str]]:
        """
        查找两个实体之间的路径
        
        Args:
            source_id: 源实体ID
            target_id: 目标实体ID
            max_length: 最大路径长度
            
        Returns:
            路径列表（每个路径是实体ID列表）
        """
        if not self.graph.has_node(source_id) or not self.graph.has_node(target_id):
            return []
        
        try:
            # 使用 NetworkX 的简单路径查找
            paths = list(nx.all_simple_paths(
                self.graph.to_undirected(),
                source_id,
                target_id,
                cutoff=max_length,
            ))
            return paths[:10]  # 限制返回数量
        except nx.NetworkXNoPath:
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取图统计信息"""
        type_counts = defaultdict(int)
        for node_id in self.graph.nodes():
            node_type = self.graph.nodes[node_id].get("type", "Unknown")
            type_counts[node_type] += 1
        
        relation_counts = defaultdict(int)
        for _, _, data in self.graph.edges(data=True):
            rel_type = data.get("type", "Unknown")
            relation_counts[rel_type] += 1
        
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": dict(type_counts),
            "relation_types": dict(relation_counts),
            "density": nx.density(self.graph),
            "is_connected": nx.is_weakly_connected(self.graph) if self.graph.number_of_nodes() > 0 else True,
        }
    
    def save(self) -> bool:
        """保存图到磁盘"""
        try:
            # 保存图
            with open(self.graph_file, "wb") as f:
                pickle.dump(self.graph, f)
            
            # 保存元数据
            metadata = {
                "org_id": self.org_id,
                "entity_index": {k.value: list(v) for k, v in self.entity_index.items()},
                "name_to_id": self.name_to_id,
                "statistics": self.get_statistics(),
            }
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Graph saved to {self.graph_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save graph: {e}")
            return False
    
    def _load_graph(self) -> bool:
        """从磁盘加载图"""
        try:
            # 加载图
            with open(self.graph_file, "rb") as f:
                self.graph = pickle.load(f)
            
            # 加载元数据
            if self.metadata_file.exists():
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                
                # 恢复索引
                for type_str, entity_ids in metadata.get("entity_index", {}).items():
                    try:
                        entity_type = EntityType(type_str)
                        self.entity_index[entity_type] = set(entity_ids)
                    except ValueError:
                        pass
                
                self.name_to_id = metadata.get("name_to_id", {})
            else:
                # 重建索引
                self._rebuild_indices()
            
            logger.info(f"Graph loaded from {self.graph_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to load graph: {e}")
            self.graph = nx.DiGraph()
            self._initialize_predefined_entities()
            return False
    
    def _rebuild_indices(self):
        """重建索引"""
        self.entity_index.clear()
        self.name_to_id.clear()
        
        for node_id in self.graph.nodes():
            data = self.graph.nodes[node_id]
            try:
                entity_type = EntityType(data.get("type", "Keyword"))
                self.entity_index[entity_type].add(node_id)
            except ValueError:
                pass
            
            name = data.get("name", "")
            if name:
                self.name_to_id[name] = node_id
    
    def clear(self):
        """清空图"""
        self.graph.clear()
        self.entity_index.clear()
        self.name_to_id.clear()
        self._initialize_predefined_entities()
        logger.info("Graph cleared")
    
    def update_entity_embedding(self, entity_id: str, embedding: List[float]) -> bool:
        """更新实体的向量嵌入"""
        if not self.graph.has_node(entity_id):
            return False
        
        self.graph.nodes[entity_id]["embedding"] = embedding
        return True
    
    def get_entities_without_embedding(self) -> List[Entity]:
        """获取没有嵌入向量的实体"""
        entities = []
        for node_id in self.graph.nodes():
            data = self.graph.nodes[node_id]
            if data.get("embedding") is None:
                entity = self.get_entity(node_id)
                if entity:
                    entities.append(entity)
        return entities

