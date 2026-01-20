"""
销售场景知识图谱 Schema 定义

定义实体类型、关系类型和数据结构，针对销售培训场景优化。
"""
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel, Field
from datetime import datetime


class EntityType(str, Enum):
    """实体类型枚举"""
    PRODUCT = "Product"              # 产品/服务
    FEATURE = "Feature"              # 产品特性
    BENEFIT = "Benefit"              # 客户利益
    OBJECTION = "Objection"          # 客户异议
    RESPONSE = "Response"            # 异议应对话术
    SALES_STAGE = "SalesStage"       # 销售阶段
    CUSTOMER_TYPE = "CustomerType"   # 客户类型
    SCRIPT = "Script"                # 话术模板
    SCENARIO = "Scenario"            # 销售场景
    KEYWORD = "Keyword"              # 关键词/触发词
    DOCUMENT = "Document"            # 源文档


class RelationType(str, Enum):
    """关系类型枚举"""
    # 产品相关
    HAS_FEATURE = "HAS_FEATURE"              # 产品-特性
    PROVIDES_BENEFIT = "PROVIDES_BENEFIT"    # 特性-利益
    COMPETES_WITH = "COMPETES_WITH"          # 产品-产品（竞品）
    
    # 异议处理
    ADDRESSES = "ADDRESSES"                  # 话术-异议
    LEADS_TO = "LEADS_TO"                    # 异议-异议（连锁异议）
    COUNTERS = "COUNTERS"                    # 利益-异议（利益点反驳异议）
    
    # 阶段相关
    APPLIES_TO_STAGE = "APPLIES_TO_STAGE"    # 话术-阶段
    FOLLOWS = "FOLLOWS"                      # 阶段-阶段（阶段顺序）
    
    # 客户相关
    SUITS_CUSTOMER = "SUITS_CUSTOMER"        # 话术-客户类型
    PREFERS = "PREFERS"                      # 客户类型-特性
    
    # 话术相关
    SIMILAR_TO = "SIMILAR_TO"                # 话术-话术（相似）
    VARIANT_OF = "VARIANT_OF"                # 话术-话术（变体）
    USES_KEYWORD = "USES_KEYWORD"            # 话术-关键词
    
    # 文档溯源
    EXTRACTED_FROM = "EXTRACTED_FROM"        # 实体-文档
    MENTIONED_IN = "MENTIONED_IN"            # 实体-文档
    
    # 场景相关
    APPLICABLE_IN = "APPLICABLE_IN"          # 话术-场景
    TRIGGERS = "TRIGGERS"                    # 关键词-场景


class Entity(BaseModel):
    """实体节点"""
    id: str = Field(..., description="实体唯一标识")
    name: str = Field(..., description="实体名称")
    type: EntityType = Field(..., description="实体类型")
    properties: Dict[str, Any] = Field(default_factory=dict, description="实体属性")
    embedding: Optional[List[float]] = Field(default=None, description="实体向量嵌入")
    source_doc_ids: List[str] = Field(default_factory=list, description="来源文档ID")
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, Entity):
            return self.id == other.id
        return False


class Relation(BaseModel):
    """关系边"""
    id: str = Field(..., description="关系唯一标识")
    source_id: str = Field(..., description="源实体ID")
    target_id: str = Field(..., description="目标实体ID")
    type: RelationType = Field(..., description="关系类型")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系属性")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="关系权重")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
    source_doc_ids: List[str] = Field(default_factory=list, description="来源文档ID")
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True


class Triple(BaseModel):
    """三元组 (subject, relation, object)"""
    subject: Entity = Field(..., description="主体实体")
    relation: RelationType = Field(..., description="关系类型")
    object: Entity = Field(..., description="客体实体")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="提取置信度")
    source_text: Optional[str] = Field(default=None, description="来源文本片段")
    
    class Config:
        use_enum_values = True
    
    def to_relation(self, relation_id: str, doc_id: Optional[str] = None) -> Relation:
        """转换为 Relation 对象"""
        return Relation(
            id=relation_id,
            source_id=self.subject.id,
            target_id=self.object.id,
            type=self.relation,
            confidence=self.confidence,
            source_doc_ids=[doc_id] if doc_id else [],
            properties={"source_text": self.source_text} if self.source_text else {},
        )


