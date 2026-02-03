# SalesBoost AI产品演进路线图

**审查日期**: 2026-02-02
**审查人**: AI产品经理 + 技术架构师
**项目状态**: 基础架构完善，需要AI产品化升级

---

## 📊 现状评估

### ✅ 已有的核心能力

| 能力 | 完成度 | 评价 |
|------|--------|------|
| **架构设计** | 95% | 事件驱动架构（EDA）+ 模型网关，工业级 |
| **AI智能体矩阵** | 80% | Coach/NPC/Analyst三大Agent已实现 |
| **知识闭环** | 70% | PDF→向量检索→推理链路完整 |
| **RAG系统** | 85% | BGE-M3双路径检索 + Self-RAG |
| **FSM状态机** | 90% | 7状态5阶段销售流程 |
| **语音系统** | 60% | TTS/STT后端完成，前端未集成 |
| **监控系统** | 90% | Prometheus完整监控 |
| **部署系统** | 95% | Docker + CI/CD完整 |

### ❌ 核心缺失

| 缺失 | 影响 | 优先级 |
|------|------|--------|
| **个性化学习路径** | 用户无法针对性提升 | P0 |
| **实时情感反馈** | 训练不够真实 | P1 |
| **GraphRAG** | 复杂问答准确率低 | P1 |
| **RLAIF闭环** | AI无法自我优化 | P0 |
| **语音前端** | 用户体验不完整 | P1 |
| **多租户系统** | 无法商业化 | P1 |
| **管理者驾驶舱** | 企业客户需求 | P2 |

---

## 🎯 AI产品功能缺失清单

### P0 - 核心AI功能（必须实现）

#### 1. 动态课程生成器（Dynamic Curriculum）

**现状**: `curriculum_planner.py` 是Stub，无法根据用户表现生成个性化训练

**目标**:
- 根据用户历史评分，自动识别弱点
- 生成个性化的"弱点攻克"训练营
- 动态调整训练难度

**实现方案**:
```python
class DynamicCurriculumPlanner:
    """动态课程规划器"""

    def analyze_weaknesses(self, user_id: int) -> List[Weakness]:
        """分析用户弱点"""
        # 1. 获取用户历史评估
        evaluations = get_user_evaluations(user_id)

        # 2. 识别低分维度
        weaknesses = []
        for dimension in ["methodology", "objection_handling", "empathy"]:
            avg_score = mean([e[dimension] for e in evaluations])
            if avg_score < 7.0:
                weaknesses.append({
                    "dimension": dimension,
                    "score": avg_score,
                    "gap": 7.0 - avg_score,
                })

        return weaknesses

    def generate_curriculum(self, user_id: int) -> Curriculum:
        """生成个性化课程"""
        weaknesses = self.analyze_weaknesses(user_id)

        # 根据弱点生成训练任务
        tasks = []
        for weakness in weaknesses:
            if weakness["dimension"] == "objection_handling":
                # 生成异议处理专项训练
                tasks.append({
                    "type": "objection_drill",
                    "difficulty": "hard",
                    "focus": "price_objection",
                    "target_score": 8.0,
                })

        return Curriculum(tasks=tasks, duration_days=7)
```

**价值**:
- 用户留存率提升30%+（个性化训练更有效）
- 训练效率提升50%+（针对性训练）

---

#### 2. RLAIF数据闭环（AI自我优化）

**现状**: 评估依赖固定Prompt，无法自我优化

**目标**:
- 收集用户对话样本
- 由高级模型（Claude 3.5）自动打标
- 生成微调数据集，优化轻量级模型

