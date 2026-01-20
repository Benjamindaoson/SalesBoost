# 第一阶段实施计划（2周）- P0业务阻塞项

## Week 1：合规监控系统

### Day 1-2：基础架构搭建

#### 1. AC自动机实现
```python
# app/utils/ac_automaton.py
class AhoCorasick:
    """
    Aho-Corasick 自动机实现
    高效多模式匹配，时间复杂度 O(n)
    """
    def __init__(self):
        self.trie = {}
        self.fail = {}
        self.output = {}
    
    def add_pattern(self, pattern: str, category: str):
        """添加敏感词模式"""
        pass
    
    def build_fail_links(self):
        """构建失败链接（KMP思想）"""
        pass
    
    def search(self, text: str) -> List[Match]:
        """搜索文本中的所有敏感词"""
        pass

# 性能指标：10万词库，1000字文本 < 10ms
```

#### 2. 合规服务核心
```python
# app/services/compliance_service.py
class ComplianceService:
    """
    合规检测服务
    
    【三层检测】
    L1: AC自动机精确匹配（敏感词）
    L2: 正则表达式模糊匹配（变体词）
    L3: LLM语义判断（绕过检测）
    """
    
    def __init__(self):
        self.ac_matcher = AhoCorasick()
        self.llm_judge = ComplianceLLMJudge()
        self.rules_engine = RulesEngine()
    
    async def check_compliance(
        self, 
        text: str,
        context: Optional[Dict] = None
    ) -> ComplianceResult:
        """
        合规检测主流程
        
        Returns:
            ComplianceResult:
                - is_compliant: bool
                - violations: List[Violation]
                - risk_level: Enum[LOW, MEDIUM, HIGH]
                - alternative_texts: List[str]
        """
        # L1: 快速精确匹配
        exact_matches = self.ac_matcher.search(text)
        
        # L2: 规则引擎检测
        rule_violations = self.rules_engine.check(text, context)
        
        # L3: LLM语义判断（仅当L1/L2可疑时）
        if self._needs_llm_check(exact_matches, rule_violations):
            semantic_result = await self.llm_judge.judge(text, context)
        
        # 生成替代话术
        if violations:
            alternatives = await self._generate_alternatives(text, violations)
        
        return ComplianceResult(...)
```

#### 3. 数据模型
```python
# app/models/compliance_models.py
from pydantic import BaseModel
from enum import Enum

class ViolationType(str, Enum):
    SENSITIVE_WORD = "sensitive_word"       # 敏感词
    PROMISE_RETURN = "promise_return"       # 承诺收益
    MISLEADING = "misleading"               # 误导性陈述
    PRIVACY_BREACH = "privacy_breach"       # 侵犯隐私
    AGGRESSIVE_SALES = "aggressive_sales"   # 强制销售

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Violation(BaseModel):
    type: ViolationType
    matched_text: str
    position: Tuple[int, int]
    risk_level: RiskLevel
    rule_id: str
    description: str

class ComplianceResult(BaseModel):
    is_compliant: bool
    violations: List[Violation]
    overall_risk: RiskLevel
    alternative_texts: List[str]
    confidence: float
    check_timestamp: datetime

class ComplianceAuditLog(BaseModel):
    """审计日志"""
    session_id: str
    user_id: str
    original_text: str
    check_result: ComplianceResult
    action_taken: str  # "blocked" | "warned" | "passed"
    timestamp: datetime
```

### Day 3-4：规则引擎 + LLM判断

