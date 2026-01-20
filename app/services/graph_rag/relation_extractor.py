"""
关系提取器 - 从销售文档中提取实体间关系三元组

使用 LLM 进行关系抽取，针对销售场景优化。
"""
import logging
import re
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from app.services.graph_rag.graph_schema import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    Triple,
    COMMON_OBJECTION_TEMPLATES,
    get_stage_entity_by_code,
    get_customer_type_by_keywords,
)

logger = logging.getLogger(__name__)


# 销售场景关系提取 Prompt
RELATION_EXTRACTION_PROMPT = """你是一个专业的销售知识图谱构建专家。请从以下销售文档中提取实体和关系。

【文档内容】
{text}

【已识别的实体】
{entities}

【任务说明】
请识别文档中的实体关系，输出 JSON 格式的三元组列表。

【实体类型】
- Product: 产品/服务
- Feature: 产品特性
- Benefit: 客户利益
- Objection: 客户异议
- Response: 异议应对话术
- SalesStage: 销售阶段 (OPENING/NEEDS_DISCOVERY/PRODUCT_INTRO/OBJECTION_HANDLING/CLOSING)
- CustomerType: 客户类型
- Script: 话术模板
- Keyword: 关键词

【关系类型】
- HAS_FEATURE: 产品具有某特性
- PROVIDES_BENEFIT: 特性提供某利益
- ADDRESSES: 话术/应对策略针对某异议
- LEADS_TO: 某异议可能引发另一异议
- APPLIES_TO_STAGE: 话术适用于某销售阶段
- SUITS_CUSTOMER: 话术适合某类客户
- SIMILAR_TO: 两个话术/策略相似
- COUNTERS: 某利益点可反驳某异议
- USES_KEYWORD: 话术使用某关键词

【输出格式】
{{
    "new_entities": [
        {{"name": "实体名", "type": "EntityType", "properties": {{"key": "value"}}}}
    ],
    "relations": [
        {{
            "subject": "主体实体名",
            "relation": "RelationType",
            "object": "客体实体名",
            "confidence": 0.9,
            "evidence": "支持该关系的原文片段"
        }}
    ]
}}

请确保：
1. 只提取文档中明确存在的关系，不要推测
2. 每个关系都要有原文证据支持
3. 置信度反映关系的明确程度（0.5-1.0）
4. 重点关注销售相关的实体和关系"""


