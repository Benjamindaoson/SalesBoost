"""
模拟平台 Schema 定义
"""
from app.sales_simulation.schemas.scenario import (
    SimulationScenario,
    ScenarioConfig,
    CustomerProfile,
    SalesGoal,
)
from app.sales_simulation.schemas.trajectory import (
    Trajectory,
    TrajectoryStep,
    StepAction,
    StepObservation,
)
from app.sales_simulation.schemas.metrics import (
    TrajectoryMetrics,
    AggregatedMetrics,
    ConsistencyMetrics,
    DriftMetrics,
)
from app.sales_simulation.schemas.preference import (
    PreferencePair,
    SFTSample,
    GRPOSample,
)

__all__ = [
    # Scenario
    "SimulationScenario",
    "ScenarioConfig",
    "CustomerProfile",
    "SalesGoal",
    # Trajectory
    "Trajectory",
    "TrajectoryStep",
    "StepAction",
    "StepObservation",
    # Metrics
    "TrajectoryMetrics",
    "AggregatedMetrics",
    "ConsistencyMetrics",
    "DriftMetrics",
    # Preference
    "PreferencePair",
    "SFTSample",
    "GRPOSample",
]