**实现方案**:
```python
class RLAIFPipeline:
    """RLAIF数据闭环"""

    async def collect_samples(self):
        """收集对话样本"""
        # 1. 从数据库获取高质量对话
        sessions = db.query(Session).filter(
            Session.score >= 8.0,  # 高分对话
            Session.status == "completed"
        ).all()

        # 2. 提取对话样本
        samples = []
        for session in sessions:
            messages = session.messages
            samples.append({
                "conversation": messages,
                "score": session.score,
                "evaluation": session.evaluation,
            })

        return samples

    async def label_with_ai(self, samples: List[Dict]):
        """AI自动打标"""
        labeled_data = []

        for sample in samples:
            # 使用Claude 3.5进行高质量标注
            prompt = f"""
            分析以下销售对话，标注每句话的质量：

            对话：{sample['conversation']}

            请标注：
            1. 哪些话术是优秀的（good）
            2. 哪些话术需要改进（bad）
            3. 改进建议
            """

            response = await claude_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model="claude-3-5-sonnet",
            )

            labeled_data.append({
                "conversation": sample["conversation"],
                "labels": response.content,
            })

        return labeled_data

    async def generate_training_data(self, labeled_data: List[Dict]):
        """生成微调数据"""
        training_data = []

        for data in labeled_data:
            # 转换为微调格式
            training_data.append({
                "messages": [
                    {"role": "system", "content": "你是销售教练"},
                    {"role": "user", "content": data["conversation"]},
                    {"role": "assistant", "content": data["labels"]},
                ]
            })

        # 保存为JSONL
        with open("training_data.jsonl", "w") as f:
            for item in training_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        return training_data
```

**价值**:
- AI准确率持续提升（从80%→90%+）
- 成本降低50%+（轻量级模型替代大模型）
- 数据飞轮效应（越用越好）

---

### P1 - 用户体验优化（重要功能）

#### 3. 实时情感反馈（Emotional Intelligence）

**现状**: NPC只有简单的mood分数，不够真实

**目标**:
- 声纹/文字情感分析
- 模拟客户的"不耐烦"、"购买冲动"
- 实时情感可视化

**实现方案**:
```python
class EmotionalIntelligence:
    """情感智能系统"""

    async def analyze_emotion(self, text: str, audio: bytes = None) -> Emotion:
        """分析情感"""
        # 1. 文字情感分析
        text_emotion = await self.analyze_text_emotion(text)

        # 2. 声纹情感分析（如果有音频）
        if audio:
            voice_emotion = await self.analyze_voice_emotion(audio)
            # 融合文字和声纹情感
            emotion = self.fuse_emotions(text_emotion, voice_emotion)
        else:
            emotion = text_emotion

        return emotion

    async def analyze_text_emotion(self, text: str) -> Dict:
        """文字情感分析"""
        # 使用情感分析模型
        prompt = f"""
        分析以下文字的情感：

        文字：{text}

        请判断：
        1. 情感类型（positive/neutral/negative）
        2. 情感强度（0-1）
        3. 具体情绪（happy/angry/frustrated/excited）
        """

        response = await llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
        )

        return parse_emotion(response.content)

    def update_npc_mood(self, emotion: Emotion, npc: NPCSimulator):
        """更新NPC情绪"""
        # 根据情感调整NPC行为
        if emotion["type"] == "negative" and emotion["intensity"] > 0.7:
            # 客户不耐烦，提高异议率
            npc.objection_rate = min(1.0, npc.objection_rate + 0.2)
            npc.interest_level = max(0.0, npc.interest_level - 0.3)
        elif emotion["type"] == "positive" and emotion["intensity"] > 0.8:
            # 客户兴奋，降低异议率
            npc.objection_rate = max(0.0, npc.objection_rate - 0.2)
            npc.interest_level = min(1.0, npc.interest_level + 0.3)
```

**价值**:
- 训练真实度提升40%+
- 用户满意度提升25%+

---

#### 4. 语音前端集成（Voice UI）

**现状**: 后端TTS/STT完成，前端未集成

**目标**:
- 实时语音对话
- 语音波形可视化
- 语速、语调、停顿分析

**实现方案**:
```typescript
// frontend/src/components/VoiceTraining.tsx

import { useState, useRef } from 'react';
import { voiceService } from '@/services/voice.service';

export function VoiceTraining() {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const mediaRecorder = useRef<MediaRecorder | null>(null);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder.current = new MediaRecorder(stream);

    const audioChunks: Blob[] = [];
    mediaRecorder.current.ondataavailable = (e) => {
      audioChunks.push(e.data);
    };

    mediaRecorder.current.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });

      // 发送到后端进行STT
      const result = await voiceService.transcribe(audioBlob);
      setTranscript(result.text);

      // 获取AI回复
      const response = await voiceService.getVoiceResponse(result.text);

      // 播放AI语音
      playAudio(response.audio_base64);
    };

    mediaRecorder.current.start();
    setIsRecording(true);
  };

  const stopRecording = () => {
    mediaRecorder.current?.stop();
    setIsRecording(false);
  };

  return (
    <div className="voice-training">
      <button onClick={isRecording ? stopRecording : startRecording}>
        {isRecording ? '停止录音' : '开始录音'}
      </button>

      <div className="transcript">{transcript}</div>

      <WaveformVisualizer isRecording={isRecording} />
    </div>
  );
}
```

