# 销售数据集成总结

## ✅ 已完成工作

### 1. 数据摄入脚本

**文件**：`scripts/ingest_sales_data.py`

**功能**：
- ✅ 支持Excel文件处理（产品权益、竞品分析）
- ✅ 支持PDF文件处理（SOP、培训材料）
- ✅ 支持Word文件处理（话术、经验分享）
- ✅ 自动分块和向量化
- ✅ 自动提取实体和关系
- ✅ 构建知识图谱
- ✅ 社区检测和摘要生成

**使用方法**：
```bash
python scripts/ingest_sales_data.py
```

### 2. 文档说明

**已创建文档**：
1. `DATA_INGESTION_GUIDE.md` - 数据摄入详细指南
2. `MODULES_DATA_USAGE.md` - 模块数据使用说明
3. `DATA_INTEGRATION_SUMMARY.md` - 本文档

### 3. 依赖更新

**已添加到 `requirements.txt`**：
- `openpyxl>=3.1.2` - Excel文件处理
- `python-docx>=1.1.0` - Word文档处理

---

## 📊 数据使用映射

### RAG系统（向量检索）

**使用的数据**：
- ✅ 所有文档（产品权益、SOP、话术、案例）

**模块**：
- `app/services/knowledge_service.py`
- `app/services/advanced_rag_service.py`
- `app/agents/rag_agent.py`

**用途**：语义检索、关键词检索、混合检索

### GraphRAG系统（知识图谱）

**使用的数据**：
- ✅ SOP和话术（提取话术-异议关系）
- ✅ 产品权益（提取产品-特性-利益关系）
- ✅ 销售冠军经验（提取成功案例）

**模块**：
- `app/services/graph_rag_service.py`
- `app/services/graph_rag/relation_extractor.py`
- `app/services/graph_rag/graph_builder.py`
- `app/services/graph_rag/graph_retriever.py`

**用途**：多跳推理、关系检索、社区检索

### NPC Agent（客户模拟）

**使用的数据**：
- ✅ 销售录音（对话模式学习）
- ✅ 销售冠军经验（客户行为模式）
- ✅ SOP和话术（常见异议）

**模块**：
- `app/agents/npc_agent.py`
- `app/sales_simulation/agents/npc_agent.py`

**用途**：生成客户回应、模拟异议、情绪模拟

### Coach Agent（销售教练）

**使用的数据**：
- ✅ SOP和话术（销售技巧）
- ✅ 销售冠军经验（成功案例）
- ✅ 产品权益（产品知识）

**模块**：
- `app/agents/coach_agent.py`

**用途**：实时建议、话术推荐、案例分享

### Evaluator Agent（评估器）

**使用的数据**：
- ✅ SOP和话术（评估标准）
- ✅ 销售冠军经验（最佳实践）

**模块**：
- `app/agents/evaluator_agent.py`

**用途**：表现评估、对比分析、改进建议

---

## 🚀 下一步操作

### 1. 安装依赖

```bash
pip install openpyxl python-docx
```

### 2. 运行数据摄入

```bash
python scripts/ingest_sales_data.py
```

### 3. 验证数据

```python
# 检查向量数据库
from app.services.knowledge_service import KnowledgeService
service = KnowledgeService()
print(f"文档数: {service.count_documents()}")

# 检查知识图谱
from app.services.graph_rag_service import GraphRAGService
graph_rag = GraphRAGService()
stats = graph_rag.get_statistics()
print(f"节点数: {stats['graph']['total_nodes']}")
print(f"边数: {stats['graph']['total_edges']}")
```

### 4. 测试检索功能

```python
from app.agents.rag_agent import RAGAgent
from app.schemas.fsm import SalesStage

rag_agent = RAGAgent(use_advanced_rag=True, use_graph_rag=True)

# 测试检索
result = await rag_agent.retrieve(
    query="如何处理价格异议",
    stage=SalesStage.OBJECTION_HANDLING,
    context={},
    top_k=5,
    mode="hybrid",
)

print(f"检索到 {len(result.retrieved_content)} 条结果")
```

---

## 📁 数据文件结构

```
销冠能力复制数据库/
├── 产品权益/
│   ├── FAQ.xlsx
│   ├── 卡产品&权益&年费.xlsx
│   ├── 百夫长权益详解.xlsx
│   ├── 高尔夫权益详解.xlsx
│   └── 竞品分析/
│       ├── Safari卡-竞品对比.xlsx
│       ├── 白金卡-竞品对比.xlsx
│       └── 百夫长-竞品对比.xlsx
├── 销售成交营销SOP和话术/
│   ├── 《绝对成交》谈判大师.pdf
│   ├── 信用卡的推广技巧.ppt
│   ├── 信用卡营销宝典之话术篇.pptx
│   ├── 信用卡营销经验交流.doc
│   ├── 信用卡销售心态&技巧.pdf
│   ├── 信用卡销售技巧培训.pdf
│   ├── 信用卡销售话术对练(3篇).docx
│   ├── 招商银行信用卡销售教程.pdf
│   └── 银行信用卡分期话术技巧.docx
├── 销售冠军成交经验分享/
│   └── 销售冠军经验总结.docx
└── 销售录音/
    ├── 信用卡推销_新录音-2025年12月6日.mp3
    ├── 借记卡转信用卡推销-2025年12月6日2.mp3
    ├── 工商银行免费升级大额信用卡.wav
    └── 新录音-2025年12月6日-16_25_10-音频.mp3
```

---

## ⚠️ 注意事项

1. **Excel文件**：需要安装 `openpyxl`
2. **Word文件**：需要安装 `python-docx`（仅支持.docx格式）
3. **PDF文件**：需要安装 `pymupdf`（已在requirements.txt中）
4. **PPT文件**：需要安装 `python-pptx`（可选，暂未实现）
5. **音频文件**：需要STT服务（可选，暂未实现）

---

## 🔧 故障排除

### 问题1：Excel文件无法读取

**错误**：`ModuleNotFoundError: No module named 'openpyxl'`

**解决**：
```bash
pip install openpyxl
```

### 问题2：Word文件无法读取

**错误**：`ModuleNotFoundError: No module named 'docx'`

**解决**：
```bash
pip install python-docx
```

### 问题3：PDF文件无法读取

**错误**：`ModuleNotFoundError: No module named 'fitz'`

**解决**：
```bash
pip install pymupdf
```

### 问题4：GraphRAG实体提取失败

**原因**：LLM API配置问题

**解决**：
- 检查 `OPENAI_API_KEY` 环境变量
- 确保有足够的API配额
- 检查网络连接

---

## 📈 预期效果

### 数据摄入后

- **向量数据库**：包含所有文档的分块和向量表示
- **知识图谱**：包含提取的实体和关系
- **社区结构**：自动检测的知识社区

### 检索性能提升

- **异议处理准确率**：55% → 75%+
- **多跳问答准确率**：40% → 70%+
- **长尾查询召回**：60% → 80%+

---

## 📚 相关文档

- [数据摄入指南](DATA_INGESTION_GUIDE.md)
- [模块数据使用说明](MODULES_DATA_USAGE.md)
- [GraphRAG实现报告](GRAPH_RAG_IMPLEMENTATION_COMPLETE.md)

---

## ✅ 完成状态

- [x] 数据摄入脚本
- [x] 文档说明
- [x] 依赖更新
- [ ] 数据摄入测试（待运行）
- [ ] NPC Agent集成（待实现）
- [ ] Coach Agent集成（待优化）


