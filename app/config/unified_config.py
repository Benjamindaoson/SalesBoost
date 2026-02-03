"""
Unified Configuration Management System
Centralized configuration with hot-reload support
"""
import json
import logging
from typing import Any, Dict, Optional, Callable
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field
import asyncio

from app.engine.coordinator.dynamic_workflow import WorkflowConfig, NodeType
from core.config import get_settings

logger = logging.getLogger(__name__)


class ConfigSource(str):
    """Configuration source types"""
    FILE = "file"
    REDIS = "redis"
    ENV = "env"
    DEFAULT = "default"


class ConfigMetadata(BaseModel):
    """Configuration metadata"""
    source: str
    loaded_at: datetime
    version: str
    checksum: Optional[str] = None


class UnifiedConfigManager:
    """
    Unified Configuration Manager

    Features:
    - Multiple configuration sources (file, Redis, env)
    - Hot-reload support
    - Configuration validation
    - Change notifications

    Usage:
        manager = UnifiedConfigManager()
        await manager.initialize()

        # Get workflow config
        config = manager.get_workflow_config()

        # Register change listener
        manager.on_config_change(lambda cfg: print(f"Config changed: {cfg}"))

        # Hot reload
        await manager.reload()
    """

    def __init__(
        self,
        config_file: Optional[Path] = None,
        redis_client: Optional[Any] = None,
        auto_reload: bool = False,
        reload_interval: int = 60
    ):
        """
        Initialize configuration manager

        Args:
            config_file: Path to configuration file
            redis_client: Redis client for remote config
            auto_reload: Enable automatic config reloading
            reload_interval: Reload interval in seconds
        """
        self.config_file = config_file or Path("config/workflow_config.json")
        self.redis_client = redis_client
        self.auto_reload = auto_reload
        self.reload_interval = reload_interval

        # Current configuration
        self._workflow_config: Optional[WorkflowConfig] = None
        self._metadata: Optional[ConfigMetadata] = None

        # Change listeners
        self._listeners: list[Callable[[WorkflowConfig], None]] = []

        # Auto-reload task
        self._reload_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize configuration manager"""
        logger.info("[ConfigManager] Initializing...")

        # Load initial configuration
        await self.reload()

        # Start auto-reload if enabled
        if self.auto_reload:
            self._reload_task = asyncio.create_task(self._auto_reload_loop())
            logger.info(
                f"[ConfigManager] Auto-reload enabled (interval: {self.reload_interval}s)"
            )

    async def shutdown(self):
        """Shutdown configuration manager"""
        if self._reload_task:
            self._reload_task.cancel()
            try:
                await self._reload_task
            except asyncio.CancelledError:
                pass

        logger.info("[ConfigManager] Shutdown complete")

    async def reload(self) -> bool:
        """
        Reload configuration from sources

        Priority:
        1. Redis (if available)
        2. File
        3. Environment variables
        4. Default

        Returns:
            True if configuration changed
        """
        try:
            new_config, source = await self._load_config()

            # Check if config changed
            changed = (
                self._workflow_config is None or
                new_config.model_dump() != self._workflow_config.model_dump()
            )

            if changed:
                self._workflow_config = new_config
                self._metadata = ConfigMetadata(
                    source=source,
                    loaded_at=datetime.utcnow(),
                    version=new_config.version
                )

                logger.info(
                    f"[ConfigManager] Configuration loaded from {source}: "
                    f"{new_config.name} v{new_config.version}"
                )

                # Notify listeners
                await self._notify_listeners(new_config)

            return changed

        except Exception as e:
            logger.error(f"[ConfigManager] Failed to reload config: {e}", exc_info=True)
            return False

    async def _load_config(self) -> tuple[WorkflowConfig, str]:
        """Load configuration from available sources"""

        # 1. Try Redis
        if self.redis_client:
            try:
                config_data = await self.redis_client.get("workflow_config")
                if config_data:
                    config_dict = json.loads(config_data)
                    config = WorkflowConfig.model_validate(config_dict)
                    return config, ConfigSource.REDIS
            except Exception as e:
                logger.warning(f"[ConfigManager] Failed to load from Redis: {e}")

        # 2. Try file
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
                    config = WorkflowConfig.model_validate(config_dict)
                    return config, ConfigSource.FILE
            except Exception as e:
                logger.warning(f"[ConfigManager] Failed to load from file: {e}")

        # 3. Try environment variables
        try:
            settings = get_settings()
            if hasattr(settings, 'WORKFLOW_CONFIG_JSON'):
                config_dict = json.loads(settings.WORKFLOW_CONFIG_JSON)
                config = WorkflowConfig.model_validate(config_dict)
                return config, ConfigSource.ENV
        except Exception as e:
            logger.warning(f"[ConfigManager] Failed to load from env: {e}")

        # 4. Use default
        from app.engine.coordinator.dynamic_workflow import get_full_config
        return get_full_config(), ConfigSource.DEFAULT

    async def _auto_reload_loop(self):
        """Auto-reload loop"""
        while True:
            try:
                await asyncio.sleep(self.reload_interval)
                changed = await self.reload()
                if changed:
                    logger.info("[ConfigManager] Configuration auto-reloaded")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[ConfigManager] Auto-reload error: {e}", exc_info=True)

    async def _notify_listeners(self, config: WorkflowConfig):
        """Notify all registered listeners"""
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(config)
                else:
                    listener(config)
            except Exception as e:
                logger.error(f"[ConfigManager] Listener error: {e}", exc_info=True)

    def get_workflow_config(self) -> WorkflowConfig:
        """Get current workflow configuration"""
        if self._workflow_config is None:
            raise RuntimeError("Configuration not initialized. Call initialize() first.")
        return self._workflow_config

    def get_metadata(self) -> Optional[ConfigMetadata]:
        """Get configuration metadata"""
        return self._metadata

    def on_config_change(self, listener: Callable[[WorkflowConfig], None]):
        """
        Register configuration change listener

        Args:
            listener: Callback function (can be sync or async)
        """
        self._listeners.append(listener)

    async def update_config(
        self,
        config: WorkflowConfig,
        persist: bool = True
    ) -> bool:
        """
        Update configuration

        Args:
            config: New configuration
            persist: Whether to persist to storage

        Returns:
            True if successful
        """
        try:
            # Validate configuration
            config.model_validate(config.model_dump())

            # Persist if requested
            if persist:
                await self._persist_config(config)

            # Update in-memory config
            self._workflow_config = config
            self._metadata = ConfigMetadata(
                source="api",
                loaded_at=datetime.utcnow(),
                version=config.version
            )

            # Notify listeners
            await self._notify_listeners(config)

            logger.info(f"[ConfigManager] Configuration updated: {config.name}")
            return True

        except Exception as e:
            logger.error(f"[ConfigManager] Failed to update config: {e}", exc_info=True)
            return False

    async def _persist_config(self, config: WorkflowConfig):
        """Persist configuration to storage"""
        config_dict = config.model_dump()

        # Persist to Redis
        if self.redis_client:
            try:
                await self.redis_client.set(
                    "workflow_config",
                    json.dumps(config_dict)
                )
                logger.info("[ConfigManager] Config persisted to Redis")
            except Exception as e:
                logger.warning(f"[ConfigManager] Failed to persist to Redis: {e}")

        # Persist to file
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2)
            logger.info(f"[ConfigManager] Config persisted to {self.config_file}")
        except Exception as e:
            logger.warning(f"[ConfigManager] Failed to persist to file: {e}")


# ==================== Global Instance ====================

_config_manager: Optional[UnifiedConfigManager] = None


async def get_config_manager() -> UnifiedConfigManager:
    """Get global configuration manager instance"""
    global _config_manager

    if _config_manager is None:
        from core.redis import get_redis

        try:
            redis_client = await get_redis()
        except:
            redis_client = None

        _config_manager = UnifiedConfigManager(
            redis_client=redis_client,
            auto_reload=True,
            reload_interval=60
        )
        await _config_manager.initialize()

    return _config_manager


async def shutdown_config_manager():
    """Shutdown global configuration manager"""
    global _config_manager

    if _config_manager:
        await _config_manager.shutdown()
        _config_manager = None
