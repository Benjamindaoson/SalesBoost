# 销冠AI系统 - 前端技术设计文档

## 1. 技术栈选择

### 核心框架

* **React 18**: 业界领先的组件化框架，生态成熟，性能优异
* **TypeScript 5**: 静态类型检查，提升代码质量和开发效率
* **Vite 5**: 极速的开发服务器和构建工具，HMR性能卓越

### UI与样式

* **Tailwind CSS 3**: 实用优先的CSS框架，快速构建响应式界面
* **shadcn/ui**: 基于Radix UI的高质量组件库，可定制性强
* **Lucide React**: 优雅的图标库，与设计风格完美匹配

### 状态管理与数据

* **React Query (TanStack Query)**: 强大的服务端状态管理，自动缓存和同步
* **React Context**: 管理全局UI状态（主题、用户信息等）
* **React Hook Form**: 表单状态管理和验证

### 路由与导航

* **React Router 6**: 声明式路由，支持嵌套路由和代码分割

## 2. 项目结构

```
frontend/
├── src/
│   ├── components/          # 通用组件
│   │   ├── ui/             # shadcn/ui基础组件
│   │   ├── layout/         # 布局组件（Sidebar, Navbar）
│   │   ├── common/         # 业务通用组件（StatCard, StatusBadge）
│   │   └── icons/          # 自定义图标
│   ├── pages/             # 页面组件
│   │   ├── Dashboard/      # 任务管理页
│   │   ├── Persona/        # 客户预演页
│   │   └── History/        # 历史记录页
│   ├── hooks/             # 自定义Hooks
│   ├── services/          # API服务
│   ├── utils/             # 工具函数
│   ├── types/             # TypeScript类型定义
│   ├── mocks/             # 模拟数据
│   ├── styles/            # 全局样式
│   └── App.tsx            # 根组件
├── public/                # 静态资源
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
└── README.md
```

## 3. 组件架构

### 3.1 布局组件

#### Sidebar组件

* 固定宽度，紫色渐变激活状态
* 包含用户头像、系统标题、菜单导航
* 支持折叠/展开功能

#### Navbar组件

* 顶部导航栏，包含logo、标题、用户操作
* 响应式设计，移动端自适应
* 集成搜索框和用户菜单

### 3.2 页面组件

#### Dashboard页面（任务管理）

```tsx
interface DashboardProps {
  stats: TaskStats;
  tasks: Task[];
  onTaskFilter: (filter: TaskFilter) => void;
}

组件结构:
- StatCards: 统计卡片网格（全部任务、进行中、已完成、平均分数）
- TaskSearch: 搜索和筛选栏
- TaskTable: 任务数据表格
  - 支持排序、分页、状态筛选
  - 操作按钮（去练习、查看详情）
```

#### Persona页面（客户预演）

```tsx
interface PersonaProps {
  personas: CustomerPersona[];
  onCreatePersona: () => void;
  onSelectPersona: (id: string) => void;
}

组件结构:
- PageHeader: 页面标题和新建按钮
- PersonaGrid: 客户卡片网格布局
  - PersonaCard: 单个客户卡片
    - 头像、基本信息、标签、时间戳
    - 操作按钮（去预演、编辑、查看、更多）
```

#### History页面（历史记录）

```tsx
interface HistoryProps {
  stats: PracticeStats;
  records: PracticeRecord[];
  onExport: () => void;
  onFilter: (filter: HistoryFilter) => void;
}

组件结构:
- StatCards: 练习统计数据（总次数、平均分、最高分、总时长）
- HistoryFilters: 时间筛选、分数筛选、导出按钮
- HistoryTable: 历史记录表格
  - 得分徽章（蓝/橙/绿彩色标签）
  - 操作列（查看详情、重新练习）
```

## 4. 数据模型

### TypeScript接口定义

```typescript
// 任务相关
type TaskStatus = 'not_started' | 'in_progress' | 'completed';

interface Task {
  id: string;
  courseName: string;
  courseTags: string[];
  taskInfo: string;
  taskLink?: string;
  status: TaskStatus;
  dateRange: {
    start: string;
    end: string;
  };
  progress: {
    completed: number;
    total: number;
    score?: number;
  };
}

interface TaskStats {
  total: number;
  inProgress: number;
  completed: number;
  averageScore: number;
}

// 客户预演相关
interface CustomerPersona {
  id: string;
  name: string;
  description: string;
  tags: string[];
  level?: string;
  lastPracticed: string;
  avatar?: string;
}

// 历史记录相关
interface PracticeRecord {
  id: string;
  dateTime: string;
  courseInfo: string;
  customerRole: string;
  category: string;
  duration: string;
  score: number;
}

interface PracticeStats {
  totalSessions: number;
  averageScore: number;
  highestScore: number;
  totalDuration: number; // 分钟
}

// 筛选条件
interface TaskFilter {
  search?: string;
  status?: TaskStatus;
}

interface HistoryFilter {
  timeRange?: 'all' | 'week' | 'month';
  scoreRange?: 'all' | 'excellent' | 'good' | 'needs_improvement';
}
```