class SubGraph(BaseModel):
    """子图结构"""
    entities: List[Entity] = Field(default_factory=list, description="实体列表")
    relations: List[Relation] = Field(default_factory=list, description="关系列表")
    center_entity_id: Optional[str] = Field(default=None, description="中心实体ID")
    hop_count: int = Field(default=0, description="跳数")
    relevance_score: float = Field(default=0.0, description="相关性分数")
    
    def get_entity_ids(self) -> Set[str]:
        """获取所有实体ID"""
        return {e.id for e in self.entities}
    
    def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """根据ID获取实体"""
        for e in self.entities:
            if e.id == entity_id:
                return e
        return None
    
    def to_text(self) -> str:
        """将子图转换为文本描述（用于LLM上下文）"""
        lines = []
        
        # 实体描述
        lines.append("【相关实体】")
        for entity in self.entities:
            props = ", ".join(f"{k}={v}" for k, v in entity.properties.items() if v)
            if props:
                lines.append(f"- {entity.name} ({entity.type}): {props}")
            else:
                lines.append(f"- {entity.name} ({entity.type})")
        
        # 关系描述
        lines.append("\n【实体关系】")
        entity_map = {e.id: e.name for e in self.entities}
        for rel in self.relations:
            source_name = entity_map.get(rel.source_id, rel.source_id)
            target_name = entity_map.get(rel.target_id, rel.target_id)
            lines.append(f"- {source_name} --[{rel.type}]--> {target_name}")
        
        return "\n".join(lines)


class CommunitySummary(BaseModel):
    """社区摘要"""
    community_id: str = Field(..., description="社区ID")
    level: int = Field(default=0, description="层次级别（0为最细粒度）")
    title: str = Field(..., description="社区标题")
    summary: str = Field(..., description="社区摘要")
    key_entities: List[str] = Field(default_factory=list, description="关键实体名称")
    entity_ids: List[str] = Field(default_factory=list, description="包含的实体ID")
    size: int = Field(default=0, description="社区大小（实体数量）")
    embedding: Optional[List[float]] = Field(default=None, description="摘要向量嵌入")
    relevance_score: float = Field(default=0.0, description="检索相关性分数")
    
    def to_context(self) -> str:
        """转换为上下文文本"""
        entities_str = ", ".join(self.key_entities[:5])
        return f"【{self.title}】\n{self.summary}\n关键实体: {entities_str}"


class GraphRAGResult(BaseModel):
    """GraphRAG 检索结果"""
    query: str = Field(..., description="原始查询")
    mode: str = Field(default="hybrid", description="检索模式")
    
    # 局部检索结果
    local_subgraphs: List[SubGraph] = Field(default_factory=list, description="局部子图列表")
    
    # 全局检索结果
    community_summaries: List[CommunitySummary] = Field(default_factory=list, description="社区摘要列表")
    
    # 融合后的上下文
    context: str = Field(default="", description="融合后的上下文文本")
    
    # 推理路径（可解释性）
    reasoning_paths: List[List[str]] = Field(default_factory=list, description="推理路径")
    
    # 元数据
    total_entities: int = Field(default=0, description="涉及的实体总数")
    total_relations: int = Field(default=0, description="涉及的关系总数")
    retrieval_time_ms: float = Field(default=0.0, description="检索耗时（毫秒）")
    
    def build_context(self, max_tokens: int = 2000) -> str:
        """构建上下文文本"""
        context_parts = []
        
        # 添加社区摘要（全局视角）
        if self.community_summaries:
            context_parts.append("=== 全局知识摘要 ===")
            for cs in self.community_summaries[:3]:
                context_parts.append(cs.to_context())
        
        # 添加子图信息（局部细节）
        if self.local_subgraphs:
            context_parts.append("\n=== 相关知识细节 ===")
            for sg in self.local_subgraphs[:3]:
                context_parts.append(sg.to_text())
        
        # 添加推理路径
        if self.reasoning_paths:
            context_parts.append("\n=== 推理路径 ===")
            for i, path in enumerate(self.reasoning_paths[:3], 1):
                context_parts.append(f"{i}. {' -> '.join(path)}")
        
        self.context = "\n\n".join(context_parts)
        return self.context


