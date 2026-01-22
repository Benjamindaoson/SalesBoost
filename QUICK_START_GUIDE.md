# 快速使用指南 - 新功能

## 🚀 快速开始

### 1. 安装依赖（PDF 支持，可选）

```bash
pip install pymupdf
```

如果不安装，PDF 解析功能将被禁用，其他功能正常使用。

---

## 📚 知识库结构化处理

### 上传文档（带自动提取）

**通过 Web UI：**
1. 访问 `/admin/knowledge`
2. 点击 "Upload Document"
3. 选择文件（支持 TXT、MD、PDF）
4. 确保 "Enable Processing" 已勾选（默认开启）
5. 上传后自动提取实体、标签、摘要

**通过 API：**
```bash
curl -X POST http://localhost:8000/api/v1/admin/knowledge/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf" \
  -F "enable_processing=true" \
  -F "doc_type=knowledge" \
  -F "source=Q3 Playbook"
```

**响应示例：**
```json
{
  "id": "doc-uuid",
  "filename": "document.pdf",
  "message": "Upload and processing successful",
  "chunks_added": 15,
  "entities": ["信用卡", "年费", "权益"],
  "tags": ["产品介绍", "价格说明"],
  "summary": "本文档介绍了信用卡的年费政策和相关权益..."
}
```

### 查看文档详情

在知识库列表中，点击任意文档行即可查看：
- 完整摘要
- 提取的标签和实体
- 关键要点列表
- 内容预览

---

## 🛡️ 合规规则批量导入

### CSV 格式示例

创建 `compliance_rules.csv`：
```csv
pattern,risk_type,severity,reason,alternative
"绝对.*保证",exaggeration,high,"使用绝对化承诺","根据过往经验，大多数情况下可以..."
"稳赚.*保本",misleading,high,"虚假收益承诺","根据历史数据，收益表现稳定，但不代表未来..."
"内部消息",misleading,high,"暗示内幕信息","根据公开信息和专业分析..."
```

### JSON 格式示例

创建 `compliance_rules.json`：
```json
[
  {
    "pattern": "绝对.*保证",
    "risk_type": "exaggeration",
    "severity": "high",
    "reason": "使用绝对化承诺",
    "alternative": "根据过往经验，大多数情况下可以..."
  },
  {
    "pattern": "稳赚.*保本",
    "risk_type": "misleading",
    "severity": "high",
    "reason": "虚假收益承诺",
    "alternative": "根据历史数据，收益表现稳定，但不代表未来..."
  }
]
```

### 批量导入

**通过 Web UI：**
1. 访问 `/admin/compliance`
2. 点击 "Batch Import"
3. 选择 CSV 或 JSON 文件
4. 点击 "Import"
5. 查看导入结果（成功/失败统计）

**通过 API：**
```bash
curl -X POST http://localhost:8000/api/v1/admin/compliance/rules/batch-import \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@compliance_rules.csv"
```

**响应示例：**
```json
{
  "success": true,
  "created_count": 25,
  "skipped_count": 2,
  "errors": ["Row 5: Invalid severity value"]
}
```

---

## 📊 合规统计仪表盘

访问 `/admin/compliance` 查看实时统计：

- **Active Rules**: 当前启用的规则总数
- **Violations Today**: 今日被拦截的违规消息数
- **High Risk Rules**: 高风险规则数量
- **Risk Level**: 整体风险等级（Low/Medium/High）

统计数据每30秒自动刷新。

---

## 🔍 RAG 检索性能测试

### 运行压力测试

```bash
python scripts/test_rag_performance.py
```

**测试内容：**
- 单查询响应时间
- 并发查询性能（10个并发）
- 检索相关性准确性
- 自动生成优化建议

**输出示例：**
```
=== Starting RAG Performance Test Suite ===
1. Testing single queries...
  Query: 信用卡年费是多少？... | Time: 145.23ms | Relevance: 0.82
  ...

2. Testing concurrent queries...
  Total: 10 queries
  Successful: 10
  Avg Response Time: 156.78ms
  Queries/Second: 6.37
  Avg Relevance: 0.79

3. Testing relevance accuracy...
  Test Cases: 2
  Avg Accuracy: 85.00%

Recommendations:
  - 响应时间良好
  - 相关性良好
  - 检索准确性优秀
```

---

## 🎯 最佳实践

### 知识库管理

1. **文档准备**
   - 使用清晰的文档结构（标题、段落）
   - 避免过长的单个文档（建议 < 10MB）
   - PDF 文档确保文本可提取（非扫描版）

2. **文档类型选择**
   - `knowledge`: 通用知识文档
   - `script`: 销售话术模板
   - `case`: 成功案例
   - `faq`: 常见问答

3. **结构化提取**
   - 启用 `enable_processing` 以自动提取实体和标签
   - 检查提取结果，必要时手动调整标签
   - 使用标签和实体进行知识库检索过滤

### 合规规则管理

1. **规则设计**
   - 使用正则表达式匹配模式
   - 设置合适的严重程度（high/medium/low）
   - 提供清晰的替代建议

2. **批量导入**
   - 先小批量测试（10-20条规则）
   - 验证规则效果后再大规模导入
   - 定期审查和更新规则

3. **监控和优化**
   - 定期查看合规统计
   - 分析违规日志，识别新风险模式
   - 根据业务需求调整规则优先级

### RAG 检索优化

1. **查询优化**
   - 使用具体的关键词
   - 包含销售阶段信息（如 "产品介绍阶段：信用卡年费"）
   - 避免过于宽泛的查询

2. **相关性阈值**
   - 默认 `min_relevance=0.5`，可根据需求调整
   - 提高阈值可减少无关结果，但可能遗漏相关内容
   - 降低阈值可增加召回率，但可能包含噪声

3. **性能监控**
   - 定期运行性能测试脚本
   - 监控响应时间，超过 500ms 需要优化
   - 关注相关性分数，低于 0.6 需要改进

---

## 🐛 故障排除

### PDF 解析失败

**错误：** `PDF parsing requires PyMuPDF`

**解决：**
```bash
pip install pymupdf
```

### 实体提取返回空结果

**原因：** LLM API 未配置或调用失败

**解决：**
1. 检查 `OPENAI_API_KEY` 环境变量
2. 检查网络连接
3. 系统会自动降级到关键词提取模式

### 批量导入部分规则失败

**检查：**
1. CSV 格式是否正确（逗号分隔，UTF-8编码）
2. 必填字段是否完整（pattern, reason）
3. severity 值是否有效（high/medium/low）
4. 查看错误列表了解具体原因

### RAG 检索结果不相关

**优化建议：**
1. 检查知识库中是否有相关内容
2. 调整 `min_relevance` 参数
3. 优化查询文本，添加更多上下文
4. 检查文档的标签和实体是否正确提取

---

## 📞 支持

如有问题，请查看：
- `IMPLEMENTATION_SUMMARY.md` - 详细实现文档
- `app/services/document_parser.py` - 文档解析源码
- `app/api/endpoints/admin/` - API 端点源码



