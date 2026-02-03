@echo off
echo ========================================
echo SalesBoost Services Startup Script
echo ========================================
echo.

REM 检查Docker是否运行
echo [1/4] Checking Docker...
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop first, then run this script again.
    echo.
    pause
    exit /b 1
)
echo [OK] Docker is running

REM 启动Redis
echo.
echo [2/4] Starting Redis...
docker run -d --name salesboost-redis -p 6379:6379 redis:latest >nul 2>&1
if %errorlevel% neq 0 (
    echo Redis container already exists, starting it...
    docker start salesboost-redis >nul 2>&1
)
timeout /t 2 /nobreak >nul
echo [OK] Redis started on port 6379

REM 启动Celery Worker
echo.
echo [3/4] Starting Celery Worker...
start "SalesBoost Celery Worker" cmd /k "cd /d d:\SalesBoost && echo Starting Celery Worker... && celery -A app.tasks.coach_tasks worker --loglevel=info"
timeout /t 2 /nobreak >nul
echo [OK] Celery Worker started in new window

REM 启动FastAPI
echo.
echo [4/4] Starting FastAPI...
start "SalesBoost FastAPI" cmd /k "cd /d d:\SalesBoost && echo Starting FastAPI... && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3 /nobreak >nul
echo [OK] FastAPI started in new window

echo.
echo ========================================
echo All services started successfully!
echo ========================================
echo.
echo Services:
echo   - Redis:      localhost:6379
echo   - Celery:     Running in background window
echo   - FastAPI:    http://localhost:8000
echo   - API Docs:   http://localhost:8000/docs
echo   - Metrics:    http://localhost:8000/metrics
echo.
echo Press any key to open API documentation...
pause >nul
start http://localhost:8000/docs
