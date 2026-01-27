import os
import re

# Comprehensive mapping for cognitive refactor
mapping = {
    # Perceptive / Intent
    r'app\.engine\.intent\.intent_gateway': 'app.engine.intent.intent_classifier',
    r'app\.services\.intent_classifier': 'app.engine.intent.intent_classifier',
    
    # Cognition / Coordinator
    r'app\.engine\.orchestrator': 'app.engine.coordinator.workflow_coordinator',
    r'app\.services\.orchestrator': 'app.engine.coordinator.workflow_coordinator',
    r'app\.services\.prompt_service': 'app.engine.coordinator.prompt_manager',
    r'app\.services\.background_tasks': 'app.engine.coordinator.task_executor',
    r'app\.services\.dead_loop_prevention': 'app.engine.coordinator.loop_guard',
    r'app\.services\.prompt_renderer': 'app.engine.coordinator.prompt_renderer',
    r'app\.services\.enhanced_task_registry': 'app.engine.coordinator.task_registry',
    r'app\.services\.task_registry': 'app.engine.coordinator.task_registry',
    
    # Execution / Agents
    r'app\.services\.knowledge_engine': 'app.agents.study.knowledge_retriever',
    r'app\.services\.micro_feedback_service': 'app.agents.ask.feedback_agent',
    r'app\.agents\.practice\.npc_generator_v3': 'app.agents.practice.npc_simulator',
    r'app\.agents\.practice\.npc_generator': 'app.agents.practice.npc_simulator',
    r'app\.agents\.evaluate\.evaluator_v3': 'app.agents.evaluate.performance_evaluator',
    r'app\.agents\.evaluate\.evaluator': 'app.agents.evaluate.performance_evaluator',
    r'app\.agents\.evaluate\.adoption_tracker_v3': 'app.agents.evaluate.adoption_tracker',
    r'app\.services\.sentiment_service': 'app.agents.ask.sentiment_analyzer',
    r'app\.services\.correction_service': 'app.agents.ask.correction_agent',
    r'app\.services\.curriculum_planner': 'app.agents.evaluate.curriculum_planner',
    r'app\.services\.strategy_analyzer': 'app.agents.evaluate.strategy_analyzer',
    r'app\.services\.adoption_tracker': 'app.agents.evaluate.adoption_tracker',
    r'app\.services\.report_service': 'app.agents.evaluate.report_generator',
    r'app\.services\.sales_coach': 'app.agents.ask.feedback_agent',
    r'app\.agents\.practice\.coach_generator': 'app.agents.ask.coach_generator',
    
    # Memory
    r'app\.services\.shadow_summarizer': 'app.memory.context.shadow_summarizer',
    r'app\.services\.followup_manager': 'app.memory.tracking.followup_tracker',
    r'app\.services\.memory_service': 'app.memory.storage.memory_service',
    r'app\.services\.context_engine': 'app.memory.context.context_engine',
    
    # Infra
    r'app\.services\.model_gateway': 'app.infra.gateway.model_gateway',
    r'app\.infra\.gateway\.model_gateway\.gateway': 'app.infra.gateway.model_gateway',
    r'app\.services\.runtime_guard': 'app.infra.guardrails.runtime_guardrail',
    r'app\.services\.llm_service': 'app.infra.gateway.llm_service',
    r'app\.services\.cost_control': 'app.infra.gateway.cost_control',
    
    # Observability
    r'app\.services\.observability\.trace_manager': 'app.observability.tracing.execution_tracer',
    r'app\.services\.performance_metrics': 'app.observability.metrics.business_metrics',
    r'app\.services\.observability\.metrics': 'app.observability.metrics.system_metrics',
    r'app\.services\.logging_service': 'app.observability.logging_service',
    
    # State
    r'app\.engine\.state\.wal': 'app.engine.state.write_ahead_log',
    r'app\.services\.state\.wal': 'app.engine.state.write_ahead_log',
    r'app\.services\.state_recovery': 'app.engine.state.recovery',
    r'app\.services\.state_snapshot': 'app.engine.state.snapshot',
    r'app\.services\.state_updater': 'app.engine.state.updater',
    r'app\.services\.memory\.local_storage': 'app.memory.storage.backends.memory.local_storage',
    r'app\.services\.memory\.sqlite_storage': 'app.memory.storage.backends.memory.sqlite_storage',
    r'app\.agents\.practice\.coach_agent': 'app.agents.ask.coach_agent',
    r'app\.agents\.practice\.coach_generator': 'app.agents.ask.coach_generator',
}

def refactor_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    # Sort mapping by key length descending to handle nested paths correctly
    sorted_keys = sorted(mapping.keys(), key=len, reverse=True)
    
    for old in sorted_keys:
        new = mapping[old]
        new_content = re.sub(old, new, new_content)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Refactored: {file_path}")

def main():
    dirs_to_scan = ['app', 'tests', 'scripts']
    for d in dirs_to_scan:
        if not os.path.exists(d): continue
        for root, dirs, files in os.walk(d):
            for file in files:
                if file.endswith('.py'):
                    refactor_file(os.path.join(root, file))
    
    for file in os.listdir('.'):
        if file.endswith('.py') and 'refactor' not in file:
            refactor_file(file)

if __name__ == "__main__":
    main()
