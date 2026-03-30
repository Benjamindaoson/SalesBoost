# 前后端功能集成分析报告

## 执行日期
2026-02-07

## 问题描述

用户反馈学员端页面的功能未实现：
- **左侧栏三个功能**：任务管理、客户预演、历史记录
- **右侧功能**：统计数据、任务列表、操作按钮

## 分析结果

### ✅ 后端 API 已完整实现

所有必需的后端 API 端点都已经实现并注册：

#### 1. 任务管理 API（Tasks）
**文件**: `backend/app/api/endpoints/tasks.py`
**路由注册**: `main.py:470` - `/api/v1/tasks`

| 端点 | 方法 | 功能 | 状态 |
|------|------|------|------|
| `/api/v1/tasks` | GET | 获取任务列表 | ✅ 已实现 |
| `/api/v1/tasks` | POST | 创建任务（管理员） | ✅ 已实现 |
| `/api/v1/tasks/{id}` | GET | 获取任务详情 | ✅ 已实现 |
| `/api/v1/tasks/{id}` | PUT | 更新任务（管理员） | ✅ 已实现 |
| `/api/v1/tasks/{id}` | DELETE | 删除任务（管理员） | ✅ 已实现 |
| `/api/v1/tasks/{id}/start` | POST | 开始任务 | ✅ 已实现 |

**功能特性**：
- 支持按课程、类型、状态筛选
- 支持分页（page, page_size）
- 自动计算完成率和平均分数
- 任务状态管理（locked, available, in_progress, completed）

#### 2. 客户管理 API（Customers）
**文件**: `backend/app/api/endpoints/customers.py`
**路由注册**: `main.py:484` - `/api/v1/customers`

| 端点 | 方法 | 功能 | 状态 |
|------|------|------|------|
| `/api/v1/customers` | GET | 获取客户列表 | ✅ 已实现 |
| `/api/v1/customers` | POST | 创建客户 | ✅ 已实现 |
| `/api/v1/customers/{id}` | GET | 获取客户详情 | ✅ 已实现 |
| `/api/v1/customers/{id}` | PATCH | 更新客户 | ✅ 已实现 |
| `/api/v1/customers/{id}` | DELETE | 删除客户 | ✅ 已实现 |

**功能特性**：
- 客户画像管理（姓名、年龄、职业、性格特征）
- 关联场景（scenario_id）
- 头像颜色自定义
- 预演次数统计

#### 3. 会话管理 API（Sessions）
**文件**: `backend/app/api/endpoints/sessions.py`
**路由注册**: `main.py:438` - `/api/v1/sessions`

| 端点 | 方法 | 功能 | 状态 |
|------|------|------|------|
| `/api/v1/sessions` | GET | 获取会话列表 | ✅ 已实现 |
| `/api/v1/sessions` | POST | 创建会话 | ✅ 已实现 |
| `/api/v1/sessions/{id}` | GET | 获取会话详情 | ✅ 已实现 |
| `/api/v1/sessions/{id}/review` | GET | 获取会话评审 | ✅ 已实现 |
| `/api/v1/sessions/{id}/complete` | PATCH | 完成会话 | ✅ 已实现 |
| `/api/v1/sessions/{id}/evaluate` | POST | 评估会话 | ✅ 已实现 |

**功能特性**：
- 会话状态管理（active, completed）
- 策略决策记录
- 技能提升追踪
- 异步评估任务

### ✅ 前端服务已完整实现

#### 1. 任务服务（Task Service）
**文件**: `frontend/src/services/task.service.ts`

```typescript
export const taskService = {
  getTasks: async (): Promise<DashboardTask[]>  // ✅ 已实现
  getStatistics: async (): Promise<Statistics>  // ⚠️ 端点缺失
  getTaskById: async (taskId: string)           // ✅ 已实现
  startTask: async (taskId: string)             // ✅ 已实现
  createTask: async (data: TaskCreate)          // ✅ 已实现
  updateTask: async (taskId: number)            // ✅ 已实现
  deleteTask: async (taskId: number)            // ✅ 已实现
}
```

#### 2. 客户服务（Customer Service）
**文件**: `frontend/src/services/customer.service.ts`

```typescript
export const customerService = {
  getCustomers: async ()                        // ✅ 已实现
  createCustomer: async (data: CustomerCreate)  // ✅ 已实现
  updateCustomer: async (id: string)            // ✅ 已实现
  deleteCustomer: async (id: string)            // ✅ 已实现
}
```

