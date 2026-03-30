"""
Configuration Validator

验证所有必需的环境变量和配置

Author: Claude (Anthropic)
Date: 2026-02-05
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """
    应用配置

    使用Pydantic进行验证，确保所有必需的配置都存在
    """

    # ============================================
    # LLM API Keys (至少需要一个)
    # ============================================
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API Key")
    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic API Key")
    GEMINI_API_KEY: str = Field(default="", alias="GOOGLE_API_KEY", description="Google Gemini API Key")

    # ============================================
    # Database (必需)
    # ============================================
    DATABASE_URL: str = Field(..., description="PostgreSQL Database URL")

    # ============================================
    # Authentication (必需)
    # ============================================
    # Supabase
    SUPABASE_URL: str = Field(default="", description="Supabase Project URL")
    SUPABASE_KEY: str = Field(default="", description="Supabase Anon Key")
    SUPABASE_JWT_SECRET: str = Field(default="", description="Supabase JWT Secret")

    # FastAPI JWT (alternative)
    JWT_SECRET_KEY: str = Field(default="", description="JWT Secret Key")
    SECRET_KEY: str = Field(default="", description="Application Secret Key")

    # ============================================
    # Optional Settings
    # ============================================
    ENVIRONMENT: str = Field(default="development", alias="ENV_STATE")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")

    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CORS_ORIGINS: str = Field(default="http://localhost:3000,http://localhost:5173")

    # Feature Flags
    ENABLE_CONSTITUTIONAL_AI: bool = Field(default=True)
    ENABLE_MOE_ROUTER: bool = Field(default=True)
    ENABLE_RL_LEARNING: bool = Field(default=True)

    # Model Configuration
    DEFAULT_LLM_PROVIDER: str = Field(default="openai")
    OPENAI_MODEL: str = Field(default="gpt-4-turbo-preview")
    ANTHROPIC_MODEL: str = Field(default="claude-3-5-sonnet-20241022")
    GEMINI_MODEL: str = Field(default="gemini-1.5-pro")

    class Config:
        env_file = ".env"
        case_sensitive = True

    @validator("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")
    def validate_api_keys(cls, v, field):
        """验证API Keys不是dummy值"""
        if v and v in ["dummy-key", "your-key-here", "changeme", ""]:
            raise ValueError(f"{field.name} cannot be a dummy value: {v}")
        return v

    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        """验证数据库URL格式"""
        if not v:
            raise ValueError("DATABASE_URL is required")
        if "change_me" in v or "password" in v:
            raise ValueError("DATABASE_URL contains default password, please change it")
        return v

    def validate_auth_config(self) -> Tuple[bool, str]:
        """
        验证认证配置

        Returns:
            (is_valid, auth_type)
        """
        has_supabase = all([
            self.SUPABASE_URL,
            self.SUPABASE_KEY,
            self.SUPABASE_JWT_SECRET
        ])

        has_fastapi_jwt = bool(self.JWT_SECRET_KEY or self.SECRET_KEY)

        if has_supabase:
            return True, "supabase"
        elif has_fastapi_jwt:
            return True, "fastapi"
        else:
            return False, "none"

    def validate_llm_providers(self) -> Tuple[bool, List[str]]:
        """
        验证至少有一个LLM Provider配置

        Returns:
            (is_valid, available_providers)
        """
        providers = []

        if self.OPENAI_API_KEY and self.OPENAI_API_KEY not in ["", "dummy-key"]:
            providers.append("openai")

        if self.ANTHROPIC_API_KEY and self.ANTHROPIC_API_KEY not in ["", "dummy-key"]:
            providers.append("anthropic")

        if self.GEMINI_API_KEY and self.GEMINI_API_KEY not in ["", "dummy-key"]:
            providers.append("gemini")

        return len(providers) > 0, providers


def validate_configuration() -> Tuple[bool, Dict[str, any]]:
    """
    验证完整配置

    Returns:
        (is_valid, report)
    """
    print("=" * 70)
    print("Configuration Validation")
    print("=" * 70)
    print()

    report = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "info": {},
    }

    try:
        # Load settings
        settings = Settings()

        # 1. Validate LLM Providers
        print("[1/4] Validating LLM Providers...")
        llm_valid, providers = settings.validate_llm_providers()

        if llm_valid:
            print(f"  ✓ Found {len(providers)} LLM provider(s): {', '.join(providers)}")
            report["info"]["llm_providers"] = providers
        else:
            print("  ✗ No valid LLM providers configured")
            report["errors"].append("At least one LLM provider (OpenAI, Anthropic, or Gemini) must be configured")
            report["valid"] = False

        # 2. Validate Authentication
        print("\n[2/4] Validating Authentication...")
        auth_valid, auth_type = settings.validate_auth_config()

        if auth_valid:
            print(f"  ✓ Authentication configured: {auth_type}")
            report["info"]["auth_type"] = auth_type
        else:
            print("  ✗ No authentication configured")
            report["errors"].append("Either Supabase or FastAPI JWT authentication must be configured")
            report["valid"] = False

        # 3. Validate Database
        print("\n[3/4] Validating Database...")
        if settings.DATABASE_URL:
            print(f"  ✓ Database URL configured")
            report["info"]["database"] = "configured"
        else:
            print("  ✗ Database URL not configured")
            report["errors"].append("DATABASE_URL is required")
            report["valid"] = False

        # 4. Check Optional Services
        print("\n[4/4] Checking Optional Services...")

        if settings.REDIS_URL:
            print(f"  ✓ Redis configured: {settings.REDIS_URL}")
        else:
            print("  ⚠ Redis not configured (caching will be disabled)")
            report["warnings"].append("Redis not configured")

        # Feature Flags
        print("\n[Features]")
        print(f"  • Constitutional AI: {'Enabled' if settings.ENABLE_CONSTITUTIONAL_AI else 'Disabled'}")
        print(f"  • MoE Router: {'Enabled' if settings.ENABLE_MOE_ROUTER else 'Disabled'}")
        print(f"  • RL Learning: {'Enabled' if settings.ENABLE_RL_LEARNING else 'Disabled'}")

        report["info"]["features"] = {
            "constitutional_ai": settings.ENABLE_CONSTITUTIONAL_AI,
            "moe_router": settings.ENABLE_MOE_ROUTER,
            "rl_learning": settings.ENABLE_RL_LEARNING,
        }

    except Exception as e:
        print(f"\n✗ Configuration validation failed: {e}")
        report["errors"].append(str(e))
        report["valid"] = False

    print()
    print("=" * 70)

    if report["valid"]:
        print("✓ Configuration is valid!")
    else:
        print("✗ Configuration has errors:")
        for error in report["errors"]:
            print(f"  • {error}")

    if report["warnings"]:
        print("\n⚠ Warnings:")
        for warning in report["warnings"]:
            print(f"  • {warning}")

    print("=" * 70)

    return report["valid"], report


def main():
    """主函数"""
    is_valid, report = validate_configuration()

    if not is_valid:
        print("\nPlease fix the configuration errors and try again.")
        print("See .env.example for reference.")
        sys.exit(1)
    else:
        print("\n✓ System is ready to start!")
        sys.exit(0)


if __name__ == "__main__":
    main()
