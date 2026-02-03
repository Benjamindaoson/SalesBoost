# 🚀 SalesBoost Frontend - 快速启动指南

## ⚡ 5分钟快速开始

### 1. 安装依赖
```bash
cd frontend
npm install
```

### 2. 配置环境变量
```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 Supabase 凭据：
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key_here
```

### 3. 启动开发服务器
```bash
npm run dev
```

访问: http://localhost:5173

---

## 🔑 配置管理员账户

### 在 Supabase 中设置管理员角色

**方法 1: SQL (推荐)**
```sql
UPDATE auth.users
SET raw_user_meta_data = raw_user_meta_data || '{"role": "admin"}'::jsonb
WHERE email = 'your-email@example.com';
```

**方法 2: Dashboard**
1. 打开 Supabase Dashboard
2. Authentication → Users
3. 选择用户 → Edit User Metadata
4. 添加: `{"role": "admin"}`

---

## 📋 可用命令

```bash
# 开发
npm run dev              # 启动开发服务器
npm run build            # 构建生产版本
npm run preview          # 预览生产构建

# 测试
npm run test             # 运行单元测试
npm run test:ui          # 测试 UI 界面
npm run test:coverage    # 生成覆盖率报告
npm run test:e2e         # 运行 E2E 测试
npm run test:e2e:ui      # E2E UI 模式

# 代码质量
npm run check            # TypeScript 类型检查
npm run lint             # ESLint 检查
npm run lint:biome       # Biome 检查
npm run format           # 代码格式化
```

---

## 🎯 核心功能

### ✅ 已实现
- 🔒 管理员角色授权
- 📝 表单验证 (React Hook Form + Zod)
- ⚡ 代码分割 (React.lazy)
- 📊 错误监控 (Sentry)
- 📈 性能监控 (Web Vitals)
- 🧪 测试框架 (Vitest + Playwright)
- 🔄 智能轮询 (指数退避)
- 💾 API 缓存 (React Query)

### 🎨 页面状态
- ✅ LoginPage - 完整表单验证
- ✅ CourseList - 真实 API 集成
- ✅ Admin/Users - 真实 API 集成
- ✅ Admin/Courses - 真实 API 集成
- ✅ Admin/Dashboard - 真实 API 集成
- ✅ Admin/KnowledgeBase - 真实 API 集成
- ⚠️ Evaluation - 待连接 API
- ⚠️ Student/Dashboard - 待连接 API

---

## 🔧 故障排除

### 问题: 环境变量错误
```
❌ Invalid environment configuration:
  - VITE_SUPABASE_URL: VITE_SUPABASE_URL must be a valid URL
```

**解决方案**:
1. 检查 `.env` 文件是否存在
2. 确保 `VITE_SUPABASE_URL` 是有效的 URL
3. 重启开发服务器

### 问题: 管理员路由被拒绝
```
Access denied: User does not have admin role
```

**解决方案**:
1. 在 Supabase 中设置用户角色为 `admin`
2. 登出并重新登录
3. 检查浏览器控制台确认角色

### 问题: API 调用失败
```
Failed to load courses
```

**解决方案**:
1. 确保后端服务正在运行
2. 检查 `VITE_API_URL` 配置
3. 查看网络请求详情
4. 检查 Supabase 认证状态

---

## 📊 生产部署

### 构建
```bash
npm run build
```

### 环境变量 (生产)
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_production_key
VITE_API_URL=https://api.your-domain.com/api/v1
VITE_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
VITE_ENABLE_ERROR_REPORTING=true
VITE_ENABLE_ANALYTICS=true
```

### Docker 部署
```bash
docker build -t salesboost-frontend .
docker run -p 80:80 salesboost-frontend
```

---

## 📚 更多文档

- [完整实施报告](./FRONTEND_FINAL_REPORT.md)
- [实施计划](C:\Users\Benjamindaoson\.claude\plans\composed-giggling-globe.md)
- [环境配置示例](./.env.example)

---

## 🆘 获取帮助

- 查看浏览器控制台错误
- 检查网络请求
- 查看 Sentry 错误报告
- 运行 `npm run check` 检查类型错误

---

**快速启动完成！** 🎉

现在你可以：
1. 访问 http://localhost:5173
2. 使用魔法链接登录
3. 探索学生和管理员功能
4. 运行测试验证功能