#### 4. 规则引擎
```python
# app/services/compliance_rules_engine.py
class RulesEngine:
    """
    基于配置的规则引擎
    支持正则、NER、依存句法等多种规则
    """
    
    def __init__(self, rules_config: str = "data/compliance/rules.yaml"):
        self.rules = self._load_rules(rules_config)
    
    def check(self, text: str, context: Dict) -> List[Violation]:
        violations = []
        
        # 规则类型1：正则表达式
        for rule in self.rules.get("regex_rules", []):
            if re.search(rule.pattern, text):
                violations.append(Violation(...))
        
        # 规则类型2：实体识别（如具体收益数字）
        entities = self._extract_entities(text)
        if self._violates_entity_rules(entities):
            violations.append(...)
        
        # 规则类型3：上下文依赖（如连续承诺）
        if context and self._violates_context_rules(text, context):
            violations.append(...)
        
        return violations

# 规则配置示例 (data/compliance/rules.yaml)
"""
regex_rules:
  - id: "promise_return_001"
    pattern: "(保证|承诺|确保).{0,10}(收益|回报|盈利)"
    risk_level: "high"
    description: "承诺收益违规"
  
  - id: "misleading_001"
    pattern: "(零风险|无风险|绝对安全)"
    risk_level: "critical"
    description: "误导性陈述"

entity_rules:
  - id: "specific_return_001"
    entity_type: "PERCENTAGE"
    condition: "value > 10"
    context: "return_promise"
    description: "承诺超过10%收益"
"""
```

#### 5. LLM语义判断
```python
# app/services/compliance_llm_judge.py
class ComplianceLLMJudge:
    """
    使用LLM进行语义层面的合规判断
    处理变体表达、隐晦表述等
    """
    
    JUDGE_PROMPT = """
你是一个金融销售合规专家。请判断以下话术是否违规。

【合规要点】
1. 不能承诺具体收益或保证回报
2. 不能使用"保证"、"确保"等绝对化表述
3. 不能误导客户夸大产品优势
4. 必须如实告知风险

【待检测话术】
{text}

【上下文】
{context}

【输出格式】
{{
  "is_compliant": true/false,
  "violations": [
    {{
      "type": "类型",
      "reason": "原因",
      "risk_level": "风险等级"
    }}
  ],
  "confidence": 0.0-1.0
}}
"""
    
    async def judge(self, text: str, context: Dict) -> Dict:
        prompt = self.JUDGE_PROMPT.format(
            text=text,
            context=json.dumps(context, ensure_ascii=False)
        )
        
        response = await self.llm.generate(
            prompt, 
            temperature=0.1,  # 低温度确保稳定输出
            response_format="json"
        )
        
        return json.loads(response)
```

#### 6. 替代话术生成
```python
# app/services/compliance_alternative_generator.py
class AlternativeGenerator:
    """
    生成合规的替代话术
    
    【策略】
    1. 检索式：从预设话术库匹配
    2. 生成式：LLM改写
    3. 混合式：检索 + 微调
    """
    
    def __init__(self):
        self.alternatives_db = self._load_alternatives_db()
        self.llm_rewriter = LLMRewriter()
    
    async def generate_alternatives(
        self, 
        original_text: str, 
        violations: List[Violation]
    ) -> List[str]:
        """生成3-5条替代话术"""
        
        # 策略1：检索相似合规话术
        retrieved = self._retrieve_similar_compliant(original_text)
        
        # 策略2：LLM改写违规部分
        rewritten = await self._llm_rewrite(original_text, violations)
        
        # 策略3：模板填充
        templated = self._template_based_generation(original_text)
        
        # 去重排序
        alternatives = self._deduplicate_and_rank(
            retrieved + rewritten + templated
        )
        
        return alternatives[:5]
    
    async def _llm_rewrite(self, text: str, violations: List[Violation]) -> List[str]:
        prompt = f"""
请将以下话术改写为合规版本。

【原话术】{text}

【违规点】
{violations}

【改写要求】
1. 保持原意和友好度
2. 去除违规表述
3. 添加必要的风险提示
4. 生成3个版本

【输出格式】
1. [改写版本1]
2. [改写版本2]
3. [改写版本3]
"""
        response = await self.llm.generate(prompt)
        return self._parse_alternatives(response)
```

### Day 5：集成 + 测试