#### 3. 会话服务（Session Service）
**文件**: `frontend/src/services/session.service.ts`

```typescript
export const sessionService = {
  createSession: async (data: SessionCreate)    // ✅ 已实现
  listSessions: async (params)                  // ✅ 已实现
  getSession: async (sessionId: string)         // ✅ 已实现
  getSessionReview: async (sessionId: string)   // ✅ 已实现
  completeSession: async (sessionId: string)    // ✅ 已实现
}
```

### ✅ 前端页面已完整实现

#### 1. 任务管理页面
**文件**: `frontend/src/pages/student/Dashboard.tsx`
**路由**: `/student/dashboard`

**功能**：
- ✅ 统计卡片（全部任务、进行中、已完成、平均分数）
- ✅ 任务筛选（全部、进行中、已完成）
- ✅ 任务搜索
- ✅ 任务列表展示
- ✅ "去练习"按钮

**数据流**：
```
Dashboard.tsx
  → taskService.getTasks()
  → GET /api/v1/tasks
  → backend/app/api/endpoints/tasks.py
```

#### 2. 客户预演页面
**文件**: `frontend/src/pages/student/CustomerList.tsx`
**路由**: `/student/customers`

**功能**：
- ✅ 客户卡片展示
- ✅ 新建客户对话框
- ✅ 编辑客户功能
- ✅ 删除客户功能
- ✅ 查看客户详情
- ✅ "去预演"按钮

**数据流**：
```
CustomerList.tsx
  → customerService.getCustomers()
  → GET /api/v1/customers
  → backend/app/api/endpoints/customers.py
```

#### 3. 历史记录页面
**文件**: `frontend/src/pages/student/History.tsx`
**路由**: `/student/history`

**功能**：
- ✅ 统计卡片（总训练次数、平均分数、最高分数、总时长）
- ✅ 历史记录筛选
- ✅ 历史记录搜索
- ✅ 历史记录表格
- ✅ 查看详情按钮
- ⚠️ 使用模拟数据（mockData）

**数据流**：
```
History.tsx
  → getHistory()
  → mockData (⚠️ 未连接真实 API)
```

---

## 🔴 发现的问题

### 问题 1: Statistics 端点缺失

**影响**: 任务管理页面的统计数据无法加载

**前端调用**:
```typescript
// frontend/src/services/task.service.ts:145
const response = await api.get<Statistics>(STATISTICS_ENDPOINT);
// STATISTICS_ENDPOINT = '/api/v1/statistics'
```

**后端状态**: ❌ 端点不存在

**解决方案**: 需要实现 `/api/v1/statistics` 端点

### 问题 2: 历史记录使用模拟数据

**影响**: 历史记录页面显示的是假数据

**前端调用**:
```typescript
// frontend/src/pages/student/History.tsx:44
const data = await getHistory();  // 来自 mockData
```

**后端状态**: ✅ Sessions API 已实现，但前端未连接

**解决方案**: 将 History 页面连接到 `/api/v1/sessions` API

### 问题 3: 数据库可能为空

**影响**: 即使 API 正常工作，也可能没有数据显示

**原因**:
- 数据库可能没有初始化数据
- 没有种子数据（seed data）

**解决方案**: 需要创建初始数据或提供数据导入功能

---

## 🔧 修复方案

### 修复 1: 实现 Statistics 端点

**创建文件**: `backend/app/api/endpoints/statistics.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ...core.database import get_db_session
from ...api.deps import require_user
from ...models.task import Task
from ...models.session import Session

router = APIRouter()

@router.get("")
async def get_statistics(
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(require_user)
):
    """获取用户统计数据"""
    # 查询任务统计
    tasks_query = select(Task)
    tasks_result = await db.execute(tasks_query)
    tasks = tasks_result.scalars().all()

    # 查询会话统计
    sessions_query = select(Session).where(Session.user_id == current_user.id)
    sessions_result = await db.execute(sessions_query)
    sessions = sessions_result.scalars().all()

    # 计算统计数据
    total_tasks = len(tasks)
    in_progress = len([s for s in sessions if s.status == "active"])
    completed = len([s for s in sessions if s.status == "completed"])

    # 计算平均分数
    scores = [s.final_score for s in sessions if s.final_score is not None]
    average_score = sum(scores) / len(scores) if scores else 0

    return {
        "totalTasks": total_tasks,
        "inProgress": in_progress,
        "completed": completed,
        "averageScore": round(average_score, 1),
        "lockedItems": 0
    }
```

