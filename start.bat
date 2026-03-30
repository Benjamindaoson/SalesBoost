@echo off
REM SalesBoost 快速启动脚本
REM 用于同时启动后端和前端服务

echo ========================================
echo   SalesBoost 快速启动
echo ========================================
echo.

REM 检查是否在正确的目录
if not exist "backend" (
    echo [错误] 请在SalesBoost根目录运行此脚本
    pause
    exit /b 1
)

echo [1/3] 启动后端服务...
cd backend
start "SalesBoost Backend" cmd /k "python main.py"
cd ..

echo [2/3] 等待后端启动...
timeout /t 10 /nobreak > nul

echo [3/3] 启动前端服务...
cd frontend
start "SalesBoost Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ========================================
echo   启动完成!
echo ========================================
echo.
echo 后端地址: http://localhost:8000
echo 前端地址: http://localhost:5173 (或 5174)
echo API文档: http://localhost:8000/docs
echo.
echo 按任意键打开浏览器...
pause > nul

start http://localhost:5173/student/dashboard

echo.
echo 提示: 关闭此窗口不会停止服务
echo 要停止服务,请关闭后端和前端的命令行窗口
echo.
