# 🎯 SalesBoost - 前后端完全贯通使用指南

## 🚀 快速启动

### 方式1: 使用启动脚本 (推荐)
```bash
# 在SalesBoost根目录运行
start.bat
```

### 方式2: 手动启动

**启动后端**:
```bash
cd backend
python main.py
```

**启动前端** (新终端):
```bash
cd frontend
npm run dev
```

## 📱 访问应用

- **学生端**: http://localhost:5174/student/dashboard
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## ✅ 已实现功能

### 1. 任务管理 (/student/dashboard)
- ✅ 查看所有任务 (5个任务)
- ✅ 查看统计数据 (总任务、进行中、已完成、平均分)
- ✅ 筛选和搜索任务
- ✅ 点击"去练习"跳转到训练页面

### 2. 客户预演 (/student/customers)
- ✅ 查看客户画像列表 (3个客户)
- ✅ 查看客户详情
- ✅ 点击"去预演"开始训练

### 3. 历史记录 (/student/history)
- ✅ 查看训练历史
- ✅ 查看统计数据
- ✅ 筛选和搜索记录
- ⚠️ 当前为空(需要完成训练后才有数据)

### 4. 课程列表 (/student/courses)
- ✅ 查看所有课程 (2个课程)
- ✅ 查看课程详情

## 🔌 API端点

### 已实现的端点

| 端点 | 方法 | 说明 | 示例 |
|------|------|------|------|
| `/api/v1/tasks` | GET | 获取所有任务 | `curl http://localhost:8000/api/v1/tasks` |
| `/api/v1/statistics` | GET | 获取统计数据 | `curl http://localhost:8000/api/v1/statistics` |
| `/api/v1/courses` | GET | 获取所有课程 | `curl http://localhost:8000/api/v1/courses` |
| `/api/v1/customers` | GET | 获取客户画像 | `curl http://localhost:8000/api/v1/customers` |

### API响应示例

**Tasks API**:
```json
[
  {
    "id": 1,
    "title": "新客户开场白训练",
    "description": "练习与新客户的第一次接触",
    "task_type": "conversation",
    "status": "available",
    "order": 1,
    "points": 100,
    "passing_score": 70.0,
    "time_limit_minutes": 30,
    "course_id": 1
  }
]
```

**Statistics API**:
```json
{
  "totalTasks": 5,
  "inProgress": 0,
  "completed": 0,
  "averageScore": 0.0,
  "lockedItems": 2
}
```

## 🎮 功能测试

### 测试任务管理
1. 访问 http://localhost:5174/student/dashboard
2. 应该看到:
   - 统计卡片显示: 全部任务 5, 进行中 0, 已完成 0
   - 任务列表显示5个任务
3. 点击"去练习"按钮
4. 应该跳转到训练页面

### 测试客户预演
1. 访问 http://localhost:5174/student/customers
2. 应该看到3个客户卡片
3. 点击"去预演"按钮
4. 应该跳转到训练页面

### 测试API连通性
```bash
# 测试tasks端点
curl http://localhost:8000/api/v1/tasks

# 测试statistics端点
curl http://localhost:8000/api/v1/statistics

# 测试courses端点
curl http://localhost:8000/api/v1/courses

# 测试customers端点
curl http://localhost:8000/api/v1/customers
```

## ⚠️ 已知限制

### 1. 训练功能未完全实现
- **问题**: WebSocket端点未注册
- **影响**: 无法进行实时对话训练
- **状态**: 待修复

### 2. 客户数据为模拟数据
- **问题**: 使用硬编码的3个客户
- **影响**: 无法创建/编辑/删除客户
- **状态**: 待连接数据库

### 3. 历史记录为空
- **问题**: 数据库中没有训练会话
- **影响**: 历史记录页面显示空数据
- **状态**: 完成训练功能后自动有数据

## 🔧 故障排除

### 后端启动失败
```bash
# 检查端口是否被占用
netstat -ano | findstr :8000

# 如果被占用,杀掉进程
taskkill /F /PID <进程ID>
```

### 前端启动失败
```bash
# 检查端口是否被占用
netstat -ano | findstr :5173

# 如果被占用,前端会自动使用5174端口
```

### API请求失败
1. 检查后端是否运行: http://localhost:8000/health
2. 检查浏览器控制台是否有CORS错误
3. 检查网络代理设置

### 页面显示空数据
1. 打开浏览器开发者工具 (F12)
2. 切换到Network标签
3. 刷新页面
4. 检查API请求是否返回200
5. 检查响应数据是否正确

## 📚 相关文档

- [前后端集成测试报告](docs/FRONTEND_BACKEND_INTEGRATION_TEST.md)
- [快速修复指南](docs/QUICK_FIX_GUIDE.md)
- [API文档](http://localhost:8000/docs)

## 🎉 成功标志

如果看到以下内容,说明系统运行正常:

1. ✅ 后端日志显示: `Uvicorn running on http://0.0.0.0:8000`
2. ✅ 前端日志显示: `Local: http://localhost:5174/`
3. ✅ Dashboard页面显示5个任务
4. ✅ 统计卡片显示正确数据
5. ✅ 所有按钮可以点击

## 💡 下一步

1. **完成训练功能** - 修复WebSocket端点
2. **连接客户数据库** - 实现客户CRUD
3. **实现评估系统** - 自动评分和反馈

---

**最后更新**: 2026-02-07
**状态**: ✅ 核心功能可用
**版本**: v1.0
