"""
Interaction Configuration Center - 交互配置中心
支持热更新、A/B测试、版本管理

替代原有硬编码配置，实现动态可配置
"""
import hashlib
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================
# Configuration Models
# ============================================================

class ConfigVersion(BaseModel):
    """配置版本"""
    version: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str = "system"
    description: str = ""
    hash: str = ""


class ReActConfig(BaseModel):
    """ReAct 推理配置"""
    max_iterations: int = Field(default=3, ge=1, le=10)
    confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    budget_per_step: float = Field(default=0.005)
    enable_reflection: bool = True
    fast_path_confidence: float = Field(default=0.9)
    temperature: float = Field(default=0.3)


class ImportanceWeights(BaseModel):
    """重要性权重配置"""
    stage_weight: float = Field(default=0.25)
    engagement_weight: float = Field(default=0.20)
    business_value_weight: float = Field(default=0.20)
    time_decay_weight: float = Field(default=0.15)
    risk_weight: float = Field(default=0.10)
    momentum_weight: float = Field(default=0.10)


class RiskPatternConfig(BaseModel):
    """风险模式配置"""
    id: str
    category: str
    level: str
    pattern_type: str
    pattern: str
    description: str
    action: str
    enabled: bool = True


class ModalityFlags(BaseModel):
    """模态开关配置"""
    text_enabled: bool = True
    voice_enabled: bool = False
    vision_enabled: bool = False
    voice_model: str = "whisper-1"
    vision_model: str = "gpt-4-vision-preview"
    voice_language: str = "zh"


class PersonalizationConfig(BaseModel):
    """个性化配置"""
    learning_style_detection: bool = False
    experience_level_detection: bool = True
    adaptive_difficulty: bool = True
    preference_tracking: bool = True


class ABTestConfig(BaseModel):
    """A/B 测试配置"""
    test_id: str
    name: str
    enabled: bool = True
    traffic_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    variant_a: Dict[str, Any] = Field(default_factory=dict)
    variant_b: Dict[str, Any] = Field(default_factory=dict)
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class InteractionConfig(BaseModel):
    """完整交互配置"""
    # 配置元信息
    version: ConfigVersion = Field(default_factory=lambda: ConfigVersion(version="1.0.0"))

    # ReAct 推理配置
    react: ReActConfig = Field(default_factory=ReActConfig)

    # 重要性权重
    importance_weights: ImportanceWeights = Field(default_factory=ImportanceWeights)

    # 风险模式
    risk_patterns: List[RiskPatternConfig] = Field(default_factory=list)

    # 模态配置
    modality: ModalityFlags = Field(default_factory=ModalityFlags)

    # 个性化配置
    personalization: PersonalizationConfig = Field(default_factory=PersonalizationConfig)

    # A/B 测试
    ab_tests: List[ABTestConfig] = Field(default_factory=list)


# ============================================================
# Configuration Manager
# ============================================================

class ConfigChangeEvent(BaseModel):
    """配置变更事件"""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    old_version: str
    new_version: str
    changed_fields: List[str]
    source: str = "api"  # api, file, remote


