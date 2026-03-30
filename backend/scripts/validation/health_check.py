"""
健康检查脚本 - 使用 Python requests 避免 PowerShell 交互确认
"""
import sys
import requests


def check_health():
    """检查服务健康状态"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ 服务健康")
            print(f"   状态: {data.get('status')}")
            print(f"   版本: {data.get('version')}")
            print(f"   活跃会话: {data.get('active_sessions')}")
            return True
        else:
            print(f"❌ 服务异常: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务 (http://localhost:8000)")
        print("   请确保服务已启动: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False


if __name__ == "__main__":
    result = check_health()
    sys.exit(0 if result else 1)
