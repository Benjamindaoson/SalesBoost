import pytest
import asyncio
import subprocess
import time
import os
import signal
import sys
import websockets
import json
import sqlite3
import requests

# Configure Uvicorn server process
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8003
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
WS_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}/ws/train"

@pytest.fixture(scope="session")
def uvicorn_server():
    """Start Uvicorn server as a subprocess for integration testing."""
    # Start the server
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", SERVER_HOST, "--port", str(SERVER_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Wait for server to start
    max_retries = 30 # Increased timeout
    server_started = False
    for i in range(max_retries):
        try:
            time.sleep(1)
            response = requests.get(f"{BASE_URL}/health", timeout=1)
            if response.status_code == 200:
                server_started = True
                break
        except Exception:
            pass
            
    if not server_started:
        # Dump server logs for debugging
        outs, errs = proc.communicate(timeout=1)
        print("Server stdout:", outs.decode() if outs else "None")
        print("Server stderr:", errs.decode() if errs else "None")
        proc.terminate()
        pytest.fail("Server failed to start within timeout")

    yield proc
    
    # Cleanup
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

@pytest.mark.asyncio
async def test_websocket_integration_real(uvicorn_server):
    """
    Real WebSocket Integration Test (P0)
    Connects to a running Uvicorn instance using websockets library.
    """
    
    # Params
    params = "course_id=course-credit-card-001&scenario_id=scenario-annual-fee-001&persona_id=persona-wang-001&user_id=test-user-integration-001"
    uri = f"{WS_URL}?{params}"
    
    print(f"Connecting to {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            # 1. Verify Init Message
            init_msg = await websocket.recv()
            init_data = json.loads(init_msg)
            
            assert init_data["type"] == "init"
            assert "session_id" in init_data
            session_id = init_data["session_id"]
            print(f"Session initialized: {session_id}")
            
            # 2. Send Message (Turn 1)
            await websocket.send(json.dumps({
                "type": "message",
                "content": "您好王总，我是小李。"
            }))
            
            # 3. Receive Turn Result (Partial)
            turn_partial_msg = await websocket.recv()
            turn_partial = json.loads(turn_partial_msg)
            
            assert turn_partial["type"] == "turn_result_partial"
            assert "npc_response" in turn_partial
            print("Turn 1 (Partial) completed")
            
            # 4. Receive Analysis Result (Full)
            # Depending on processing speed, this might take a moment
            # We set a timeout for the next message
            turn_analysis_msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            turn_analysis = json.loads(turn_analysis_msg)
            
            assert turn_analysis["type"] == "turn_analysis"
            assert "coach_suggestion" in turn_analysis
            print("Turn 1 (Analysis) completed")
            
            # 5. Verify DB Persistence (Real Check)
            db_path = "salesboost.db"
            # In a real environment, we should configure the DB path via env var to ensure consistency
            # Assuming default salesboost.db is created in CWD
            
            assert os.path.exists(db_path), f"DB file not found at {os.path.abspath(db_path)}"
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check Session
            cursor.execute("SELECT id, status FROM sessions WHERE id=?", (session_id,))
            session_row = cursor.fetchone()
            assert session_row is not None, "Session record not found in DB"
            assert session_row[1] == "active"
            
            # Check Messages (User + NPC)
            cursor.execute("SELECT count(*) FROM messages WHERE session_id=?", (session_id,))
            msg_count = cursor.fetchone()[0]
            assert msg_count >= 2, f"Expected at least 2 messages, found {msg_count}"
            
            conn.close()
            print("DB Verification Passed")
            
    except Exception as e:
        pytest.fail(f"WebSocket interaction failed: {e}")

if __name__ == "__main__":
    # Allow running this file directly for debugging
    pytest.main([__file__, "-v", "-s"])