class InteractionConfigManager:
    """
    交互配置管理器

    核心能力:
    - 热更新配置
    - 版本管理
    - A/B 测试分流
    - 配置变更监听
    - 配置持久化
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        enable_file_watch: bool = True,
        auto_save: bool = True,
    ):
        self.config_path = Path(config_path) if config_path else Path("./config/interaction.json")
        self.enable_file_watch = enable_file_watch
        self.auto_save = auto_save

        # 当前配置
        self._config: InteractionConfig = InteractionConfig()
        self._config_lock = threading.RLock()

        # 变更监听器
        self._listeners: List[Callable[[ConfigChangeEvent], None]] = []

        # 版本历史
        self._version_history: List[ConfigVersion] = []

        # A/B 测试分配缓存
        self._ab_assignments: Dict[str, str] = {}  # user_id -> variant

        # 加载配置
        self._load_config()

        # 启动文件监控
        if enable_file_watch:
            self._start_file_watcher()

    def _load_config(self):
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._config = InteractionConfig(**data)
                logger.info(f"Loaded config version: {self._config.version.version}")
            except Exception as e:
                logger.warning(f"Failed to load config: {e}, using defaults")

    def _save_config(self):
        """保存配置"""
        if not self.auto_save:
            return

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config.model_dump(), f, ensure_ascii=False, indent=2)
            logger.info(f"Saved config version: {self._config.version.version}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def _start_file_watcher(self):
        """启动文件监控线程"""
        def watch():
            last_mtime = None
            while True:
                try:
                    if self.config_path.exists():
                        mtime = self.config_path.stat().st_mtime
                        if last_mtime and mtime > last_mtime:
                            logger.info("Config file changed, reloading...")
                            old_version = self._config.version.version
                            self._load_config()
                            self._notify_change(old_version, "file")
                        last_mtime = mtime
                except Exception as e:
                    logger.warning(f"File watcher error: {e}")
                time.sleep(5)  # 每 5 秒检查一次

        thread = threading.Thread(target=watch, daemon=True)
        thread.start()

    def _notify_change(self, old_version: str, source: str):
        """通知配置变更"""
        event = ConfigChangeEvent(
            old_version=old_version,
            new_version=self._config.version.version,
            changed_fields=[],  # TODO: 计算实际变更字段
            source=source,
        )

        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Listener error: {e}")

    # ===== 配置访问 =====

    @property
    def config(self) -> InteractionConfig:
        """获取当前配置"""
        with self._config_lock:
            return self._config

    @property
    def react(self) -> ReActConfig:
        """获取 ReAct 配置"""
        return self._config.react

    @property
    def importance_weights(self) -> ImportanceWeights:
        """获取重要性权重"""
        return self._config.importance_weights

    @property
    def modality(self) -> ModalityFlags:
        """获取模态配置"""
        return self._config.modality

    # ===== 配置更新 =====

    def update_react_config(self, **kwargs) -> bool:
        """更新 ReAct 配置"""
        with self._config_lock:
            old_version = self._config.version.version
            for key, value in kwargs.items():
                if hasattr(self._config.react, key):
                    setattr(self._config.react, key, value)

            self._bump_version()
            self._save_config()
            self._notify_change(old_version, "api")
            return True

    def update_importance_weights(self, **kwargs) -> bool:
        """更新重要性权重"""
        with self._config_lock:
            old_version = self._config.version.version
            for key, value in kwargs.items():
                if hasattr(self._config.importance_weights, key):
                    setattr(self._config.importance_weights, key, value)

            self._bump_version()
            self._save_config()
            self._notify_change(old_version, "api")
            return True

    def add_risk_pattern(self, pattern: RiskPatternConfig) -> bool:
        """添加风险模式"""
        with self._config_lock:
            old_version = self._config.version.version
            self._config.risk_patterns.append(pattern)
            self._bump_version()
            self._save_config()
            self._notify_change(old_version, "api")
            return True

    def remove_risk_pattern(self, pattern_id: str) -> bool:
        """移除风险模式"""
        with self._config_lock:
            old_version = self._config.version.version
            self._config.risk_patterns = [
                p for p in self._config.risk_patterns if p.id != pattern_id
            ]
            self._bump_version()
            self._save_config()
            self._notify_change(old_version, "api")
            return True

    def toggle_modality(self, modality: str, enabled: bool) -> bool:
        """切换模态开关"""
        with self._config_lock:
            old_version = self._config.version.version
            field = f"{modality}_enabled"
            if hasattr(self._config.modality, field):
                setattr(self._config.modality, field, enabled)
                self._bump_version()
                self._save_config()
                self._notify_change(old_version, "api")
                return True
            return False

    def _bump_version(self):
        """递增版本号"""
        parts = self._config.version.version.split(".")
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
            new_version = ".".join(parts)
        else:
            new_version = "1.0.1"

        # 计算配置哈希
        config_str = self._config.model_dump_json()
        config_hash = hashlib.md5(config_str.encode()).hexdigest()[:8]

        self._config.version = ConfigVersion(
            version=new_version,
            hash=config_hash,
        )
        self._version_history.append(self._config.version)

    # ===== A/B 测试 =====

    def create_ab_test(
        self,
        test_id: str,
        name: str,
        variant_a: Dict[str, Any],
        variant_b: Dict[str, Any],
        traffic_ratio: float = 0.5,
    ) -> bool:
        """创建 A/B 测试"""
        with self._config_lock:
            test = ABTestConfig(
                test_id=test_id,
                name=name,
                variant_a=variant_a,
                variant_b=variant_b,
                traffic_ratio=traffic_ratio,
                start_time=datetime.utcnow().isoformat(),
            )
            self._config.ab_tests.append(test)
            self._save_config()
            logger.info(f"Created A/B test: {test_id}")
            return True

    def get_ab_variant(self, test_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户的 A/B 测试变体"""
        # 检查缓存
        cache_key = f"{test_id}:{user_id}"
        if cache_key in self._ab_assignments:
            variant_key = self._ab_assignments[cache_key]
        else:
            # 基于用户 ID 哈希分配
            test = next((t for t in self._config.ab_tests if t.test_id == test_id and t.enabled), None)
            if not test:
                return None

            hash_value = int(hashlib.md5(f"{test_id}{user_id}".encode()).hexdigest(), 16)
            threshold = int(test.traffic_ratio * 0xFFFFFFFF)

            variant_key = "a" if (hash_value % 0xFFFFFFFF) < threshold else "b"
            self._ab_assignments[cache_key] = variant_key

        # 获取测试配置
        test = next((t for t in self._config.ab_tests if t.test_id == test_id), None)
        if not test:
            return None

        return test.variant_a if variant_key == "a" else test.variant_b

    def end_ab_test(self, test_id: str) -> bool:
        """结束 A/B 测试"""
        with self._config_lock:
            for test in self._config.ab_tests:
                if test.test_id == test_id:
                    test.enabled = False
                    test.end_time = datetime.utcnow().isoformat()
                    self._save_config()
                    return True
            return False

    # ===== 监听器 =====

    def add_listener(self, listener: Callable[[ConfigChangeEvent], None]):
        """添加配置变更监听器"""
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[ConfigChangeEvent], None]):
        """移除监听器"""
        if listener in self._listeners:
            self._listeners.remove(listener)

    # ===== 导入导出 =====

    def export_config(self) -> Dict[str, Any]:
        """导出当前配置"""
        return self._config.model_dump()

    def import_config(self, data: Dict[str, Any]) -> bool:
        """导入配置"""
        try:
            with self._config_lock:
                old_version = self._config.version.version
                self._config = InteractionConfig(**data)
                self._save_config()
                self._notify_change(old_version, "import")
                return True
        except Exception as e:
            logger.error(f"Failed to import config: {e}")
            return False

    def get_version_history(self) -> List[ConfigVersion]:
        """获取版本历史"""
        return self._version_history.copy()


# ============================================================
# Global Instance
# ============================================================

_config_manager: Optional[InteractionConfigManager] = None


def get_config_manager() -> InteractionConfigManager:
    """获取全局配置管理器"""
    global _config_manager
    if _config_manager is None:
        _config_manager = InteractionConfigManager()
    return _config_manager


def get_react_config() -> ReActConfig:
    """快捷方法: 获取 ReAct 配置"""
    return get_config_manager().react


def get_importance_weights() -> ImportanceWeights:
    """快捷方法: 获取重要性权重"""
    return get_config_manager().importance_weights


def is_modality_enabled(modality: str) -> bool:
    """快捷方法: 检查模态是否启用"""
    flags = get_config_manager().modality
    return getattr(flags, f"{modality}_enabled", False)
