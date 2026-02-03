# 部署说明 - Redis配置

## Redis安装与启动

### 方法1: 使用Docker（推荐）

1. **启动Docker Desktop**
   - 打开Docker Desktop应用
   - 等待Docker引擎启动完成

2. **启动Redis容器**
   ```bash
   docker run -d --name salesboost-redis -p 6379:6379 redis:latest
   ```

3. **验证Redis运行**
   ```bash
   docker ps | findstr redis
   ```

### 方法2: 使用WSL2 + Redis

1. **安装WSL2**
   ```bash
   wsl --install
   ```

2. **在WSL中安装Redis**
   ```bash
   wsl
   sudo apt update
   sudo apt install redis-server
   ```

3. **启动Redis**
   ```bash
   wsl redis-server --daemonize yes
   ```

### 方法3: Windows原生Redis（不推荐）

1. **下载Redis for Windows**
   - 访问: https://github.com/microsoftarchive/redis/releases
   - 下载最新版本的.msi安装包

2. **安装并启动**
   - 运行安装程序
   - Redis会自动作为Windows服务启动

### 验证Redis连接

```bash
# 使用redis-cli测试
redis-cli ping
# 应该返回: PONG

# 或使用Python测试
python -c "import redis; r=redis.Redis(); print(r.ping())"
# 应该返回: True
```

---

## 当前部署状态

### ✅ 已完成
- [x] 依赖安装完成
- [x] 代码实现完成
- [x] 配置文件创建完成

### ⏳ 待完成
- [ ] Redis启动（需要手动启动Docker Desktop或WSL）
- [ ] Celery Worker启动
- [ ] FastAPI应用启动
- [ ] 功能验证

---

## 快速启动脚本

创建 `start_services.bat`:

```batch
@echo off
echo Starting SalesBoost Services...

REM 检查Docker是否运行
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

REM 启动Redis
echo Starting Redis...
docker run -d --name salesboost-redis -p 6379:6379 redis:latest 2>nul
if %errorlevel% neq 0 (
    echo Redis container already exists, starting it...
    docker start salesboost-redis
)

REM 等待Redis启动
timeout /t 3 /nobreak >nul

REM 启动Celery Worker（新窗口）
echo Starting Celery Worker...
start "Celery Worker" cmd /k "cd /d d:\SalesBoost && celery -A app.tasks.coach_tasks worker --loglevel=info"

REM 等待Celery启动
timeout /t 3 /nobreak >nul

REM 启动FastAPI（新窗口）
echo Starting FastAPI...
start "FastAPI" cmd /k "cd /d d:\SalesBoost && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo.
echo All services started!
echo - Redis: localhost:6379
echo - Celery Worker: Running in background
echo - FastAPI: http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo - Metrics: http://localhost:8000/metrics
echo.
pause
```

创建 `stop_services.bat`:

```batch
@echo off
echo Stopping SalesBoost Services...

REM 停止Redis
docker stop salesboost-redis

REM 停止Celery和FastAPI（通过窗口标题）
taskkill /FI "WINDOWTITLE eq Celery Worker*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq FastAPI*" /F >nul 2>&1

echo All services stopped!
pause
```

---

## 手动启动步骤

### 1. 启动Redis
```bash
# 方法A: Docker
docker start salesboost-redis

# 方法B: WSL
wsl redis-server --daemonize yes
```

### 2. 启动Celery Worker（新终端）
```bash
cd d:\SalesBoost
celery -A app.tasks.coach_tasks worker --loglevel=info
```

### 3. 启动FastAPI（新终端）
```bash
cd d:\SalesBoost
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 验证部署
```bash
# 测试用户反馈API
curl -X POST http://localhost:8000/api/v1/feedback/submit ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\": \"test\", \"turn_number\": 1, \"rating\": 5}"

# 查看Prometheus metrics
curl http://localhost:8000/metrics | findstr coordinator

# 访问API文档
start http://localhost:8000/docs
```

---

## 故障排查

### 问题1: Redis连接失败
**错误**: `redis.exceptions.ConnectionError`

**解决**:
```bash
# 检查Redis是否运行
docker ps | findstr redis

# 如果没有运行，启动它
docker start salesboost-redis

# 测试连接
python -c "import redis; r=redis.Redis(); print(r.ping())"
```

### 问题2: Celery无法连接Redis
**错误**: `kombu.exceptions.OperationalError`

**解决**:
- 确保Redis正在运行
- 检查REDIS_URL配置（默认: redis://localhost:6379/0）
- 验证防火墙没有阻止6379端口

### 问题3: FastAPI启动失败
**错误**: `ModuleNotFoundError`

**解决**:
```bash
# 重新安装依赖
pip install -r requirements-coordinator.txt

# 检查Python环境
python --version
pip list | findstr celery
```

---

## 监控与日志

### 查看Celery日志
```bash
# Celery worker会在终端输出日志
# 或查看日志文件（如果配置了）
type celery.log
```

### 查看FastAPI日志
```bash
# FastAPI会在终端输出日志
# 或使用uvicorn的日志配置
```

### 查看Redis日志
```bash
# Docker容器日志
docker logs salesboost-redis

# 或连接到容器
docker exec -it salesboost-redis redis-cli
```

---

## 生产环境部署

### 使用Supervisor管理进程

创建 `supervisor.conf`:

```ini
[program:celery]
command=celery -A app.tasks.coach_tasks worker --loglevel=info
directory=d:\SalesBoost
autostart=true
autorestart=true
stderr_logfile=d:\SalesBoost\logs\celery.err.log
stdout_logfile=d:\SalesBoost\logs\celery.out.log

[program:fastapi]
command=uvicorn main:app --host 0.0.0.0 --port 8000
directory=d:\SalesBoost
autostart=true
autorestart=true
stderr_logfile=d:\SalesBoost\logs\fastapi.err.log
stdout_logfile=d:\SalesBoost\logs\fastapi.out.log
```

### 使用Docker Compose

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:latest
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  celery:
    build: .
    command: celery -A app.tasks.coach_tasks worker --loglevel=info
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0

  fastapi:
    build: .
    command: uvicorn main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - celery
    environment:
      - REDIS_URL=redis://redis:6379/0

volumes:
  redis_data:
```

启动所有服务:
```bash
docker-compose up -d
```

---

## 下一步

1. **启动Docker Desktop**
2. **运行 `start_services.bat`**
3. **访问 http://localhost:8000/docs 查看API文档**
4. **运行验证测试**

祝您部署顺利！🚀