class RelationExtractor:
    """
    关系提取器
    
    从销售文档中提取实体间关系，构建知识图谱三元组。
    支持 LLM 提取和规则提取两种模式。
    """
    
    def __init__(self, llm_client=None, use_rules: bool = True):
        """
        初始化关系提取器
        
        Args:
            llm_client: LLM 客户端（OpenAI 兼容）
            use_rules: 是否启用规则提取（作为 LLM 的补充）
        """
        self.llm_client = llm_client
        self.use_rules = use_rules
        
        # 预编译正则表达式
        self._compile_patterns()
    
    def _compile_patterns(self):
        """预编译关系提取正则模式"""
        # 异议-应对模式
        self.objection_response_patterns = [
            # "当客户说XXX时，可以回应XXX"
            re.compile(r'当客户(?:说|提出|表示)[「""]?([^「""]+)[」""]?时[，,](?:可以|应该|建议)?(?:回应|回答|说)[「""]?([^「""]+)[」""]?'),
            # "针对XXX异议，话术：XXX"
            re.compile(r'针对[「""]?([^「""]+)[」""]?(?:异议|顾虑|问题)[，,：:](?:话术|回应|应对)[：:]?\s*[「""]?([^「""]+)[」""]?'),
            # "客户：XXX 销售：XXX"
            re.compile(r'客户[：:]\s*[「""]?([^「""]+)[」""]?\s*销售[：:]\s*[「""]?([^「""]+)[」""]?'),
        ]
        
        # 产品-特性模式
        self.product_feature_patterns = [
            # "XXX产品具有XXX功能"
            re.compile(r'([^\s，,。]+(?:产品|服务|卡|账户))(?:具有|拥有|包含|提供)[「""]?([^「""，,。]+)[」""]?(?:功能|特性|特点)?'),
            # "XXX的特点是XXX"
            re.compile(r'([^\s，,。]+)的(?:特点|特性|优势|亮点)(?:是|包括|有)[「""]?([^「""，,。]+)[」""]?'),
        ]
        
        # 特性-利益模式
        self.feature_benefit_patterns = [
            # "XXX可以帮助客户XXX"
            re.compile(r'([^\s，,。]+)(?:可以|能够|帮助)(?:客户|用户|您)?([^\s，,。]+)'),
            # "通过XXX，实现XXX"
            re.compile(r'通过([^\s，,。]+)[，,](?:实现|达到|获得)([^\s，,。]+)'),
        ]
        
        # 阶段关键词映射
        self.stage_keywords = {
            "OPENING": ["开场", "破冰", "建联", "问候", "自我介绍"],
            "NEEDS_DISCOVERY": ["需求", "挖掘", "了解", "痛点", "问题"],
            "PRODUCT_INTRO": ["产品", "介绍", "功能", "特点", "优势"],
            "OBJECTION_HANDLING": ["异议", "顾虑", "担心", "反对", "处理"],
            "CLOSING": ["成交", "促单", "签约", "下单", "购买"],
        }
    
    async def extract_relations(
        self,
        text: str,
        entities: List[Entity],
        doc_id: Optional[str] = None,
    ) -> Tuple[List[Entity], List[Triple]]:
        """
        从文本中提取实体关系
        
        Args:
            text: 文档文本
            entities: 已识别的实体列表
            doc_id: 文档ID
            
        Returns:
            (新发现的实体列表, 三元组列表)
        """
        all_new_entities = []
        all_triples = []
        
        # 1. 规则提取（快速、确定性高）
        if self.use_rules:
            rule_entities, rule_triples = self._extract_by_rules(text, entities, doc_id)
            all_new_entities.extend(rule_entities)
            all_triples.extend(rule_triples)
        
        # 2. LLM 提取（更全面、语义理解强）
        if self.llm_client:
            try:
                llm_entities, llm_triples = await self._extract_by_llm(text, entities, doc_id)
                
                # 合并去重
                existing_entity_names = {e.name for e in entities + all_new_entities}
                for entity in llm_entities:
                    if entity.name not in existing_entity_names:
                        all_new_entities.append(entity)
                        existing_entity_names.add(entity.name)
                
                # 去重三元组
                existing_triples = {
                    (t.subject.name, t.relation, t.object.name) 
                    for t in all_triples
                }
                for triple in llm_triples:
                    key = (triple.subject.name, triple.relation, triple.object.name)
                    if key not in existing_triples:
                        all_triples.append(triple)
                        existing_triples.add(key)
                        
            except Exception as e:
                logger.error(f"LLM relation extraction failed: {e}")
        
        logger.info(f"Extracted {len(all_new_entities)} new entities, {len(all_triples)} triples")
        return all_new_entities, all_triples
    
    def _extract_by_rules(
        self,
        text: str,
        entities: List[Entity],
        doc_id: Optional[str] = None,
    ) -> Tuple[List[Entity], List[Triple]]:
        """规则提取关系"""
        new_entities = []
        triples = []
        
        entity_map = {e.name: e for e in entities}
        
        # 1. 提取异议-应对关系
        for pattern in self.objection_response_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if len(match) >= 2:
                    objection_text, response_text = match[0].strip(), match[1].strip()
                    
                    # 创建或获取异议实体
                    objection_entity = entity_map.get(objection_text)
                    if not objection_entity:
                        objection_entity = self._create_entity(
                            objection_text, EntityType.OBJECTION, doc_id
                        )
                        new_entities.append(objection_entity)
                        entity_map[objection_text] = objection_entity
                    
                    # 创建或获取应对话术实体
                    response_entity = entity_map.get(response_text)
                    if not response_entity:
                        response_entity = self._create_entity(
                            response_text, EntityType.RESPONSE, doc_id
                        )
                        new_entities.append(response_entity)
                        entity_map[response_text] = response_entity
                    
                    # 创建三元组
                    triples.append(Triple(
                        subject=response_entity,
                        relation=RelationType.ADDRESSES,
                        object=objection_entity,
                        confidence=0.85,
                        source_text=f"{objection_text} -> {response_text}",
                    ))
        
        # 2. 提取产品-特性关系
        for pattern in self.product_feature_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if len(match) >= 2:
                    product_text, feature_text = match[0].strip(), match[1].strip()
                    
                    product_entity = entity_map.get(product_text)
                    if not product_entity:
                        product_entity = self._create_entity(
                            product_text, EntityType.PRODUCT, doc_id
                        )
                        new_entities.append(product_entity)
                        entity_map[product_text] = product_entity
                    
                    feature_entity = entity_map.get(feature_text)
                    if not feature_entity:
                        feature_entity = self._create_entity(
                            feature_text, EntityType.FEATURE, doc_id
                        )
                        new_entities.append(feature_entity)
                        entity_map[feature_text] = feature_entity
                    
                    triples.append(Triple(
                        subject=product_entity,
                        relation=RelationType.HAS_FEATURE,
                        object=feature_entity,
                        confidence=0.8,
                        source_text=f"{product_text} has {feature_text}",
                    ))
        
        # 3. 提取阶段关联
        for stage_code, keywords in self.stage_keywords.items():
            if any(kw in text for kw in keywords):
                stage_entity = get_stage_entity_by_code(stage_code)
                if stage_entity:
                    # 将文档中的话术/策略与阶段关联
                    for entity in entities:
                        if entity.type in [EntityType.SCRIPT, EntityType.RESPONSE]:
                            triples.append(Triple(
                                subject=entity,
                                relation=RelationType.APPLIES_TO_STAGE,
                                object=stage_entity,
                                confidence=0.7,
                                source_text=f"Stage: {stage_code}",
                            ))
        
        # 4. 匹配客户类型
        matched_customer_types = get_customer_type_by_keywords(text)
        for customer_type in matched_customer_types:
            for entity in entities:
                if entity.type in [EntityType.SCRIPT, EntityType.RESPONSE]:
                    triples.append(Triple(
                        subject=entity,
                        relation=RelationType.SUITS_CUSTOMER,
                        object=customer_type,
                        confidence=0.65,
                        source_text=f"Customer type: {customer_type.name}",
                    ))
        
        return new_entities, triples
    
    async def _extract_by_llm(
        self,
        text: str,
        entities: List[Entity],
        doc_id: Optional[str] = None,
    ) -> Tuple[List[Entity], List[Triple]]:
        """LLM 提取关系"""
        new_entities = []
        triples = []
        
        # 构建实体描述
        entities_desc = "\n".join([
            f"- {e.name} ({e.type})" for e in entities[:20]  # 限制数量
        ])
        
        # 构建 Prompt
        prompt = RELATION_EXTRACTION_PROMPT.format(
            text=text[:3000],  # 限制文本长度
            entities=entities_desc if entities_desc else "（无预识别实体）",
        )
        
        try:
            # 调用 LLM
            if hasattr(self.llm_client, 'chat'):
                response = self.llm_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                result_text = response.choices[0].message.content
            else:
                logger.warning("LLM client does not support chat completions")
                return new_entities, triples
            
            # 解析 JSON
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if not json_match:
                logger.warning("No JSON found in LLM response")
                return new_entities, triples
            
            result = json.loads(json_match.group())
            
            # 处理新实体
            entity_map = {e.name: e for e in entities}
            for entity_data in result.get("new_entities", []):
                name = entity_data.get("name", "").strip()
                type_str = entity_data.get("type", "")
                
                if not name or name in entity_map:
                    continue
                
                try:
                    entity_type = EntityType(type_str)
                except ValueError:
                    entity_type = EntityType.KEYWORD
                
                entity = self._create_entity(
                    name, entity_type, doc_id,
                    properties=entity_data.get("properties", {}),
                )
                new_entities.append(entity)
                entity_map[name] = entity
            
            # 处理关系
            for rel_data in result.get("relations", []):
                subject_name = rel_data.get("subject", "").strip()
                object_name = rel_data.get("object", "").strip()
                relation_str = rel_data.get("relation", "")
                confidence = rel_data.get("confidence", 0.8)
                evidence = rel_data.get("evidence", "")
                
                if not subject_name or not object_name:
                    continue
                
                # 获取或创建实体
                subject_entity = entity_map.get(subject_name)
                object_entity = entity_map.get(object_name)
                
                if not subject_entity:
                    subject_entity = self._create_entity(subject_name, EntityType.KEYWORD, doc_id)
                    new_entities.append(subject_entity)
                    entity_map[subject_name] = subject_entity
                
                if not object_entity:
                    object_entity = self._create_entity(object_name, EntityType.KEYWORD, doc_id)
                    new_entities.append(object_entity)
                    entity_map[object_name] = object_entity
                
                # 解析关系类型
                try:
                    relation_type = RelationType(relation_str)
                except ValueError:
                    relation_type = RelationType.SIMILAR_TO
                
                triples.append(Triple(
                    subject=subject_entity,
                    relation=relation_type,
                    object=object_entity,
                    confidence=confidence,
                    source_text=evidence,
                ))
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
        
        return new_entities, triples
    
    def _create_entity(
        self,
        name: str,
        entity_type: EntityType,
        doc_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Entity:
        """创建实体"""
        # 生成稳定的实体ID
        entity_id = hashlib.md5(f"{entity_type}:{name}".encode()).hexdigest()[:16]
        
        return Entity(
            id=entity_id,
            name=name,
            type=entity_type,
            properties=properties or {},
            source_doc_ids=[doc_id] if doc_id else [],
        )
    
    def extract_objections_from_text(self, text: str) -> List[Entity]:
        """
        从文本中提取异议实体
        
        使用预定义的异议模板和关键词匹配
        """
        objections = []
        text_lower = text.lower()
        
        for template in COMMON_OBJECTION_TEMPLATES:
            keywords = template.get("keywords", [])
            if any(kw in text_lower for kw in keywords):
                # 尝试提取具体的异议表述
                for pattern in self.objection_response_patterns:
                    matches = pattern.findall(text)
                    for match in matches:
                        if match and any(kw in match[0].lower() for kw in keywords):
                            objection = self._create_entity(
                                match[0].strip(),
                                EntityType.OBJECTION,
                                properties={
                                    "category": template["category"],
                                    "template_name": template["name"],
                                },
                            )
                            objections.append(objection)
                            break
                else:
                    # 使用模板名称作为通用异议
                    objection = self._create_entity(
                        template["name"],
                        EntityType.OBJECTION,
                        properties={"category": template["category"]},
                    )
                    objections.append(objection)
        
        return objections

