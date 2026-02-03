@echo off
echo ========================================
echo SalesBoost Services Shutdown Script
echo ========================================
echo.

echo [1/3] Stopping FastAPI...
taskkill /FI "WINDOWTITLE eq SalesBoost FastAPI*" /F >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] FastAPI stopped
) else (
    echo [INFO] FastAPI was not running
)

echo.
echo [2/3] Stopping Celery Worker...
taskkill /FI "WINDOWTITLE eq SalesBoost Celery Worker*" /F >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Celery Worker stopped
) else (
    echo [INFO] Celery Worker was not running
)

echo.
echo [3/3] Stopping Redis...
docker stop salesboost-redis >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Redis stopped
) else (
    echo [INFO] Redis was not running
)

echo.
echo ========================================
echo All services stopped!
echo ========================================
echo.
pause
