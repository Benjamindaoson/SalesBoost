我将按照“Staff+ 工程师”的标准，分阶段、系统性地将 SalesBoost 升级为可售卖的 SaaS 产品。我已制定了详细的实施计划，涵盖数据库修复、租户体系、管理后台、WS 稳定性及创新功能补齐。

### **实施拆解与执行计划**

## **Phase 1: 基础设施与数据层 (P0) - \[Step 1]**

## **目标**：构建稳固的多租户数据底座，修复迁移问题，确保“有地可建”。

## **SaaS 数据模型**:

## 新增 `Tenant` (租户), `User` (用户/学员), `Subscription` (订阅/计费) 模型。

## 确保 `TenantMixin` 正确应用于所有核心业务表。

## **DB Migration 修复**:

## 排查并修复 `alembic` 配置，确保能从零 `init` 并 `upgrade head`。

## 编写 `scripts/check_db_consistency.py`，用于启动时自检。

1. **租户隔离验证**: 确保查询自动附加 `tenant_id` 过滤（通过 Session 上下文或 DAO 层封装）。

#### **Phase 2: 管理端 UI 与鉴权 (P0) - \[Step 2, Step 3]**

**目标**：提供可视化的运营能力，让运营人员能“干活”。

1. **Admin UI 实现**:

   * 基于 `shadcn/ui` 快速搭建 CRUD 页面：`Courses`, `Personas`, `Scenarios`, `Knowledge`, `Evaluations`。

   * 实现 `AuditLog` (审计日志) 界面。
2. **鉴权与 SaaS 外围**:

   * 实现 `/admin/login` 与 `/login` (学员端)。

   * 中间件实现：解析 Token -> 获取 Tenant -> 注入 Context。

   * 实现基础 Gating：根据 `Subscription` 限制训练次数或功能。

#### **Phase 3: 生产级 WebSocket (P0) - \[Step 4]**

**目标**：确保多人同时训练不掉线、不串台。

1. **稳定性增强**:

   * 实现前端心跳 (`ping/pong`) 与断线自动重连 (`reconnect_interval`)。

   * 后端实现“僵尸连接清理”任务。
2. **分布式能力**:

   * 基于 Redis Pub/Sub 实现跨实例消息广播（模拟多实例环境验证）。
3. **限流与监控**:

   * 实现简单的 Token Bucket 限流。

   * 暴露 `/metrics` 接口（Prometheus 格式）。

#### **Phase 4: 硅谷差距补齐 (P1) - \[Step 5]**

**目标**：提升产品竞争力，从“能用”到“好用”。

1. **多模态 (E1)**: 定义 ASR/TTS 接口，前端增加“语音模式”开关（模拟）。
2. **超个性化 (E2)**: 实现“导入 CSV 生成 Persona”的 API 与界面。
3. **Live Copilot (E3)**: 在练习室增加“Copilot 侧栏”，支持粘贴文本分析。

#### **Phase 5: 验收与交付 (P0) - \[Step 6]**

**目标**：确保交付物质量。

1. **端到端测试**: 手动跑通“注册 -> 配置 -> 训练 -> 报表”全流程。
2. **文档**: 更新 README，包含部署、迁移、双实例测试指南。

***

**风险点预判**:

1. **DB Migration**: 现有代码可能存在模型定义与数据库状态不一致，需暴力修正（可能需要清库重建）。
2. **前端工作量**: Admin UI 页面较多，将采用“通用组件 + 配置化”方式提效，不追求极致美观，只求功能完整。
3. **WS 广播**: 本地单机模拟多实例广播需要技巧（启动不同端口进程）。

我将从 **Step 1: 数据库迁移修复与租户体系初始化** 开始执行。
