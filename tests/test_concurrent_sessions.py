import pytest
import asyncio
import websockets
import json
import uuid
import subprocess
import sys
import time
import os
import requests
import sqlite3

# Server Config
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8004  # Use a distinct port for concurrency tests
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
WS_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}/ws/train"

CONCURRENT_USERS = 10
TURNS_PER_USER = 3

@pytest.fixture(scope="session")
def server_process():
    """Start the server for the duration of the test session."""
    env = os.environ.copy()
    # Ensure we use a test DB if possible, or just the main one (concurrency shouldn't care)
    
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "app.main:app", 
        "--host", SERVER_HOST, 
        "--port", str(SERVER_PORT)
    ]
    
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Wait for health check
    start_time = time.time()
    while time.time() - start_time < 15:
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=1)
            if resp.status_code == 200:
                break
        except:
            time.sleep(0.5)
    else:
        proc.terminate()
        stdout, stderr = proc.communicate()
        pytest.fail(f"Server failed to start: {stderr.decode()}")
        
    yield proc
    
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except:
        proc.kill()

async def simulate_user_session(user_index):
    """Simulate a single user session."""
    user_id = f"concurrent_user_{user_index}_{uuid.uuid4().hex[:8]}"
    params = f"course_id=course-001&scenario_id=scenario-001&persona_id=persona-001&user_id={user_id}"
    uri = f"{WS_URL}?{params}"
    
    session_id = None
    turns_completed = 0
    
    try:
        async with websockets.connect(uri) as websocket:
            # 1. Init
            init_msg = await websocket.recv()
            init_data = json.loads(init_msg)
            session_id = init_data.get("session_id")
            assert session_id is not None
            
            # 2. Turns
            for i in range(TURNS_PER_USER):
                msg = {
                    "type": "message",
                    "content": f"User {user_index} message turn {i}"
                }
                await websocket.send(json.dumps(msg))
                
                # Receive response
                resp = await websocket.recv()
                resp_data = json.loads(resp)
                assert resp_data["type"] == "turn_result"
                assert resp_data["user_message"] == msg["content"]
                turns_completed += 1
                
                # Small delay to vary timing
                await asyncio.sleep(0.1)
                
    except Exception as e:
        return {"user_id": user_id, "success": False, "error": str(e)}
        
    return {
        "user_id": user_id, 
        "session_id": session_id, 
        "success": True, 
        "turns": turns_completed
    }

@pytest.mark.asyncio
async def test_concurrent_sessions(server_process):
    """
    P0: Multi-user concurrency verification.
    """
    print(f"\nStarting {CONCURRENT_USERS} concurrent sessions...")
    
    tasks = [simulate_user_session(i) for i in range(CONCURRENT_USERS)]
    results = await asyncio.gather(*tasks)
    
    # 1. Verify Success Rate
    failures = [r for r in results if not r["success"]]
    assert len(failures) == 0, f"Some sessions failed: {failures}"
    
    # 2. Verify DB Isolation
    # Connect to DB and check records
    db_path = "salesboost.db"  # Assuming default path
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    [r["user_id"] for r in results]
    session_ids = [r["session_id"] for r in results]
    
    # Check Session Uniqueness
    assert len(set(session_ids)) == CONCURRENT_USERS, "Duplicate session IDs detected!"
    
    # Check Data Integrity per User
    for res in results:
        uid = res["user_id"]
        sid = res["session_id"]
        
        # Verify Session Record
        cursor.execute("SELECT count(*) FROM sessions WHERE id=? AND user_id=?", (sid, uid))
        assert cursor.fetchone()[0] == 1, f"Session record missing or mismatched for {uid}"
        
        # Verify Messages
        # Expecting at least TURNS_PER_USER * 2 (User + NPC)
        cursor.execute("SELECT count(*) FROM messages WHERE session_id=?", (sid,))
        msg_count = cursor.fetchone()[0]
        assert msg_count >= TURNS_PER_USER * 2, f"Message count low for {sid}"
        
        # Verify Strategy Decisions
        cursor.execute("SELECT count(*) FROM strategy_decisions WHERE session_id=?", (sid,))
        strat_count = cursor.fetchone()[0]
        assert strat_count >= TURNS_PER_USER, f"Strategy decisions missing for {sid}"
        
    conn.close()
    print("\n✅ Concurrency Test Passed: All sessions isolated and persisted correctly.")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
