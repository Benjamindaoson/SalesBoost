from fastapi.testclient import TestClient
from main import app
import json

client = TestClient(app)

def test_websocket_connection():
    uri = "/ws/train?course_id=course-credit-card-001&scenario_id=scenario-annual-fee-001&persona_id=persona-wang-001&user_id=test-user-pytest"
    with client.websocket_connect(uri) as websocket:
        data = websocket.receive_json()
        assert data["type"] == "init"
        assert "session_id" in data

def test_websocket_turn_loop():
    uri = "/ws/train?course_id=course-credit-card-001&scenario_id=scenario-annual-fee-001&persona_id=persona-wang-001&user_id=test-user-pytest"
    with client.websocket_connect(uri) as websocket:
        # Init
        websocket.receive_json()
        
        # Turn 1
        websocket.send_json({
            "type": "message", 
            "content": "您好王总，我是您的客户经理，听说您要销卡？"
        })
        
        response = websocket.receive_json()
        assert response["type"] == "turn_result"
        assert "npc_response" in response
        assert "strategy_analysis" in response
        assert "adoption_analysis" in response  # Should be None for turn 1 or present
        
        # Turn 2
        websocket.send_json({
            "type": "message", 
            "content": "王总，其实这张卡的权益还是不错的，比如机场贵宾厅。"
        })
        
        response = websocket.receive_json()
        assert response["type"] == "turn_result"
