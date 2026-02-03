# 完整实现脚本 - 剩余60%代码

## 已完成 ✅

1. ✅ 后端 REST APIs (courses.py, users.py, tasks.py)
2. ✅ 路由注册 (main.py)
3. ✅ 前端服务层 (course.service.ts, user.service.ts, task.service.ts)
4. ✅ Dashboard.tsx 更新

## 剩余实现代码

### 1. History.tsx 更新

```typescript
// frontend/src/pages/student/History.tsx
import { useEffect, useState } from 'react';
import { sessionService } from '@/services/session.service';
import { useAuthStore } from '@/store/auth.store';
import { useToast } from '@/hooks/use-toast';

export default function History() {
  const [historyRecords, setHistoryRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuthStore();
  const { toast } = useToast();

  useEffect(() => {
    const fetchHistory = async () => {
      if (!user) return;

      setLoading(true);
      try {
        const response = await sessionService.listSessions({
          user_id: user.id,
          status: 'completed',
          page: 1,
          page_size: 50
        });

        // Transform sessions to history records
        const records = response.items.map(session => ({
          id: session.session_id,
          dateTime: session.ended_at || session.started_at,
          courseName: `Course ${session.course_id}`,
          customerName: 'Customer',
          category: session.task_type || 'conversation',
          duration: calculateDuration(session.started_at, session.ended_at),
          score: session.final_score || 0,
          scoreLevel: getScoreLevel(session.final_score || 0)
        }));

        setHistoryRecords(records);
      } catch (error) {
        console.error("Failed to fetch history", error);
        toast({
          variant: "destructive",
          title: "加载失败",
          description: "无法加载历史记录"
        });
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [user, toast]);

  // ... rest of component
}

function calculateDuration(start: string, end: string): string {
  if (!start || !end) return '0分钟';
  const diff = new Date(end).getTime() - new Date(start).getTime();
  const minutes = Math.floor(diff / 60000);
  return `${minutes}分钟`;
}

function getScoreLevel(score: number): string {
  if (score >= 90) return 'excellent';
  if (score >= 80) return 'good';
  if (score >= 70) return 'average';
  return 'poor';
}
```

### 2. Admin/Users.tsx 更新

```typescript
// frontend/src/pages/Admin/Users.tsx
import { useEffect, useState } from 'react';
import { userService, User } from '@/services/user.service';
import { useToast } from '@/hooks/use-toast';

export default function AdminUsers() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const { toast } = useToast();

  useEffect(() => {
    fetchUsers();
  }, [page, search]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await userService.listUsers({
        search,
        page,
        page_size: 20
      });
      setUsers(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error("Failed to fetch users", error);
      toast({
        variant: "destructive",
        title: "加载失败",
        description: "无法加载用户数据"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (userId: number) => {
    if (!confirm('确定要删除此用户吗？')) return;

    try {
      await userService.deleteUser(userId);
      toast({
        title: "删除成功",
        description: "用户已被删除"
      });
      fetchUsers();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "删除失败",
        description: "无法删除用户"
      });
    }
  };

  // ... rest of component with real CRUD operations
}
```

### 3. Admin/Courses.tsx 更新

```typescript
// frontend/src/pages/Admin/Courses.tsx
import { useEffect, useState } from 'react';
import { courseService, Course } from '@/services/course.service';
import { llmService } from '@/services/llm.service';
import { useToast } from '@/hooks/use-toast';

export default function AdminCourses() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const { toast } = useToast();

  useEffect(() => {
    fetchCourses();
  }, [page, searchTerm]);

  const fetchCourses = async () => {
    setLoading(true);
    try {
      const response = await courseService.listCourses({
        search: searchTerm,
        page,
        page_size: 20
      });
      setCourses(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error("Failed to fetch courses", error);
      toast({
        variant: "destructive",
        title: "加载失败",
        description: "无法加载课程数据"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateCourse = async (topic: string) => {
    try {
      // Use LLM to generate course outline
      const prompt = llmService.createCourseOutlinePrompt();
      const messages = [
        { role: 'system', content: prompt },
        { role: 'user', content: `Generate a course about: ${topic}` }
      ];

      const response = await llmService.chatCompletion(messages, true);
      const courseData = JSON.parse(response);

      // Save to backend
      const newCourse = await courseService.createCourse({
        title: courseData.title,
        description: courseData.description,
        tags: courseData.tags,
        difficulty: courseData.difficulty === 'beginner' ? 1 : courseData.difficulty === 'intermediate' ? 3 : 5,
        status: 'draft'
      });

      toast({
        title: "课程生成成功",
        description: `已创建草稿：${newCourse.title}`
      });

      fetchCourses();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "生成失败",
        description: "无法生成课程"
      });
    }
  };

  // ... rest of component
}
```

### 4. Admin/Tasks.tsx 更新

