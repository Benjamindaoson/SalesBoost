@echo off
REM ============================================================
REM Celery Worker Startup Script - Production Ready
REM ============================================================

echo.
echo ============================================================
echo   Starting Celery Worker for SalesBoost
echo ============================================================
echo.

cd /d D:\SalesBoost

REM Check if Redis is running
echo [1/3] Checking Redis connection...
python -c "import redis; r=redis.Redis(host='localhost', port=6379); r.ping(); print('Redis OK')" 2>nul
if errorlevel 1 (
    echo [ERROR] Redis is not running! Please start Redis first.
    echo Run: docker run -d -p 6379:6379 redis:latest
    pause
    exit /b 1
)

REM Start Celery Worker
echo [2/3] Starting Celery Worker...
echo.
echo Worker Configuration:
echo   - App: app.tasks.coach_tasks
echo   - Concurrency: solo (Windows compatible)
echo   - Log Level: info
echo   - Queues: default
echo.

start "Celery Worker - SalesBoost" cmd /k "celery -A app.tasks.coach_tasks worker --loglevel=info --pool=solo -E"

timeout /t 3 /nobreak >nul

REM Verify worker is running
echo [3/3] Verifying worker status...
celery -A app.tasks.coach_tasks inspect active >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Worker may not be fully started yet. Check the Celery window.
) else (
    echo [OK] Celery Worker is running!
)

echo.
echo ============================================================
echo   Celery Worker Started Successfully
echo ============================================================
echo.
echo The worker is running in a separate window.
echo To stop: Close the "Celery Worker - SalesBoost" window
echo.
pause
