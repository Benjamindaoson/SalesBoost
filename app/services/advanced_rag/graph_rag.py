"""
GraphRAG Service - 知识图谱增强检索
模拟 Neo4j + GraphRAG 的图谱推理能力
"""
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class GraphNode:
    id: str
    type: str  # "Product", "Benefit", "Objection", "Script"
    content: str
    metadata: Dict[str, Any]

@dataclass
class GraphEdge:
    source: str
    target: str
    relation: str  # "HAS_BENEFIT", "HANDLES_OBJECTION", "REQUIRES_CONDITION"

class GraphRAGService:
    """
    轻量级内存图谱服务 (Mock Neo4j)
    支持多跳推理：Entity -> Relation -> Entity
    """
    
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.adjacency: Dict[str, List[GraphEdge]] = {}
        
        # 初始化一些示例数据 (Sales Knowledge Graph)
        self._init_demo_graph()
        
    def _init_demo_graph(self):
        """初始化示例图谱数据"""
        # 节点：产品
        self.add_node("VisaPlatinum", "Product", "Visa联名高端商务卡", {"alias": ["白金卡", "商务卡"]})
        
        # 节点：权益
        self.add_node("AirportLounge", "Benefit", "无限次机场贵宾厅", {"value": "high"})
        self.add_node("Golf", "Benefit", "每年6次高尔夫果岭", {"value": "high"})
        self.add_node("Insurance", "Benefit", "1000万航空意外险", {"value": "medium"})
        
        # 节点：限制条件
        self.add_node("LoungeCondition", "Condition", "需提前24小时预约", {})
        self.add_node("AnnualFee", "Condition", "年费2000元", {})
        self.add_node("FeeWaiver", "Condition", "年消费满20万免次年", {})
        
        # 节点：异议
        self.add_node("Obj_TooExpensive", "Objection", "年费太贵了", {})
        self.add_node("Obj_NoTravel", "Objection", "我不常出差", {})
        
        # 节点：话术
        self.add_node("Script_FeeValue", "Script", "虽然有年费，但光是无限次贵宾厅和高尔夫权益的价值就远超2000元了。", {})
        self.add_node("Script_FeeWaiver", "Script", "其实只要您平时把商务支出都用这张卡，一年20万很容易达到，相当于免费享受顶级权益。", {})
        
        # 边：关系
        self.add_edge("VisaPlatinum", "AirportLounge", "HAS_BENEFIT")
        self.add_edge("VisaPlatinum", "Golf", "HAS_BENEFIT")
        self.add_edge("VisaPlatinum", "Insurance", "HAS_BENEFIT")
        self.add_edge("VisaPlatinum", "AnnualFee", "HAS_COST")
        
        self.add_edge("AirportLounge", "LoungeCondition", "REQUIRES")
        self.add_edge("AnnualFee", "FeeWaiver", "CAN_BE_WAIVED")
        
        self.add_edge("Obj_TooExpensive", "AnnualFee", "TARGETS")
        self.add_edge("Script_FeeValue", "Obj_TooExpensive", "HANDLES")
        self.add_edge("Script_FeeWaiver", "Obj_TooExpensive", "HANDLES")
        self.add_edge("Script_FeeValue", "AirportLounge", "REFERENCES")
        
    def add_node(self, id: str, type: str, content: str, metadata: Dict):
        self.nodes[id] = GraphNode(id, type, content, metadata)
        if id not in self.adjacency:
            self.adjacency[id] = []
            
    def add_edge(self, source: str, target: str, relation: str):
        edge = GraphEdge(source, target, relation)
        self.edges.append(edge)
        if source in self.adjacency:
            self.adjacency[source].append(edge)
            
    async def search(self, query: str, hops: int = 2) -> List[Dict[str, Any]]:
        """
        图谱检索
        1. 实体链接 (Entity Linking)
        2. 子图遍历 (Subgraph Traversal)
        """
        # 1. 简单的关键词实体链接
        start_nodes = []
        for node_id, node in self.nodes.items():
            if node.content in query or any(alias in query for alias in node.metadata.get("alias", [])):
                start_nodes.append(node)
        
        if not start_nodes:
            return []
            
        results = []
        visited = set()
        
        # 2. 遍历
        for start_node in start_nodes:
            path_results = self._traverse(start_node, hops, visited)
            results.extend(path_results)
            
        return results

    def _traverse(self, start_node: GraphNode, max_hops: int, visited: Set[str]) -> List[Dict[str, Any]]:
        """BFS 遍历获取上下文"""
        results = []
        queue = [(start_node, 0, [])] # (node, depth, path)
        
        visited.add(start_node.id)
        
        while queue:
            current_node, depth, path = queue.pop(0)
            
            # 将当前节点加入结果
            results.append({
                "content": current_node.content,
                "type": current_node.type,
                "metadata": current_node.metadata,
                "path": path,
                "depth": depth
            })
            
            if depth >= max_hops:
                continue
                
            if current_node.id in self.adjacency:
                for edge in self.adjacency[current_node.id]:
                    target_node = self.nodes.get(edge.target)
                    if target_node and target_node.id not in visited:
                        visited.add(target_node.id)
                        new_path = path + [edge.relation]
                        queue.append((target_node, depth + 1, new_path))
                        
        return results

    async def get_objection_handling(self, objection_query: str) -> List[str]:
        """专门用于异议处理的图谱检索"""
        # 找到异议节点
        objection_node = None
        for node in self.nodes.values():
            if node.type == "Objection" and (node.content in objection_query or objection_query in node.content):
                objection_node = node
                break
        
        if not objection_node:
            return []
            
        # 查找处理该异议的 Script 节点
        scripts = []
        # 反向查找（模拟）- 在实际图数据库中可以直接查询
        # 这里遍历边
        for edge in self.edges:
            if edge.target == objection_node.id and edge.relation == "HANDLES":
                source_node = self.nodes.get(edge.source)
                if source_node and source_node.type == "Script":
                    scripts.append(source_node.content)
                    
        return scripts
