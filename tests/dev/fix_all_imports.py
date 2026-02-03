#!/usr/bin/env python3
"""
全面修复所有 import 路径
"""
import re
from pathlib import Path

# 完整的 import 修复映射
FIXES = [
    # Gateway
    (r'from app\.infra\.gateway\.providers', 'from cognitive.infra.providers'),
    (r'from app\.infra\.gateway\.model_gateway\.', 'from cognitive.infra.gateway.'),
    (r'import app\.infra\.gateway\.model_gateway', 'import app.infra.gateway'),
    
    # Providers
    (r'from app\.infra\.providers\.providers\.', 'from cognitive.infra.providers.'),
    
    # Observability
    (r'from app\.observability\.logging_service', 'from cognitive.observability.logging_service'),
    (r'from app\.observability\.tracing import trace_manager', 'from cognitive.observability.tracing.execution_tracer import trace_manager'),
    
    # Recovery
    (r'SessionOrchestrator\(\)', 'WorkflowCoordinator('),
    (r'orchestrator\.', 'coordinator.'),
    
    # 其他
    (r'from app\.services\.state_recovery', 'from cognitive.brain.state.recovery'),
]

def fix_file(file_path: Path):
    """修复单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        for pattern, replacement in FIXES:
            content = re.sub(pattern, replacement, content)
        
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error: {file_path}: {e}")
        return False

def main():
    app_dir = Path('app')
    updated = 0
    
    for py_file in app_dir.rglob('*.py'):
        if fix_file(py_file):
            updated += 1
            print(f"Fixed: {py_file}")
    
    print(f"\nTotal: {updated} files updated")

if __name__ == '__main__':
    main()
