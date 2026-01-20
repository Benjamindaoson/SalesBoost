"""
社区检测器 - 基于图结构的社区发现和层次化摘要生成

使用 Leiden/Louvain 算法进行社区检测，生成多层次的社区摘要。
"""
import logging
import hashlib
from typing import List, Dict, Any, Optional, Set, TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    import networkx as nx

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

try:
    from community import community_louvain
    HAS_LOUVAIN = True
except ImportError:
    HAS_LOUVAIN = False

from app.services.graph_rag.graph_schema import (
    Entity,
    EntityType,
    CommunitySummary,
)
from app.services.graph_rag.graph_builder import SalesKnowledgeGraph

logger = logging.getLogger(__name__)


# 社区摘要生成 Prompt
COMMUNITY_SUMMARY_PROMPT = """请为以下销售知识社区生成简洁的摘要。

【社区实体】
{entities}

【社区关系】
{relations}

【任务】
1. 生成一个简短的社区标题（10字以内）
2. 生成社区摘要（50-100字），描述这个社区的主要内容和用途
3. 列出3-5个关键实体名称

【输出格式】（JSON）
{{
    "title": "社区标题",
    "summary": "社区摘要内容...",
    "key_entities": ["实体1", "实体2", "实体3"]
}}"""


class CommunityDetector:
    """
    社区检测器
    
    功能：
    - 使用 Louvain/Leiden 算法检测社区
    - 生成层次化的社区结构
    - 为每个社区生成摘要
    """
    
    def __init__(
        self,
        knowledge_graph: SalesKnowledgeGraph,
        llm_client=None,
        min_community_size: int = 3,
        resolution: float = 1.0,
    ):
        """
        初始化社区检测器
        
        Args:
            knowledge_graph: 知识图谱实例
            llm_client: LLM 客户端（用于生成摘要）
            min_community_size: 最小社区大小
            resolution: 社区检测分辨率（越大社区越小）
        """
        self.kg = knowledge_graph
        self.llm_client = llm_client
        self.min_community_size = min_community_size
        self.resolution = resolution
        
        # 社区缓存
        self.communities: Dict[int, Dict[str, Set[str]]] = {}  # level -> {community_id: {entity_ids}}
        self.community_summaries: Dict[str, CommunitySummary] = {}  # community_id -> summary
    
    def detect_communities(self, levels: int = 2) -> Dict[int, Dict[str, Set[str]]]:
        """
        检测社区（多层次）
        
        Args:
            levels: 层次数量
            
        Returns:
            {level: {community_id: {entity_ids}}}
        """
        if not HAS_NETWORKX:
            logger.error("NetworkX is required for community detection")
            return {}
        
        graph = self.kg.graph
        
        if graph.number_of_nodes() == 0:
            logger.warning("Empty graph, no communities to detect")
            return {}
        
        # 转换为无向图
        undirected = graph.to_undirected()
        
        self.communities = {}
        
        for level in range(levels):
            if level == 0:
                # 第一层：使用 Louvain 算法
                communities = self._detect_louvain(undirected, self.resolution * (level + 1))
            else:
                # 更高层：在上一层基础上合并
                communities = self._merge_communities(self.communities.get(level - 1, {}))
            
            # 过滤小社区
            filtered = {
                cid: members for cid, members in communities.items()
                if len(members) >= self.min_community_size
            }
            
            self.communities[level] = filtered
            logger.info(f"Level {level}: {len(filtered)} communities detected")
        
        return self.communities
    
    def _detect_louvain(
        self,
        graph: "nx.Graph",
        resolution: float = 1.0,
    ) -> Dict[str, Set[str]]:
        """使用 Louvain 算法检测社区"""
        if HAS_LOUVAIN:
            try:
                # 使用 python-louvain 库
                partition = community_louvain.best_partition(
                    graph,
                    resolution=resolution,
                    random_state=42,
                )
                
                # 转换格式
                communities = defaultdict(set)
                for node_id, community_id in partition.items():
                    communities[f"c_{community_id}"].add(node_id)
                
                return dict(communities)
            except Exception as e:
                logger.warning(f"Louvain detection failed: {e}, using fallback")
        
        # 降级方案：基于连通分量
        return self._detect_by_components(graph)
    
    def _detect_by_components(self, graph: "nx.Graph") -> Dict[str, Set[str]]:
        """基于连通分量的简单社区检测（降级方案）"""
        communities = {}
        
        # 获取连通分量
        components = list(nx.connected_components(graph))
        
        for i, component in enumerate(components):
            if len(component) >= self.min_community_size:
                communities[f"comp_{i}"] = component
        
        # 如果只有一个大分量，尝试基于节点类型分割
        if len(communities) == 1 and len(list(communities.values())[0]) > 20:
            return self._split_by_entity_type(graph)
        
        return communities
    
    def _split_by_entity_type(self, graph: "nx.Graph") -> Dict[str, Set[str]]:
        """基于实体类型分割社区"""
        type_groups = defaultdict(set)
        
        for node_id in graph.nodes():
            node_data = self.kg.graph.nodes.get(node_id, {})
            node_type = node_data.get("type", "Unknown")
            type_groups[node_type].add(node_id)
        
        communities = {}
        for i, (type_name, members) in enumerate(type_groups.items()):
            if len(members) >= self.min_community_size:
                communities[f"type_{type_name}_{i}"] = members
        
        return communities
    
    def _merge_communities(
        self,
        lower_communities: Dict[str, Set[str]],
    ) -> Dict[str, Set[str]]:
        """合并下层社区形成上层社区"""
        if not lower_communities:
            return {}
        
        # 简单策略：基于社区间的边连接合并
        community_list = list(lower_communities.items())
        merged = {}
        used = set()
        
        for i, (cid1, members1) in enumerate(community_list):
            if cid1 in used:
                continue
            
            merged_members = set(members1)
            merged_ids = [cid1]
            
            # 查找可以合并的社区
            for j, (cid2, members2) in enumerate(community_list[i+1:], i+1):
                if cid2 in used:
                    continue
                
                # 计算社区间的连接强度
                connections = self._count_inter_community_edges(members1, members2)
                
                # 如果连接足够强，合并
                threshold = min(len(members1), len(members2)) * 0.3
                if connections >= threshold:
                    merged_members.update(members2)
                    merged_ids.append(cid2)
                    used.add(cid2)
            
            used.add(cid1)
            merged_id = f"merged_{'_'.join(merged_ids)}"
            merged[merged_id] = merged_members
        
        return merged
    
    def _count_inter_community_edges(
        self,
        members1: Set[str],
        members2: Set[str],
    ) -> int:
        """计算两个社区之间的边数"""
        count = 0
        for m1 in members1:
            for m2 in members2:
                if self.kg.graph.has_edge(m1, m2) or self.kg.graph.has_edge(m2, m1):
                    count += 1
        return count
    
    async def generate_summaries(
        self,
        level: int = 0,
        force_regenerate: bool = False,
    ) -> List[CommunitySummary]:
        """
        为指定层级的社区生成摘要
        
        Args:
            level: 社区层级
            force_regenerate: 是否强制重新生成
            
        Returns:
            社区摘要列表
        """
        if level not in self.communities:
            logger.warning(f"No communities at level {level}")
            return []
        
        summaries = []
        
        for community_id, member_ids in self.communities[level].items():
            # 检查缓存
            cache_key = f"{level}_{community_id}"
            if not force_regenerate and cache_key in self.community_summaries:
                summaries.append(self.community_summaries[cache_key])
                continue
            
            # 生成摘要
            summary = await self._generate_community_summary(
                community_id, member_ids, level
            )
            
            if summary:
                self.community_summaries[cache_key] = summary
                summaries.append(summary)
        
        return summaries
    
    async def _generate_community_summary(
        self,
        community_id: str,
        member_ids: Set[str],
        level: int,
    ) -> Optional[CommunitySummary]:
        """为单个社区生成摘要"""
        # 获取社区实体
        entities = []
        for mid in member_ids:
            entity = self.kg.get_entity(mid)
            if entity:
                entities.append(entity)
        
        if not entities:
            return None
        
        # 获取社区内的关系
        relations = []
        member_set = set(member_ids)
        for source_id in member_ids:
            for _, target_id, data in self.kg.graph.out_edges(source_id, data=True):
                if target_id in member_set:
                    relations.append({
                        "source": self.kg.graph.nodes[source_id].get("name", source_id),
                        "target": self.kg.graph.nodes[target_id].get("name", target_id),
                        "type": data.get("type", "RELATED"),
                    })
        
        # 使用 LLM 生成摘要
        if self.llm_client:
            summary = await self._generate_summary_with_llm(entities, relations)
        else:
            summary = self._generate_summary_fallback(entities, relations)
        
        if summary:
            summary.community_id = f"{level}_{community_id}"
            summary.level = level
            summary.entity_ids = list(member_ids)
            summary.size = len(member_ids)
        
        return summary
    
    async def _generate_summary_with_llm(
        self,
        entities: List[Entity],
        relations: List[Dict],
    ) -> Optional[CommunitySummary]:
        """使用 LLM 生成社区摘要"""
        # 构建实体描述
        entities_desc = "\n".join([
            f"- {e.name} ({e.type})" for e in entities[:20]
        ])
        
        # 构建关系描述
        relations_desc = "\n".join([
            f"- {r['source']} --[{r['type']}]--> {r['target']}"
            for r in relations[:20]
        ])
        
        prompt = COMMUNITY_SUMMARY_PROMPT.format(
            entities=entities_desc,
            relations=relations_desc if relations_desc else "（无显式关系）",
        )
        
        try:
            import json
            import re
            
            if hasattr(self.llm_client, 'chat'):
                response = self.llm_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                )
                result_text = response.choices[0].message.content
            else:
                return self._generate_summary_fallback(entities, relations)
            
            # 解析 JSON
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                result = json.loads(json_match.group())
                return CommunitySummary(
                    community_id="",  # 稍后填充
                    level=0,
                    title=result.get("title", "未命名社区"),
                    summary=result.get("summary", ""),
                    key_entities=result.get("key_entities", [e.name for e in entities[:5]]),
                )
        except Exception as e:
            logger.error(f"LLM summary generation failed: {e}")
        
        return self._generate_summary_fallback(entities, relations)
    
    def _generate_summary_fallback(
        self,
        entities: List[Entity],
        relations: List[Dict],
    ) -> CommunitySummary:
        """降级摘要生成（不使用 LLM）"""
        # 统计实体类型
        type_counts = defaultdict(int)
        for e in entities:
            type_counts[e.type] += 1
        
        # 确定主要类型
        main_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else "知识"
        
        # 生成标题
        type_names = {
            EntityType.PRODUCT: "产品",
            EntityType.FEATURE: "特性",
            EntityType.BENEFIT: "利益",
            EntityType.OBJECTION: "异议处理",
            EntityType.RESPONSE: "应对话术",
            EntityType.SALES_STAGE: "销售阶段",
            EntityType.CUSTOMER_TYPE: "客户类型",
            EntityType.SCRIPT: "话术",
        }
        title = f"{type_names.get(main_type, '销售')}知识集合"
        
        # 生成摘要
        entity_names = [e.name for e in entities[:5]]
        summary = f"包含 {len(entities)} 个相关实体，主要涉及：{', '.join(entity_names)}等。"
        
        if relations:
            summary += f" 共有 {len(relations)} 条关系连接。"
        
        return CommunitySummary(
            community_id="",
            level=0,
            title=title,
            summary=summary,
            key_entities=entity_names,
        )
    
    def get_community_for_entity(self, entity_id: str, level: int = 0) -> Optional[str]:
        """获取实体所属的社区"""
        if level not in self.communities:
            return None
        
        for community_id, members in self.communities[level].items():
            if entity_id in members:
                return community_id
        
        return None
    
    def get_related_communities(
        self,
        community_id: str,
        level: int = 0,
    ) -> List[str]:
        """获取与指定社区相关的社区"""
        if level not in self.communities:
            return []
        
        target_members = self.communities[level].get(community_id, set())
        if not target_members:
            return []
        
        related = []
        for cid, members in self.communities[level].items():
            if cid == community_id:
                continue
            
            # 检查是否有边连接
            connections = self._count_inter_community_edges(target_members, members)
            if connections > 0:
                related.append((cid, connections))
        
        # 按连接数排序
        related.sort(key=lambda x: x[1], reverse=True)
        return [cid for cid, _ in related[:5]]
    
    def search_communities_by_embedding(
        self,
        query_embedding: List[float],
        top_k: int = 3,
        level: int = 0,
    ) -> List[CommunitySummary]:
        """
        基于向量相似度搜索社区
        
        Args:
            query_embedding: 查询向量
            top_k: 返回数量
            level: 社区层级
            
        Returns:
            相关社区摘要列表
        """
        if not self.community_summaries:
            logger.warning("No community summaries available")
            return []
        
        # 过滤指定层级的摘要
        level_summaries = [
            s for s in self.community_summaries.values()
            if s.level == level and s.embedding is not None
        ]
        
        if not level_summaries:
            # 如果没有嵌入，返回所有摘要
            return list(self.community_summaries.values())[:top_k]
        
        # 计算相似度
        import numpy as np
        query_vec = np.array(query_embedding)
        
        scored = []
        for summary in level_summaries:
            if summary.embedding:
                summary_vec = np.array(summary.embedding)
                # 余弦相似度
                similarity = np.dot(query_vec, summary_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(summary_vec) + 1e-8
                )
                summary.relevance_score = float(similarity)
                scored.append(summary)
        
        # 排序
        scored.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored[:top_k]
    
    async def update_summary_embeddings(self, embedding_fn) -> int:
        """
        更新社区摘要的向量嵌入
        
        Args:
            embedding_fn: 嵌入函数 (text) -> List[float]
            
        Returns:
            更新的摘要数量
        """
        updated = 0
        
        for summary in self.community_summaries.values():
            if summary.embedding is None:
                try:
                    # 使用摘要文本生成嵌入
                    text = f"{summary.title}. {summary.summary}"
                    embedding = embedding_fn([text])
                    if embedding:
                        summary.embedding = embedding[0]
                        updated += 1
                except Exception as e:
                    logger.error(f"Failed to generate embedding for community {summary.community_id}: {e}")
        
        logger.info(f"Updated embeddings for {updated} community summaries")
        return updated

