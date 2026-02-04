import pytest
import subprocess
import time
import os
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
    max_retries = 20
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
            
            # 3. Receive Turn Result
            turn_result_msg = await websocket.recv()
            turn_data = json.loads(turn_result_msg)
            
            assert turn_data["type"] == "turn_result"
            assert turn_data["turn"] == 1
            assert "npc_response" in turn_data
            assert "coach_suggestion" in turn_data
            print("Turn 1 completed")
            
            # 4. Verify DB Persistence (Real Check)
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