```typescript
// frontend/src/pages/Admin/Tasks.tsx
import { useEffect, useState } from 'react';
import { taskService, Task } from '@/services/task.service';
import { useToast } from '@/hooks/use-toast';

export default function AdminTasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const { toast } = useToast();

  useEffect(() => {
    fetchTasks();
  }, [page]);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const response = await taskService.listTasks({
        page,
        page_size: 20
      });
      setTasks(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error("Failed to fetch tasks", error);
      toast({
        variant: "destructive",
        title: "加载失败",
        description: "无法加载任务数据"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (taskId: number) => {
    if (!confirm('确定要删除此任务吗？')) return;

    try {
      await taskService.deleteTask(taskId);
      toast({
        title: "删除成功",
        description: "任务已被删除"
      });
      fetchTasks();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "删除失败",
        description: "无法删除任务"
      });
    }
  };

  // ... rest of component
}
```

### 5. useWebSocket Hook

```typescript
// frontend/src/hooks/useWebSocket.ts
import { useState, useEffect, useRef, useCallback } from 'react';
import { useToast } from '@/hooks/use-toast';

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  autoConnect?: boolean;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

export function useWebSocket(options: UseWebSocketOptions) {
  const {
    url,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    autoConnect = true,
    reconnectAttempts = 5,
    reconnectInterval = 3000
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const { toast } = useToast();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setIsConnecting(true);

    try {
      // Add auth token to URL
      const token = localStorage.getItem('access_token');
      const wsUrl = new URL(url);
      if (token) {
        wsUrl.searchParams.set('token', token);
      }

      wsRef.current = new WebSocket(wsUrl.toString());

      wsRef.current.onopen = () => {
        setIsConnected(true);
        setIsConnecting(false);
        reconnectCountRef.current = 0;
        onConnect?.();
      };

      wsRef.current.onclose = () => {
        setIsConnected(false);
        setIsConnecting(false);
        onDisconnect?.();

        // Attempt reconnection
        if (reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current++;
          reconnectTimerRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        } else {
          toast({
            variant: "destructive",
            title: "连接失败",
            description: "无法连接到服务器，请刷新页面重试"
          });
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        onError?.(error);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setIsConnecting(false);
    }
  }, [url, onMessage, onConnect, onDisconnect, onError, reconnectAttempts, reconnectInterval, toast]);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    isConnected,
    isConnecting,
    connect,
    disconnect,
    send
  };
}
```

### 6. Training.tsx WebSocket 重构

```typescript
// frontend/src/pages/student/Training.tsx - Key changes
import { useWebSocket } from '@/hooks/useWebSocket';

export default function Training() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [tips, setTips] = useState<CoachTip[]>([]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  // Replace LLM service with WebSocket
  const { isConnected, send } = useWebSocket({
    url: 'ws://localhost:8000/ws/chat',
    onMessage: (message) => {
      if (message.type === 'turn_result') {
        // Handle NPC response
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'assistant',
          content: message.npc_response,
          timestamp: Date.now()
        }]);
        setIsTyping(false);
      } else if (message.type === 'round_event') {
        // Handle coach tips
        if (message.coach_tip) {
          setTips(prev => [...prev, {
            id: Date.now().toString(),
            content: message.coach_tip.content,
            type: message.coach_tip.type
          }]);
        }
      } else if (message.type === 'error') {
        console.error('WebSocket error:', message);
        setIsTyping(false);
      }
    },
    onConnect: () => {
      console.log('WebSocket connected');
    },
    onDisconnect: () => {
      console.log('WebSocket disconnected');
    }
  });

  const handleSend = () => {
    if (!inputText.trim() || !isConnected) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputText,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsTyping(true);

    // Send via WebSocket instead of direct LLM call
    send({
      type: 'message',
      content: userMessage.content
    });
  };

  // Remove all llmService.chatCompletion() calls
  // Remove createSystemPrompt() and createCoachPrompt()

  // ... rest of component
}
```

## 实现检查清单

- [x] 后端 REST APIs
- [x] 路由注册
- [x] course.service.ts
- [x] user.service.ts
- [x] task.service.ts
- [x] Dashboard.tsx
- [ ] History.tsx (代码已提供)
- [ ] Admin/Users.tsx (代码已提供)
- [ ] Admin/Courses.tsx (代码已提供)
- [ ] Admin/Tasks.tsx (代码已提供)
- [ ] useWebSocket.ts (代码已提供)
- [ ] Training.tsx (代码已提供)

## 测试步骤

1. **启动后端**:
   ```bash
   cd d:\SalesBoost
   python main.py
   ```

2. **测试 API**:
   访问 http://localhost:8000/docs
   测试 /api/v1/courses, /api/v1/users, /api/v1/tasks

3. **启动前端**:
   ```bash
   cd d:\SalesBoost\frontend
   npm run dev
   ```

4. **测试页面**:
   - Dashboard: http://localhost:5173/student/dashboard
   - History: http://localhost:5173/student/history
   - Admin Users: http://localhost:5173/admin/users
   - Admin Courses: http://localhost:5173/admin/courses
   - Training: http://localhost:5173/student/training

## 成功标准

✅ 所有 API 返回 200 OK
✅ 前端页面加载无 mock 数据
✅ CRUD 操作正常工作
✅ WebSocket 连接成功
✅ Training 页面消息收发正常
✅ 无控制台错误
✅ 用户体验流畅