**价值**:
- 用户体验提升50%+（更接近真实场景）
- 训练效果提升30%+（语音细节很重要）

---

#### 5. GraphRAG集成（复杂问答）

**现状**: 向量检索难以处理"产品A vs 产品B"等对比问题

**目标**:
- 知识图谱构建
- 关系推理
- 对比性问答

**实现方案**:
```python
class GraphRAG:
    """知识图谱RAG"""

    def build_knowledge_graph(self, documents: List[Document]):
        """构建知识图谱"""
        # 1. 实体抽取
        entities = []
        for doc in documents:
            extracted = self.extract_entities(doc.content)
            entities.extend(extracted)

        # 2. 关系抽取
        relations = []
        for doc in documents:
            extracted = self.extract_relations(doc.content, entities)
            relations.extend(extracted)

        # 3. 构建图
        graph = nx.DiGraph()
        for entity in entities:
            graph.add_node(entity["id"], **entity)
        for relation in relations:
            graph.add_edge(
                relation["source"],
                relation["target"],
                type=relation["type"]
            )

        return graph

    async def query_graph(self, query: str, graph: nx.DiGraph) -> List[str]:
        """图查询"""
        # 1. 识别查询意图
        if "对比" in query or "vs" in query:
            # 对比查询
            entities = self.extract_entities_from_query(query)
            if len(entities) >= 2:
                # 找到两个实体的共同属性
                paths = self.find_comparison_paths(
                    graph, entities[0], entities[1]
                )
                return self.format_comparison(paths)

        # 2. 普通查询
        entities = self.extract_entities_from_query(query)
        if entities:
            # 子图检索
            subgraph = self.extract_subgraph(graph, entities[0], depth=2)
            return self.format_subgraph(subgraph)

        return []
```

**价值**:
- 复杂问答准确率提升40%+
- 用户满意度提升20%+

---

### P2 - 商业化功能（扩展功能）

#### 6. 多租户系统（Enterprise）

**现状**: 单租户，无法商业化

**目标**:
- 租户隔离
- 自定义知识库
- 配额管理

**实现方案**:
```python
class TenantManager:
    """租户管理器"""

    async def create_tenant(self, tenant_data: Dict) -> Tenant:
        """创建租户"""
        tenant = Tenant(
            name=tenant_data["name"],
            schema_name=f"tenant_{uuid.uuid4().hex[:8]}",
            quota={
                "max_users": 100,
                "max_sessions_per_month": 10000,
                "max_storage_gb": 10,
            }
        )

        # 创建租户Schema
        await self.create_tenant_schema(tenant.schema_name)

        # 创建租户数据库表
        await self.create_tenant_tables(tenant.schema_name)

        return tenant

    async def upload_tenant_knowledge(
        self,
        tenant_id: int,
        files: List[UploadFile]
    ):
        """上传租户知识库"""
        tenant = await self.get_tenant(tenant_id)

        # 处理文件
        documents = []
        for file in files:
            content = await self.process_file(file)
            documents.append(Document(
                content=content,
                tenant_id=tenant_id,
            ))

        # 向量化并存储到租户专属Collection
        collection_name = f"tenant_{tenant_id}_knowledge"
        await qdrant_client.create_collection(collection_name)
        await qdrant_client.upsert_documents(collection_name, documents)
```

**价值**:
- 商业化能力（支持企业客户）
- ARR提升10x+

---

#### 7. 管理者驾驶舱（Management Dashboard）

**现状**: 只服务员工，不服务管理者

**目标**:
- 团队能力分布
- 弱点识别
- SOP有效性分析

