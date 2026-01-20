"""
FSM 状态一致性验证
防止 Simulation 和主系统 FSM 语义漂移

【工业级防护】
- 启动时验证状态一致性
- 运行时检测非法状态
- 防止双 FSM 问题
"""
import logging
from typing import List, Set

from app.schemas.fsm import SalesStage
from app.fsm.protocol import SalesFSMState, FSM_STATE_ORDER, validate_state

logger = logging.getLogger(__name__)


class FSMConsistencyValidator:
    """
    FSM 一致性验证器
    
    【核心功能】
    - 验证 Simulation 使用的状态名称与主系统一致
    - 检测非法状态
    - 防止状态语义漂移
    """
    
    @staticmethod
    def validate_simulation_startup() -> None:
        """
        Simulation 启动时验证
        
        【验证项】
        1. 主系统 SalesStage 与 Protocol SalesFSMState 一致
        2. 状态顺序一致
        3. 状态名称完全匹配
        
        Raises:
            RuntimeError: 如果发现不一致
        """
        logger.info("Validating FSM consistency between Online and Offline systems...")
        
        # 验证 1: 状态名称集合一致
        online_states: Set[str] = {stage.value for stage in SalesStage}
        protocol_states: Set[str] = {state.value for state in SalesFSMState}
        
        if online_states != protocol_states:
            missing_in_protocol = online_states - protocol_states
            missing_in_online = protocol_states - online_states
            
            error_msg = "FSM State Mismatch Detected!\n"
            if missing_in_protocol:
                error_msg += f"  States in Online but not in Protocol: {missing_in_protocol}\n"
            if missing_in_online:
                error_msg += f"  States in Protocol but not in Online: {missing_in_online}\n"
            
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # 验证 2: 状态顺序一致（前5个核心状态）
        online_order = [
            SalesStage.OPENING.value,
            SalesStage.NEEDS_DISCOVERY.value,
            SalesStage.PRODUCT_INTRO.value,
            SalesStage.OBJECTION_HANDLING.value,
            SalesStage.CLOSING.value,
        ]
        
        protocol_order = [state.value for state in FSM_STATE_ORDER[:5]]
        
        if online_order != protocol_order:
            error_msg = (
                f"FSM State Order Mismatch!\n"
                f"  Online Order: {online_order}\n"
                f"  Protocol Order: {protocol_order}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.info("✅ FSM consistency validation passed!")
        logger.info(f"  Validated {len(online_states)} states")
        logger.info(f"  State order: {' -> '.join(online_order)}")
    
    @staticmethod
    def validate_state_at_runtime(state_name: str) -> None:
        """
        运行时验证状态
        
        Args:
            state_name: 状态名称
            
        Raises:
            ValueError: 如果状态非法
        """
        if not validate_state(state_name):
            error_msg = (
                f"Invalid FSM state detected at runtime: '{state_name}'\n"
                f"Valid states: {[s.value for s in SalesFSMState]}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    @staticmethod
    def get_consistency_report() -> dict:
        """
        获取一致性报告
        
        Returns:
            一致性报告字典
        """
        online_states = {stage.value for stage in SalesStage}
        protocol_states = {state.value for state in SalesFSMState}
        
        return {
            "online_states": sorted(online_states),
            "protocol_states": sorted(protocol_states),
            "is_consistent": online_states == protocol_states,
            "num_states": len(online_states),
        }


def validate_on_import() -> None:
    """
    模块导入时自动验证
    
    【重要】
    这确保任何使用 Simulation 的代码都会自动触发验证
    """
    try:
        FSMConsistencyValidator.validate_simulation_startup()
    except RuntimeError as e:
        logger.critical(f"FSM Consistency Validation Failed on Import: {e}")
        raise


# 自动验证（模块导入时执行）
validate_on_import()




