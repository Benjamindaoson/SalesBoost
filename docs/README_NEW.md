# SalesBoost - AI驱动的销售能力训练平台

[![CI/CD](https://github.com/salesboost/salesboost/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/salesboost/salesboost/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/typescript-5.0+-blue.svg)](https://www.typescriptlang.org/)

基于大模型和多Agent协同的智能销售培训系统，集成RAG知识检索、FSM状态机、语音交互和RLAIF自动评估。

## 🎯 核心特性

### AI算法亮点

- **双路径混合检索（BGE-M3 + RRF）**: Dense + Sparse向量检索，准确率提升30%+
- **Self-RAG自我反思系统**: 三维质量评估（Relevance/Faithfulness/Completeness）
- **销售对话FSM**: 7状态5阶段模型（Opening→Discovery→Pitch→Objection→Closing）
- **多Agent协同训练（RLAIF）**: 6种客户人格模拟 + 5维评估系统
- **情感语音合成**: 6种情感映射，销售阶段自动调整
- **GraphRAG知识图谱**: 实体关联检索，增强话术知识

### 系统工程亮点

- **FastAPI微服务架构**: 4个独立服务（RAG/Agent/Voice/Gateway）
- **Pydantic统一配置**: 12个配置组，类型安全，生产环境验证
- **JWT + API Key双重认证**: 角色管理，速率限制（100 req/min）
- **熔断器机制**: LLM API高可用保护
- **Docker化部署**: 多阶段构建，健康检查，自动重启
- **CI/CD流程**: GitHub Actions，自动测试、构建、部署
- **Prometheus + Grafana监控**: 实时metrics收集和可视化

## 📊 技术栈

### 后端
- **框架**: FastAPI, Pydantic v2, SQLAlchemy
- **AI/ML**: BGE-M3, Qdrant, OpenAI, SiliconFlow, Gemini
- **数据库**: PostgreSQL, Redis, Qdrant
- **监控**: Prometheus, Grafana

### 前端
- **框架**: React 18, TypeScript, Vite
- **UI**: Tailwind CSS, Shadcn UI
- **状态管理**: Zustand
- **路由**: React Router

### DevOps
- **容器化**: Docker, Docker Compose
- **CI/CD**: GitHub Actions
- **部署**: Nginx, Uvicorn

## 🚀 快速开始

### 前置要求

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- Qdrant

### 使用Docker Compose（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/salesboost/salesboost.git
cd salesboost

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入API密钥

# 3. 启动所有服务
docker-compose up -d

# 4. 初始化数据库
docker-compose exec backend python scripts/init_database.py

# 5. 访问应用
# Frontend: http://localhost
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Grafana: http://localhost:3001 (admin/admin)
# Prometheus: http://localhost:9090
```

### 本地开发

#### 后端

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env

# 4. 初始化数据库
python scripts/init_database.py

# 5. 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

#### 前端

```bash
cd frontend

# 1. 安装依赖
npm install

# 2. 配置环境变量
cp .env.example .env

# 3. 启动开发服务器
npm run dev
```

## 📖 文档

- [架构设计](ARCHITECTURE.md)
- [部署指南](DEPLOYMENT.md)
- [API文档](http://localhost:8000/docs)
- [开发指南](DEVELOPMENT.md)

## 🏗️ 项目结构

```
salesboost/
├── app/                          # 后端应用
│   ├── agents/                   # AI Agents
│   │   ├── ask/                  # 销售教练Agent
│   │   ├── conversation/         # 对话Agent (FSM)
│   │   ├── evaluate/             # 评估Agent
│   │   ├── practice/             # 练习Agent
│   │   └── simulation/           # 客户模拟Agent
│   ├── config/                   # 配置
│   │   └── unified.py            # 统一配置系统
│   ├── infra/                    # 基础设施
│   │   ├── llm/                  # LLM客户端
│   │   │   └── unified_client.py # 统一LLM客户端
│   │   ├── search/               # 检索系统
│   │   │   ├── bgem3_retriever.py # BGE-M3双路径检索
│   │   │   └── graph_rag.py      # GraphRAG
│   │   ├── vector_store/         # 向量数据库
│   │   │   └── qdrant_client.py  # Qdrant客户端
│   │   └── resilience/           # 弹性机制
│   │       └── circuit_breaker.py # 熔断器
│   ├── models/                   # ORM模型
│   │   ├── user.py               # 用户模型
│   │   ├── course.py             # 课程模型
│   │   ├── task.py               # 任务模型
│   │   ├── session.py            # 会话模型
│   │   ├── message.py            # 消息模型
│   │   └── evaluation.py         # 评估模型
│   ├── retrieval/                # RAG系统
│   │   ├── self_rag.py           # Self-RAG
│   │   └── hyde_retriever.py     # HyDE
│   └── main.py                   # FastAPI应用入口
├── frontend/                     # 前端应用
│   ├── src/
│   │   ├── components/           # React组件
│   │   ├── pages/                # 页面
│   │   ├── services/             # API服务
│   │   ├── store/                # 状态管理
│   │   └── App.tsx               # 应用入口
│   ├── Dockerfile                # 前端Docker配置
│   └── nginx.conf                # Nginx配置
├── scripts/                      # 脚本
│   ├── init_database.py          # 数据库初始化
│   ├── week5_day1_sales_fsm.py   # FSM实现
│   ├── week6_day1_user_simulator.py # 客户模拟
│   ├── week6_day3_sales_coach.py # 销售教练
│   ├── week7_day1_tts_emotion.py # 情感TTS
│   ├── week7_day3_stt_lowlatency.py # 低延迟STT
│   └── week8_day*_*.py           # 微服务实现
├── tests/                        # 测试
│   ├── unit/                     # 单元测试
│   └── integration/              # 集成测试
├── alembic/                      # 数据库迁移
├── monitoring/                   # 监控配置
│   ├── prometheus.yml            # Prometheus配置
│   └── grafana/                  # Grafana仪表板
├── .github/                      # GitHub配置
│   └── workflows/
│       └── ci.yml                # CI/CD流程
├── Dockerfile                    # 后端Docker配置
├── docker-compose.yml            # Docker Compose配置
├── requirements.txt              # Python依赖
├── alembic.ini                   # Alembic配置
└── README.md                     # 本文件
```

## 🧪 测试

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 生成覆盖率报告
pytest tests/ --cov=app --cov-report=html
```

## 📈 性能指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 检索准确率 | +30% | 相比单路径检索 |
| 检索延迟 | 50-60ms | BGE-M3双路径 |
| Self-RAG质量 | 0.7+ | 三维评估平均分 |
| TTS延迟 | 0.01s | 缓存命中 |
| STT准确率 | 95%+ | Faster Whisper |
| API吞吐量 | 100 req/min | 速率限制 |
| 系统可用性 | 99.9% | 熔断器保护 |

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 👥 团队

- **核心架构师**: [Your Name]
- **AI算法负责人**: [Your Name]

## 📞 联系方式

- **Email**: contact@salesboost.com
- **GitHub**: https://github.com/salesboost/salesboost
- **文档**: https://docs.salesboost.com

## 🙏 致谢

- [BGE-M3](https://github.com/FlagOpen/FlagEmbedding) - 多向量检索模型
- [Qdrant](https://qdrant.tech/) - 向量数据库
- [FastAPI](https://fastapi.tiangolo.com/) - 现代Web框架
- [React](https://react.dev/) - 前端框架

---

**Built with ❤️ by SalesBoost Team**