**实现方案**:
```python
class ManagementDashboard:
    """管理者驾驶舱"""

    async def get_team_overview(self, team_id: int) -> Dict:
        """团队概览"""
        users = await self.get_team_users(team_id)

        # 1. 能力分布
        ability_distribution = {}
        for dimension in ["methodology", "objection_handling", "empathy"]:
            scores = [u.avg_score[dimension] for u in users]
            ability_distribution[dimension] = {
                "mean": mean(scores),
                "median": median(scores),
                "std": stdev(scores),
                "distribution": self.get_distribution(scores),
            }

        # 2. 识别需要培训的员工
        weak_users = []
        for user in users:
            if user.avg_score["overall"] < 7.0:
                weak_users.append({
                    "user_id": user.id,
                    "name": user.full_name,
                    "weaknesses": self.identify_weaknesses(user),
                })

        # 3. SOP有效性分析
        sop_effectiveness = await self.analyze_sop_effectiveness(team_id)

        return {
            "ability_distribution": ability_distribution,
            "weak_users": weak_users,
            "sop_effectiveness": sop_effectiveness,
        }

    async def analyze_sop_effectiveness(self, team_id: int) -> Dict:
        """SOP有效性分析"""
        # 分析哪些SOP在实际中被证明有效
        sessions = await self.get_team_sessions(team_id)

        sop_usage = {}
        for session in sessions:
            for message in session.messages:
                if message.sales_technique:
                    technique = message.sales_technique
                    if technique not in sop_usage:
                        sop_usage[technique] = {
                            "count": 0,
                            "success_count": 0,
                            "avg_score": 0,
                        }

                    sop_usage[technique]["count"] += 1
                    if session.score >= 8.0:
                        sop_usage[technique]["success_count"] += 1

        # 计算成功率
        for technique, data in sop_usage.items():
            data["success_rate"] = data["success_count"] / data["count"]

        return sop_usage
```

**价值**:
- 企业客户满意度提升30%+
- 续费率提升20%+

---

## 🗺️ 实施路线图

### Phase 1: AI核心能力（1个月）

**目标**: 让AI更智能

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 动态课程生成器 | 5天 | P0 |
| RLAIF数据闭环 | 10天 | P0 |
| 情感分析系统 | 5天 | P1 |
| GraphRAG集成 | 10天 | P1 |

**交付物**:
- 个性化训练路径
- AI自我优化能力
- 情感智能NPC
- 复杂问答能力

---

### Phase 2: 用户体验（1个月）

**目标**: 让训练更真实

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 语音前端集成 | 10天 | P1 |
| 实时情感可视化 | 5天 | P1 |
| 战力值系统 | 5天 | P2 |
| 话术实验室 | 10天 | P2 |

**交付物**:
- 语音对话界面
- 情感实时反馈
- 能力可视化
- 压力测试功能

---

### Phase 3: 商业化（2个月）

**目标**: 让产品可商业化

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 多租户系统 | 15天 | P1 |
| 管理者驾驶舱 | 10天 | P2 |
| API市场化 | 10天 | P2 |
| 计费系统 | 10天 | P2 |

**交付物**:
- 企业级部署
- 管理者功能
- API服务
- 商业化能力

---

## 📊 预期效果

| 指标 | 当前 | Phase 1后 | Phase 2后 | Phase 3后 |
|------|------|-----------|-----------|-----------|
| **AI准确率** | 80% | 85% | 90% | 95% |
| **用户留存率** | 60% | 75% | 85% | 90% |
| **训练效率** | 基准 | +30% | +50% | +70% |
| **用户满意度** | 70% | 80% | 90% | 95% |
| **商业化能力** | 0 | 0 | 0 | 100% |

---

## 💡 关键建议

### 1. 优先级排序

**立即执行（本月）**:
1. ✅ 动态课程生成器（个性化是核心竞争力）
2. ✅ RLAIF数据闭环（AI自我优化是长期优势）

**下个月执行**:
3. ✅ 语音前端集成（用户体验关键）
4. ✅ 情感分析系统（训练真实度）

**3个月内执行**:
5. ✅ 多租户系统（商业化基础）
6. ✅ 管理者驾驶舱（企业客户需求）

### 2. 技术选型建议

- **情感分析**: 使用HuggingFace的emotion-english-distilroberta-base
- **GraphRAG**: 使用Neo4j或NetworkX
- **语音前端**: 使用Web Audio API + MediaRecorder
- **多租户**: 使用PostgreSQL Schema隔离

### 3. 数据策略

- **RLAIF**: 每周收集100+高质量对话
- **A/B测试**: 新功能先灰度10%用户
- **用户反馈**: 每次训练后收集满意度评分

---

**文档版本**: v1.0
**创建日期**: 2026-02-02
**维护者**: AI产品团队
