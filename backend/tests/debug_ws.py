from fastapi.testclient import TestClient
from main import app
import traceback

client = TestClient(app)

def test_websocket_debug():
    uri = "/ws/train?course_id=course-credit-card-001&scenario_id=scenario-annual-fee-001&persona_id=persona-wang-001&user_id=test-user-debug"
    print(f"Connecting to {uri}")
    try:
        with client.websocket_connect(uri) as websocket:
            print("Connected!")
            data = websocket.receive_json()
            print(f"Received: {data}")
    except Exception as e:
        print("Exception occurred:")
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    test_websocket_debug()
