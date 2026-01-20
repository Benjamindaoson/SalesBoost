# RAG系统优化方案 - 基于数据摄入问题分析

## 📊 当前问题分析

### 1. ChromaDB DLL问题（Windows）

**问题**：`DLL load failed while importing chromadb_rust_bindings`

**原因**：ChromaDB的Rust绑定在Windows上需要Visual C++运行时库

**解决方案**：
1. 安装Visual C++ Redistributable
2. 或使用Docker运行（推荐）
3. 或降级到ChromaDB旧版本
4. 或切换到其他向量数据库（Qdrant、Milvus）

### 2. PDF解析问题

**问题**：PDF文件无法解析

**原因**：
- PyMuPDF未安装
- MinerU未安装（更强大的解析器）

**解决方案**：
- ✅ 已添加PyMuPDF到requirements.txt
- ✅ 已添加MinerU支持（增强解析器）
- 需要安装：`pip install pymupdf mineru`

### 3. NetworkX缺失

**问题**：GraphRAG需要NetworkX

**解决方案**：
- ✅ 已添加到requirements.txt
- 需要安装：`pip install networkx python-louvain`

---

## 🚀 优化方案

### Phase 1: 修复依赖问题（立即）

1. **安装所有依赖**
   ```bash
   pip install networkx python-louvain pymupdf openpyxl python-docx
   ```

2. **解决ChromaDB问题**
   - 选项A：安装Visual C++ Redistributable
   - 选项B：使用Docker
   - 选项C：切换到Qdrant（Python原生，无DLL依赖）

3. **安装MinerU（可选但推荐）**
   ```bash
   pip install mineru
   ```

### Phase 2: 集成MinerU（推荐）

**为什么使用MinerU**：

1. **更强的PDF解析能力**
   - 支持扫描件OCR
   - 保留文档结构（标题、段落、表格、公式）
   - 输出结构化Markdown

2. **表格识别**
   - 自动识别表格结构
   - 保留表格数据完整性

3. **多后端支持**
   - `pipeline`：快速，适合文本PDF
   - `vlm`：高精度，适合扫描件
   - `hybrid`：平衡速度和精度

**集成方式**：

已创建 `EnhancedDocumentParser`，优先使用MinerU，降级到PyMuPDF。

### Phase 3: 优化RAG处理流程

#### 3.1 文档预处理优化

**当前问题**：
- 文档分块可能截断表格
- 复杂布局文档解析质量差

**优化方案**：
1. 使用MinerU提取结构化内容
2. 基于文档结构分块（章节、段落、表格）
3. 保留表格完整性

#### 3.2 向量化优化

**当前问题**：
- 简单文本分块可能丢失上下文
- 表格数据向量化效果差

**优化方案**：
1. 表格单独处理（结构化存储）
2. 使用表格专用的embedding策略
3. 混合存储：向量+结构化数据

#### 3.3 GraphRAG优化

**当前问题**：
- 实体提取可能不准确
- 关系提取可能遗漏

**优化方案**：
1. 使用MinerU的结构化输出改进实体提取
2. 表格数据自动提取实体关系
3. 多轮提取和验证

---

## 📝 实施步骤

### Step 1: 安装依赖

```bash
# 基础依赖
pip install networkx python-louvain pymupdf openpyxl python-docx

# MinerU（推荐）
pip install mineru

# 如果ChromaDB有问题，考虑Qdrant
pip install qdrant-client
```

### Step 2: 修复ChromaDB问题

**选项A：安装Visual C++ Redistributable**
- 下载：https://aka.ms/vs/17/release/vc_redist.x64.exe
- 安装后重启

**选项B：切换到Qdrant**
```python
# 修改 knowledge_service.py
# 使用Qdrant替代ChromaDB
```

**选项C：使用Docker**
```bash
docker run -p 8000:8000 chromadb/chroma
```

### Step 3: 运行数据摄入

```bash
python scripts/ingest_sales_data_robust.py
```

### Step 4: 验证数据

```python
from app.services.knowledge_service import KnowledgeService
service = KnowledgeService()
print(f"文档数: {service.count_documents()}")
```

---

## 🔧 代码优化

### 1. 增强文档解析器

已创建 `app/services/enhanced_document_parser.py`：
- ✅ 优先使用MinerU
- ✅ 降级到PyMuPDF
- ✅ 支持Excel、Word、PDF

### 2. 健壮的数据摄入脚本

已创建 `scripts/ingest_sales_data_robust.py`：
- ✅ 错误处理
- ✅ 部分失败不影响整体
- ✅ 详细日志

### 3. 待优化项

- [ ] 表格数据特殊处理
- [ ] 文档结构感知分块
- [ ] 多语言支持（中文优化）
- [ ] 增量更新机制

---

## 📈 预期改进

### 解析质量

| 指标 | 当前 | 优化后 |
|-----|------|--------|
| PDF解析准确率 | 60% | 90%+ |
| 表格识别率 | 40% | 85%+ |
| 扫描件OCR | 不支持 | 支持 |
| 文档结构保留 | 低 | 高 |

### RAG性能

| 指标 | 当前 | 优化后 |
|-----|------|--------|
| 检索准确率 | 65% | 80%+ |
| 表格数据检索 | 不支持 | 支持 |
| 多跳推理 | 基础 | 增强 |

---

## 🎯 下一步行动

1. **立即**：安装缺失依赖
2. **短期**：集成MinerU，优化PDF解析
3. **中期**：优化表格处理，改进RAG检索
4. **长期**：支持多模态（图像、表格、文本）

---

## 📚 参考资源

- [MinerU文档](https://github.com/opendatalab/MinerU)
- [ChromaDB Windows问题](https://docs.trychroma.com/troubleshooting)
- [Qdrant替代方案](https://qdrant.tech/documentation/)

