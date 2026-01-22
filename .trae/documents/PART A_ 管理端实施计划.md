我将严格按照您的角色定义（Senior Full-Stack Engineer & AI Platform Implementer）和 MVP 交付标准，分阶段落地 **PART A: 管理端（Admin Panel）**。

这是本轮对话的执行计划：

### **PART A: 管理端 (Admin Panel) 实施计划**

#### **Step 1: 后端基础设施与 CRUD (Backend)**
**目标**: 实现 `/api/v1/admin/*` 下的核心资源管理接口，并确保数据落库。
1.  **创建 Admin 路由模块**:
    *   在 `app/api/endpoints/admin/` 下创建 `courses.py`, `personas.py`, `scenarios.py`, `evaluation.py`。
    *   在 `app/main.py` 中注册这些路由。
2.  **实现核心 CRUD**:
    *   **Course/Scenario/Persona**: 基于 `app/models/config_models.py` 实现增删改查。
    *   **EvaluationConfig**: 新建 `evaluation_dimensions` 表（通过 Alembic），并实现配置接口。
3.  **集成 EvaluatorAgent**:
    *   修改 `EvaluatorAgent`，使其不再使用硬编码的评分维度，而是从 DB (或 Redis 缓存) 读取配置。

#### **Step 2: 前端管理控制台 (Frontend)**
**目标**: 为管理员提供可视化的配置界面。
1.  **搭建 Admin Layout**:
    *   创建 `AdminLayout`，包含侧边栏导航（Dashboard, Courses, Personas, Evaluation）。
    *   配置路由 `/admin/*`。
2.  **实现管理页面**:
    *   **Courses/Personas**: 列表页 + 编辑/新建模态框（使用 shadcn/ui 表单）。
    *   **EvaluationConfig**: 维度权重配置页（支持拖拽或数字输入）。

#### **Step 3: 验证与验收**
1.  **功能验证**:
    *   在管理端创建一个新的 Persona（例如“极其挑剔的CFO”）。
    *   在管理端调整“信任建立”维度的权重。
2.  **闭环验证**:
    *   切换到学员端，验证新 Persona 是否可选。
    *   进行一轮对话，验证 Evaluator 的评分是否反映了新的权重设置。

---

**是否同意我立即开始执行 Step 1 (后端基础设施与 CRUD)？**
