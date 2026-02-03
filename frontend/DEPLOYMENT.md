# AI Sales Training Agent - 部署文档

本系统已完成生产环境构建并启动服务。以下是访问和维护指南。

## 1. 访问信息

*   **访问地址**: [http://localhost:5000](http://localhost:5000)
*   **系统状态**: 🟢 运行中

### 登录凭证 (演示模式)
本系统已配置为 Mock 演示模式，无需真实后端即可体验完整流程。

*   **方式一 (推荐)**: 在登录页直接点击 **"Demo Login (No Email Required)"** 按钮。
*   **方式二**: 输入任意邮箱（如 `demo@salesboost.com`），系统将自动模拟登录流程。

## 2. 部署详情

### 技术栈
*   **前端框架**: React 18 + TypeScript + Vite
*   **构建工具**: Vite (生产模式构建)
*   **Web 服务器**: `serve` (高性能静态资源服务器)
*   **运行端口**: 5000

### 文件结构
*   **构建产物**: `/dist` (包含优化后的 HTML/CSS/JS 静态文件)
*   **源代码**: `/src`
*   **配置文件**: `.env` (环境变量), `vite.config.ts`, `tsconfig.json`

## 3. 环境配置

当前运行的 `.env` 配置如下（已自动生成）：

```env
VITE_SUPABASE_URL=https://example.supabase.co
VITE_SUPABASE_ANON_KEY=dummy-key-for-development
VITE_API_URL=http://localhost:8000/api/v1
VITE_ENABLE_AI_FEATURES=false
VITE_ENABLE_ANALYTICS=false
```

> **注意**: 在演示模式下，`VITE_SUPABASE_URL` 和 Key 使用了占位符。若需连接真实后端，请修改 `.env` 文件并重新构建。

## 4. 验证与验收

1.  **访问系统**: 打开浏览器访问 [http://localhost:5000](http://localhost:5000)。
2.  **登录验证**: 点击 "Demo Login"，应直接跳转至学员仪表板。
3.  **功能检查**:
    *   **仪表板**: 检查统计卡片数据是否显示。
    *   **任务列表**: 检查是否可以筛选（"进行中"、"已完成"）和搜索。
    *   **导航**: 点击侧边栏菜单，确认路由切换正常（部分页面为占位符）。

## 5. 维护说明

如果服务意外停止，请在项目根目录 (`d:\SalesBoost\frontend`) 执行以下命令重启：

```bash
# 启动生产服务
npx serve -s dist -l 5000
```

若需更新代码并重新部署：

```bash
# 1. 安装依赖 (如有新增)
npm install

# 2. 重新构建
npm run build

# 3. 重启服务
npx serve -s dist -l 5000
```