#### 7. 增强 ComplianceAgent
```python
# app/agents/compliance_agent.py (重构)
class ComplianceAgent:
    """
    合规检测 Agent（重构版）
    集成 ComplianceService
    """
    
    def __init__(self):
        self.service = ComplianceService()
        self.logger = logging.getLogger(__name__)
    
    async def check(
        self,
        message: str,
        stage: SalesStage,
        conversation_history: List[Dict] = None
    ) -> ComplianceOutput:
        """
        检测消息合规性
        
        【增强】
        - 三层检测机制
        - 上下文感知
        - 替代话术建议
        """
        # 构建检测上下文
        context = {
            "stage": stage.value,
            "history": conversation_history,
            "user_intent": self._infer_intent(message)
        }
        
        # 调用合规服务
        result = await self.service.check_compliance(message, context)
        
        # 记录审计日志
        await self._log_audit(message, result)
        
        # 转换为 Agent 输出格式
        return ComplianceOutput(
            is_compliant=result.is_compliant,
            violations=[v.dict() for v in result.violations],
            risk_level=result.overall_risk.value,
            alternative_suggestions=result.alternative_texts,
            confidence=result.confidence
        )
```

#### 8. 单元测试
```python
# tests/services/test_compliance_service.py
import pytest

class TestComplianceService:
    
    @pytest.fixture
    def service(self):
        return ComplianceService()
    
    @pytest.mark.asyncio
    async def test_detect_promise_return(self, service):
        """测试承诺收益检测"""
        text = "我们保证年化收益至少15%"
        result = await service.check_compliance(text)
        
        assert result.is_compliant == False
        assert any(v.type == ViolationType.PROMISE_RETURN for v in result.violations)
        assert result.overall_risk == RiskLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_detect_misleading(self, service):
        """测试误导性陈述"""
        text = "这款产品零风险，绝对安全"
        result = await service.check_compliance(text)
        
        assert result.is_compliant == False
        assert len(result.violations) >= 1
    
    @pytest.mark.asyncio
    async def test_alternative_generation(self, service):
        """测试替代话术生成"""
        text = "保证收益15%"
        result = await service.check_compliance(text)
        
        assert len(result.alternative_texts) >= 3
        # 验证替代话术确实合规
        for alt in result.alternative_texts:
            alt_result = await service.check_compliance(alt)
            assert alt_result.is_compliant == True
```

---

## Week 2：建议采纳追踪 + 基础指标面板

### Day 6-7：增强 AdoptionTracker

#### 9. 扩展数据模型
```python
# app/models/adoption_models.py (扩展)
class SuggestionExposure(BaseModel):
    """建议曝光记录"""
    exposure_id: str
    session_id: str
    user_id: str
    suggestion_id: str
    suggestion_type: str  # "coach" | "objection_handler" | "compliance"
    suggestion_content: str
    context: Dict  # 曝光时的上下文
    position: int  # 展示位置
    timestamp: datetime

class SuggestionInteraction(BaseModel):
    """用户交互记录"""
    interaction_id: str
    exposure_id: str
    action: str  # "view" | "click" | "adopt" | "reject" | "modify"
    dwell_time_ms: int  # 停留时间
    timestamp: datetime

class AdoptionOutcome(BaseModel):
    """采纳后效果"""
    outcome_id: str
    exposure_id: str
    customer_reaction: str  # 客户反应（正面/中性/负面）
    conversation_continuation: bool  # 对话是否继续
    deal_stage_change: Optional[str]  # 成交阶段变化
    final_result: Optional[str]  # 最终结果（成交/流失/跟进）
    timestamp: datetime

class EnhancedAdoptionRecord(BaseModel):
    """增强的采纳记录（完整链路）"""
    record_id: str
    exposure: SuggestionExposure
    interactions: List[SuggestionInteraction]
    outcome: Optional[AdoptionOutcome]
    
    # 计算字段
    time_to_action: Optional[int]  # 曝光到采纳的时间
    adoption_score: float  # 采纳质量评分
    effectiveness_score: Optional[float]  # 效果评分
```

