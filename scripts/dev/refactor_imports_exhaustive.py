import os
import re

mapping = {
    # File name changes
    r'from app\.engine\.intent\.intent_gateway import IntentGateway': 'from cognitive.brain.intent.intent_classifier import IntentClassifier',
    r'from app\.observability\.tracing\.trace_manager import trace_manager': 'from cognitive.observability.tracing.execution_tracer import trace_manager',
    r'from app\.memory\.tracking\.followup_manager import followup_manager': 'from cognitive.memory.tracking.followup_tracker import followup_tracker',
    r'from app\.observability\.metrics\.performance import performance_metrics_collector': 'from cognitive.observability.metrics.business_metrics import performance_metrics_collector',
    r'from app\.infra\.guardrails\.runtime_guard import': 'from cognitive.infra.guardrails.runtime_guardrail import',
    r'from app\.engine\.state\.wal import wal_manager': 'from cognitive.brain.state.write_ahead_log import wal_manager',
    r'from app\.agents\.practice\.npc_generator_v3 import': 'from cognitive.skills.practice.npc_simulator import',
    r'from app\.agents\.evaluate\.evaluator_v3 import': 'from cognitive.skills.evaluate.performance_evaluator import',
    r'from app\.services\.shadow_summarizer import shadow_summarizer': 'from cognitive.memory.context.shadow_summarizer import shadow_summarizer',
    r'from app\.services\.followup_manager import followup_manager': 'from cognitive.memory.tracking.followup_tracker import followup_tracker',
    r'from app\.services\.memory_service import': 'from cognitive.memory.storage.memory_service import',
    r'from app\.infra\.gateway\.model_gateway\.gateway import ModelGateway': 'from cognitive.infra.gateway.model_gateway import ModelGateway',
    r'from app\.services\.runtime_guard import': 'from cognitive.infra.guardrails.runtime_guardrail import',
    r'from app\.services\.observability\.trace_manager import trace_manager': 'from cognitive.observability.tracing.execution_tracer import trace_manager',
    r'from app\.services\.performance_metrics import': 'from cognitive.observability.metrics.business_metrics import',
    r'from app\.services\.observability\.metrics import': 'from cognitive.observability.metrics.system_metrics import',
    r'from app\.engine\.orchestrator import': 'from cognitive.brain.coordinator.workflow_coordinator import',
    r'from app\.services\.prompt_service import': 'from cognitive.brain.coordinator.prompt_manager import',
    r'from app\.services\.background_tasks import': 'from cognitive.brain.coordinator.task_executor import',
    r'from app\.services\.sentiment_service import': 'from cognitive.skills.ask.sentiment_analyzer import',
    r'from app\.services\.correction_service import': 'from cognitive.skills.ask.correction_agent import',
    r'from app\.services\.dead_loop_prevention import': 'from cognitive.brain.coordinator.loop_guard import',
    r'from app\.services\.llm_service import': 'from cognitive.infra.gateway.llm_service import',
    r'from app\.services\.logging_service import': 'from cognitive.observability.logging_service import',
    r'from app\.services\.state_recovery import': 'from cognitive.brain.state.recovery import',
    r'from app\.services\.state_snapshot import': 'from cognitive.brain.state.snapshot import',
    r'from app\.services\.intent_classifier import': 'from cognitive.brain.intent.intent_classifier import',
    r'from app\.services\.curriculum_planner import': 'from cognitive.skills.evaluate.curriculum_planner import',
    r'from app\.services\.strategy_analyzer import': 'from cognitive.skills.evaluate.strategy_analyzer import',
    r'from app\.services\.adoption_tracker import': 'from cognitive.skills.evaluate.adoption_tracker import',
    r'from app\.services\.report_service import': 'from cognitive.skills.evaluate.report_generator import',
    r'from app\.services\.prompt_renderer import': 'from cognitive.brain.coordinator.prompt_renderer import',
    r'from app\.services\.cost_control import': 'from cognitive.infra.gateway.cost_control import',
    r'from app\.services\.data_quality_service import': 'from cognitive.skills.study.data_quality_agent import',
    r'from app\.services\.enhanced_task_registry import': 'from cognitive.brain.coordinator.task_registry import',
    r'from app\.services\.sales_coach\.schemas import': 'from cognitive.skills.ask.coach_schemas import',
    r'from app\.services\.task_registry import': 'from cognitive.brain.coordinator.task_registry import',
    r'from app\.services\.graph_rag_service import': 'from cognitive.skills.study.graph_rag_service import',
    r'from app\.services\.knowledge_service import': 'from cognitive.skills.study.knowledge_service import',
    r'from app\.services\.audio_service import': 'from cognitive.tools.connectors.audio_service import',
    r'from app\.services\.document_parser import': 'from cognitive.tools.parsers.document_parser import',
    r'from app\.services\.enhanced_document_parser import': 'from cognitive.tools.parsers.enhanced_parser import',
    r'from app\.services\.advanced_rag_service import': 'from cognitive.skills.study.advanced_rag_service import',
    r'from app\.services\.knowledge_service_qdrant import': 'from cognitive.skills.study.qdrant_service import',
    r'from app\.services\.context_engine import': 'from cognitive.memory.context.context_engine import',
    r'from app\.services\.orchestrator import': 'from cognitive.brain.coordinator.session_orchestrator import',
    r'from app\.services\.sales_coach import': 'from cognitive.skills.ask.coach_agent import',
    r'from app\.services\.state_updater import': 'from cognitive.brain.state.updater import',
    r'from app\.services\.memory\.storage import': 'from cognitive.memory.storage.backends.memory.storage import',
    r'from app\.services\.observability import': 'from app.observability import',
    r'from app\.services\.simple_state_snapshot import': 'from cognitive.brain.state.snapshot import',
    r'from app\.services\.graph_rag import': 'from cognitive.skills.study.graph_rag import',
    r'from app\.services\.advanced_rag import': 'from cognitive.skills.study.advanced_rag import',
    r'from app\.services\.ingestion import': 'from cognitive.tools.connectors.ingestion import',
    r'from app\.services\.retrieval_control_plane import': 'from cognitive.skills.study.retrieval_control import',
    r'from app\.services\.retrieval_protocol import': 'from cognitive.skills.study.retrieval_protocol import',
    r'from app\.services\.multimodal import': 'from cognitive.tools.connectors.multimodal import',
}

def refactor_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    sorted_keys = sorted(mapping.keys(), key=len, reverse=True)
    
    for old in sorted_keys:
        new = mapping[old]
        new_content = re.sub(old, new, new_content)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Refactored: {file_path}")

def main():
    for root, dirs, files in os.walk('app'):
        for file in files:
            if file.endswith('.py'):
                refactor_file(os.path.join(root, file))
    for root, dirs, files in os.walk('tests'):
        for file in files:
            if file.endswith('.py'):
                refactor_file(os.path.join(root, file))
    for root, dirs, files in os.walk('scripts'):
        for file in files:
            if file.endswith('.py'):
                refactor_file(os.path.join(root, file))
    for file in os.listdir('.'):
        if file.endswith('.py') and file != 'refactor_imports_exhaustive.py':
            refactor_file(file)

if __name__ == "__main__":
    main()
