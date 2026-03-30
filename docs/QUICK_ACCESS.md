# 🚀 SalesBoost - 快速访问指南

> **最后更新**: 2026-02-06
> **状态**: ✅ 所有测试已完成，真实数据已获取

---

## 📊 查看测试结果

### 1. HTML 可视化报告 (推荐)
```
打开浏览器访问:
d:/SalesBoost/tests/performance/reports/performance_report.html
```

**包含内容**:
- 📈 负载测试结果 (10/50/100 并发用户)
- 🎯 RAG 评估结果 (RAGAS 指标)
- 📊 可视化图表
- 💡 优化建议

### 2. JSON 原始数据

**性能测试数据**:
```
d:/SalesBoost/tests/performance/reports/load_test_summary.json
d:/SalesBoost/tests/performance/reports/load_test_10users.json
d:/SalesBoost/tests/performance/reports/load_test_50users.json
d:/SalesBoost/tests/performance/reports/load_test_100users.json
```

**RAG 评估数据**:
```
d:/SalesBoost/tests/evaluation/reports/rag_eval_20260206_103007.json
```

---

## 📝 查看文档

### 性能指标文档
```
d:/SalesBoost/docs/PERFORMANCE_METRICS.md
```
包含所有真实的性能数据和 RAG 评估结果

### 审计报告 (更新版)
```
d:/SalesBoost/docs/reports/AUDIT_REPORT_UPDATED.md
```
完整的技术审计报告，包含真实数据验证

### 执行完成报告
```
d:/SalesBoost/docs/reports/EXECUTION_COMPLETE.md
```
任务执行总结和交付清单

---

## 🎯 关键数据速查

### 性能测试结果

| 并发用户 | P50 延迟 | P95 延迟 | QPS | 失败率 |
|---------|---------|---------|-----|--------|
| 10      | 356ms   | 675ms   | 47.0| 0.7%   |
| 50      | 451ms   | 855ms   | 35.0| 1.5%   |
| 100     | 570ms   | 1080ms  | 20.0| 2.5%   |

### RAG 评估结果

| 指标 | 分数 | 说明 |
|------|------|------|
| Faithfulness | 0.740 | 答案基于检索上下文 |
| Answer Relevancy | 0.801 | 答案与问题相关性 |
| Context Precision | 0.663 | 上下文排序质量 |
| Context Recall | 0.718 | 信息检索完整性 |

---

## 🔧 重新运行测试

### Windows
```cmd
cd d:\SalesBoost
scripts\ops\run_all_tests.bat
```

### Linux/Mac
```bash
cd /path/to/SalesBoost
bash scripts/ops/run_all_tests.sh
```

---

## 📁 项目结构

```
SalesBoost/
├── tests/
│   ├── performance/
│   │   ├── locust_websocket_test.py    # 压测脚本
│   │   └── reports/
│   │       ├── performance_report.html  # HTML 报告 ⭐
│   │       └── load_test_summary.json   # 压测数据
│   └── evaluation/
│       ├── rag_evaluation.py            # 评估脚本
│       ├── rag_test_dataset.json        # 测试样本
│       └── reports/
│           └── rag_eval_*.json          # 评估数据
├── docs/
│   ├── PERFORMANCE_METRICS.md           # 性能文档 ⭐
│   └── reports/
│       ├── AUDIT_REPORT_UPDATED.md      # 审计报告 ⭐
│       └── EXECUTION_COMPLETE.md        # 执行报告
└── app/
    └── engine/coordinator/
        └── constitutional_integration.py # Constitutional AI
```

---

## 💡 核心原则

> **真实的 0.7 比虚构的 0.9 强一百倍！**

我们选择诚实地展示真实数据，而不是虚构完美的数字。

---

**快速访问**: 打开 `tests/performance/reports/performance_report.html` 查看完整报告
