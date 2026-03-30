@echo off
REM SalesBoost Quick Start Script (Windows)
REM This script starts both backend and frontend servers

echo ==========================================
echo SalesBoost - Quick Start
echo ==========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python not found. Please install Python 3.11+
    pause
    exit /b 1
)
echo √ Python found

REM Check if Node.js is available
node --version >nul 2>&1
if errorlevel 1 (
    echo X Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)
echo √ Node.js found
echo.

REM Start backend
echo Step 1: Starting backend server...
echo   Backend will run on http://localhost:8000
start "SalesBoost Backend" cmd /k "cd /d %~dp0 && python main.py"
timeout /t 5 /nobreak >nul
echo √ Backend started
echo.

REM Start frontend
echo Step 2: Starting frontend server...
echo   Frontend will run on http://localhost:5173
start "SalesBoost Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 3 /nobreak >nul
echo √ Frontend started
echo.

echo ==========================================
echo √ SalesBoost is starting!
echo ==========================================
echo.
echo 📊 Services:
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   Health:   http://localhost:8000/health
echo.
echo 🌐 Open your browser and visit:
echo   http://localhost:5173
echo.
echo 💡 To stop the servers:
echo   Close the terminal windows or press Ctrl+C
echo.
echo ==========================================
pause
