"""Configuration settings for WeChat integrations."""
from pydantic import Field
from pydantic_settings import BaseSettings


class WeChatSettings(BaseSettings):
    """WeChat configuration settings."""

    # Personal WeChat
    wechat_personal_enabled: bool = Field(default=True, env="WECHAT_PERSONAL_ENABLED")
    wechat_personal_auto_login: bool = Field(default=True, env="WECHAT_PERSONAL_AUTO_LOGIN")
    wechat_personal_qr_callback_url: str = Field(default="", env="WECHAT_PERSONAL_QR_CALLBACK_URL")
    wechat_personal_hot_reload: bool = Field(default=True, env="WECHAT_PERSONAL_HOT_RELOAD")
    wechat_personal_session_file: str = Field(default=".wechat_session.pkl", env="WECHAT_PERSONAL_SESSION_FILE")

    # Enterprise WeChat (WeChat Work)
    wechat_work_enabled: bool = Field(default=False, env="WECHAT_WORK_ENABLED")
    wechat_work_corp_id: str = Field(default="", env="WECHAT_WORK_CORP_ID")
    wechat_work_agent_id: str = Field(default="", env="WECHAT_WORK_AGENT_ID")
    wechat_work_secret: str = Field(default="", env="WECHAT_WORK_SECRET")
    wechat_work_token: str = Field(default="", env="WECHAT_WORK_TOKEN")
    wechat_work_encoding_aes_key: str = Field(default="", env="WECHAT_WORK_ENCODING_AES_KEY")
    wechat_work_webhook_url: str = Field(default="", env="WECHAT_WORK_WEBHOOK_URL")

    class Config:
        env_file = ".env"
        case_sensitive = False