#### 10. 增强 AdoptionTracker
```python
# app/services/adoption_tracker.py (重构)
class AdoptionTracker:
    """
    建议采纳追踪器（增强版）
    
    【新增能力】
    - 完整链路追踪（曝光→交互→采纳→效果）
    - 实时指标计算
    - A/B测试支持
    - 因果推断分析
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.causal_analyzer = CausalAnalyzer()
        self.ab_tester = ABTestFramework()
    
    async def track_exposure(
        self,
        session_id: str,
        user_id: str,
        suggestion_id: str,
        suggestion_content: str,
        context: Dict,
        ab_group: Optional[str] = None
    ) -> str:
        """记录建议曝光"""
        exposure = SuggestionExposure(
            exposure_id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            suggestion_id=suggestion_id,
            suggestion_content=suggestion_content,
            context=context,
            timestamp=datetime.utcnow()
        )
        
        await self.db.execute(
            insert(suggestion_exposures).values(exposure.dict())
        )
        
        # A/B测试分组
        if ab_group:
            await self.ab_tester.assign_exposure(exposure.exposure_id, ab_group)
        
        return exposure.exposure_id
    
    async def track_interaction(
        self,
        exposure_id: str,
        action: str,
        dwell_time_ms: int
    ):
        """记录用户交互"""
        interaction = SuggestionInteraction(
            interaction_id=str(uuid.uuid4()),
            exposure_id=exposure_id,
            action=action,
            dwell_time_ms=dwell_time_ms,
            timestamp=datetime.utcnow()
        )
        
        await self.db.execute(
            insert(suggestion_interactions).values(interaction.dict())
        )
    
    async def track_outcome(
        self,
        exposure_id: str,
        customer_reaction: str,
        deal_stage_change: Optional[str] = None,
        final_result: Optional[str] = None
    ):
        """记录采纳后效果"""
        outcome = AdoptionOutcome(
            outcome_id=str(uuid.uuid4()),
            exposure_id=exposure_id,
            customer_reaction=customer_reaction,
            conversation_continuation=True,  # 从上下文判断
            deal_stage_change=deal_stage_change,
            final_result=final_result,
            timestamp=datetime.utcnow()
        )
        
        await self.db.execute(
            insert(adoption_outcomes).values(outcome.dict())
        )
        
        # 触发因果分析
        await self._analyze_effectiveness(exposure_id)
    
    async def calculate_adoption_rate(
        self,
        time_window: timedelta,
        filters: Optional[Dict] = None
    ) -> float:
        """计算采纳率"""
        query = """
        SELECT 
            COUNT(DISTINCT e.exposure_id) as total_exposures,
            COUNT(DISTINCT CASE WHEN i.action = 'adopt' THEN e.exposure_id END) as adoptions
        FROM suggestion_exposures e
        LEFT JOIN suggestion_interactions i ON e.exposure_id = i.exposure_id
        WHERE e.timestamp >= :start_time
        """
        
        result = await self.db.execute(
            text(query),
            {"start_time": datetime.utcnow() - time_window}
        )
        
        row = result.fetchone()
        return row.adoptions / row.total_exposures if row.total_exposures > 0 else 0.0
    
    async def _analyze_effectiveness(self, exposure_id: str):
        """因果分析：建议是否真正有效"""
        # 获取完整链路数据
        record = await self._get_full_record(exposure_id)
        
        # 因果推断：对比采纳组 vs 未采纳组的成交率
        causal_effect = await self.causal_analyzer.estimate_treatment_effect(
            treatment="adopted_suggestion",
            outcome="deal_closed",
            exposure_id=exposure_id
        )
        
        # 更新效果评分
        await self._update_effectiveness_score(exposure_id, causal_effect)
```