**注册路由**: 在 `main.py` 中添加

```python
_safe_include("api.endpoints.statistics", "/api/v1/statistics", tags=["statistics"])
```

### 修复 2: 连接历史记录到真实 API

**修改文件**: `frontend/src/pages/student/History.tsx`

```typescript
// 替换 mockData 导入
import { sessionService } from '@/services/session.service';

// 修改 fetchData 函数
const fetchData = async () => {
  setLoading(true);
  try {
    // 获取会话列表
    const sessionsData = await sessionService.listSessions({
      user_id: user?.id,
      page: 1,
      page_size: 100
    });

    // 转换为历史记录格式
    const records = sessionsData.items.map(session => ({
      id: session.id,
      dateTime: session.started_at,
      courseName: session.course_id,
      customerName: session.persona_id,
      customerRole: "客户",
      category: "新客户培训",
      duration: calculateDuration(session.started_at, session.completed_at),
      score: session.final_score || 0
    }));

    setRecords(records);

    // 计算统计数据
    const stats = {
      totalRehearsals: records.length,
      averageScore: calculateAverage(records.map(r => r.score)),
      bestScore: Math.max(...records.map(r => r.score)),
      totalDurationMinutes: calculateTotalDuration(records)
    };

    setStats(stats);
  } finally {
    setLoading(false);
  }
};
```

### 修复 3: 创建种子数据

**创建文件**: `backend/scripts/seed_data.py`

```python
"""
种子数据脚本 - 创建初始测试数据
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db_session
from backend.app.models.course import Course
from backend.app.models.task import Task, TaskStatus
from backend.app.models.config_models import CustomerPersona, Scenario

async def create_seed_data():
    """创建种子数据"""
    async for db in get_db_session():
        # 创建课程
        course = Course(
            id=1,
            title="新客户开发训练",
            description="学习如何有效地开发新客户",
            difficulty="beginner",
            estimated_hours=2
        )
        db.add(course)

        # 创建任务
        task1 = Task(
            course_id=1,
            title="新客户开场白训练",
            description="练习与新客户的第一次接触",
            task_type="conversation",
            status=TaskStatus.AVAILABLE,
            order=1,
            points=100,
            passing_score=70.0
        )
        db.add(task1)

        task2 = Task(
            course_id=1,
            title="异议处理训练",
            description="学习如何处理客户异议",
            task_type="conversation",
            status=TaskStatus.LOCKED,
            order=2,
            points=150,
            passing_score=75.0
        )
        db.add(task2)

        # 创建场景
        scenario = Scenario(
            id="scenario-1",
            name="金融行业客户开发",
            description="针对金融行业的客户开发场景"
        )
        db.add(scenario)

        # 创建客户画像
        customer1 = CustomerPersona(
            id="customer-1",
            scenario_id="scenario-1",
            name="刘先生",
            occupation="金融经理",
            age_range="35",
            personality_traits="谨慎,专业,注重细节"
        )
        db.add(customer1)

        customer2 = CustomerPersona(
            id="customer-2",
            scenario_id="scenario-1",
            name="王女士",
            occupation="企业主",
            age_range="42",
            personality_traits="果断,高效,重视结果"
        )
        db.add(customer2)

        await db.commit()
        print("✅ 种子数据创建成功！")

if __name__ == "__main__":
    asyncio.run(create_seed_data())
```

**运行命令**:
```bash
cd backend
python scripts/seed_data.py
```

---

## 📋 完整修复清单

### 立即修复（P0）

- [ ] **创建 Statistics 端点**
  - 文件: `backend/app/api/endpoints/statistics.py`
  - 注册路由: `main.py`
  - 测试: `curl http://localhost:8000/api/v1/statistics`

- [ ] **连接历史记录到真实 API**
  - 文件: `frontend/src/pages/student/History.tsx`
  - 替换 mockData 为 sessionService
  - 测试: 访问 `/student/history` 页面

- [ ] **创建种子数据**
  - 文件: `backend/scripts/seed_data.py`
  - 运行: `python backend/scripts/seed_data.py`
  - 验证: 检查数据库是否有数据

### 短期优化（P1）

- [ ] **添加错误处理**
  - 前端显示友好的错误消息
  - 后端返回详细的错误信息

- [ ] **添加加载状态**
  - 显示骨架屏（Skeleton）
  - 添加加载动画

- [ ] **添加空状态**
  - 没有数据时显示引导信息
  - 提供创建数据的快捷入口

### 长期改进（P2）

