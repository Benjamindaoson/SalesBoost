# RAG 评估指南

## 快速开始

### 1. 安装依赖

```bash
pip install ragas langchain openai datasets pandas
```

### 2. 运行压测

```bash
# WebSocket 压测 - 10 用户
cd d:/SalesBoost
locust -f tests/performance/locust_websocket_test.py --host=ws://localhost:8000 -u 10 -r 2 --run-time 60s --headless --html=tests/performance/reports/load_test_10users.html

# WebSocket 压测 - 50 用户
locust -f tests/performance/locust_websocket_test.py --host=ws://localhost:8000 -u 50 -r 5 --run-time 120s --headless --html=tests/performance/reports/load_test_50users.html

# WebSocket 压测 - 100 用户
locust -f tests/performance/locust_websocket_test.py --host=ws://localhost:8000 -u 100 -r 10 --run-time 180s --headless --html=tests/performance/reports/load_test_100users.html
```

### 3. 运行 RAG 评估

```bash
cd d:/SalesBoost
python tests/evaluation/rag_evaluation.py
```

## 文件说明

- `rag_test_dataset.json` - 50个标注的测试样本
- `rag_evaluation.py` - RAGAS评估脚本
- `locust_websocket_test.py` - WebSocket压测脚本
- `locust_rest_api_test.py` - REST API压测脚本

## 评估指标

### RAG 指标
- **Faithfulness**: 答案是否基于检索到的上下文
- **Answer Relevancy**: 答案与问题的相关性
- **Context Precision**: 相关上下文的排序质量
- **Context Recall**: 是否检索到所有相关信息

### 性能指标
- **P50/P95/P99 延迟**: 响应时间百分位数
- **QPS**: 每秒请求数
- **失败率**: 请求失败百分比
- **并发用户数**: 同时在线用户数

## 真实数据 vs 理论估算

### ✅ 已验证（有真实测试）
- Locust 压测结果
- RAGAS 评估分数

### ⚠️ 待验证（理论估算）
- 文档中声称的"P50 420ms"需要用压测验证
- 文档中声称的"Hit@5 85%"需要用RAGAS验证

## 下一步

1. 运行压测获取真实性能数据
2. 运行RAGAS获取真实RAG指标
3. 更新文档，用真实数据替换估算值
4. 建立持续评估流程（CI/CD集成）