#### 11. 因果推断分析器
```python
# app/services/causal_analyzer.py
class CausalAnalyzer:
    """
    因果推断分析器
    区分相关性 vs 因果性
    """
    
    async def estimate_treatment_effect(
        self,
        treatment: str,
        outcome: str,
        exposure_id: str
    ) -> float:
        """
        估计因果效应（Treatment Effect）
        
        【方法】倾向得分匹配（Propensity Score Matching）
        1. 计算采纳倾向得分
        2. 匹配相似用户（采纳 vs 未采纳）
        3. 比较结果差异
        """
        # 1. 获取特征
        features = await self._get_user_features(exposure_id)
        
        # 2. 训练倾向得分模型
        propensity_model = LogisticRegression()
        propensity_model.fit(features, treatment_labels)
        
        # 3. 匹配
        matched_pairs = self._propensity_score_matching(
            treated_group, control_group, propensity_scores
        )
        
        # 4. 计算 ATE (Average Treatment Effect)
        ate = np.mean(matched_pairs.treated_outcome) - \
              np.mean(matched_pairs.control_outcome)
        
        return ate
```

### Day 8-9：基础指标面板

#### 12. MetricsService
```python
# app/services/metrics_service.py
class MetricsService:
    """
    指标计算服务
    实时 + 批量计算
    """
    
    def __init__(self):
        self.db = get_db()
        self.cache = Redis()
    
    async def get_business_metrics(
        self,
        time_range: str = "7d"
    ) -> BusinessMetrics:
        """获取业务指标"""
        
        # 从缓存读取（5分钟过期）
        cache_key = f"business_metrics:{time_range}"
        cached = await self.cache.get(cache_key)
        if cached:
            return BusinessMetrics.parse_raw(cached)
        
        # 实时计算
        metrics = BusinessMetrics(
            adoption_rate=await self._calc_adoption_rate(time_range),
            accuracy_rate=await self._calc_accuracy_rate(time_range),
            compliance_block_rate=await self._calc_compliance_rate(time_range),
            productivity_improvement=await self._calc_productivity(time_range),
        )
        
        # 写入缓存
        await self.cache.setex(cache_key, 300, metrics.json())
        
        return metrics
    
    async def _calc_adoption_rate(self, time_range: str) -> float:
        """计算建议采纳率"""
        query = """
        WITH exposures AS (
            SELECT exposure_id, timestamp
            FROM suggestion_exposures
            WHERE timestamp >= NOW() - INTERVAL :time_range
        ),
        adoptions AS (
            SELECT DISTINCT exposure_id
            FROM suggestion_interactions
            WHERE action = 'adopt'
            AND exposure_id IN (SELECT exposure_id FROM exposures)
        )
        SELECT 
            COUNT(DISTINCT e.exposure_id) as total,
            COUNT(DISTINCT a.exposure_id) as adopted
        FROM exposures e
        LEFT JOIN adoptions a ON e.exposure_id = a.exposure_id
        """
        
        result = await self.db.execute(text(query), {"time_range": time_range})
        row = result.fetchone()
        
        return row.adopted / row.total if row.total > 0 else 0.0
```

#### 13. API接口
```python
# app/api/endpoints/metrics.py
@router.get("/metrics/business")
async def get_business_metrics(
    time_range: str = "7d",
    current_user: User = Depends(get_current_user),
    metrics_service: MetricsService = Depends()
):
    """
    获取业务指标
    
    【权限】管理员 + 团队主管
    """
    if not current_user.has_permission("view_metrics"):
        raise HTTPException(403, "无权限")
    
    metrics = await metrics_service.get_business_metrics(time_range)
    
    return {
        "adoption_rate": metrics.adoption_rate,
        "target": 0.30,
        "trend": await metrics_service.get_trend("adoption_rate", time_range),
        "accuracy_rate": metrics.accuracy_rate,
        "compliance_block_rate": metrics.compliance_block_rate,
        "productivity_improvement": metrics.productivity_improvement
    }

@router.get("/metrics/adoption/detail")
async def get_adoption_details(
    user_id: Optional[str] = None,
    suggestion_type: Optional[str] = None,
    time_range: str = "7d"
):
    """采纳率详细数据"""
    # 返回分用户、分类型的采纳情况
    pass

@router.post("/metrics/ab_test/create")
async def create_ab_test(
    test_config: ABTestConfig,
    current_user: User = Depends(get_current_admin)
):
    """创建A/B测试"""
    test_id = await ab_tester.create_test(test_config)
    return {"test_id": test_id}
```

