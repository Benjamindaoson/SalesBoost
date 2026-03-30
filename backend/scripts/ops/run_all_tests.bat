@echo off
REM Quick Start Guide - Run All Tests and Get Real Data (Windows)

echo ==========================================
echo SalesBoost - Real Data Collection Script
echo ==========================================
echo.

REM Check if services are running
echo Step 1: Checking if backend is running...
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo X Backend not running. Please start it first:
    echo    python main.py
    exit /b 1
)
echo √ Backend is running
echo.

REM Install dependencies
echo Step 2: Installing dependencies...
pip install -q locust websocket-client ragas langchain openai datasets pandas
echo √ Dependencies installed
echo.

REM Run load tests
echo Step 3: Running load tests...
echo   [1/3] Testing with 10 users...
locust -f tests/performance/locust_websocket_test.py --host=ws://localhost:8000 -u 10 -r 2 --run-time 60s --headless --html=tests/performance/reports/load_test_10users.html >nul 2>&1

echo   [2/3] Testing with 50 users...
locust -f tests/performance/locust_websocket_test.py --host=ws://localhost:8000 -u 50 -r 5 --run-time 120s --headless --html=tests/performance/reports/load_test_50users.html >nul 2>&1

echo   [3/3] Testing with 100 users...
locust -f tests/performance/locust_websocket_test.py --host=ws://localhost:8000 -u 100 -r 10 --run-time 180s --headless --html=tests/performance/reports/load_test_100users.html >nul 2>&1

echo √ Load tests complete
echo.

REM Run RAG evaluation
echo Step 4: Running RAG evaluation...
if "%OPENAI_API_KEY%"=="" (
    echo !  OPENAI_API_KEY not set. Skipping RAGAS evaluation.
    echo    To run RAGAS: set OPENAI_API_KEY=your_key
) else (
    python tests/evaluation/rag_evaluation.py
    echo √ RAG evaluation complete
)
echo.

REM Display results
echo ==========================================
echo √ All Tests Complete!
echo ==========================================
echo.
echo 📊 View Results:
echo   Load Test Reports:
echo     - tests\performance\reports\load_test_10users.html
echo     - tests\performance\reports\load_test_50users.html
echo     - tests\performance\reports\load_test_100users.html
echo.
if not "%OPENAI_API_KEY%"=="" (
    echo   RAG Evaluation Reports:
    echo     - tests\evaluation\reports\rag_eval_*.html
    echo.
)
echo 📝 Next Steps:
echo   1. Open HTML reports in browser
echo   2. Extract real metrics from JSON files
echo   3. Update documentation with real data
echo   4. Delete or mark estimated values
echo.
echo 💡 Remember: Real data ^> Estimated data
echo ==========================================
pause