## 5. 状态管理策略

### React Query配置

```typescript
// 查询客户端配置
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5分钟
      cacheTime: 10 * 60 * 1000, // 10分钟
      retry: 3,
      refetchOnWindowFocus: false,
    },
  },
});

// 自定义查询Hooks
export const useTasks = (filter?: TaskFilter) => {
  return useQuery({
    queryKey: ['tasks', filter],
    queryFn: () => taskService.getTasks(filter),
  });
};

export const usePersonas = () => {
  return useQuery({
    queryKey: ['personas'],
    queryFn: personaService.getPersonas,
  });
};

export const useHistory = (filter?: HistoryFilter) => {
  return useQuery({
    queryKey: ['history', filter],
    queryFn: () => historyService.getHistory(filter),
  });
};
```

### Context状态管理

```typescript
// UI状态Context
interface UIContextType {
  sidebarCollapsed: boolean;
  theme: 'light' | 'dark';
  toggleSidebar: () => void;
  toggleTheme: () => void;
}

// 用户状态Context
interface UserContextType {
  user: User | null;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
}
```

## 6. 路由定义

```typescript
// React Router配置
const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: <DashboardPage />,
        loader: dashboardLoader,
      },
      {
        path: 'persona',
        element: <PersonaPage />,
        loader: personaLoader,
      },
      {
        path: 'history',
        element: <HistoryPage />,
        loader: historyLoader,
      },
    ],
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
]);

// 路由加载器（数据预加载）
export async function dashboardLoader() {
  const [stats, tasks] = await Promise.all([
    taskService.getStats(),
    taskService.getTasks(),
  ]);
  return { stats, tasks };
}
```

## 7. 模拟数据策略

### Mock Service Worker (MSW)配置

```typescript
// src/mocks/handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  // 任务管理
  http.get('/api/tasks', () => {
    return HttpResponse.json({
      stats: mockTaskStats,
      tasks: mockTasks,
    });
  }),
  
  // 客户预演
  http.get('/api/personas', () => {
    return HttpResponse.json(mockPersonas);
  }),
  
  // 历史记录
  http.get('/api/history', () => {
    return HttpResponse.json({
      stats: mockHistoryStats,
      records: mockHistoryRecords,
    });
  }),
];

// 开发环境启用MSW
if (import.meta.env.DEV) {
  const { worker } = await import('./browser');
  worker.start();
}
```

### 模拟数据示例

```typescript
// src/mocks/data.ts
export const mockTaskStats: TaskStats = {
  total: 5,
  inProgress: 3,
  completed: 1,
  averageScore: 84,
};

export const mockTasks: Task[] = [
  {
    id: '1',
    courseName: '新客户开卡+场景训练',
    courseTags: ['2/5节', '客户开卡', '渠道训练'],
    taskInfo: '第一章 — AI客服训练计划',
    taskLink: '模拟客户',
    status: 'in_progress',
    dateRange: {
      start: '2024-12-01',
      end: '2024-12-31',
    },
    progress: {
      completed: 3,
      total: 5,
      score: 85,
    },
  },
  // ... 更多模拟数据
];
```

## 8. 开发环境配置

### Vite配置优化

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@types': path.resolve(__dirname, './src/types'),
    },
  },
  server: {
    port: 3000,
    open: true,
  },
});
```

### TypeScript配置

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

## UI Reference (OCR from Images)

**Visual style notes:**
- Primary color: purple gradient for active states and primary buttons
- Status badges: blue for “进行中”, gray for “未开始”, green for “已结束”
- Score badges elsewhere use blue/orange/green to indicate ranges
- Fonts: sans-serif UI, medium weight for headings, regular for body; Chinese and English mixed

**Dashboard Page Data:**
- Stats:
  - Total Tasks: 5
  - In Progress: 3
  - Completed: 1
  - Avg Score: 84
- Table Columns: 课程名称, 任务信息, 状态, 时间范围, 进度, 操作
- Sample Row: "新客户开卡+场景训练", "第一章 — AI客服训练计划", "进行中", "2024-12-01 至 2024-12-31", "3/5", "85分"

**Persona Page Data:**
- Cards:
  - "刘先生": 27岁, 互联网行业程序员, 商旅需求高. Level: 9级别.
  - "王女士": 33岁, 金融行业, 家庭型, 关注子女教育.
  - "李总": 42岁, 企业高管, 追求高端服务和品质.
  - "张小姐": Note: "Do not sell or share my personal info"

**History Page Data:**
- Stats:
  - Total Sessions: 8
  - Avg Score: 82
  - Highest Score: 92
  - Total Duration: 120 mins
- Table Columns: 日期时间, 课程信息, 客户角色, 类别, 时长, 得分, 操作
- Sample Row: "2024-12-21 14:30", "新客户开卡+场景训练", "刘先生", "新客户开卡", "15分32秒", "85" (Blue badge)