### Day 10：集成测试 + 部署

#### 14. 集成测试
```python
# tests/integration/test_phase1_integration.py
class TestPhase1Integration:
    
    @pytest.mark.asyncio
    async def test_compliance_in_conversation(self):
        """测试合规检测在真实对话中的工作"""
        # 创建会话
        session = await create_test_session()
        
        # 用户说出违规话术
        response = await session.send_message("这个产品保证赚钱")
        
        # 验证被拦截
        assert response.compliance_blocked == True
        assert len(response.alternative_suggestions) > 0
        
        # 验证审计日志
        logs = await get_compliance_logs(session.id)
        assert len(logs) == 1
    
    @pytest.mark.asyncio
    async def test_adoption_tracking_full_flow(self):
        """测试采纳追踪完整流程"""
        # 1. 曝光建议
        exposure_id = await tracker.track_exposure(
            session_id="test_session",
            user_id="test_user",
            suggestion_id="test_suggestion",
            suggestion_content="建议使用XX话术",
            context={}
        )
        
        # 2. 用户点击
        await tracker.track_interaction(exposure_id, "click", 2000)
        
        # 3. 用户采纳
        await tracker.track_interaction(exposure_id, "adopt", 5000)
        
        # 4. 记录效果
        await tracker.track_outcome(
            exposure_id,
            customer_reaction="positive",
            deal_stage_change="NEEDS_DISCOVERY->PRODUCT_INTRO"
        )
        
        # 5. 验证数据
        record = await tracker.get_full_record(exposure_id)
        assert record.outcome is not None
        assert record.adoption_score > 0
```

#### 15. 部署清单
```bash
# deployment/phase1_checklist.sh

# 1. 数据库迁移
alembic revision --autogenerate -m "Add compliance and adoption tracking tables"
alembic upgrade head

# 2. 敏感词库导入
python scripts/import_compliance_wordlist.py data/compliance/sensitive_words.json

# 3. 配置更新
# - 添加 LLM API 配置（合规判断）
# - 添加 Redis 配置（指标缓存）

# 4. 服务重启
systemctl restart salesboost-api

# 5. 监控配置
# - 添加合规检测响应时间监控
# - 添加采纳率实时监控告警
```

---

## 验收标准（Week 2 End）

### 功能验收
- ✅ 合规检测准确率 > 95%
- ✅ 敏感词检测延迟 < 50ms
- ✅ LLM语义判断延迟 < 2s
- ✅ 替代话术生成成功率 > 90%
- ✅ 采纳率计算准确性验证通过
- ✅ 审计日志完整记录所有检测

### 性能验收
- ✅ AC自动机检测 10万词库 < 10ms
- ✅ 完整合规检测（三层）< 3s
- ✅ 指标计算接口响应 < 500ms
- ✅ 数据库查询优化（添加索引）

### 安全验收
- ✅ 合规词库加密存储
- ✅ 审计日志不可篡改
- ✅ 管理后台权限控制
- ✅ 敏感信息脱敏

---

## 风险控制

### 技术风险
| 风险 | 缓解措施 |
|------|---------|
| LLM判断不稳定 | 多次调用取最严格结果 + 人工审核机制 |
| AC自动机内存占用大 | 词库分级加载 + 热词缓存 |
| 指标计算慢 | 增量计算 + 缓存 + 异步任务 |

### 业务风险
| 风险 | 缓解措施 |
|------|---------|
| 误判率高 | 白名单机制 + 人工申诉流程 |
| 用户体验差 | 优化提示文案 + 快速替代建议 |

---

## 下一阶段准备

**Week 2结束时应完成：**
1. 合规系统上线并稳定运行
2. 采纳率数据开始积累
3. 基础指标面板可用
4. P1阶段需求分析完成
5. AI陪练模块技术选型确定

**交付物：**
- 合规检测服务（部署）
- 采纳追踪服务（部署）
- 指标面板前端（上线）
- 第一阶段总结报告
- 第二阶段详细设计文档

