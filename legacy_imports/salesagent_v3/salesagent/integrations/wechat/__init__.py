"""WeChat integration module initialization."""
from salesagent.integrations.wechat.wechat_personal import PersonalWeChatClient
from salesagent.integrations.wechat.wechat_work import WeChatWorkClient

__all__ = ["PersonalWeChatClient", "WeChatWorkClient"]
