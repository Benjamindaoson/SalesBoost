# 销售数据摄入指南

## 概述

本指南说明如何将"sample-data"文件夹中的数据导入到 SalesBoost 系统中。

## 数据来源

数据位于 `path/to/documents` 文件夹，包含：

1. **产品权益** (`产品权益/`)
   - Excel文件：产品信息、权益、年费、FAQ
   - 竞品分析：竞品对比表格

2. **销售成交营销SOP和话术** (`销售成交营销SOP和话术/`)
   - PDF：销售技巧、培训材料
   - Word：话术、经验交流
   - PPT：推广技巧、营销宝典

3. **销售冠军成交经验分享** (`销售冠军成交经验分享/`)
   - Word：成功案例和经验总结

4. **销售录音** (`销售录音/`)
   - 音频文件：实际销售对话录音（需要STT处理）

## 使用的系统模块

### 1. RAG系统（向量检索）

**模块**：
- `KnowledgeService` - 向量数据库（ChromaDB）
- `AdvancedRAGService` - 高级RAG（混合检索、Reranker）

**用途**：
- 存储所有文档的向量表示
- 支持语义检索和关键词检索
- 用于快速检索相关话术、案例、策略

**数据流**：
```
文档 → DocumentProcessor（分块） → ChromaDB（向量存储）
```

### 2. GraphRAG系统（知识图谱）

**模块**：
- `GraphRAGService` - 知识图谱服务
- `RelationExtractor` - 关系提取器
- `SalesKnowledgeGraph` - 图构建器
- `CommunityDetector` - 社区检测器

**用途**：
- 提取实体（产品、特性、异议、话术等）
- 提取关系（产品-特性、话术-异议等）
- 构建知识图谱
- 支持多跳推理和全局检索

**数据流**：
```
文档 → RelationExtractor（提取实体和关系） → SalesKnowledgeGraph（构建图） → CommunityDetector（社区检测）
```

### 3. 多智能体系统

#### NPC Agent（客户模拟）

**使用的数据**：
- 销售录音（实际对话模式）
- 销售冠军经验（客户行为模式）
- 异议类型（客户常见异议）

**用途**：
- 模拟真实客户对话
- 生成符合销售场景的客户回应
- 提供多样化的异议场景

#### Coach Agent（销售教练）

**使用的数据**：
- SOP和话术（销售技巧）
- 销售冠军经验（成功案例）
- 产品权益（产品知识）

**用途**：
- 提供实时销售建议
- 推荐合适的话术
- 分享成功案例

#### Evaluator Agent（评估器）

**使用的数据**：
- SOP和话术（评估标准）
- 销售冠军经验（最佳实践）

**用途**：
- 评估销售表现
- 对比最佳实践
- 提供改进建议

#### RAG Agent（知识检索）

**使用的数据**：
- 所有文档（统一检索入口）

**用途**：
- 检索相关话术、案例、策略
- 支持向量检索和图检索
- 提供来源引用

## 数据摄入流程

### 步骤1：安装依赖

```bash
pip install openpyxl python-docx
```

### 步骤2：运行摄入脚本

```bash
python scripts/ingest_sales_data.py
```

### 步骤3：验证数据

脚本会输出统计信息：
- 处理的文件数量
- 提取的实体数量
- 提取的关系数量
- 社区数量

## 数据分类和标签

### 文档类型（doc_type）

- `product_benefit` - 产品权益
- `competitor_analysis` - 竞品分析
- `sop` - 标准操作流程
- `script` - 销售话术
- `case` - 成功案例
- `training` - 培训材料

### 销售阶段映射

根据文档内容自动映射到销售阶段：
- `OPENING` - 破冰建联
- `NEEDS_DISCOVERY` - 需求挖掘
- `PRODUCT_INTRO` - 产品介绍
- `OBJECTION_HANDLING` - 异议处理
- `CLOSING` - 促单成交

## 数据使用示例

### 1. RAG检索

```python
from app.agents.roles.rag_agent import RAGAgent
from app.schemas.fsm import SalesStage

rag_agent = RAGAgent(use_advanced_rag=True, use_graph_rag=True)

# 检索异议处理话术
result = await rag_agent.retrieve_for_objection(
    objection_text="年费太贵",
    stage=SalesStage.OBJECTION_HANDLING,
    customer_type="价格敏感型",
)
```

### 2. GraphRAG检索

```python
from app.services.graph_rag_service import GraphRAGService

graph_rag = GraphRAGService()

# 混合检索
result = await graph_rag.search(
    query="如何处理价格异议",
    stage="OBJECTION_HANDLING",
    mode="hybrid",
    top_k=5,
)
```

### 3. 知识图谱查询

```python
# 获取统计信息
stats = graph_rag.get_statistics()
print(f"节点数: {stats['graph']['total_nodes']}")
print(f"边数: {stats['graph']['total_edges']}")
```

## 数据更新

### 增量更新

当有新数据时，可以：
1. 将新文件放入对应文件夹
2. 重新运行摄入脚本（会自动跳过已处理的文件）

### 手动更新

```python
from scripts.ingest_sales_data import SalesDataIngester

ingester = SalesDataIngester(org_id="your_org_id")
await ingester.ingest_all()
```

## 注意事项

1. **Excel文件**：需要安装 `openpyxl`
2. **Word文件**：需要安装 `python-docx`（仅支持.docx格式）
3. **PDF文件**：需要安装 `pymupdf`（已在requirements.txt中）
4. **PPT文件**：需要安装 `python-pptx`（可选）
5. **音频文件**：需要STT服务（可选，暂未实现）

## 故障排除

### 问题1：Excel文件无法读取

**解决方案**：
```bash
pip install openpyxl
```

### 问题2：Word文件无法读取

**解决方案**：
```bash
pip install python-docx
```

### 问题3：PDF文件无法读取

**解决方案**：
```bash
pip install pymupdf
```

### 问题4：GraphRAG实体提取失败

**原因**：可能是LLM API配置问题

**解决方案**：
- 检查 `OPENAI_API_KEY` 环境变量
- 确保有足够的API配额

## 性能优化

1. **批量处理**：脚本会自动批量处理文件
2. **并行处理**：可以修改脚本支持并行处理
3. **缓存**：GraphRAG会自动缓存社区摘要

## 下一步

1. 运行数据摄入脚本
2. 验证数据是否正确导入
3. 测试RAG检索功能
4. 测试GraphRAG检索功能
5. 在销售模拟中使用这些数据