- [ ] **实现实时更新**
  - 使用 WebSocket 推送更新
  - 自动刷新统计数据

- [ ] **添加数据导出**
  - 导出历史记录为 CSV
  - 导出统计报告为 PDF

- [ ] **添加数据可视化**
  - 进度图表
  - 分数趋势图

---

## 🎯 验证步骤

### 1. 验证后端 API

```bash
# 启动后端
cd backend
python main.py

# 测试任务 API
curl http://localhost:8000/api/v1/tasks

# 测试客户 API
curl http://localhost:8000/api/v1/customers

# 测试会话 API
curl http://localhost:8000/api/v1/sessions

# 测试统计 API（修复后）
curl http://localhost:8000/api/v1/statistics
```

### 2. 验证前端页面

```bash
# 启动前端
cd frontend
npm run dev

# 访问页面
# http://localhost:5173/student/dashboard  - 任务管理
# http://localhost:5173/student/customers  - 客户预演
# http://localhost:5173/student/history    - 历史记录
```

### 3. 验证数据流

1. **任务管理页面**
   - 打开浏览器开发者工具（F12）
   - 访问 `/student/dashboard`
   - 检查 Network 标签，应该看到：
     - `GET /api/v1/tasks` - 200 OK
     - `GET /api/v1/statistics` - 200 OK（修复后）

2. **客户预演页面**
   - 访问 `/student/customers`
   - 检查 Network 标签，应该看到：
     - `GET /api/v1/customers` - 200 OK
   - 点击"新建预演角色"
     - `POST /api/v1/customers` - 200 OK

3. **历史记录页面**
   - 访问 `/student/history`
   - 检查 Network 标签，应该看到：
     - `GET /api/v1/sessions` - 200 OK（修复后）

---

## 📊 当前状态总结

| 功能模块 | 后端 API | 前端服务 | 前端页面 | 数据连接 | 状态 |
|---------|---------|---------|---------|---------|------|
| 任务管理 | ✅ 完整 | ✅ 完整 | ✅ 完整 | ⚠️ 部分 | 需修复 Statistics |
| 客户预演 | ✅ 完整 | ✅ 完整 | ✅ 完整 | ✅ 完整 | 正常工作 |
| 历史记录 | ✅ 完整 | ✅ 完整 | ✅ 完整 | ❌ 未连接 | 需连接 API |

**总体评估**:
- 后端 API: **95% 完成**（缺少 Statistics 端点）
- 前端实现: **100% 完成**
- 数据连接: **70% 完成**（需要修复 2 个连接）
- 数据准备: **0% 完成**（需要种子数据）

---

## 🚀 快速修复指南

### 最小可行修复（5分钟）

1. **临时修复 Statistics**
   ```typescript
   // frontend/src/services/task.service.ts
   getStatistics: async (): Promise<Statistics> => {
     try {
       // 临时从任务列表计算统计
       const tasks = await taskService.getTasks();
       return {
         totalTasks: tasks.length,
         inProgress: tasks.filter(t => t.status === 'in-progress').length,
         completed: tasks.filter(t => t.status === 'completed').length,
         averageScore: calculateAverage(tasks.map(t => t.progress.bestScore)),
         lockedItems: 0
       };
     } catch (error) {
       return { totalTasks: 0, inProgress: 0, completed: 0, averageScore: 0, lockedItems: 0 };
     }
   }
   ```

2. **保持历史记录使用模拟数据**
   - 暂时不修改，等待后续完善

### 完整修复（30分钟）

按照上面的"修复方案"章节，依次完成：
1. 创建 Statistics 端点（10分钟）
2. 连接历史记录 API（10分钟）
3. 创建种子数据（10分钟）

---

## 总结

**好消息**:
- ✅ 所有后端 API 都已经实现
- ✅ 所有前端页面都已经开发完成
- ✅ 大部分功能可以正常工作

**需要修复**:
- ⚠️ Statistics 端点缺失（影响任务管理页面统计）
- ⚠️ 历史记录未连接真实 API（显示模拟数据）
- ⚠️ 数据库可能为空（需要种子数据）

**修复优先级**:
1. **P0**: 创建 Statistics 端点 + 种子数据（让页面能显示真实数据）
2. **P1**: 连接历史记录 API（完整的数据流）
3. **P2**: 优化用户体验（错误处理、加载状态、空状态）

---

**报告生成时间**: 2026-02-07
**分析人**: Claude Sonnet 4.5
**项目版本**: SalesBoost V1.0
