# Sales Simulation Demo Script

## Overview

The `scripts/run_simulation_demo.py` script provides a dry-run demonstration of the P0 simulation flow using `SingleAgentSimulationRunner`.

## Features

- ✅ **Complete Setup**: Initializes all required components
- ✅ **Real Agent**: Uses actual `DialogueAgent` (not mock)
- ✅ **Dummy Scenario**: Creates a test scenario with 3 turns
- ✅ **Pretty Output**: Formats simulation results and conversation trajectory
- ✅ **Error Handling**: Graceful error handling and logging

## Prerequisites

1. **Environment Variables**:
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   # Optional: Custom API endpoint
   export OPENAI_BASE_URL=https://api.siliconflow.cn/v1
   ```

2. **Dependencies**:
   - All dependencies from `requirements.txt` should be installed
   - Python 3.11+

## Usage

### Basic Run

```bash
python scripts/run_simulation_demo.py
```

### Expected Output

```
🚀 Starting Sales Simulation Demo
Using OpenAI API: https://api.siliconflow.cn/v1
Model: gpt-4

📋 Step 1: Creating simulation config...
   Max turns: 3
   Seed: 42

📋 Step 2: Creating scenario...
   Scenario ID: demo_scenario_001
   Scenario Name: 演示场景 - 冷呼销售
   Customer: 张总 (技术总监)
   Goal: demo
   Max Turns: 3

📋 Step 3: Initializing DialogueAgent...
   ✅ DialogueAgent initialized

📋 Step 4: Creating agent adapter...
   ✅ Agent adapter created

📋 Step 5: Initializing simulation runner...
   ✅ Runner initialized

🎬 Step 6: Running simulation episode...
   Episode ID: test_run_001
--------------------------------------------------------------------------------

================================================================================
SIMULATION RESULT
================================================================================
Episode ID: test_run_001
Trajectory ID: sim_traj_test_run_001_abc12345
Total Steps: 3
Total Reward: 2.45
Successful Sale: ✅ YES
Duration: 5.23 seconds
Status: completed
================================================================================

================================================================================
CONVERSATION TRAJECTORY
================================================================================

--- Turn 1 ---
🤖 Agent (question):
   李总，您目前团队在协作上遇到的最大挑战是什么？
   💭 Reasoning: Generated dialogue with professional tone
   📊 Confidence: 0.85

👤 Customer Response:
   我们现在用的工具确实有点老了，主要问题是不同部门的数据打不通
   😊 Mood: 0.55
   💡 Interest: 0.45
   📍 Stage: NEEDS_DISCOVERY
   🎯 Goal Progress: 0.25
   ⭐ Step Reward: 0.80
   📈 Step Score: 0.75

--- Turn 2 ---
...

================================================================================
TRAJECTORY SUMMARY
================================================================================
Total Steps: 3
Total Reward: 2.45
Goal Achieved: ✅ YES
Duration: 5.23s
================================================================================

✅ Simulation demo completed successfully!
```

## Architecture

### Components

1. **SimulationConfig**: Global simulation configuration
   - `max_turns`: 3 (for demo)
   - `seed`: 42 (for reproducibility)

2. **SimulationScenario**: Test scenario
   - Customer: 张总 (技术总监)
   - Goal: Demo appointment
   - Max turns: 3

3. **DialogueAgent**: Real LLM-powered agent
   - Uses OpenAI API
   - Generates natural dialogue

4. **DialogueAgentAdapter**: Adapter wrapper
   - Converts `observation` + `history` → DialogueAgent format
   - Implements `act()` method required by runner
   - Determines action type based on stage

5. **SingleAgentSimulationRunner**: Main runner
   - Drives agent-environment interaction
   - Collects trajectory data
   - Returns `SimulationResult`

### Flow

```
1. Create Config
   ↓
2. Create Scenario
   ↓
3. Initialize DialogueAgent
   ↓
4. Create Adapter (DialogueAgentAdapter)
   ↓
5. Initialize Runner
   ↓
6. Run Episode
   ├── Reset Environment
   ├── Loop (max_turns):
   │   ├── Agent.act(observation, history)
   │   ├── Environment.step(action)
   │   └── Record trajectory step
   └── Collect Results
   ↓
7. Print Results
```

## Customization

### Change Max Turns

Edit `create_dummy_scenario()`:

```python
config=ScenarioConfig(
    max_turns=5,  # Change from 3 to 5
    ...
)
```

### Use Different Scenario

Load from file:

```python
from app.sales_simulation.scenarios.loader import ScenarioLoader

loader = ScenarioLoader()
scenario = loader.load_scenario("scenario_001_cold_call")
```

### Change Agent Behavior

Modify `DialogueAgentAdapter._determine_action_type()` to change action selection strategy.

## Troubleshooting

### Error: OPENAI_API_KEY not set

```bash
export OPENAI_API_KEY=your_key
```

### Error: Module not found

```bash
pip install -r requirements.txt
```

### Error: Agent generation failed

- Check API key validity
- Check network connectivity
- Check API rate limits
- Review logs for detailed error messages

## Next Steps

1. **Extend Scenario**: Add more complex scenarios
2. **Add Metrics**: Calculate additional evaluation metrics
3. **Batch Runs**: Run multiple episodes
4. **Export Data**: Save trajectories for analysis
5. **Visualization**: Create trajectory visualization

## Related Files

- `app/sales_simulation/runners/single_agent_runner.py`: Runner implementation
- `app/sales_simulation/agents/dialogue_agent.py`: Agent implementation
- `app/sales_simulation/schemas/scenario.py`: Scenario schemas
- `app/sales_simulation/schemas/trajectory.py`: Trajectory schemas


