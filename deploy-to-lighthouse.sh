#!/bin/bash

# SalesBoost 完整部署脚本
# 用于在 Lighthouse 上部署完整的前后端项目

set -e

echo "=== SalesBoost 完整部署开始 ==="
echo "部署时间: $(date)"

# 1. 清理旧容器
echo -e "\n[1/6] 清理旧容器..."
docker stop salesboost-backend salesboost-frontend 2>/dev/null || true
docker rm salesboost-backend salesboost-frontend 2>/dev/null || true
echo "✓ 旧容器已清理"

# 2. 创建目录结构
echo -e "\n[2/6] 创建目录结构..."
mkdir -p /root/salesboost/{backend,frontend,docker,logs}
mkdir -p /root/salesboost/webapp/{student,admin}
echo "✓ 目录结构已创建"

# 3. 部署后端
echo -e "\n[3/6] 部署后端服务..."
cd /root/salesboost/backend

# 创建后端主程序
cat > main.py << 'BACKEND_PY'
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
from datetime import datetime

app = FastAPI(
    title="SalesBoost API",
    version="1.0.0",
    description="AI Sales Champion Replication Platform"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康检查
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "SalesBoost Backend",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    return {
        "message": "SalesBoost API is running",
        "status": "ok",
        "docs": "/docs"
    }

# 数据模型
class Customer(BaseModel):
    id: Optional[int] = None
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    status: str = "active"

class Task(BaseModel):
    id: Optional[int] = None
    title: str
    course: str
    status: str
    progress: int
    score: Optional[int] = None

class Course(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    student_count: int
    status: str

# 模拟数据库
customers_db = {
    1: {"id": 1, "name": "张三", "email": "zhangsan@example.com", "phone": "13800138000", "company": "ABC公司", "status": "active"},
    2: {"id": 2, "name": "李四", "email": "lisi@example.com", "phone": "13900139000", "company": "XYZ公司", "status": "active"},
    3: {"id": 3, "name": "王五", "email": "wangwu@example.com", "phone": "13700137000", "company": "DEF公司", "status": "active"},
}

tasks_db = {
    1: {"id": 1, "title": "产品介绍话术训练", "course": "基础话术", "status": "in_progress", "progress": 60, "score": None},
    2: {"id": 2, "title": "异议处理演练", "course": "异议处理", "status": "completed", "progress": 100, "score": 85},
    3: {"id": 3, "title": "成交技巧训练", "course": "成交技巧", "status": "not_started", "progress": 0, "score": None},
}

courses_db = {
    1: {"id": 1, "name": "产品介绍话术训练", "description": "学习如何有效介绍产品", "student_count": 23, "status": "published"},
    2: {"id": 2, "name": "异议处理演练", "description": "掌握处理客户异议的技巧", "student_count": 18, "status": "published"},
}

# API 端点
@app.get("/api/v1/customers", response_model=List[Customer])
async def get_customers():
    """获取所有客户"""
    return list(customers_db.values())

@app.get("/api/v1/customers/{customer_id}", response_model=Customer)
async def get_customer(customer_id: int):
    """获取单个客户"""
    if customer_id not in customers_db:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customers_db[customer_id]

@app.post("/api/v1/customers", response_model=Customer)
async def create_customer(customer: Customer):
    """创建客户"""
    new_id = max(customers_db.keys()) + 1 if customers_db else 1
    customer.id = new_id
    customers_db[new_id] = customer.dict()
    return customer

@app.get("/api/v1/tasks", response_model=List[Task])
async def get_tasks():
    """获取所有任务"""
    return list(tasks_db.values())

@app.get("/api/v1/tasks/{task_id}", response_model=Task)
async def get_task(task_id: int):
    """获取单个任务"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]

@app.get("/api/v1/courses", response_model=List[Course])
async def get_courses():
    """获取所有课程"""
    return list(courses_db.values())

@app.get("/api/v1/stats")
async def get_stats():
    """获取统计信息"""
    return {
        "total_tasks": len(tasks_db),
        "in_progress": sum(1 for t in tasks_db.values() if t["status"] == "in_progress"),
        "completed": sum(1 for t in tasks_db.values() if t["status"] == "completed"),
        "average_score": 85
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)
BACKEND_PY

cat > requirements.txt << 'REQUIREMENTS'
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
REQUIREMENTS

echo "✓ 后端代码已准备"

# 4. 部署前端
echo -e "\n[4/6] 部署前端页面..."
cd /root/salesboost/webapp

# 主页
python3 << 'PYTHON_EOF'
import os

# 主页 HTML
index_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SalesBoost - AI 销售作战平台</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <nav class="bg-white shadow-md">
        <div class="max-w-7xl mx-auto px-4 py-4">
            <div class="flex justify-between items-center">
                <span class="text-xl font-bold text-blue-600">🎯 SalesBoost</span>
                <div class="space-x-4">
                    <a href="/" class="text-gray-700 hover:text-blue-600">首页</a>
                    <a href="/student/tasks.html" class="text-gray-700 hover:text-blue-600">学员端</a>
                    <a href="/admin/" class="text-gray-700 hover:text-blue-600">管理端</a>
                </div>
            </div>
        </div>
    </nav>
    <div class="max-w-7xl mx-auto px-4 py-8">
        <h1 class="text-4xl font-bold text-gray-900 mb-4">欢迎使用 SalesBoost</h1>
        <p class="text-xl text-gray-600 mb-8">AI 销售作战平台 · 训练 · 管道 · 实战</p>
        <div class="grid grid-cols-4 gap-6 mb-8">
            <div class="bg-white rounded-lg shadow p-6">
                <div class="text-3xl font-bold text-blue-600">12</div>
                <div class="text-gray-600">总任务数</div>
            </div>
            <div class="bg-white rounded-lg shadow p-6">
                <div class="text-3xl font-bold text-green-600">5</div>
                <div class="text-gray-600">进行中</div>
            </div>
            <div class="bg-white rounded-lg shadow p-6">
                <div class="text-3xl font-bold text-purple-600">7</div>
                <div class="text-gray-600">已完成</div>
            </div>
            <div class="bg-white rounded-lg shadow p-6">
                <div class="text-3xl font-bold text-orange-600">85%</div>
                <div class="text-gray-600">平均评分</div>
            </div>
        </div>
        <div class="grid grid-cols-2 gap-6">
            <a href="/student/tasks.html" class="bg-white rounded-lg shadow p-6 hover:shadow-lg transition">
                <h2 class="text-xl font-bold mb-2">📚 学员任务管理</h2>
                <p class="text-gray-600">查看和管理您的培训任务</p>
            </a>
            <a href="/admin/" class="bg-white rounded-lg shadow p-6 hover:shadow-lg transition">
                <h2 class="text-xl font-bold mb-2">⚙️ 管理控制台</h2>
                <p class="text-gray-600">管理系统课程和数据</p>
            </a>
        </div>
    </div>
</body>
</html>'''

with open('/root/salesboost/webapp/index.html', 'w', encoding='utf-8') as f:
    f.write(index_html)

print('index.html created')

# 学员任务页面
student_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>学员任务管理 - SalesBoost</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <div class="flex min-h-screen">
        <div class="w-64 bg-white shadow-md">
            <div class="p-4"><h1 class="text-lg font-bold text-blue-600">🎯 学员端</h1></div>
            <nav class="mt-4">
                <a href="/student/tasks.html" class="block px-4 py-2 bg-blue-50 text-blue-600">任务管理</a>
                <a href="/student/persona.html" class="block px-4 py-2 text-gray-700 hover:bg-gray-50">客户预览</a>
                <a href="/student/history.html" class="block px-4 py-2 text-gray-700 hover:bg-gray-50">培训历史</a>
            </nav>
        </div>
        <div class="flex-1 p-8">
            <h1 class="text-2xl font-bold mb-6">任务管理</h1>
            <div class="grid grid-cols-4 gap-4 mb-6">
                <div class="bg-white rounded-lg shadow p-4"><div class="text-2xl font-bold text-blue-600">12</div><div class="text-sm text-gray-600">总任务</div></div>
                <div class="bg-white rounded-lg shadow p-4"><div class="text-2xl font-bold text-yellow-600">5</div><div class="text-sm text-gray-600">进行中</div></div>
                <div class="bg-white rounded-lg shadow p-4"><div class="text-2xl font-bold text-green-600">7</div><div class="text-sm text-gray-600">已完成</div></div>
                <div class="bg-white rounded-lg shadow p-4"><div class="text-2xl font-bold text-purple-600">85%</div><div class="text-sm text-gray-600">平均评分</div></div>
            </div>
            <div class="bg-white rounded-lg shadow">
                <table class="w-full">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">任务名称</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">课程</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">进度</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200">
                        <tr><td class="px-6 py-4">产品介绍话术训练</td><td class="px-6 py-4">基础话术</td><td class="px-6 py-4"><span class="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-sm">进行中</span></td><td class="px-6 py-4">60%</td><td class="px-6 py-4"><button class="text-blue-600 hover:underline">继续</button></td></tr>
                        <tr><td class="px-6 py-4">异议处理演练</td><td class="px-6 py-4">异议处理</td><td class="px-6 py-4"><span class="px-2 py-1 bg-green-100 text-green-800 rounded text-sm">已完成</span></td><td class="px-6 py-4">100%</td><td class="px-6 py-4"><button class="text-blue-600 hover:underline">查看</button></td></tr>
                        <tr><td class="px-6 py-4">成交技巧训练</td><td class="px-6 py-4">成交技巧</td><td class="px-6 py-4"><span class="px-2 py-1 bg-gray-100 text-gray-800 rounded text-sm">未开始</span></td><td class="px-6 py-4">0%</td><td class="px-6 py-4"><button class="text-blue-600 hover:underline">开始</button></td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>'''

with open('/root/salesboost/webapp/student/tasks.html', 'w', encoding='utf-8') as f:
    f.write(student_html)

print('student/tasks.html created')

# 管理页面
admin_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>管理控制台 - SalesBoost</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <div class="flex min-h-screen">
        <div class="w-64 bg-white shadow-md">
            <div class="p-4"><h1 class="text-lg font-bold text-green-600">⚙️ 管理端</h1></div>
            <nav class="mt-4">
                <a href="/admin/index.html" class="block px-4 py-2 bg-green-50 text-green-600">课程管理</a>
                <a href="/admin/tasks.html" class="block px-4 py-2 text-gray-700 hover:bg-gray-50">任务管理</a>
                <a href="/admin/capability.html" class="block px-4 py-2 text-gray-700 hover:bg-gray-50">能力分析</a>
                <a href="/admin/knowledge.html" class="block px-4 py-2 text-gray-700 hover:bg-gray-50">知识管理</a>
            </nav>
        </div>
        <div class="flex-1 p-8">
            <h1 class="text-2xl font-bold mb-6">课程管理</h1>
            <div class="bg-white rounded-lg shadow">
                <div class="p-4 border-b flex justify-between">
                    <h2 class="text-lg font-semibold">课程列表</h2>
                    <button class="bg-blue-600 text-white px-4 py-2 rounded">+ 新增课程</button>
                </div>
                <table class="w-full">
                    <thead class="bg-gray-50">
                        <tr><th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">课程名称</th><th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">描述</th><th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">学员数</th><th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th><th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th></tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200">
                        <tr><td class="px-6 py-4">产品介绍话术训练</td><td class="px-6 py-4">学习如何有效介绍产品</td><td class="px-6 py-4">23</td><td class="px-6 py-4"><span class="px-2 py-1 bg-green-100 text-green-800 rounded text-sm">已发布</span></td><td class="px-6 py-4"><button class="text-blue-600 mr-2">编辑</button><button class="text-red-600">删除</button></td></tr>
                        <tr><td class="px-6 py-4">异议处理演练</td><td class="px-6 py-4">掌握处理客户异议的技巧</td><td class="px-6 py-4">18</td><td class="px-6 py-4"><span class="px-2 py-1 bg-green-100 text-green-800 rounded text-sm">已发布</span></td><td class="px-6 py-4"><button class="text-blue-600 mr-2">编辑</button><button class="text-red-600">删除</button></td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>'''

with open('/root/salesboost/webapp/admin/index.html', 'w', encoding='utf-8') as f:
    f.write(admin_html)

print('admin/index.html created')

PYTHON_EOF

echo "✓ 前端页面已创建"

# 5. 启动后端容器
echo -e "\n[5/6] 启动后端服务..."
docker run -d \
  --name salesboost-backend \
  -p 8000:8000 \
  --restart always \
  -v /root/salesboost/backend:/app \
  -w /app \
  -e TZ=Asia/Shanghai \
  python:3.11-slim \
  sh -c 'pip install --no-cache-dir -r requirements.txt && python main.py'

echo "✓ 后端容器已启动"

# 6. 启动前端容器
echo -e "\n[6/6] 启动前端服务..."
docker run -d \
  --name salesboost-frontend \
  -p 80:80 \
  --restart always \
  -v /root/salesboost/webapp:/usr/share/nginx/html:ro \
  -e TZ=Asia/Shanghai \
  nginx:alpine

echo "✓ 前端容器已启动"

# 等待服务启动
echo -e "\n等待服务启动..."
sleep 15

# 健康检查
echo -e "\n=== 健康检查 ==="

# 检查后端
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")
if [ "$BACKEND_STATUS" = "200" ]; then
    echo "✅ 后端服务正常 (HTTP 200)"
else
    echo "❌ 后端服务异常 (HTTP $BACKEND_STATUS)"
    docker logs salesboost-backend --tail 50
fi

# 检查前端
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ || echo "000")
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo "✅ 前端服务正常 (HTTP 200)"
else
    echo "❌ 前端服务异常 (HTTP $FRONTEND_STATUS)"
    docker logs salesboost-frontend --tail 50
fi

# 显示运行状态
echo -e "\n=== 服务运行状态 ==="
docker ps --filter name=salesboost --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n=== 部署完成 ==="
echo ""
echo "🌍 访问地址:"
echo "   前端主页: http://101.43.199.144"
echo "   学员端: http://101.43.199.144/student/tasks.html"
echo "   管理端: http://101.43.199.144/admin/"
echo "   后端API: http://101.43.199.144:8000"
echo "   API文档: http://101.43.199.144:8000/docs"
echo ""
echo "✅ SalesBoost 已成功部署!"
