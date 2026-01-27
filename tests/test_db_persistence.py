import sqlite3
import pytest
from fastapi.testclient import TestClient
from main import app
import os

client = TestClient(app)

def test_db_persistence_real():
    # 1. Run a session via WebSocket
    user_id = "test-user-db-check"
    uri = f"/ws/train?course_id=course-credit-card-001&scenario_id=scenario-annual-fee-001&persona_id=persona-wang-001&user_id={user_id}"
    
    session_id = None
    
    with client.websocket_connect(uri) as websocket:
        init_data = websocket.receive_json()
        session_id = init_data["session_id"]
        
        # Turn 1
        websocket.send_json({"type": "message", "content": "您好王总，我是小李。"})
        websocket.receive_json()
        
    # 2. Check DB
    # Connect to sqlite file directly
    db_path = "salesboost.db"
    assert os.path.exists(db_path), "Database file not found"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Checking DB for Session ID: {session_id}")
    
    # Check Session
    cursor.execute("SELECT id FROM sessions WHERE id=?", (session_id,))
    assert cursor.fetchone() is not None, "Session not found in DB"
    
    # Check Messages
    cursor.execute("SELECT count(*) FROM messages WHERE session_id=?", (session_id,))
    msg_count = cursor.fetchone()[0]
    assert msg_count >= 2, f"Messages count mismatch: {msg_count}"
    
    # Check Strategy Decision
    cursor.execute("SELECT count(*) FROM strategy_decisions WHERE session_id=?", (session_id,))
    strat_count = cursor.fetchone()[0]
    assert strat_count >= 1, f"Strategy decisions count mismatch: {strat_count}"
    
    # Check Adoption Record (might be 0 for turn 1, but let's check table exists)
    cursor.execute("SELECT count(*) FROM adoption_records WHERE session_id=?", (session_id,))
    cursor.fetchone()
    
    conn.close()
