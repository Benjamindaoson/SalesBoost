"""
场景加载器
从 JSON/YAML 文件加载场景
"""
import logging
import json
from pathlib import Path
from typing import List, Optional

from app.sales_simulation.schemas.scenario import SimulationScenario

logger = logging.getLogger(__name__)


class ScenarioLoader:
    """场景加载器"""
    
    def __init__(self, scenarios_dir: Optional[str] = None):
        """
        初始化加载器
        
        Args:
            scenarios_dir: 场景目录路径
        """
        if scenarios_dir is None:
            # 默认路径
            scenarios_dir = Path(__file__).parent / "data"
        
        self.scenarios_dir = Path(scenarios_dir)
        logger.info(f"ScenarioLoader initialized with dir: {self.scenarios_dir}")
    
    def load_scenario(self, scenario_id: str) -> SimulationScenario:
        """
        加载单个场景
        
        Args:
            scenario_id: 场景 ID
            
        Returns:
            场景对象
        """
        scenario_file = self.scenarios_dir / f"{scenario_id}.json"
        
        if not scenario_file.exists():
            raise FileNotFoundError(f"Scenario file not found: {scenario_file}")
        
        with open(scenario_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        scenario = SimulationScenario.model_validate(data)
        logger.info(f"Loaded scenario: {scenario.id} - {scenario.name}")
        
        return scenario
    
    def load_all_scenarios(self) -> List[SimulationScenario]:
        """
        加载所有场景
        
        Returns:
            场景列表
        """
        scenarios = []
        
        if not self.scenarios_dir.exists():
            logger.warning(f"Scenarios directory not found: {self.scenarios_dir}")
            return scenarios
        
        for scenario_file in self.scenarios_dir.glob("*.json"):
            try:
                with open(scenario_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                scenario = SimulationScenario.model_validate(data)
                scenarios.append(scenario)
                logger.debug(f"Loaded scenario: {scenario.id}")
            except Exception as e:
                logger.error(f"Failed to load {scenario_file}: {e}")
        
        logger.info(f"Loaded {len(scenarios)} scenarios")
        return scenarios
    
    def list_scenario_ids(self) -> List[str]:
        """
        列出所有场景 ID
        
        Returns:
            场景 ID 列表
        """
        if not self.scenarios_dir.exists():
            return []
        
        ids = []
        for scenario_file in self.scenarios_dir.glob("*.json"):
            # 从文件名提取 ID
            scenario_id = scenario_file.stem
            ids.append(scenario_id)
        
        return sorted(ids)