# 预定义的销售阶段实体
PREDEFINED_SALES_STAGES = [
    Entity(
        id="stage_opening",
        name="破冰建联",
        type=EntityType.SALES_STAGE,
        properties={"stage_code": "OPENING", "order": 1, "goal": "建立信任关系，获取客户基本信息"},
    ),
    Entity(
        id="stage_needs_discovery",
        name="需求挖掘",
        type=EntityType.SALES_STAGE,
        properties={"stage_code": "NEEDS_DISCOVERY", "order": 2, "goal": "挖掘客户核心需求和痛点"},
    ),
    Entity(
        id="stage_product_intro",
        name="产品介绍",
        type=EntityType.SALES_STAGE,
        properties={"stage_code": "PRODUCT_INTRO", "order": 3, "goal": "针对需求介绍产品价值"},
    ),
    Entity(
        id="stage_objection_handling",
        name="异议处理",
        type=EntityType.SALES_STAGE,
        properties={"stage_code": "OBJECTION_HANDLING", "order": 4, "goal": "有效处理客户异议"},
    ),
    Entity(
        id="stage_closing",
        name="促单成交",
        type=EntityType.SALES_STAGE,
        properties={"stage_code": "CLOSING", "order": 5, "goal": "推动成交或明确下一步"},
    ),
]

# 预定义的客户类型实体
PREDEFINED_CUSTOMER_TYPES = [
    Entity(
        id="customer_price_sensitive",
        name="价格敏感型",
        type=EntityType.CUSTOMER_TYPE,
        properties={"description": "注重性价比，对价格敏感", "keywords": ["便宜", "优惠", "划算", "打折"]},
    ),
    Entity(
        id="customer_quality_first",
        name="品质优先型",
        type=EntityType.CUSTOMER_TYPE,
        properties={"description": "注重品质和服务，愿意为好产品付费", "keywords": ["品质", "服务", "保障", "专业"]},
    ),
    Entity(
        id="customer_risk_averse",
        name="风险规避型",
        type=EntityType.CUSTOMER_TYPE,
        properties={"description": "谨慎保守，担心风险", "keywords": ["安全", "风险", "保障", "稳定"]},
    ),
    Entity(
        id="customer_efficiency_oriented",
        name="效率导向型",
        type=EntityType.CUSTOMER_TYPE,
        properties={"description": "注重效率，决策快速", "keywords": ["快速", "方便", "简单", "高效"]},
    ),
    Entity(
        id="customer_relationship_focused",
        name="关系导向型",
        type=EntityType.CUSTOMER_TYPE,
        properties={"description": "注重人际关系和信任", "keywords": ["信任", "朋友", "推荐", "口碑"]},
    ),
]

# 常见异议类型
COMMON_OBJECTION_TEMPLATES = [
    {"name": "价格太贵", "category": "price", "keywords": ["贵", "价格", "便宜", "优惠"]},
    {"name": "暂时不需要", "category": "need", "keywords": ["不需要", "用不上", "暂时"]},
    {"name": "需要考虑", "category": "decision", "keywords": ["考虑", "想想", "商量"]},
    {"name": "已有竞品", "category": "competition", "keywords": ["已经有", "在用", "其他"]},
    {"name": "担心风险", "category": "risk", "keywords": ["风险", "安全", "担心", "怕"]},
    {"name": "不信任", "category": "trust", "keywords": ["不信", "骗", "假的"]},
]


def get_stage_entity_by_code(stage_code: str) -> Optional[Entity]:
    """根据阶段代码获取预定义的阶段实体"""
    for stage in PREDEFINED_SALES_STAGES:
        if stage.properties.get("stage_code") == stage_code:
            return stage
    return None


def get_customer_type_by_keywords(text: str) -> List[Entity]:
    """根据文本关键词匹配客户类型"""
    matched = []
    text_lower = text.lower()
    for customer_type in PREDEFINED_CUSTOMER_TYPES:
        keywords = customer_type.properties.get("keywords", [])
        if any(kw in text_lower for kw in keywords):
            matched.append(customer_type)
    return matched

